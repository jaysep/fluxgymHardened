# Auto-Resume Implementation Summary

## Overview

The training monitor (`training_monitor.py`) now fully implements automatic resume/restart functionality when training gets stuck.

## What Was Changed

### File Modified: `training_monitor.py`

**Key Changes:**

1. **Implemented `resume_training()` method (lines 302-367)**
   - Reads the train.sh script
   - Finds the insertion point (before `--loss_type l2`)
   - Adds `--resume <checkpoint_path> \` line
   - Saves modified script
   - Executes modified script in background

2. **Added `restart_training_from_beginning()` method (lines 369-382)**
   - Executes original train.sh without modifications
   - Used when no checkpoint exists

3. **Added `_execute_training_script()` method (lines 384-410)**
   - Executes train.sh in background using subprocess
   - Redirects output to `training_resume.log`
   - Detaches from parent process using `start_new_session=True`
   - Logs PID for tracking

4. **Updated `handle_stuck_training()` method (lines 289-300)**
   - Now calls `resume_training()` if checkpoint exists
   - Calls `restart_training_from_beginning()` if no checkpoint
   - Previously only logged manual instructions

5. **Updated docstring and help text**
   - Added usage examples
   - Clarified auto-resume behavior
   - Updated argument descriptions

## How It Works

### Detection Flow

```
GPU < 5% for 300s → Stuck Detected → Kill Processes → Find Checkpoint
                                                           ↓
                                          Checkpoint Exists?
                                          ↓              ↓
                                        YES            NO
                                          ↓              ↓
                                    Resume Training  Restart from Beginning
                                          ↓              ↓
                                    Add --resume    Execute original script
                                          ↓              ↓
                                    Execute script
                                          ↓              ↓
                                    Continue Monitoring
```

### train.sh Modification

**Before (Original):**
```bash
accelerate launch --num_cpu_threads_per_process=2 sd-scripts/flux_train_network.py \
  --pretrained_model_name_or_path flux1-dev.safetensors \
  --dataset_config dataset.toml \
  --output_dir outputs/my-lora \
  --save_state \
  --loss_type l2
```

**After (With Checkpoint):**
```bash
accelerate launch --num_cpu_threads_per_process=2 sd-scripts/flux_train_network.py \
  --pretrained_model_name_or_path flux1-dev.safetensors \
  --dataset_config dataset.toml \
  --output_dir outputs/my-lora \
  --save_state \
  --resume outputs/my-lora/my-lora-step-150-state \
  --loss_type l2
```

The `--resume` line is inserted before the last parameter line.

## Usage

### Start Monitor with Auto-Resume

```bash
python3 training_monitor.py \
  --output-dir /workspace/fluxgym/outputs/my-lora \
  --train-script /workspace/fluxgym/outputs/my-lora/train.sh \
  --auto-resume \
  --stuck-threshold 300 \
  --check-interval 30
```

### Run in Background

```bash
nohup python3 training_monitor.py \
  --output-dir /workspace/fluxgym/outputs/my-lora \
  --train-script /workspace/fluxgym/outputs/my-lora/train.sh \
  --auto-resume \
  > training_monitor.log 2>&1 &

# Monitor logs
tail -f training_monitor.log
```

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--output-dir` | *required* | Where checkpoints are saved |
| `--train-script` | *required* | Path to train.sh (needed for auto-resume) |
| `--auto-resume` | `false` | Enable auto-resume/restart |
| `--check-interval` | `30` | Check GPU every N seconds |
| `--stuck-threshold` | `300` | Consider stuck after N seconds (5 min) |
| `--gpu-threshold` | `5.0` | GPU % below which is idle |

## Log Output

When stuck training is detected and auto-resume kicks in:

```
2025-01-26 14:40:00 - ERROR - ================================================================================
2025-01-26 14:40:00 - ERROR - TRAINING STUCK DETECTED!
2025-01-26 14:40:00 - ERROR - ================================================================================
2025-01-26 14:40:00 - ERROR - GPU utilization: 0.0%
2025-01-26 14:40:00 - ERROR - GPU memory: 15234 MB
2025-01-26 14:40:00 - INFO - Latest state checkpoint: /workspace/fluxgym/outputs/my-lora/my-lora-step-150-state
2025-01-26 14:40:00 - INFO - Killing all training processes...
2025-01-26 14:40:09 - INFO - All training processes killed successfully
2025-01-26 14:40:09 - INFO - Auto-resume is enabled. Attempting to resume training from checkpoint...
2025-01-26 14:40:09 - INFO - Modified training script with --resume /workspace/fluxgym/outputs/my-lora/my-lora-step-150-state
2025-01-26 14:40:09 - INFO - Executing: bash /workspace/fluxgym/outputs/my-lora/train.sh
2025-01-26 14:40:09 - INFO - Output will be logged to: /workspace/fluxgym/outputs/my-lora/training_resume.log
2025-01-26 14:40:09 - INFO - Training restarted with PID: 12345
2025-01-26 14:40:09 - INFO - Continuing to monitor after recovery...
```

## Testing

### Test Files Created

1. **test_auto_resume.md** - Comprehensive testing documentation
2. **test_monitor_resume.sh** - Automated test script that creates mock training scenario

### Quick Test

```bash
# Run the test setup script
bash test_monitor_resume.sh

# Follow the manual verification steps printed by the script
```

### Test with Short Timeouts

