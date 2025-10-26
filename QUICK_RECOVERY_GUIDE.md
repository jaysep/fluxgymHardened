# Quick Recovery Guide - Training Stuck

## If Training Gets Stuck (GPU at 0%)

### Option 1: Quick Manual Fix (30 seconds)

```bash
# 1. Kill stuck processes
pkill -9 -f "flux_train_network"

# 2. Find checkpoint
python find_checkpoint.py outputs/<YOUR-LORA-NAME>

# 3. Copy the checkpoint path shown, e.g.:
#    outputs/my-lora/my-lora-8-state

# 4. In FluxGym UI:
#    - Paste path into "Resume from Checkpoint" field
#    - Click "Start training"
```

### Option 2: Automatic Monitoring (Recommended)

**Before starting training**, run this in a separate terminal:

```bash
python training_monitor.py --output-dir outputs/<YOUR-LORA-NAME>
```

The monitor will:
- ✅ Watch GPU usage every 30 seconds
- ✅ Detect if training is stuck (GPU < 5% for 5+ minutes)
- ✅ Automatically kill stuck processes
- ✅ Show you the checkpoint to resume from

---

## Enable Checkpointing (Before Training)

In FluxGym UI:
1. ✅ Check **"Enable Checkpointing (Save training state for resume)"**
2. Start training

This saves your progress every 4 epochs so you can resume if training gets stuck.

---

## Common Commands

```bash
# Find latest checkpoint
python find_checkpoint.py outputs/my-lora

# List all checkpoints
python find_checkpoint.py outputs/my-lora --list

# Monitor training (in separate terminal)
python training_monitor.py --output-dir outputs/my-lora

# Kill all training processes manually
pkill -9 -f "flux_train_network"
```

---

## Full Documentation

See [CHECKPOINT_RESUME_GUIDE.md](CHECKPOINT_RESUME_GUIDE.md) for complete documentation.
