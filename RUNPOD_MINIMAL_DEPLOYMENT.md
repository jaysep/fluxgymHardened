# Runpod Minimal Deployment Guide

## TL;DR - Skip the 5-6GB Container!

**Yes, you can skip those massive containers!** FluxGym code is only **64MB** including sd-scripts. The bloat comes from base images and redundant dependencies.

---

## Container Bloat Analysis

### What's in Those 5-6GB Containers?

Looking at the Dockerfile:

```dockerfile
FROM nvidia/cuda:12.2.2-base-ubuntu22.04  # ~2-3GB base image
RUN git clone sd-scripts && pip install   # ~1GB PyTorch deps
RUN pip install torch torchvision...      # ~2-3GB PyTorch wheels
```

**Breakdown**:
- NVIDIA CUDA base: **~2-3GB**
- PyTorch + dependencies: **~2-3GB**
- FluxGym + sd-scripts: **~64MB** ← Actual code!

**95% is redundant** if you're using Runpod's pre-built templates!

---

## What You Actually Need

### Core Requirements

1. **Python 3.10+** ✅ (Runpod templates have this)
2. **CUDA 12.1+** ✅ (Runpod GPUs have this)
3. **PyTorch 2.0+** ✅ (Most Runpod templates include)
4. **FluxGym code** (64MB - just copy files!)

### That's It!

Runpod's PyTorch templates already have everything except FluxGym itself.

---

## Recommended Runpod Deployment Methods

### **Method 1: Direct File Copy (Fastest - 2 minutes)**

Perfect for quick testing or one-off training runs.

#### Step 1: Choose Runpod Template

Use any of these pre-built templates:
- **PyTorch 2.4** (Recommended)
- **RunPod PyTorch**
- **Stable Diffusion**
- **ComfyUI** (has all deps)

**DO NOT** use "Build your own" - it's slower and unnecessary!

#### Step 2: Start Pod

```
1. Select template: "PyTorch 2.4"
2. Select GPU: RTX 4090 / A5000 / A6000 (24GB VRAM recommended)
3. Disk: 50GB minimum (for models)
4. Start pod
```

#### Step 3: SSH to Pod

```bash
ssh root@<pod-ip> -p <port>
# Credentials shown in Runpod UI
```

#### Step 4: Install FluxGym (2 minutes)

```bash
# Install FluxGym dependencies
pip install gradio_logsview@https://huggingface.co/spaces/cocktailpeanut/gradio_logsview/resolve/main/gradio_logsview-0.0.17-py3-none-any.whl
pip install python-slugify transformers accelerate peft lycoris-lora toml safetensors

# Clone FluxGym (or upload via SCP)
cd /workspace
git clone https://github.com/cocktailpeanut/fluxgym
cd fluxgym

# OR upload your local copy with all fixes:
# From your machine: scp -r -P <port> /path/to/fluxgym root@<pod-ip>:/workspace/
```

#### Step 5: Start FluxGym

```bash
cd /workspace/fluxgym
nohup python app.py > fluxgym.log 2>&1 &
echo $! > fluxgym.pid
```

#### Step 6: Access UI

```
1. In Runpod, click "Connect" → "HTTP Service [Port 7860]"
2. Opens FluxGym UI
3. Start training!
```

**Total time: ~2 minutes**

---

### **Method 2: Startup Script (Automated - 1 minute)**

For pods you'll use repeatedly.

#### Create Startup Script

In Runpod template settings:

```bash
#!/bin/bash

# Install FluxGym dependencies (cached after first run)
pip install -q gradio_logsview@https://huggingface.co/spaces/cocktailpeanut/gradio_logsview/resolve/main/gradio_logsview-0.0.17-py3-none-any.whl python-slugify transformers accelerate peft lycoris-lora toml safetensors

# Clone/update FluxGym
cd /workspace
if [ ! -d "fluxgym" ]; then
    git clone https://github.com/cocktailpeanut/fluxgym
else
    cd fluxgym && git pull && cd ..
fi

# Start FluxGym
cd /workspace/fluxgym
nohup python app.py > fluxgym.log 2>&1 &
echo $! > fluxgym.pid

echo "FluxGym started! Access via HTTP Service [Port 7860]"
```

