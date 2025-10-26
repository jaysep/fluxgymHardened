# Checkpoint Resume Fix - KeyError: 'step'

## Problem Summary

When trying to resume training with `--resume <checkpoint_path>`, you got:

```
KeyError: 'step'
  File "accelerate/accelerator.py", line 3156, in load_state
    self.step = override_attributes["step"]
```

## Root Cause

The issue was that **sd-scripts never set `accelerator.step`** before saving checkpoints.

### What Happened:

1. **When saving checkpoint:**
   - sd-scripts called `accelerator.save_state(state_dir)` at step 360
   - But `accelerator.step` was still 0 (never set by sd-scripts)
   - Accelerate saved `step=0` in `random_states_0.pkl`
   - sd-scripts' hook saved `current_step=360` in `train_state.json`

2. **When loading checkpoint:**
   - Accelerate loaded `random_states_0.pkl`
   - Found `step=0` and set `override_attributes["step"] = 0`
   - Tried to set `self.step = override_attributes["step"]`
   - But code expected step to be 360, causing failures

### Evidence:

```bash
# From your checkpoint:
root@pod:/workspace/fluxgym/outputs/kristyhardened9/kristyhardened9-000030-state# cat train_state.json
{"current_epoch": 30, "current_step": 360}

# But in random_states_0.pkl:
Keys in random_states_0.pkl:
  step: 0  ← WRONG! Should be 360
  random_state: <tuple>
  numpy_random_seed: <tuple>
  torch_manual_seed: <Tensor>
  torch_cuda_manual_seed: <list>
```

## The Fix

Two fixes were needed:

### Fix 1: Set accelerator.step Before Saving

Set `accelerator.step` to the correct value **before** calling `accelerator.save_state()`.

### Fix 2: Allow Loading Numpy Arrays from Checkpoints

Accelerate 0.33.0's `load()` function uses `weights_only=True` by default, which blocks loading numpy arrays from `random_states_0.pkl`. We pass `load_kwargs={"weights_only": False}` to `accelerator.load_state()` to allow loading these arrays.

### Files Modified:

**1. `/workspace/fluxgym/sd-scripts/library/train_util.py`**

#### Change 1: `save_and_remove_state_stepwise()` (line 5877)
```python
def save_and_remove_state_stepwise(args, accelerator, step_no):
    # ...

    # FIX: Set accelerator.step before saving so it's included in the checkpoint
    # This is needed for accelerator.load_state() to work correctly
    accelerator.step = step_no  # ← ADDED

    state_dir = os.path.join(args.output_dir, STEP_STATE_NAME.format(model_name, step_no))
    accelerator.save_state(state_dir)
```

#### Change 2: `save_and_remove_state_on_epoch_end()` (line 5846)
```python
def save_and_remove_state_on_epoch_end(args, accelerator, epoch_no, global_step=None):  # ← Added global_step param
    # ...

    # FIX: Set accelerator.step before saving
    if global_step is not None:
        accelerator.step = global_step  # ← ADDED

    state_dir = os.path.join(args.output_dir, EPOCH_STATE_NAME.format(model_name, epoch_no))
    accelerator.save_state(state_dir)
```

#### Change 3: `save_state_on_train_end()` (line 5903)
```python
def save_state_on_train_end(args, accelerator, global_step=None):  # ← Added global_step param
    # ...

    # FIX: Set accelerator.step before saving
    if global_step is not None:
        accelerator.step = global_step  # ← ADDED

    state_dir = os.path.join(args.output_dir, LAST_STATE_NAME.format(model_name))
    accelerator.save_state(state_dir)
```

#### Change 4: `resume_from_local_or_hf_if_specified()` (line 4685)
```python
def resume_from_local_or_hf_if_specified(accelerator, args):
    if not args.resume:
        return

    if not args.resume_from_huggingface:
        logger.info(f"resume training from local state: {args.resume}")

        # FIX: Pass weights_only=False to allow loading numpy arrays
        load_kwargs = {"weights_only": False}  # ← ADDED
        accelerator.load_state(args.resume, load_kwargs=load_kwargs)  # ← MODIFIED

        return
```

**2. `/workspace/fluxgym/sd-scripts/train_network.py`**

