import os
import sys
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
os.environ['GRADIO_ANALYTICS_ENABLED'] = '0'
sys.path.insert(0, os.getcwd())
sys.path.append(os.path.join(os.path.dirname(__file__), 'sd-scripts'))
import subprocess
import logging
import gradio as gr

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
from PIL import Image
import torch
import uuid
import shutil
import json
import yaml
from slugify import slugify
from transformers import AutoProcessor, AutoModelForCausalLM
from gradio_logsview import LogsView, LogsViewRunner
from huggingface_hub import hf_hub_download, HfApi
from library import flux_train_utils, huggingface_util
from argparse import Namespace
import train_network
import toml
import re
MAX_IMAGES = 10000

with open('models.yaml', 'r') as file:
    models = yaml.safe_load(file)

def readme(base_model, lora_name, instance_prompt, sample_prompts):

    # model license
    model_config = models[base_model]
    model_file = model_config["file"]
    base_model_name = model_config["base"]
    license = None
    license_name = None
    license_link = None
    license_items = []
    if "license" in model_config:
        license = model_config["license"]
        license_items.append(f"license: {license}")
    if "license_name" in model_config:
        license_name = model_config["license_name"]
        license_items.append(f"license_name: {license_name}")
    if "license_link" in model_config:
        license_link = model_config["license_link"]
        license_items.append(f"license_link: {license_link}")
    license_str = "\n".join(license_items)
    print(f"license_items={license_items}")
    print(f"license_str = {license_str}")

    # tags
    tags = [ "text-to-image", "flux", "lora", "diffusers", "template:sd-lora", "fluxgym" ]

    # widgets
    widgets = []
    sample_image_paths = []
    output_name = slugify(lora_name)
    samples_dir = resolve_path_without_quotes(f"outputs/{output_name}/sample")
    try:
        for filename in os.listdir(samples_dir):
            # Filename Schema: [name]_[steps]_[index]_[timestamp].png
            match = re.search(r"_(\d+)_(\d+)_(\d+)\.png$", filename)
            if match:
                steps, index, timestamp = int(match.group(1)), int(match.group(2)), int(match.group(3))
                sample_image_paths.append((steps, index, f"sample/{filename}"))

        # Sort by numeric index
        sample_image_paths.sort(key=lambda x: x[0], reverse=True)

        final_sample_image_paths = sample_image_paths[:len(sample_prompts)]
        final_sample_image_paths.sort(key=lambda x: x[1])
        for i, prompt in enumerate(sample_prompts):
            _, _, image_path = final_sample_image_paths[i]
            widgets.append(
                {
                    "text": prompt,
                    "output": {
                        "url": image_path
                    },
                }
            )
    except:
        print(f"no samples")
    dtype = "torch.bfloat16"
    # Construct the README content
    readme_content = f"""---
tags:
{yaml.dump(tags, indent=4).strip()}
{"widget:" if os.path.isdir(samples_dir) else ""}
{yaml.dump(widgets, indent=4).strip() if widgets else ""}
base_model: {base_model_name}
{"instance_prompt: " + instance_prompt if instance_prompt else ""}
{license_str}
---

# {lora_name}

A Flux LoRA trained on a local computer with [Fluxgym](https://github.com/cocktailpeanut/fluxgym)

<Gallery />

## Trigger words

{"You should use `" + instance_prompt + "` to trigger the image generation." if instance_prompt else "No trigger words defined."}

## Download model and use it with ComfyUI, AUTOMATIC1111, SD.Next, Invoke AI, Forge, etc.

Weights for this model are available in Safetensors format.

"""
    return readme_content

def account_hf():
    try:
        with open("HF_TOKEN", "r") as file:
            token = file.read()
            api = HfApi(token=token)
            try:
                account = api.whoami()
                return { "token": token, "account": account['name'] }
            except:
                return None
    except:
        return None

"""
hf_logout.click(fn=logout_hf, outputs=[hf_token, hf_login, hf_logout, repo_owner])
"""
def logout_hf():
    os.remove("HF_TOKEN")
    global current_account
    current_account = account_hf()
    print(f"current_account={current_account}")
    return gr.update(value=""), gr.update(visible=True), gr.update(visible=False), gr.update(value="", visible=False)


"""
hf_login.click(fn=login_hf, inputs=[hf_token], outputs=[hf_token, hf_login, hf_logout, repo_owner])
"""
def login_hf(hf_token):
    api = HfApi(token=hf_token)
    try:
        account = api.whoami()
        if account != None:
            if "name" in account:
                with open("HF_TOKEN", "w") as file:
                    file.write(hf_token)
                global current_account
                current_account = account_hf()
                return gr.update(visible=True), gr.update(visible=False), gr.update(visible=True), gr.update(value=current_account["account"], visible=True)
        return gr.update(), gr.update(), gr.update(), gr.update()
    except:
        print(f"incorrect hf_token")
        return gr.update(), gr.update(), gr.update(), gr.update()

def upload_hf(base_model, lora_rows, repo_owner, repo_name, repo_visibility, hf_token):
    src = lora_rows
    repo_id = f"{repo_owner}/{repo_name}"
    gr.Info(f"Uploading to Huggingface. Please Stand by...", duration=None)
    args = Namespace(
        huggingface_repo_id=repo_id,
        huggingface_repo_type="model",
        huggingface_repo_visibility=repo_visibility,
        huggingface_path_in_repo="",
        huggingface_token=hf_token,
        async_upload=False
    )
    print(f"upload_hf args={args}")
    huggingface_util.upload(args=args, src=src)
    gr.Info(f"[Upload Complete] https://huggingface.co/{repo_id}", duration=None)

def load_captioning(uploaded_files, concept_sentence):
    uploaded_images = [file for file in uploaded_files if not file.endswith('.txt')]
    txt_files = [file for file in uploaded_files if file.endswith('.txt')]
    txt_files_dict = {os.path.splitext(os.path.basename(txt_file))[0]: txt_file for txt_file in txt_files}
    updates = []
    if len(uploaded_images) <= 1:
        raise gr.Error(
            "Please upload at least 2 images to train your model (the ideal number with default settings is between 4-30)"
        )
    elif len(uploaded_images) > MAX_IMAGES:
        raise gr.Error(f"For now, only {MAX_IMAGES} or less images are allowed for training")
    # Update for the captioning_area
    # for _ in range(3):
    updates.append(gr.update(visible=True))
    # Update visibility and image for each captioning row and image
    for i in range(1, MAX_IMAGES + 1):
        # Determine if the current row and image should be visible
        visible = i <= len(uploaded_images)

        # Update visibility of the captioning row
        updates.append(gr.update(visible=visible))

        # Update for image component - display image if available, otherwise hide
        image_value = uploaded_images[i - 1] if visible else None
        updates.append(gr.update(value=image_value, visible=visible))

        corresponding_caption = False
        if(image_value):
            base_name = os.path.splitext(os.path.basename(image_value))[0]
            if base_name in txt_files_dict:
                with open(txt_files_dict[base_name], 'r') as file:
                    corresponding_caption = file.read()

        # Update value of captioning area
        text_value = corresponding_caption if visible and corresponding_caption else concept_sentence if visible and concept_sentence else None
        updates.append(gr.update(value=text_value, visible=visible))

    # Update for the sample caption area
    updates.append(gr.update(visible=True))
    updates.append(gr.update(visible=True))

    return updates

def hide_captioning():
    return gr.update(visible=False), gr.update(visible=False)

