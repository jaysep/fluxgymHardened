# FluxGym Checkpoint & Auto-Recovery Implementation Summary

## What Was Implemented

I've successfully implemented a comprehensive checkpoint and auto-recovery system for FluxGym to address the issue of training getting stuck with GPU usage dropping to zero.

---

## 🎯 Problem Solved

**Before**: Training would randomly get stuck mid-session with GPU at 0%. No easy way to resume, questionable state management.

**After**:
- ✅ Checkpointing enabled in UI (saves training state every N epochs)
- ✅ Resume functionality integrated into UI and training scripts
- ✅ Automatic monitoring script detects stuck training
- ✅ Auto-kill stuck processes with checkpoint recovery
- ✅ Helper scripts to find and manage checkpoints

---

## 📁 New Files Created

### 1. `training_monitor.py` - Main Monitoring & Recovery Script
- **Purpose**: Monitors GPU usage and detects stuck training
- **Features**:
  - Configurable check intervals and thresholds
  - Automatic process cleanup when stuck
  - Finds latest checkpoint for recovery
  - Optional auto-resume (experimental)
  - Detailed logging to file and console

**Usage**:
```bash
python training_monitor.py --output-dir outputs/my-lora
```

### 2. `find_checkpoint.py` - Checkpoint Discovery Helper
- **Purpose**: Quickly find latest checkpoints for resume
- **Features**:
  - Lists all available state and model checkpoints
  - Shows timestamps and file sizes
  - Provides exact resume commands
  - Supports filtering by type (state/model)

**Usage**:
```bash
python find_checkpoint.py outputs/my-lora --list
```

### 3. `CHECKPOINT_RESUME_GUIDE.md` - Comprehensive Documentation
- Complete guide to checkpoint and resume functionality
- Step-by-step recovery procedures
- Troubleshooting section
- Best practices
- Technical details about checkpoint structure
- Multiple usage examples

### 4. `QUICK_RECOVERY_GUIDE.md` - Emergency Quick Reference
- 30-second recovery procedure
- Common commands cheat sheet
- Quick setup instructions
- Minimal documentation for urgent situations

### 5. `IMPLEMENTATION_SUMMARY.md` - This File
- Overview of changes
- Testing instructions
- Migration notes

---

## 🔧 Modified Files

### `app.py` - Main Application

#### Changes Made:

1. **Added checkpoint/resume parameters to `gen_sh()` function**:
   - `enable_checkpointing` - Toggle to save training states
   - `resume_from_checkpoint` - Path to resume from

2. **Updated training script generation**:
   - Adds `--save_state` flag when checkpointing enabled
   - Adds `--resume <path>` flag when resuming
   - Properly integrated into bash/bat script generation

3. **Added UI components**:
   - Checkbox: "Enable Checkpointing (Save training state for resume)"
   - Text field: "Resume from Checkpoint"
   - Both appear in Step 1 (LoRA Info) section

4. **Updated `update()` function**:
   - Accepts new checkpoint/resume parameters
   - Passes them to `gen_sh()`

5. **Updated listeners array**:
   - Included new UI components for real-time script updates

6. **Updated `basic_args` set**:
   - Added 'save_state' and 'resume' to prevent them appearing in advanced options

#### Code Locations:
- Line 377-395: Modified `gen_sh()` function signature
- Line 397: Updated debug print
- Line 413-422: Added checkpoint and resume argument generation
- Line 470: Integrated resume args into training command
- Line 484: Integrated checkpoint args into training command
- Line 655-696: Modified `update()` function
- Line 949-950: Added UI components
- Line 765-766: Added to basic_args
- Line 1061-1081: Updated listeners array

---

## 🧪 How to Test

### Test 1: Checkpoint Creation

1. Start FluxGym: `python app.py`
2. In UI, check "Enable Checkpointing"
3. Start a short training run (2-3 epochs, small dataset)
4. After completion, verify checkpoint exists:
   ```bash
   python find_checkpoint.py outputs/<your-lora-name> --list
   ```
5. You should see `-state` directories

### Test 2: Resume Functionality

