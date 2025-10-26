#!/bin/bash

cd /workspace/fluxgym
source env/bin/activate

python3 << 'EOF'
import torch
from pathlib import Path

checkpoint_dir = Path("/workspace/fluxgym/outputs/kristyhardened9/kristyhardened9-000030-state")
random_states_file = checkpoint_dir / "random_states_0.pkl"

print("=" * 80)
print("Checking random_states_0.pkl for step information")
print("=" * 80)

if random_states_file.exists():
    print(f"\n✓ File exists: {random_states_file}")
    print(f"  Size: {random_states_file.stat().st_size} bytes")

    # Load it (need weights_only=False for pickle files with numpy data)
    states = torch.load(random_states_file, weights_only=False)

    print(f"\nKeys in random_states_0.pkl:")
    for key in states.keys():
        value = states[key]
        if isinstance(value, (int, float, str)):
            print(f"  {key}: {value}")
        else:
            print(f"  {key}: <{type(value).__name__}>")

    if 'step' in states:
        print(f"\n✓✓✓ FOUND IT! step = {states['step']}")
        print(f"This matches train_state.json current_step = 360")
    else:
        print(f"\n✗ 'step' key NOT found in random_states_0.pkl")
else:
    print(f"\n✗ File not found: {random_states_file}")
EOF