def resize_image(image_path, output_path, size):
    with Image.open(image_path) as img:
        width, height = img.size
        if width < height:
            new_width = size
            new_height = int((size/width) * height)
        else:
            new_height = size
            new_width = int((size/height) * width)
        print(f"resize {image_path} : {new_width}x{new_height}")
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        img_resized.save(output_path)

def create_dataset(destination_folder, size, *inputs):
    print("Creating dataset")
    images = inputs[0]
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    for index, image in enumerate(images):
        # copy the images to the datasets folder
        new_image_path = shutil.copy(image, destination_folder)

        # if it's a caption text file skip the next bit
        ext = os.path.splitext(new_image_path)[-1].lower()
        if ext == '.txt':
            continue

        # resize the images
        resize_image(new_image_path, new_image_path, size)

        # copy the captions

        original_caption = inputs[index + 1]

        image_file_name = os.path.basename(new_image_path)
        caption_file_name = os.path.splitext(image_file_name)[0] + ".txt"
        caption_path = resolve_path_without_quotes(os.path.join(destination_folder, caption_file_name))
        print(f"image_path={new_image_path}, caption_path = {caption_path}, original_caption={original_caption}")
        # if caption_path exists, do not write
        if os.path.exists(caption_path):
            print(f"{caption_path} already exists. use the existing .txt file")
        else:
            print(f"{caption_path} create a .txt caption file")
            with open(caption_path, 'w') as file:
                file.write(original_caption)

    print(f"destination_folder {destination_folder}")
    return destination_folder


def run_captioning(images, concept_sentence, *captions):
    print(f"run_captioning")
    print(f"concept sentence {concept_sentence}")
    print(f"captions {captions}")
    #Load internally to not consume resources for training
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device={device}")
    torch_dtype = torch.float16
    model = AutoModelForCausalLM.from_pretrained(
        "multimodalart/Florence-2-large-no-flash-attn", torch_dtype=torch_dtype, trust_remote_code=True
    ).to(device)
    processor = AutoProcessor.from_pretrained("multimodalart/Florence-2-large-no-flash-attn", trust_remote_code=True)

    captions = list(captions)
    for i, image_path in enumerate(images):
        print(captions[i])
        if isinstance(image_path, str):  # If image is a file path
            image = Image.open(image_path).convert("RGB")

        prompt = "<DETAILED_CAPTION>"
        inputs = processor(text=prompt, images=image, return_tensors="pt").to(device, torch_dtype)
        print(f"inputs {inputs}")

        generated_ids = model.generate(
            input_ids=inputs["input_ids"], pixel_values=inputs["pixel_values"], max_new_tokens=1024, num_beams=3
        )
        print(f"generated_ids {generated_ids}")

        generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
        print(f"generated_text: {generated_text}")
        parsed_answer = processor.post_process_generation(
            generated_text, task=prompt, image_size=(image.width, image.height)
        )
        print(f"parsed_answer = {parsed_answer}")
        caption_text = parsed_answer["<DETAILED_CAPTION>"].replace("The image shows ", "")
        print(f"caption_text = {caption_text}, concept_sentence={concept_sentence}")
        if concept_sentence:
            caption_text = f"{concept_sentence} {caption_text}"
        captions[i] = caption_text

        yield captions
    model.to("cpu")
    del model
    del processor
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

def recursive_update(d, u):
    for k, v in u.items():
        if isinstance(v, dict) and v:
            d[k] = recursive_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d

def download(base_model):
    model = models[base_model]
    model_file = model["file"]
    repo = model["repo"]

    # download unet
    if base_model == "flux-dev" or base_model == "flux-schnell":
        unet_folder = "models/unet"
    else:
        unet_folder = f"models/unet/{repo}"
    unet_path = os.path.join(unet_folder, model_file)
    if not os.path.exists(unet_path):
        os.makedirs(unet_folder, exist_ok=True)
        gr.Info(f"Downloading base model: {base_model}. Please wait. (You can check the terminal for the download progress)", duration=None)
        print(f"download {base_model}")
        hf_hub_download(repo_id=repo, local_dir=unet_folder, filename=model_file)

    # download vae
    vae_folder = "models/vae"
    vae_path = os.path.join(vae_folder, "ae.sft")
    if not os.path.exists(vae_path):
        os.makedirs(vae_folder, exist_ok=True)
        gr.Info(f"Downloading vae")
        print(f"downloading ae.sft...")
        hf_hub_download(repo_id="cocktailpeanut/xulf-dev", local_dir=vae_folder, filename="ae.sft")

    # download clip
    clip_folder = "models/clip"
    clip_l_path = os.path.join(clip_folder, "clip_l.safetensors")
    if not os.path.exists(clip_l_path):
        os.makedirs(clip_folder, exist_ok=True)
        gr.Info(f"Downloading clip...")
        print(f"download clip_l.safetensors")
        hf_hub_download(repo_id="comfyanonymous/flux_text_encoders", local_dir=clip_folder, filename="clip_l.safetensors")

    # download t5xxl
    t5xxl_path = os.path.join(clip_folder, "t5xxl_fp16.safetensors")
    if not os.path.exists(t5xxl_path):
        print(f"download t5xxl_fp16.safetensors")
        gr.Info(f"Downloading t5xxl...")
        hf_hub_download(repo_id="comfyanonymous/flux_text_encoders", local_dir=clip_folder, filename="t5xxl_fp16.safetensors")


def resolve_path(p):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    norm_path = os.path.normpath(os.path.join(current_dir, p))
    return f"\"{norm_path}\""
def resolve_path_without_quotes(p):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    norm_path = os.path.normpath(os.path.join(current_dir, p))
    return norm_path

