#!/bin/bash

# Test script for training monitor auto-resume functionality
# This creates a mock training scenario to test the monitor

set -e

echo "=========================================="
echo "Training Monitor Auto-Resume Test"
echo "=========================================="
echo ""

# Configuration
TEST_DIR="/tmp/test_monitor_resume"
OUTPUT_DIR="$TEST_DIR/outputs/test-lora"
TRAIN_SCRIPT="$OUTPUT_DIR/train.sh"

# Clean up previous test
rm -rf "$TEST_DIR"
mkdir -p "$OUTPUT_DIR"

echo "Test directory: $TEST_DIR"
echo ""

# Create a mock train.sh script
echo "Creating mock training script..."
cat > "$TRAIN_SCRIPT" << 'EOF'
#!/bin/bash

# Mock training script that simulates training
echo "Starting mock training..."
echo "Loading model..."
sleep 2
echo "Training epoch 1/10..."
sleep 2
echo "Training epoch 2/10..."
sleep 2
echo "Saving checkpoint at step 150..."

# Create mock checkpoint
mkdir -p "$OUTPUT_DIR/test-lora-step-150-state"
echo "mock checkpoint" > "$OUTPUT_DIR/test-lora-step-150-state/checkpoint.txt"

sleep 2
echo "Training epoch 3/10..."
sleep 2

# Simulate hang - just sleep forever
echo "Simulating hang (sleeping forever)..."
sleep 999999
EOF

chmod +x "$TRAIN_SCRIPT"
echo "✓ Created: $TRAIN_SCRIPT"
echo ""

# Create mock dataset.toml (referenced in train scripts)
cat > "$OUTPUT_DIR/dataset.toml" << 'EOF'
# Mock dataset config
[[datasets]]
resolution = 512
batch_size = 1
EOF

echo "✓ Created: $OUTPUT_DIR/dataset.toml"
echo ""

echo "=========================================="
echo "Test Scenario 1: Resume from Checkpoint"
echo "=========================================="
echo ""

echo "Step 1: Start mock training (will hang after creating checkpoint)"
echo "Command: bash $TRAIN_SCRIPT"
echo ""

# Start training in background
export OUTPUT_DIR
nohup bash "$TRAIN_SCRIPT" > "$OUTPUT_DIR/training.log" 2>&1 &
TRAIN_PID=$!

echo "✓ Training started with PID: $TRAIN_PID"
echo "  Waiting 15 seconds for training to reach hung state..."
sleep 15

echo ""
echo "Step 2: Check if checkpoint was created"
if [ -d "$OUTPUT_DIR/test-lora-step-150-state" ]; then
    echo "✓ Checkpoint found: $OUTPUT_DIR/test-lora-step-150-state"
else
    echo "✗ Checkpoint not found - test may have failed"
    exit 1
fi

echo ""
echo "Step 3: Check if training process is still running (simulating hang)"
if ps -p $TRAIN_PID > /dev/null; then
    echo "✓ Training process still running (hung state simulated)"
else
    echo "✗ Training process died unexpectedly"
    exit 1
fi

echo ""
echo "Step 4: Start training monitor with auto-resume"
echo "Command: python3 training_monitor.py --output-dir $OUTPUT_DIR --train-script $TRAIN_SCRIPT --auto-resume --stuck-threshold 10 --check-interval 5"
echo ""
echo "NOTE: This test uses short timeouts (10s stuck threshold, 5s check interval)"
echo "      In production, use 300s stuck threshold and 30s check interval"
echo ""

# Kill the hung training
echo "Killing hung training process to simulate stuck detection..."
kill $TRAIN_PID 2>/dev/null || true
sleep 2

echo ""
echo "✓ Test setup complete!"
echo ""
echo "=========================================="
echo "Manual Verification Steps"
echo "=========================================="
echo ""
echo "1. Examine the mock train.sh script:"
echo "   cat $TRAIN_SCRIPT"
echo ""
echo "2. Check if checkpoint exists:"
echo "   ls -la $OUTPUT_DIR/"
echo ""
echo "3. Run the monitor (it will detect no active training and wait):"
echo "   python3 training_monitor.py \\"
echo "     --output-dir $OUTPUT_DIR \\"
echo "     --train-script $TRAIN_SCRIPT \\"
echo "     --auto-resume \\"
echo "     --stuck-threshold 10 \\"
echo "     --check-interval 5"
echo ""
echo "4. Expected behavior:"
echo "   - Monitor checks GPU every 5 seconds"
echo "   - If GPU stays at 0% for 10 seconds, training is 'stuck'"
echo "   - Monitor kills processes (if any)"
echo "   - Monitor finds checkpoint: test-lora-step-150-state"
echo "   - Monitor modifies train.sh to add: --resume <checkpoint>"
echo "   - Monitor executes train.sh"
echo ""
echo "5. Examine modified train.sh after monitor runs:"
echo "   cat $TRAIN_SCRIPT"
echo "   (should contain '--resume' line)"
echo ""
echo "=========================================="
echo "Test Scenario 2: Restart from Beginning"
echo "=========================================="
echo ""
echo "To test restart without checkpoint:"
echo ""
echo "1. Remove checkpoint directory:"
echo "   rm -rf $OUTPUT_DIR/test-lora-step-150-state"
echo ""
echo "2. Restore original train.sh (remove --resume line)"
echo ""
echo "3. Run monitor again - it should restart from beginning"
echo ""
echo "=========================================="
echo "Cleanup"
echo "=========================================="
echo ""
echo "To clean up test files:"
echo "  rm -rf $TEST_DIR"
echo ""
