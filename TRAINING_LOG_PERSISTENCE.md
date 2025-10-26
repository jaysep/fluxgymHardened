# Training Log Persistence Guide

## Overview

FluxGym now saves all training logs to a file, so you can view training progress even after page refresh or SSH reconnection.

---

## The Problem (Before)

**Previous behavior:**
- Training logs were only streamed to the UI during the initial session
- Refresh page → lose all training progress visibility
- SSH disconnect → reconnect shows empty log terminal
- No way to see what epoch you're on without checking filesystem

This was problematic for cloud environments where:
- SSH connections drop frequently
- Browser tabs get accidentally closed
- Long training runs span multiple sessions

---

## The Solution (Now)

**New behavior:**
- ✅ Training logs written to `outputs/<lora-name>/training.log`
- ✅ Logs streamed to UI in real-time AND saved to file simultaneously
- ✅ New "Training Log (Persisted)" accordion shows saved logs
- ✅ Auto-refreshes every 5 seconds
- ✅ Shows last 100 lines of training output
- ✅ Survives page refresh/reconnection

---

## How It Works

### 1. Log Writing (During Training)

When you click "Start training", FluxGym:

```python
# In start_training() function
training_log_file = f"outputs/{output_name}/training.log"

with open(training_log_file, 'w', encoding='utf-8') as log_file:
    for line in runner.run_command([command], cwd=cwd):
        log_file.write(line + '\n')  # Write to file
        log_file.flush()              # Immediate write
        yield line                    # Stream to UI
```

**Both happen simultaneously:**
- Logs stream to the "Train log" terminal (real-time)
- Logs write to `outputs/<lora-name>/training.log` (persisted)

### 2. Log Reading (After Refresh)

When you refresh the page or reconnect:

```python
def get_training_log(lora_name, num_lines=100):
    """Get training log tail for display"""
    training_log_file = f"outputs/{output_name}/training.log"

    with open(training_log_file, 'r') as f:
        lines = f.readlines()
        # Return last 100 lines
        tail = lines[-num_lines:]
        return ''.join(tail)
```

**UI automatically:**
- Reads the saved log file
- Shows last 100 lines
- Refreshes every 5 seconds

---

## Using the Feature

### During Training

**You'll see TWO log displays:**

1. **"Train log" (Terminal)**
   - Real-time streaming output
   - Shows all output as it happens
   - Uses LogsView component
   - **Loses connection on page refresh**

2. **"📜 Training Log (Persisted)"** (Accordion)
   - File-based display
   - Shows last 100 lines from saved file
   - Auto-refreshes every 5 seconds
   - **Survives page refresh/reconnection**

### After Reconnection

1. Open FluxGym UI
2. Expand "📜 Training Log (Persisted)" accordion
3. Click "Refresh Training Log" (or wait 5 seconds for auto-refresh)
4. See the last 100 lines of training output!

**You can see:**
- Current epoch/step
- Loss values
- Sample generation messages
- Checkpoint saving notifications
- Any errors or warnings

---

## File Structure

```
outputs/
└── my-lora/
    ├── training.log          ← NEW! Complete training logs
    ├── monitor.log           ← Monitor logs (if enabled)
    ├── ui_state.json         ← UI state (for restore)
    ├── my-lora.safetensors   ← Trained model
    ├── my-lora-4-state/      ← Checkpoints
    └── sample/               ← Sample images
```

---

## UI Components

### Accordion: "📜 Training Log (Persisted)"

Located below "Monitor Status & Logs" accordion.

**Components:**
- **Info text:** Explains the feature
- **Textbox:** Shows last 100 lines (20 line display)
- **Copy button:** Copy logs to clipboard
- **Refresh button:** Manual refresh
- **Auto-refresh:** Every 5 seconds

**Status:**
- Always visible
- Closed by default (to save space)
- Shows empty if no training log exists yet

---

## Scenarios

### Scenario 1: Training in Progress

