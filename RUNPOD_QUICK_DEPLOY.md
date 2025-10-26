# FluxGym Hardened - Runpod Quick Deploy Guide

**Last Updated:** Based on working Next Diffusion FluxGym template with exact version matching

---

## 1. Create Runpod Template

**URL:** https://www.runpod.io/console/user/templates

### Basic Settings

**Template Name:**
```
FluxGym Hardened
```

**Container Image:**
```
runpod/pytorch:2.1.1-py3.10-cuda12.1.0-devel-ubuntu22.04
```
**IMPORTANT:** Must use Python 3.10 (not 3.11) to match the working template.

**Container Disk:**
```
100 GB
```

**Volume Mount Path:**
```
/workspace
```

**Expose HTTP Ports:**
```
7860,8888
```

### Environment Variables

Add these three:

1. **HF_HOME** = `/workspace/.cache/huggingface`
2. **GRADIO_SERVER_NAME** = `0.0.0.0`
3. **PYTORCH_CUDA_ALLOC_CONF** = `max_split_size_mb:512` (optional)

### Docker Command / Container Start Command

**Copy this EXACTLY** (1398 characters):

```bash
bash -c '
cd /workspace
if [ ! -f "/usr/bin/code-server" ]; then curl -fsSL https://code-server.dev/install.sh | sh; fi
nohup code-server --bind-addr 0.0.0.0:8888 --auth none /workspace > code-server.log 2>&1 &
echo $! > code-server.pid
if [ ! -d "fluxgym" ]; then git clone --depth 1 https://github.com/jaysep/fluxgymHardened.git fluxgym; else cd fluxgym && git pull && cd ..; fi
cd fluxgym
python -m venv --system-site-packages env
source env/bin/activate
pip install -q --upgrade pip
pip install -q --no-cache-dir fastapi==0.116.1 starlette==0.47.2 uvicorn==0.35.0 httpcore==1.0.9 httpx==0.28.1 h11==0.16.0 anyio==4.9.0 certifi==2025.7.14 attrs==25.3.0 jsonschema==4.25.0 packaging==25.0 accelerate==0.33.0 transformers==4.44.0 bitsandbytes==0.46.1 safetensors==0.4.4 huggingface-hub==0.34.3 toml==0.10.2 einops==0.7.0 opencv-python==4.8.1.78 sentencepiece==0.2.0 rich==13.7.0 voluptuous==0.13.1 gradio==4.44.1 python-slugify==8.0.4 pyyaml==6.0.2 imagesize==1.4.1 peft==0.16.0 lycoris-lora==1.8.3 "gradio_logsview@https://huggingface.co/spaces/cocktailpeanut/gradio_logsview/resolve/main/gradio_logsview-0.0.17-py3-none-any.whl" && pip install -q --no-cache-dir "git+https://github.com/huggingface/diffusers.git@56d438727036b0918b30bbe3110c5fe1634ed19d"
export PYTHONWARNINGS="ignore"
nohup python3 app.py > fluxgym.log 2>&1 &
echo $! > fluxgym.pid
echo "FluxGym ready on port 7860, VS Code on port 8888"
tail -f fluxgym.log
'
```

**CRITICAL:** Make sure to include:
- Opening `bash -c '` at the start
- Closing `'` at the end
- All lines exactly as shown (no line breaks in the middle of commands)

---

## 2. Deploy Pod

**Recommended GPUs:**

- **Budget**: RTX 4090 24GB - ~$0.69/hr
- **Best Value**: RTX A5000 24GB - ~$0.79/hr
- **Performance**: A6000 48GB - ~$1.29/hr

**Disk**: 100GB minimum

---

## 3. Access Services

**Wait ~1-2 minutes for startup**, then:

### FluxGym UI (Training)
1. Click **"Connect"** → **"HTTP Service [Port 7860]"**
2. FluxGym interface opens
3. Start training!

### VS Code Server (Editor)
1. Click **"Connect"** → **"HTTP Service [Port 8888]"**
2. VS Code opens in browser
3. Edit files, use terminal, view logs

---

## 4. Verify Deployment

### Check Logs (SSH to pod)

```bash
# FluxGym logs
tail -f /workspace/fluxgym/fluxgym.log

# Should see:
# Running on local URL:  http://0.0.0.0:7860
# Running on public URL: https://...runpod.net/proxy/7860

# VS Code logs
tail -f /workspace/code-server.log

# Check processes
ps aux | grep python
ps aux | grep code-server
```

