# Checkpoint Format Investigation

## What We Found

Your checkpoint at `/workspace/fluxgym/outputs/kristyhardened9/kristyhardened9-000030-state` contains:

```
model.safetensors       158 MB
optimizer.bin            81 MB
random_states_0.pkl      14 KB
scheduler.bin             1 KB
train_state.json         42 bytes
```

The `train_state.json` contains:
```json
{"current_epoch": 30, "current_step": 360}
```

## The Problem

When you try to resume with `--resume /path/to/checkpoint`, you get:
```
KeyError: 'step'
  File "accelerate/accelerator.py", line 3156, in load_state
    self.step = override_attributes["step"]
```

This means `accelerate.load_state()` is trying to access `override_attributes["step"]` but that key doesn't exist.

## Why This Happens

There are two possible checkpoint formats:

### Format 1: With `custom_checkpoint_0.pkl` (Expected by newer accelerate)
```
checkpoint-dir/
├── custom_checkpoint_0.pkl  ← Contains override_attributes with "step"
├── optimizer.bin
├── random_states_0.pkl
├── scheduler.bin
└── model.safetensors (or pytorch_model.bin)
```

### Format 2: With `train_state.json` (What you have)
```
checkpoint-dir/
├── train_state.json         ← Contains {"current_step": 360, "current_epoch": 30}
├── optimizer.bin
├── random_states_0.pkl
├── scheduler.bin
└── model.safetensors
```

## Investigation Needed

Run this script on the pod to understand what's happening:

```bash
bash diagnose_checkpoint_on_pod.sh
```

This will tell us:
1. What version of accelerate is installed
2. What `accelerate.save_state()` creates on that system
3. Where the code expects to find "step" information

## Possible Causes

### 1. Version Mismatch
- Checkpoint was created with old accelerate version
- Trying to load with new accelerate version
- Format changed between versions

### 2. Incomplete Save
- `custom_checkpoint_0.pkl` should have been created but wasn't
- Save was interrupted
- Bug in accelerate or sd-scripts

### 3. Different Code Path
- Maybe flux_train uses a different save mechanism
- Maybe the hooks interfere with normal save_state

## What to Check on the Pod

```python
# Check if this works - create a new checkpoint
cd /workspace/fluxgym
source env/bin/activate

python3 << 'EOF'
from accelerate import Accelerator
import torch
from pathlib import Path

acc = Accelerator()
model = torch.nn.Linear(10, 10)
opt = torch.optim.Adam(model.parameters())
sched = torch.optim.lr_scheduler.StepLR(opt, step_size=1)

model, opt, sched = acc.prepare(model, opt, sched)
acc.step = 360  # Same as your checkpoint

# Save test state
test_dir = Path("/workspace/test_checkpoint")
test_dir.mkdir(exist_ok=True)
acc.save_state(str(test_dir))

print("Test checkpoint created at /workspace/test_checkpoint")
print("Files:")
for f in sorted(test_dir.iterdir()):
    print(f"  {f.name}")

# Check for custom_checkpoint
if (test_dir / "custom_checkpoint_0.pkl").exists():
    import pickle
    with open(test_dir / "custom_checkpoint_0.pkl", 'rb') as f:
        data = pickle.load(f)
    print(f"\ncustom_checkpoint_0.pkl keys: {list(data.keys())}")
    if 'step' in data:
        print(f"  step = {data['step']}")
else:
    print("\nNO custom_checkpoint_0.pkl created!")

# Now try to load it
acc2 = Accelerator()
model2 = torch.nn.Linear(10, 10)
opt2 = torch.optim.Adam(model2.parameters())
sched2 = torch.optim.lr_scheduler.StepLR(opt2, step_size=1)
model2, opt2, sched2 = acc2.prepare(model2, opt2, sched2)

try:
    acc2.load_state(str(test_dir))
    print(f"\n✓ Load succeeded! acc2.step = {acc2.step}")
except Exception as e:
    print(f"\n✗ Load failed: {e}")
    import traceback
    traceback.print_exc()
EOF
```

## Temporary Workaround

Until we understand the issue, you have two options:

### Option 1: Don't use --resume
Remove the `--resume` line from train.sh and start from scratch.

### Option 2: Check other checkpoints
```bash
ls -la /workspace/fluxgym/outputs/kristyhardened9/ | grep state
```

Try an earlier checkpoint that might have the correct format.

## Questions to Answer

1. **What accelerate version is on the pod?**
   ```bash
   pip show accelerate
   ```

2. **What does accelerate.save_state() create on that pod?**
   Run the Python script above

3. **Are there any other checkpoints with different format?**
   Check other state directories

4. **Can we manually create custom_checkpoint_0.pkl?**
   If we know the format, we might be able to create it from train_state.json

## Next Steps

Once we run the diagnostic script, we'll know:
- If this is a version issue
- If we can create compatible checkpoints going forward
- If we can fix existing checkpoints
- Or if we need to change how resume works