def gen_sh(
    base_model,
    output_name,
    resolution,
    seed,
    workers,
    learning_rate,
    network_dim,
    max_train_epochs,
    save_every_n_epochs,
    timestep_sampling,
    guidance_scale,
    vram,
    sample_prompts,
    sample_every_n_steps,
    enable_checkpointing,
    resume_from_checkpoint,
    *advanced_components
):

    print(f"gen_sh: network_dim:{network_dim}, max_train_epochs={max_train_epochs}, save_every_n_epochs={save_every_n_epochs}, timestep_sampling={timestep_sampling}, guidance_scale={guidance_scale}, vram={vram}, sample_prompts={sample_prompts}, sample_every_n_steps={sample_every_n_steps}, enable_checkpointing={enable_checkpointing}, resume_from_checkpoint={resume_from_checkpoint}")

    output_dir = resolve_path(f"outputs/{output_name}")
    sample_prompts_path = resolve_path(f"outputs/{output_name}/sample_prompts.txt")

    line_break = "\\"
    file_type = "sh"
    if sys.platform == "win32":
        line_break = "^"
        file_type = "bat"

    ############# Sample args ########################
    sample = ""
    # Disable sampling by default for 12GB VRAM to avoid hangs during sample generation
    # For 16GB and 20GB, sampling is enabled but monitored
    if len(sample_prompts) > 0 and sample_every_n_steps > 0:
        sample = f"""--sample_prompts={sample_prompts_path} --sample_every_n_steps="{sample_every_n_steps}" {line_break}
  """

    ############# Checkpoint args ########################
    checkpoint_args = ""
    if enable_checkpointing:
        # Save state at each epoch to enable resume
        checkpoint_args = f"""--save_state {line_break}
  """

    ############# Resume args ########################
    resume_args = ""
    if resume_from_checkpoint and resume_from_checkpoint.strip():
        resume_args = f"""--resume {resolve_path(resume_from_checkpoint)} {line_break}"""


    ############# Optimizer args ########################
    # CRITICAL FIX: Do NOT use blocks_to_swap as it causes deadlocks (see SD_SCRIPTS_HANG_ANALYSIS.md)
    # Instead, use gradient_checkpointing + split_mode + fp8 for memory optimization

    if vram == "16G":
        # 16G VRAM - No block swapping, use adafactor for memory efficiency
        optimizer = f"""--optimizer_type adafactor {line_break}
  --optimizer_args "relative_step=False" "scale_parameter=False" "warmup_init=False" {line_break}
  --lr_scheduler constant_with_warmup {line_break}
  --max_grad_norm 0.0 {line_break}"""
    elif vram == "12G":
        # 12G VRAM - Use split_mode to train only single blocks, no block swapping
        optimizer = f"""--optimizer_type adafactor {line_break}
  --optimizer_args "relative_step=False" "scale_parameter=False" "warmup_init=False" {line_break}
  --split_mode {line_break}
  --network_args "train_blocks=single" {line_break}
  --lr_scheduler constant_with_warmup {line_break}
  --max_grad_norm 0.0 {line_break}"""
    else:
        # 20G+ VRAM - Can use standard adamw8bit
        optimizer = f"""--optimizer_type adamw8bit {line_break}
  """


    #######################################################
    model_config = models[base_model]
    model_file = model_config["file"]
    repo = model_config["repo"]
    if base_model == "flux-dev" or base_model == "flux-schnell":
        model_folder = "models/unet"
    else:
        model_folder = f"models/unet/{repo}"
    model_path = os.path.join(model_folder, model_file)
    pretrained_model_path = resolve_path(model_path)

    clip_path = resolve_path("models/clip/clip_l.safetensors")
    t5_path = resolve_path("models/clip/t5xxl_fp16.safetensors")
    ae_path = resolve_path("models/vae/ae.sft")
    sh = f"""accelerate launch {line_break}
  --mixed_precision bf16 {line_break}
  --num_cpu_threads_per_process 1 {line_break}
  sd-scripts/flux_train_network.py {line_break}
  {resume_args}--pretrained_model_name_or_path {pretrained_model_path} {line_break}
  --clip_l {clip_path} {line_break}
  --t5xxl {t5_path} {line_break}
  --ae {ae_path} {line_break}
  --cache_latents_to_disk {line_break}
  --save_model_as safetensors {line_break}
  --sdpa --persistent_data_loader_workers {line_break}
  --max_data_loader_n_workers {workers} {line_break}
  --seed {seed} {line_break}
  --gradient_checkpointing {line_break}
  --mixed_precision bf16 {line_break}
  --save_precision bf16 {line_break}
  --network_module networks.lora_flux {line_break}
  --network_dim {network_dim} {line_break}
  {optimizer}{checkpoint_args}{sample}--learning_rate {learning_rate} {line_break}
  --cache_text_encoder_outputs {line_break}
  --cache_text_encoder_outputs_to_disk {line_break}
  --fp8_base {line_break}
  --highvram {line_break}
  --max_train_epochs {max_train_epochs} {line_break}
  --save_every_n_epochs {save_every_n_epochs} {line_break}
  --dataset_config {resolve_path(f"outputs/{output_name}/dataset.toml")} {line_break}
  --output_dir {output_dir} {line_break}
  --output_name {output_name} {line_break}
  --timestep_sampling {timestep_sampling} {line_break}
  --discrete_flow_shift 3.1582 {line_break}
  --model_prediction_type raw {line_break}
  --guidance_scale {guidance_scale} {line_break}
  --loss_type l2"""
   


    ############# Advanced args ########################
    global advanced_component_ids
    global original_advanced_component_values
   
    # check dirty
    print(f"original_advanced_component_values = {original_advanced_component_values}")
    advanced_flags = []
    for i, current_value in enumerate(advanced_components):
#        print(f"compare {advanced_component_ids[i]}: old={original_advanced_component_values[i]}, new={current_value}")
        if original_advanced_component_values[i] != current_value:
            # dirty
            if current_value == True:
                # Boolean
                advanced_flags.append(advanced_component_ids[i])
            else:
                # string
                advanced_flags.append(f"{advanced_component_ids[i]} {current_value}")

    if len(advanced_flags) > 0:
        advanced_flags_str = f" {line_break}\n  ".join(advanced_flags)
        sh = sh + f" {line_break}\n  " + advanced_flags_str

    return sh

def gen_toml(
  dataset_folder,
  resolution,
  class_tokens,
  num_repeats
):
    toml = f"""[general]
shuffle_caption = false
caption_extension = '.txt'
keep_tokens = 1

[[datasets]]
resolution = {resolution}
batch_size = 1
keep_tokens = 1

  [[datasets.subsets]]
  image_dir = '{resolve_path_without_quotes(dataset_folder)}'
  class_tokens = '{class_tokens}'
  num_repeats = {num_repeats}"""
    return toml

def update_total_steps(max_train_epochs, num_repeats, images):
    try:
        num_images = len(images)
        total_steps = max_train_epochs * num_images * num_repeats
        print(f"max_train_epochs={max_train_epochs} num_images={num_images}, num_repeats={num_repeats}, total_steps={total_steps}")
        return gr.update(value = total_steps)
    except:
        print("")

def set_repo(lora_rows):
    selected_name = os.path.basename(lora_rows)
    return gr.update(value=selected_name)

def get_loras():
    try:
        outputs_path = resolve_path_without_quotes(f"outputs")
        files = os.listdir(outputs_path)
        folders = [os.path.join(outputs_path, item) for item in files if os.path.isdir(os.path.join(outputs_path, item)) and item != "sample"]
        folders.sort(key=lambda file: os.path.getctime(file), reverse=True)
        return folders
    except Exception as e:
        return []

def get_samples(lora_name):
    output_name = slugify(lora_name)
    try:
        samples_path = resolve_path_without_quotes(f"outputs/{output_name}/sample")
        files = [os.path.join(samples_path, file) for file in os.listdir(samples_path)]
        files.sort(key=lambda file: os.path.getctime(file), reverse=True)
        return files
    except:
        return []

def get_monitor_status(lora_name):
    """Check if monitoring is running for a given lora"""
    output_name = slugify(lora_name)
    monitor_pid_file = resolve_path_without_quotes(f"outputs/{output_name}/monitor.pid")
    monitor_log = resolve_path_without_quotes(f"outputs/{output_name}/monitor.log")

    status = {
        'running': False,
        'pid': None,
        'log_path': monitor_log,
        'log_tail': ""
    }

    # Check if PID file exists
    if not os.path.exists(monitor_pid_file):
        return status

    try:
        with open(monitor_pid_file, 'r') as f:
            pid = int(f.read().strip())

        # Check if process is actually running
        try:
            os.kill(pid, 0)  # Signal 0 just checks if process exists
            status['running'] = True
            status['pid'] = pid
        except OSError:
            # Process doesn't exist
            status['running'] = False
    except:
        pass

    # Get last few lines of log
    if os.path.exists(monitor_log):
        try:
            with open(monitor_log, 'r') as f:
                lines = f.readlines()
                status['log_tail'] = ''.join(lines[-10:])  # Last 10 lines
        except:
            pass

    return status

def stop_monitor(lora_name):
    """Stop monitoring for a given lora"""
    output_name = slugify(lora_name)
    monitor_pid_file = resolve_path_without_quotes(f"outputs/{output_name}/monitor.pid")

    if not os.path.exists(monitor_pid_file):
        return "No monitor running"

    try:
        with open(monitor_pid_file, 'r') as f:
            pid = int(f.read().strip())

        # Try to kill the process
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(2)
            try:
                os.kill(pid, 0)  # Check if still running
                os.kill(pid, signal.SIGKILL)  # Force kill
            except OSError:
                pass  # Already dead

            os.remove(monitor_pid_file)
            return f"Monitor stopped (PID: {pid})"
        except OSError:
            os.remove(monitor_pid_file)
            return f"Monitor was not running (PID: {pid})"
    except Exception as e:
        return f"Error stopping monitor: {e}"

