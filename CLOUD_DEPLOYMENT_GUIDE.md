# FluxGym Cloud Deployment Guide

Complete guide for running FluxGym on cloud services (Runpod, Vast.ai, Lambda Labs, etc.) with automatic monitoring and recovery.

## ⚡ Quick Start (Cloud-Ready)

### 1. Install FluxGym

```bash
cd /workspace  # or your cloud workspace path
git clone https://github.com/cocktailpeanut/fluxgym
cd fluxgym
git clone -b sd3 https://github.com/kohya-ss/sd-scripts

# Create venv
python -m venv env
source env/bin/activate

# Install dependencies
cd sd-scripts
pip install -r requirements.txt
cd ..
pip install -r requirements.txt

# Install PyTorch (for CUDA 12.1)
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 2. Start FluxGym (Persistent Mode)

The app is already configured to survive terminal disconnections:

```bash
# Start FluxGym in background
nohup python app.py > fluxgym.log 2>&1 &

# Save the PID
echo $! > fluxgym.pid

# Check it's running
tail -f fluxgym.log
```

Access at: `http://<your-ip>:7860`

### 3. Train with Monitoring

In the FluxGym UI:
1. ✅ Check "Enable Checkpointing"
2. ✅ Check "Enable Auto-Monitoring"
3. Start training

**That's it!** The monitoring runs automatically in the background, detached from your terminal.

---

## 🔧 Cloud-Specific Features

### Automatic Process Management

FluxGym now handles everything for you:

