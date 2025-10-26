# FluxGym UI Resume After Auto-Recovery - Solution Design

## Problem Statement

When the training monitor kills and restarts stuck training:

1. **UI starts training** → `LogsViewRunner.run_command()` streams logs to UI via generator
2. **Training hangs** → Monitor kills the training process after 5 minutes
3. **Monitor restarts** → Training resumes, but writes to `training_resume.log`
4. **UI stops streaming** → The `run_command()` generator exits because the process was killed
5. **User sees nothing** → No indication training resumed, no new logs in UI

## Current Behavior

### UI Side (app.py)
```python
# Line 1025-1031
with open(training_log_file, 'w', encoding='utf-8') as log_file:
    for log_batch in runner.run_command([command], cwd=cwd):
        for log in log_batch:
            log_file.write(log.message + '\n')
            log_file.flush()
        yield log_batch  # Streams to UI
```

- Opens `outputs/{output_name}/training.log` in write mode
- Streams logs from `run_command()` generator
- When training process is killed, generator exits
- Function returns, UI shows training as "stopped"

### Monitor Side (training_monitor.py)
```python
# Line 395-404
log_file = script_dir / 'training_resume.log'

with open(log_file, 'w') as f:
    process = subprocess.Popen(
        ['bash', str(script_path)],
        cwd=str(script_dir),
        stdout=f,
        stderr=subprocess.STDOUT,
    )
```

- Opens `outputs/{output_name}/training_resume.log` in write mode
- Resumed training logs go to different file
- UI never sees these logs

## Proposed Solutions

### Solution 1: Unified Log File (Simplest) ⭐

**Approach:** Monitor appends to the same `training.log` file that UI uses

**Changes needed:**

#### 1. Monitor writes to `training.log` in append mode

```python
# training_monitor.py - Line 395
log_file = script_dir / 'training.log'  # Same file as UI

with open(log_file, 'a') as f:  # Append mode, not write
    # Write a clear separator
    f.write('\n' + '='*80 + '\n')
    f.write('TRAINING RESUMED BY MONITOR AT ' + datetime.now().isoformat() + '\n')
    f.write('='*80 + '\n\n')
    f.flush()

    process = subprocess.Popen(
        ['bash', str(script_path)],
        cwd=str(script_dir),
        stdout=f,
        stderr=subprocess.STDOUT,
    )
```

**Pros:**
- ✅ Simple - minimal changes needed
- ✅ All logs in one file
- ✅ User can refresh to see continued logs
- ✅ Works with existing UI code

**Cons:**
- ❌ UI won't stream in real-time after resume (generator already exited)
- ❌ User must manually check log file or refresh

---

### Solution 2: File-Based Log Streaming (Recommended) ⭐⭐⭐

**Approach:** UI tails the log file instead of streaming from process

**Changes needed:**

#### 1. Create a log tailing generator

```python
# app.py - New function
import time

def tail_log_file(log_file_path, initial_position=0, check_interval=0.5):
    """
    Tail a log file and yield new lines as they're written.
    Works even if the writing process is killed and restarted.
    """
    from gradio_logsview import Log

    position = initial_position
    consecutive_no_data = 0
    max_consecutive_no_data = 600  # Stop after 5 min of no new data

    while consecutive_no_data < max_consecutive_no_data:
        try:
            if not os.path.exists(log_file_path):
                time.sleep(check_interval)
                consecutive_no_data += 1
                continue

            with open(log_file_path, 'r', encoding='utf-8') as f:
                f.seek(position)
                new_lines = f.readlines()

                if new_lines:
                    consecutive_no_data = 0
                    position = f.tell()

                    # Convert to Log objects for UI
                    logs = [Log(level='INFO', message=line.rstrip()) for line in new_lines]
                    yield logs
                else:
                    consecutive_no_data += 1
                    time.sleep(check_interval)

        except Exception as e:
            logger.error(f"Error tailing log: {e}")
            time.sleep(check_interval)

    logger.info("Log tailing stopped - no new data")
```

#### 2. Modify training function to use log tailing

```python
# app.py - Modified run_training function
def run_training(...):
    # ... setup code ...

    training_log_file = resolve_path_without_quotes(f"outputs/{output_name}/training.log")

    # Start training in background (don't block on streaming)
    runner = LogsViewRunner()
    cwd = os.path.dirname(os.path.abspath(__file__))

    # Start training process in background
    import threading

    def run_training_background():
        """Run training and write all output to log file"""
        try:
            with open(training_log_file, 'w', encoding='utf-8') as log_file:
                for log_batch in runner.run_command([command], cwd=cwd):
                    for log in log_batch:
                        log_file.write(log.message + '\n')
                        log_file.flush()
        except Exception as e:
            with open(training_log_file, 'a', encoding='utf-8') as log_file:
                log_file.write(f'\nERROR: {e}\n')

    # Start training in background thread
    training_thread = threading.Thread(target=run_training_background, daemon=True)
    training_thread.start()

    # Give it a moment to start
    time.sleep(2)

    gr.Info(f"Started training (Log: outputs/{output_name}/training.log)")

    # Stream logs by tailing the file
    # This will continue working even if training process is killed and restarted!
    for log_batch in tail_log_file(training_log_file):
        yield log_batch

    # ... rest of function ...
```