#### Benefits

- Runs on pod start automatically
- No manual setup needed
- FluxGym ready in ~1 minute

---

### **Method 3: Custom Template (Reusable - 0 minutes)**

Create once, reuse forever.

#### Step 1: Set Up Once

```bash
# SSH to pod
ssh root@<pod-ip> -p <port>

# Install everything
pip install gradio_logsview@https://huggingface.co/spaces/cocktailpeanut/gradio_logsview/resolve/main/gradio_logsview-0.0.17-py3-none-any.whl python-slugify transformers accelerate peft lycoris-lora toml safetensors

cd /workspace
git clone https://github.com/cocktailpeanut/fluxgym
```

#### Step 2: Save as Template

```
1. In Runpod, click "Save Template"
2. Name: "FluxGym Ready"
3. Save
```

#### Step 3: Use Forever

```
1. Select "FluxGym Ready" template
2. Start pod
3. SSH and run: cd /workspace/fluxgym && nohup python app.py > fluxgym.log 2>&1 &
4. Done!
```

---

## Pre-Download Models (Optional)

To avoid downloading FLUX models on each pod:

### Option A: Volume Storage

```bash
# Create network volume in Runpod (costs ~$0.10/GB/month)
# Mount to /workspace/models

# Download models once:
cd /workspace/fluxgym
python -c "
from library import huggingface_util
# Downloads happen to models/ folder
"
```

### Option B: Download Per Pod

```bash
# Models download automatically on first training
# Takes ~5-10 minutes for FLUX-dev (12GB)
# Cached on pod disk, no re-download within pod lifetime
```

**Recommendation**: Let FluxGym download models automatically. Only use volume if you're running many pods.

---

## Disk Space Requirements

| Component | Size | Notes |
|-----------|------|-------|
| FluxGym code | 64MB | Tiny! |
| FLUX-dev model | ~12GB | Auto-downloaded |
| CLIP models | ~500MB | Auto-downloaded |
| T5XXL model | ~8GB | Auto-downloaded |
| VAE model | ~300MB | Auto-downloaded |
| Training data | Varies | Your images |
| Outputs | ~500MB/LoRA | Your trained models |
| **Total minimum** | **~50GB** | Safe starting point |

**Runpod recommendation**: 50GB disk minimum

---

## Network Usage

### First Launch (Downloads)

- FLUX-dev: ~12GB
- T5XXL: ~8GB
- CLIP: ~500MB
- Total: **~21GB one-time download**

### Subsequent Launches

- FluxGym code: ~64MB (if pulling from GitHub)
- Models: 0GB (cached)
- Total: **~64MB** or **0MB** if using saved template

---

## Cost Comparison

### Method 1: Pre-built Container (Old Way)

```
Download container: 5-6GB (~10 minutes on Runpod)
Start container: ~2 minutes
Total startup: ~12 minutes
Pod cost while downloading: ~$0.10 (for 12 minutes)
```

### Method 2: Minimal Deployment (New Way)

```
Install dependencies: ~30 seconds (cached after first)
Clone FluxGym: ~5 seconds (64MB)
Start FluxGym: ~1 second
Total startup: ~40 seconds
Pod cost while downloading: ~$0.01 (for 40 seconds)
```

**Savings**: 10x faster, 10x cheaper!

---

## Recommended Runpod Templates

### Best Choice: PyTorch 2.4

```
Base: PyTorch 2.4 + CUDA 12.1
Pre-installed: torch, transformers, accelerate
Size: ~8GB (but already on Runpod servers, instant start)
Missing: Just FluxGym-specific deps (install in ~30s)
```

**Why**: Has 90% of what you need, starts instantly