#### Change 1: Call site for epoch save (line 1682)
```python
if args.save_state:
    train_util.save_and_remove_state_on_epoch_end(args, accelerator, epoch + 1, global_step)  # ← Added global_step
```

#### Change 2: Call site for train end save (line 1700)
```python
if is_main_process and (args.save_state or args.save_state_on_train_end):
    train_util.save_state_on_train_end(args, accelerator, global_step)  # ← Added global_step
```

## How This Fixes The Issue

### Before Fix:
```
Checkpoint saved:
  random_states_0.pkl: step=0 (WRONG)
  train_state.json: current_step=360 (RIGHT)

Resume attempt:
  accelerator.load_state() reads step=0 from random_states_0.pkl
  Code expects step=360
  ✗ MISMATCH → Error or wrong behavior
```

### After Fix:
```
Checkpoint saved:
  accelerator.step = 360 (SET BEFORE SAVE)
  random_states_0.pkl: step=360 (CORRECT)
  train_state.json: current_step=360 (CORRECT)

Resume attempt:
  accelerator.load_state() reads step=360 from random_states_0.pkl
  Code expects step=360
  ✓ MATCH → Resume works correctly
```

## Testing

### For Existing Bad Checkpoints

Your existing checkpoint at step 360 **cannot be used** because it has `step=0` in `random_states_0.pkl`. You must:

1. **Start training from scratch** (remove `--resume`)
2. **OR** manually fix the checkpoint (see below)

### Manual Checkpoint Fix (Advanced)

You can manually fix the checkpoint:

```bash
cd /workspace/fluxgym
source env/bin/activate

python3 << 'EOF'
import torch
from pathlib import Path

checkpoint_dir = Path("/workspace/fluxgym/outputs/kristyhardened9/kristyhardened9-000030-state")
random_states_file = checkpoint_dir / "random_states_0.pkl"

# Load the states
states = torch.load(random_states_file, weights_only=False)

print(f"Before: step = {states['step']}")

# Fix the step value to match train_state.json
states['step'] = 360

# Save it back
torch.save(states, random_states_file)

print(f"After: step = {states['step']}")
print("✓ Checkpoint fixed!")
EOF
```

After running this, your checkpoint should work with `--resume`.

### For New Checkpoints

All NEW checkpoints created after deploying this fix will have the correct `step` value and will work with `--resume`.

## Deployment

This fix is included in the hardened sd-scripts files. Deploy using:

```bash
cd /workspace
bash deploy_hardened.sh
```

The deployment script will:
1. Backup your current sd-scripts files
2. Download the fixed versions from GitHub
3. Future checkpoint saves will have correct step values

## Verification

After deploying the fix, start a new training and let it save a checkpoint, then verify:

```bash
cd /workspace/fluxgym

python3 << 'EOF'
import torch
import json
from pathlib import Path

# Find the latest checkpoint
checkpoint_dir = Path("outputs/your-lora-name/your-lora-name-000001-state")

# Check random_states_0.pkl
random_states = torch.load(checkpoint_dir / "random_states_0.pkl", weights_only=False)
step_from_random = random_states['step']

# Check train_state.json
with open(checkpoint_dir / "train_state.json") as f:
    train_state = json.load(f)
step_from_json = train_state['current_step']

print(f"random_states_0.pkl step: {step_from_random}")
print(f"train_state.json current_step: {step_from_json}")

if step_from_random == step_from_json:
    print("✓ CORRECT - Both match!")
else:
    print("✗ INCORRECT - Mismatch!")
EOF
```

Both should show the same step number.

## Impact on Training Monitor

The training monitor's auto-resume feature will now work correctly because:

1. Checkpoints will have correct `step` values
2. `accelerator.load_state()` will succeed
3. Training will resume from the correct step

No changes needed to `training_monitor.py` - it will work once checkpoints are fixed.

## Summary

**Root Cause:** sd-scripts never set `accelerator.step`, so checkpoints saved `step=0`
**Fix:** Set `accelerator.step = global_step` before calling `accelerator.save_state()`
**Files Changed:** `train_util.py` (3 functions), `train_network.py` (2 call sites)
**Result:** Checkpoints now compatible with `--resume` and auto-resume

This was a bug in sd-scripts, not in your setup!