```
You: Start training
     Wait 5 minutes
     Browser freezes
     Force-close browser tab

You: Reopen browser
     Navigate to FluxGym
     Expand "📜 Training Log (Persisted)"

FluxGym: Shows last 100 lines:
         "steps: 45%|████▌     | 9/20 [03:15<03:45, 20.5s/it]"
         "loss=0.0234"
         ...
```

**You know exactly where training is!** ✅

### Scenario 2: SSH Disconnect on Cloud

```
Cloud: SSH connection lost...

You: Reconnect to cloud instance
     Open FluxGym UI (still running from nohup)
     Check "🔄 Active Training Sessions" → 🟢 Running
     Expand "📜 Training Log (Persisted)"

FluxGym: Shows latest progress:
         "Epoch 12/16"
         "Saving checkpoint: outputs/my-lora/my-lora-12-state"
         ...
```

**Complete visibility into running training!** ✅

### Scenario 3: Debugging Stuck Training

```
You: Training seems stuck
     Check "📜 Training Log (Persisted)"

FluxGym: Last lines show:
         "steps: 25%|██▌       | 5/20 [00:45<02:15, 9.05s/it]"
         (timestamp: 30 minutes ago)

You: Ah, it's been stuck at step 5 for 30 minutes
     Check monitor.log to see if auto-kill triggered
```

**Easy debugging!** ✅

---

## Comparison with Other Log Sources

| Log Source | What It Shows | When Available | Survives Refresh |
|------------|---------------|----------------|------------------|
| **Train log (Terminal)** | Real-time stream | During active session only | ❌ No |
| **📜 Training Log** | Last 100 lines from file | Always (if training started) | ✅ Yes |
| **monitor.log** | Monitor status/actions | If monitoring enabled | ✅ Yes |
| **ui_state.json** | UI configuration | Always (after training starts) | ✅ Yes |

---

## Manual Log Access

### View Full Log

```bash
# View entire log
cat outputs/my-lora/training.log

# Tail in real-time
tail -f outputs/my-lora/training.log

# Last 100 lines
tail -n 100 outputs/my-lora/training.log

# Search for errors
grep -i error outputs/my-lora/training.log

# Check current epoch
grep "Epoch" outputs/my-lora/training.log | tail -n 1
```

### Log Size Management

```bash
# Check log size
ls -lh outputs/my-lora/training.log

# Compress old logs
gzip outputs/old-lora/training.log

# Delete old logs
find outputs -name "training.log" -mtime +30 -delete
```

---

## Technical Details

### Log Writing Performance

**No performance impact:**
- `flush()` called after each line to ensure immediate write
- File I/O is negligible compared to training computation
- Logs written in same thread as UI streaming (no additional overhead)

### Log File Size

**Typical sizes:**
- 16 epochs training: ~5-10 MB
- 100 epochs training: ~30-50 MB
- Depends on verbosity and sample generation frequency

**Safe to keep:**
- Log files are text and compress well
- Can be safely deleted after training completes
- Only the latest `num_lines` are shown in UI (default: 100)

### Auto-Refresh Behavior

```python
training_log_display = gr.Textbox(
    get_training_log,
    inputs=[lora_name],
    every=5  # Refresh every 5 seconds
)
```

**Characteristics:**
- Polls every 5 seconds
- Only reads last 100 lines (efficient)
- Stops when component not visible
- Minimal network traffic (text only)

---

## Troubleshooting

### Log Not Showing

**Problem:** "Training Log (Persisted)" is empty

**Solutions:**
```bash
# 1. Check if log file exists
ls outputs/my-lora/training.log

# 2. Check file permissions
chmod 644 outputs/my-lora/training.log

# 3. Verify not empty
wc -l outputs/my-lora/training.log

# 4. Manually refresh in UI
# Click "Refresh Training Log" button
```

### Log Stops Updating

**Problem:** Log shown but not updating during training

**Causes:**
1. Training actually stopped (check `ps aux | grep flux_train`)
2. Auto-refresh disabled (check accordion is open)
3. Browser tab suspended (reactivate tab)

