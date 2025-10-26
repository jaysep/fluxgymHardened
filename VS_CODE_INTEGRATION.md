# VS Code Server Integration - FluxGym Hardened

## Overview

Your Runpod template now includes **code-server** (VS Code in browser) for convenient file editing, debugging, and system management without needing SSH.

---

## What's Included

### code-server

**What it is**: Official VS Code editor running in your browser

**Port**: 8888

**Authentication**: Disabled (--auth none) for convenience

**Workspace**: /workspace (all FluxGym files accessible)

---

## Access Methods

### Via Runpod UI (Easiest)

1. Deploy pod with FluxGym Hardened template
2. Wait ~1 minute for startup
3. Click **"Connect"** button
4. Select **"HTTP Service [Port 8888]"**
5. VS Code opens in new browser tab

### Via Direct URL

```
https://<pod-id>-8888.proxy.runpod.net/
```

Replace `<pod-id>` with your actual pod ID from Runpod.

---

## Features Available

### ✅ File Explorer

- Browse entire /workspace directory
- Navigate to /workspace/fluxgym
- View all Python files, configs, documentation
- Double-click to open files

### ✅ Code Editor

**Syntax Highlighting**:
- Python (.py)
- YAML (.yaml)
- JSON (.json)
- Markdown (.md)
- Shell scripts (.sh)

**Editing**:
- IntelliSense (code completion)
- Find & Replace
- Multi-cursor editing
- Code folding
- Auto-save

### ✅ Integrated Terminal

**Access**: Menu → Terminal → New Terminal

**Features**:
- Full bash shell
- Run any command (python, pip, git, nvidia-smi)
- Multiple terminal tabs
- Split terminals
- Command history

### ✅ Git Integration

**Source Control Panel** (left sidebar):
- View changed files
- Stage/unstage changes
- Commit with messages
- Push/pull from GitHub
- View diff of changes

### ✅ Search Across Files

**Search Panel** (left sidebar):
- Search text in all files
- Regex support
- Case-sensitive option
- Search and replace across files

---

## Common Use Cases

### 1. Edit Configuration Files

**Task**: Modify training parameters

```
1. Open VS Code (port 8888)
2. Navigate to /workspace/fluxgym/app.py
3. Search for "optimizer_type"
4. Modify settings
5. Save (Ctrl/Cmd + S)
6. Restart FluxGym in terminal:
   kill $(cat fluxgym.pid)
   nohup python app.py > fluxgym.log 2>&1 &
```

### 2. View Training Logs Live

**Task**: Monitor training progress

```
1. Open VS Code
2. File → Open File → /workspace/fluxgym/outputs/my-lora/training.log
3. File auto-updates as training progresses
4. Scroll to bottom to see latest
```

### 3. Debug Issues

**Task**: Investigate errors

```
1. Open VS Code terminal
2. Run: tail -f fluxgym.log
3. See errors in real-time
4. Open app.py to fix bugs
5. Test fixes immediately
```

### 4. Update from GitHub

**Task**: Get latest improvements

```
1. Open VS Code terminal
2. cd /workspace/fluxgym
3. git status (check current state)
4. git pull (get updates)
5. Restart FluxGym
```

### 5. Install New Dependencies

**Task**: Add Python packages

```
1. Open VS Code terminal
2. pip install new-package
3. Verify: pip list | grep new-package
4. Update requirements.txt if needed
```

### 6. Edit Documentation

**Task**: Update README or guides

```
1. Navigate to /workspace/fluxgym
2. Open README.md or any .md file
3. Edit in Markdown
4. Preview with Markdown extension (if installed)
5. Save changes
```

### 7. Manage Multiple Training Runs

**Task**: Check active trainings

```
1. Open VS Code terminal
2. ls outputs/  # See all LoRAs
3. cat outputs/*/ui_state.json | grep status
4. View training logs for each
```

### 8. Create New Files

**Task**: Add helper scripts

```
1. Right-click in Explorer
2. Select "New File"
3. Name: my_script.py
4. Write Python code
5. Run in terminal: python my_script.py
```

---

## Startup Integration

### How It Works

**Startup Script** (`RUNPOD_TEMPLATE_FOR_JAYSEP.md`):

