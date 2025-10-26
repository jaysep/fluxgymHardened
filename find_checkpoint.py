#!/usr/bin/env python3
"""
Helper script to find the latest checkpoint for a FluxGym training run.

Usage:
    python find_checkpoint.py outputs/my-lora
    python find_checkpoint.py outputs/my-lora --type state
    python find_checkpoint.py outputs/my-lora --type model
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime


def find_latest_state_checkpoint(output_dir: Path):
    """Find the latest state checkpoint directory"""
    if not output_dir.exists():
        print(f"Error: Directory does not exist: {output_dir}")
        return None

    state_dirs = []
    for item in output_dir.iterdir():
        if item.is_dir() and 'state' in item.name.lower():
            state_dirs.append(item)

    if not state_dirs:
        print(f"No state checkpoints found in {output_dir}")
        return None

    # Sort by modification time, most recent first
    state_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return state_dirs[0]


def find_latest_model_checkpoint(output_dir: Path):
    """Find the latest model checkpoint (.safetensors file)"""
    if not output_dir.exists():
        print(f"Error: Directory does not exist: {output_dir}")
        return None

    safetensors_files = list(output_dir.glob("*.safetensors"))
    if not safetensors_files:
        print(f"No .safetensors model checkpoints found in {output_dir}")
        return None

    # Sort by modification time, most recent first
    safetensors_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return safetensors_files[0]


def list_all_checkpoints(output_dir: Path):
    """List all available checkpoints"""
    print(f"\n=== Checkpoints in {output_dir} ===\n")

    # State checkpoints
    state_dirs = []
    for item in output_dir.iterdir():
        if item.is_dir() and 'state' in item.name.lower():
            state_dirs.append(item)

    if state_dirs:
        state_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        print("State Checkpoints (for resume):")
        for i, state_dir in enumerate(state_dirs):
            mtime = datetime.fromtimestamp(state_dir.stat().st_mtime)
            marker = " <-- LATEST" if i == 0 else ""
            print(f"  [{i+1}] {state_dir.name} ({mtime.strftime('%Y-%m-%d %H:%M:%S')}){marker}")
    else:
        print("State Checkpoints: None found")

    # Model checkpoints
    safetensors_files = list(output_dir.glob("*.safetensors"))
    if safetensors_files:
        safetensors_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        print("\nModel Checkpoints (.safetensors):")
        for i, model_file in enumerate(safetensors_files):
            mtime = datetime.fromtimestamp(model_file.stat().st_mtime)
            size_mb = model_file.stat().st_size / (1024 * 1024)
            marker = " <-- LATEST" if i == 0 else ""
            print(f"  [{i+1}] {model_file.name} ({size_mb:.1f} MB, {mtime.strftime('%Y-%m-%d %H:%M:%S')}){marker}")
    else:
        print("\nModel Checkpoints: None found")


def main():
    parser = argparse.ArgumentParser(
        description="Find checkpoints for FluxGym training runs"
    )
    parser.add_argument(
        'output_dir',
        type=str,
        help='Output directory (e.g., outputs/my-lora)'
    )
    parser.add_argument(
        '--type',
        choices=['state', 'model', 'all'],
        default='all',
        help='Type of checkpoint to find (default: all)'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all checkpoints instead of just the latest'
    )

    args = parser.parse_args()
    output_dir = Path(args.output_dir)

    if not output_dir.exists():
        print(f"Error: Directory does not exist: {output_dir}")
        sys.exit(1)

    if args.list:
        list_all_checkpoints(output_dir)
        return

    if args.type in ['state', 'all']:
        latest_state = find_latest_state_checkpoint(output_dir)
        if latest_state:
            print(f"Latest state checkpoint: {latest_state}")
            print(f"\nTo resume training, add this to your training command:")
            print(f"  --resume {latest_state}")
            print(f"\nOr in FluxGym UI, enter this in 'Resume from Checkpoint' field:")
            print(f"  {latest_state}")

    if args.type in ['model', 'all']:
        if args.type == 'all':
            print()  # Add spacing
        latest_model = find_latest_model_checkpoint(output_dir)
        if latest_model:
            mtime = datetime.fromtimestamp(latest_model.stat().st_mtime)
            size_mb = latest_model.stat().st_size / (1024 * 1024)
            print(f"Latest model checkpoint: {latest_model}")
            print(f"  Size: {size_mb:.1f} MB")
            print(f"  Modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    main()
