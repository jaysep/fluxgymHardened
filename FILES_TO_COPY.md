# Files to Copy to Working Template

## Strategy

1. Start pod using: https://console.runpod.io/hub/template/next-diffusion-fluxgym?id=bxfngsn6x6
2. SSH to pod
3. Copy these files from your fluxgymHardened to `/workspace/fluxgym/`
4. Restart using their `run_fluxgym.sh` script

---

## Essential Files to Copy

### Core Application Files

### 1. app.py (REQUIRED)
**Your hardened version with all improvements**

Location: `/workspace/fluxgym/app.py`

Features added:
- State persistence (sessions, active runs)
- Training log persistence
- GPU monitoring integration
- Hang detection support
- Success verification
- UI improvements

**How to copy:**
```bash
# From your local machine or GitHub
scp app.py root@<pod-ip>:/workspace/fluxgym/app.py

# Or via GitHub
cd /workspace/fluxgym
curl -O https://raw.githubusercontent.com/jaysep/fluxgymHardened/main/app.py
```

### 2. training_monitor.py (REQUIRED if using monitoring)
**GPU monitoring script**

Location: `/workspace/fluxgym/training_monitor.py`

Features:
- Monitors GPU usage every 30 seconds
- Detects stuck training (GPU=0% for 5+ minutes)
- Auto-kills hung processes
- Logs checkpoint paths

**How to copy:**
```bash
scp training_monitor.py root@<pod-ip>:/workspace/fluxgym/training_monitor.py

# Or via GitHub
cd /workspace/fluxgym
curl -O https://raw.githubusercontent.com/jaysep/fluxgymHardened/main/training_monitor.py
```

### 3. find_checkpoint.py (OPTIONAL)
**Checkpoint recovery utility**

Location: `/workspace/fluxgym/find_checkpoint.py`

Features:
- Finds latest checkpoint for a LoRA
- Helps resume interrupted training

**How to copy:**
```bash
scp find_checkpoint.py root@<pod-ip>:/workspace/fluxgym/find_checkpoint.py

# Or via GitHub
cd /workspace/fluxgym
curl -O https://raw.githubusercontent.com/jaysep/fluxgymHardened/main/find_checkpoint.py
```

---

### SD-Scripts Hang Prevention Files

### 4. sd-scripts/flux_train.py (REQUIRED)
**Main training script with DataLoader timeout fix**

Location: `/workspace/fluxgym/sd-scripts/flux_train.py`

Changes:
- Line 402: Added `timeout=60` to DataLoader to prevent worker process hangs
- Line 403: Added `pin_memory=True` for faster GPU transfers

**How to copy:**
```bash
# Backup original first!
cp /workspace/fluxgym/sd-scripts/flux_train.py /workspace/fluxgym/sd-scripts/flux_train.py.original

# Then copy
scp sd-scripts/flux_train.py root@<pod-ip>:/workspace/fluxgym/sd-scripts/flux_train.py

# Or via GitHub
cd /workspace/fluxgym/sd-scripts
curl -O https://raw.githubusercontent.com/jaysep/fluxgymHardened/main/sd-scripts/flux_train.py
```

### 5. sd-scripts/library/custom_offloading_utils.py (REQUIRED)
**Block swap with timeout to prevent CUDA deadlocks**

Location: `/workspace/fluxgym/sd-scripts/library/custom_offloading_utils.py`

Changes:
- Added 30-second timeout to block swap operations
- Prevents indefinite blocking on CUDA deadlocks
- Error message when timeout occurs

**How to copy:**
```bash
# Backup original
cp /workspace/fluxgym/sd-scripts/library/custom_offloading_utils.py /workspace/fluxgym/sd-scripts/library/custom_offloading_utils.py.original

# Copy
scp sd-scripts/library/custom_offloading_utils.py root@<pod-ip>:/workspace/fluxgym/sd-scripts/library/custom_offloading_utils.py

# Or via GitHub
cd /workspace/fluxgym/sd-scripts/library
curl -O https://raw.githubusercontent.com/jaysep/fluxgymHardened/main/sd-scripts/library/custom_offloading_utils.py
```

### 6. sd-scripts/library/strategy_base.py (REQUIRED)
**File I/O with timeout to prevent network filesystem hangs**

Location: `/workspace/fluxgym/sd-scripts/library/strategy_base.py`

Changes:
- Added `timeout_context` manager for file I/O operations
- 30-second timeout for loading cached latents/embeddings
- Prevents hangs on network filesystems or corrupted files

**How to copy:**
```bash
# Backup original
cp /workspace/fluxgym/sd-scripts/library/strategy_base.py /workspace/fluxgym/sd-scripts/library/strategy_base.py.original

# Copy
scp sd-scripts/library/strategy_base.py root@<pod-ip>:/workspace/fluxgym/sd-scripts/library/strategy_base.py

# Or via GitHub
cd /workspace/fluxgym/sd-scripts/library
curl -O https://raw.githubusercontent.com/jaysep/fluxgymHardened/main/sd-scripts/library/strategy_base.py
```