```bash
# 1. Install code-server (first run only)
if [ ! -f "/usr/bin/code-server" ]; then
    curl -fsSL https://code-server.dev/install.sh | sh
fi

# 2. Start code-server in background
nohup code-server --bind-addr 0.0.0.0:8888 --auth none /workspace > /workspace/code-server.log 2>&1 &
echo $! > /workspace/code-server.pid

# 3. Continue with FluxGym setup...
```

**Timeline**:
- First start: ~10 seconds to install code-server
- Subsequent starts: Instant (already installed)

### Process Management

**PID File**: `/workspace/code-server.pid`

**Log File**: `/workspace/code-server.log`

**Check if running**:
```bash
ps -p $(cat /workspace/code-server.pid)
```

**Restart code-server**:
```bash
kill $(cat /workspace/code-server.pid)
nohup code-server --bind-addr 0.0.0.0:8888 --auth none /workspace > /workspace/code-server.log 2>&1 &
echo $! > /workspace/code-server.pid
```

---

## Security Considerations

### Authentication Disabled

**Why**: Runpod proxy already provides security
- Each pod has unique URL
- Only accessible via Runpod account
- Temporary pods (terminate when done)

**Safe because**:
- No public internet access
- Runpod proxy layer authentication
- Short-lived pods

### Best Practices

**DO**:
- ✅ Use VS Code for editing and debugging
- ✅ Commit changes to GitHub for persistence
- ✅ Terminate pod when finished

**DON'T**:
- ❌ Store secrets in code (use environment variables)
- ❌ Leave pod running indefinitely
- ❌ Share pod URLs publicly

---

## Troubleshooting

### "Cannot connect to port 8888"

**Check 1**: Verify port exposed in template
```
Template settings → Expose HTTP Ports → Should include "8888"
```

**Check 2**: Verify code-server is running
```bash
ps aux | grep code-server
cat /workspace/code-server.pid
ps -p $(cat /workspace/code-server.pid)
```

**Check 3**: Check logs
```bash
tail -f /workspace/code-server.log
```

**Fix**: Restart code-server
```bash
kill $(cat /workspace/code-server.pid)
nohup code-server --bind-addr 0.0.0.0:8888 --auth none /workspace > /workspace/code-server.log 2>&1 &
echo $! > /workspace/code-server.pid
```

### "VS Code shows 'Cannot load workspace'"

**Cause**: code-server started before /workspace mounted

**Fix**: Restart code-server (it will pick up /workspace)

### "Changes not saving"

**Cause**: File permissions issue

**Fix**: Check file ownership
```bash
ls -la /workspace/fluxgym/
chown -R root:root /workspace/fluxgym/
```

### "Terminal commands not working"

**Cause**: Wrong working directory

**Fix**: Navigate to correct directory
```bash
cd /workspace/fluxgym
pwd  # Verify location
```

---

## Comparison: SSH vs VS Code

| Task | SSH | VS Code |
|------|-----|---------|
| **File Editing** | vim/nano (terminal) | Full GUI editor |
| **Syntax Highlighting** | Basic | Advanced |
| **Multiple Files** | Switch windows | Tabs |
| **Search** | grep command | GUI search |
| **Terminal** | Native | Integrated |
| **File Browser** | ls command | GUI explorer |
| **Git** | CLI only | GUI + CLI |
| **Learning Curve** | Steep (vim) | Gentle (familiar) |

**Verdict**: Use VS Code for convenience, SSH for advanced tasks

---

## Advanced: Extensions

### Installing Extensions

VS Code Server supports extensions, but they must be compatible with server mode.

**Open Extensions Panel**:
1. Click Extensions icon (left sidebar)
2. Search for extension
3. Click "Install"

**Recommended Extensions**:
- Python (official)
- GitLens (Git integration)
- Markdown Preview Enhanced
- YAML
- Docker (if using containers)

**Note**: Some extensions may not work in server mode. Test before relying on them.

---

## Integration with FluxGym Workflow

### Complete Workflow Example

**Scenario**: Train a LoRA, monitor progress, fix issues