def get_training_log(lora_name, num_lines=100):
    """Get training log tail for display after reconnection"""
    if not lora_name or lora_name.strip() == "":
        return ""

    output_name = slugify(lora_name)
    training_log_file = resolve_path_without_quotes(f"outputs/{output_name}/training.log")

    if not os.path.exists(training_log_file):
        return ""

    try:
        with open(training_log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Return last N lines
            tail = lines[-num_lines:] if len(lines) > num_lines else lines
            return ''.join(tail)
    except Exception as e:
        return f"Error reading training log: {e}"

def refresh_monitor_status(lora_name):
    """Refresh monitor status display"""
    if not lora_name or lora_name.strip() == "":
        return "### Monitor Status\nNo LoRA name provided", ""

    status = get_monitor_status(lora_name)

    if status['running']:
        status_md = f"""### Monitor Status: ✅ Running
**PID:** {status['pid']}
**Log:** `{status['log_path']}`

Monitor is actively watching for stuck training."""
    else:
        status_md = f"""### Monitor Status: ⭕ Not Running
**Log:** `{status['log_path']}`

Monitor is not currently running for this LoRA."""

    return status_md, status['log_tail']

def stop_monitor_ui(lora_name):
    """Stop monitor and refresh status"""
    message = stop_monitor(lora_name)
    gr.Info(message)
    return refresh_monitor_status(lora_name)

def save_training_state(lora_name, config):
    """Save current training state to JSON file"""
    if not lora_name or lora_name.strip() == "":
        return

    output_name = slugify(lora_name)
    state_file = resolve_path_without_quotes(f"outputs/{output_name}/ui_state.json")

    try:
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved UI state to {state_file}")
    except Exception as e:
        logger.error(f"Failed to save UI state: {e}")

def load_training_state(lora_name):
    """Load training state from JSON file"""
    if not lora_name or lora_name.strip() == "":
        return None

    output_name = slugify(lora_name)
    state_file = resolve_path_without_quotes(f"outputs/{output_name}/ui_state.json")

    try:
        if os.path.exists(state_file):
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            logger.info(f"Loaded UI state from {state_file}")
            return state
    except Exception as e:
        logger.error(f"Failed to load UI state: {e}")

    return None

def get_active_trainings():
    """Find all currently active training sessions"""
    active_trainings = []

    try:
        outputs_dir = resolve_path_without_quotes("outputs")
        if not os.path.exists(outputs_dir):
            return active_trainings

        for item in os.listdir(outputs_dir):
            item_path = os.path.join(outputs_dir, item)
            if not os.path.isdir(item_path):
                continue

            state_file = os.path.join(item_path, "ui_state.json")
            if not os.path.exists(state_file):
                continue

            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)

                # Check if training is actually running
                is_running = False
                training_pid_file = os.path.join(item_path, "training.pid")
                if os.path.exists(training_pid_file):
                    try:
                        with open(training_pid_file, 'r') as pf:
                            pid = int(pf.read().strip())
                        os.kill(pid, 0)  # Check if process exists
                        is_running = True
                    except (OSError, ValueError):
                        pass

                state['is_running'] = is_running
                state['output_dir'] = item_path
                active_trainings.append(state)
            except Exception as e:
                logger.error(f"Error loading state for {item}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error finding active trainings: {e}")

    # Sort by most recent first
    active_trainings.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    return active_trainings

def restore_ui_state(lora_name):
    """Restore UI to previous training state"""
    state = load_training_state(lora_name)

    if not state:
        return [gr.update()] * 20  # Return no updates

    # Build updates for all UI components
    updates = []

    # Basic fields
    updates.append(gr.update(value=state.get('lora_name', '')))  # lora_name
    updates.append(gr.update(value=state.get('concept_sentence', '')))  # concept_sentence
    updates.append(gr.update(value=state.get('base_model', 'flux-dev')))  # base_model
    updates.append(gr.update(value=state.get('vram', '20G')))  # vram
    updates.append(gr.update(value=state.get('num_repeats', 10)))  # num_repeats
    updates.append(gr.update(value=state.get('max_train_epochs', 16)))  # max_train_epochs
    updates.append(gr.update(value=state.get('sample_prompts', '')))  # sample_prompts
    updates.append(gr.update(value=state.get('sample_every_n_steps', 0)))  # sample_every_n_steps
    updates.append(gr.update(value=state.get('resolution', 512)))  # resolution
    updates.append(gr.update(value=state.get('enable_checkpointing', True)))  # enable_checkpointing
    updates.append(gr.update(value=state.get('resume_from_checkpoint', '')))  # resume_from_checkpoint
    updates.append(gr.update(value=state.get('enable_monitoring', True)))  # enable_monitoring

    # Advanced fields
    updates.append(gr.update(value=state.get('seed', 42)))  # seed
    updates.append(gr.update(value=state.get('workers', 2)))  # workers
    updates.append(gr.update(value=state.get('learning_rate', '8e-4')))  # learning_rate
    updates.append(gr.update(value=state.get('save_every_n_epochs', 4)))  # save_every_n_epochs
    updates.append(gr.update(value=state.get('guidance_scale', 1.0)))  # guidance_scale
    updates.append(gr.update(value=state.get('timestep_sampling', 'shift')))  # timestep_sampling
    updates.append(gr.update(value=state.get('network_dim', 4)))  # network_dim

    # Info message
    if state.get('is_running', False):
        gr.Info(f"Restored training state for: {state.get('lora_name')} (Currently Running)")
    else:
        gr.Info(f"Restored training state for: {state.get('lora_name')} (Last trained: {state.get('timestamp', 'unknown')})")

    return updates

def display_active_sessions():
    """Display all active/recent training sessions"""
    active = get_active_trainings()

    if not active:
        return "### No Active Training Sessions\n\nNo recent or active training sessions found."

    md = "### Active Training Sessions\n\n"
    md += "Click a LoRA name to restore its state in the UI.\n\n"

    for i, session in enumerate(active):
        # Determine status based on state
        training_status = session.get('status', 'unknown')
        is_running = session.get('is_running', False)

        if training_status == 'failed':
            status_emoji = "❌"
            status_text = "Failed"
        elif training_status == 'completed':
            status_emoji = "✅"
            status_text = "Completed"
        elif is_running:
            status_emoji = "🟢"
            status_text = "Running"
        else:
            status_emoji = "🔵"
            status_text = "Stopped"

        from datetime import datetime
        timestamp = session.get('timestamp', 0)
        time_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S') if timestamp else 'Unknown'

        md += f"{status_emoji} **{session.get('lora_name', 'Unknown')}** - {status_text}\n"
        md += f"   - Started: {time_str}\n"
        md += f"   - Epochs: {session.get('max_train_epochs', '?')}\n"
        md += f"   - Checkpointing: {'✅' if session.get('enable_checkpointing') else '❌'}\n"
        md += f"   - Monitoring: {'✅' if session.get('enable_monitoring') else '❌'}\n"

        # Show error message if failed
        if training_status == 'failed' and session.get('error'):
            md += f"   - ⚠️ Error: {session.get('error')}\n"

        if i < len(active) - 1:
            md += "\n---\n\n"

    return md

