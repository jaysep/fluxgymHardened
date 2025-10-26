#!/bin/bash

cd /workspace/fluxgym
source env/bin/activate

python3 << 'EOF'
import accelerate.checkpointing as chk

# Find where load is defined
print("Checking accelerate.checkpointing module:")
print(f"Has 'load' attribute: {hasattr(chk, 'load')}")

if hasattr(chk, 'load'):
    print(f"load is: {chk.load}")
    print(f"load module: {chk.load.__module__}")
else:
    print("\nListing all attributes:")
    for attr in dir(chk):
        if not attr.startswith('_'):
            print(f"  {attr}")

# Check what's imported at the module level
print("\nChecking source imports:")
import inspect
source_file = inspect.getsourcefile(chk)
with open(source_file, 'r') as f:
    for i, line in enumerate(f, 1):
        if 'from' in line and 'load' in line:
            print(f"  {i}: {line.rstrip()}")
        if i > 100:  # Just check first 100 lines
            break
EOF
