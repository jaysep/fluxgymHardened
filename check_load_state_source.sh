#!/bin/bash

cd /workspace/fluxgym
source env/bin/activate

python3 << 'EOF'
from accelerate import Accelerator
import inspect

acc = Accelerator()
source = inspect.getsource(acc.load_state)

print("=" * 80)
print("Full load_state source code:")
print("=" * 80)

lines = source.split('\n')
for i, line in enumerate(lines):
    print(f"{i:4d}: {line}")

print()
print("=" * 80)
print("Looking for where override_attributes is created:")
print("=" * 80)

# Find load_accelerator_state function
from accelerate.checkpointing import load_accelerator_state
load_acc_source = inspect.getsource(load_accelerator_state)

print("\nload_accelerator_state function:")
load_lines = load_acc_source.split('\n')
for i, line in enumerate(load_lines):
    if i < 100:  # First 100 lines
        print(f"{i:4d}: {line}")
EOF
