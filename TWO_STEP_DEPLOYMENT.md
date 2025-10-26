# Two-Step Deployment Strategy

## Goal

1. **Step 1:** Get original fluxgym working (lightweight, no modifications)
2. **Step 2:** Switch to fluxgymHardened (add resiliency features)

This approach lets us isolate problems and verify the deployment works before adding our improvements.

---

## Step 1: Minimal Deployment (Original FluxGym)

### Template Settings

**Container Image:**
```
runpod/pytorch:2.1.1-py3.10-cuda12.1.0-devel-ubuntu22.04
```

**Environment Variables:**
- `HF_HOME` = `/workspace/.cache/huggingface`
- `GRADIO_SERVER_NAME` = `0.0.0.0`

**Expose HTTP Ports:**
```
7860
```

**Container Disk:**
```
100 GB
```

### Startup Script (1177 characters)

**Copy this into Docker Command field:**

```bash
bash -c '
cd /workspace
if [ ! -d "fluxgym" ]; then git clone https://github.com/cocktailpeanut/fluxgym.git; else cd fluxgym && git pull && cd ..; fi
cd fluxgym
python -m venv --system-site-packages env
source env/bin/activate
pip install -q --upgrade pip
pip install -q --no-cache-dir fastapi==0.116.1 starlette==0.47.2 uvicorn==0.35.0 httpcore==1.0.9 httpx==0.28.1 h11==0.16.0 anyio==4.9.0 certifi==2025.7.14 attrs==25.3.0 jsonschema==4.25.0 packaging==25.0 accelerate==0.33.0 transformers==4.44.0 bitsandbytes==0.46.1 safetensors==0.4.4 huggingface-hub==0.34.3 toml==0.10.2 einops==0.7.0 opencv-python==4.8.1.78 sentencepiece==0.2.0 rich==13.7.0 voluptuous==0.13.1 gradio==4.44.1 python-slugify==8.0.4 pyyaml==6.0.2 imagesize==1.4.1 peft==0.16.0 lycoris-lora==1.8.3 "gradio_logsview@https://huggingface.co/spaces/cocktailpeanut/gradio_logsview/resolve/main/gradio_logsview-0.0.17-py3-none-any.whl" && pip install -q --no-cache-dir "git+https://github.com/huggingface/diffusers.git@56d438727036b0918b30bbe3110c5fe1634ed19d"
export PYTHONWARNINGS="ignore"
nohup python3 app.py > fluxgym.log 2>&1 &
echo $! > fluxgym.pid
echo "FluxGym ready on port 7860"
tail -f fluxgym.log
'
```

### What This Does

1. Clones **original** fluxgym from cocktailpeanut/fluxgym
2. Creates venv with system packages
3. Installs exact package versions from working template
4. Starts app with `python3`
5. Tails the log

### Expected Result

- FluxGym starts successfully on port 7860
- Access via Runpod's "Connect" → "HTTP Service [Port 7860]"
- Should see Gradio interface
- Can upload images and start training

### If This Works

✅ Proves the deployment mechanism works
✅ Confirms package versions are correct
✅ Validates Python version is compatible
✅ Ready to proceed to Step 2

### If This Fails

❌ Need to debug base deployment first
❌ Check logs: `tail -f /workspace/fluxgym/fluxgym.log`
❌ Verify Python version: `source /workspace/fluxgym/env/bin/activate && python3 --version`
❌ Check packages: `pip list | grep -E 'fastapi|starlette|uvicorn|gradio'`

---

## Step 2: Switch to FluxGym Hardened

**Only proceed if Step 1 works!**

### Changes from Step 1

1. **Repository:** Change from `cocktailpeanut/fluxgym` to `jaysep/fluxgymHardened`
2. **VS Code Server:** Add code-server installation and startup
3. **Port 8888:** Expose for VS Code

### Updated Startup Script (1430 characters)

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

### Additional Template Changes

**Expose HTTP Ports:**
```
7860,8888
```

### What's Added

- ✅ VS Code Server on port 8888
- ✅ Hang prevention features
- ✅ GPU monitoring
- ✅ State persistence
- ✅ Training log persistence
- ✅ Success verification

### If This Works

✅ Full FluxGym Hardened deployment successful!
✅ Access FluxGym on port 7860
✅ Access VS Code on port 8888
✅ All resiliency features active

### If This Fails But Step 1 Worked

The problem is likely in fluxgymHardened modifications:
- Check if app.py differences cause issues
- Compare original vs hardened app.py
- Verify all hardened features are compatible

---

## Comparison: Original vs Hardened

### Original FluxGym (cocktailpeanut/fluxgym)

**Pros:**
- Lightweight
- Proven to work
- Minimal complexity

**Cons:**
- No hang prevention
- No monitoring
- No state persistence
- No training log persistence
- No VS Code access

### FluxGym Hardened (jaysep/fluxgymHardened)

**Pros:**
- All original features
- Plus hang prevention
- Plus monitoring
- Plus state persistence
- Plus training logs
- Plus VS Code access
- Plus comprehensive documentation

**Cons:**
- Slightly more complex
- More code to debug if issues arise

---

## Testing Checklist

### Step 1 Testing

- [ ] Pod starts without errors
- [ ] FluxGym accessible on port 7860
- [ ] Can upload images
- [ ] Can configure training settings
- [ ] Training can start
- [ ] Logs appear in Gradio interface

### Step 2 Testing

All of Step 1, plus:
- [ ] VS Code accessible on port 8888
- [ ] Can edit files in VS Code
- [ ] Terminal works in VS Code
- [ ] Training logs persist after page refresh
- [ ] State restores after page refresh
- [ ] GPU monitoring active (check logs)
- [ ] Hang detection active (check logs)

---

## Quick Start

### For Step 1 (Minimal Test)

1. Create Runpod template with settings above
2. Use RUNPOD_MINIMAL_TEST.txt startup script
3. Deploy pod
4. Wait ~1 minute
5. Access port 7860
6. Verify it works

### For Step 2 (Full Deployment)

1. Update template to expose port 8888
2. Switch to RUNPOD_STARTUP_COMMAND.txt
3. Deploy pod
4. Wait ~1 minute
5. Access port 7860 (FluxGym)
6. Access port 8888 (VS Code)
7. Verify all features work

---

## Troubleshooting

### Both Steps Fail

Problem is in base configuration:
- Container image
- Python version
- Package versions
- Environment variables

### Step 1 Works, Step 2 Fails

Problem is in FluxGym Hardened:
- app.py modifications
- Additional features
- Code incompatibilities

### Both Steps Work

🎉 Success! Deploy with confidence!

---

## Files Reference

- `RUNPOD_MINIMAL_TEST.txt` - Step 1 startup script (original fluxgym)
- `RUNPOD_STARTUP_COMMAND.txt` - Step 2 startup script (fluxgymHardened)
- `TWO_STEP_DEPLOYMENT.md` - This file
- `RUNPOD_TEMPLATE_FOR_JAYSEP.md` - Complete Step 2 guide
- `RUNPOD_QUICK_DEPLOY.md` - Quick reference for Step 2

---

**Start with Step 1, validate it works, then proceed to Step 2.**