1. Start a training with checkpointing enabled
2. Manually kill it after a few epochs (Ctrl+C or kill process)
3. Find the checkpoint:
   ```bash
   python find_checkpoint.py outputs/<your-lora-name>
   ```
4. In FluxGym UI, enter the checkpoint path in "Resume from Checkpoint"
5. Start training again
6. Check logs - should show "resume training from local state"
7. Verify it continues from the correct epoch

### Test 3: Stuck Detection

1. Start a training run
2. In another terminal, start the monitor:
   ```bash
   python training_monitor.py --output-dir outputs/<your-lora-name> --stuck-threshold 60 --check-interval 10
   ```
3. Simulate stuck training by suspending the process:
   ```bash
   # Find the training process PID
   ps aux | grep flux_train_network
   # Suspend it (replace PID)
   kill -STOP <PID>
   ```
4. Wait 60 seconds - monitor should detect it as stuck
5. Monitor will kill the process and show recovery instructions
6. Verify checkpoint is found correctly

### Test 4: End-to-End Recovery

1. Start training with checkpointing enabled
2. Start monitor in background:
   ```bash
   python training_monitor.py --output-dir outputs/test-lora > monitor.log 2>&1 &
   ```
3. Simulate a crash (kill -9 on training process)
4. Check monitor detected it: `tail -f monitor.log`
5. Follow recovery instructions
6. Resume training via UI
7. Verify training continues correctly

---

## 📊 How It Works

### Checkpoint System

1. **During Training**:
   - When `enable_checkpointing` is checked, `--save_state` is added to training command
   - Kohya sd-scripts saves full training state every `save_every_n_epochs` (default: 4)
   - State includes: model weights, optimizer state, scheduler, random states

2. **State Storage**:
   ```
   outputs/my-lora/
   ├── my-lora-4-state/       # Epoch 4 checkpoint
   ├── my-lora-8-state/       # Epoch 8 checkpoint
   ├── my-lora-12-state/      # Epoch 12 checkpoint
   ├── my-lora.safetensors    # Final model
   └── sample/                # Sample images
   ```

3. **Resume Process**:
   - User enters checkpoint path in UI
   - `gen_sh()` adds `--resume <path>` to training command
   - Kohya sd-scripts `accelerate.load_state()` restores full state
   - Training continues from next epoch/step

### Monitoring System

1. **GPU Usage Tracking**:
   - Polls `nvidia-smi` every N seconds (default: 30)
   - Tracks GPU utilization percentage
   - Maintains history of measurements

2. **Stuck Detection**:
   - If GPU < threshold% (default: 5%) for duration (default: 300s)
   - Mark as "stuck"
   - Trigger recovery

3. **Recovery Process**:
   - Find all Python training processes
   - Send SIGKILL to terminate
   - Wait for cleanup
   - Find latest checkpoint
   - Display recovery instructions
   - (Optional) Auto-resume with edited script

---

## 🔍 Technical Details

### Checkpoint Format

FluxGym uses the standard Accelerate checkpoint format:
- `optimizer.bin` - Optimizer state (AdamW/AdaFactor)
- `scheduler.bin` - LR scheduler state
- `random_states_0.pkl` - PyTorch RNG states
- `scaler.pt` - Mixed precision scaler
- `custom_checkpoint_0.pkl` - Additional metadata

### Resume Compatibility

Checkpoints are compatible when:
- ✅ Same base model (flux-dev, flux-schnell, etc.)
- ✅ Same network architecture (network_dim, etc.)
- ✅ Same optimizer type
- ✅ Same PyTorch major version
- ⚠️ May have issues if changing VRAM settings
- ⚠️ May have issues if changing dataset

### Monitoring Accuracy

The monitor is accurate for:
- ✅ True stuck training (process alive but not using GPU)
- ✅ Crashed processes (GPU goes to 0%)
- ⚠️ May false-positive during:
  - Dataset loading phase (brief GPU idle)
  - Checkpoint saving (brief pause)
  - Sample image generation (brief pause)

Tune `--stuck-threshold` to avoid false positives.

---

## 🚀 Usage Recommendations

### For Normal Training

