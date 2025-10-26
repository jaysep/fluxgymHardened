# Package Version Fix - Critical for Runpod Deployment

## Problem Summary

FluxGym deployment on Runpod was failing with this error:

```python
TypeError: argument of type 'bool' is not iterable
# in gradio_client/utils.py line 863
ValueError: When localhost is not accessible, a shareable link must be created.
```

**Root Cause:** Newer versions of fastapi, starlette, and uvicorn (released late 2024) have breaking changes that cause Gradio's API documentation generation to fail.

## The Solution

Use **exact package versions** AND **Python 3.10** from the verified working Next Diffusion FluxGym template.

**CRITICAL:** Python version must be 3.10, not 3.11! The same package versions that work on Python 3.10.12 fail on Python 3.11.10 with the TypeError.

### Critical Version Requirements

**MUST use these exact versions:**

```
fastapi==0.116.1     # NOT 0.120.0 or newer
starlette==0.47.2    # NOT 0.48.0 or newer
uvicorn==0.35.0      # NOT 0.38.0 or newer
httpcore==1.0.9      # NOT 1.0.5 or older
httpx==0.28.1        # NOT 0.27.2 or older
h11==0.16.0          # NOT 0.14.0 or older
anyio==4.9.0         # NOT 4.6.0 or older
```

**Supporting packages also pinned:**

```
certifi==2025.7.14
attrs==25.3.0
jsonschema==4.25.0
packaging==25.0
```

**ML/FluxGym packages:**

```
accelerate==0.33.0
transformers==4.44.0
bitsandbytes==0.46.1
safetensors==0.4.4
huggingface-hub==0.34.3
toml==0.10.2
einops==0.7.0
opencv-python==4.8.1.78
sentencepiece==0.2.0
rich==13.7.0
voluptuous==0.13.1
gradio==4.44.1
python-slugify==8.0.4
pyyaml==6.0.2
imagesize==1.4.1
peft==0.16.0
lycoris-lora==1.8.3
```

**Plus:**
- gradio_logsview from HuggingFace
- diffusers from specific git commit

## Why Virtual Environment is Required

**Problem without venv:**
- System pip installs newer package versions by default
- Conflicts between system packages and FluxGym requirements
- Cannot isolate FluxGym dependencies from system dependencies

**Solution with venv:**

```bash
python -m venv --system-site-packages env
source env/bin/activate
pip install -q --upgrade pip
pip install -q --no-cache-dir [exact versions...]
```

**Why `--system-site-packages`:**
- Base container has torch 2.4.1+cu124 and torchvision 0.19.1+cu124
- These are HUGE packages (gigabytes)
- Don't want to reinstall them in venv
- `--system-site-packages` inherits them from system while isolating other packages

## Discovery Process

### What Failed

1. **Gradio version pinning** - Tried gradio<4.44, gradio==4.36.1 → Still failed
2. **Adding `show_api=False`** - Tried disabling API docs → Still failed
3. **Creating separate app_runpod.py** - Tried different configurations → Still failed
4. **Removing root_path** - Tried different Gradio settings → Still failed

### Breakthrough

User deployed working Next Diffusion FluxGym template and:
1. Got complete package list with `pip list`
2. Discovered they use a venv, we weren't
3. Ran our app.py in their venv → **IT WORKED!**
4. This proved our code was fine, only package versions were wrong

### Version Comparison

Compared complete package lists from both environments:

**Working (Next Diffusion template):**
- 181 packages total
- fastapi==0.116.1, starlette==0.47.2, uvicorn==0.35.0
- FluxGym works perfectly

**Failing (our deployment):**
- 206 packages total
- fastapi==0.120.0, starlette==0.48.0, uvicorn==0.38.0
- TypeError in Gradio API generation

**Key insight:** Newer is NOT better. Late 2024 versions of fastapi/starlette/uvicorn introduced breaking changes.

## Implementation in Startup Script

Final RUNPOD_STARTUP_COMMAND.txt (1398 characters):

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
nohup python app.py > fluxgym.log 2>&1 &
echo $! > fluxgym.pid
echo "FluxGym ready on port 7860, VS Code on port 8888"
tail -f fluxgym.log
'
```

**Key changes from previous attempts:**
- Line 8: Create venv with `--system-site-packages`
- Line 9: Activate venv
- Line 10: Upgrade pip first
- Line 11: Install ALL packages with exact versions in single command
- Line 12: **CRITICAL** - Use `python3` (not `python`) to match working template

## Verification

After deployment, verify:

```bash
# Check package versions
source /workspace/fluxgym/env/bin/activate
pip list | grep -E "fastapi|starlette|uvicorn|gradio"

# Should show:
# fastapi      0.116.1
# starlette    0.47.2
# uvicorn      0.35.0
# gradio       4.44.1
```

**If deployment fails, check:**
1. Virtual environment created? `ls /workspace/fluxgym/env/`
2. Virtual environment activated? Check logs for "source env/bin/activate"
3. Correct versions installed? Use pip list command above
4. FluxGym started WITH venv Python? Check that script uses `env/bin/python app.py` not `python app.py`
5. FluxGym logs? Check `cat /workspace/fluxgym/fluxgym.log`

**Common mistake - Using `python` instead of `python3`:**
```bash
# WRONG - may use Python 2 or wrong version
nohup python app.py > fluxgym.log 2>&1 &

# CORRECT - uses Python 3 (which will be venv's python3 after activation)
nohup python3 app.py > fluxgym.log 2>&1 &
```

After `source env/bin/activate`, both `python3` and `pip` commands use the venv versions. Using `python3` explicitly matches the working Next Diffusion template.

## Why This Matters

**Without exact version pinning:**
- Deployment fails with cryptic error
- Hours wasted debugging
- False assumption that code is broken

**With exact version pinning:**
- Deployment works first time
- Reliable, reproducible deployments
- Matches proven working template

## Future Considerations

**When updating packages:**
- Test thoroughly before changing versions
- Check Gradio + fastapi/starlette/uvicorn compatibility
- Consider that newer versions may have breaking changes
- Document any version changes and reasons

**If Gradio updates:**
- Check if newer fastapi/starlette/uvicorn are compatible
- Test complete deployment before updating
- Keep this document updated with new working versions

## References

- Working template: https://console.runpod.io/hub/template/next-diffusion-fluxgym?id=bxfngsn6x6
- Package comparison: theirdeps.txt vs ourdeps.txt
- **Base container:** runpod/pytorch:2.1.1-py3.10-cuda12.1.0-devel-ubuntu22.04 (Python 3.10.12)
- **DO NOT USE:** runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04 (Python 3.11 - causes TypeError)
- FluxGym repository: https://github.com/jaysep/fluxgymHardened

---

**Bottom line:** Use exact package versions. Don't assume newer is better. Test before updating.