For faster testing, use shorter thresholds:

```bash
python3 training_monitor.py \
  --output-dir /workspace/fluxgym/outputs/my-lora \
  --train-script /workspace/fluxgym/outputs/my-lora/train.sh \
  --auto-resume \
  --stuck-threshold 60 \
  --check-interval 10
```

This will detect stuck state after 1 minute instead of 5 minutes.

## Integration with FluxGym

### Deployment

The auto-resume feature is included in hardened deployment:

```bash
# Deploy hardened FluxGym (includes updated training_monitor.py)
bash deploy_hardened.sh
```

### Usage in Runpod

After deployment:

1. Start training from FluxGym UI
   - Generates `train.sh` in output directory

2. Start monitor in separate terminal:
   ```bash
   cd /workspace/fluxgym
   source env/bin/activate

   python3 training_monitor.py \
     --output-dir outputs/your-lora-name \
     --train-script outputs/your-lora-name/train.sh \
     --auto-resume
   ```

3. Monitor runs continuously:
   - Watches GPU usage
   - Auto-recovers if stuck
   - Resumes from checkpoint or restarts

## Technical Details

### Checkpoint Detection

The monitor searches for checkpoint directories in this priority:

1. Most recent directory containing "state" in name
2. Examples: `my-lora-step-150-state`, `my-lora-epoch-3-state`
3. Sorted by modification time (most recent first)

**Path Resolution:**
- All paths (output_dir, train_script, checkpoints) are converted to **absolute paths** using `Path.resolve()`
- This ensures the checkpoint path works regardless of where the monitor or train.sh run from
- The `--resume` argument inserted into train.sh always uses absolute paths
- Example: `--resume /workspace/fluxgym/outputs/my-lora/my-lora-step-150-state`

### Process Management

**Process Detection:**
- Searches for Python processes containing:
  - `flux_train_network.py`
  - `accelerate launch`
  - `train_network.py`

**Process Killing:**
- Uses `SIGKILL` (force kill) by default
- Waits 3 seconds and verifies all processes killed
- Reports remaining processes if any

### Script Modification

**Insertion Logic:**
1. Read train.sh line by line
2. Find line containing `--loss_type` without trailing `\`
3. Insert `--resume <checkpoint> \` before that line
4. Preserve all other lines unchanged
5. Write modified script back to same file

**Important:** Original train.sh is **overwritten**, not backed up. If you need the original, copy it before starting monitor.

### Background Execution

**Subprocess Configuration:**
```python
subprocess.Popen(
    ['bash', str(script_path)],
    cwd=str(script_dir),           # Run in script's directory
    stdout=f,                       # Redirect to log file
    stderr=subprocess.STDOUT,       # Combine stderr with stdout
    start_new_session=True          # Detach from parent
)
```

**Output Logging:**
- Training output goes to `training_resume.log` in output directory
- Monitor continues tracking while training runs
- Can tail both logs:
  ```bash
  tail -f training_monitor.log training_resume.log
  ```

## Limitations

1. **Only supports .sh scripts**
   - .bat scripts (Windows) show warning and require manual intervention
   - Direct Python command execution not supported

2. **train.sh overwritten**
   - Original script not backed up
   - If you want original, copy before starting monitor

3. **Assumes specific script format**
   - Looks for `--loss_type` as last parameter
   - If script format differs, insertion may fail

4. **Single checkpoint format**
   - Only uses state directories (not .safetensors files)
   - Assumes checkpoint named like `<name>-state` or `<name>-step-N-state`

## Future Enhancements

Potential improvements:

1. **Backup original script** before modification
2. **Support .bat scripts** for Windows environments
3. **Configurable insertion point** for different script formats
4. **Multiple resume strategies** (state vs model checkpoint)
5. **Notifications** (email, webhook) when stuck detected
6. **Web UI** for monitoring status
7. **Multiple training sessions** monitoring

## Troubleshooting

### Monitor Says "Training script not found"

**Check path:**
```bash
ls -la /workspace/fluxgym/outputs/your-lora-name/train.sh
```

**Provide absolute path:**
```bash
--train-script /workspace/fluxgym/outputs/your-lora-name/train.sh
```

### Training Not Restarting

**Check training_resume.log:**
```bash
tail -50 /workspace/fluxgym/outputs/your-lora-name/training_resume.log
```

**Look for errors** like:
- Python import errors
- Missing dependencies
- Invalid arguments

### Checkpoint Not Detected

**Manually check for checkpoints:**
```bash
ls -la /workspace/fluxgym/outputs/your-lora-name/ | grep state
```

**If no checkpoints:**
- Monitor will restart from beginning
- First training run won't have checkpoint yet
- Checkpoint created after first save interval

### Monitor Stops After Recovery

**Check logs:**
```bash
tail -100 training_monitor.log
```

**If subprocess failed:**
- Training script may have errors
- Check training_resume.log for details

## Summary

The auto-resume implementation provides:

✅ **Automatic stuck detection** - No manual monitoring needed
✅ **Process cleanup** - Kills all stuck training processes
✅ **Checkpoint resume** - Continues from last save point
✅ **Fallback restart** - Starts fresh if no checkpoint
✅ **Background execution** - Training runs independently
✅ **Continuous monitoring** - Keeps watching after recovery
✅ **Comprehensive logging** - All actions logged for debugging

This makes FluxGym training on Runpod much more reliable and hands-off!
