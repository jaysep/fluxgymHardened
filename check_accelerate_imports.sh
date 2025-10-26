#!/bin/bash

cd /workspace/fluxgym
source env/bin/activate

python3 << 'EOF'
import accelerate
print(f"Accelerate version: {accelerate.__version__}")

import accelerate.checkpointing as chk
print(f"\nacceleratate.checkpointing attributes:")
attrs = [attr for attr in dir(chk) if not attr.startswith('_')]
for attr in attrs:
    print(f"  {attr}")

print(f"\nHas 'load': {hasattr(chk, 'load')}")

# Try to import directly
try:
    from accelerate.checkpointing import load
    print("✓ Can import: from accelerate.checkpointing import load")
    print(f"  load function: {load}")
except ImportError as e:
    print(f"✗ Cannot import load from checkpointing: {e}")

# Try utils
try:
    from accelerate.utils.other import load
    print("✓ Can import: from accelerate.utils.other import load")
    print(f"  load function: {load}")
except ImportError as e:
    print(f"✗ Cannot import from utils.other: {e}")

# Find where load_accelerator_state is defined and what it uses
from accelerate.checkpointing import load_accelerator_state
import inspect

source = inspect.getsource(load_accelerator_state)
print("\nIn load_accelerator_state, checking what 'load' is used:")
for i, line in enumerate(source.split('\n')[:20], 1):
    print(f"{i:3d}: {line}")
EOF