def start_training(
    base_model,
    lora_name,
    train_script,
    train_config,
    sample_prompts,
    enable_monitoring,
    concept_sentence,
    vram,
    num_repeats,
    max_train_epochs,
    sample_every_n_steps,
    resolution,
    enable_checkpointing,
    resume_from_checkpoint,
    seed,
    workers,
    learning_rate,
    save_every_n_epochs,
    guidance_scale,
    timestep_sampling,
    network_dim,
):
    # write custom script and toml
    if not os.path.exists("models"):
        os.makedirs("models", exist_ok=True)
    if not os.path.exists("outputs"):
        os.makedirs("outputs", exist_ok=True)
    output_name = slugify(lora_name)
    output_dir = resolve_path_without_quotes(f"outputs/{output_name}")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    download(base_model)

    file_type = "sh"
    if sys.platform == "win32":
        file_type = "bat"

    sh_filename = f"train.{file_type}"
    sh_filepath = resolve_path_without_quotes(f"outputs/{output_name}/{sh_filename}")
    with open(sh_filepath, 'w', encoding="utf-8") as file:
        file.write("#!/bin/bash\nsource /workspace/fluxgym/env/bin/activate\ncd /workspace/fluxgym/\n")
        file.write(train_script)
    gr.Info(f"Generated train script at {sh_filename}")


    dataset_path = resolve_path_without_quotes(f"outputs/{output_name}/dataset.toml")
    with open(dataset_path, 'w', encoding="utf-8") as file:
        file.write(train_config)
    gr.Info(f"Generated dataset.toml")

    sample_prompts_path = resolve_path_without_quotes(f"outputs/{output_name}/sample_prompts.txt")
    with open(sample_prompts_path, 'w', encoding='utf-8') as file:
        file.write(sample_prompts)
    gr.Info(f"Generated sample_prompts.txt")

    # Save UI state for recovery after refresh
    import time
    ui_state = {
        'lora_name': lora_name,
        'concept_sentence': concept_sentence,
        'base_model': base_model,
        'vram': vram,
        'num_repeats': num_repeats,
        'max_train_epochs': max_train_epochs,
        'sample_prompts': sample_prompts,
        'sample_every_n_steps': sample_every_n_steps,
        'resolution': resolution,
        'enable_checkpointing': enable_checkpointing,
        'resume_from_checkpoint': resume_from_checkpoint,
        'enable_monitoring': enable_monitoring,
        'seed': seed,
        'workers': workers,
        'learning_rate': learning_rate,
        'save_every_n_epochs': save_every_n_epochs,
        'guidance_scale': guidance_scale,
        'timestep_sampling': timestep_sampling,
        'network_dim': network_dim,
        'timestamp': time.time(),
        'status': 'starting',
    }
    save_training_state(lora_name, ui_state)

    # Start monitoring if enabled
    monitor_pid = None
    if enable_monitoring:
        monitor_script = resolve_path_without_quotes("training_monitor.py")
        monitor_log = resolve_path_without_quotes(f"outputs/{output_name}/monitor.log")
        monitor_pid_file = resolve_path_without_quotes(f"outputs/{output_name}/monitor.pid")

        monitor_cmd = [
            sys.executable,
            monitor_script,
            "--output-dir", output_dir,
            "--check-interval", "30",
            "--stuck-threshold", "300",
            "--gpu-threshold", "5.0",
            "--auto-resume",
            "--train-script", sh_filepath
        ]

        # Start monitor in background with nohup
        try:
            with open(monitor_log, 'w') as log_file:
                if sys.platform == "win32":
                    # Windows: use CREATE_NEW_PROCESS_GROUP
                    monitor_process = subprocess.Popen(
                        monitor_cmd,
                        stdout=log_file,
                        stderr=subprocess.STDOUT,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    )
                else:
                    # Linux/Mac: use nohup
                    monitor_process = subprocess.Popen(
                        monitor_cmd,
                        stdout=log_file,
                        stderr=subprocess.STDOUT,
                        start_new_session=True  # Detach from parent
                    )

            monitor_pid = monitor_process.pid
            # Save PID for later management
            with open(monitor_pid_file, 'w') as f:
                f.write(str(monitor_pid))

            gr.Info(f"Started auto-monitoring with auto-resume (PID: {monitor_pid}, Log: outputs/{output_name}/monitor.log)")
        except Exception as e:
            gr.Warning(f"Failed to start monitoring: {e}")

    # Train
    if sys.platform == "win32":
        command = sh_filepath
    else:
        command = f"bash \"{sh_filepath}\""

    # Setup training log file for persistence
    training_log_file = resolve_path_without_quotes(f"outputs/{output_name}/training.log")

    # Use LogsViewRunner to execute and stream logs
    runner = LogsViewRunner()
    cwd = os.path.dirname(os.path.abspath(__file__))
    gr.Info(f"Started training (Log: outputs/{output_name}/training.log)")

    # Write logs to file while streaming to UI
    training_failed = False
    error_message = None

    try:
        with open(training_log_file, 'w', encoding='utf-8') as log_file:
            for log_batch in runner.run_command([command], cwd=cwd):
                # log_batch is a list of Log objects
                for log in log_batch:
                    log_file.write(log.message + '\n')
                    log_file.flush()  # Ensure immediate write
                yield log_batch

        yield runner.log(f"Runner: {runner}")

        # Check if training actually completed successfully
        # LogsViewRunner doesn't provide exit code directly, so check for model file
        expected_model = resolve_path_without_quotes(f"outputs/{output_name}/{output_name}.safetensors")
        if not os.path.exists(expected_model):
            training_failed = True
            error_message = "Training did not produce model file. Check logs for errors."

            # Also mark in training log
            with open(training_log_file, 'a', encoding='utf-8') as log_file:
                log_file.write("\n" + "="*80 + "\n")
                log_file.write("ERROR: TRAINING FAILED - Model file not generated\n")
                log_file.write("="*80 + "\n")

    except Exception as e:
        training_failed = True
        error_message = f"Training crashed with error: {str(e)}"

        # Log the error
        with open(training_log_file, 'a', encoding='utf-8') as log_file:
            log_file.write("\n" + "="*80 + "\n")
            log_file.write(f"ERROR: TRAINING CRASHED - {str(e)}\n")
            log_file.write("="*80 + "\n")

        yield f"\n\n{'='*80}\nERROR: Training crashed - {str(e)}\n{'='*80}\n"

    # Update UI state to reflect actual status
    if training_failed:
        # Update state file to show failure
        try:
            state_file = resolve_path_without_quotes(f"outputs/{output_name}/ui_state.json")
            if os.path.exists(state_file):
                with open(state_file, 'r', encoding='utf-8') as f:
                    ui_state = json.load(f)
                ui_state['status'] = 'failed'
                ui_state['error'] = error_message
                with open(state_file, 'w', encoding='utf-8') as f:
                    json.dump(ui_state, f, indent=2, ensure_ascii=False)
        except:
            pass  # Don't fail if we can't update state

        gr.Error(f"❌ Training Failed: {error_message}", duration=None)
        yield f"\n\n❌ Training Failed: {error_message}\n"
    else:
        # Training succeeded - generate README
        try:
            config = toml.loads(train_config)
            concept_sentence = config['datasets'][0]['subsets'][0]['class_tokens']
            print(f"concept_sentence={concept_sentence}")
            print(f"lora_name {lora_name}, concept_sentence={concept_sentence}, output_name={output_name}")
            sample_prompts_path = resolve_path_without_quotes(f"outputs/{output_name}/sample_prompts.txt")
            with open(sample_prompts_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            sample_prompts = [line.strip() for line in lines if len(line.strip()) > 0 and line[0] != "#"]
            md = readme(base_model, lora_name, concept_sentence, sample_prompts)
            readme_path = resolve_path_without_quotes(f"outputs/{output_name}/README.md")
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(md)

            # Update state file to show completion
            try:
                state_file = resolve_path_without_quotes(f"outputs/{output_name}/ui_state.json")
                if os.path.exists(state_file):
                    with open(state_file, 'r', encoding='utf-8') as f:
                        ui_state = json.load(f)
                    ui_state['status'] = 'completed'
                    import time
                    ui_state['completed_at'] = time.time()
                    with open(state_file, 'w', encoding='utf-8') as f:
                        json.dump(ui_state, f, indent=2, ensure_ascii=False)
            except:
                pass

            # Mark success in training log
            with open(training_log_file, 'a', encoding='utf-8') as log_file:
                log_file.write("\n" + "="*80 + "\n")
                log_file.write("✅ TRAINING COMPLETED SUCCESSFULLY\n")
                log_file.write(f"Model saved: outputs/{output_name}/{output_name}.safetensors\n")
                log_file.write("="*80 + "\n")

            gr.Info(f"✅ Training Complete. Check the outputs folder for the LoRA files.", duration=None)
            yield f"\n\n✅ Training completed successfully!\n"
        except Exception as e:
            gr.Warning(f"Training completed but README generation failed: {e}")
            yield f"\n\n⚠️ Training completed but README generation failed: {e}\n"


def update(
    base_model,
    lora_name,
    resolution,
    seed,
    workers,
    class_tokens,
    learning_rate,
    network_dim,
    max_train_epochs,
    save_every_n_epochs,
    timestep_sampling,
    guidance_scale,
    vram,
    num_repeats,
    sample_prompts,
    sample_every_n_steps,
    enable_checkpointing,
    resume_from_checkpoint,
    *advanced_components,
):
    output_name = slugify(lora_name)
    dataset_folder = str(f"datasets/{output_name}")
    sh = gen_sh(
        base_model,
        output_name,
        resolution,
        seed,
        workers,
        learning_rate,
        network_dim,
        max_train_epochs,
        save_every_n_epochs,
        timestep_sampling,
        guidance_scale,
        vram,
        sample_prompts,
        sample_every_n_steps,
        enable_checkpointing,
        resume_from_checkpoint,
        *advanced_components,
    )
    toml = gen_toml(
        dataset_folder,
        resolution,
        class_tokens,
        num_repeats
    )
    return gr.update(value=sh), gr.update(value=toml), dataset_folder

"""
demo.load(fn=loaded, js=js, outputs=[hf_token, hf_login, hf_logout, hf_account])
"""
def loaded():
    global current_account
    current_account = account_hf()
    print(f"current_account={current_account}")
    if current_account != None:
        return gr.update(value=current_account["token"]), gr.update(visible=False), gr.update(visible=True), gr.update(value=current_account["account"], visible=True)
    else:
        return gr.update(value=""), gr.update(visible=True), gr.update(visible=False), gr.update(value="", visible=False)

def update_sample(concept_sentence):
    return gr.update(value=concept_sentence)

def refresh_publish_tab():
    loras = get_loras()
    return gr.Dropdown(label="Trained LoRAs", choices=loras)

def init_advanced():
    # if basic_args
    basic_args = {
        'pretrained_model_name_or_path',
        'clip_l',
        't5xxl',
        'ae',
        'cache_latents_to_disk',
        'save_model_as',
        'sdpa',
        'persistent_data_loader_workers',
        'max_data_loader_n_workers',
        'seed',
        'gradient_checkpointing',
        'mixed_precision',
        'save_precision',
        'network_module',
        'network_dim',
        'learning_rate',
        'cache_text_encoder_outputs',
        'cache_text_encoder_outputs_to_disk',
        'fp8_base',
        'highvram',
        'max_train_epochs',
        'save_every_n_epochs',
        'dataset_config',
        'output_dir',
        'output_name',
        'timestep_sampling',
        'discrete_flow_shift',
        'model_prediction_type',
        'guidance_scale',
        'loss_type',
        'optimizer_type',
        'optimizer_args',
        'lr_scheduler',
        'sample_prompts',
        'sample_every_n_steps',
        'max_grad_norm',
        'split_mode',
        'network_args',
        'save_state',
        'resume'
    }

    # generate a UI config
    # if not in basic_args, create a simple form
    parser = train_network.setup_parser()
    flux_train_utils.add_flux_train_arguments(parser)
    args_info = {}
    for action in parser._actions:
        if action.dest != 'help':  # Skip the default help argument
            # if the dest is included in basic_args
            args_info[action.dest] = {
                "action": action.option_strings,  # Option strings like '--use_8bit_adam'
                "type": action.type,              # Type of the argument
                "help": action.help,              # Help message
                "default": action.default,        # Default value, if any
                "required": action.required       # Whether the argument is required
            }
    temp = []
    for key in args_info:
        temp.append({ 'key': key, 'action': args_info[key] })
    temp.sort(key=lambda x: x['key'])
    advanced_component_ids = []
    advanced_components = []
    for item in temp:
        key = item['key']
        action = item['action']
        if key in basic_args:
            print("")
        else:
            action_type = str(action['type'])
            component = None
            with gr.Column(min_width=300):
                if action_type == "None":
                    # radio
                    component = gr.Checkbox()
    #            elif action_type == "<class 'str'>":
    #                component = gr.Textbox()
    #            elif action_type == "<class 'int'>":
    #                component = gr.Number(precision=0)
    #            elif action_type == "<class 'float'>":
    #                component = gr.Number()
    #            elif "int_or_float" in action_type:
    #                component = gr.Number()
                else:
                    component = gr.Textbox(value="")
                if component != None:
                    component.interactive = True
                    component.elem_id = action['action'][0]
                    component.label = component.elem_id
                    component.elem_classes = ["advanced"]
                if action['help'] != None:
                    component.info = action['help']
            advanced_components.append(component)
            advanced_component_ids.append(component.elem_id)
    return advanced_components, advanced_component_ids


theme = gr.themes.Monochrome(
    text_size=gr.themes.Size(lg="18px", md="15px", sm="13px", xl="22px", xs="12px", xxl="24px", xxs="9px"),
    font=[gr.themes.GoogleFont("Source Sans Pro"), "ui-sans-serif", "system-ui", "sans-serif"],
)
css = """
@keyframes rotate {
    0% {
        transform: rotate(0deg);
    }
    100% {
        transform: rotate(360deg);
    }
}
#advanced_options .advanced:nth-child(even) { background: rgba(0,0,100,0.04) !important; }
h1{font-family: georgia; font-style: italic; font-weight: bold; font-size: 30px; letter-spacing: -1px;}
h3{margin-top: 0}
.tabitem{border: 0px}
.group_padding{}
nav{position: fixed; top: 0; left: 0; right: 0; z-index: 1000; text-align: center; padding: 10px; box-sizing: border-box; display: flex; align-items: center; backdrop-filter: blur(10px); }
nav button { background: none; color: firebrick; font-weight: bold; border: 2px solid firebrick; padding: 5px 10px; border-radius: 5px; font-size: 14px; }
nav img { height: 40px; width: 40px; border-radius: 40px; }
nav img.rotate { animation: rotate 2s linear infinite; }
.flexible { flex-grow: 1; }
.tast-details { margin: 10px 0 !important; }
.toast-wrap { bottom: var(--size-4) !important; top: auto !important; border: none !important; backdrop-filter: blur(10px); }
.toast-title, .toast-text, .toast-icon, .toast-close { color: black !important; font-size: 14px; }
.toast-body { border: none !important; }
#terminal { box-shadow: none !important; margin-bottom: 25px; background: rgba(0,0,0,0.03); }
#terminal .generating { border: none !important; }
#terminal label { position: absolute !important; }
.tabs { margin-top: 50px; }
.hidden { display: none !important; }
.codemirror-wrapper .cm-line { font-size: 12px !important; }
label { font-weight: bold !important; }
#start_training.clicked { background: silver; color: black; }
"""

js = """
function() {
    let autoscroll = document.querySelector("#autoscroll")
    if (window.iidxx) {
        window.clearInterval(window.iidxx);
    }
    window.iidxx = window.setInterval(function() {
        let text=document.querySelector(".codemirror-wrapper .cm-line").innerText.trim()
        let img = document.querySelector("#logo")
        if (text.length > 0) {
            autoscroll.classList.remove("hidden")
            if (autoscroll.classList.contains("on")) {
                autoscroll.textContent = "Autoscroll ON"
                window.scrollTo(0, document.body.scrollHeight, { behavior: "smooth" });
                img.classList.add("rotate")
            } else {
                autoscroll.textContent = "Autoscroll OFF"
                img.classList.remove("rotate")
            }
        }
    }, 500);
    console.log("autoscroll", autoscroll)
    autoscroll.addEventListener("click", (e) => {
        autoscroll.classList.toggle("on")
    })
    function debounce(fn, delay) {
        let timeoutId;
        return function(...args) {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => fn(...args), delay);
        };
    }

    function handleClick() {
        console.log("refresh")
        document.querySelector("#refresh").click();
    }
    const debouncedClick = debounce(handleClick, 1000);
    document.addEventListener("input", debouncedClick);

    document.querySelector("#start_training").addEventListener("click", (e) => {
      e.target.classList.add("clicked")
      e.target.innerHTML = "Training..."
    })

}
"""

current_account = account_hf()
print(f"current_account={current_account}")

with gr.Blocks(elem_id="app", theme=theme, css=css, fill_width=True) as demo:
    with gr.Tabs() as tabs:
        with gr.TabItem("Gym"):
            output_components = []
            with gr.Row():
                gr.HTML("""<nav>
            <img id='logo' src='/proxy/7860/file=icon.png' width='80' height='80'>
            <div class='flexible'></div>
            <button id='autoscroll' class='on hidden'></button>
        </nav>
        """)

            # Active Training Sessions Banner
            with gr.Accordion("🔄 Active Training Sessions", open=False, visible=True) as active_sessions_accordion:
                with gr.Row():
                    active_sessions_display = gr.Markdown("No active training sessions found")
                    refresh_sessions_btn = gr.Button("Refresh Sessions", size="sm")

            with gr.Row(elem_id='container'):
                with gr.Column():
                    gr.Markdown(
                        """# Step 1. LoRA Info
        <p style="margin-top:0">Configure your LoRA train settings.</p>
        """, elem_classes="group_padding")
                    lora_name = gr.Textbox(
                        label="The name of your LoRA",
                        info="This has to be a unique name",
                        placeholder="e.g.: Persian Miniature Painting style, Cat Toy",
                    )
                    concept_sentence = gr.Textbox(
                        elem_id="--concept_sentence",
                        label="Trigger word/sentence",
                        info="Trigger word or sentence to be used",
                        placeholder="uncommon word like p3rs0n or trtcrd, or sentence like 'in the style of CNSTLL'",
                        interactive=True,
                    )
                    model_names = list(models.keys())
                    print(f"model_names={model_names}")
                    base_model = gr.Dropdown(label="Base model (edit the models.yaml file to add more to this list)", choices=model_names, value=model_names[0])
                    vram = gr.Radio(["20G", "16G", "12G" ], value="20G", label="VRAM", interactive=True)
                    num_repeats = gr.Number(value=10, precision=0, label="Repeat trains per image", interactive=True)
                    max_train_epochs = gr.Number(label="Max Train Epochs", value=16, interactive=True)
                    total_steps = gr.Number(0, interactive=False, label="Expected training steps")
                    sample_prompts = gr.Textbox("", lines=5, label="Sample Image Prompts (Separate with new lines)", interactive=True)
                    sample_every_n_steps = gr.Number(0, precision=0, label="Sample Image Every N Steps", interactive=True)
                    resolution = gr.Number(value=512, precision=0, label="Resize dataset images")
                    enable_checkpointing = gr.Checkbox(value=True, label="Enable Checkpointing (Save training state for resume)", interactive=True)
                    resume_from_checkpoint = gr.Textbox("", label="Resume from Checkpoint (path to state folder, e.g., outputs/my-lora/my-lora-state)", interactive=True)
                    enable_monitoring = gr.Checkbox(value=True, label="Enable Auto-Monitoring with Auto-Resume", interactive=True, info="Monitors GPU usage and automatically resumes from last checkpoint if training gets stuck (GPU=0% for 5min)")
                with gr.Column():
                    gr.Markdown(
                        """# Step 2. Dataset
        <p style="margin-top:0">Make sure the captions include the trigger word.</p>
        """, elem_classes="group_padding")
                    with gr.Group():
                        images = gr.File(
                            file_types=["image", ".txt"],
                            label="Upload your images",
                            #info="If you want, you can also manually upload caption files that match the image names (example: img0.png => img0.txt)",
                            file_count="multiple",
                            interactive=True,
                            visible=True,
                            scale=1,
                        )
                    with gr.Group(visible=False) as captioning_area:
                        do_captioning = gr.Button("Add AI captions with Florence-2")
                        output_components.append(captioning_area)
                        #output_components = [captioning_area]
                        caption_list = []
                        for i in range(1, MAX_IMAGES + 1):
                            locals()[f"captioning_row_{i}"] = gr.Row(visible=False)
                            with locals()[f"captioning_row_{i}"]:
                                locals()[f"image_{i}"] = gr.Image(
                                    type="filepath",
                                    width=111,
                                    height=111,
                                    min_width=111,
                                    interactive=False,
                                    scale=2,
                                    show_label=False,
                                    show_share_button=False,
                                    show_download_button=False,
                                )
                                locals()[f"caption_{i}"] = gr.Textbox(
                                    label=f"Caption {i}", scale=15, interactive=True
                                )

                            output_components.append(locals()[f"captioning_row_{i}"])
                            output_components.append(locals()[f"image_{i}"])
                            output_components.append(locals()[f"caption_{i}"])
                            caption_list.append(locals()[f"caption_{i}"])
                with gr.Column():
                    gr.Markdown(
                        """# Step 3. Train
        <p style="margin-top:0">Press start to start training.</p>
        """, elem_classes="group_padding")
                    refresh = gr.Button("Refresh", elem_id="refresh", visible=False)
                    start = gr.Button("Start training", visible=False, elem_id="start_training")
                    output_components.append(start)
                    train_script = gr.Textbox(label="Train script", max_lines=100, interactive=True)
                    train_config = gr.Textbox(label="Train config", max_lines=100, interactive=True)
            with gr.Accordion("Advanced options", elem_id='advanced_options', open=False):
                with gr.Row():
                    with gr.Column(min_width=300):
                        seed = gr.Number(label="--seed", info="Seed", value=42, interactive=True)
                    with gr.Column(min_width=300):
                        workers = gr.Number(label="--max_data_loader_n_workers", info="Number of Workers", value=2, interactive=True)
                    with gr.Column(min_width=300):
                        learning_rate = gr.Textbox(label="--learning_rate", info="Learning Rate", value="8e-4", interactive=True)
                    with gr.Column(min_width=300):
                        save_every_n_epochs = gr.Number(label="--save_every_n_epochs", info="Save every N epochs", value=4, interactive=True)
                    with gr.Column(min_width=300):
                        guidance_scale = gr.Number(label="--guidance_scale", info="Guidance Scale", value=1.0, interactive=True)
                    with gr.Column(min_width=300):
                        timestep_sampling = gr.Textbox(label="--timestep_sampling", info="Timestep Sampling", value="shift", interactive=True)
                    with gr.Column(min_width=300):
                        network_dim = gr.Number(label="--network_dim", info="LoRA Rank", value=4, minimum=4, maximum=128, step=4, interactive=True)
                    advanced_components, advanced_component_ids = init_advanced()
            with gr.Row():
                terminal = LogsView(label="Train log", elem_id="terminal")
            with gr.Accordion("Monitor Status & Logs", open=False):
                with gr.Row():
                    with gr.Column():
                        monitor_status_text = gr.Markdown("Monitor not running")
                        refresh_monitor_btn = gr.Button("Refresh Monitor Status", size="sm")
                        stop_monitor_btn = gr.Button("Stop Monitor", size="sm", variant="stop")
                    with gr.Column():
                        monitor_log_view = gr.Textbox(label="Monitor Log (last 10 lines)", lines=10, interactive=False, max_lines=10)
            with gr.Accordion("📜 Training Log (Persisted)", open=False, visible=True):
                with gr.Row():
                    gr.Markdown("""**View training progress even after page refresh/reconnection.**
                    This shows the last 100 lines from the saved training log file. Auto-refreshes every 5 seconds.""")
                with gr.Row():
                    training_log_display = gr.Textbox(
                        get_training_log,
                        inputs=[lora_name],
                        label="Training Log (last 100 lines)",
                        lines=20,
                        interactive=False,
                        max_lines=20,
                        show_copy_button=True,
                        every=5
                    )
                with gr.Row():
                    refresh_training_log_btn = gr.Button("Refresh Training Log", size="sm")
            with gr.Row():
                gallery = gr.Gallery(get_samples, inputs=[lora_name], label="Samples", every=10, columns=6)

        with gr.TabItem("Publish") as publish_tab:
            hf_token = gr.Textbox(label="Huggingface Token")
            hf_login = gr.Button("Login")
            hf_logout = gr.Button("Logout")
            with gr.Row() as row:
                gr.Markdown("**LoRA**")
                gr.Markdown("**Upload**")
            loras = get_loras()
            with gr.Row():
                lora_rows = refresh_publish_tab()
                with gr.Column():
                    with gr.Row():
                        repo_owner = gr.Textbox(label="Account", interactive=False)
                        repo_name = gr.Textbox(label="Repository Name")
                    repo_visibility = gr.Textbox(label="Repository Visibility ('public' or 'private')", value="public")
                    upload_button = gr.Button("Upload to HuggingFace")
                    upload_button.click(
                        fn=upload_hf,
                        inputs=[
                            base_model,
                            lora_rows,
                            repo_owner,
                            repo_name,
                            repo_visibility,
                            hf_token,
                        ]
                    )
            hf_login.click(fn=login_hf, inputs=[hf_token], outputs=[hf_token, hf_login, hf_logout, repo_owner])
            hf_logout.click(fn=logout_hf, outputs=[hf_token, hf_login, hf_logout, repo_owner])


    publish_tab.select(refresh_publish_tab, outputs=lora_rows)
    lora_rows.select(fn=set_repo, inputs=[lora_rows], outputs=[repo_name])

    dataset_folder = gr.State()

    listeners = [
        base_model,
        lora_name,
        resolution,
        seed,
        workers,
        concept_sentence,
        learning_rate,
        network_dim,
        max_train_epochs,
        save_every_n_epochs,
        timestep_sampling,
        guidance_scale,
        vram,
        num_repeats,
        sample_prompts,
        sample_every_n_steps,
        enable_checkpointing,
        resume_from_checkpoint,
        *advanced_components
    ]
    advanced_component_ids = [x.elem_id for x in advanced_components]
    original_advanced_component_values = [comp.value for comp in advanced_components]
    images.upload(
        load_captioning,
        inputs=[images, concept_sentence],
        outputs=output_components
    )
    images.delete(
        load_captioning,
        inputs=[images, concept_sentence],
        outputs=output_components
    )
    images.clear(
        hide_captioning,
        outputs=[captioning_area, start]
    )
    max_train_epochs.change(
        fn=update_total_steps,
        inputs=[max_train_epochs, num_repeats, images],
        outputs=[total_steps]
    )
    num_repeats.change(
        fn=update_total_steps,
        inputs=[max_train_epochs, num_repeats, images],
        outputs=[total_steps]
    )
    images.upload(
        fn=update_total_steps,
        inputs=[max_train_epochs, num_repeats, images],
        outputs=[total_steps]
    )
    images.delete(
        fn=update_total_steps,
        inputs=[max_train_epochs, num_repeats, images],
        outputs=[total_steps]
    )
    images.clear(
        fn=update_total_steps,
        inputs=[max_train_epochs, num_repeats, images],
        outputs=[total_steps]
    )
    concept_sentence.change(fn=update_sample, inputs=[concept_sentence], outputs=sample_prompts)
    start.click(fn=create_dataset, inputs=[dataset_folder, resolution, images] + caption_list, outputs=dataset_folder).then(
        fn=start_training,
        inputs=[
            base_model,
            lora_name,
            train_script,
            train_config,
            sample_prompts,
            enable_monitoring,
            concept_sentence,
            vram,
            num_repeats,
            max_train_epochs,
            sample_every_n_steps,
            resolution,
            enable_checkpointing,
            resume_from_checkpoint,
            seed,
            workers,
            learning_rate,
            save_every_n_epochs,
            guidance_scale,
            timestep_sampling,
            network_dim,
        ],
        outputs=terminal,
    )
    do_captioning.click(fn=run_captioning, inputs=[images, concept_sentence] + caption_list, outputs=caption_list)

    # Monitor status callbacks
    refresh_monitor_btn.click(
        fn=refresh_monitor_status,
        inputs=[lora_name],
        outputs=[monitor_status_text, monitor_log_view]
    )
    stop_monitor_btn.click(
        fn=stop_monitor_ui,
        inputs=[lora_name],
        outputs=[monitor_status_text, monitor_log_view]
    )

    # Training log callbacks
    refresh_training_log_btn.click(
        fn=get_training_log,
        inputs=[lora_name],
        outputs=[training_log_display]
    )

    # Active sessions callbacks
    refresh_sessions_btn.click(
        fn=display_active_sessions,
        outputs=[active_sessions_display]
    )

    # Load active sessions on page load
    def on_load():
        """Called when UI loads - restore HF state and display active sessions"""
        hf_state = loaded()
        sessions_display = display_active_sessions()
        return list(hf_state) + [sessions_display]

    demo.load(
        fn=on_load,
        js=js,
        outputs=[hf_token, hf_login, hf_logout, repo_owner, active_sessions_display]
    )

    refresh.click(update, inputs=listeners, outputs=[train_script, train_config, dataset_folder])
if __name__ == "__main__":
    cwd = os.path.dirname(os.path.abspath(__file__))
    demo.launch(server_name="0.0.0.0", server_port=7860, root_path="/proxy/7860", debug=True, show_error=True, allowed_paths=[cwd], show_api=False, share=True)
