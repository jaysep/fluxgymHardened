# Quick Start - Cloud Edition ☁️

## 30-Second Setup

```bash
# 1. Start FluxGym (persistent)
nohup python app.py > fluxgym.log 2>&1 &
echo $! > fluxgym.pid

# 2. In browser (http://<your-ip>:7860):
#    ✅ Enable Checkpointing (default ON)
#    ✅ Enable Auto-Monitoring (default ON)
#    Click "Start training"

# 3. Disconnect SSH - everything keeps running!

# 4. Reconnect anytime and check status:
tail -f outputs/my-lora/monitor.log
```

That's it! 🎉

---

## The Two Checkboxes You Need

```
Step 1. LoRA Info
[...configuration...]

✅ Enable Checkpointing (Save training state for resume)
✅ Enable Auto-Monitoring (Detect stuck training automatically)
```

**Both are ON by default.** Just leave them checked!

---

## What Happens Automatically

When you click "Start training":

1. ✅ Training starts
2. ✅ Monitor starts (in background, detached)
3. ✅ Checkpoints save every 4 epochs
4. ✅ Monitor watches GPU every 30 seconds
5. ✅ If stuck (GPU=0% for 5min), monitor kills processes
6. ✅ Everything survives SSH disconnect

**You do**: Configure and click start
**FluxGym does**: Everything else

---

## Check Status

### In UI

1. Expand "Monitor Status & Logs" (below train log)
2. Click "Refresh Monitor Status"
3. See: Running ✅ or Not Running ⭕
4. View last 10 lines of monitor log

### In Terminal

```bash
# Is monitor running?
cat outputs/my-lora/monitor.pid
ps -p $(cat outputs/my-lora/monitor.pid)

# View monitor log
tail -f outputs/my-lora/monitor.log

# Is training running?
ps aux | grep flux_train_network

# Check GPU
nvidia-smi
```

---

## Recovery if Stuck

### Automatic

Monitor detects stuck and kills processes automatically.
Check the log to see:
```bash
tail outputs/my-lora/monitor.log
# Look for: "TRAINING STUCK DETECTED!"
```

### Manual Resume

1. Find checkpoint:
   ```bash
   python find_checkpoint.py outputs/my-lora
   ```

2. In UI, enter checkpoint path:
   ```
   outputs/my-lora/my-lora-8-state
   ```

3. Click "Start training"

Done! Continues from epoch 9.

---

## Stop Everything

```bash
# Stop FluxGym
kill $(cat fluxgym.pid)
rm fluxgym.pid

# Stop monitor (or use UI button)
kill $(cat outputs/my-lora/monitor.pid)

# Stop training
pkill -9 -f "flux_train_network"
```

---

## Download Your Model

```bash
# From cloud to local machine
scp user@cloud-ip:/workspace/fluxgym/outputs/my-lora/*.safetensors ./
```

---

## Full Documentation

- **Cloud Guide**: [CLOUD_DEPLOYMENT_GUIDE.md](CLOUD_DEPLOYMENT_GUIDE.md)
- **Cloud Update**: [CLOUD_UPDATE_SUMMARY.md](CLOUD_UPDATE_SUMMARY.md)
- **Feature Docs**: [README_CHECKPOINT_FEATURE.md](README_CHECKPOINT_FEATURE.md)
- **Complete Guide**: [CHECKPOINT_RESUME_GUIDE.md](CHECKPOINT_RESUME_GUIDE.md)

---

## Pro Tips

1. **Always start FluxGym with nohup on cloud**
2. **Keep both checkboxes checked (default)**
3. **Check monitor.log if training seems stuck**
4. **Download models promptly (cloud storage costs money)**
5. **Clean up old checkpoints (save disk space)**

---

That's all you need! Simple, automatic, cloud-ready. 🚀