---

## Files You DON'T Need to Copy

### ❌ run_fluxgym.sh
**Use the template's existing version!**

Their `run_fluxgym.sh` already works and has the right environment setup. Your version is similar but might have different paths.

### ❌ runpod_startup.sh / RUNPOD_STARTUP_COMMAND.txt
**Not needed - you're using their template**

These are only for creating your own template from scratch.

### ❌ app_runpod.py
**Not needed - same as app.py**

This was a duplicate we created during debugging.

### ❌ Documentation files (*.md)
**Optional - only if you want them for reference**

All the .md files are documentation, not required for operation.

---

## Step-by-Step Deployment

### 1. Deploy Working Template

1. Go to: https://console.runpod.io/hub/template/next-diffusion-fluxgym?id=bxfngsn6x6
2. Click **"Deploy"**
3. Select GPU (RTX 4090 or similar)
4. Wait for pod to start (~1-2 minutes)

### 2. Verify Template Works

```bash
# SSH to pod
ssh root@<pod-ip> -p <port>

# Check if fluxgym is running
ps aux | grep "python3 app.py"

# Check logs
tail -f /workspace/fluxgym/fluxgym.log

# Access UI via Runpod Connect → HTTP Service [Port 7860]
```

### 3. Stop the Running App

```bash
cd /workspace/fluxgym

# Stop current app
kill $(cat fluxgym.pid 2>/dev/null) 2>/dev/null || pkill -f "python3 app.py"

# Wait a moment
sleep 2
```

### 4. Backup Original Files

```bash
cd /workspace/fluxgym

# Backup original app.py
cp app.py app.py.original

# Backup in case you need to revert
tar czf original_backup.tar.gz app.py
```

### 5. Copy Your Hardened Files

**Option A: From Local Machine (via SCP)**

```bash
# From your local machine where you have fluxgymHardened
cd /path/to/fluxgymHardened

scp app.py root@<pod-ip>:/workspace/fluxgym/app.py
scp training_monitor.py root@<pod-ip>:/workspace/fluxgym/training_monitor.py
scp find_checkpoint.py root@<pod-ip>:/workspace/fluxgym/find_checkpoint.py
```

**Option B: From GitHub (Directly on Pod)**

```bash
# On the pod
cd /workspace/fluxgym

# Download from your GitHub repo
curl -O https://raw.githubusercontent.com/jaysep/fluxgymHardened/main/app.py
curl -O https://raw.githubusercontent.com/jaysep/fluxgymHardened/main/training_monitor.py
curl -O https://raw.githubusercontent.com/jaysep/fluxgymHardened/main/find_checkpoint.py

# Make monitoring script executable
chmod +x training_monitor.py
```

**Option C: Clone Your Repo Temporarily**

```bash
cd /workspace
git clone https://github.com/jaysep/fluxgymHardened.git temp_hardened
cd /workspace/fluxgym

# Copy just the files you need
cp /workspace/temp_hardened/app.py ./
cp /workspace/temp_hardened/training_monitor.py ./
cp /workspace/temp_hardened/find_checkpoint.py ./

# Cleanup
rm -rf /workspace/temp_hardened
```

### 6. Verify Files Are Copied

```bash
cd /workspace/fluxgym

# Check files exist
ls -lh app.py training_monitor.py find_checkpoint.py

# Quick sanity check - look for hardened features
grep "enable_monitoring" app.py
# Should find results

grep "GPU usage monitoring" training_monitor.py
# Should find results
```

### 7. Start App Using Their Script

```bash
cd /workspace/fluxgym

# Use their existing run_fluxgym.sh
bash run_fluxgym.sh
```

**Their script already does:**
- Activates venv
- Sets environment variables
- Checks for root_path patch
- Starts with python3

### 8. Verify It Works

```bash
# Watch the logs
tail -f /workspace/fluxgym/fluxgym.log

# Should see:
# ✅ No errors about missing modules
# ✅ "Running on local URL: http://0.0.0.0:7860"
# ✅ "Running on public URL: https://..."
# ✅ No TypeError or 500 errors
```

### 9. Test the UI

1. Access via Runpod **"Connect"** → **"HTTP Service [Port 7860]"**
2. Verify hardened features:
   - ✅ "Enable Auto-Monitoring" checkbox appears
   - ✅ Can upload images
   - ✅ Can start training
   - ✅ Training log shows in UI
   - ✅ State persists after page refresh

### 10. Test Training with Monitoring

1. Upload sample images
2. Check **"Enable Auto-Monitoring"**
3. Start training
4. Verify:
   - Training starts
   - Monitor process starts (check logs)
   - GPU usage tracked
   - Training completes or monitoring detects issues

```bash
# Check if monitoring is running
ps aux | grep training_monitor

# Check monitor logs
ls -la outputs/*/monitor.log
tail -f outputs/*/monitor.log
```

---

## Verification Checklist

