#!/bin/bash

# FluxGym Hardened Deployment Script
# This script downloads hardened files from GitHub and installs them on a running FluxGym pod
# Usage: bash deploy_hardened.sh [--dry-run]

set -e  # Exit on error

# Configuration
GITHUB_RAW_URL="https://raw.githubusercontent.com/jaysep/fluxgymHardened/main"
WORKSPACE_DIR="/workspace"
FLUXGYM_DIR="/workspace/fluxgym"
BACKUP_DIR="/workspace/fluxgym_backups/$(date +%Y%m%d_%H%M%S)"
DRY_RUN=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
if [ "$1" == "--dry-run" ]; then
    DRY_RUN=true
    echo -e "${YELLOW}DRY RUN MODE - No files will be modified${NC}"
fi

# Helper functions
print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Check if we're in the right location
check_environment() {
    print_header "Checking Environment"

    if [ ! -d "$FLUXGYM_DIR" ]; then
        print_error "FluxGym directory not found at $FLUXGYM_DIR"
        print_info "This script should be run on a Runpod pod with FluxGym installed"
        exit 1
    fi

    if [ ! -f "$FLUXGYM_DIR/app.py" ]; then
        print_error "app.py not found in $FLUXGYM_DIR"
        exit 1
    fi

    if [ ! -d "$FLUXGYM_DIR/sd-scripts" ]; then
        print_error "sd-scripts directory not found"
        exit 1
    fi

    print_success "Environment check passed"
    print_info "FluxGym directory: $FLUXGYM_DIR"
}

# Stop running FluxGym app
stop_app() {
    print_header "Stopping FluxGym App"

    if [ "$DRY_RUN" = true ]; then
        print_info "Would stop FluxGym app"
        return
    fi

    cd "$FLUXGYM_DIR"

    # Try to kill using PID file
    if [ -f "fluxgym.pid" ]; then
        local pid=$(cat fluxgym.pid)
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            print_success "Stopped FluxGym (PID: $pid)"
            sleep 2
        else
            print_warning "PID file exists but process not running"
        fi
    else
        print_warning "No PID file found"
    fi

    # Fallback: kill by process name
    if pgrep -f "python3 app.py" > /dev/null; then
        pkill -f "python3 app.py"
        print_success "Stopped FluxGym by process name"
        sleep 2
    fi

    # Verify it's stopped
    if pgrep -f "python3 app.py" > /dev/null; then
        print_error "Failed to stop FluxGym"
        exit 1
    else
        print_success "FluxGym stopped successfully"
    fi
}

# Create backup directory
create_backup_dir() {
    print_header "Creating Backup Directory"

    if [ "$DRY_RUN" = true ]; then
        print_info "Would create backup at: $BACKUP_DIR"
        return
    fi

    mkdir -p "$BACKUP_DIR"
    mkdir -p "$BACKUP_DIR/sd-scripts/library"
    print_success "Created backup directory: $BACKUP_DIR"
}

# Backup original files
backup_file() {
    local file_path="$1"
    local relative_path="${file_path#$FLUXGYM_DIR/}"
    local backup_path="$BACKUP_DIR/$relative_path"

    if [ ! -f "$file_path" ]; then
        print_warning "File not found (will be created): $relative_path"
        return
    fi

    if [ "$DRY_RUN" = true ]; then
        print_info "Would backup: $relative_path"
        return
    fi

    # Create parent directory if needed
    mkdir -p "$(dirname "$backup_path")"

    # Copy file
    cp "$file_path" "$backup_path"
    print_success "Backed up: $relative_path"
}

# Download file from GitHub
download_file() {
    local github_path="$1"
    local local_path="$2"
    local relative_path="${local_path#$FLUXGYM_DIR/}"

    if [ "$DRY_RUN" = true ]; then
        print_info "Would download: $relative_path"
        return
    fi

    local url="$GITHUB_RAW_URL/$github_path"

    # Download with curl
    if curl -f -s -o "$local_path" "$url"; then
        print_success "Downloaded: $relative_path"
    else
        print_error "Failed to download: $github_path"
        print_error "URL: $url"
        exit 1
    fi
}

