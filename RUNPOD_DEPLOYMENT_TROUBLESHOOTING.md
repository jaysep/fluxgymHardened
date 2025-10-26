# Runpod Deployment Troubleshooting

Quick fixes for common Runpod template deployment issues.

---

## Error: Script Commands Printed Instead of Executed

### Problem

When creating the Runpod template, you see all the commands printed in the logs literally instead of being executed:
```
echo ================================================================ echo FluxGym Hardened...
```

### Cause

The startup script is not wrapped in `bash -c '...'`

Runpod's "Docker Command" field needs scripts to be wrapped in `bash -c` to execute them as a bash script.

### Solution

**CORRECT FORMAT** (must include `bash -c '` wrapper):
```bash
bash -c '
echo "..."
[all your commands]
tail -f /workspace/fluxgym/fluxgym.log
'
```

**INCORRECT** (without wrapper):
```bash
echo "..."
[commands]
```

**Steps:**
1. Open `RUNPOD_TEMPLATE_FOR_JAYSEP.md`
2. Find the section marked: **📋 COPY FROM HERE 👇**
3. Copy starting from `bash -c '`
4. Copy until the closing `'` (marked **📋 COPY UNTIL HERE 👆**)
5. Make sure to include BOTH the opening `bash -c '` AND the closing `'`
6. Paste into Runpod's "Docker Command" field

**Or use the ready-made file:**
- Copy entire contents of `runpod_startup.sh` file
- Already has correct `bash -c` wrapper

---

## Error: "git: command not found"

### Problem

Script fails with:
```
git: command not found
```

### Cause

The base container image doesn't have git pre-installed.

### Solution

**Option 1: Use a different base image** (recommended):
```
runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04
```
This image has git pre-installed.

**Option 2: Install git in startup script**:

Add this at the beginning of your startup script (after the first echo):
```bash
echo "Installing git..."
apt-get update && apt-get install -y git
```

---

## Error: "Port 7860 not accessible"

### Problem

FluxGym UI doesn't load when clicking "HTTP Service [Port 7860]"

### Checklist

1. **Verify port is exposed in template:**
   - Template settings → "Expose HTTP Ports"
   - Should include: `7860,8888`

2. **Wait for startup to complete:**
   - First start: ~65 seconds
   - Check pod logs to see "Ready!" message

3. **Use Runpod's proxy link:**
   - Click "Connect" button in pod view
   - Select "HTTP Service [Port 7860]"
   - DO NOT use direct IP address

4. **Check if FluxGym started:**
   ```bash
   # SSH to pod
   cat /workspace/fluxgym/fluxgym.log
   ```

### Common fixes

**If FluxGym failed to start:**
```bash
# View logs
cat /workspace/fluxgym/fluxgym.log

# Try manual start
cd /workspace/fluxgym
python app.py
```

---

## Error: "code-server installation failed"

### Problem

VS Code Server (port 8888) doesn't load.

### Cause

Network issues during code-server installation, or insufficient permissions.

### Solution

**Check logs:**
```bash
cat /workspace/code-server.log
```

**Manual installation:**
```bash
# SSH to pod
curl -fsSL https://code-server.dev/install.sh | sh

# Start code-server
nohup code-server --bind-addr 0.0.0.0:8888 --auth none /workspace > /workspace/code-server.log 2>&1 &
echo $! > /workspace/code-server.pid
```

**Alternative: Skip VS Code**

If you don't need VS Code, you can remove that section from the startup script:
1. Delete lines installing code-server
2. Delete lines starting code-server
3. Keep only FluxGym installation

---

## Error: "pip install fails"

### Problem

Python dependencies fail to install:
```
ERROR: Could not find a version that satisfies the requirement...
```

### Cause

- Network connectivity issues
- PyTorch version mismatch
- Incompatible Python version

### Solution

**Check Python version:**
```bash
python --version  # Should be 3.10 or 3.11
```

**Try alternative base image:**
```
runpod/pytorch:2.1.1-py3.10-cuda12.1.0-devel-ubuntu22.04
```

**Install dependencies manually:**
```bash
# SSH to pod
pip install gradio_logsview@https://huggingface.co/spaces/cocktailpeanut/gradio_logsview/resolve/main/gradio_logsview-0.0.17-py3-none-any.whl
pip install python-slugify transformers accelerate peft lycoris-lora toml safetensors
```

---

## Error: "GitHub clone fails"

### Problem

```
fatal: could not create work tree dir 'fluxgym': Permission denied
```

### Cause

Insufficient permissions in `/workspace` directory.

### Solution

**Check permissions:**
```bash
ls -la /workspace
```

**Fix permissions:**
```bash
chmod 755 /workspace
cd /workspace
git clone https://github.com/jaysep/fluxgymHardened.git fluxgym
```

---

## Container Keeps Restarting

### Problem

Pod starts, then immediately restarts in a loop.

### Cause

The startup script exits with an error, causing container to restart.

### Solution

**Check startup script:**
1. Remove `exit 1` commands (if any)
2. Make sure last line is `tail -f /workspace/fluxgym/fluxgym.log`
3. This keeps container running

