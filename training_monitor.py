#!/usr/bin/env python3
"""
FluxGym Training Monitor and Auto-Recovery Script

This script monitors GPU usage during training and automatically detects
when training gets stuck (GPU usage drops to 0%). It can:
1. Alert the user when training is stuck
2. Kill stuck Python processes
3. Automatically resume training from the last checkpoint

Usage:
    python training_monitor.py --output-dir outputs/my-lora --check-interval 30 --stuck-threshold 300 --auto-resume
"""

import os
import sys
import time
import argparse
import subprocess
import signal
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('training_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GPUMonitor:
    """Monitor GPU usage using nvidia-smi"""

    def __init__(self):
        self.last_gpu_util = None

    def get_gpu_utilization(self) -> Optional[float]:
        """Get current GPU utilization percentage"""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Get first GPU utilization (main training GPU)
                util = float(result.stdout.strip().split('\n')[0])
                self.last_gpu_util = util
                return util
            return None
        except Exception as e:
            logger.error(f"Error getting GPU utilization: {e}")
            return None

    def get_gpu_memory_used(self) -> Optional[float]:
        """Get current GPU memory used in MB"""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                mem = float(result.stdout.strip().split('\n')[0])
                return mem
            return None
        except Exception as e:
            logger.error(f"Error getting GPU memory: {e}")
            return None


class ProcessManager:
    """Manage training processes"""

    @staticmethod
    def get_python_training_processes() -> List[Dict]:
        """Find all Python processes related to training"""
        processes = []
        try:
            # Find processes with 'flux_train_network.py' or 'accelerate' in command
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True,
                timeout=5
            )
            for line in result.stdout.split('\n'):
                if 'python' in line.lower() and (
                    'flux_train_network.py' in line or
                    'accelerate launch' in line or
                    'train_network.py' in line
                ):
                    parts = line.split()
                    if len(parts) >= 2:
                        processes.append({
                            'pid': int(parts[1]),
                            'cmdline': ' '.join(parts[10:])
                        })
        except Exception as e:
            logger.error(f"Error finding training processes: {e}")
        return processes

    @staticmethod
    def kill_process(pid: int, force: bool = False) -> bool:
        """Kill a process by PID"""
        try:
            if force:
                os.kill(pid, signal.SIGKILL)
                logger.info(f"Force killed process {pid}")
            else:
                os.kill(pid, signal.SIGTERM)
                logger.info(f"Terminated process {pid}")
            time.sleep(2)
            return True
        except ProcessLookupError:
            logger.warning(f"Process {pid} not found")
            return False
        except Exception as e:
            logger.error(f"Error killing process {pid}: {e}")
            return False

    @staticmethod
    def kill_all_training_processes(force: bool = True):
        """Kill all training-related Python processes"""
        processes = ProcessManager.get_python_training_processes()
        logger.info(f"Found {len(processes)} training processes to kill")

        for proc in processes:
            logger.info(f"Killing process {proc['pid']}: {proc['cmdline'][:100]}")
            ProcessManager.kill_process(proc['pid'], force=force)

        # Wait a bit and verify
        time.sleep(3)
        remaining = ProcessManager.get_python_training_processes()
        if remaining:
            logger.warning(f"Still {len(remaining)} processes remaining after cleanup")
            return False
        else:
            logger.info("All training processes killed successfully")
            return True


class CheckpointManager:
    """Manage training checkpoints"""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)

    def find_latest_checkpoint(self) -> Optional[Path]:
        """Find the latest checkpoint (state) directory"""
        if not self.output_dir.exists():
            logger.warning(f"Output directory does not exist: {self.output_dir}")
            return None

        # Look for state directories (epoch states, step states, or last state)
        state_dirs = []

        # Pattern: <name>-state or <name>-<epoch>-state or <name>-step-<step>-state
        for item in self.output_dir.iterdir():
            if item.is_dir() and 'state' in item.name.lower():
                state_dirs.append(item)

        if not state_dirs:
            logger.warning(f"No checkpoint states found in {self.output_dir}")
            return None

        # Sort by modification time, most recent first
        state_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        latest = state_dirs[0]

        logger.info(f"Found latest checkpoint: {latest}")
        return latest

    def find_latest_model_checkpoint(self) -> Optional[Path]:
        """Find the latest model checkpoint (.safetensors file)"""
        if not self.output_dir.exists():
            return None

        safetensors_files = list(self.output_dir.glob("*.safetensors"))
        if not safetensors_files:
            logger.warning(f"No .safetensors checkpoints found in {self.output_dir}")
            return None

        # Sort by modification time
        safetensors_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        latest = safetensors_files[0]

        logger.info(f"Found latest model checkpoint: {latest}")
        return latest


