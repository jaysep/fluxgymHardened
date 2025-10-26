# sd-scripts Hang Analysis: Root Causes & Mitigations

## Executive Summary

After thorough analysis of the Kohya sd-scripts codebase, I've identified **multiple potential hang points** where GPU usage can drop to 0% and training gets stuck indefinitely.

**Key Finding**: The sd-scripts **can definitely cause itself to hang**, with the most critical issue being the **block swapping mechanism** that uses multiple CUDA synchronization points without timeout handling.

---

## Critical Hang Points (Ordered by Severity)

### 🔴 CRITICAL: Block Swapping Deadlock

**Location**: `sd-scripts/library/custom_offloading_utils.py`

**The Issue**:
```python
# Lines 43-60
def swap_weight_devices_cuda(device, layer_to_cpu, layer_to_cuda):
    torch.cuda.current_stream().synchronize()  # BLOCKING - no timeout

    stream = torch.Stream(device="cuda")
    with torch.cuda.stream(stream):
        # Weight transfers...
        stream.synchronize()  # BLOCKING - no timeout

    stream.synchronize()  # BLOCKING - no timeout
    torch.cuda.current_stream().synchronize()  # BLOCKING - no timeout
```

**Why It Hangs**:
- **4 synchronization points** that can deadlock if CUDA kernels stall
- Uses `ThreadPoolExecutor(max_workers=1)` - single-threaded, so if one swap blocks, everything stops
- `future.result()` at line 144 **blocks indefinitely** waiting for thread completion
- **No timeout mechanism** on any blocking operation

**When It Happens**:
- Training with `--blocks_to_swap > 0` (memory optimization for FLUX)
- During denoising loop when swapping double blocks in/out of VRAM
- CUDA kernel failures or memory fragmentation

**Impact**: Complete training freeze, GPU usage drops to 0%

**Mitigation**:
```python
# Add timeout to future.result()
try:
    _, bidx_to_cuda = future.result(timeout=30.0)  # 30 second timeout
except TimeoutError:
    logger.error(f"Block swap timed out for block {block_idx}")
    raise
```

**Workaround for Users**: Use `--blocks_to_swap 0` to disable block swapping

---

### 🔴 HIGH: DataLoader Worker Deadlock

**Location**: `sd-scripts/flux_train.py` lines 394-402

**The Issue**:
```python
train_dataloader = torch.utils.data.DataLoader(
    train_dataset_group,
    batch_size=1,
    shuffle=True,
    collate_fn=collator,
    num_workers=n_workers,
    persistent_workers=args.persistent_data_loader_workers,
    # NO TIMEOUT PARAMETER!
)
```

**Why It Hangs**:
- Worker processes can deadlock when loading cached latents from disk
- `persistent_workers=True` keeps workers alive, but if they deadlock, training hangs forever
- Workers share `multiprocessing.Value` for epoch/step tracking (potential race condition)
- Image loading with `ThreadPoolExecutor` can starve if disk I/O blocks
- No `timeout` parameter means blocked workers wait indefinitely

**When It Happens**:
- Large datasets with many workers (`--max_data_loader_n_workers > 2`)
- Network filesystems (NFS, SMB) causing I/O delays
- Corrupted cache files or latent NPZ files
- Disk I/O saturation

**Impact**: Training hangs waiting for batch data, GPU idle

**Mitigation**:
```python
train_dataloader = torch.utils.data.DataLoader(
    train_dataset_group,
    batch_size=1,
    shuffle=True,
    collate_fn=collator,
    num_workers=n_workers,
    persistent_workers=args.persistent_data_loader_workers,
    timeout=60,  # 60 second timeout
    pin_memory=True,  # Faster GPU transfers
)
```

**Workaround for Users**: Use `--max_data_loader_n_workers 0` to disable multiprocessing

---

### 🔴 HIGH: File I/O Blocking (No Timeouts)

**Location**: `sd-scripts/library/train_util.py` lines 1594-1606

**The Issue**:
```python
elif image_info.latents_npz is not None:
    # NO TIMEOUT on NPZ file loading
    latents, original_size, crop_ltrb, flipped_latents, alpha_mask = (
        self.latents_caching_strategy.load_latents_from_disk(
            image_info.latents_npz, image_info.bucket_reso
        )
    )
```

**Why It Hangs**:
- NPZ file loading has no timeout
- Network filesystems (NFS, SMB on cloud) can hang indefinitely on I/O
- No error handling for corrupted cache files
- Text encoder cache loading (NPZ files) also has no timeout
- `ThreadPoolExecutor` for image loading can exhaust file descriptors

