# Runpod Template Configuration for fluxgymHardened

## Your Repository
**GitHub URL**: https://github.com/jaysep/fluxgymHardened

---

## Runpod Template Configuration

### Step 1: Create Template

Go to: https://www.runpod.io/console/user/templates

Click **"New Template"**

---

### Step 2: Template Settings

#### Basic Information

**Template Name**:
```
FluxGym Hardened
```

**Template Description**:
```
Production-ready FluxGym with comprehensive improvements:
- Hang prevention fixes (DataLoader timeout, block swap timeout, file I/O timeout)
- Automatic monitoring (detect stuck training, GPU=0% detection)
- State persistence (survives disconnects and refreshes)
- Training log persistence (view progress after reconnection)
- Success verification (prevents false positive completions)
- All fixes from https://github.com/jaysep/fluxgymHardened
```

---

#### Container Configuration

**Container Image**:
```
runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04
```
*Or use: `runpod/pytorch:2.1.1-py3.10-cuda12.1.0-devel-ubuntu22.04` for broader compatibility*

**Docker Command**: (Leave empty)

**Container Disk**:
```
100 GB
```

**Volume Mount Path**:
```
/workspace
```

---

#### Environment Variables

Click **"Add Environment Variable"** for each:

**Variable 1**:
- Name: `HF_HOME`
- Value: `/workspace/.cache/huggingface`

**Variable 2**:
- Name: `GRADIO_SERVER_NAME`
- Value: `0.0.0.0`

**Variable 3** (Optional - for better performance):
- Name: `PYTORCH_CUDA_ALLOC_CONF`
- Value: `max_split_size_mb:512`

---

#### Expose HTTP Ports

**HTTP Ports**:
```
7860
```

---

#### Start Script

**COPY AND PASTE THIS ENTIRE SCRIPT**:

```bash
#!/bin/bash
set -e

echo "================================================================"
echo "   FluxGym Hardened - Automatic Setup"
echo "   Repository: https://github.com/jaysep/fluxgymHardened"
echo "================================================================"

# Install FluxGym dependencies (cached after first run)
echo "[1/4] Installing Python dependencies..."
pip install -q --no-cache-dir \
    gradio_logsview@https://huggingface.co/spaces/cocktailpeanut/gradio_logsview/resolve/main/gradio_logsview-0.0.17-py3-none-any.whl \
    python-slugify \
    transformers \
    accelerate \
    peft \
    lycoris-lora==1.8.3 \
    toml \
    safetensors

echo "[2/4] Setting up FluxGym..."
cd /workspace

# Clone or update repository
if [ ! -d "fluxgym" ]; then
    echo "Cloning fluxgymHardened from GitHub..."
    git clone --depth 1 https://github.com/jaysep/fluxgymHardened.git fluxgym
    echo "✓ Repository cloned"
else
    echo "Updating existing installation..."
    cd fluxgym
    git pull
    cd ..
    echo "✓ Repository updated"
fi

echo "[3/4] Starting FluxGym..."
cd /workspace/fluxgym

# Start FluxGym in background
nohup python app.py > fluxgym.log 2>&1 &
FLUXGYM_PID=$!
echo $FLUXGYM_PID > fluxgym.pid

# Wait a moment for startup
sleep 3

# Check if process is running
if ps -p $FLUXGYM_PID > /dev/null; then
    echo "✓ FluxGym started successfully (PID: $FLUXGYM_PID)"
else
    echo "✗ FluxGym failed to start. Check logs:"
    tail -n 20 fluxgym.log
    exit 1
fi

echo "[4/4] Ready!"
echo "================================================================"
echo "   FluxGym Hardened is running!"
echo "================================================================"
echo ""
echo "Access FluxGym UI:"
echo "  → Click 'Connect' → 'HTTP Service [Port 7860]' in Runpod"
echo ""
echo "Logs:"
echo "  → tail -f /workspace/fluxgym/fluxgym.log"
echo ""
echo "Features enabled:"
echo "  ✓ Hang prevention (timeout fixes)"
echo "  ✓ Automatic monitoring (GPU stuck detection)"
echo "  ✓ State persistence (survives disconnects)"
echo "  ✓ Training log persistence (view after refresh)"
echo "  ✓ Success verification (no false positives)"
echo ""
echo "Documentation: /workspace/fluxgym/*.md"
echo "================================================================"

# Keep container running and show logs
tail -f /workspace/fluxgym/fluxgym.log
```

