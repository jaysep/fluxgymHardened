#!/bin/bash

cd /workspace/fluxgym
source env/bin/activate

python3 << 'EOF'
from accelerate import Accelerator
import inspect

print("=" * 80)
print("Checking how Accelerator.load_state accesses override_attributes['step']")
print("=" * 80)

acc = Accelerator()
source = inspect.getsource(acc.load_state)
lines = source.split('\n')

# Find where it accesses override_attributes["step"]
found_access = False
for i, line in enumerate(lines):
    if ('override_attributes' in line and 'step' in line) or ('self.step' in line and '=' in line):
        # Print context
        start = max(0, i-5)
        end = min(len(lines), i+6)
        print(f"\nFound at line {i}:")
        for j in range(start, end):
            marker = " >>> " if j == i else "     "
            print(f"{marker}{j:3d}: {lines[j]}")
        found_access = True

if not found_access:
    print("\nNo direct access to override_attributes['step'] found")
    print("Checking the full source...")
    for i, line in enumerate(lines):
        print(f"{i:3d}: {line}")
EOF
