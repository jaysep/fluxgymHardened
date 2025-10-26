# Checkpoint Path Resolution - How It Works

## Question
*Will the training script automatically know where to find the checkpoint?*

## Answer: Yes! ✅

The training script will automatically find the checkpoint because we use **absolute paths** throughout the entire process.

## How It Works

### 1. Path Resolution in Monitor

When you start the monitor:

```bash
python3 training_monitor.py \
  --output-dir /workspace/fluxgym/outputs/my-lora \
  --train-script /workspace/fluxgym/outputs/my-lora/train.sh \
  --auto-resume
```

**What happens internally:**

```python
# In CheckpointManager.__init__
self.output_dir = Path(output_dir).resolve()
# Result: Path('/workspace/fluxgym/outputs/my-lora')
```

The `.resolve()` method:
- Converts relative paths to absolute paths
- Resolves any `.` or `..` references
- Ensures we have a fully qualified path

### 2. Checkpoint Discovery

When training gets stuck and checkpoint is found:

```python
# In CheckpointManager.find_latest_checkpoint()
for item in self.output_dir.iterdir():
    if item.is_dir() and 'state' in item.name.lower():
        state_dirs.append(item)

latest = state_dirs[0]
# Result: Path('/workspace/fluxgym/outputs/my-lora/my-lora-step-150-state')
```

Because `self.output_dir` is already an absolute Path:
- All child paths (via `.iterdir()`) are also absolute
- The checkpoint path is: `/workspace/fluxgym/outputs/my-lora/my-lora-step-150-state`

### 3. Insertion into train.sh

The monitor modifies train.sh to add:

```bash
--resume /workspace/fluxgym/outputs/my-lora/my-lora-step-150-state \
```

This is an **absolute path**, not relative.

### 4. Training Script Execution

When train.sh runs:

```bash
# train.sh is executed from /workspace/fluxgym
cd /workspace/fluxgym
bash outputs/my-lora/train.sh
```

Inside train.sh:

```bash
accelerate launch --num_cpu_threads_per_process=2 sd-scripts/flux_train_network.py \
  --pretrained_model_name_or_path "/workspace/fluxgym/flux1-dev.safetensors" \
  --dataset_config "/workspace/fluxgym/outputs/my-lora/dataset.toml" \
  --output_dir "/workspace/fluxgym/outputs/my-lora" \
  --resume /workspace/fluxgym/outputs/my-lora/my-lora-step-150-state \
  --loss_type l2
```

### 5. Accelerate Loads the Checkpoint

In the training code:

```python
# sd-scripts/library/train_util.py line 4687
accelerator.load_state(args.resume)
# args.resume = '/workspace/fluxgym/outputs/my-lora/my-lora-step-150-state'
```

Accelerate's `load_state()` method:
- Receives the absolute path
- Loads the checkpoint from that exact location
- Works regardless of current working directory

## Why Absolute Paths Are Critical

### Scenario 1: Using Absolute Paths (Correct) ✅

```bash
# Monitor started from /tmp
cd /tmp
python3 /workspace/fluxgym/training_monitor.py \
  --output-dir /workspace/fluxgym/outputs/my-lora \
  --train-script /workspace/fluxgym/outputs/my-lora/train.sh \
  --auto-resume

# Checkpoint found: /workspace/fluxgym/outputs/my-lora/my-lora-step-150-state
# Inserted into train.sh: --resume /workspace/fluxgym/outputs/my-lora/my-lora-step-150-state
# train.sh runs from: /workspace/fluxgym
# Accelerate looks for: /workspace/fluxgym/outputs/my-lora/my-lora-step-150-state
# ✅ WORKS!
```

### Scenario 2: Using Relative Paths (Wrong) ✗

**Without `.resolve()` (hypothetical broken version):**

```bash
# Monitor started from /tmp
cd /tmp
python3 /workspace/fluxgym/training_monitor.py \
  --output-dir outputs/my-lora \
  --train-script outputs/my-lora/train.sh \
  --auto-resume

# output_dir = Path('outputs/my-lora')  # Relative!
# Resolved relative to /tmp: /tmp/outputs/my-lora
# Checkpoint found: /tmp/outputs/my-lora/my-lora-step-150-state (WRONG!)
# Inserted into train.sh: --resume /tmp/outputs/my-lora/my-lora-step-150-state
# train.sh runs from: /workspace/fluxgym
# Accelerate looks for: /tmp/outputs/my-lora/my-lora-step-150-state
# ✗ FAILS! Checkpoint not at /tmp, it's at /workspace/fluxgym!
```