class TrainingMonitor:
    """Main training monitor with stuck detection and auto-recovery"""

    def __init__(
        self,
        output_dir: str,
        check_interval: int = 30,
        stuck_threshold: int = 300,
        gpu_threshold: float = 5.0,
        auto_resume: bool = False,
        train_script: Optional[str] = None
    ):
        self.output_dir = output_dir
        self.check_interval = check_interval
        self.stuck_threshold = stuck_threshold
        self.gpu_threshold = gpu_threshold
        self.auto_resume = auto_resume
        self.train_script = train_script

        self.gpu_monitor = GPUMonitor()
        self.checkpoint_mgr = CheckpointManager(output_dir)
        self.stuck_start_time = None
        self.last_good_time = time.time()

        logger.info(f"Training Monitor initialized:")
        logger.info(f"  Output directory: {output_dir}")
        logger.info(f"  Check interval: {check_interval}s")
        logger.info(f"  Stuck threshold: {stuck_threshold}s")
        logger.info(f"  GPU threshold: {gpu_threshold}%")
        logger.info(f"  Auto-resume: {auto_resume}")

    def is_training_stuck(self) -> bool:
        """Check if training appears to be stuck"""
        gpu_util = self.gpu_monitor.get_gpu_utilization()

        if gpu_util is None:
            logger.warning("Could not get GPU utilization")
            return False

        logger.debug(f"Current GPU utilization: {gpu_util}%")

        # Check if GPU usage is below threshold
        if gpu_util < self.gpu_threshold:
            if self.stuck_start_time is None:
                self.stuck_start_time = time.time()
                logger.warning(f"Low GPU usage detected ({gpu_util}%), monitoring...")
            else:
                stuck_duration = time.time() - self.stuck_start_time
                logger.warning(f"Low GPU usage for {stuck_duration:.0f}s (threshold: {self.stuck_threshold}s)")

                if stuck_duration >= self.stuck_threshold:
                    return True
        else:
            # GPU is active, reset stuck timer
            if self.stuck_start_time is not None:
                logger.info(f"GPU usage recovered ({gpu_util}%)")
            self.stuck_start_time = None
            self.last_good_time = time.time()

        return False

    def handle_stuck_training(self):
        """Handle stuck training by killing processes and optionally resuming"""
        logger.error("=" * 80)
        logger.error("TRAINING STUCK DETECTED!")
        logger.error("=" * 80)

        # Log current state
        gpu_util = self.gpu_monitor.get_gpu_utilization()
        gpu_mem = self.gpu_monitor.get_gpu_memory_used()
        logger.error(f"GPU utilization: {gpu_util}%")
        logger.error(f"GPU memory: {gpu_mem} MB")

        # Find latest checkpoint
        latest_checkpoint = self.checkpoint_mgr.find_latest_checkpoint()
        latest_model = self.checkpoint_mgr.find_latest_model_checkpoint()

        if latest_checkpoint:
            logger.info(f"Latest state checkpoint: {latest_checkpoint}")
        if latest_model:
            logger.info(f"Latest model checkpoint: {latest_model}")

        # Kill all training processes
        logger.info("Killing all training processes...")
        ProcessManager.kill_all_training_processes(force=True)

        # Wait a bit for cleanup
        time.sleep(5)

        if self.auto_resume:
            if latest_checkpoint:
                logger.info("Auto-resume is enabled. Attempting to resume training...")
                self.resume_training(latest_checkpoint)
            else:
                logger.error("Cannot auto-resume: No checkpoint found!")
        else:
            logger.info("Auto-resume is disabled. Please manually restart training.")
            logger.info("To resume from checkpoint, add this flag to your training command:")
            if latest_checkpoint:
                logger.info(f"  --resume {latest_checkpoint}")

    def resume_training(self, checkpoint_path: Path):
        """Resume training from checkpoint"""
        if not self.train_script:
            logger.error("Cannot resume: No training script provided")
            logger.info(f"Please manually run with: --resume {checkpoint_path}")
            return

        train_script_path = Path(self.train_script)
        if not train_script_path.exists():
            logger.error(f"Training script not found: {train_script_path}")
            return

        # Build resume command
        if train_script_path.suffix == '.sh':
            # Bash script - we need to modify it to add --resume flag
            logger.warning("Auto-resume with .sh scripts requires manual intervention")
            logger.info(f"Please edit {train_script_path} and add:")
            logger.info(f"  --resume {checkpoint_path}")
        elif train_script_path.suffix == '.bat':
            logger.warning("Auto-resume with .bat scripts requires manual intervention")
            logger.info(f"Please edit {train_script_path} and add:")
            logger.info(f"  --resume {checkpoint_path}")
        else:
            logger.error("Unknown training script format")

        logger.info("For now, auto-resume requires manual script editing")
        logger.info("Future versions will support automatic resume")

    def monitor(self):
        """Main monitoring loop"""
        logger.info("Starting training monitor...")
        logger.info("Press Ctrl+C to stop monitoring")

        try:
            while True:
                if self.is_training_stuck():
                    self.handle_stuck_training()

                    if not self.auto_resume:
                        logger.info("Monitoring stopped. Restart manually when ready.")
                        break
                    else:
                        # Reset stuck timer after handling
                        self.stuck_start_time = None
                        logger.info("Continuing to monitor after recovery...")

                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            logger.info("\nMonitoring stopped by user")
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}", exc_info=True)


def main():
    parser = argparse.ArgumentParser(
        description="Monitor FluxGym training and auto-recover from stuck states"
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        required=True,
        help='Output directory where checkpoints are saved (e.g., outputs/my-lora)'
    )
    parser.add_argument(
        '--check-interval',
        type=int,
        default=30,
        help='How often to check GPU usage in seconds (default: 30)'
    )
    parser.add_argument(
        '--stuck-threshold',
        type=int,
        default=300,
        help='How long GPU must be idle before considering stuck in seconds (default: 300)'
    )
    parser.add_argument(
        '--gpu-threshold',
        type=float,
        default=5.0,
        help='GPU usage percentage below which is considered idle (default: 5.0)'
    )
    parser.add_argument(
        '--auto-resume',
        action='store_true',
        help='Automatically attempt to resume training (experimental)'
    )
    parser.add_argument(
        '--train-script',
        type=str,
        help='Path to training script for auto-resume (e.g., outputs/my-lora/train.sh)'
    )

    args = parser.parse_args()

    monitor = TrainingMonitor(
        output_dir=args.output_dir,
        check_interval=args.check_interval,
        stuck_threshold=args.stuck_threshold,
        gpu_threshold=args.gpu_threshold,
        auto_resume=args.auto_resume,
        train_script=args.train_script
    )

    monitor.monitor()


if __name__ == '__main__':
    main()