- ✅ **Monitoring auto-starts** when you click "Start training"
- ✅ **Runs in background** (won't die if terminal closes)
- ✅ **Process detachment** (uses `start_new_session`)
- ✅ **PID tracking** (easy to find and manage processes)
- ✅ **Log persistence** (everything logged to files)

### Monitor Status in UI

After starting training:
1. Click "Monitor Status & Logs" accordion
2. Click "Refresh Monitor Status"
3. See live monitor status and recent logs
4. Click "Stop Monitor" if needed

---

## 📋 Common Cloud Workflows

### Workflow 1: Start Training and Disconnect

```bash
# 1. Start FluxGym in background
nohup python app.py > fluxgym.log 2>&1 &
echo $! > fluxgym.pid

# 2. In browser:
#    - Configure training
#    - ✅ Enable Checkpointing
#    - ✅ Enable Auto-Monitoring
#    - Click "Start training"

# 3. Disconnect from SSH - everything keeps running!

# 4. Reconnect later and check status
tail -f outputs/my-lora/monitor.log
ls -lh outputs/my-lora/  # Check for checkpoints
```

### Workflow 2: Resume After Stuck Training

```bash
# 1. Reconnect to your cloud instance

# 2. Check if monitor detected stuck training
tail outputs/my-lora/monitor.log

# If stuck was detected, you'll see:
# "TRAINING STUCK DETECTED!"
# "Latest checkpoint: outputs/my-lora/my-lora-8-state"

# 3. In FluxGym UI:
#    - Enter checkpoint path in "Resume from Checkpoint"
#    - Click "Start training"

# Training continues from epoch 9!
```

### Workflow 3: Manual Check and Recovery

```bash
# Check if training is still running
ps aux | grep flux_train_network

# Check GPU usage
nvidia-smi

# If stuck (GPU at 0%), kill processes
pkill -9 -f "flux_train_network"

# Find checkpoint
python find_checkpoint.py outputs/my-lora

# Resume in UI with the checkpoint path shown
```

### Workflow 4: Multiple Training Runs

```bash
# Start FluxGym once
nohup python app.py > fluxgym.log 2>&1 &

# Train multiple LoRAs in sequence (in browser):
# 1. Train lora-1 (with monitoring)
# 2. When complete, train lora-2 (with monitoring)
# 3. Each gets its own monitor automatically

# All monitors run independently in background
```

---

## 🛡️ Reliability Features

### 1. Process Persistence

**Problem**: SSH disconnect kills processes
**Solution**: Background processes with `nohup` and `start_new_session`

```python
# FluxGym automatically uses:
subprocess.Popen(..., start_new_session=True)
```

This detaches from parent, survives SSH disconnects.

### 2. PID Tracking

Every monitor saves its PID:
```
outputs/my-lora/monitor.pid
```

Check what's running:
```bash
cat outputs/my-lora/monitor.pid
ps -p $(cat outputs/my-lora/monitor.pid)
```

### 3. Comprehensive Logging

All logs persist to disk:
```
fluxgym.log              # Main app log
outputs/my-lora/monitor.log     # Monitor log
outputs/my-lora/train.log       # Training log (if redirected)
```

### 4. Automatic Cleanup

If monitor detects stuck training:
- Kills stuck processes
- Logs the event
- Shows checkpoint for resume
- Continues monitoring (unless you stop it)

---

## 🔍 Monitoring & Debugging

### Check FluxGym Status

```bash
# Is FluxGym running?
ps aux | grep "python app.py"

# Check logs
tail -f fluxgym.log

# Access UI
curl http://localhost:7860  # Should return HTML
```

### Check Training Status

```bash
# Is training running?
ps aux | grep flux_train

# Check GPU
nvidia-smi
watch -n 1 nvidia-smi  # Live update

# Check training progress
ls -lth outputs/my-lora/*.safetensors
```

### Check Monitor Status

```bash
# Via UI: Click "Refresh Monitor Status"

# Via command line:
cat outputs/my-lora/monitor.pid
ps -p $(cat outputs/my-lora/monitor.pid)

# View monitor logs
tail -f outputs/my-lora/monitor.log

# Last 50 lines
tail -50 outputs/my-lora/monitor.log
```

### Debug Stuck Training

```bash
# 1. Check GPU usage
nvidia-smi

# 2. Check if training process exists
ps aux | grep flux_train

# 3. Check monitor log
tail outputs/my-lora/monitor.log

# 4. If stuck, check for checkpoint
ls -lth outputs/my-lora/*-state/

# 5. Manual kill if needed
pkill -9 -f "flux_train_network"

# 6. Resume from checkpoint in UI
```

---

## 💾 Storage Management

### Checkpoint Sizes

Checkpoints are large (~2-4 GB each):

```bash
# Check disk usage
du -h outputs/my-lora/

# Example output:
# 3.2G    outputs/my-lora/my-lora-4-state
# 3.2G    outputs/my-lora/my-lora-8-state
# 3.2G    outputs/my-lora/my-lora-12-state
# 120M    outputs/my-lora/my-lora.safetensors
```

### Cleanup Old Checkpoints

```bash
# Keep only last 2 checkpoints
cd outputs/my-lora/
ls -t *-state | tail -n +3 | xargs rm -rf

# Or delete specific checkpoint
rm -rf my-lora-4-state/
```

### Monitor Disk Space

```bash
# Check available space
df -h /workspace

# Set up alert (optional)
while true; do
  USAGE=$(df /workspace | tail -1 | awk '{print $5}' | sed 's/%//')
  if [ $USAGE -gt 90 ]; then
    echo "WARNING: Disk usage at ${USAGE}%"
  fi
  sleep 300  # Check every 5 minutes
done &
```

---

## 🔐 Security & Best Practices

### 1. Firewall (if applicable)

```bash
# FluxGym runs on port 7860
# Make sure it's accessible:
sudo ufw allow 7860
```

### 2. Process Isolation

Each LoRA training:
- Has its own monitor process
- Has its own log files
- Has its own PID file
- Runs independently

### 3. Resource Management

```bash
# Check system resources
htop

# Kill specific training if needed
kill $(cat outputs/my-lora/monitor.pid)
pkill -9 -f "flux_train_network"
```

### 4. Backup Important Data

```bash
# Backup your trained models
rsync -av outputs/ /backup/fluxgym-outputs/

# Or to local machine
scp -r user@cloud:/workspace/fluxgym/outputs/my-lora/ ./local-backup/
```

---

## 🚨 Troubleshooting

### FluxGym Won't Start

```bash
# Check logs
tail -100 fluxgym.log

# Check if port is in use
lsof -i :7860

# Kill old instance
kill $(cat fluxgym.pid)
rm fluxgym.pid

# Restart
nohup python app.py > fluxgym.log 2>&1 &
echo $! > fluxgym.pid
```

### Monitor Not Starting

```bash
# Check if training_monitor.py exists
ls -l training_monitor.py

# Test manually
python training_monitor.py --output-dir outputs/my-lora

# Check permissions
chmod +x training_monitor.py
```

### Training Stuck But Monitor Didn't Detect

```bash
# Check monitor is running
cat outputs/my-lora/monitor.pid
ps -p $(cat outputs/my-lora/monitor.pid)

# Check monitor logs for errors
tail -50 outputs/my-lora/monitor.log

# Manually trigger recovery
pkill -9 -f "flux_train_network"
python find_checkpoint.py outputs/my-lora
# Then resume in UI
```

### Can't Resume from Checkpoint

```bash
# Verify checkpoint exists
ls -la outputs/my-lora/*-state/

# Check checkpoint contents
ls -la outputs/my-lora/my-lora-8-state/
# Should contain: optimizer.bin, scheduler.bin, etc.

# Try cleaning cache
rm -rf outputs/my-lora/cache

# Verify path in UI (no quotes needed)
# Correct: outputs/my-lora/my-lora-8-state
# Wrong: "outputs/my-lora/my-lora-8-state"
```

### Out of Memory After Resume

```bash
# Clear all caches
rm -rf outputs/my-lora/cache

# Check available GPU memory
nvidia-smi

# May need to lower VRAM setting in UI
# Or use different optimizer
```

---

## 📊 Monitoring Best Practices

### 1. Always Enable for Cloud

```
✅ Enable Checkpointing: ON
✅ Enable Auto-Monitoring: ON
```

Cloud instances can be interrupted, so always protect your training.

### 2. Adjust Thresholds for Your GPU

If you get false alarms:
- Edit `app.py` line ~635
- Change `--stuck-threshold` from 300 to 600 (10 minutes)
- Change `--gpu-threshold` from 5.0 to 10.0

### 3. Check Logs Periodically

```bash
# Set up a cron job to email you logs daily
0 0 * * * tail -100 /workspace/fluxgym/outputs/*/monitor.log | mail -s "FluxGym Status" you@email.com
```

### 4. Keep Disk Space Available

- Monitor disk usage
- Clean old checkpoints
- Download completed models locally
- Delete old training runs

---

## 🌐 Cloud Provider Specific Tips

### Runpod

```bash
# Workspace: /workspace
cd /workspace
git clone ...

# Start FluxGym
nohup python app.py > fluxgym.log 2>&1 &

# Access via Runpod's proxy URL
# (automatically configured with root_path="/proxy/7860")
```

### Vast.ai

```bash
# Similar to Runpod
cd /workspace
# Follow standard installation

# May need to configure firewall
# Check Vast.ai dashboard for your instance's IP
```

### Lambda Labs

```bash
# Often /home/ubuntu
cd /home/ubuntu
# Follow standard installation

# Access directly via instance IP:7860
```

### Google Colab (Not Recommended for Long Training)

```python
# Colab disconnects after inactivity
# Better for short experiments only
# For production, use dedicated cloud GPU
```

---

## 📈 Performance Optimization

### 1. Faster Checkpointing

```python
# In UI, set "Save every N epochs" to 8 instead of 4
# Fewer checkpoints = faster training
# But less granular resume points
```

### 2. Monitor Interval

```python
# For very long training (48+ hours):
# Could increase check interval to 60 seconds
# Edit app.py line ~634:
"--check-interval", "60",  # Was 30
```

### 3. Disk I/O

```bash
# If using NVMe SSD, cache can be on disk
# If using network storage, may want to disable cache

# Check I/O speed
dd if=/dev/zero of=test.img bs=1G count=1 oflag=direct
rm test.img
```

---

## ✅ Cloud Deployment Checklist

Before starting a long training run:

- [ ] FluxGym running in background (`nohup`)
- [ ] Checkpointing enabled in UI
- [ ] Auto-monitoring enabled in UI
- [ ] Sufficient disk space (check with `df -h`)
- [ ] GPU detected (`nvidia-smi`)
- [ ] Test resume with small dataset first
- [ ] Know how to access logs (`tail -f ...`)
- [ ] Have backup plan for trained models

---

## 🎓 Example: Full Cloud Training Session

```bash
# === Initial Setup (once per instance) ===

# 1. Clone and install
cd /workspace
git clone https://github.com/cocktailpeanut/fluxgym
cd fluxgym
git clone -b sd3 https://github.com/kohya-ss/sd-scripts
python -m venv env
source env/bin/activate
cd sd-scripts && pip install -r requirements.txt && cd ..
pip install -r requirements.txt
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 2. Start FluxGym (persistent)
nohup python app.py > fluxgym.log 2>&1 &
echo $! > fluxgym.pid

# === Training (in browser) ===

# 3. Access http://<cloud-ip>:7860
# 4. Configure LoRA
# 5. Upload images
# 6. ✅ Enable Checkpointing
# 7. ✅ Enable Auto-Monitoring
# 8. Click "Start training"

# === Monitoring (terminal) ===

# 9. Watch progress
tail -f outputs/my-lora/monitor.log

# 10. Disconnect SSH (everything keeps running!)

# === Next Day (reconnect) ===

# 11. Check status
cat outputs/my-lora/monitor.log | tail -20
ls -lh outputs/my-lora/

# 12. If stuck, resume
python find_checkpoint.py outputs/my-lora
# Use checkpoint path in UI

# === After Training ===

# 13. Download trained model
scp user@cloud:/workspace/fluxgym/outputs/my-lora/my-lora.safetensors ./

# 14. Clean up
rm -rf outputs/my-lora/*-state/  # Remove checkpoints
kill $(cat fluxgym.pid)  # Stop FluxGym if done
```

---

## 🆘 Emergency Recovery

If everything goes wrong:

```bash
# 1. Kill all Python processes
pkill -9 python

# 2. Clean up PIDs
rm -f fluxgym.pid outputs/*/monitor.pid

# 3. Find latest checkpoint
find outputs -name "*-state" -type d | sort

# 4. Restart FluxGym
nohup python app.py > fluxgym.log 2>&1 &
echo $! > fluxgym.pid

# 5. Resume in UI with latest checkpoint

# 6. Re-enable monitoring
# (will start automatically when you click "Start training")
```

---

## 📚 Additional Resources

- Main Guide: [CHECKPOINT_RESUME_GUIDE.md](CHECKPOINT_RESUME_GUIDE.md)
- Quick Reference: [QUICK_RECOVERY_GUIDE.md](QUICK_RECOVERY_GUIDE.md)
- Feature Overview: [README_CHECKPOINT_FEATURE.md](README_CHECKPOINT_FEATURE.md)

---

**Remember**: Cloud instances can be terminated without warning. Always:
1. Enable checkpointing
2. Enable monitoring
3. Download completed models promptly
4. Keep backups of important training data

Happy cloud training! ☁️🚀
