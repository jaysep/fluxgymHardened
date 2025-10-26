# FluxGym Hardened - Quick Reference

## Repository

**GitHub**: https://github.com/jaysep/fluxgymHardened

---

## What's Been Improved

✅ **Hang Prevention**
- Disabled `blocks_to_swap` (critical deadlock fix)
- DataLoader timeout (60s)
- Block swap timeout (30s)
- File I/O timeout (30s)

✅ **Automatic Monitoring**
- Detects stuck training (GPU < 5% for 5+ minutes)
- Auto-kills stuck processes
- Logs checkpoint path for resume

✅ **State Persistence**
- UI saves complete configuration
- Survives disconnects and page refreshes
- Shows active training sessions

✅ **Training Log Persistence**
- Dual logging: streaming + file-based
- View logs after reconnection
- Auto-refresh every 5s

✅ **Success Verification**
- Model file existence check
- Exception handling
- Status tracking (completed/failed)
- Clear UI indicators (✅/❌)

✅ **Cloud-Ready**
- Processes detach from terminal
- Survive SSH disconnects
- nohup compatible

✅ **Development Tools**
- VS Code Server (browser-based editor)
- Built-in terminal access
- Full file editing capabilities
- Git integration
- No password required

---

## Quick Start (Local)

```bash
# Install dependencies
pip install -r requirements.txt

# Start FluxGym
python app.py

# Access UI at http://localhost:7860
```

---

## Quick Start (Runpod)

### Method 1: Use Your Template

1. **Create Template** (one-time setup):
   - Go to: https://www.runpod.io/console/user/templates
   - Click "New Template"
   - Copy settings from `RUNPOD_TEMPLATE_FOR_JAYSEP.md`
   - Save template

2. **Deploy Pod**:
   - Select your "FluxGym Hardened" template
   - Choose GPU (24GB recommended)
   - Deploy
   - Wait ~1 minute for startup
   - Click "Connect" → "HTTP Service [Port 7860]" (FluxGym UI)
   - Click "Connect" → "HTTP Service [Port 8888]" (VS Code)

### Method 2: Minimal Manual Setup

```bash
# SSH to Runpod pod with PyTorch template
ssh root@<pod-ip> -p <port>

# One-liner install
pip install -q gradio_logsview@https://huggingface.co/spaces/cocktailpeanut/gradio_logsview/resolve/main/gradio_logsview-0.0.17-py3-none-any.whl python-slugify peft lycoris-lora toml && cd /workspace && git clone https://github.com/jaysep/fluxgymHardened.git fluxgym && cd fluxgym && nohup python app.py > fluxgym.log 2>&1 & echo $! > fluxgym.pid && echo "FluxGym ready on port 7860!"
```

---

## Training Workflow

### 1. Start Training

```
1. Upload images (12-20 recommended)
2. Set LoRA name
3. Write concept sentence
4. ✅ Enable Checkpointing (ON by default)
5. ✅ Enable Auto-Monitoring (ON by default)
6. Click "Start training"
7. Disconnect if needed - everything keeps running!
```

### 2. Monitor Progress

**If connected**:
- Training log streams in real-time
- Sample images appear in gallery

**If disconnected and reconnected**:
- Refresh page
- See "🔄 Active Training Sessions" banner
- Shows 🟢 Running / ✅ Completed / ❌ Failed / 🔵 Stopped
- Training log shows last 100 lines (auto-refreshes)

### 3. Handle Issues

**Training stuck (GPU = 0%)**:
- Monitor auto-detects after 5 minutes
- Kills stuck processes
- Check `outputs/<lora>/monitor.log` for checkpoint path
- Resume training with checkpoint path

**UI disconnected**:
- Refresh page
- All state preserved
- Training continues in background

**Training failed**:
- Status shows ❌ Failed
- Error message displayed
- Check training log for details

---

## File Structure

```
outputs/my-lora/
├── ui_state.json          # UI configuration (auto-saved)
├── training.log           # Training logs (persistent)
├── monitor.pid            # Monitor process ID
├── monitor.log            # Monitor activity log
├── my-lora-8-state/       # Checkpoint at epoch 8
├── my-lora.safetensors    # Final trained model
└── sample/                # Generated sample images
```

---

## Using VS Code (Runpod)

### Access VS Code

1. In Runpod pod view, click **"Connect"**
2. Select **"HTTP Service [Port 8888]"**
3. VS Code opens in browser (no password)

### What You Can Do

**Edit Files**:
- Click Explorer (left sidebar)
- Browse to /workspace/fluxgym
- Edit app.py, config files, documentation
- Changes saved automatically

**Run Commands**:
- Open Terminal (Menu → Terminal → New Terminal)
- Full shell access
- Run any command (python, pip, git, etc.)