**When It Happens**:
- Network storage with high latency or connection issues
- Corrupted cache files (`.npz` files)
- Disk errors or filesystem issues
- File locking conflicts (multiple processes)

**Impact**: Hangs during data loading or cache preparation

**Mitigation**: Wrap file I/O in timeout decorators, validate cache files before loading

**Workaround for Users**: Use local SSD storage instead of network mounts, delete cache and rebuild

---

### 🟠 HIGH: Distributed Synchronization Deadlocks

**Location**: `sd-scripts/flux_train.py` multiple locations

**The Issue**:
```python
# Line 207: After latent caching
accelerator.wait_for_everyone()  # NO TIMEOUT

# Line 265: After text encoder caching
accelerator.wait_for_everyone()  # NO TIMEOUT

# Line 714: Before checkpoint saving
accelerator.wait_for_everyone()  # NO TIMEOUT

# Line 747: At epoch end
accelerator.wait_for_everyone()  # NO TIMEOUT
```

**Why It Hangs**:
- If one process crashes/hangs during caching, all processes wait forever
- No timeout on distributed synchronization primitives
- Multi-GPU training hangs if one GPU has OOM or CUDA error
- Process 0 (main) may continue while others are stuck

**When It Happens**:
- Multi-GPU training (`--num_processes > 1`)
- One GPU has different memory/compute capacity
- CUDA errors on specific GPU
- Cache corruption on one process

**Impact**: All processes frozen, GPUs idle

**Mitigation**: Implement health checks, add timeouts to sync operations

**Workaround for Users**: Single GPU training only

---

### 🟠 MEDIUM-HIGH: Sample Generation Blocking

**Location**: `sd-scripts/library/flux_train_utils.py` lines 33-413

**The Issue**:
```python
def sample_images(accelerator, args, epoch, steps, flux, ae, text_encoders, ...):
    with torch.no_grad(), accelerator.autocast():
        for prompt_dict in prompts:
            sample_image_inference(...)  # Can hang on model.forward()

# Denoising loop (lines 353-413)
for t_curr, t_prev in zip(tqdm(timesteps[:-1]), timesteps[1:]):
    model.prepare_block_swap_before_forward()  # BLOCKING - waits for weight swap
    pred = model(...)  # Forward pass can hang
```

**Why It Hangs**:
- Sample generation happens at step 0, every N steps, every N epochs
- No timeout on forward passes during sampling
- **Block swap preparation is synchronous** - if swap hangs, sampling hangs
- Main training loop is blocked until sampling completes
- TQDM progress bar can cause buffering issues

**When It Happens**:
- Using `--sample_every_n_steps` or `--sample_every_n_epochs`
- Block swapping enabled during sampling
- CUDA errors during inference
- OOM during sample generation

**Impact**: Training freezes during sampling, can appear stuck at specific steps

**Mitigation**: Make sampling async or add timeout, handle CUDA errors gracefully

**Workaround for Users**: Disable sampling (`--sample_every_n_steps 0`)

---

### 🟡 MEDIUM: Fused Optimizer Gradient Hook Issues

**Location**: `sd-scripts/flux_train.py` lines 476-530

**The Issue**:
```python
if args.blockwise_fused_optimizers:
    def grad_hook(parameter: torch.Tensor):
        if accelerator.sync_gradients and args.max_grad_norm != 0.0:
            accelerator.clip_grad_norm_(parameter, args.max_grad_norm)

        i = parameter_optimizer_map[parameter]
        optimizer_hooked_count[i] += 1
        if optimizer_hooked_count[i] == num_parameters_per_group[i]:
            optimizers[i].step()  # BLOCKING
            optimizers[i].zero_grad(set_to_none=True)

    parameter.register_post_accumulate_grad_hook(grad_hook)
```

**Why It Hangs**:
- If gradient accumulation fails (e.g., NaN gradients), hook may never trigger
- Counter mismatch causes `optimizer.step()` to never be called
- No error handling if parameter count changes dynamically
- Counter reset at line 594 could race with backward pass

**When It Happens**:
- Using `--blockwise_fused_optimizers`
- NaN/Inf gradients
- Dynamic parameter freezing/unfreezing
- Gradient accumulation edge cases

**Impact**: Optimizer never steps, training appears to continue but model doesn't update

**Mitigation**: Add safety checks, timeout on hook execution, validate counters

**Workaround for Users**: Don't use `--blockwise_fused_optimizers`

---

### 🟡 MEDIUM: CUDA Memory Allocation Stalls

**Location**: `sd-scripts/flux_train.py` lines 598, 602, 637