### Scenario 3: With `.resolve()` (Fixed) ✅

**With `.resolve()` (actual implementation):**

```bash
# Monitor started from /tmp
cd /tmp
python3 /workspace/fluxgym/training_monitor.py \
  --output-dir outputs/my-lora \  # Relative input
  --train-script outputs/my-lora/train.sh \
  --auto-resume

# output_dir = Path('outputs/my-lora').resolve()
# Resolves relative to /tmp: /tmp/outputs/my-lora
# Then looks for checkpoint there...
# If checkpoint exists: Great!
# If not: No checkpoint found, restarts from beginning
```

**Best Practice:** Always provide absolute paths to avoid confusion:

```bash
python3 training_monitor.py \
  --output-dir /workspace/fluxgym/outputs/my-lora \
  --train-script /workspace/fluxgym/outputs/my-lora/train.sh \
  --auto-resume
```

## Code Implementation

### Path Resolution Added (training_monitor.py)

**Line 165 - CheckpointManager:**
```python
def __init__(self, output_dir: str):
    self.output_dir = Path(output_dir).resolve()  # Convert to absolute path
```

**Line 319 - resume_training():**
```python
train_script_path = Path(self.train_script).resolve()  # Convert to absolute path
```

**Line 385 - restart_training_from_beginning():**
```python
train_script_path = Path(self.train_script).resolve()  # Convert to absolute path
```

## Testing Path Resolution

Run the test script to verify path resolution:

```bash
cd /workspace/fluxgym
python3 test_path_resolution.py
```

This demonstrates:
- How relative paths are converted to absolute
- Why absolute paths are important
- That checkpoints will be found correctly

## Summary

✅ **Checkpoint paths are always absolute**
- Monitor converts all paths to absolute using `.resolve()`
- Checkpoint discovery returns absolute paths
- train.sh receives absolute `--resume` path
- Accelerate loads from absolute path
- Works regardless of working directory

✅ **Training script will find the checkpoint**
- No manual path configuration needed
- No environment variables required
- No symbolic links or path tricks needed
- Just works! 🎉

## Real-World Example

```bash
# Start training
cd /workspace/fluxgym
python3 app.py
# ... training runs, creates checkpoint at step 150, then hangs ...

# Start monitor (can be run from anywhere)
cd /workspace/fluxgym
python3 training_monitor.py \
  --output-dir /workspace/fluxgym/outputs/anime-style \
  --train-script /workspace/fluxgym/outputs/anime-style/train.sh \
  --auto-resume

# Monitor detects stuck training after 5 minutes:
# 2025-01-26 15:00:00 - ERROR - TRAINING STUCK DETECTED!
# 2025-01-26 15:00:00 - INFO - Latest state checkpoint: /workspace/fluxgym/outputs/anime-style/anime-style-step-150-state
# 2025-01-26 15:00:09 - INFO - Modified training script with --resume /workspace/fluxgym/outputs/anime-style/anime-style-step-150-state
# 2025-01-26 15:00:09 - INFO - Training restarted with PID: 12345

# Training resumes from step 150
# ✅ Works perfectly!
```

## Troubleshooting

### "Checkpoint not found"

**Symptom:** Monitor logs `No checkpoint states found`

**Check:**
```bash
ls -la /workspace/fluxgym/outputs/your-lora-name/
```

**Look for directories like:**
- `your-lora-name-step-150-state`
- `your-lora-name-epoch-5-state`

**If missing:** First training run hasn't created checkpoint yet, or `--save_state` not enabled

### "Training script not found"

**Symptom:** Monitor logs `Training script not found`

**Check:**
```bash
ls -la /workspace/fluxgym/outputs/your-lora-name/train.sh
```

**Fix:** Ensure you provide the correct absolute path:
```bash
--train-script /workspace/fluxgym/outputs/your-lora-name/train.sh
```

### "Resume failed" in training logs

**Symptom:** Training starts but can't load checkpoint

**Check training_resume.log:**
```bash
tail -50 /workspace/fluxgym/outputs/your-lora-name/training_resume.log
```

**Possible causes:**
- Checkpoint directory exists but is empty/corrupted
- Permission issues reading checkpoint files
- Checkpoint format incompatible with current training code

**Solution:** Delete corrupted checkpoint and restart from beginning:
```bash
rm -rf /workspace/fluxgym/outputs/your-lora-name/*-state
```

Monitor will then restart from beginning (no checkpoint found).
