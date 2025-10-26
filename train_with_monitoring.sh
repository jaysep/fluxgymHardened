#!/bin/bash
#
# FluxGym Training with Automatic Monitoring
#
# This script wraps FluxGym training with automatic monitoring and recovery.
# It will detect if training gets stuck and help you resume.
#
# Usage:
#   ./train_with_monitoring.sh <lora-name>
#
# Example:
#   ./train_with_monitoring.sh my-cat-lora
#

set -e

# Check arguments
if [ $# -eq 0 ]; then
    echo "Usage: $0 <lora-name>"
    echo "Example: $0 my-cat-lora"
    exit 1
fi

LORA_NAME="$1"
OUTPUT_DIR="outputs/$LORA_NAME"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONITOR_LOG="$OUTPUT_DIR/monitor.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== FluxGym Training with Monitoring ===${NC}"
echo ""
echo "LoRA Name: $LORA_NAME"
echo "Output Directory: $OUTPUT_DIR"
echo ""

# Check if output directory exists
if [ ! -d "$OUTPUT_DIR" ]; then
    echo -e "${RED}Error: Output directory not found: $OUTPUT_DIR${NC}"
    echo ""
    echo "Please start your training through FluxGym UI first."
    echo "This script is for monitoring an already configured training."
    exit 1
fi

# Check if training script exists
TRAIN_SCRIPT=""
if [ -f "$OUTPUT_DIR/train.sh" ]; then
    TRAIN_SCRIPT="$OUTPUT_DIR/train.sh"
elif [ -f "$OUTPUT_DIR/train.bat" ]; then
    TRAIN_SCRIPT="$OUTPUT_DIR/train.bat"
else
    echo -e "${YELLOW}Warning: Training script not found in $OUTPUT_DIR${NC}"
    echo "This is normal if you haven't started training yet."
fi

# Check if checkpoint exists (resuming?)
LATEST_CHECKPOINT=$($SCRIPT_DIR/find_checkpoint.py "$OUTPUT_DIR" --type state 2>/dev/null | grep "Latest state checkpoint:" | cut -d: -f2- | xargs)
if [ -n "$LATEST_CHECKPOINT" ]; then
    echo -e "${YELLOW}Found existing checkpoint: $LATEST_CHECKPOINT${NC}"
    echo ""
    read -p "Do you want to resume from this checkpoint? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}Please update your training in FluxGym UI:${NC}"
        echo "  1. Enter this in 'Resume from Checkpoint' field:"
        echo "     $LATEST_CHECKPOINT"
        echo "  2. Click 'Start training'"
        echo ""
        read -p "Press Enter when you've started training..."
    fi
fi

# Create output directory for logs
mkdir -p "$OUTPUT_DIR"

echo ""
echo -e "${GREEN}Starting monitoring...${NC}"
echo ""
echo "Monitor settings:"
echo "  - Check interval: 30 seconds"
echo "  - Stuck threshold: 5 minutes (300 seconds)"
echo "  - GPU threshold: 5% utilization"
echo ""
echo "Monitor log: $MONITOR_LOG"
echo ""
echo -e "${YELLOW}To view live logs:${NC}"
echo "  tail -f $MONITOR_LOG"
echo ""
echo -e "${YELLOW}To stop monitoring:${NC}"
echo "  Press Ctrl+C"
echo ""

# Start monitoring
python "$SCRIPT_DIR/training_monitor.py" \
    --output-dir "$OUTPUT_DIR" \
    --check-interval 30 \
    --stuck-threshold 300 \
    --gpu-threshold 5.0 \
    2>&1 | tee "$MONITOR_LOG"

echo ""
echo -e "${GREEN}Monitoring stopped.${NC}"
echo ""

# Check if training was completed or stuck
if grep -q "TRAINING STUCK DETECTED" "$MONITOR_LOG"; then
    echo -e "${RED}Training appears to have gotten stuck!${NC}"
    echo ""

    # Find latest checkpoint again
    LATEST_CHECKPOINT=$($SCRIPT_DIR/find_checkpoint.py "$OUTPUT_DIR" --type state 2>/dev/null | grep "Latest state checkpoint:" | cut -d: -f2- | xargs)

    if [ -n "$LATEST_CHECKPOINT" ]; then
        echo -e "${GREEN}Latest checkpoint found: $LATEST_CHECKPOINT${NC}"
        echo ""
        echo "To resume training:"
        echo "  1. Go to FluxGym UI"
        echo "  2. Enter this in 'Resume from Checkpoint' field:"
        echo "     $LATEST_CHECKPOINT"
        echo "  3. Click 'Start training'"
        echo ""
        echo "Or run this command to start monitoring again:"
        echo "  ./train_with_monitoring.sh $LORA_NAME"
    else
        echo -e "${YELLOW}No checkpoint found. You may need to restart training.${NC}"
        echo ""
        echo "Tips:"
        echo "  - Make sure 'Enable Checkpointing' is checked in FluxGym UI"
        echo "  - Training needs to complete at least one epoch to create a checkpoint"
    fi
else
    echo "Training completed or monitoring was stopped manually."
    echo ""
    echo "To check your results:"
    echo "  ls -lh $OUTPUT_DIR/"
fi