**The Issue**:
```python
# Line 598: Large tensor transfer
latents = batch["latents"].to(accelerator.device, dtype=weight_dtype)

# Line 602: AutoEncoder encoding
latents = ae.encode(batch["images"].to(ae.dtype))

# Line 637: Image ID preparation
img_ids = flux_utils.prepare_img_ids(...).to(device=accelerator.device)
```

**Why It Hangs**:
- CUDA malloc can stall if memory is fragmented
- No explicit memory cleanup before large allocations
- Gradient accumulation without clearing can cause gradual memory growth
- Block swapping moves weights but doesn't guarantee freed memory is available

**When It Happens**:
- Limited VRAM (12GB, 16GB configs)
- Memory fragmentation over time
- Gradient accumulation enabled
- Large batch sizes or resolutions

**Impact**: CUDA allocation hangs, appears as GPU idle but process alive

**Mitigation**: Call `torch.cuda.empty_cache()` periodically, better memory management

**Workaround for Users**: Lower resolution, disable gradient accumulation, use lower VRAM config

---

### 🟡 MEDIUM: Checkpoint Saving Blocking

**Location**: `sd-scripts/library/flux_train_utils.py` lines 550-612

**The Issue**:
```python
def save_models(ckpt_path, flux, sai_metadata, save_dtype, use_mem_eff_save):
    state_dict = {}
    # ... collect state dict ...
    if not use_mem_eff_save:
        save_file(state_dict, ckpt_path, metadata=sai_metadata)  # BLOCKING I/O
    else:
        mem_eff_save_file(state_dict, ckpt_path, metadata=sai_metadata)  # BLOCKING I/O
```

**Why It Hangs**:
- No timeout on safetensors save (can be 5-10GB files)
- Network filesystem writes can hang indefinitely
- Disk full errors not caught gracefully
- Only main process saves, but other processes wait at barrier

**When It Happens**:
- Network storage with high latency
- Disk full or quota exceeded
- File locking conflicts
- Slow I/O systems

**Impact**: All processes frozen during checkpoint save

**Mitigation**: Save to local disk first, then copy; add timeout wrapper

**Workaround for Users**: Save to local SSD, increase `--save_every_n_epochs` frequency

---

## Summary Table: Hang Points by Severity

| Severity | Location | Issue | User Impact | Workaround |
|----------|----------|-------|-------------|------------|
| 🔴 **CRITICAL** | `custom_offloading_utils.py` | Block swap deadlock | Complete freeze | `--blocks_to_swap 0` |
| 🔴 **HIGH** | `flux_train.py:394` | DataLoader deadlock | Hangs on data loading | `--max_data_loader_n_workers 0` |
| 🔴 **HIGH** | `train_util.py:1594` | File I/O no timeout | Hangs on cache load | Use local SSD storage |
| 🟠 **HIGH** | `flux_train.py:207,265,714,747` | Distributed sync deadlock | Multi-GPU freeze | Single GPU only |
| 🟠 **MEDIUM-HIGH** | `flux_train_utils.py:33-413` | Sample generation blocking | Hangs at sampling steps | `--sample_every_n_steps 0` |
| 🟡 **MEDIUM** | `flux_train.py:476` | Fused optimizer hooks | Silent training failure | Don't use blockwise fused |
| 🟡 **MEDIUM** | `flux_train.py:598,602,637` | CUDA malloc stalls | GPU idle, OOM | Lower resolution/VRAM |
| 🟡 **MEDIUM** | `flux_train_utils.py:550` | Checkpoint save blocking | Hangs at save epochs | Save to local disk |

---

## Diagnostic Workflow

When training hangs, check in this order:

### 1. Check GPU Activity
```bash
nvidia-smi dmon -s u
# If GPU util = 0% for >5 minutes, training is stuck
```

### 2. Check Process State
```bash
ps aux | grep flux_train_network
# If process exists but GPU idle = hang
# If process missing = crashed
```

### 3. Check Last Training Log Entry
```bash
tail -n 50 outputs/my-lora/training.log
# Look for last activity timestamp
# Check if stuck at specific step/epoch
```

### 4. Check for Specific Hang Patterns

**Block swap hang**:
```bash
grep "prepare_block_swap" outputs/my-lora/training.log | tail -n 1
# If last entry was block swap preparation = block swap deadlock
```

**DataLoader hang**:
```bash
# Training log shows no progress for >2 minutes
# Last entry: "steps: X%" with no increment
```

**Sample generation hang**:
```bash
grep -i "sample" outputs/my-lora/training.log | tail -n 5
# If last entry is "Generating samples" with no completion
```

**Checkpoint save hang**:
```bash
grep -i "saving" outputs/my-lora/training.log | tail -n 5
# If last entry is "Saving checkpoint" with no completion
```