1. **Always enable checkpointing** for runs > 8 epochs
2. Set "Save every N epochs" to 4 (good balance)
3. Don't need monitoring for short runs

### For Long Training (>4 hours)

1. **Enable checkpointing**
2. **Run monitor in separate terminal**:
   ```bash
   python training_monitor.py --output-dir outputs/my-lora &
   ```
3. **Check logs periodically**:
   ```bash
   tail -f training_monitor.log
   ```

### For Overnight/Unattended Training

1. **Enable checkpointing**
2. **Run monitor with longer threshold**:
   ```bash
   python training_monitor.py \
     --output-dir outputs/my-lora \
     --stuck-threshold 600 \
     --check-interval 60 > monitor.log 2>&1 &
   ```
3. **Check in the morning**
4. **Resume if stuck**

### For High-Memory Training (Frequent OOMs)

1. **Checkpointing is critical** - saves progress before OOM
2. **Lower save_every_n_epochs to 2** - more frequent saves
3. **Clear cache before resume**:
   ```bash
   rm -rf outputs/my-lora/cache
   ```

---

## ⚠️ Known Limitations

1. **Auto-resume is experimental**
   - Currently requires manual script editing
   - Full automation planned for future

2. **Checkpoint size**
   - State dirs are large (several GB)
   - Consider disk space for long training

3. **False positives possible**
   - Monitor may trigger during legitimate pauses
   - Adjust thresholds as needed

4. **No cross-machine resume**
   - Checkpoints tied to specific hardware
   - Can resume on same machine only

5. **Memory requirements**
   - Resume needs same or more memory than original
   - Can't resume 20G training on 12G GPU

---

## 🔮 Future Enhancements

Potential improvements:
- [ ] Web UI integration for monitoring
- [ ] Automatic resume without manual editing
- [ ] Checkpoint compression
- [ ] HuggingFace checkpoint sync
- [ ] Email/webhook alerts on stuck detection
- [ ] Cross-GPU resume support
- [ ] Checkpoint pruning (keep last N)
- [ ] Training metrics tracking

---

## 📝 Migration Notes

### For Existing FluxGym Users

1. **No breaking changes** - existing training scripts work as before
2. **Optional features** - checkpointing is opt-in
3. **Backward compatible** - old outputs still work

### To Enable on Existing Project

1. Pull latest code
2. In next training run, check "Enable Checkpointing"
3. If you have old training to resume:
   - Can only resume if you previously used `--save_state`
   - Otherwise, must start fresh

### Upgrading Running Training

- **Cannot add checkpointing mid-training**
- **Must restart training with checkpointing enabled**
- **Can resume from any old checkpoint if it exists**

---

## 🐛 Debugging

### Check if checkpointing is enabled:

```bash
cat outputs/my-lora/train.sh | grep save_state
# Should show: --save_state \
```

### Check if resume is configured:

```bash
cat outputs/my-lora/train.sh | grep resume
# Should show: --resume "outputs/..." \
```

### Verify checkpoint contents:

```bash
ls -lh outputs/my-lora/my-lora-8-state/
# Should show: optimizer.bin, scheduler.bin, etc.
```

### Test monitor without training:

```bash
# Monitor will report "no training processes" but you can test GPU detection
python training_monitor.py --output-dir outputs/test --check-interval 5
```

### View detailed logs:

```bash
# Monitor logs
tail -f training_monitor.log

# Training logs
tail -f outputs/my-lora/train.log  # if you redirect output
```

---

## 📞 Support

If you encounter issues:
1. Check `CHECKPOINT_RESUME_GUIDE.md` for detailed troubleshooting
2. Verify checkpoints exist with `find_checkpoint.py`
3. Check logs for error messages
4. Test on small dataset first
5. Report bugs with logs and training config

---

## ✅ Summary

This implementation provides:
- ✅ Full checkpoint/resume support in UI
- ✅ Automatic stuck training detection
- ✅ Easy recovery process
- ✅ Comprehensive documentation
- ✅ Helper scripts for management
- ✅ Backward compatible

**Result**: You can now safely train overnight or for extended periods, knowing you can recover from stuck training and resume from checkpoints.
