#!/bin/bash

# Diagnostic script to run on the Runpod to understand the checkpoint issue

CHECKPOINT_DIR="/workspace/fluxgym/outputs/kristyhardened9/kristyhardened9-000030-state"

echo "=========================================="
echo "Checkpoint Diagnosis"
echo "=========================================="
echo ""
echo "Checkpoint directory: $CHECKPOINT_DIR"
echo ""

cd "$CHECKPOINT_DIR" || exit 1

echo "Files in checkpoint:"
ls -lh
echo ""

echo "=========================================="
echo "Checking for step information"
echo "=========================================="
echo ""

# Check train_state.json
if [ -f "train_state.json" ]; then
    echo "train_state.json exists:"
    cat train_state.json
    echo ""
fi

# Check if custom_checkpoint_0.pkl exists
if [ -f "custom_checkpoint_0.pkl" ]; then
    echo "custom_checkpoint_0.pkl exists!"
    python3 << 'EOF'
import pickle
with open('custom_checkpoint_0.pkl', 'rb') as f:
    data = pickle.load(f)
print(f"Keys: {list(data.keys())}")
if 'step' in data:
    print(f"step: {data['step']}")
if 'epoch' in data:
    print(f"epoch: {data['epoch']}")
EOF
else
    echo "custom_checkpoint_0.pkl DOES NOT EXIST"
fi

echo ""
echo "=========================================="
echo "Check accelerate version in environment"
echo "=========================================="
echo ""

cd /workspace/fluxgym
source env/bin/activate

python3 << 'EOF'
import accelerate
print(f"Accelerate version: {accelerate.__version__}")

# Try to understand what load_state does
import inspect
from pathlib import Path

acc_file = Path(inspect.getfile(accelerate.Accelerator))
print(f"Accelerator file: {acc_file}")

# Find the load_state method
acc = accelerate.Accelerator()
load_state_source = inspect.getsource(acc.load_state)

# Look for where it accesses 'step'
if 'override_attributes["step"]' in load_state_source:
    print("\nFound: override_attributes['step'] in load_state source")
    # Find the line
    for i, line in enumerate(load_state_source.split('\n')):
        if 'override_attributes["step"]' in line or "override_attributes['step']" in line:
            print(f"  Line {i}: {line.strip()}")
else:
    print("\nDid not find override_attributes['step'] in load_state source")

# Check what accelerate expects in a checkpoint
print("\nLet's check what save_state creates:")
import tempfile
import torch

with tempfile.TemporaryDirectory() as tmpdir:
    test_acc = accelerate.Accelerator()
    test_model = torch.nn.Linear(10, 10)
    test_opt = torch.optim.Adam(test_model.parameters())
    test_sched = torch.optim.lr_scheduler.StepLR(test_opt, step_size=1)
    test_model, test_opt, test_sched = test_acc.prepare(test_model, test_opt, test_sched)

    # Set a step
    test_acc.step = 360

    # Save
    state_path = Path(tmpdir) / "test_state"
    test_acc.save_state(str(state_path))

    print(f"\nFiles created by save_state() on this system:")
    for file in sorted(state_path.iterdir()):
        print(f"  {file.name}")

    # Check for custom_checkpoint
    if (state_path / "custom_checkpoint_0.pkl").exists():
        import pickle
        with open(state_path / "custom_checkpoint_0.pkl", 'rb') as f:
            data = pickle.load(f)
        print(f"\ncustom_checkpoint_0.pkl contains: {list(data.keys())}")
EOF

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo ""
echo "The checkpoint has train_state.json with step info,"
echo "but accelerate.load_state() is looking for custom_checkpoint_0.pkl"
echo "We need to understand WHY they don't match."
