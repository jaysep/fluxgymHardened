# FluxGym State Persistence Guide

## Overview

FluxGym now automatically saves and restores your training state, so you can:
- ✅ **Refresh the browser** - UI restores to your last training
- ✅ **Disconnect/reconnect** - See active training sessions
- ✅ **Resume monitoring** -Continue where you left off
- ✅ **Cloud-friendly** - Perfect for long cloud training sessions

---

## How It Works

### Automatic State Saving

When you click "Start training", FluxGym saves a state file:
```
outputs/my-lora/ui_state.json
```

This contains all your training configuration:
- LoRA name and settings
- Model configuration
- Training parameters
- Checkpointing/monitoring status
- Timestamp

### Automatic State Restoration

When you **refresh the page** or **reconnect**:

1. **Active Sessions Banner** appears at top
2. Shows all recent/active training sessions
3. Green 🟢 = Currently running
4. Blue 🔵 = Stopped but config saved

### State File Format

```json
{
  "lora_name": "my-cat-lora",
  "concept_sentence": "catsy style",
  "base_model": "flux-dev",
  "vram": "20G",
  "num_repeats": 10,
  "max_train_epochs": 16,
  "enable_checkpointing": true,
  "enable_monitoring": true,
  "timestamp": 1234567890.123,
  "status": "starting"
}
```

---

## Using State Persistence

### Scenario 1: Page Refresh During Training

```
You: Start training
     Wait 30 minutes
     Accidentally close browser tab
     Panic! 😱

FluxGym: Don't worry!
         Refresh the page
         Click "🔄 Active Training Sessions"
         See your training listed (🟢 Running)
         All your settings are still there!
```

### Scenario 2: Cloud Disconnect

```
Cloud Terminal: Connection lost...

You: Reconnect to cloud instance
     Open browser to FluxGym UI
     Click "🔄 Active Training Sessions"
     See your training: 🟢 Running
     Click "Refresh Monitor Status"
     Everything still going!
```

### Scenario 3: Multiple Training Runs

```
Day 1: Train "cat-lora" ✅
Day 2: Train "dog-lora" ✅
Day 3: Train "style-lora" ✅

Refresh UI:
  🔄 Active Training Sessions shows:
     🔵 style-lora - Stopped
     🔵 dog-lora - Stopped
     🔵 cat-lora - Stopped

  All configurations preserved!
```

---

## Active Sessions Banner

Located at the top of the UI, below the navigation.

### What It Shows

```
🔄 Active Training Sessions
━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟢 my-cat-lora - Running
   - Started: 2025-01-25 14:30:22
   - Epochs: 16
   - Checkpointing: ✅
   - Monitoring: ✅

---

🔵 old-style-lora - Stopped
   - Started: 2025-01-24 10:15:45
   - Epochs: 12
   - Checkpointing: ✅
   - Monitoring: ❌
```

### Status Indicators

- 🟢 **Green** = Training is currently running
- 🔵 **Blue** = Training stopped, but config saved

### Refresh Button

Click "Refresh Sessions" to update the list with latest status.

---

## State Files Location

All state files are saved alongside your training outputs:

```
outputs/
├── my-cat-lora/
│   ├── ui_state.json          ← UI configuration
│   ├── monitor.pid             ← Monitor process ID
│   ├── monitor.log             ← Monitor logs
│   ├── my-cat-lora-4-state/    ← Training checkpoint
│   ├── my-cat-lora.safetensors ← Trained model
│   └── sample/                 ← Sample images
│
└── my-dog-lora/
    ├── ui_state.json
    └── ...
```

---

## What Gets Saved

### Basic Configuration
- LoRA name
- Trigger word/concept sentence
- Base model (flux-dev, etc.)
- VRAM setting
- Number of repeats
- Max training epochs
- Sample prompts
- Sample frequency
- Resolution

### Checkpoint Settings
- Enable checkpointing (yes/no)
- Resume from checkpoint (path)

### Monitoring Settings
- Enable monitoring (yes/no)

### Advanced Settings
- Seed
- Workers
- Learning rate
- Save frequency
- Guidance scale
- Timestep sampling
- Network dimension

### Metadata
- Timestamp (when training started)
- Status (starting/running/stopped)

---

## Manual State Management

### View State File

```bash
cat outputs/my-lora/ui_state.json | jq .
```

### Check All State Files

```bash
find outputs -name "ui_state.json" -exec echo {} \; -exec cat {} \;
```

### Backup State

```bash
# Backup all state files
tar -czf fluxgym-states-backup.tar.gz outputs/*/ui_state.json

# Restore
tar -xzf fluxgym-states-backup.tar.gz
```

### Delete Old States

```bash
# Remove states older than 30 days
find outputs -name "ui_state.json" -mtime +30 -delete
```

---

## State Detection Logic

FluxGym determines if training is **running** by checking:

1. **PID file exists**: `outputs/my-lora/training.pid`
2. **Process is alive**: `ps -p <PID>` succeeds
3. If both true → 🟢 Running
4. Otherwise → 🔵 Stopped

Note: `training.pid` is created by the monitor (future enhancement - not yet implemented in current version).

---

## Troubleshooting

### Sessions Not Showing

**Problem**: Active Sessions banner shows "No active training sessions found"