---

## Recommended FluxGym Parameters for Stability

To minimize hang risk, use these settings:

```python
# In FluxGym UI:
✅ Enable Checkpointing (for recovery)
✅ Enable Auto-Monitoring (for detection)

# Recommended VRAM-specific settings:

# 12GB VRAM:
--blocks_to_swap 0               # Disable block swapping (critical!)
--max_data_loader_n_workers 1    # Minimize DataLoader issues
--gradient_checkpointing         # Save memory without swapping
--sample_every_n_steps 0         # Disable sampling
--cache_latents                  # Pre-cache to avoid runtime I/O

# 16GB VRAM:
--blocks_to_swap 0               # Still risky, disable
--max_data_loader_n_workers 2    # Safe with timeout
--sample_every_n_steps 100       # Enable but monitor
--cache_latents                  # Pre-cache recommended

# 20GB VRAM:
--blocks_to_swap 0               # Enough VRAM, no need for swapping
--max_data_loader_n_workers 2    # Safe
--sample_every_n_steps 50        # Can generate more frequently
--cache_latents_to_disk          # Optional, helps with large datasets
```

---

## How FluxGym's Monitoring Helps

The `training_monitor.py` script we implemented detects these hangs:

```python
# Monitors GPU every 30 seconds
gpu_util = get_gpu_utilization()

if gpu_util < 5.0:  # GPU essentially idle
    stuck_duration += check_interval

    if stuck_duration >= 300:  # 5 minutes of idle
        # HANG DETECTED!
        # Kills stuck processes
        # Logs checkpoint path for resume
```

**What it catches**:
- ✅ Block swap deadlocks (GPU drops to 0%)
- ✅ DataLoader deadlocks (GPU idle waiting for data)
- ✅ File I/O hangs (GPU idle waiting for cache)
- ✅ Sample generation hangs (GPU idle during sampling)
- ✅ CUDA malloc stalls (GPU idle on allocation)

**What it doesn't catch**:
- ❌ Distributed sync deadlocks (processes alive, no GPU usage)
- ❌ Checkpoint save hangs (intermittent, happens at save points only)

---

## Upstream Fix Recommendations for Kohya sd-scripts

These should be reported/contributed to the Kohya repo:

### 1. Add Timeout to Block Swapping
```python
# In custom_offloading_utils.py line 144:
future = self.futures.pop(block_idx)
try:
    _, bidx_to_cuda = future.result(timeout=30.0)
except TimeoutError:
    logger.error(f"Block swap timeout for block {block_idx}")
    raise RuntimeError("Block swap deadlock detected")
```

### 2. Add DataLoader Timeout
```python
# In flux_train.py line 394:
train_dataloader = torch.utils.data.DataLoader(
    train_dataset_group,
    batch_size=1,
    shuffle=True,
    collate_fn=collator,
    num_workers=n_workers,
    persistent_workers=args.persistent_data_loader_workers,
    timeout=60,  # NEW: 60 second worker timeout
    pin_memory=True,  # NEW: Faster GPU transfers
)
```

### 3. Add File I/O Timeout Wrapper
```python
# In train_util.py, wrap NPZ loading:
import signal
from contextlib import contextmanager

@contextmanager
def timeout_context(seconds):
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds}s")

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

# Use it:
with timeout_context(30):
    latents = self.latents_caching_strategy.load_latents_from_disk(...)
```

### 4. Add Distributed Sync Timeout
```python
# In flux_train.py, replace wait_for_everyone():
def wait_with_timeout(accelerator, timeout=300):
    """Wait for all processes with timeout"""
    # Implementation using threading + timeout
    pass

# Use it:
wait_with_timeout(accelerator, timeout=300)  # 5 minute max
```

---

## Conclusion

**YES**, the sd-scripts can definitely cause training to hang due to:

1. **Block swapping deadlocks** (most critical)
2. **DataLoader worker deadlocks** (very common)
3. **File I/O operations without timeouts** (especially on cloud)
4. **Distributed synchronization without timeouts** (multi-GPU)
5. **Sample generation blocking main loop** (periodic)

**FluxGym's monitoring system successfully detects most of these**, but the root cause is in the upstream sd-scripts code.

**Best mitigation strategy**:
1. Use recommended parameters (disable block swapping, limit workers)
2. Keep monitoring enabled (auto-detect and kill stuck training)
3. Keep checkpointing enabled (resume from last good state)
4. Use local SSD storage (avoid network filesystem hangs)

The hang issue is **not a bug in FluxGym** but rather **inherent limitations in the upstream Kohya sd-scripts** that lack proper timeout handling and error recovery mechanisms.
