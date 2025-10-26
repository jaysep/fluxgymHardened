# FluxGym Checkpoint & Auto-Recovery Feature

## 🎯 Quick Start

### Problem: Training Gets Stuck?

FluxGym now has **automatic stuck detection and checkpoint recovery**!

### Solution in 3 Steps:

1. **Enable Checkpointing** (in FluxGym UI before training)
   - ✅ Check "Enable Checkpointing (Save training state for resume)"

2. **Start Monitoring** (in separate terminal while training)
   ```bash
   ./train_with_monitoring.sh my-lora-name
   ```

3. **Recover if Stuck** (follow the prompts)
   - Monitor detects stuck training automatically
   - Shows you the checkpoint to resume from
   - You resume through FluxGym UI

That's it! Now your training is protected.

---

## 📚 Documentation

- **[QUICK_RECOVERY_GUIDE.md](QUICK_RECOVERY_GUIDE.md)** - Emergency 30-second fix
- **[CHECKPOINT_RESUME_GUIDE.md](CHECKPOINT_RESUME_GUIDE.md)** - Complete documentation
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Technical details

---

## 🛠️ New Tools

### 1. Training Monitor (Automatic Stuck Detection)

Watches your training and alerts when GPU usage drops to zero:

```bash
python training_monitor.py --output-dir outputs/my-lora
```

Or use the wrapper for easier setup:

```bash
./train_with_monitoring.sh my-lora
```

**What it does:**
- ✅ Monitors GPU usage every 30 seconds
- ✅ Detects when training is stuck (GPU < 5% for 5+ minutes)
- ✅ Automatically kills stuck processes
- ✅ Shows you the latest checkpoint to resume from
- ✅ Logs everything for debugging

### 2. Checkpoint Finder

Quickly find checkpoints to resume from:

```bash
python find_checkpoint.py outputs/my-lora
```

**Output:**
```
Latest state checkpoint: outputs/my-lora/my-lora-8-state

To resume training, add this in FluxGym UI:
  outputs/my-lora/my-lora-8-state
```

List all checkpoints:
```bash
python find_checkpoint.py outputs/my-lora --list
```

### 3. Training Wrapper (Easiest)

All-in-one script that handles monitoring:

```bash
./train_with_monitoring.sh my-lora
```

This will:
- ✅ Check for existing checkpoints
- ✅ Offer to resume if found
- ✅ Start monitoring automatically
- ✅ Show recovery instructions if stuck
- ✅ Log everything to `outputs/my-lora/monitor.log`

---

## 💡 Usage Examples

### Example 1: Protected Training (Recommended)

```bash
# Terminal 1: Start FluxGym
python app.py

# In browser:
# 1. Configure your LoRA
# 2. ✅ Check "Enable Checkpointing"
# 3. Click "Start training"

# Terminal 2: Start monitoring
./train_with_monitoring.sh my-lora
```

Now you're protected! If training gets stuck, the monitor will detect it and help you resume.

### Example 2: Resume After Crash

```bash
# Find your checkpoint
python find_checkpoint.py outputs/my-lora

# Output shows: outputs/my-lora/my-lora-12-state

# In FluxGym UI:
# 1. Paste "outputs/my-lora/my-lora-12-state" in Resume field
# 2. Click "Start training"
```

Training continues from epoch 13!

### Example 3: Manual Recovery

```bash
# 1. Kill stuck processes
pkill -9 -f "flux_train_network"

# 2. Find checkpoint
python find_checkpoint.py outputs/my-lora

# 3. Resume in FluxGym UI with the shown path
```

---

## ⚙️ How It Works

### Checkpoint System

When you enable checkpointing, FluxGym saves the **complete training state** every N epochs:

```
outputs/my-lora/
├── my-lora-4-state/       # Full state at epoch 4
│   ├── optimizer.bin       # Optimizer state (AdamW/AdaFactor)
│   ├── scheduler.bin       # Learning rate scheduler
│   ├── random_states_0.pkl # Random number generator states
│   └── ...
├── my-lora-8-state/       # Full state at epoch 8
├── my-lora.safetensors    # Final trained model
└── sample/                # Sample images
```

This allows **exact resume** from any checkpoint - same optimizer state, same progress.

### Stuck Detection

The monitor watches your GPU:

1. **Every 30 seconds**: Checks GPU utilization via `nvidia-smi`
2. **If GPU < 5%**: Starts counting
3. **If stuck for 5+ minutes**: Triggers recovery
4. **Recovery**: Kills processes, finds checkpoint, shows instructions

### Resume Process

When you resume:

1. FluxGym loads the checkpoint state
2. Restores model, optimizer, scheduler, everything
3. Continues training from the next epoch
4. Uses same random seeds for reproducibility

---

## 🎛️ Configuration

### FluxGym UI Settings

**Enable Checkpointing** (Checkbox)
- When: Before starting training
- What: Saves training state every `save_every_n_epochs` (default: 4)
- Size: ~2-4 GB per checkpoint
- Recommendation: ✅ Always enable for long training

**Resume from Checkpoint** (Text field)
- When: Restarting stuck/crashed training
- What: Path to checkpoint folder (e.g., `outputs/my-lora/my-lora-8-state`)
- Find it: `python find_checkpoint.py outputs/my-lora`