```
1. Deploy pod → Wait 1 minute

2. Open FluxGym UI (port 7860)
   - Upload images
   - Configure training
   - Start training

3. Open VS Code (port 8888)
   - Open outputs/my-lora/training.log
   - Watch training progress live
   - Open monitor.log to see GPU stats

4. If training hangs:
   - Check monitor.log (shows GPU stuck detection)
   - Get checkpoint path from monitor.log
   - Resume in FluxGym UI with checkpoint path

5. Make improvements:
   - Edit app.py in VS Code
   - Modify monitoring thresholds
   - Add new features
   - Commit to GitHub via VS Code

6. Test changes:
   - Restart FluxGym via VS Code terminal
   - Verify in FluxGym UI

7. Share improvements:
   - Use VS Code Git panel
   - Commit and push
   - Others benefit from your improvements
```

---

## Configuration Options

### Change Port (if needed)

**In startup script**:
```bash
# Default port 8888
nohup code-server --bind-addr 0.0.0.0:8888 --auth none /workspace

# Custom port (e.g., 9999)
nohup code-server --bind-addr 0.0.0.0:9999 --auth none /workspace
```

**Update template**: Add new port to "Expose HTTP Ports"

### Enable Authentication (optional)

**In startup script**:
```bash
# Generate random password
export PASSWORD=$(openssl rand -base64 16)
echo "VS Code Password: $PASSWORD" > /workspace/vscode-password.txt

# Start with password
nohup code-server --bind-addr 0.0.0.0:8888 /workspace
# Uses PASSWORD env var automatically
```

**Access**: Check /workspace/vscode-password.txt for password

### Change Workspace Directory

**In startup script**:
```bash
# Default: /workspace
nohup code-server --bind-addr 0.0.0.0:8888 --auth none /workspace

# FluxGym only: /workspace/fluxgym
nohup code-server --bind-addr 0.0.0.0:8888 --auth none /workspace/fluxgym
```

---

## Performance Considerations

### Resource Usage

**code-server**:
- CPU: ~50-100 MB (idle)
- RAM: ~200-300 MB (idle)
- Negligible impact on training performance

**Network**:
- Initial load: ~5-10 MB (downloading UI)
- Ongoing: <1 MB (just updates)

**Recommendation**: Leave code-server running, minimal overhead

### When to Use

**Use VS Code for**:
- Editing configuration files
- Viewing logs
- Debugging issues
- Git operations
- Quick terminal commands

**Use SSH for**:
- Heavy file transfers (scp)
- Complex system administration
- Running multiple long-lived processes
- Advanced debugging (gdb, strace)

---

## FAQ

### Q: Is code-server safe?

**A**: Yes, especially on Runpod:
- Runpod proxy provides authentication layer
- Pods are isolated
- Temporary pods (not permanent servers)
- --auth none is safe in this context

### Q: Can I use my local VS Code to connect?

**A**: Yes, but requires SSH setup:
1. SSH to pod
2. Install code-server
3. Use VS Code Remote-SSH extension
4. More complex than browser version

**Recommendation**: Just use browser version (easier)

### Q: Will code-server survive pod restart?

**A**: Yes:
- code-server reinstalls automatically (if needed)
- Startup script handles it
- Your files in /workspace persist (if using network volume)

### Q: Can I install VS Code extensions?

**A**: Some extensions work, some don't:
- Web-compatible extensions: ✅ Work
- Native extensions: ❌ May not work
- Test before relying on them

### Q: Does this slow down training?

**A**: No:
- code-server uses minimal CPU/RAM
- Runs on separate process
- No impact on GPU training

---

## Summary

### What You Get

✅ **VS Code in browser** (no local installation)
✅ **Port 8888** (alongside FluxGym on 7860)
✅ **No password** (Runpod proxy handles security)
✅ **Full file access** (/workspace and all subdirectories)
✅ **Integrated terminal** (bash shell)
✅ **Git integration** (commit, push, pull)
✅ **Auto-installed** (startup script handles it)
✅ **Persistent** (survives pod restarts)

### Quick Commands

```bash
# Check if running
ps -p $(cat /workspace/code-server.pid)

# View logs
tail -f /workspace/code-server.log

# Restart
kill $(cat /workspace/code-server.pid)
nohup code-server --bind-addr 0.0.0.0:8888 --auth none /workspace > /workspace/code-server.log 2>&1 &
echo $! > /workspace/code-server.pid
```

### Access

**Runpod UI**: Connect → HTTP Service [Port 8888]
**Direct URL**: https://<pod-id>-8888.proxy.runpod.net/

---

**VS Code Server is now fully integrated with FluxGym Hardened!** 🚀

Edit files, monitor training, and manage your pod—all from your browser.