### Alternative: Stable Diffusion / ComfyUI Templates

```
Base: SD WebUI or ComfyUI
Pre-installed: torch, transformers, diffusers, etc.
Size: ~10GB (instant start on Runpod)
Missing: gradio_logsview, python-slugify (install in ~10s)
```

**Why**: Has even more deps, but slightly heavier

### Avoid: Building Custom CUDA Image

```
Base: nvidia/cuda:12.2.2-base-ubuntu22.04
Pre-installed: Only CUDA
Missing: Everything (PyTorch, deps, etc.)
Build time: ~15-20 minutes
Download time: ~10 minutes
```

**Why**: Wastes time and money rebuilding what Runpod already has

---

## Complete Minimal Setup Script

Save this as `setup_fluxgym.sh`:

```bash
#!/bin/bash
set -e

echo "=== FluxGym Minimal Setup for Runpod ==="

# Install FluxGym-specific dependencies
echo "Installing dependencies..."
pip install -q \
    gradio_logsview@https://huggingface.co/spaces/cocktailpeanut/gradio_logsview/resolve/main/gradio_logsview-0.0.17-py3-none-any.whl \
    python-slugify \
    peft \
    lycoris-lora \
    toml

# Clone or update FluxGym
cd /workspace
if [ ! -d "fluxgym" ]; then
    echo "Cloning FluxGym..."
    git clone https://github.com/cocktailpeanut/fluxgym
else
    echo "Updating FluxGym..."
    cd fluxgym && git pull && cd ..
fi

# Apply your fixes (if you have local modifications)
# Uncomment if you want to upload your fixed version:
# echo "Uploading local fixes..."
# scp -r /local/path/to/fluxgym/* root@runpod:/workspace/fluxgym/

# Start FluxGym
cd /workspace/fluxgym
echo "Starting FluxGym..."
nohup python app.py > fluxgym.log 2>&1 &
echo $! > fluxgym.pid

echo "=== FluxGym Started! ==="
echo "PID: $(cat fluxgym.pid)"
echo "Access via Runpod 'HTTP Service [Port 7860]'"
echo "Logs: tail -f /workspace/fluxgym/fluxgym.log"
```

**Usage**:
```bash
chmod +x setup_fluxgym.sh
./setup_fluxgym.sh
```

---

## Troubleshooting

### "No module named 'gradio_logsview'"

```bash
# Install the specific wheel
pip install gradio_logsview@https://huggingface.co/spaces/cocktailpeanut/gradio_logsview/resolve/main/gradio_logsview-0.0.17-py3-none-any.whl
```

### "CUDA out of memory"

```
Choose GPU with more VRAM:
- 12GB VRAM: Use 12G config, disable sampling
- 16GB VRAM: Use 16G config (recommended)
- 24GB VRAM: Use 20G config (best)
```

### "Models not downloading"

```bash
# Set HuggingFace token (if using gated models)
export HF_TOKEN=your_token_here

# Or login
huggingface-cli login
```

### "Port 7860 not accessible"

```
1. Check Runpod firewall settings
2. Use Runpod's "HTTP Service [Port 7860]" link
3. Or use SSH tunnel: ssh -L 7860:localhost:7860 root@<pod-ip> -p <port>
```

---

## Uploading Your Fixed FluxGym Version

If you want to use your local version with all the fixes:

### Method 1: SCP Direct Upload

```bash
# From your local machine
cd /path/to/fluxgym
scp -r -P <runpod-ssh-port> . root@<pod-ip>:/workspace/fluxgym/

# Uploads 64MB in ~10 seconds on decent connection
```

### Method 2: Git Repository

```bash
# Push your version to GitHub
git init
git add .
git commit -m "FluxGym with hang fixes"
git remote add origin https://github.com/yourusername/fluxgym-fixed
git push -u origin main

# On Runpod:
git clone https://github.com/yourusername/fluxgym-fixed /workspace/fluxgym
```

