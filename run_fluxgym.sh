#!/bin/bash
cd /workspace/fluxgym || exit 1
source env/bin/activate

export PYTHONWARNINGS="ignore"
export GRADIO_SERVER_NAME="0.0.0.0"

echo "🚀 Starting FluxGym..."

# Check if app.py has been patched
if grep -q 'root_path="/proxy/7860"' app.py; then
    echo "✅ Using patched app.py (proxy support built-in)"
    nohup python3 app.py & # ← NO arguments - the patch handles everything
else
    echo "⚠️ Using command line arguments for proxy support"
    nohup python3 app.py --server-name 0.0.0.0 --server-port 7860 --root-path /proxy/7860 &
fi
