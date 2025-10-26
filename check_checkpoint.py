#!/usr/bin/env python3
"""
Diagnostic script to check checkpoint validity.

Usage:
    python3 check_checkpoint.py /workspace/fluxgym/outputs/your-lora/your-lora-000030-state
"""

import sys
import os
from pathlib import Path
import pickle

def check_checkpoint(checkpoint_path):
    """Check if a checkpoint is valid for resume"""

    checkpoint = Path(checkpoint_path)

    print("=" * 80)
    print(f"Checking checkpoint: {checkpoint}")
    print("=" * 80)

    # Check if directory exists
    if not checkpoint.exists():
        print(f"❌ ERROR: Checkpoint directory does not exist")
        return False

    if not checkpoint.is_dir():
        print(f"❌ ERROR: Path is not a directory")
        return False

    print(f"✓ Checkpoint directory exists")

    # Required files for accelerate checkpoint
    required_files = [
        'custom_checkpoint_0.pkl',  # Training metadata
        'optimizer.bin',             # Optimizer state
        'random_states_0.pkl',       # RNG states
        'scheduler.bin'              # LR scheduler state
    ]

    print("\nChecking required files:")
    print("-" * 80)

    all_files_ok = True

    for required_file in required_files:
        file_path = checkpoint / required_file

        if not file_path.exists():
            print(f"❌ MISSING: {required_file}")
            all_files_ok = False
        else:
            size = file_path.stat().st_size
            if size == 0:
                print(f"❌ EMPTY: {required_file} (0 bytes)")
                all_files_ok = False
            else:
                size_mb = size / (1024 * 1024)
                print(f"✓ OK: {required_file} ({size_mb:.2f} MB)")

    if not all_files_ok:
        print("\n" + "=" * 80)
        print("❌ CHECKPOINT IS INVALID - Missing or empty required files")
        print("=" * 80)
        return False

    # Check metadata
    print("\nChecking metadata:")
    print("-" * 80)

    try:
        metadata_path = checkpoint / 'custom_checkpoint_0.pkl'

        with open(metadata_path, 'rb') as f:
            data = pickle.load(f)

        print(f"Metadata keys: {list(data.keys())}")

        # Check for required keys
        if 'step' not in data:
            print(f"❌ ERROR: Metadata missing 'step' key - THIS WILL CAUSE RESUME TO FAIL")
            print(f"   Available keys: {list(data.keys())}")
            print("\n" + "=" * 80)
            print("❌ CHECKPOINT IS INVALID - Missing 'step' in metadata")
            print("=" * 80)
            return False

        # Print metadata info
        print(f"\nCheckpoint Information:")
        print(f"  Step: {data.get('step', 'N/A')}")
        print(f"  Epoch: {data.get('epoch', 'N/A')}")

        # Print all available metadata
        print(f"\nAll metadata:")
        for key, value in data.items():
            if isinstance(value, (int, float, str, bool, type(None))):
                print(f"  {key}: {value}")
            else:
                print(f"  {key}: <{type(value).__name__}>")

    except Exception as e:
        print(f"❌ ERROR reading metadata: {e}")
        print("\n" + "=" * 80)
        print("❌ CHECKPOINT IS INVALID - Cannot read metadata")
        print("=" * 80)
        return False

    # List all files in checkpoint
    print("\nAll files in checkpoint:")
    print("-" * 80)

    all_files = sorted(checkpoint.iterdir())
    for file_path in all_files:
        if file_path.is_file():
            size = file_path.stat().st_size
            size_mb = size / (1024 * 1024)
            print(f"  {file_path.name}: {size_mb:.2f} MB")
        elif file_path.is_dir():
            print(f"  {file_path.name}/ (directory)")

    print("\n" + "=" * 80)
    print("✅ CHECKPOINT IS VALID - Can be used for resume")
    print("=" * 80)

    return True

def scan_all_checkpoints(output_dir):
    """Scan all checkpoints in an output directory"""

    output_path = Path(output_dir)

    if not output_path.exists():
        print(f"❌ ERROR: Output directory does not exist: {output_dir}")
        return

    print("=" * 80)
    print(f"Scanning for checkpoints in: {output_dir}")
    print("=" * 80)

    # Find all state directories
    checkpoints = []
    for item in output_path.iterdir():
        if item.is_dir() and 'state' in item.name.lower():
            checkpoints.append(item)

    if not checkpoints:
        print("\n❌ No checkpoint directories found")
        return

    # Sort by modification time
    checkpoints.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    print(f"\nFound {len(checkpoints)} checkpoint(s):\n")

    valid_checkpoints = []

    for i, checkpoint in enumerate(checkpoints, 1):
        print(f"\n{'='*80}")
        print(f"Checkpoint {i}/{len(checkpoints)}: {checkpoint.name}")
        print(f"{'='*80}")

        is_valid = check_checkpoint(checkpoint)

        if is_valid:
            valid_checkpoints.append(checkpoint)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total checkpoints found: {len(checkpoints)}")
    print(f"Valid checkpoints: {len(valid_checkpoints)}")
    print(f"Invalid checkpoints: {len(checkpoints) - len(valid_checkpoints)}")

    if valid_checkpoints:
        print(f"\n✅ Latest valid checkpoint:")
        print(f"   {valid_checkpoints[0]}")
        print(f"\n   Use this for resume:")
        print(f"   --resume {valid_checkpoints[0]}")
    else:
        print(f"\n❌ No valid checkpoints found")
        print(f"   You will need to restart training from the beginning")

    print("=" * 80)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Check specific checkpoint:")
        print("    python3 check_checkpoint.py /workspace/fluxgym/outputs/my-lora/my-lora-000030-state")
        print("")
        print("  Scan all checkpoints in output directory:")
        print("    python3 check_checkpoint.py /workspace/fluxgym/outputs/my-lora")
        sys.exit(1)

    path = sys.argv[1]
    path_obj = Path(path)

    if not path_obj.exists():
        print(f"❌ ERROR: Path does not exist: {path}")
        sys.exit(1)

    if path_obj.is_dir() and not 'state' in path_obj.name.lower():
        # Looks like an output directory, scan all checkpoints
        scan_all_checkpoints(path)
    else:
        # Specific checkpoint
        is_valid = check_checkpoint(path)
        sys.exit(0 if is_valid else 1)