#### 3. Monitor appends to same log file

```python
# training_monitor.py - Same as Solution 1
log_file = script_dir / 'training.log'

with open(log_file, 'a') as f:  # Append
    f.write('\n' + '='*80 + '\n')
    f.write('TRAINING RESUMED BY MONITOR\n')
    f.write('='*80 + '\n\n')
    f.flush()

    process = subprocess.Popen(...)
```

**Pros:**
- ✅ UI continues streaming even after resume
- ✅ Works if training killed and restarted
- ✅ User sees seamless log flow
- ✅ All logs in one file
- ✅ No manual refresh needed

**Cons:**
- ❌ More complex implementation
- ❌ Requires background threading
- ❌ Need to handle thread cleanup

---

### Solution 3: Resume Signal + Reconnect (Most Complex)

**Approach:** Monitor signals UI when training resumes, UI creates new log stream

**Changes needed:**

#### 1. Monitor writes resume signal file

```python
# training_monitor.py
resume_signal_file = script_dir / 'resume_signal.flag'
with open(resume_signal_file, 'w') as f:
    f.write(str(process.pid))
```

#### 2. UI polls for resume signal

```python
# app.py
resume_signal_file = resolve_path_without_quotes(f"outputs/{output_name}/resume_signal.flag")

while True:
    if os.path.exists(resume_signal_file):
        # Training was resumed!
        yield runner.log("🔄 Training resumed by monitor, reconnecting...")

        # Start streaming from resumed training
        # ... reconnect logic ...

        os.remove(resume_signal_file)

    # ... continue streaming ...
```

**Pros:**
- ✅ UI knows immediately when training resumes
- ✅ Can show special message to user

**Cons:**
- ❌ Very complex coordination
- ❌ Race conditions possible
- ❌ Hard to get right

---

## Recommended Implementation: Solution 2

**Why Solution 2 is best:**

1. **Resilient** - Works even if training crashes/restarts multiple times
2. **Real-time** - User sees logs streaming continuously
3. **Simple for user** - No manual refresh needed
4. **Clean architecture** - File-based streaming is more robust than process-based

**Implementation steps:**

1. Create `tail_log_file()` generator function
2. Modify `run_training()` to:
   - Start training in background thread
   - Stream logs by tailing the file
3. Modify monitor to append to `training.log` instead of `training_resume.log`
4. Add clear separator in log when training resumes

**User experience after implementation:**

```
[User starts training in UI]

Starting training...
Epoch 1/10 - Loss: 0.145
Epoch 2/10 - Loss: 0.132
Epoch 3/10 - Loss: 0.128
[Training hangs - GPU 0% for 5 minutes]

================================================================================
TRAINING RESUMED BY MONITOR AT 2025-01-26T15:30:00
Resumed from checkpoint: my-lora-step-150-state
================================================================================

Loading checkpoint from step 150...
Resuming training...
Epoch 4/10 - Loss: 0.125
Epoch 5/10 - Loss: 0.120
...
Training completed successfully!
```

The logs continue seamlessly in the UI without user intervention!

---

## Alternative: Hybrid Approach (Solution 1 + Manual Refresh)

If full file-tailing is too complex, a simpler hybrid:

1. Monitor appends to `training.log`
2. Add a **"Refresh Logs"** button in UI
3. Button re-reads the entire log file and displays it

```python
# app.py - Add refresh button
def refresh_training_logs(output_name):
    """Reload logs from file"""
    log_file = resolve_path_without_quotes(f"outputs/{output_name}/training.log")

    if not os.path.exists(log_file):
        return "No logs found"

    with open(log_file, 'r', encoding='utf-8') as f:
        return f.read()

# In UI
with gr.Tab("Training"):
    logs_output = gr.LogsView(...)
    with gr.Row():
        start_training_btn = gr.Button("Start Training")
        refresh_logs_btn = gr.Button("🔄 Refresh Logs")

    refresh_logs_btn.click(
        fn=refresh_training_logs,
        inputs=[lora_name_input],
        outputs=[logs_output]
    )
```

**Pros:**
- ✅ Very simple to implement
- ✅ Logs are unified
- ✅ User can refresh anytime

**Cons:**
- ❌ Requires manual refresh
- ❌ Not automatic

---

## Summary

| Solution | Complexity | Auto-Resume UI | User Action | Recommended |
|----------|------------|----------------|-------------|-------------|
| 1. Unified Log | Low | ❌ No | Manual refresh | ⭐ OK |
| 2. File Tailing | Medium | ✅ Yes | None | ⭐⭐⭐ Best |
| 3. Signal + Reconnect | High | ✅ Yes | None | Not recommended |
| Hybrid (1 + Button) | Low | ❌ No | Click refresh | ⭐⭐ Good |

**My recommendation:** Start with **Solution 2 (File Tailing)** for the best user experience.

If time is limited, implement **Hybrid Approach** (unified log + refresh button) first, then upgrade to file tailing later.
