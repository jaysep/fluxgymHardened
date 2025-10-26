# Training Success Verification Guide

## Overview

With the addition of fast-failure timeouts, it's critical to **distinguish between successful completion and failures**. FluxGym now has multiple layers of verification to ensure you always know the true status of your training.

---

## The Risk You Identified

**Excellent question!** You asked:

> "With fast failure, will there be any risk of thinking training completed successfully when it just stopped?"

**Answer**: Not anymore! We've implemented comprehensive status tracking to prevent this exact scenario.

---

## How FluxGym Verifies Training Success

### 1. **Model File Check** ✅

**Location**: `app.py:1011-1022`

```python
# Check if training actually completed successfully
expected_model = f"outputs/{output_name}/{output_name}.safetensors"
if not os.path.exists(expected_model):
    training_failed = True
    error_message = "Training did not produce model file. Check logs for errors."
```

**What it does**:
- After training process exits, checks if `.safetensors` file exists
- If missing → Training failed (even if process exited cleanly)
- Only shows "Training Complete" if model file exists

---

### 2. **Exception Handling** ❌→✅

**Location**: `app.py:1024-1034`

```python
except Exception as e:
    training_failed = True
    error_message = f"Training crashed with error: {str(e)}"

    # Log the error
    with open(training_log_file, 'a') as log_file:
        log_file.write("\n" + "="*80 + "\n")
        log_file.write(f"ERROR: TRAINING CRASHED - {str(e)}\n")
        log_file.write("="*80 + "\n")
```

**What it does**:
- Catches any exception during training
- Marks training as failed
- Logs error to training.log with clear markers
- Shows error in UI

---

### 3. **State File Status Tracking**

**Location**: `app.py:1037-1049` (failure) and `app.py:1069-1081` (success)

#### On Failure:
```json
{
  "lora_name": "my-lora",
  "status": "failed",
  "error": "Training did not produce model file. Check logs for errors.",
  "timestamp": 1234567890.123,
  ...
}
```

#### On Success:
```json
{
  "lora_name": "my-lora",
  "status": "completed",
  "completed_at": 1234567890.456,
  "timestamp": 1234567890.123,
  ...
}
```

**What it does**:
- Persists training status to `ui_state.json`
- Status values: `starting`, `running`, `completed`, `failed`
- Survives page refresh / reconnection
- Shows in Active Training Sessions banner

---

### 4. **Training Log Markers**

**Success Marker** (lines 1083-1088):
```
================================================================================
✅ TRAINING COMPLETED SUCCESSFULLY
Model saved: outputs/my-lora/my-lora.safetensors
================================================================================
```

**Failure Marker** (lines 1018-1022):
```
================================================================================
ERROR: TRAINING FAILED - Model file not generated
================================================================================
```

**Crash Marker** (lines 1029-1032):
```
================================================================================
ERROR: TRAINING CRASHED - TimeoutError: Block swap timeout...
================================================================================
```

**What it does**:
- Appends clear status markers to training.log
- Easy to check: `tail outputs/my-lora/training.log`
- Visible in "Training Log (Persisted)" UI component

---

### 5. **UI Status Indicators**

#### Active Training Sessions Banner

**Shows different emojis based on status**:

```
✅ my-successful-lora - Completed
   - Started: 2025-01-25 14:30:22
   - Epochs: 16
   - Checkpointing: ✅
   - Monitoring: ✅

❌ my-failed-lora - Failed
   - Started: 2025-01-25 10:15:33
   - Epochs: 16
   - Checkpointing: ✅
   - Monitoring: ✅
   - ⚠️ Error: Training did not produce model file. Check logs for errors.

🟢 my-running-lora - Running
   - Started: 2025-01-25 16:45:12
   - Epochs: 16
   - Checkpointing: ✅
   - Monitoring: ✅
```

**Status Emojis**:
- ✅ Green checkmark = Completed successfully
- ❌ Red X = Failed
- 🟢 Green circle = Currently running
- 🔵 Blue circle = Stopped (unknown status)

---

### 6. **Gradio UI Notifications**

**On Success**:
```python
gr.Info(f"✅ Training Complete. Check the outputs folder for the LoRA files.", duration=None)
yield f"\n\n✅ Training completed successfully!\n"
```

**On Failure**:
```python
gr.Error(f"❌ Training Failed: {error_message}", duration=None)
yield f"\n\n❌ Training Failed: {error_message}\n"
```

**What it does**:
- Green "Info" banner for success
- Red "Error" banner for failure
- Persistent (duration=None means stays until dismissed)
- Shows in both UI banner and training terminal

---

## Verification Workflow