# Main deployment function
deploy_files() {
    print_header "Backing Up Original Files"

    # Backup all files that will be replaced
    backup_file "$WORKSPACE_DIR/run_fluxgym.sh"
    backup_file "$FLUXGYM_DIR/app.py"
    backup_file "$FLUXGYM_DIR/training_monitor.py"
    backup_file "$FLUXGYM_DIR/find_checkpoint.py"
    backup_file "$FLUXGYM_DIR/sd-scripts/flux_train.py"
    backup_file "$FLUXGYM_DIR/sd-scripts/train_network.py"
    backup_file "$FLUXGYM_DIR/sd-scripts/library/custom_offloading_utils.py"
    backup_file "$FLUXGYM_DIR/sd-scripts/library/strategy_base.py"
    backup_file "$FLUXGYM_DIR/sd-scripts/library/train_util.py"

    print_header "Downloading Hardened Files from GitHub"

    # Download core application files
    print_info "Downloading core application files..."
    download_file "run_fluxgym.sh" "$WORKSPACE_DIR/run_fluxgym.sh"
    download_file "app.py" "$FLUXGYM_DIR/app.py"
    download_file "training_monitor.py" "$FLUXGYM_DIR/training_monitor.py"
    download_file "find_checkpoint.py" "$FLUXGYM_DIR/find_checkpoint.py"

    # Make scripts executable
    if [ "$DRY_RUN" = false ]; then
	chmod +x "$WORKSPACE_DIR/run_fluxgym.sh" 2>/dev/null || true
        chmod +x "$FLUXGYM_DIR/training_monitor.py" 2>/dev/null || true
        chmod +x "$FLUXGYM_DIR/find_checkpoint.py" 2>/dev/null || true
    fi

    # Download hang prevention files
    print_info "Downloading hang prevention files..."
    download_file "sd-scripts/flux_train.py" "$FLUXGYM_DIR/sd-scripts/flux_train.py"
    download_file "sd-scripts/library/custom_offloading_utils.py" "$FLUXGYM_DIR/sd-scripts/library/custom_offloading_utils.py"
    download_file "sd-scripts/library/strategy_base.py" "$FLUXGYM_DIR/sd-scripts/library/strategy_base.py"

    # Download training resumption files
    print_info "Downloading training resumption files..."
    download_file "sd-scripts/train_network.py" "$FLUXGYM_DIR/sd-scripts/train_network.py"
    download_file "sd-scripts/library/train_util.py" "$FLUXGYM_DIR/sd-scripts/library/train_util.py"

    print_success "All files downloaded successfully"
}

# Verify downloaded files
verify_files() {
    print_header "Verifying Downloaded Files"

    local all_good=true

    # Check core files
    if [ -f "$WORKSPACE_DIR/app.py" ]; then
        if grep -q "nohup" "$WORKSPACE_DIR/run_fluxgym.sh"; then
            print_success "run_fluxgym.sh has hardened features"
        else
            print_error "run_fluxgym.sh missing hardened features"
            all_good=false
        fi
    else
        print_error "run_fluxgym not found"
        all_good=false
    fi

    if [ -f "$FLUXGYM_DIR/app.py" ]; then
        if grep -q "enable_monitoring" "$FLUXGYM_DIR/app.py"; then
            print_success "app.py has hardened features"
        else
            print_error "app.py missing hardened features"
            all_good=false
        fi
    else
        print_error "app.py not found"
        all_good=false
    fi

    if [ -f "$FLUXGYM_DIR/training_monitor.py" ]; then
        if grep -q "Monitor GPU usage" "$FLUXGYM_DIR/training_monitor.py"; then
            print_success "training_monitor.py looks correct"
        else
            print_warning "training_monitor.py may not be correct version"
        fi
    else
        print_error "training_monitor.py not found"
        all_good=false
    fi

    # Check hang prevention files
    if [ -f "$FLUXGYM_DIR/sd-scripts/flux_train.py" ]; then
        if grep -q "timeout=60" "$FLUXGYM_DIR/sd-scripts/flux_train.py"; then
            print_success "flux_train.py has timeout fix"
        else
            print_error "flux_train.py missing timeout fix"
            all_good=false
        fi
    else
        print_error "flux_train.py not found"
        all_good=false
    fi

    if [ -f "$FLUXGYM_DIR/sd-scripts/library/custom_offloading_utils.py" ]; then
        if grep -q "timeout=30" "$FLUXGYM_DIR/sd-scripts/library/custom_offloading_utils.py"; then
            print_success "custom_offloading_utils.py has timeout fix"
        else
            print_warning "custom_offloading_utils.py may not have timeout fix"
        fi
    else
        print_error "custom_offloading_utils.py not found"
        all_good=false
    fi

    if [ -f "$FLUXGYM_DIR/sd-scripts/library/strategy_base.py" ]; then
        if grep -q "timeout_context" "$FLUXGYM_DIR/sd-scripts/library/strategy_base.py"; then
            print_success "strategy_base.py has timeout fix"
        else
            print_warning "strategy_base.py may not have timeout fix"
        fi
    else
        print_error "strategy_base.py not found"
        all_good=false
    fi

    # check training resumption files
    if [ -f "$FLUXGYM_DIR/sd-scripts/train_network.py" ]; then
        if grep -q "save_and_remove_state_on_epoch_end(args, accelerator, epoch + 1, global_step)" "$FLUXGYM_DIR/sd-scripts/train_network.py"; then
            print_success "train_network.py has training fix"
        else
            print_error "train_network.py missing training fix"
            all_good=false
        fi
    else
        print_error "train_network.py not found"
        all_good=false
    fi

    if [ -f "$FLUXGYM_DIR/sd-scripts/library/train_util.py" ]; then
        if grep -q "# FIX: Manually set accelerator.step from checkpoint before loading" "$FLUXGYM_DIR/sd-scripts/library/train_util.py"; then
            print_success "train_util.py has training fix"
        else
            print_warning "train_util.py may not have training fix"
        fi
    else
        print_error "train_util.py not found"
        all_good=false
    fi

    if [ "$all_good" = false ]; then
        print_error "Verification failed - some files are missing or incorrect"
        exit 1
    fi

    print_success "All files verified successfully"
}