**Debug approach:**
```bash
# Modify startup script to NOT exit on error
# Replace this:
if ps -p $FLUXGYM_PID > /dev/null; then
    echo "✓ FluxGym started"
else
    echo "✗ FluxGym failed"
    exit 1              ❌ Remove this!
fi

# With this:
if ps -p $FLUXGYM_PID > /dev/null; then
    echo "✓ FluxGym started"
else
    echo "✗ FluxGym failed. Check logs at /workspace/fluxgym/fluxgym.log"
fi
```

---

## Slow Startup (> 5 minutes)

### Problem

Pod takes a very long time to become ready.

### Cause

- Downloading large models (first time)
- Slow network connection
- Installing code-server

### Solution

**First start is slower (expected):**
- Code-server install: ~10 seconds
- Pip dependencies: ~30 seconds
- Git clone: ~5 seconds
- Total: ~65 seconds

**If slower than 2 minutes:**

**Check what's hanging:**
```bash
# SSH to pod
ps aux | grep python
ps aux | grep curl
```

**Speed up subsequent starts:**
- Use network volume (models persist)
- Dependencies are cached after first install

---

## Template Settings Checklist

Before deploying, verify:

### Container Configuration
- ✅ Container Image: `runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04`
- ✅ Container Disk: `100 GB` minimum
- ✅ Volume Mount Path: `/workspace`

### Environment Variables
- ✅ `HF_HOME=/workspace/.cache/huggingface`
- ✅ `GRADIO_SERVER_NAME=0.0.0.0`

### Expose Ports
- ✅ HTTP Ports: `7860,8888`

### Start Script
- ✅ Copied from `RUNPOD_TEMPLATE_FOR_JAYSEP.md`
- ✅ NO `#!/bin/bash` or `set -e`
- ✅ NO markdown markers (\`\`\`bash)
- ✅ Starts with comment: `# ============= FLUXGYM HARDENED STARTUP SCRIPT =============`
- ✅ Ends with: `tail -f /workspace/fluxgym/fluxgym.log`

---

## Verification Steps

After template is created and pod deployed:

### 1. Check Pod Logs

In Runpod pod view, click "Logs" and verify you see:
```
================================================================
   FluxGym Hardened - Automatic Setup
   Repository: https://github.com/jaysep/fluxgymHardened
================================================================
[1/5] Setting up VS Code Server...
...
[5/5] Ready!
```

### 2. Test FluxGym UI

1. Click "Connect" → "HTTP Service [Port 7860]"
2. FluxGym UI should load
3. Should see "🔄 Active Training Sessions" banner

### 3. Test VS Code

1. Click "Connect" → "HTTP Service [Port 8888]"
2. VS Code should load in browser
3. Should see /workspace directory

### 4. Verify Processes

SSH to pod and check:
```bash
# FluxGym running
ps -p $(cat /workspace/fluxgym/fluxgym.pid)

# VS Code running
ps -p $(cat /workspace/code-server.pid)

# Both should show running processes
```

---

## Quick Recovery Commands

If something breaks after deployment:

### Restart FluxGym
```bash
cd /workspace/fluxgym
kill $(cat fluxgym.pid) 2>/dev/null
nohup python app.py > fluxgym.log 2>&1 &
echo $! > fluxgym.pid
```

### Restart VS Code
```bash
kill $(cat /workspace/code-server.pid) 2>/dev/null
nohup code-server --bind-addr 0.0.0.0:8888 --auth none /workspace > /workspace/code-server.log 2>&1 &
echo $! > /workspace/code-server.pid
```

### Full Reset
```bash
# Remove everything
rm -rf /workspace/fluxgym
rm /workspace/code-server.pid

# Restart pod (Runpod UI)
# Startup script will reinstall everything
```

---

## Still Having Issues?

### Get Help

1. **Check detailed logs:**
   ```bash
   # FluxGym logs
   cat /workspace/fluxgym/fluxgym.log

   # VS Code logs
   cat /workspace/code-server.log

   # Pod system logs
   # (Available in Runpod pod view → Logs)
   ```

2. **GitHub Issues:**
   - https://github.com/jaysep/fluxgymHardened/issues
   - Include:
     - Error message
     - Pod logs
     - Template settings used

3. **Simplified Template:**

If all else fails, use minimal template without VS Code:

```bash
echo "Installing FluxGym Hardened..."
pip install -q gradio_logsview@https://huggingface.co/spaces/cocktailpeanut/gradio_logsview/resolve/main/gradio_logsview-0.0.17-py3-none-any.whl python-slugify peft lycoris-lora toml
cd /workspace
git clone https://github.com/jaysep/fluxgymHardened.git fluxgym
cd fluxgym
nohup python app.py > fluxgym.log 2>&1 &
echo $! > fluxgym.pid
echo "FluxGym ready on port 7860"
tail -f fluxgym.log
```

This minimal script skips VS Code and just installs FluxGym.

---

**Most common issue:** Copying script with `#!/bin/bash` or `set -e`

**Fix:** Copy only the commands, not the shell directives!

**Need the correct script?** See `RUNPOD_TEMPLATE_FOR_JAYSEP.md` section "Start Script" with clear copy markers.