### Method 3: Zip Upload via Runpod UI

```bash
# On local machine
cd /path/to/fluxgym
zip -r fluxgym.zip .

# Upload via Runpod web terminal file manager
# Extract: unzip fluxgym.zip -d /workspace/fluxgym
```

---

## Performance Comparison

| Deployment Method | Startup Time | Download Size | Pod Cost | Complexity |
|-------------------|--------------|---------------|----------|------------|
| **Docker Container** | ~12 minutes | 5-6GB | ~$0.10 | Medium |
| **Minimal Direct** | ~40 seconds | 64MB | ~$0.01 | Low |
| **With Startup Script** | ~1 minute | 64MB | ~$0.02 | Low |
| **Saved Template** | ~10 seconds | 0MB | ~$0.00 | Very Low |

---

## Best Practice Workflow

### For Testing / One-Off Training

```
1. Start PyTorch 2.4 template pod
2. Run minimal setup script (~1 minute)
3. Train
4. Download model
5. Terminate pod
```

### For Regular Use

```
1. Set up once with startup script
2. Save as custom template
3. Future: Just start template → training ready
4. No repeated setup!
```

### For Production / Multiple Projects

```
1. Create network volume for models
2. Create custom template with FluxGym
3. Mount volume on each pod
4. Models cached, instant start
5. Cost: ~$2/month for volume storage vs $0.10/pod startup
```

---

## Comparison: Container vs Minimal

### Using Pre-built Container (Docker)

**Pros**:
- Consistent environment
- Everything pre-installed
- Works offline (if cached)

**Cons**:
- 5-6GB download every time (unless cached)
- 10-15 minute startup
- Wastes Runpod storage
- Costs money during download
- Complex to modify

### Using Minimal Deployment

**Pros**:
- 64MB download (100x smaller!)
- 40 second startup (15x faster!)
- Minimal storage waste
- Nearly free startup cost
- Easy to modify and fix

**Cons**:
- Requires manual setup (once)
- Slightly more steps

**Verdict**: Minimal deployment is **clearly better** for Runpod!

---

## FAQ

### Q: Do I need Docker at all?

**A**: No! Runpod already runs containerized environments. You're just running Python directly in their pre-built containers.

### Q: Will this work on other cloud providers?

**A**: Yes! Same approach works on:
- Vast.ai
- Lambda Labs
- Paperspace
- Any cloud with PyTorch pre-installed

### Q: What about model downloads?

**A**: FluxGym auto-downloads models on first use. They're cached in `models/` folder. No manual download needed!

### Q: Can I use multiple pods simultaneously?

**A**: Yes! Each pod is independent. Just copy FluxGym to each or use network volume.

### Q: How do I update FluxGym?

**A**: Just `cd /workspace/fluxgym && git pull` or upload new files via SCP.

---

## Summary

**DO NOT use 5-6GB containers for Runpod!**

✅ **DO**: Use PyTorch template + copy FluxGym files (64MB)
✅ **DO**: Create startup script for automation
✅ **DO**: Save as custom template for reuse

**Result**:
- 100x smaller (64MB vs 6GB)
- 15x faster startup (40s vs 12min)
- 10x cheaper startup ($0.01 vs $0.10)
- Easier to modify and maintain
- All fixes included immediately

**You were right to question the bloat!** 🎯

---

## Quick Start Command

For the impatient:

```bash
# One-liner to install and start FluxGym on Runpod PyTorch template
pip install -q gradio_logsview@https://huggingface.co/spaces/cocktailpeanut/gradio_logsview/resolve/main/gradio_logsview-0.0.17-py3-none-any.whl python-slugify peft lycoris-lora toml && cd /workspace && git clone https://github.com/cocktailpeanut/fluxgym && cd fluxgym && nohup python app.py > fluxgym.log 2>&1 & echo $! > fluxgym.pid && echo "FluxGym ready on port 7860!"
```

Copy, paste, done! ✨