# Start FluxGym app
start_app() {
    print_header "Starting FluxGym App"

    if [ "$DRY_RUN" = true ]; then
        print_info "Would start FluxGym using run_fluxgym.sh"
        return
    fi

    cd "$WORKSPACE_DIR"
    
    local autostart = true
    if [ ! -f "run_fluxgym.sh" ]; then
        print_error "run_fluxgym.sh not found"
        print_info "Please start manually..."
	autostart = false
        # Fallback: start manually
        #source env/bin/activate
        #export PYTHONWARNINGS="ignore"
        #nohup python3 app.py > fluxgym.log 2>&1 &
        #echo $! > fluxgym.pid
    else
        # Use their startup script
        bash run_fluxgym.sh &
    fi

    if [ "$autostart" = true ]; then
    	print_success "FluxGym started"
    	print_info "Waiting 5 seconds for startup..."
    	sleep 5
    fi
}

# Check if app started successfully
check_app() {
    print_header "Checking App Status"

    if [ "$DRY_RUN" = true ]; then
        print_info "Would check if app started successfully"
        return
    fi

    cd "$FLUXGYM_DIR"

    # Check if process is running
    if pgrep -f "python3 app.py" > /dev/null; then
        print_success "FluxGym process is running"
    else
        print_error "FluxGym process not found"
        print_info "Check logs: tail -f $FLUXGYM_DIR/fluxgym.log"
        exit 1
    fi

    # Check logs for errors
    if [ -f "fluxgym.log" ]; then
        # Look for recent errors
        if tail -20 fluxgym.log | grep -i "error\|traceback\|exception" > /dev/null; then
            print_warning "Errors detected in logs (may be startup warnings)"
            print_info "Check logs: tail -f $FLUXGYM_DIR/fluxgym.log"
        else
            print_success "No errors detected in recent logs"
        fi

        # Look for success indicators
        if tail -20 fluxgym.log | grep -i "Running on local URL" > /dev/null; then
            print_success "FluxGym UI is running!"
        else
            print_warning "UI may still be starting up..."
        fi
    fi
}