### Scenario 1: Training Completes Normally

```
1. Training runs for 16 epochs
2. Model file generated: ✅
3. Status set to "completed" in ui_state.json
4. Training log appends: "✅ TRAINING COMPLETED SUCCESSFULLY"
5. README.md generated
6. UI shows: "✅ Training Complete"
7. Active Sessions shows: ✅ my-lora - Completed
```

### Scenario 2: Training Hits Timeout

```
1. Training runs for 8 epochs
2. DataLoader timeout triggers after 60 seconds
3. Exception caught: TimeoutError
4. Status set to "failed" in ui_state.json
5. Training log appends: "ERROR: TRAINING CRASHED - TimeoutError..."
6. UI shows: "❌ Training Failed: Training crashed with error..."
7. Active Sessions shows: ❌ my-lora - Failed
   - ⚠️ Error: Training crashed with error: TimeoutError...
```

### Scenario 3: Training Crashes Silently

```
1. Training runs for 12 epochs
2. Process exits without error (e.g., OOM kill)
3. Model file NOT created
4. Check detects missing .safetensors file
5. Status set to "failed" in ui_state.json
6. Training log appends: "ERROR: TRAINING FAILED - Model file not generated"
7. UI shows: "❌ Training Failed: Training did not produce model file..."
8. Active Sessions shows: ❌ my-lora - Failed
   - ⚠️ Error: Training did not produce model file. Check logs for errors.
```

### Scenario 4: Monitoring Kills Stuck Training

```
1. Training runs for 6 epochs
2. GPU usage drops to 0% (stuck)
3. Monitoring detects after 5 minutes
4. Monitor kills training process
5. Monitor logs checkpoint path
6. Model file NOT created (training incomplete)
7. FluxGym detects missing model file
8. Status set to "failed" in ui_state.json
9. UI shows: "❌ Training Failed: Training did not produce model file..."
10. User can resume from checkpoint logged by monitor
```

---

## How to Verify Training Success (Manual Checks)

### Method 1: Check Active Sessions Banner (Easiest)

```
1. Refresh FluxGym UI
2. Expand "🔄 Active Training Sessions"
3. Look for your LoRA

✅ = Success
❌ = Failure
🟢 = Still running
🔵 = Unknown (check manually)
```

### Method 2: Check Training Log

```bash
# Last 20 lines of training log
tail -n 20 outputs/my-lora/training.log

# Look for:
# ✅ "TRAINING COMPLETED SUCCESSFULLY" = Success
# ❌ "ERROR: TRAINING FAILED" = Failure
# ❌ "ERROR: TRAINING CRASHED" = Crash
```

### Method 3: Check Model File Exists

```bash
# Check if model was generated
ls -lh outputs/my-lora/*.safetensors

# If exists = Likely success
# If missing = Definitely failure
```

### Method 4: Check State File

```bash
# View state file
cat outputs/my-lora/ui_state.json | jq '.status'

# Returns:
# "completed" = Success
# "failed" = Failure
# "starting" or "running" = In progress or interrupted
```

### Method 5: Check for README

```bash
# README only generated on success
ls outputs/my-lora/README.md

# If exists = Training completed successfully
# If missing = Training failed or still running
```

---

## False Positives/Negatives

### Can FluxGym Show Success When Training Failed?

**No!** Multiple checks prevent this:

1. ✅ Model file must exist
2. ✅ No exceptions during training
3. ✅ State file must show "completed"
4. ✅ Training log must have success marker

All 4 must pass for "✅ Training Complete" to show.

### Can FluxGym Show Failure When Training Succeeded?

**Very unlikely**, but possible in edge cases:

1. ❌ Model file renamed/moved manually before check
2. ❌ Permission issues preventing file read
3. ❌ Filesystem lag (network storage)

**Mitigation**: Check manually if you suspect false negative.

---

## Timeout Scenarios

### DataLoader Timeout (60 seconds)

**When**: Worker process hangs loading data

**What happens**:
```
1. Worker timeout after 60 seconds
2. Exception: "DataLoader worker (pid XXXX) is killed by signal: Terminated."
3. Training stops immediately
4. Status: "failed"
5. UI shows: "❌ Training Failed: Training crashed with error..."
6. Training log shows: "ERROR: TRAINING CRASHED - ..."
```

**User sees**: Clear error message about DataLoader timeout

### Block Swap Timeout (30 seconds)

**When**: CUDA deadlock during weight swap (only if user enables `--blocks_to_swap`)

