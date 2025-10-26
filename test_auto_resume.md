# Testing Auto-Resume Functionality

## Overview

The training monitor now supports automatic resume/restart when training gets stuck:
- **If checkpoint exists:** Kills stuck processes, modifies train.sh to add `--resume <checkpoint>`, restarts training
- **If no checkpoint:** Kills stuck processes, restarts training from beginning

## How It Works

1. **Detection:** Monitor checks GPU usage every 30 seconds (configurable)
2. **Stuck Threshold:** If GPU drops below 5% for 300 seconds (5 minutes), training is considered stuck
3. **Kill Processes:** All training-related Python processes are killed
4. **Find Checkpoint:** Searches output directory for latest checkpoint (state directory)
5. **Resume/Restart:**
   - With checkpoint: Modifies train.sh to add `--resume <checkpoint>`, executes it
   - No checkpoint: Executes original train.sh

## Usage

### Start Monitoring with Auto-Resume

```bash
cd /workspace/fluxgym

# Start monitoring in background
nohup python3 training_monitor.py \
  --output-dir /workspace/fluxgym/outputs/my-lora \
  --train-script /workspace/fluxgym/outputs/my-lora/train.sh \
  --auto-resume \
  --stuck-threshold 300 \
  --check-interval 30 \
  > training_monitor.log 2>&1 &

# Check monitor logs
tail -f training_monitor.log
```

### What Happens When Training Gets Stuck

1. Monitor detects GPU at 0% for 5 minutes
2. Logs: `TRAINING STUCK DETECTED!`
3. Finds and logs latest checkpoint: `Latest state checkpoint: outputs/my-lora/my-lora-step-150-state`
4. Kills all training processes
5. Modifies train.sh to add: `--resume outputs/my-lora/my-lora-step-150-state \`
6. Executes modified train.sh
7. Logs: `Training restarted with PID: 12345`
8. Continues monitoring the resumed training

### Monitor Output Example

```
2025-01-26 14:30:00 - INFO - Training Monitor initialized:
2025-01-26 14:30:00 - INFO -   Output directory: /workspace/fluxgym/outputs/my-lora
2025-01-26 14:30:00 - INFO -   Check interval: 30s
2025-01-26 14:30:00 - INFO -   Stuck threshold: 300s
2025-01-26 14:30:00 - INFO -   GPU threshold: 5.0%
2025-01-26 14:30:00 - INFO -   Auto-resume: True
2025-01-26 14:30:00 - INFO - Starting training monitor...

# ... normal monitoring ...

2025-01-26 14:35:00 - WARNING - Low GPU usage detected (0.0%), monitoring...
2025-01-26 14:35:30 - WARNING - Low GPU usage for 30s (threshold: 300s)
2025-01-26 14:36:00 - WARNING - Low GPU usage for 60s (threshold: 300s)
# ... continues for 5 minutes ...
2025-01-26 14:40:00 - WARNING - Low GPU usage for 300s (threshold: 300s)

2025-01-26 14:40:00 - ERROR - ================================================================================
2025-01-26 14:40:00 - ERROR - TRAINING STUCK DETECTED!
2025-01-26 14:40:00 - ERROR - ================================================================================
2025-01-26 14:40:00 - ERROR - GPU utilization: 0.0%
2025-01-26 14:40:00 - ERROR - GPU memory: 15234 MB
2025-01-26 14:40:00 - INFO - Latest state checkpoint: /workspace/fluxgym/outputs/my-lora/my-lora-step-150-state
2025-01-26 14:40:00 - INFO - Latest model checkpoint: /workspace/fluxgym/outputs/my-lora/my-lora-step-150.safetensors
2025-01-26 14:40:00 - INFO - Killing all training processes...
2025-01-26 14:40:00 - INFO - Found 3 training processes to kill
2025-01-26 14:40:00 - INFO - Killing process 9876: accelerate launch --num_cpu_threads_per_process=2 sd-scripts/flux_train_network.py...
2025-01-26 14:40:02 - INFO - Force killed process 9876
2025-01-26 14:40:02 - INFO - Killing process 9877: python flux_train_network.py --pretrained_model_name_or_path...
2025-01-26 14:40:04 - INFO - Force killed process 9877
2025-01-26 14:40:04 - INFO - Killing process 9878: python flux_train_network.py --pretrained_model_name_or_path...
2025-01-26 14:40:06 - INFO - Force killed process 9878
2025-01-26 14:40:09 - INFO - All training processes killed successfully
2025-01-26 14:40:09 - INFO - Auto-resume is enabled. Attempting to resume training from checkpoint...
2025-01-26 14:40:09 - INFO - Modified training script with --resume /workspace/fluxgym/outputs/my-lora/my-lora-step-150-state
2025-01-26 14:40:09 - INFO - Starting training from checkpoint: /workspace/fluxgym/outputs/my-lora/my-lora-step-150-state
2025-01-26 14:40:09 - INFO - Executing: bash /workspace/fluxgym/outputs/my-lora/train.sh
2025-01-26 14:40:09 - INFO - Output will be logged to: /workspace/fluxgym/outputs/my-lora/training_resume.log
2025-01-26 14:40:09 - INFO - Training restarted with PID: 12345
2025-01-26 14:40:09 - INFO - Monitor will continue tracking the resumed training...
2025-01-26 14:40:09 - INFO - Continuing to monitor after recovery...

