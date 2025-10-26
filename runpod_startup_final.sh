bash -c '
echo "================================================================"
echo "   FluxGym Hardened - Automatic Setup"
echo "   Repository: https://github.com/jaysep/fluxgymHardened"
echo "================================================================"

echo "[1/5] Setting up VS Code Server..."
if [ ! -f "/usr/bin/code-server" ]; then
    echo "Installing code-server..."
    curl -fsSL https://code-server.dev/install.sh | sh
    echo "✓ code-server installed"
else
    echo "✓ code-server already installed"
fi

nohup code-server --bind-addr 0.0.0.0:8888 --auth none /workspace > /workspace/code-server.log 2>&1 &
CODE_SERVER_PID=$!
echo $CODE_SERVER_PID > /workspace/code-server.pid
echo "✓ VS Code Server started (PID: $CODE_SERVER_PID)"

echo "[2/5] Cloning FluxGym repository..."
cd /workspace

if [ ! -d "fluxgym" ]; then
    echo "Cloning fluxgymHardened from GitHub..."
    git clone --depth 1 https://github.com/jaysep/fluxgymHardened.git fluxgym
    echo "✓ Repository cloned"
else
    echo "Updating existing installation..."
    cd fluxgym
    git pull
    cd ..
    echo "✓ Repository updated"
fi

echo "[3/5] Installing Python dependencies..."
cd /workspace/fluxgym

echo "Installing sd-scripts core dependencies (this may take 1-2 minutes)..."
pip install --no-cache-dir accelerate transformers diffusers[torch] bitsandbytes safetensors huggingface-hub

echo "Installing sd-scripts additional dependencies..."
pip install --no-cache-dir toml einops opencv-python sentencepiece rich

echo "Installing FluxGym UI dependencies..."
pip install --no-cache-dir gradio python-slugify pyyaml imagesize

echo "Installing LoRA dependencies..."
pip install --no-cache-dir peft lycoris-lora==1.8.3

echo "Installing gradio_logsview..."
pip install --no-cache-dir gradio_logsview@https://huggingface.co/spaces/cocktailpeanut/gradio_logsview/resolve/main/gradio_logsview-0.0.17-py3-none-any.whl

echo "✓ All dependencies installed"

echo "[4/5] Starting FluxGym..."
cd /workspace/fluxgym

# Patch app.py for Runpod compatibility
echo "Patching Gradio launch configuration for Runpod..."
sed -i 's/demo.launch(server_name="0.0.0.0", server_port=7860, root_path="\/proxy\/7860", debug=True, show_error=True, allowed_paths=\[cwd\])/demo.launch(server_name="0.0.0.0", server_port=7860, debug=True, show_error=True, allowed_paths=[cwd], share=False)/' app.py
echo "✓ Gradio configuration patched"

nohup python app.py > fluxgym.log 2>&1 &
FLUXGYM_PID=$!
echo $FLUXGYM_PID > fluxgym.pid

sleep 3

if ps -p $FLUXGYM_PID > /dev/null; then
    echo "✓ FluxGym started successfully (PID: $FLUXGYM_PID)"
else
    echo "✗ FluxGym failed to start. Check logs:"
    tail -n 20 fluxgym.log
fi

echo "[5/5] Ready!"
echo "================================================================"
echo "   FluxGym Hardened is running!"
echo "================================================================"
echo ""
echo "Access Services:"
echo "  → FluxGym UI: Click '\''Connect'\'' → '\''HTTP Service [Port 7860]'\''"
echo "  → VS Code: Click '\''Connect'\'' → '\''HTTP Service [Port 8888]'\''"
echo ""
echo "VS Code Info:"
echo "  → No password required (--auth none)"
echo "  → Direct access to /workspace with all files"
echo "  → Built-in terminal for commands"
echo ""
echo "Logs:"
echo "  → FluxGym: tail -f /workspace/fluxgym/fluxgym.log"
echo "  → VS Code: tail -f /workspace/code-server.log"
echo ""
echo "Process IDs:"
echo "  → FluxGym PID: $(cat /workspace/fluxgym/fluxgym.pid)"
echo "  → VS Code PID: $(cat /workspace/code-server.pid)"
echo ""
echo "Features enabled:"
echo "  ✓ Hang prevention (timeout fixes)"
echo "  ✓ Automatic monitoring (GPU stuck detection)"
echo "  ✓ State persistence (survives disconnects)"
echo "  ✓ Training log persistence (view after refresh)"
echo "  ✓ Success verification (no false positives)"
echo "  ✓ VS Code Server (browser-based editor)"
echo ""
echo "Documentation: /workspace/fluxgym/*.md"
echo "================================================================"

tail -f /workspace/fluxgym/fluxgym.log
'
