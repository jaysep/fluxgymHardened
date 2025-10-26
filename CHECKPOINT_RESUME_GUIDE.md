# FluxGym Checkpoint & Resume Guide

This guide explains how to use the checkpoint and resume functionality in FluxGym, and how to recover from stuck training sessions.

## Table of Contents
1. [Overview](#overview)
2. [Enabling Checkpoints](#enabling-checkpoints)
3. [Resuming Training](#resuming-training)
4. [Training Monitor](#training-monitor)
5. [Manual Recovery](#manual-recovery)
6. [Troubleshooting](#troubleshooting)

---

## Overview

FluxGym now supports:
- **Checkpointing**: Save training state at each epoch to enable resume
- **Resume**: Continue training from a saved checkpoint
- **Stuck Detection**: Automatically detect when GPU usage drops to zero
- **Auto-Recovery**: Optionally kill stuck processes and resume training

### What Gets Saved in Checkpoints?

When you enable checkpointing, FluxGym saves:
- Model weights at that epoch
- Optimizer state (Adam/AdaFactor states)
- Learning rate scheduler state
- Training progress (epoch/step counters)
- Random number generator states

This allows you to resume training exactly where it left off.

---

## Enabling Checkpoints

### Method 1: Using FluxGym Web UI

1. In the FluxGym UI, scroll to **Step 1. LoRA Info**
2. Check the box: **"Enable Checkpointing (Save training state for resume)"**
3. Start training as normal

Checkpoints will be saved to `outputs/<lora-name>/<lora-name>-state/` after each epoch.

### Method 2: Manual Script Editing

If you're editing the training script manually, add this flag:

```bash
--save_state \
```

This will create checkpoint directories like:
- `outputs/my-lora/my-lora-state` (final state)
- `outputs/my-lora/my-lora-4-state` (epoch 4 state)
- `outputs/my-lora/my-lora-8-state` (epoch 8 state)

---

## Resuming Training

### Method 1: Using FluxGym Web UI

1. Find your latest checkpoint (see [Finding Checkpoints](#finding-checkpoints) below)
2. In the FluxGym UI, find the field: **"Resume from Checkpoint"**
3. Enter the path to the state folder, e.g., `outputs/my-lora/my-lora-8-state`
4. Start training

The training will continue from where it left off at epoch 8.

### Method 2: Manual Script Editing

Add the `--resume` flag to your training command:

```bash
--resume "outputs/my-lora/my-lora-8-state" \
```

### Finding Checkpoints

Use the helper script to find your checkpoints:

```bash
# List all checkpoints
python find_checkpoint.py outputs/my-lora --list

# Find latest state checkpoint (for resume)
python find_checkpoint.py outputs/my-lora --type state

# Find latest model checkpoint
python find_checkpoint.py outputs/my-lora --type model
```

Example output:
```
Latest state checkpoint: outputs/my-lora/my-lora-8-state

To resume training, add this to your training command:
  --resume outputs/my-lora/my-lora-8-state

Or in FluxGym UI, enter this in 'Resume from Checkpoint' field:
  outputs/my-lora/my-lora-8-state
```

---

## Training Monitor

The training monitor automatically detects when training gets stuck (GPU usage drops to 0%) and can optionally recover.

### Basic Usage (Alert Only)

Monitor training and get alerted when it's stuck:

```bash
python training_monitor.py --output-dir outputs/my-lora
```

This will:
- Check GPU usage every 30 seconds
- Alert you if GPU stays below 5% for 5 minutes (300 seconds)
- Kill all training processes when stuck
- Show you the latest checkpoint to resume from

### Advanced Usage (Auto-Recovery)

**Note**: Auto-recovery is experimental and requires manual script editing for now.

```bash
python training_monitor.py \
  --output-dir outputs/my-lora \
  --check-interval 30 \
  --stuck-threshold 300 \
  --gpu-threshold 5.0 \
  --auto-resume \
  --train-script outputs/my-lora/train.sh
```

Parameters:
- `--output-dir`: Where your LoRA outputs are saved
- `--check-interval`: How often to check GPU (seconds, default: 30)
- `--stuck-threshold`: How long GPU must be idle before considered stuck (seconds, default: 300)
- `--gpu-threshold`: GPU usage % below which is considered idle (default: 5.0)
- `--auto-resume`: Attempt to automatically resume (experimental)
- `--train-script`: Path to training script (required for auto-resume)

### Running Monitor in Background

To run the monitor in the background while training:

```bash
# Terminal 1: Start training normally through FluxGym UI

# Terminal 2: Start monitoring
python training_monitor.py --output-dir outputs/my-lora > monitor.log 2>&1 &
```

Check the logs:
```bash
tail -f monitor.log
tail -f training_monitor.log
```

---

## Manual Recovery

If training gets stuck and you're not using the monitor:

### Step 1: Kill Stuck Processes

```bash
# Find training processes
ps aux | grep python | grep flux_train

# Kill them (replace PID with actual process IDs)
kill -9 <PID>

# Or kill all Python processes (USE WITH CAUTION)
pkill -9 -f "flux_train_network"
```

### Step 2: Find Latest Checkpoint

```bash
python find_checkpoint.py outputs/my-lora --type state
```

### Step 3: Resume Training

In FluxGym UI:
1. Enter the checkpoint path in "Resume from Checkpoint" field
2. Click "Start training"

Or manually:
1. Edit `outputs/my-lora/train.sh`
2. Add `--resume "outputs/my-lora/my-lora-8-state" \` after the `sd-scripts/flux_train_network.py \` line
3. Run `bash outputs/my-lora/train.sh`

---

## Troubleshooting

### Issue: "No state checkpoints found"

**Solution**: You need to enable checkpointing before starting training. If you forgot, you'll need to start from scratch (but you can use the latest `.safetensors` model checkpoint as a base).

### Issue: Training resumes but starts from epoch 1

**Solution**: Make sure you're pointing to a `-state` directory, not a `.safetensors` file. State directories contain the full training state, while `.safetensors` files are just model weights.

### Issue: "Resume checkpoint not found"

**Solution**:
1. Check the path is correct: `python find_checkpoint.py outputs/my-lora --list`
2. Make sure the path is relative to the FluxGym root directory
3. Check for typos in the checkpoint path

### Issue: Monitor shows stuck but training is actually running

**Solution**: Adjust the thresholds:
```bash
python training_monitor.py \
  --output-dir outputs/my-lora \
  --stuck-threshold 600 \  # Wait 10 minutes instead of 5
  --gpu-threshold 10.0     # Consider stuck only below 10% instead of 5%
```

### Issue: Out of memory after resume

**Solution**: If you resume on a different GPU or system:
1. Check your VRAM setting matches your hardware
2. You may need to lower batch size or use more aggressive optimization
3. Clear cache: `rm -rf outputs/my-lora/cache`

### Issue: Different results after resume

**Solution**: This is normal due to:
- Different random states if training was interrupted mid-epoch
- Slight numerical differences in optimizer states
- To minimize: always resume from epoch boundaries (not step checkpoints)

---

## Best Practices

1. **Always enable checkpointing** for long training runs
2. **Monitor your training** especially for the first few hours
3. **Save checkpoints every 4 epochs** (default) for good granularity
4. **Keep the last 2-3 checkpoints** in case one is corrupted
5. **Test resume functionality** on a small dataset first
6. **Use the monitoring script** for overnight training runs

---

## Technical Details

### Checkpoint Structure

A typical checkpoint directory contains:
```
outputs/my-lora/my-lora-8-state/
├── optimizer.bin           # Optimizer state (AdamW, AdaFactor, etc.)
├── random_states_0.pkl     # PyTorch random states
├── scheduler.bin           # Learning rate scheduler state
├── scaler.pt              # Gradient scaler state (for mixed precision)
└── custom_checkpoint_0.pkl # Additional training state
```

### Resume Process

When you resume training:
1. FluxGym loads the checkpoint directory
2. Restores model weights, optimizer states, scheduler
3. Continues from the next epoch/step
4. Uses the same random seed states (for reproducibility)

### Checkpoint Compatibility

Checkpoints are compatible as long as:
- Same model architecture (same network_dim, same base model)
- Same optimizer type (can't switch from AdamW to AdaFactor mid-training)
- Same PyTorch version (major version)

---

## Examples

### Example 1: Normal Training with Checkpoints

```bash
# In FluxGym UI:
# 1. Check "Enable Checkpointing"
# 2. Start training
# 3. Training creates checkpoints every 4 epochs

# If training completes: Great!
# If training gets stuck: Use resume functionality
```

### Example 2: Resume After Stuck Training

```bash
# Find latest checkpoint
python find_checkpoint.py outputs/my-cat-lora

# Output shows: outputs/my-cat-lora/my-cat-lora-12-state

# In FluxGym UI:
# 1. Enter "outputs/my-cat-lora/my-cat-lora-12-state" in Resume field
# 2. Click Start training
# 3. Training continues from epoch 13
```

### Example 3: Monitored Training

```bash
# Terminal 1: Start FluxGym normally
python app.py

# In browser: Start training with checkpointing enabled

# Terminal 2: Start monitor
python training_monitor.py --output-dir outputs/my-cat-lora

# Monitor will alert if training gets stuck
# You can then manually resume using the UI
```

### Example 4: Unattended Training (Advanced)

```bash
# Setup: Create a wrapper script
cat > train_with_recovery.sh << 'EOF'
#!/bin/bash
OUTPUT_DIR="outputs/my-cat-lora"

# Function to start training
start_training() {
    cd /path/to/fluxgym
    source env/bin/activate
    bash $OUTPUT_DIR/train.sh
}

# Start initial training
start_training &
TRAIN_PID=$!

# Start monitor
python training_monitor.py \
    --output-dir $OUTPUT_DIR \
    --check-interval 60 \
    --stuck-threshold 600 &
MONITOR_PID=$!

# Wait for training to complete
wait $TRAIN_PID
kill $MONITOR_PID
EOF

chmod +x train_with_recovery.sh
./train_with_recovery.sh
```

---

## Support

If you encounter issues:
1. Check the logs: `training_monitor.log` and the terminal output
2. Verify checkpoints exist: `python find_checkpoint.py outputs/my-lora --list`
3. Test on a small dataset first
4. Report issues to the FluxGym repository

---

## Future Improvements

Planned features:
- Automatic resume integration (no manual script editing needed)
- Web UI for monitoring
- Checkpoint compression
- Cloud checkpoint storage (HuggingFace integration)
- Multiple recovery strategies