# Print summary
print_summary() {
    print_header "Deployment Summary"

    if [ "$DRY_RUN" = true ]; then
        print_info "DRY RUN completed - no changes made"
        echo ""
        print_info "Run without --dry-run to apply changes:"
        echo "  bash deploy_hardened.sh"
        return
    fi

    echo ""
    print_success "Hardened FluxGym deployed successfully!"
    echo ""
    print_info "Backup location: $BACKUP_DIR"
    print_info "View logs: tail -f $FLUXGYM_DIR/fluxgym.log"
    echo ""
    print_info "Features enabled:"
    echo "  ✓ State persistence (sessions, active runs)"
    echo "  ✓ Training log persistence"
    echo "  ✓ GPU monitoring & hang detection"
    echo "  ✓ Auto-resume/restart from checkpoints"
    echo "  ✓ DataLoader timeout (60s)"
    echo "  ✓ Block swap timeout (30s)"
    echo "  ✓ File I/O timeout (30s)"
    echo ""
    print_info "Access FluxGym via Runpod Connect → HTTP Service [Port 7860]"
    echo ""
    print_warning "To rollback if needed:"
    echo "  bash rollback_hardened.sh $BACKUP_DIR"
}

# Create rollback script
create_rollback_script() {
    if [ "$DRY_RUN" = true ]; then
        return
    fi

    local rollback_script="/workspace/rollback_hardened.sh"

    cat > "$rollback_script" << 'ROLLBACK_EOF'
#!/bin/bash

# FluxGym Hardened Rollback Script
# Usage: bash rollback_hardened.sh <backup_directory>

if [ -z "$1" ]; then
    echo "Usage: bash rollback_hardened.sh <backup_directory>"
    echo "Example: bash rollback_hardened.sh /workspace/fluxgym_backups/20250126_123456"
    exit 1
fi

BACKUP_DIR="$1"
FLUXGYM_DIR="/workspace/fluxgym"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "Backup directory not found: $BACKUP_DIR"
    exit 1
fi

echo "Rolling back from: $BACKUP_DIR"
echo "Stopping FluxGym..."

cd "$FLUXGYM_DIR"
kill $(cat fluxgym.pid 2>/dev/null) 2>/dev/null || pkill -f "python3 app.py"
sleep 2

echo "Restoring files..."
cp -v "$BACKUP_DIR/app.py" "$FLUXGYM_DIR/app.py" 2>/dev/null || echo "Skipped: app.py"
cp -v "$BACKUP_DIR/training_monitor.py" "$FLUXGYM_DIR/training_monitor.py" 2>/dev/null || echo "Skipped: training_monitor.py"
cp -v "$BACKUP_DIR/find_checkpoint.py" "$FLUXGYM_DIR/find_checkpoint.py" 2>/dev/null || echo "Skipped: find_checkpoint.py"
cp -v "$BACKUP_DIR/sd-scripts/flux_train.py" "$FLUXGYM_DIR/sd-scripts/flux_train.py" 2>/dev/null || echo "Skipped: flux_train.py"
cp -v "$BACKUP_DIR/sd-scripts/library/custom_offloading_utils.py" "$FLUXGYM_DIR/sd-scripts/library/custom_offloading_utils.py" 2>/dev/null || echo "Skipped: custom_offloading_utils.py"
cp -v "$BACKUP_DIR/sd-scripts/library/strategy_base.py" "$FLUXGYM_DIR/sd-scripts/library/strategy_base.py" 2>/dev/null || echo "Skipped: strategy_base.py"
cp -v "$BACKUP_DIR/sd-scripts/train_network.py" "$FLUXGYM_DIR/sd-scripts/train_network.py" 2>/dev/null || echo "Skipped: train_network.py"
cp -v "$BACKUP_DIR/sd-scripts/library/train_util.py" "$FLUXGYM_DIR/sd-scripts/library/train_util.py" 2>/dev/null || echo "Skipped: train_util.py"

echo "Restarting FluxGym..."
cd "$FLUXGYM_DIR"
bash run_fluxgym.sh &

echo "Rollback complete!"
echo "Check logs: tail -f $FLUXGYM_DIR/fluxgym.log"
ROLLBACK_EOF

    chmod +x "$rollback_script"
    print_success "Created rollback script: $rollback_script"
}

# Main execution
main() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════╗"
    echo "║   FluxGym Hardened Deployment Script          ║"
    echo "║   github.com/jaysep/fluxgymHardened           ║"
    echo "╚════════════════════════════════════════════════╝"
    echo -e "${NC}"

    check_environment
    stop_app
    create_backup_dir
    deploy_files
    verify_files
    create_rollback_script
    start_app
    check_app
    print_summary
}

# Run main function
main