### Verify Package Versions

```bash
source /workspace/fluxgym/env/bin/activate
pip list | grep -E "fastapi|starlette|uvicorn|gradio"

# Should show:
# fastapi      0.116.1    ✓
# gradio       4.44.1     ✓
# starlette    0.47.2     ✓
# uvicorn      0.35.0     ✓
```

**If you see different versions (especially fastapi 0.120+, starlette 0.48+, uvicorn 0.38+), deployment will fail!**

---

## 5. Startup Timeline

**First start (cold):**
```
0:00 - Container starts
0:10 - Install code-server (~10-15s)
0:25 - Clone repo and create venv (~10s)
0:35 - Install all dependencies (~25-30s)
1:05 - Start FluxGym
1:10 - Ready! ✓
```

**Subsequent starts (warm):**
```
0:00 - Container starts
0:10 - code-server already installed (skip)
0:12 - Git pull updates
0:14 - Venv already exists (skip)
0:16 - Dependencies cached (skip or quick)
0:18 - Start FluxGym
0:22 - Ready! ✓
```

---

## Troubleshooting

### "TypeError: argument of type 'bool' is not iterable"

**Cause:** Wrong package versions (fastapi/starlette/uvicorn too new)

**Fix:** Make sure startup script uses exact versions:
- fastapi==0.116.1 (NOT 0.120.0)
- starlette==0.47.2 (NOT 0.48.0)
- uvicorn==0.35.0 (NOT 0.38.0)

### "ModuleNotFoundError: No module named 'torchvision'"

**Cause:** Venv not using `--system-site-packages`

**Fix:** Startup script has `python -m venv --system-site-packages env`

### "Port 7860 not accessible"

**Check:**
1. Wait 1-2 minutes for startup
2. Use Runpod's "HTTP Service" link (not direct IP)
3. Check `tail -f /workspace/fluxgym/fluxgym.log` for errors

### "pip install hanging"

**Cause:** Network timeout or package conflict

**Try:**
1. Stop pod
2. Restart pod (will retry installation)
3. Check logs: `tail -f /workspace/fluxgym/fluxgym.log`

### Manual restart

If FluxGym crashes or needs restart:

```bash
cd /workspace/fluxgym
source env/bin/activate
kill $(cat fluxgym.pid) 2>/dev/null
nohup python app.py > fluxgym.log 2>&1 &
echo $! > fluxgym.pid
tail -f fluxgym.log
```

---

## What's Included

**FluxGym Hardened Features:**
- ✓ Hang prevention (DataLoader timeout, block swap timeout, file I/O timeout)
- ✓ Automatic monitoring (GPU usage tracking, stuck detection)
- ✓ State persistence (survives disconnects and refreshes)
- ✓ Training log persistence (view logs after reconnection)
- ✓ Success verification (prevents false positive completions)
- ✓ VS Code Server (browser-based editor + terminal)
- ✓ All documentation in `/workspace/fluxgym/*.md`

**Deployment Features:**
- ✓ One-click deployment
- ✓ Automatic setup (~1 minute first start)
- ✓ Exact package versions (proven working)
- ✓ Virtual environment isolation
- ✓ Git pull updates on restart

---

## Next Steps

1. **Create template** using settings above
2. **Deploy pod** with recommended GPU
3. **Wait ~1 minute** for automatic setup
4. **Access FluxGym** on port 7860
5. **Start training!**

---

## Cost Estimate

**Example: RTX 4090 24GB @ $0.69/hr**

- Setup: ~1 minute = $0.01
- Training 16 epochs: ~2 hours = $1.38
- **Total per LoRA: ~$1.39**

With monitoring enabled, stuck training auto-kills = no wasted money on hung processes!

---

## Support

**Documentation:** All guides in `/workspace/fluxgym/`

**Repository:** https://github.com/jaysep/fluxgymHardened

**Key Files:**
- `RUNPOD_STARTUP_COMMAND.txt` - Ready-to-copy startup script
- `RUNPOD_TEMPLATE_FOR_JAYSEP.md` - Complete template guide
- `PACKAGE_VERSION_FIX.md` - Why exact versions matter
- `RUNPOD_QUICK_DEPLOY.md` - This file

---

**Your FluxGym Hardened is ready to deploy!** 🚀
