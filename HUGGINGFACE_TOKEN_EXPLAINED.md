# HuggingFace Token - When Do You Need It?

## TL;DR - Token NOT Required for Training!

**You do NOT need a HuggingFace token to train models in FluxGym.** The token is **only** for uploading your trained LoRAs to HuggingFace.

---

## Why the Confusion?

The Runpod template (https://console.runpod.io/hub/template/next-diffusion-fluxgym) doesn't ask for HF credentials because **they're not needed for the core functionality**!

---

## HuggingFace Token Usage in FluxGym

### What DOESN'T Need a Token ✅

#### 1. **Model Downloads** (Automatic)

FluxGym downloads these models automatically:

```python
# app.py lines 325-365
def download(base_model):
    # FLUX model
    hf_hub_download(repo_id="black-forest-labs/FLUX.1-dev", ...)

    # VAE
    hf_hub_download(repo_id="cocktailpeanut/xulf-dev", ...)

    # CLIP
    hf_hub_download(repo_id="comfyanonymous/flux_text_encoders", ...)

    # T5XXL
    hf_hub_download(repo_id="comfyanonymous/flux_text_encoders", ...)
```

**All these repos are PUBLIC** - no authentication required!

#### 2. **Training** ✅

Training uses downloaded models from local `models/` folder. No HF access needed.

#### 3. **Checkpoint Resume** ✅

Checkpoints are local files. No HF access needed.

#### 4. **All Core Features** ✅

Everything we've implemented:
- Monitoring
- State persistence
- Log persistence
- Hang detection
- Auto-recovery

**None require HuggingFace token!**

---

### What DOES Need a Token ❌

#### 1. **Publishing to HuggingFace** (Optional)

**Location**: "Publish" tab in FluxGym UI

**Purpose**: Upload your trained LoRA to your HuggingFace account

**Usage**:
```
1. Get token from https://huggingface.co/settings/tokens
2. Enter in "Huggingface Token" field
3. Click "Login"
4. Upload trained LoRAs to your HF account
```

**Stored**: Locally in `HF_TOKEN` file (never uploaded)

#### 2. **Gated Model Access** (Rare)

If you want to use gated/private models (not the default FLUX models), you'd need a token with appropriate access.

**FluxGym defaults**: All use public models, no token needed!

---

## Runpod Template Analysis

### Why No HF Token Required?

The Runpod template creators correctly understood:
1. ✅ Model downloads use public repos
2. ✅ Training is fully local
3. ✅ Most users don't need to publish
4. ✅ Token can be added later if needed

**Smart design!** They didn't bloat the template with unnecessary auth.

---

## How Models Are Downloaded

### Method 1: Automatic (Default)

```python
# When you start training, FluxGym checks:
if not os.path.exists("models/unet/flux1-dev.sft"):
    # Downloads automatically from HuggingFace
    hf_hub_download(repo_id="black-forest-labs/FLUX.1-dev", ...)
```

**No token needed!** Uses anonymous access to public repos.

### Method 2: Manual Pre-download (Optional)

If you want to pre-download before training:

```bash
cd /workspace/fluxgym
python -c "
from app import download
download('flux-dev')
"
```

Still no token needed!

---

## Token Setup (If You Want to Publish)

### Step 1: Get Token

```
1. Go to https://huggingface.co/settings/tokens
2. Click "New token"
3. Name: "FluxGym Upload"
4. Type: "Write" (not "Read")
5. Create token
6. Copy token
```

### Step 2: Add to FluxGym

**Option A: Via UI**
```
1. Open FluxGym
2. Go to "Publish" tab
3. Paste token in "Huggingface Token" field
4. Click "Login"
```

**Option B: Via File**
```bash
# Create HF_TOKEN file
echo "your_token_here" > /workspace/fluxgym/HF_TOKEN
```

### Step 3: Publish LoRAs

```
1. Train a LoRA
2. Go to "Publish" tab
3. Select your LoRA from dropdown
4. Edit name/visibility
5. Click "Upload to HuggingFace"
```

---

## Security Considerations

### Token Storage

**FluxGym approach**:
```python
# app.py line 147-148
with open("HF_TOKEN", "w") as file:
    file.write(hf_token)
```

**Stored locally**:
- File: `HF_TOKEN` in FluxGym directory
- Never uploaded to cloud
- Never logged
- Only used for HF API calls

**Safe for cloud use**: Even on Runpod, token stays on your pod.

### Token Permissions

**Recommended**: "Write" token with minimal scope
- ✅ Can create repos
- ✅ Can upload models
- ❌ Cannot delete repos
- ❌ Cannot modify org settings

**Not recommended**: "Admin" token (too broad)

---

## Common Scenarios

### Scenario 1: Just Training (No Publishing)

**What you need**:
- ✅ Runpod pod with GPU
- ✅ FluxGym code
- ❌ HuggingFace token

**Workflow**:
```bash
# Start pod, install FluxGym
cd /workspace/fluxgym
python app.py

# Train → Models download automatically
# Download trained .safetensors files to local machine
# Done! No HF token ever needed.
```

### Scenario 2: Training + Publishing

**What you need**:
- ✅ Runpod pod with GPU
- ✅ FluxGym code
- ✅ HuggingFace token (for publishing only)

**Workflow**:
```bash
# Start pod, install FluxGym
cd /workspace/fluxgym
echo "hf_YOUR_TOKEN" > HF_TOKEN  # Add token
python app.py

# Train → Models download automatically
# Go to "Publish" tab → Upload to HF
# Share your LoRA with the world!
```

### Scenario 3: Runpod Template (Most Common)

**What you need**:
- ✅ Runpod template (has FluxGym)
- ❌ HuggingFace token

**Why no token**:
```
Template is pre-configured for:
1. Training only (no publishing)
2. Public model downloads (no auth)
3. Local storage (no cloud upload)

Perfect for 90% of users!
```

**If you want to publish later**:
```
Just add HF_TOKEN file or use "Publish" tab login
```

---

## Troubleshooting

### "401 Unauthorized" During Download

**Problem**: HF download fails with 401 error

**Cause**: Trying to download gated model without token

**Solution**:
```bash
# Option 1: Use public models (default in FluxGym)
# Option 2: If you need gated model, add token:
export HF_TOKEN=your_token_here
# or
huggingface-cli login
```

**Note**: This is NOT an issue with default FluxGym setup!

### "Cannot Upload to HuggingFace"

**Problem**: Upload fails in "Publish" tab

**Cause**: No HF token provided

**Solution**:
```
1. Get token from https://huggingface.co/settings/tokens
2. Enter in FluxGym "Publish" tab
3. Click "Login"
4. Retry upload
```

### "HF_TOKEN file not found"

**Problem**: Warning about missing HF_TOKEN file

**Cause**: File-based auth not set up

**Impact**: None if you're not publishing!

**Solution**: Ignore if you don't need to publish, or create the file:
```bash
echo "your_token" > HF_TOKEN
```

---

## Runpod Template Recommendations

### For Template Creators

**DO**:
- ✅ Pre-install FluxGym
- ✅ Use public model repos
- ✅ Skip HF token requirement
- ✅ Document how to add token later

**DON'T**:
- ❌ Hardcode HF tokens (security risk!)
- ❌ Require tokens for basic usage
- ❌ Force users to create HF accounts

### For Template Users

**If template doesn't ask for HF token**:
- ✅ This is CORRECT behavior
- ✅ You can train without it
- ✅ Add token later if you want to publish

**If template requires HF token**:
- ⚠️ Probably unnecessary
- ⚠️ Check if it's for gated models
- ⚠️ Consider using FluxGym defaults instead

---

## Alternative: Using Your Own Models

If you have private/gated models:

### Option 1: Manual Download

```bash
# Download with token
export HF_TOKEN=your_token
huggingface-cli download black-forest-labs/FLUX.1-dev --local-dir models/unet/

# FluxGym will use local files (no token needed for training)
```

### Option 2: Environment Variable

```bash
# Set token globally
export HF_TOKEN=your_token

# FluxGym will use it automatically for downloads
```

### Option 3: Modify models.yaml

```yaml
# models.yaml
flux-dev-custom:
  repo: "your-org/your-private-flux"
  file: "flux-custom.safetensors"
  ...
```

Then FluxGym will download from your repo (token required).

---

## Comparison: FluxGym vs Other Tools

| Tool | HF Token Required | Why |
|------|------------------|-----|
| **FluxGym** | ❌ No (for training) | Public models |
| **FluxGym Publish** | ✅ Yes | Upload to HF |
| **ComfyUI** | ❌ No | Public models |
| **A1111 WebUI** | ❌ No | Public models |
| **Kohya GUI** | ❌ No (for training) | Public models |
| **Diffusers** | ❌ No (for public) | Depends on model |
| **Private Models** | ✅ Yes | Gated access |

**Pattern**: Training tools don't need tokens unless uploading or using gated models.

---

## FAQ

### Q: Why does the Runpod template not ask for HF token?

**A**: Because it's not needed! All model downloads use public repos. This is correct design, not an oversight.

### Q: Is the template using a hardcoded token?

**A**: No! It's using anonymous access to public HuggingFace repos. This is the recommended approach for public models.

### Q: Should I add my HF token anyway?

**A**: Only if you want to publish trained LoRAs to HuggingFace. Otherwise, unnecessary.

### Q: Is it safe to use without a token?

**A**: Yes! Downloading from public repos is the intended use case. No security implications.

### Q: What if I want to keep my LoRAs private?

**A**: Download the .safetensors files to your local machine. Don't use the "Publish" feature. No HF token needed.

### Q: Can I train on private datasets without a token?

**A**: Yes! Your training images are local files. HF token is only for HF uploads/downloads, not local files.

---

## Summary

### HuggingFace Token in FluxGym:

**NOT NEEDED FOR**:
- ✅ Model downloads (public repos)
- ✅ Training
- ✅ Checkpointing
- ✅ Monitoring
- ✅ All core features
- ✅ Downloading trained LoRAs locally

**NEEDED FOR**:
- ❌ Publishing LoRAs to HuggingFace
- ❌ Accessing gated/private models

**Runpod Template Behavior**:
- ✅ Correctly omits HF token requirement
- ✅ Uses public models via anonymous access
- ✅ Users can add token later if needed for publishing

**Conclusion**: The template is doing it right! No hardcoded tokens, no unnecessary auth, just clean public model access. 🎯

---

## Quick Reference

**Want to train only?**
```bash
# No HF token needed
python app.py
```

**Want to publish to HF?**
```bash
# Add token
echo "hf_YOUR_TOKEN" > HF_TOKEN
python app.py
# Use "Publish" tab
```

**Want to use private models?**
```bash
# Set token
export HF_TOKEN=your_token
python app.py
```

Simple! ✨