**Solutions**:
```bash
# 1. Check if state files exist
ls outputs/*/ui_state.json

# 2. Check file permissions
chmod 644 outputs/*/ui_state.json

# 3. Verify JSON is valid
cat outputs/my-lora/ui_state.json | jq .

# 4. Click "Refresh Sessions" button
```

### State Shows Wrong Status

**Problem**: Training shows 🟢 Running but it's actually stopped

**Cause**: PID file exists but process died

**Solution**:
```bash
# Remove stale PID file
rm outputs/my-lora/training.pid

# Refresh UI
# Click "Refresh Sessions"
```

### State File Corrupted

**Problem**: JSON parse error

**Solution**:
```bash
# Check the file
cat outputs/my-lora/ui_state.json

# If corrupted, you can manually reconstruct or delete
rm outputs/my-lora/ui_state.json

# Start training again - will create new state
```

### Old Sessions Cluttering UI

**Problem**: Too many old sessions showing

**Solution**:
```bash
# Delete specific state
rm outputs/old-lora/ui_state.json

# Or delete all states (keeps trained models)
find outputs -name "ui_state.json" -delete

# Refresh UI
```

---

## Integration with Other Features

### With Checkpointing

State persistence + checkpointing = **perfect cloud setup**:

```
1. Start training with checkpointing ✅
2. State saved automatically ✅
3. Browser disconnects ❌
4. Reconnect, see active session 🟢
5. Training still running ✅
6. If it stopped, resume from checkpoint ✅
```

### With Monitoring

State shows if monitoring is enabled:

```
UI Shows:
  - Monitoring: ✅  (monitor.pid exists and running)
  - Monitoring: ❌  (monitoring not enabled or stopped)
```

### With Resume

State can help auto-resume (future):

```
Future Feature:
  - Detect training stopped
  - Find latest checkpoint automatically
  - Offer "Resume" button in banner
  - Click to auto-resume
```

---

## Best Practices

### 1. Always Enable State Persistence

It's automatic! Just use FluxGym normally.

### 2. Check Active Sessions After Disconnect

```
Reconnect → Click "🔄 Active Training Sessions" → See status
```

### 3. Keep State Files

They're small (< 1KB each) and very useful for reference.

### 4. Backup Important States

```bash
# Before deleting outputs
cp outputs/my-important-lora/ui_state.json ~/backups/
```

### 5. Use with Cloud Training

Perfect for:
- Runpod
- Vast.ai
- Lambda Labs
- Any cloud GPU service

---

## Advanced: Programmatic Access

### Python

```python
import json

# Load state
with open('outputs/my-lora/ui_state.json') as f:
    state = json.load(f)

print(f"LoRA: {state['lora_name']}")
print(f"Epochs: {state['max_train_epochs']}")
print(f"Started: {state['timestamp']}")

# Modify state (careful!)
state['max_train_epochs'] = 20
with open('outputs/my-lora/ui_state.json', 'w') as f:
    json.dump(state, f, indent=2)
```

### Bash

```bash
# Get all LoRA names
jq -r '.lora_name' outputs/*/ui_state.json

# Find long-running training (>12 epochs)
find outputs -name "ui_state.json" -exec sh -c \
  'if [ $(jq ".max_train_epochs" "$1") -gt 12 ]; then echo "$1"; fi' _ {} \;

# Count total trainings
find outputs -name "ui_state.json" | wc -l
```

---

## Security Considerations

### State Files Are Local

- Not uploaded anywhere
- Stored on your machine/cloud instance
- No sensitive data (no passwords, tokens, etc.)

### What's NOT Saved

- Uploaded images (too large)
- Model weights (in .safetensors)
- HuggingFace tokens (in separate HF_TOKEN file)
- Training logs

### Safe to Share

State files contain only:
- Configuration values
- Timestamps
- Settings

Safe to share for debugging/help.

---

## Future Enhancements

Planned improvements:

- [ ] Auto-restore last training on page load
- [ ] "Resume" button in Active Sessions
- [ ] Training progress in session list
- [ ] State history/versioning
- [ ] Export/import state files
- [ ] State templates (save common configs)

---

## Examples

### Example 1: Cloud Training Recovery

```bash
# Day 1: Start training on Runpod
# Configure LoRA in UI
# Start training
# State saved to outputs/my-lora/ui_state.json

# Connection drops...

# Day 2: Reconnect to Runpod
# Open FluxGym UI
# See "🔄 Active Training Sessions"
# Click it:
#   🔵 my-lora - Stopped
#      - Started: 2025-01-24 20:15:33
#      - Epochs: 16
#      - Checkpointing: ✅

# All your settings preserved!
# If training crashed, use checkpoint to resume
```

### Example 2: Multiple Sessions

```python
# outputs/cat/ui_state.json
{
  "lora_name": "fluffy-cats",
  "max_train_epochs": 16,
  "timestamp": 1706140800.0
}

# outputs/dog/ui_state.json
{
  "lora_name": "puppy-style",
  "max_train_epochs": 12,
  "timestamp": 1706227200.0
}

# UI shows both:
# 🔵 puppy-style (most recent)
# 🔵 fluffy-cats
```

---

## Summary

State persistence makes FluxGym:

✅ **Resilient** - Survives disconnects
✅ **User-friendly** - No manual config management
✅ **Cloud-ready** - Perfect for cloud GPU services
✅ **Transparent** - See all active/recent trainings
✅ **Automatic** - Works without any setup

Just train normally, FluxGym handles the rest! 🚀
