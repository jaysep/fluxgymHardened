# FluxGym Hardened Deployment Script

Automated deployment script that downloads and installs all hardened files from GitHub.

---

## Quick Start

### 1. Deploy the Working Template Pod

Go to: https://console.runpod.io/hub/template/next-diffusion-fluxgym?id=bxfngsn6x6

Deploy a pod with your preferred GPU.

### 2. Download the Deployment Script

SSH to your pod and download the script:

```bash
ssh root@<pod-ip> -p <port>

cd /workspace
curl -O https://raw.githubusercontent.com/jaysep/fluxgymHardened/main/deploy_hardened.sh
chmod +x deploy_hardened.sh
```

### 3. Run the Script

```bash
bash deploy_hardened.sh
```

That's it! The script will:
- ✅ Stop the running FluxGym app
- ✅ Backup all original files (timestamped)
- ✅ Download all 6 hardened files from GitHub
- ✅ Verify the downloads
- ✅ Restart FluxGym
- ✅ Check that it started successfully
- ✅ Create a rollback script

---

## What Gets Installed

### Core Application (3 files)
1. `app.py` - Hardened UI with monitoring, persistence, logs
2. `training_monitor.py` - GPU monitoring and hang detection
3. `find_checkpoint.py` - Checkpoint recovery utility

### Hang Prevention & Fixes (4 files)
4. `sd-scripts/flux_train.py` - DataLoader timeout fix
5. `sd-scripts/library/custom_offloading_utils.py` - Block swap timeout
6. `sd-scripts/library/strategy_base.py` - File I/O timeout
7. `sd-scripts/library/train_util.py` - Checkpoint resume fix (KeyError: 'step')
8. `sd-scripts/train_network.py` - Checkpoint resume fix (pass global_step)

---

## Dry Run Mode

Test the script without making changes:

```bash
bash deploy_hardened.sh --dry-run
```

This shows what would happen without actually modifying files.

---

## Verification

After running, the script will show:

```
=== Deployment Summary ===

✓ Hardened FluxGym deployed successfully!

Backup location: /workspace/fluxgym_backups/20250126_123456
View logs: tail -f /workspace/fluxgym/fluxgym.log

Features enabled:
  ✓ State persistence (sessions, active runs)
  ✓ Training log persistence
  ✓ GPU monitoring & hang detection
  ✓ Auto-resume/restart from checkpoints
  ✓ DataLoader timeout (60s)
  ✓ Block swap timeout (30s)
  ✓ File I/O timeout (30s)

Access FluxGym via Runpod Connect → HTTP Service [Port 7860]
```

### Check Logs

```bash
tail -f /workspace/fluxgym/fluxgym.log
```

Should see:
- No errors or tracebacks
- "Running on local URL: http://0.0.0.0:7860"
- "Running on public URL: https://..."

### Test the UI

1. In Runpod, click **"Connect"** → **"HTTP Service [Port 7860]"**
2. Verify:
   - ✅ "Enable Auto-Monitoring" checkbox appears
   - ✅ Can upload images
   - ✅ Training starts successfully
   - ✅ Logs appear in UI
   - ✅ State persists after refresh

---

## Rollback

If something goes wrong, rollback to original files:

```bash
# The script creates this for you
bash /workspace/rollback_hardened.sh /workspace/fluxgym_backups/20250126_123456
```

Replace the timestamp with your actual backup directory.

### Manual Rollback

```bash
cd /workspace/fluxgym

# Stop app
kill $(cat fluxgym.pid) 2>/dev/null || pkill -f "python3 app.py"

# Restore from backup
BACKUP_DIR="/workspace/fluxgym_backups/20250126_123456"
cp "$BACKUP_DIR/app.py" ./
cp "$BACKUP_DIR/sd-scripts/flux_train.py" sd-scripts/
cp "$BACKUP_DIR/sd-scripts/library/custom_offloading_utils.py" sd-scripts/library/
cp "$BACKUP_DIR/sd-scripts/library/strategy_base.py" sd-scripts/library/

# Restart
bash run_fluxgym.sh
```

---

## Troubleshooting

### Script Fails to Download Files

**Error:** `Failed to download: app.py`

**Fix:** Check internet connectivity and GitHub access:

```bash
curl -I https://raw.githubusercontent.com/jaysep/fluxgymHardened/main/app.py
```

If blocked, manually download files and run script in dry-run mode to verify.

### App Won't Start After Deployment

**Check logs:**
```bash
tail -50 /workspace/fluxgym/fluxgym.log
```

**Rollback to original:**
```bash
bash /workspace/rollback_hardened.sh /workspace/fluxgym_backups/<timestamp>
```

**Common issues:**
- Python environment not activated
- Missing dependencies
- Port already in use

### Verification Fails

**Error:** `app.py missing hardened features`

This means the download didn't work correctly. Check:

```bash
# Check file size
ls -lh /workspace/fluxgym/app.py

# Check content
head -20 /workspace/fluxgym/app.py
```

If file is too small or wrong content, download manually:

```bash
cd /workspace/fluxgym
curl -O https://raw.githubusercontent.com/jaysep/fluxgymHardened/main/app.py
```

---

## Script Internals

### What the Script Does

1. **Environment Check**
   - Verifies `/workspace/fluxgym` exists
   - Checks for `app.py` and `sd-scripts/`

2. **Stop App**
   - Kills process using PID file
   - Fallback: kill by process name
   - Verifies app stopped

3. **Create Backup**
   - Creates timestamped backup directory
   - Copies all 6 files before replacement

