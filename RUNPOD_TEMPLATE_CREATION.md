# Creating a Runpod Template from GitHub

## TL;DR - Yes, Just Push to GitHub!

**Correct!** If you push your FluxGym folder to a public GitHub repo, you can create a Runpod template that:
- ✅ Fetches everything automatically
- ✅ No SCP needed
- ✅ No manual file copying
- ✅ All your fixes included
- ✅ One-click deployment

---

## Step-by-Step Guide

### Step 1: Create GitHub Repository

#### Option A: GitHub Web UI

```
1. Go to https://github.com/new
2. Repository name: "fluxgym-fixed" (or whatever you want)
3. Description: "FluxGym with hang fixes and improvements"
4. Public: ✅ (Important for Runpod access)
5. Click "Create repository"
```

#### Option B: Command Line

```bash
# In your fluxgym folder
cd /Users/alpha/fluxgym

# Initialize git (if not already)
git init

# Add all files
git add .

# Commit
git commit -m "FluxGym with hang fixes, monitoring, and state persistence"

# Create repo on GitHub first, then:
git remote add origin https://github.com/YOUR_USERNAME/fluxgym-fixed.git
git branch -M main
git push -u origin main
```

---

### Step 2: Create Runpod Template

#### Go to Runpod Template Creation

```
https://www.runpod.io/console/serverless/user/templates
```

#### Configure Template

**Container Image**: Use PyTorch base
```
runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04
```
Or any PyTorch 2.x image from https://github.com/runpod/containers