### Monitor Settings

```bash
python training_monitor.py \
  --output-dir outputs/my-lora \    # Required: where your LoRA is saved
  --check-interval 30 \              # How often to check (seconds)
  --stuck-threshold 300 \            # How long before "stuck" (seconds)
  --gpu-threshold 5.0                # GPU% below which is idle
```

**Adjust for your needs:**
- **Faster detection**: `--stuck-threshold 120` (2 minutes)
- **Avoid false alarms**: `--stuck-threshold 600` (10 minutes)
- **More frequent checks**: `--check-interval 10`

---

## ❓ FAQ

### Q: Do I need to enable checkpointing every time?

A: Yes, it's a per-training setting. But once enabled, it saves automatically every N epochs.

### Q: How much disk space do checkpoints use?

A: ~2-4 GB per checkpoint. A 16-epoch training with save every 4 epochs = ~8-16 GB total.

### Q: Can I delete old checkpoints?

A: Yes, but keep at least the last 2 in case one is corrupted. Checkpoints are in `<name>-state` folders.

### Q: What if I forgot to enable checkpointing?

A: You can only resume if checkpointing was enabled. Otherwise, you'll need to start over. Lesson: Always enable checkpointing for long training!

### Q: Does resume work across different GPUs?

A: Only if they have the same or more VRAM. Can't resume 20G training on 12G GPU.

### Q: Will monitoring slow down training?

A: No, the monitor runs separately and only checks GPU stats every 30 seconds. Zero impact on training speed.

### Q: Can I monitor multiple training runs?

A: Yes, run one monitor per training in separate terminals:
```bash
# Terminal 1
./train_with_monitoring.sh lora-1

# Terminal 2
./train_with_monitoring.sh lora-2
```

### Q: What if the monitor gives false alarms?

A: Increase the stuck threshold:
```bash
python training_monitor.py --output-dir outputs/my-lora --stuck-threshold 600
```

### Q: Can resume change results?

A: Resume should give nearly identical results if resuming from epoch boundaries. Tiny numerical differences may occur due to random states.

---

## 🐛 Troubleshooting

### "No state checkpoints found"

**Solution**: Enable checkpointing before starting training. It only saves if enabled.

### "Resume checkpoint not found"

**Solution**:
```bash
# Check what exists
python find_checkpoint.py outputs/my-lora --list

# Use exact path shown
```

### Monitor reports stuck but training is running

**Solution**: Increase threshold or check GPU usage manually:
```bash
nvidia-smi
# If GPU is actually idle, training is really stuck
```

### Out of memory after resume

**Solution**:
```bash
# Clear cache
rm -rf outputs/my-lora/cache

# Or resume on GPU with same VRAM
```

### Training doesn't continue from right epoch

**Solution**: Make sure you're using a `-state` directory, not a `.safetensors` file.

---

## 🚀 Best Practices

1. **✅ Always enable checkpointing** for training > 8 epochs
2. **✅ Use monitoring** for training > 4 hours
3. **✅ Keep last 2-3 checkpoints** for safety
4. **✅ Test resume** on small dataset first
5. **✅ Check disk space** before long training
6. **❌ Don't resume** on different GPU VRAM
7. **❌ Don't delete** all checkpoints until training complete

---

## 📊 Performance Impact

- **Checkpoint saving**: 10-30 seconds per epoch (depends on model size)
- **Monitoring overhead**: None (separate process, only checks GPU stats)
- **Disk I/O**: Brief spike when saving checkpoint
- **Resume time**: 30-60 seconds to load checkpoint

---

## 🔮 Planned Features

- [ ] Web UI for monitoring (see live status in browser)
- [ ] Automatic resume (no manual intervention needed)
- [ ] Email/Slack alerts when stuck
- [ ] Checkpoint compression (smaller disk usage)
- [ ] Cloud checkpoint sync (HuggingFace, S3)
- [ ] Multi-GPU support
- [ ] Automatic checkpoint pruning

---

## 📝 Summary

**What you get:**
- ✅ Training protection against stuck/crash
- ✅ Easy resume from any epoch
- ✅ Automatic stuck detection
- ✅ Process cleanup and recovery
- ✅ Comprehensive logging
- ✅ Zero configuration (good defaults)

**What you need to do:**
1. Check "Enable Checkpointing" in UI
2. Run `./train_with_monitoring.sh my-lora` in separate terminal
3. Relax - you're protected!

**Result:** No more losing hours of training to random stuck issues!

---

## 🔗 Links

- Main README: [README.md](README.md)
- Quick Recovery: [QUICK_RECOVERY_GUIDE.md](QUICK_RECOVERY_GUIDE.md)
- Full Guide: [CHECKPOINT_RESUME_GUIDE.md](CHECKPOINT_RESUME_GUIDE.md)
- Technical Details: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

---

## 💬 Feedback

Found a bug? Have suggestions? Please report issues with:
- FluxGym version
- GPU type and VRAM
- Training settings
- Monitor logs (`training_monitor.log`)
- Error messages

Happy training! 🚀