**View Logs in Real-Time**:
- Open training.log or fluxgym.log in editor
- Logs update live as training progresses

**Git Integration**:
- Make changes to files
- View changes in Source Control panel
- Commit and push to your repository

**Common Tasks**:
```bash
# In VS Code terminal

# View running processes
ps aux | grep python

# Restart FluxGym
kill $(cat fluxgym.pid)
nohup python app.py > fluxgym.log 2>&1 &

# Update from GitHub
git pull

# Install new dependencies
pip install some-package

# Check GPU status
nvidia-smi
```

---

## Common Commands

```bash
# Check if FluxGym is running
ps -p $(cat fluxgym.pid)

# View FluxGym logs
tail -f fluxgym.log

# View training log
tail -f outputs/my-lora/training.log

# View monitor log
tail -f outputs/my-lora/monitor.log

# Check training status
cat outputs/my-lora/ui_state.json | grep status

# Find checkpoints
python find_checkpoint.py outputs/my-lora

# Stop everything (if needed)
kill $(cat fluxgym.pid)
kill $(cat outputs/my-lora/monitor.pid)
pkill -9 -f "flux_train_network"
```

---

## GPU Configurations

### 12GB VRAM
```
Config: 12G
Optimizer: Adafactor
split_mode: Enabled
train_blocks: single
Sampling: Disabled (save VRAM)
```

### 16GB VRAM (Recommended)
```
Config: 16G
Optimizer: Adafactor
Sampling: Enabled
Best balance of speed and features
```

### 24GB+ VRAM (Best)
```
Config: 20G
Optimizer: AdamW8bit
Full features enabled
Fastest training
```

---

## Documentation Map

**Quick Starts**:
- `README_COMPLETE_UPDATE.md` - Main overview
- `QUICK_START_CLOUD.md` - 30-second cloud setup
- `QUICK_RECOVERY_GUIDE.md` - Emergency recovery

**Runpod Deployment**:
- `RUNPOD_TEMPLATE_FOR_JAYSEP.md` - Your custom template (USE THIS!)
- `RUNPOD_TEMPLATE_CREATION.md` - Template creation guide
- `RUNPOD_MINIMAL_DEPLOYMENT.md` - Skip 6GB containers

**Features**:
- `STATE_PERSISTENCE_GUIDE.md` - How UI state works
- `CHECKPOINT_RESUME_GUIDE.md` - Checkpoint system
- `TRAINING_LOG_PERSISTENCE.md` - Log persistence
- `TRAINING_SUCCESS_VERIFICATION.md` - Success detection

**Technical**:
- `SD_SCRIPTS_HANG_ANALYSIS.md` - Root cause analysis
- `HANG_FIXES_IMPLEMENTED.md` - All fixes explained
- `HUGGINGFACE_TOKEN_EXPLAINED.md` - When you need HF token
- `FINAL_UPDATE_SUMMARY.md` - Complete changelog

---

## Troubleshooting

### "Training stuck at GPU 0%"
**Auto-detected**: Monitor will kill and log checkpoint path after 5 minutes.
**Manual**: Kill processes, resume from checkpoint.

### "UI shows blank after refresh"
**Check**: Active Training Sessions banner should show your training.
**Fix**: Ensure `outputs/<lora>/ui_state.json` exists.

### "Training shows ✅ Complete but no model file"
**Fixed**: Success verification prevents this - will show ❌ Failed instead.

### "Monitor not running"
**Check**: `cat outputs/<lora>/monitor.pid`
**Fix**: Enable Auto-Monitoring checkbox before training.

### "Can't access port 7860 on Runpod"
**Fix**: Use Runpod's "HTTP Service [Port 7860]" link, not direct IP.

---

## Cost Optimization (Runpod)

### Recommended Setup

**GPU**: RTX 4090 (24GB) @ $0.69/hr
**Training time**: ~2 hours for 16 epochs
**Cost per LoRA**: ~$1.38

**With monitoring**: Auto-kills stuck training → saves money

### Storage Options

**Ephemeral (Default)**:
- Free storage
- Models re-download each pod
- Best for occasional use

**Network Volume**:
- $10/month (100GB)
- Models persist
- Best for regular use (13+ sessions/month)

---

## Support

**Issues**: https://github.com/jaysep/fluxgymHardened/issues

**All guides included**: Check `*.md` files for detailed documentation

---

## Next Steps

1. **Create Runpod template** using `RUNPOD_TEMPLATE_FOR_JAYSEP.md`
2. **Deploy test pod** to verify setup
3. **Train your first LoRA** with all improvements active
4. **Share template** (optional) - help the community!

---

**Your FluxGym Hardened is production-ready!** 🚀

All improvements active by default. Just enable the two checkboxes and train!