**Docker Command** (Leave empty, we'll use startup script)

**Container Disk**: 50 GB minimum

**Volume Mount Path**: `/workspace` (standard)

**Environment Variables**:
```bash
# Optional: Set HF cache to workspace
HF_HOME=/workspace/.cache/huggingface
```

**Expose HTTP Ports**: `7860`

**Start Script**: This is the key part!

```bash
#!/bin/bash
set -e

echo "=== FluxGym Auto-Setup ==="

# Install dependencies (cached after first run)
echo "Installing Python dependencies..."
pip install -q --no-cache-dir \
    gradio_logsview@https://huggingface.co/spaces/cocktailpeanut/gradio_logsview/resolve/main/gradio_logsview-0.0.17-py3-none-any.whl \
    python-slugify \
    transformers \
    accelerate \
    peft \
    lycoris-lora==1.8.3 \
    toml \
    safetensors

# Clone or update FluxGym
cd /workspace
if [ ! -d "fluxgym" ]; then
    echo "Cloning FluxGym from GitHub..."
    git clone https://github.com/YOUR_USERNAME/fluxgym-fixed.git fluxgym
else
    echo "Updating FluxGym..."
    cd fluxgym
    git pull
    cd ..
fi

# Start FluxGym
cd /workspace/fluxgym
echo "Starting FluxGym on port 7860..."
nohup python app.py > fluxgym.log 2>&1 &
echo $! > fluxgym.pid

echo "=== FluxGym Ready! ==="
echo "Access via HTTP Service [Port 7860]"
echo "Logs: tail -f /workspace/fluxgym/fluxgym.log"
echo "PID: $(cat fluxgym.pid)"

# Keep container running
tail -f /workspace/fluxgym/fluxgym.log
```

**IMPORTANT**: Replace `YOUR_USERNAME/fluxgym-fixed` with your actual GitHub repo!

---

### Step 3: Save Template

```
1. Name: "FluxGym with Fixes"
2. Category: "AI Training"
3. Description: "FluxGym with hang fixes, monitoring, state persistence"
4. Click "Save Template"
```

---

### Step 4: Use Your Template

```
1. Go to Runpod Pods
2. Click "New Pod"
3. Select your template: "FluxGym with Fixes"
4. Choose GPU (24GB recommended)
5. Click "Deploy"
6. Wait ~1 minute for startup script
7. Click "Connect" → "HTTP Service [Port 7860]"
8. FluxGym UI opens - ready to train!
```

---

## What Happens Automatically

### First Pod Start (Cold Start)

```
1. Runpod starts PyTorch container (~10 seconds)
2. Startup script runs:
   - Installs Python deps (~30 seconds)
   - Clones your GitHub repo (~5 seconds)
   - Starts FluxGym (~5 seconds)
3. Total: ~50 seconds
4. FluxGym ready on port 7860
```

### Subsequent Starts (Warm Start)

```
1. Runpod starts container (~10 seconds)
2. Startup script runs:
   - Deps already cached (skip)
   - Git pull updates (~2 seconds)
   - Starts FluxGym (~5 seconds)
3. Total: ~20 seconds
4. FluxGym ready
```

---

## Benefits of GitHub Approach

### ✅ **No Manual File Transfer**
```
Before: SCP 64MB every time
After: Git clone/pull only changes
```

### ✅ **Version Control**
```bash
# Update your local FluxGym
cd /Users/alpha/fluxgym
# Make improvements
git add .
git commit -m "Add new feature"
git push

# Next pod start automatically gets updates!
```

### ✅ **Easy Sharing**
```
Share template URL with others
They get your exact setup
All fixes included
```

### ✅ **Rollback if Needed**
```bash
# In startup script or manually:
git checkout v1.0  # Specific version
git checkout main  # Latest
```

### ✅ **No SCP/Port Forwarding**
```
No need for:
- scp -r -P <port> files root@pod
- Finding SSH credentials
- Managing file permissions
```

---

## Alternative: Private Repository

If you don't want to make your repo public:

### Option 1: GitHub Personal Access Token

**In startup script**:
```bash
# Use token for private repo access
git clone https://YOUR_TOKEN@github.com/YOUR_USERNAME/fluxgym-private.git fluxgym
```

**Security**: Add token as Runpod environment variable (not in script!)

### Option 2: Runpod Network Volume

```bash
# First pod: Clone once to volume
git clone https://github.com/YOUR_USERNAME/fluxgym-fixed.git /workspace/fluxgym

# Subsequent pods: Mount same volume
# No re-download needed
```

---

## Optimized Startup Script

For faster starts, here's an optimized version:

```bash
#!/bin/bash
set -e

echo "=== FluxGym Auto-Setup ==="

# Install dependencies in parallel
pip install -q --no-cache-dir \
    gradio_logsview@https://huggingface.co/spaces/cocktailpeanut/gradio_logsview/resolve/main/gradio_logsview-0.0.17-py3-none-any.whl \
    python-slugify transformers accelerate peft lycoris-lora==1.8.3 toml safetensors &

PIP_PID=$!

# Clone/update FluxGym while pip installs
cd /workspace
if [ ! -d "fluxgym" ]; then
    git clone --depth 1 https://github.com/YOUR_USERNAME/fluxgym-fixed.git fluxgym
else
    cd fluxgym && git pull && cd ..
fi

# Wait for pip to finish
wait $PIP_PID

# Start FluxGym
cd /workspace/fluxgym
nohup python app.py > fluxgym.log 2>&1 &
echo $! > fluxgym.pid

echo "=== FluxGym Ready on Port 7860! ==="
tail -f fluxgym.log
```

**Improvements**:
- Pip install runs in background
- Git clone uses `--depth 1` (faster)
- Parallel execution saves ~15 seconds

---

## Template Configuration Best Practices

### Container Disk

```
Minimum: 50GB
Recommended: 100GB

Breakdown:
- Base image: ~8GB
- Models (FLUX, CLIP, T5): ~21GB
- Training data: 1-5GB
- Outputs: Variable
- Overhead: 10GB
```

### GPU Selection

```
12GB VRAM: ⚠️ Works but limited (use 12G config)
16GB VRAM: ✅ Good (RTX 4000, A4000)
20GB VRAM: ✅ Better (A5000)
24GB VRAM: ✅ Best (RTX 4090, A6000, L40)
```

### Volume vs Ephemeral

**Ephemeral (Default)**:
- ✅ Cheaper
- ✅ Fresh start each time
- ❌ Re-download models
- Best for: One-off training

**Network Volume**:
- ✅ Persistent models
- ✅ No re-download
- ❌ Costs $0.10/GB/month
- Best for: Regular use

---

## Testing Your Template

### Quick Test

```bash
# Start pod with your template
# SSH in
ssh root@<pod-ip> -p <port>

# Check if FluxGym is running
cat /workspace/fluxgym/fluxgym.pid
ps -p $(cat /workspace/fluxgym/fluxgym.pid)

# Check logs
tail /workspace/fluxgym/fluxgym.log

# Access UI
# Use Runpod's "HTTP Service [Port 7860]" link
```

### Full Test

```
1. Start pod from template
2. Access UI
3. Upload test images
4. Start training
5. Check monitoring works
6. Check state persistence (refresh page)
7. Check training log persistence
8. Verify success/failure detection
9. Download trained model
10. Stop pod
```

---

## Updating Your Template

### When You Make Changes

```bash
# Local machine
cd /Users/alpha/fluxgym
# Make changes
git add .
git commit -m "Fix bug X"
git push

# Next pod start: Automatically gets updates!
# Or on running pod:
cd /workspace/fluxgym
git pull
# Restart FluxGym
kill $(cat fluxgym.pid)
nohup python app.py > fluxgym.log 2>&1 &
echo $! > fluxgym.pid
```

### Versioned Deployments

**In startup script**:
```bash
# Option 1: Always latest
git clone https://github.com/YOUR_USERNAME/fluxgym-fixed.git fluxgym

# Option 2: Specific release
git clone --branch v1.0 https://github.com/YOUR_USERNAME/fluxgym-fixed.git fluxgym

# Option 3: Specific commit
git clone https://github.com/YOUR_USERNAME/fluxgym-fixed.git fluxgym
cd fluxgym
git checkout abc123  # Specific commit hash
```

---

## Sharing Your Template

### Make Public

```
1. In Runpod template settings
2. Toggle "Public"
3. Get shareable URL
4. Share with community!
```

### Documentation to Include

**In your GitHub README.md**:
```markdown
# FluxGym with Fixes

Production-ready FluxGym with:
- ✅ Hang fixes (no block swapping deadlocks)
- ✅ Monitoring (auto-detect stuck training)
- ✅ State persistence (survives disconnects)
- ✅ Training log persistence (view after refresh)
- ✅ Success verification (no false positives)

## Runpod Deployment

1. Click: [Deploy on Runpod](https://console.runpod.io/hub/template/YOUR_TEMPLATE_ID)
2. Choose GPU
3. Deploy
4. Access on port 7860
5. Train!

## Features

- Checkpoint/resume system
- Automatic monitoring
- Cloud-ready processes
- Complete documentation

See docs for details!
```

---

## Advanced: Multi-Environment Support

**Startup script with environment detection**:

```bash
#!/bin/bash
set -e

# Detect environment
if [ -f "/.dockerenv" ]; then
    echo "Running in Docker"
    WORKDIR="/workspace"
elif [ -f "/etc/runpod-release" ]; then
    echo "Running on Runpod"
    WORKDIR="/workspace"
else
    echo "Running locally"
    WORKDIR="$HOME"
fi

# Install deps
pip install -q gradio_logsview@... python-slugify transformers accelerate peft lycoris-lora toml safetensors

# Clone FluxGym
cd $WORKDIR
git clone https://github.com/YOUR_USERNAME/fluxgym-fixed.git fluxgym

# Start
cd fluxgym
python app.py
```

Works on: Runpod, Vast.ai, Lambda Labs, local Docker!

---

## Troubleshooting

### "git: command not found"

**Cause**: Base image doesn't have git

**Fix**: Add to startup script:
```bash
apt-get update && apt-get install -y git
```

### "Permission denied" on git clone

**Cause**: Private repo without credentials

**Fix**: Use public repo or add token:
```bash
git clone https://YOUR_TOKEN@github.com/user/repo.git
```

### "Port 7860 not accessible"

**Cause**: Firewall or wrong port mapping

**Fix**:
- Check template has `7860` in exposed ports
- Use Runpod's "HTTP Service" link (not direct IP)

### "FluxGym not starting"

**Check**:
```bash
# View logs
cat /workspace/fluxgym/fluxgym.log

# Check if process running
ps aux | grep python

# Check port
netstat -tulpn | grep 7860
```

---

## Cost Analysis

### Template Approach (GitHub)

```
Pod startup: 1 minute
Cost during startup: ~$0.02 (at $1.00/hr)
No additional transfer costs
Recurring: Free (git pull is fast)
```

### SCP Approach (Manual)

```
SCP upload: 2-5 minutes (64MB)
Cost during transfer: ~$0.05-$0.10
Manual effort: High
Recurring: Every time
```

**Savings**: ~$0.03-$0.08 per deployment + time saved!

---

## Example: Complete Template Config

**Template Name**: FluxGym Production Ready

**Container Image**:
```
runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04
```

**Container Disk**: 100GB

**Volume Mount**: /workspace

**Expose Ports**: 7860

**Environment Variables**:
```bash
HF_HOME=/workspace/.cache/huggingface
GRADIO_SERVER_NAME=0.0.0.0
```

**Docker Command**: (empty)

**Start Script**:
```bash
#!/bin/bash
set -e
pip install -q --no-cache-dir gradio_logsview@https://huggingface.co/spaces/cocktailpeanut/gradio_logsview/resolve/main/gradio_logsview-0.0.17-py3-none-any.whl python-slugify transformers accelerate peft lycoris-lora==1.8.3 toml safetensors &
cd /workspace
[ ! -d "fluxgym" ] && git clone --depth 1 https://github.com/YOUR_USERNAME/fluxgym-fixed.git fluxgym || (cd fluxgym && git pull && cd ..)
wait
cd /workspace/fluxgym
nohup python app.py > fluxgym.log 2>&1 &
echo $! > fluxgym.pid
echo "FluxGym ready on port 7860"
tail -f fluxgym.log
```

**Notes**:
```
Production-ready FluxGym with hang fixes, monitoring, state persistence.
All features included, no setup needed.
```

---

## Summary

**Your understanding is 100% correct!**

✅ Push to GitHub → Create Runpod template → One-click deployment
✅ No SCP needed
✅ No manual file copying
✅ All updates via git push
✅ Share template with anyone
✅ Works on any cloud (Runpod, Vast.ai, etc.)

**Steps**:
1. `git push` to GitHub
2. Create Runpod template with startup script
3. Start pod → FluxGym ready in 1 minute
4. Train!

**That's it!** 🚀

---

## Next Steps

### 1. Create GitHub Repo

```bash
cd /Users/alpha/fluxgym
git init
git add .
git commit -m "FluxGym with all fixes"
git remote add origin https://github.com/YOUR_USERNAME/fluxgym-fixed.git
git push -u origin main
```

### 2. Create Runpod Template

Use the startup script from this guide, replace `YOUR_USERNAME/fluxgym-fixed` with your repo.

### 3. Test It!

Start a pod, verify everything works.

### 4. Share!

Make template public, help the community! 🌟

---

**You got it exactly right - GitHub + Runpod template = Zero manual deployment!** ✨
