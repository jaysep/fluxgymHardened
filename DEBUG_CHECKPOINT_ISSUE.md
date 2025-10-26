# Checkpoint Resume Error: KeyError 'step'

## The Error

```
File "/workspace/fluxgym/env/lib/python3.10/site-packages/accelerate/accelerator.py", line 3156, in load_state
    self.step = override_attributes["step"]
KeyError: 'step'
```

## Root Cause

The checkpoint state directory `/workspace/fluxgym/outputs/kristyhardened9/kristyhardened9-000030-state` is **missing critical metadata** that accelerate needs to resume training.

## What Should Be In a Valid State Directory

A complete checkpoint state directory should contain:

```
kristyhardened9-000030-state/
├── custom_checkpoint_0.pkl          # Training state metadata
├── optimizer.bin                     # Optimizer state
├── random_states_0.pkl              # Random number generator states
├── scheduler.bin                     # Learning rate scheduler state
└── pytorch_model.bin                # Model weights (or split into multiple files)
```

The `custom_checkpoint_0.pkl` file should contain:
- `step`: Current training step number
- `epoch`: Current epoch number
- Other training metadata

## Why This Happens

### Possible Causes:

1. **Training was killed mid-checkpoint save**
   - Checkpoint save was interrupted
   - State directory created but not fully written
   - Missing files or incomplete metadata

2. **Wrong checkpoint type**
   - Using a model checkpoint (`.safetensors`) instead of state checkpoint
   - Model checkpoints don't have training state

3. **Checkpoint format changed**
   - Older checkpoint from different version of sd-scripts
   - Incompatible state format

4. **Disk full during save**
   - Ran out of space while writing checkpoint
   - Partial files written

## How to Diagnose

Run this on the pod to check what's actually in the checkpoint:

```bash
cd /workspace/fluxgym/outputs/kristyhardened9

# List checkpoint directories
ls -la | grep state

# Check contents of the specific checkpoint
ls -la kristyhardened9-000030-state/

# Check file sizes
du -sh kristyhardened9-000030-state/*

# Try to inspect the metadata (if it exists)
python3 << 'EOF'
import pickle
import sys

checkpoint_path = "kristyhardened9-000030-state/custom_checkpoint_0.pkl"

try:
    with open(checkpoint_path, 'rb') as f:
        data = pickle.load(f)
    print("Checkpoint metadata:")
    print(data.keys())
    if 'step' in data:
        print(f"  step: {data['step']}")
    if 'epoch' in data:
        print(f"  epoch: {data['epoch']}")
except FileNotFoundError:
    print(f"ERROR: {checkpoint_path} not found")
except Exception as e:
    print(f"ERROR: {e}")
EOF
```

## Solutions

### Solution 1: Use a Different Checkpoint

If you have multiple checkpoints, try an earlier one:

```bash
# List all state checkpoints
ls -la /workspace/fluxgym/outputs/kristyhardened9/ | grep state

# Try resuming from a different checkpoint
# Edit train.sh to use:
--resume /workspace/fluxgym/outputs/kristyhardened9/kristyhardened9-000029-state
```

### Solution 2: Start Fresh (No Resume)

Remove the `--resume` flag and start from beginning:

```bash
# Remove the --resume line from train.sh
# Training will start from scratch
```

### Solution 3: Verify Checkpoint Integrity

Check if the checkpoint is complete:

```bash
cd /workspace/fluxgym/outputs/kristyhardened9/kristyhardened9-000030-state

# These files MUST exist for resume to work:
ls -lh custom_checkpoint_0.pkl
ls -lh optimizer.bin
ls -lh random_states_0.pkl
ls -lh scheduler.bin

# If any are missing, the checkpoint is incomplete
```

### Solution 4: Monitor Should Validate Checkpoint Before Using

**This is what we need to fix in training_monitor.py!**

The monitor should **validate** that a checkpoint is complete before trying to use it.

Add this to `CheckpointManager`:

```python
def validate_checkpoint(self, checkpoint_path: Path) -> bool:
    """Validate that checkpoint directory contains all required files"""
    required_files = [
        'custom_checkpoint_0.pkl',
        'optimizer.bin',
        'random_states_0.pkl',
        'scheduler.bin'
    ]

    for required_file in required_files:
        file_path = checkpoint_path / required_file
        if not file_path.exists():
            logger.warning(f"Checkpoint missing required file: {required_file}")
            return False

        # Check if file is not empty
        if file_path.stat().st_size == 0:
            logger.warning(f"Checkpoint file is empty: {required_file}")
            return False

    # Also check if step metadata exists
    try:
        import pickle
        metadata_path = checkpoint_path / 'custom_checkpoint_0.pkl'
        with open(metadata_path, 'rb') as f:
            data = pickle.load(f)

        if 'step' not in data:
            logger.warning("Checkpoint metadata missing 'step' key")
            return False

        logger.info(f"Checkpoint validated: step {data.get('step')}, epoch {data.get('epoch')}")
        return True

    except Exception as e:
        logger.warning(f"Failed to validate checkpoint metadata: {e}")
        return False
```

Then modify `find_latest_checkpoint()`:

```python
def find_latest_checkpoint(self) -> Optional[Path]:
    """Find the latest VALID checkpoint (state) directory"""
    if not self.output_dir.exists():
        logger.warning(f"Output directory does not exist: {self.output_dir}")
        return None

    state_dirs = []

    for item in self.output_dir.iterdir():
        if item.is_dir() and 'state' in item.name.lower():
            # Only include if it passes validation
            if self.validate_checkpoint(item):
                state_dirs.append(item)
            else:
                logger.warning(f"Skipping invalid checkpoint: {item}")

    if not state_dirs:
        logger.warning(f"No VALID checkpoint states found in {self.output_dir}")
        return None

    # Sort by modification time, most recent first
    state_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    latest = state_dirs[0]

    logger.info(f"Found latest valid checkpoint: {latest}")
    return latest
```

## Immediate Fix for Your Situation

**Check what checkpoints you have:**

```bash
cd /workspace/fluxgym/outputs/kristyhardened9
ls -la | grep state
```

**If you see multiple checkpoints:**
- Try the one before `000030-state` (maybe `000029-state`)
- Or try any other valid-looking checkpoint

**If this is the only checkpoint:**
- Remove the `--resume` line from train.sh
- Start training from scratch
- Make sure `--save_state` is enabled for future checkpoints

**To check if checkpoint is valid:**

```bash
ls -la kristyhardened9-000030-state/

# Should see files like:
# custom_checkpoint_0.pkl
# optimizer.bin
# random_states_0.pkl
# scheduler.bin
```

If files are missing or 0 bytes, the checkpoint is corrupted and cannot be used.

## Prevention

To prevent this in the future:

1. **Don't kill training during checkpoint save**
   - Wait for "Saving state..." message to complete
   - Checkpoint saves can take 30-60 seconds

2. **Check disk space**
   ```bash
   df -h /workspace
   ```
   Keep at least 10GB free for checkpoint saves

3. **Use multiple checkpoint saves**
   ```bash
   --save_every_n_epochs 1
   ```
   This gives you multiple recovery points

4. **Validate checkpoints after creation**
   Add validation to the monitor (as shown above)

## Next Steps

1. **Immediately**: Check what checkpoints you have and try a different one
2. **If all fail**: Remove `--resume` and start fresh
3. **For future**: We need to add checkpoint validation to training_monitor.py