**Solutions:**
```bash
# Check if training running
ps aux | grep flux_train_network

# Check if log file growing
watch -n 5 'ls -lh outputs/my-lora/training.log'

# Manual refresh
# Click "Refresh Training Log" button in UI
```

### Log Shows Old Data

**Problem:** Showing logs from previous training run

**Cause:** Log file is overwritten when new training starts, but you might be viewing before overwrite

**Solution:**
- Start new training (automatically overwrites)
- Or manually delete: `rm outputs/my-lora/training.log`

---

## Best Practices

### 1. Always Check After Reconnection

```
SSH reconnect → Open FluxGym → Check three things:
1. "🔄 Active Training Sessions" → Is training running?
2. "📜 Training Log (Persisted)" → What's the current progress?
3. "Monitor Status & Logs" → Is monitoring active?
```

### 2. Use with Monitor

```
Enable both:
✅ Enable Checkpointing
✅ Enable Auto-Monitoring

Benefits:
- Training log shows progress
- Monitor log shows stuck detection
- Checkpoints allow resume
- Complete visibility!
```

### 3. Archive Important Logs

```bash
# Before deleting outputs
mkdir -p ~/training-logs/
cp outputs/my-important-lora/training.log ~/training-logs/my-important-lora-$(date +%Y%m%d).log

# Or compress all logs
tar -czf training-logs-backup-$(date +%Y%m%d).tar.gz outputs/*/training.log
```

### 4. Check Logs for Errors

```bash
# Before downloading model, verify training completed
tail -n 20 outputs/my-lora/training.log

# Look for:
# - "Training finished"
# - Final loss values
# - No error messages
```

---

## Integration with Other Features

### With State Persistence

**Combined power:**
- UI state shows configuration
- Training log shows progress
- Together = complete picture

```
Refresh page →
1. Active Sessions: "🟢 my-lora - Running"
2. UI State: Shows all settings (epochs, LR, etc.)
3. Training Log: "Epoch 8/16, step 45/100"
```

### With Checkpointing

**Recovery workflow:**
```
Training stuck →
1. Check training log: Last activity was 30min ago
2. Check monitor log: Auto-kill triggered at step 123
3. Find checkpoint: my-lora-12-state
4. Resume from checkpoint
5. New training.log overwrites old one
```

### With Monitoring

**Dual logging:**
- `training.log` = Training script output
- `monitor.log` = Monitor script output

**Use together:**
```bash
# Terminal 1: Watch training progress
tail -f outputs/my-lora/training.log

# Terminal 2: Watch monitoring
tail -f outputs/my-lora/monitor.log
```

---

## Future Enhancements

Planned improvements:

- [ ] Configurable number of lines to show
- [ ] Search/filter within logs
- [ ] Syntax highlighting for errors/warnings
- [ ] Download log file button
- [ ] Log rotation for very long training
- [ ] Parse and display epoch/step progress bar
- [ ] Real-time log streaming from file (WebSocket)

---

## Summary

Training log persistence makes FluxGym:

✅ **Resilient** - Survives disconnects and refreshes
✅ **Transparent** - Always see training progress
✅ **Cloud-Ready** - Perfect for cloud GPU services
✅ **Debuggable** - Easy to diagnose issues
✅ **User-Friendly** - No manual log tailing needed

**You never lose visibility of your training progress!** 🚀

---

## Quick Reference

**Log Location:** `outputs/<lora-name>/training.log`

**View in UI:** Expand "📜 Training Log (Persisted)" accordion

**Auto-Refresh:** Every 5 seconds (last 100 lines)

**Manual Commands:**
```bash
# View log
cat outputs/my-lora/training.log

# Tail real-time
tail -f outputs/my-lora/training.log

# Check current epoch
grep "Epoch" outputs/my-lora/training.log | tail -1

# Archive log
cp outputs/my-lora/training.log ~/backups/
```

**Benefits:**
- Never lose training progress visibility
- Debug issues after the fact
- Monitor from anywhere (just refresh)
- Perfect for cloud environments
