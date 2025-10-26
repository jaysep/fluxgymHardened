# FluxGym Application Versions

## Two Versions for Different Environments

### `app.py` - Standard Version
**For:** Local deployment, standard cloud environments

**Launch configuration:**
```python
demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    root_path="/proxy/7860",
    debug=True,
    show_error=True,
    allowed_paths=[cwd]
)
```

**Features:**
- Uses `root_path="/proxy/7860"` for proxy environments
- Works with most standard setups
- Default version for general use

---

### `app_runpod.py` - Runpod Version
**For:** Runpod deployment (and similar cloud GPU platforms)

**Launch configuration:**
```python
demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    share=True,
    debug=True,
    show_error=True,
    allowed_paths=[cwd]
)
```

**Changes from standard version:**
- ✅ Removed `root_path="/proxy/7860"` - Conflicts with Runpod's proxy system
- ✅ Added `share=True` - Required when localhost check fails on Runpod
- ✅ Otherwise identical functionality

**Why needed:**
- Runpod's proxy system handles routing automatically
- Setting `root_path` causes Gradio to think localhost is inaccessible
- Results in `ValueError: When localhost is not accessible, a shareable link must be created`

---

## Runpod Deployment

The startup script automatically uses the Runpod version:

```bash
cd fluxgym
cp app_runpod.py app.py
nohup python app.py > fluxgym.log 2>&1 &
```

This ensures Gradio launches correctly on Runpod without manual patching.

---

## Maintaining Both Versions

When updating FluxGym functionality:

1. **Make changes to `app.py`** (standard version)
2. **Copy to `app_runpod.py`**:
   ```bash
   cp app.py app_runpod.py
   ```
3. **Update the launch line in `app_runpod.py`**:
   ```python
   # Change this line only:
   demo.launch(server_name="0.0.0.0", server_port=7860, share=True, debug=True, show_error=True, allowed_paths=[cwd])
   ```

Or use this automated approach:

```bash
# Copy app.py to app_runpod.py
cp app.py app_runpod.py

# Fix the launch line for Runpod
sed -i 's/demo.launch(server_name="0.0.0.0", server_port=7860, root_path="\/proxy\/7860",/demo.launch(server_name="0.0.0.0", server_port=7860, share=True,/' app_runpod.py
```

---

## Benefits of This Approach

✅ **No runtime patching** - Clean, pre-configured files
✅ **Version controlled** - Both versions in GitHub
✅ **Easy maintenance** - Single line difference
✅ **Explicit intent** - Clear which version is for what
✅ **No sed complexity** - Simple file copy in startup script
✅ **Faster startup** - No string replacement needed

---

## Other Cloud Platforms

**Vast.ai, Lambda Labs, etc.:**
- Try `app.py` first (standard version)
- If you get "localhost not accessible" error, use `app_runpod.py` method:
  ```bash
  cp app_runpod.py app.py
  ```

**Local deployment:**
- Use `app.py` (standard version)
- Should work without modifications

---

## File Locations

```
fluxgym/
├── app.py              # Standard version (local/general cloud)
├── app_runpod.py       # Runpod version (cloud GPU platforms)
└── APP_VERSIONS.md     # This file
```

---

**Summary:** Two versions, one line difference, clean deployment. 🚀