4. **Download Files**
   - Downloads from GitHub raw URL
   - Verifies each download succeeded
   - Sets executable permissions

5. **Verify Files**
   - Checks for hardened features in each file
   - Looks for timeout fixes
   - Ensures monitoring code present

6. **Create Rollback Script**
   - Generates custom rollback script
   - Pre-configured with backup path

7. **Start App**
   - Uses `run_fluxgym.sh` from template
   - Waits for startup

8. **Check Status**
   - Verifies process running
   - Scans logs for errors
   - Looks for success indicators

### Backup Location

Backups are stored in: `/workspace/fluxgym_backups/<timestamp>/`

Format: `YYYYMMDD_HHMMSS` (e.g., `20250126_143022`)

Each backup contains:
```
fluxgym_backups/20250126_143022/
├── app.py
├── training_monitor.py (if existed)
├── find_checkpoint.py (if existed)
└── sd-scripts/
    ├── flux_train.py
    └── library/
        ├── custom_offloading_utils.py
        └── strategy_base.py
```

---

## Manual Installation (Without Script)

If you prefer manual installation, follow FILES_TO_COPY.md.

The script automates these steps:
1. Stop app
2. Backup files
3. Download from GitHub
4. Verify downloads
5. Restart app

---

## Advanced Usage

### Custom GitHub Repository

Edit the script to use your fork:

```bash
nano deploy_hardened.sh

# Change this line:
GITHUB_RAW_URL="https://raw.githubusercontent.com/jaysep/fluxgymHardened/main"

# To your fork:
GITHUB_RAW_URL="https://raw.githubusercontent.com/YOUR_USERNAME/fluxgymHardened/main"
```

### Deploy Specific Branch

```bash
# Edit script to use different branch
GITHUB_RAW_URL="https://raw.githubusercontent.com/jaysep/fluxgymHardened/dev"
```

### Skip Verification

Not recommended, but if needed:

```bash
# Comment out verification in script
nano deploy_hardened.sh

# Find and comment out:
# verify_files
```

---

## Support

**Issues?** Check:
1. Logs: `tail -f /workspace/fluxgym/fluxgym.log`
2. Process: `ps aux | grep "python3 app.py"`
3. Backup: Files in `/workspace/fluxgym_backups/`

**Repository:** https://github.com/jaysep/fluxgymHardened

**Documentation:**
- `FILES_TO_COPY.md` - Manual installation guide
- `TWO_STEP_DEPLOYMENT.md` - Step-by-step deployment
- `PACKAGE_VERSION_FIX.md` - Technical details

---

## Example Session

```bash
root@pod:~# cd /workspace
root@pod:/workspace# curl -O https://raw.githubusercontent.com/jaysep/fluxgymHardened/main/deploy_hardened.sh
root@pod:/workspace# chmod +x deploy_hardened.sh
root@pod:/workspace# bash deploy_hardened.sh

╔════════════════════════════════════════════════╗
║   FluxGym Hardened Deployment Script          ║
║   github.com/jaysep/fluxgymHardened           ║
╚════════════════════════════════════════════════╝

=== Checking Environment ===
✓ Environment check passed
ℹ FluxGym directory: /workspace/fluxgym

=== Stopping FluxGym App ===
✓ Stopped FluxGym (PID: 1234)
✓ FluxGym stopped successfully

=== Creating Backup Directory ===
✓ Created backup directory: /workspace/fluxgym_backups/20250126_143022

=== Backing Up Original Files ===
✓ Backed up: app.py
✓ Backed up: sd-scripts/flux_train.py
✓ Backed up: sd-scripts/library/custom_offloading_utils.py
✓ Backed up: sd-scripts/library/strategy_base.py

=== Downloading Hardened Files from GitHub ===
ℹ Downloading core application files...
✓ Downloaded: app.py
✓ Downloaded: training_monitor.py
✓ Downloaded: find_checkpoint.py
ℹ Downloading hang prevention files...
✓ Downloaded: sd-scripts/flux_train.py
✓ Downloaded: sd-scripts/library/custom_offloading_utils.py
✓ Downloaded: sd-scripts/library/strategy_base.py
✓ All files downloaded successfully

=== Verifying Downloaded Files ===
✓ app.py has hardened features
✓ training_monitor.py looks correct
✓ flux_train.py has timeout fix
✓ custom_offloading_utils.py has timeout fix
✓ strategy_base.py has timeout fix
✓ All files verified successfully

✓ Created rollback script: /workspace/rollback_hardened.sh

=== Starting FluxGym App ===
✓ FluxGym started
ℹ Waiting 5 seconds for startup...

=== Checking App Status ===
✓ FluxGym process is running
✓ No errors detected in recent logs
✓ FluxGym UI is running!

=== Deployment Summary ===

✓ Hardened FluxGym deployed successfully!

Backup location: /workspace/fluxgym_backups/20250126_143022
View logs: tail -f /workspace/fluxgym/fluxgym.log

Features enabled:
  ✓ State persistence (sessions, active runs)
  ✓ Training log persistence
  ✓ GPU monitoring & hang detection
  ✓ Auto-resume/restart from checkpoints
  ✓ DataLoader timeout (60s)
  ✓ Block swap timeout (30s)
  ✓ File I/O timeout (30s)

Access FluxGym via Runpod Connect → HTTP Service [Port 7860]

⚠ To rollback if needed:
  bash rollback_hardened.sh /workspace/fluxgym_backups/20250126_143022
```

Done! 🚀