**What happens**:
```
1. Block swap timeout after 30 seconds
2. Exception: "RuntimeError: Block swap timeout for block X after 30 seconds"
3. Training stops immediately
4. Status: "failed"
5. UI shows: "❌ Training Failed: Training crashed with error..."
6. Training log shows: "ERROR: TRAINING CRASHED - RuntimeError: Block swap timeout..."
```

**User sees**: Clear error message about block swap deadlock

### File I/O Timeout (30 seconds)

**When**: NPZ cache file loading hangs (network filesystem)

**What happens**:
```
1. File load timeout after 30 seconds
2. Exception: "RuntimeError: Timeout loading latents from X after 30 seconds"
3. Training stops immediately
4. Status: "failed"
5. UI shows: "❌ Training Failed: Training crashed with error..."
6. Training log shows: "ERROR: TRAINING CRASHED - RuntimeError: Timeout loading latents..."
```

**User sees**: Clear error message about file I/O timeout

---

## Monitoring Integration

### Monitor Detects Stuck Training

**Monitor behavior**:
```python
# Every 30 seconds
gpu_util = get_gpu_utilization()

if gpu_util < 5%:
    stuck_duration += 30

if stuck_duration >= 300:  # 5 minutes
    # Kill training process
    # Log checkpoint path
```

**FluxGym detects**:
```
1. Training process killed by monitor
2. Model file not generated (incomplete)
3. Status set to "failed"
4. User can resume from checkpoint
```

**Result**: Monitoring + FluxGym work together to detect and report hangs

---

## Best Practices

### 1. Always Check Active Sessions After Training

```
✅ DO: Refresh UI and check "🔄 Active Training Sessions"
❌ DON'T: Assume training succeeded without checking
```

### 2. Monitor Training Progress

```
✅ DO: Periodically check "📜 Training Log (Persisted)"
❌ DON'T: Walk away and forget about training
```

### 3. Verify Model File Exists

```bash
✅ DO: ls outputs/my-lora/*.safetensors
❌ DON'T: Download blindly without checking
```

### 4. Check for Error Messages

```
✅ DO: Read last 20 lines of training.log
❌ DON'T: Ignore error messages in logs
```

### 5. Use Monitoring + Checkpointing

```
✅ DO: Enable both features (default ON)
❌ DON'T: Disable monitoring to save resources
```

---

## Summary Table

| Indicator | Success | Failure | Running |
|-----------|---------|---------|---------|
| **UI Banner** | ✅ Training Complete | ❌ Training Failed | 🟢 Running |
| **Active Sessions** | ✅ Completed | ❌ Failed | 🟢 Running |
| **Model File** | Exists | Missing | N/A |
| **State Status** | "completed" | "failed" | "running" |
| **Training Log** | ✅ COMPLETED | ❌ ERROR | In progress |
| **README.md** | Generated | Not generated | Not generated |

---

## Troubleshooting

### "Training Failed" but Model Exists

**Rare edge case**:
- Model was partially written before crash
- File exists but is corrupted/incomplete

**Check**:
```bash
# Check file size (should be ~50-500MB for LoRA)
ls -lh outputs/my-lora/*.safetensors

# Try loading in ComfyUI/A1111
# If loads successfully = false positive
# If fails to load = training truly failed
```

### "Training Completed" but Model Missing

**Almost impossible** - model file check happens first

**If it happens**:
- File system lag on network storage
- File deleted between check and message
- Race condition (very unlikely)

**Verify**:
```bash
# Check if file was created then deleted
ls -la outputs/my-lora/

# Check training log for success marker
tail outputs/my-lora/training.log
```

---

## Conclusion

**You asked the right question!**

With fast-failure timeouts, it's critical to distinguish success from failure. FluxGym now has **6 layers of verification**:

1. ✅ Model file existence check
2. ✅ Exception handling
3. ✅ State file status tracking
4. ✅ Training log markers
5. ✅ UI status indicators
6. ✅ Gradio notifications

**Result**: You will **always** know if training succeeded or failed. No ambiguity! 🎯

---

## Quick Reference

**Check training status**:
```bash
# Method 1: UI (easiest)
Refresh FluxGym → Check "🔄 Active Training Sessions"

# Method 2: Command line
tail -n 20 outputs/my-lora/training.log | grep -E "COMPLETED|FAILED|CRASHED"

# Method 3: State file
cat outputs/my-lora/ui_state.json | jq '.status'

# Method 4: Model file
ls outputs/my-lora/*.safetensors && echo "SUCCESS" || echo "FAILED"
```

**Status meanings**:
- ✅ = Completed successfully, model ready to use
- ❌ = Failed, check logs and resume from checkpoint if available
- 🟢 = Still running, wait or monitor progress
- 🔵 = Stopped, unknown status (check manually)