---

### Step 3: Advanced Settings (Optional)

**Category**: `AI Training` or `Stable Diffusion`

**README** (Optional - for public templates):
```markdown
# FluxGym Hardened

Production-ready FLUX LoRA training with comprehensive improvements.

## Features

- **Hang Prevention**: Timeout fixes for DataLoader, block swap, file I/O
- **Automatic Monitoring**: Detects stuck training (GPU=0% for 5+ minutes)
- **State Persistence**: Survives disconnects, page refreshes
- **Training Log Persistence**: View logs after reconnection
- **Success Verification**: Accurate completion/failure detection
- **Cloud-Ready**: Optimized for Runpod, Vast.ai, Lambda Labs

## Quick Start

1. Select GPU (24GB VRAM recommended)
2. Deploy pod
3. Wait ~1 minute for automatic setup
4. Access FluxGym on port 7860
5. Start training!

## Documentation

All guides included in `/workspace/fluxgym/*.md`:
- Quick start guides
- Cloud deployment
- Checkpoint/resume
- Troubleshooting

## Repository

https://github.com/jaysep/fluxgymHardened

All improvements, fixes, and documentation available on GitHub.
```

---

### Step 4: Save Template

Click **"Create"** or **"Save Template"**

---

## Using Your Template

### Deploy a Pod

1. Go to: https://www.runpod.io/console/gpu-cloud
2. Click **"New Pod"**
3. Filter templates → Find **"FluxGym Hardened"**
4. Select GPU:
   - **Budget**: RTX 4090 (24GB) - $0.69/hr
   - **Best Value**: RTX A5000 (24GB) - $0.79/hr
   - **Performance**: A6000 (48GB) - $1.29/hr
5. Set disk: **100GB** minimum
6. Click **"Deploy On-Demand"** or **"Rent"**

### Access FluxGym

**Wait ~1 minute for startup**, then:

1. In Runpod pod view, click **"Connect"**
2. Select **"HTTP Service [Port 7860]"**
3. FluxGym UI opens in browser
4. Start training!

### Check Logs (Optional)

```bash
# SSH to pod
ssh root@<pod-ip> -p <port>

# View FluxGym logs
tail -f /workspace/fluxgym/fluxgym.log

# Check if running
ps -p $(cat /workspace/fluxgym/fluxgym.pid)
```

---

## Startup Timeline

### First Pod Start (Cold)

```
0:00 - Container starts (PyTorch image)
0:10 - Startup script begins
0:15 - Installing dependencies...
0:45 - Cloning GitHub repo (64MB)...
0:50 - Starting FluxGym...
0:55 - Ready! ✓
```

**Total: ~55 seconds**

### Subsequent Starts (Warm)

```
0:00 - Container starts
0:10 - Startup script begins
0:12 - Dependencies cached (skip)
0:14 - Git pull updates...
0:16 - Starting FluxGym...
0:20 - Ready! ✓
```

**Total: ~20 seconds**

---

## Updating FluxGym

### Push Updates to GitHub

```bash
# On your local machine
cd /path/to/fluxgymHardened

# Make improvements
# ... edit files ...

# Commit and push
git add .
git commit -m "Improve monitoring threshold"
git push
```

### Get Updates on Runpod

**Automatic** (next pod start):
- Startup script runs `git pull`
- Gets latest changes automatically

**Manual** (running pod):
```bash
# SSH to pod
cd /workspace/fluxgym
git pull

# Restart FluxGym
kill $(cat fluxgym.pid)
nohup python app.py > fluxgym.log 2>&1 &
echo $! > fluxgym.pid
```

---

## Making Template Public (Optional)

### Share with Community

1. Go to your template in Runpod
2. Click **"Settings"**
3. Toggle **"Public Template"**
4. Get shareable URL

**Template URL will be**:
```
https://runpod.io/console/hub/templates/<template-id>
```

Share this link and others can deploy your hardened FluxGym instantly!

---

## Template Verification

### Test Checklist

After creating template, verify:

- [ ] Pod starts successfully
- [ ] FluxGym accessible on port 7860
- [ ] Can upload images
- [ ] Training starts
- [ ] Monitoring works (check logs)
- [ ] State persistence (refresh page)
- [ ] Training log shows (check accordion)
- [ ] Success/failure detection works
- [ ] All documentation accessible in `/workspace/fluxgym/`

---

## Troubleshooting

### "git: command not found"

**Fix**: Update container image to one with git pre-installed, or add to startup script:
```bash
apt-get update && apt-get install -y git
```

### "Port 7860 not accessible"

**Check**:
1. Port 7860 listed in "Expose HTTP Ports"
2. Use Runpod's "HTTP Service" link (not direct IP)
3. Check firewall settings in template

### "FluxGym not starting"

**Debug**:
```bash
# View logs
cat /workspace/fluxgym/fluxgym.log

# Check process
ps aux | grep python

# Check port
netstat -tulpn | grep 7860

# Try manual start
cd /workspace/fluxgym
python app.py
```

### "Dependencies install fails"

**Cause**: Network issues or PyTorch version mismatch

**Fix**: Try alternative base image:
```
runpod/pytorch:2.1.1-py3.10-cuda12.1.0-devel-ubuntu22.04
```

---

## Cost Optimization

### Pod Selection

**Training 16 epochs on RTX 4090**:
```
GPU: RTX 4090 24GB
Rate: $0.69/hr
Time: ~2 hours
Cost: ~$1.38 per LoRA
```

**With monitoring enabled**:
- Auto-detects hangs
- Kills stuck training
- Saves money by not wasting hours on hung processes

### Network Volume (Optional)

**For regular use**:
```
Create network volume: 100GB
Cost: $10/month
Benefit: Models persist (no re-download)
Break-even: ~13 pod sessions/month
```

**Recommendation**: Use ephemeral for occasional use, volume for heavy use

---

## Features Included

### From fluxgymHardened Repository

✅ **Hang Prevention**:
- DataLoader timeout (60s)
- Block swap timeout (30s)
- File I/O timeout (30s)
- No blocks_to_swap (disabled)

✅ **Monitoring**:
- GPU usage tracking (every 30s)
- Stuck detection (GPU<5% for 5min)
- Auto-kill stuck processes
- Checkpoint path logging

✅ **State Persistence**:
- UI state auto-save
- Active sessions display
- Configuration restore
- Status tracking (completed/failed/running)

✅ **Training Logs**:
- Persistent log files
- Auto-refresh every 5s
- Last 100 lines display
- Success/failure markers

✅ **Success Verification**:
- Model file check
- Exception handling
- Clear status indicators
- No false positive completions

✅ **Documentation**:
- 15+ comprehensive guides
- Quick start references
- Troubleshooting help
- Cloud deployment guides

---

## Next Steps

### 1. Create Template

Use the configuration above to create your Runpod template.

### 2. Test It

Deploy a test pod, verify everything works.

### 3. Train!

Start training LoRAs with all improvements active.

### 4. Share (Optional)

Make template public, help the community benefit from your improvements!

---

## Support

### Documentation

All guides in `/workspace/fluxgym/`:
- `README_COMPLETE_UPDATE.md` - Overview
- `RUNPOD_MINIMAL_DEPLOYMENT.md` - Deployment
- `TRAINING_SUCCESS_VERIFICATION.md` - Status verification
- `SD_SCRIPTS_HANG_ANALYSIS.md` - Technical details
- Plus 10+ more guides

### Repository

Issues, updates, contributions:
https://github.com/jaysep/fluxgymHardened

---

**Your FluxGym Hardened template is ready to deploy!** 🚀

**Template Link** (after creation):
```
https://runpod.io/console/hub/templates/<your-template-id>
```

Share this link and anyone can deploy your production-ready FluxGym instantly!