# ... continues monitoring ...
```

## Modified train.sh Example

### Original train.sh
```bash
accelerate launch --num_cpu_threads_per_process=2 sd-scripts/flux_train_network.py \
  --pretrained_model_name_or_path flux1-dev.safetensors \
  --dataset_config dataset.toml \
  --output_dir outputs/my-lora \
  --output_name my-lora \
  --save_model_as safetensors \
  --optimizer_type adamw8bit \
  --save_state \
  --sample_prompts=sample.txt \
  --loss_type l2
```

### After Auto-Resume (with checkpoint)
```bash
accelerate launch --num_cpu_threads_per_process=2 sd-scripts/flux_train_network.py \
  --pretrained_model_name_or_path flux1-dev.safetensors \
  --dataset_config dataset.toml \
  --output_dir outputs/my-lora \
  --output_name my-lora \
  --save_model_as safetensors \
  --optimizer_type adamw8bit \
  --save_state \
  --sample_prompts=sample.txt \
  --resume outputs/my-lora/my-lora-step-150-state \
  --loss_type l2
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `--output-dir` | *required* | Directory where checkpoints are saved |
| `--train-script` | *required* | Path to train.sh script |
| `--auto-resume` | false | Enable automatic resume/restart |
| `--check-interval` | 30 | Check GPU every N seconds |
| `--stuck-threshold` | 300 | Consider stuck after N seconds (5 min) |
| `--gpu-threshold` | 5.0 | GPU % below which is considered idle |

## Testing Without Waiting 5 Minutes

For testing, reduce the stuck threshold:

```bash
# Test with 60 second threshold (1 minute)
python3 training_monitor.py \
  --output-dir /workspace/fluxgym/outputs/my-lora \
  --train-script /workspace/fluxgym/outputs/my-lora/train.sh \
  --auto-resume \
  --stuck-threshold 60 \
  --check-interval 10
```

## Troubleshooting

### Monitor Not Detecting Stuck Training

**Check GPU usage manually:**
```bash
nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits
```

If GPU shows 0%, monitor should detect it.

### Training Not Restarting

**Check monitor logs:**
```bash
tail -f training_monitor.log
```

Look for errors like:
- "Training script not found"
- "Failed to execute training script"

**Check training resume log:**
```bash
tail -f /workspace/fluxgym/outputs/my-lora/training_resume.log
```

### Checkpoint Not Found

Monitor will restart from beginning if no checkpoint exists. Check logs:
```
WARNING - No checkpoint found. Restarting training from beginning...
```

## Integration with FluxGym UI

The monitoring script runs independently from the FluxGym UI. To integrate:

1. Start training from UI (generates train.sh)
2. Separately start the monitor with auto-resume
3. Monitor watches GPU and auto-recovers if stuck
4. Training logs visible in UI and in training_resume.log

## Security Notes

- The monitor modifies train.sh when resuming (adds --resume flag)
- Original train.sh is overwritten, not backed up
- If you need the original, copy it before starting monitor:
  ```bash
  cp outputs/my-lora/train.sh outputs/my-lora/train.sh.backup
  ```

## Future Enhancements

Potential improvements for future versions:
- Backup original train.sh before modification
- Support for .bat scripts (Windows)
- Email/webhook notifications when stuck detected
- Web UI for monitoring status
- Multiple training session monitoring
- Configurable recovery strategies