### Before Copying Files
- [ ] Template pod deployed successfully
- [ ] Original fluxgym works (can access UI)
- [ ] SSH access to pod working

### After Copying Files
- [ ] app.py copied successfully
- [ ] training_monitor.py copied successfully
- [ ] find_checkpoint.py copied successfully
- [ ] Files have correct permissions
- [ ] Original files backed up

### After Starting App
- [ ] App starts without errors
- [ ] No ModuleNotFoundError
- [ ] No TypeError in Gradio
- [ ] UI accessible on port 7860
- [ ] "Enable Auto-Monitoring" checkbox visible
- [ ] Training can start
- [ ] Monitor process starts when enabled
- [ ] Training completes successfully

---

## Troubleshooting

### If App Won't Start After Copying

**Revert to original:**
```bash
cd /workspace/fluxgym
kill $(cat fluxgym.pid 2>/dev/null) 2>/dev/null
cp app.py.original app.py
bash run_fluxgym.sh
```

**Check for differences:**
```bash
# Compare your app.py to original
diff app.py.original app.py | head -50
```

### If Monitoring Doesn't Work

**Check if script is executable:**
```bash
chmod +x /workspace/fluxgym/training_monitor.py
```

**Test monitoring manually:**
```bash
cd /workspace/fluxgym
source env/bin/activate
python3 training_monitor.py --help
```

### If Training Fails

**Check logs:**
```bash
tail -100 /workspace/fluxgym/fluxgym.log
tail -100 /workspace/fluxgym/outputs/*/monitor.log
```

**Disable monitoring temporarily:**
Uncheck "Enable Auto-Monitoring" and try training without it.

---

## Summary

**Files to copy for full hardened deployment:**

### Core Application (3 files)
1. ✅ `app.py` - REQUIRED (hardened UI with monitoring, persistence, logs)
2. ✅ `training_monitor.py` - REQUIRED (GPU monitoring, hang detection)
3. ⚠️ `find_checkpoint.py` - OPTIONAL (checkpoint recovery)

### Hang Prevention (3 files)
4. ✅ `sd-scripts/flux_train.py` - REQUIRED (DataLoader timeout fix)
5. ✅ `sd-scripts/library/custom_offloading_utils.py` - REQUIRED (block swap timeout)
6. ✅ `sd-scripts/library/strategy_base.py` - REQUIRED (file I/O timeout)

**Total: 6 files (5 required + 1 optional)**

**Files to NOT copy:**
- ❌ `run_fluxgym.sh` - Use theirs!
- ❌ `runpod_startup.sh` - Not needed
- ❌ `app_runpod.py` - Duplicate
- ❌ Documentation (*.md) - Optional

**The template's existing files that work:**
- ✅ `run_fluxgym.sh` - Their startup script
- ✅ `env/` - Their venv with correct packages
- ✅ `sd-scripts/` - Already configured
- ✅ All dependencies already installed

**This approach gives you:**
- ✅ Proven working deployment (their template)
- ✅ Your hardened features (your app.py)
- ✅ Best of both worlds
- ✅ Easy to debug (can revert to original)
- ✅ No complex template creation

---

## Quick Command Summary

```bash
# 1. Deploy pod from template
# (use Runpod UI: https://console.runpod.io/hub/template/next-diffusion-fluxgym?id=bxfngsn6x6)

# 2. SSH to pod
ssh root@<pod-ip> -p <port>

# 3. Stop app
cd /workspace/fluxgym
kill $(cat fluxgym.pid 2>/dev/null) 2>/dev/null || pkill -f "python3 app.py"

# 4. Backup originals
cp app.py app.py.original
cp sd-scripts/flux_train.py sd-scripts/flux_train.py.original
cp sd-scripts/library/custom_offloading_utils.py sd-scripts/library/custom_offloading_utils.py.original
cp sd-scripts/library/strategy_base.py sd-scripts/library/strategy_base.py.original

# 5. Copy ALL hardened files from GitHub
cd /workspace/fluxgym

# Core application files
curl -O https://raw.githubusercontent.com/jaysep/fluxgymHardened/main/app.py
curl -O https://raw.githubusercontent.com/jaysep/fluxgymHardened/main/training_monitor.py
curl -O https://raw.githubusercontent.com/jaysep/fluxgymHardened/main/find_checkpoint.py

# Hang prevention files
cd sd-scripts
curl -O https://raw.githubusercontent.com/jaysep/fluxgymHardened/main/sd-scripts/flux_train.py

cd library
curl -O https://raw.githubusercontent.com/jaysep/fluxgymHardened/main/sd-scripts/library/custom_offloading_utils.py
curl -O https://raw.githubusercontent.com/jaysep/fluxgymHardened/main/sd-scripts/library/strategy_base.py

# 6. Return to fluxgym directory and restart
cd /workspace/fluxgym
bash run_fluxgym.sh

# 7. Verify
tail -f fluxgym.log
```

Done! Your hardened FluxGym with full hang prevention running on proven template infrastructure.
