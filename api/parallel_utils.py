"""
Parallel processing utilities for photo validation
Provides batch processing, progress tracking, and performance monitoring
"""

import logging
import time
import threading
from typing import List, Dict, Any, Callable, Optional
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count, Manager
import os

# Try to import psutil for advanced resource monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil not available - advanced resource monitoring disabled")

class ProgressTracker:
    """Thread-safe progress tracker for parallel processing"""
    
    def __init__(self, total_items: int):
        self.total_items = total_items
        self.completed_items = 0
        self.failed_items = 0
        self.start_time = time.time()
        self.lock = threading.Lock()
        self.last_update = 0
        self.update_interval = 1.0  # Minimum seconds between progress updates
        
    def increment(self, success: bool = True):
        """Increment progress counter"""
        with self.lock:
            if success:
                self.completed_items += 1
            else:
                self.failed_items += 1
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current progress statistics"""
        with self.lock:
            total_processed = self.completed_items + self.failed_items
            elapsed_time = time.time() - self.start_time
            
            if total_processed > 0:
                rate = total_processed / elapsed_time
                eta = (self.total_items - total_processed) / rate if rate > 0 else 0
            else:
                rate = 0
                eta = 0
            
            return {
                'total': self.total_items,
                'completed': self.completed_items,
                'failed': self.failed_items,
                'total_processed': total_processed,
                'percentage': (total_processed / self.total_items) * 100 if self.total_items > 0 else 0,
                'elapsed_time': elapsed_time,
                'processing_rate': rate,
                'eta': eta
            }
    
    def should_update(self) -> bool:
        """Check if enough time has passed for a progress update"""
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval:
            self.last_update = current_time
            return True
        return False
    
    def log_progress(self, force: bool = False):
        """Log current progress if update interval has passed"""
        if force or self.should_update():
            progress = self.get_progress()
            logging.info(
                f"Progress: {progress['total_processed']}/{progress['total']} "
                f"({progress['percentage']:.1f}%) - "
                f"Rate: {progress['processing_rate']:.1f} images/sec - "
                f"ETA: {progress['eta']:.0f}s - "
                f"Success: {progress['completed']}, Failed: {progress['failed']}"
            )

class SystemResourceMonitor:
    """Monitor system resources during parallel processing"""
    
    def __init__(self):
        self.cpu_percent_history = []
        self.memory_percent_history = []
        self.monitoring = False
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Start resource monitoring in background thread"""
        if not PSUTIL_AVAILABLE:
            logging.info("Resource monitoring disabled - psutil not available")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_resources)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
    
    def _monitor_resources(self):
        """Background monitoring function"""
        if not PSUTIL_AVAILABLE:
            return
            
        while self.monitoring:
            try:
                cpu_percent = psutil.cpu_percent(interval=None)
                memory_percent = psutil.virtual_memory().percent
                
                self.cpu_percent_history.append(cpu_percent)
                self.memory_percent_history.append(memory_percent)
                
                # Keep only last 60 readings (1 minute at 1 second intervals)
                if len(self.cpu_percent_history) > 60:
                    self.cpu_percent_history.pop(0)
                    self.memory_percent_history.pop(0)
                
                time.sleep(1.0)
            except Exception as e:
                logging.warning(f"Resource monitoring error: {e}")
    
    def get_resource_stats(self) -> Dict[str, Any]:
        """Get current resource statistics"""
        if not self.cpu_percent_history:
            return {}
        
        return {
            'cpu_current': self.cpu_percent_history[-1] if self.cpu_percent_history else 0,
            'cpu_average': sum(self.cpu_percent_history) / len(self.cpu_percent_history),
            'cpu_max': max(self.cpu_percent_history),
            'memory_current': self.memory_percent_history[-1] if self.memory_percent_history else 0,
            'memory_average': sum(self.memory_percent_history) / len(self.memory_percent_history),
            'memory_max': max(self.memory_percent_history)
        }

class AdaptiveWorkerManager:
    """Dynamically adjust worker count based on system performance"""
    
    def __init__(self, min_workers: int = 2, max_workers: Optional[int] = None):
        self.min_workers = min_workers
        self.max_workers = max_workers or min(16, cpu_count())
        self.current_workers = self._get_initial_worker_count()
        self.performance_history = []
        
    def _get_initial_worker_count(self) -> int:
        """Calculate initial worker count based on system specs"""
        cpu_cores = cpu_count()
        
        # Conservative approach: use 70% of cores
        base_workers = max(self.min_workers, int(cpu_cores * 0.7))
        
        # Adjust for memory if psutil is available
        if PSUTIL_AVAILABLE:
            try:
                available_memory_gb = psutil.virtual_memory().available / (1024**3)
                # Reduce workers if low memory (less than 4GB available)
                if available_memory_gb < 4:
                    base_workers = max(self.min_workers, base_workers // 2)
            except Exception as e:
                logging.warning(f"Could not check memory usage: {e}")
        
        return min(base_workers, self.max_workers)
    
    def get_optimal_workers(self) -> int:
        """Get current optimal worker count"""
        return self.current_workers
    
    def update_performance(self, processing_rate: float, cpu_usage: float, memory_usage: float):
        """Update performance metrics and potentially adjust worker count"""
        self.performance_history.append({
            'rate': processing_rate,
            'cpu': cpu_usage,
            'memory': memory_usage,
            'workers': self.current_workers,
            'timestamp': time.time()
        })
        
        # Keep only recent history
        if len(self.performance_history) > 10:
            self.performance_history.pop(0)
        
        # Only adjust if we have enough history
        if len(self.performance_history) >= 3:
            self._consider_adjustment()
    
    def _consider_adjustment(self):
        """Consider adjusting worker count based on performance trends"""
        recent = self.performance_history[-3:]
        
        avg_cpu = sum(p['cpu'] for p in recent) / len(recent)
        avg_memory = sum(p['memory'] for p in recent) / len(recent)
        
        # Increase workers if CPU usage is low and memory is available
        if avg_cpu < 70 and avg_memory < 80 and self.current_workers < self.max_workers:
            self.current_workers = min(self.max_workers, self.current_workers + 1)
            logging.info(f"Increased workers to {self.current_workers} (CPU: {avg_cpu:.1f}%, Memory: {avg_memory:.1f}%)")
        
        # Decrease workers if system is under stress
        elif (avg_cpu > 90 or avg_memory > 90) and self.current_workers > self.min_workers:
            self.current_workers = max(self.min_workers, self.current_workers - 1)
            logging.info(f"Decreased workers to {self.current_workers} (CPU: {avg_cpu:.1f}%, Memory: {avg_memory:.1f}%)")

class BatchProcessor:
    """High-performance batch processor for parallel image validation"""
    
    def __init__(self, batch_size: int = 50, max_workers: Optional[int] = None):
        self.batch_size = batch_size
        self.resource_monitor = SystemResourceMonitor()
        self.worker_manager = AdaptiveWorkerManager(max_workers=max_workers)
        
    def process_batches(self, 
                       items: List[Any], 
                       process_function: Callable,
                       *args, 
                       **kwargs) -> List[Any]:
        """
        Process items in batches with progress tracking and resource monitoring
        """
        total_items = len(items)
        if total_items == 0:
            return []
        
        # Initialize tracking
        progress_tracker = ProgressTracker(total_items)
        self.resource_monitor.start_monitoring()
        
        results = []
        
        try:
            logging.info(f"Starting batch processing: {total_items} items, batch size: {self.batch_size}")
            
            # Create batches
            batches = [items[i:i + self.batch_size] for i in range(0, total_items, self.batch_size)]
            
            optimal_workers = self.worker_manager.get_optimal_workers()
            logging.info(f"Using {optimal_workers} workers for parallel processing")
            
            with ProcessPoolExecutor(max_workers=optimal_workers) as executor:
                # Submit all batches
                batch_futures = []
                for batch_idx, batch in enumerate(batches):
                    future = executor.submit(self._process_batch, batch, process_function, *args, **kwargs)
                    batch_futures.append((future, batch_idx, len(batch)))
                
                # Process completed batches
                for future, batch_idx, batch_size in batch_futures:
                    try:
                        batch_results = future.result()
                        results.extend(batch_results)
                        
                        # Update progress
                        for result in batch_results:
                            progress_tracker.increment(success=hasattr(result, 'is_valid'))
                        
                        progress_tracker.log_progress()
                        
                        # Update performance metrics
                        if progress_tracker.should_update():
                            resource_stats = self.resource_monitor.get_resource_stats()
                            if resource_stats:
                                progress_stats = progress_tracker.get_progress()
                                self.worker_manager.update_performance(
                                    progress_stats['processing_rate'],
                                    resource_stats['cpu_current'],
                                    resource_stats['memory_current']
                                )
                        
                    except Exception as e:
                        logging.error(f"Error processing batch {batch_idx}: {e}")
                        # Mark batch items as failed
                        for _ in range(batch_size):
                            progress_tracker.increment(success=False)
            
            # Final progress update
            progress_tracker.log_progress(force=True)
            
        finally:
            self.resource_monitor.stop_monitoring()
            
            # Log final resource statistics
            resource_stats = self.resource_monitor.get_resource_stats()
            if resource_stats:
                logging.info(f"Resource usage - CPU: avg {resource_stats['cpu_average']:.1f}%, "
                           f"max {resource_stats['cpu_max']:.1f}% | "
                           f"Memory: avg {resource_stats['memory_average']:.1f}%, "
                           f"max {resource_stats['memory_max']:.1f}%")
        
        return results
    
    def _process_batch(self, batch: List[Any], process_function: Callable, *args, **kwargs) -> List[Any]:
        """Process a single batch of items"""
        batch_results = []
        for item in batch:
            try:
                result = process_function(item, *args, **kwargs)
                batch_results.append(result)
            except Exception as e:
                logging.error(f"Error processing item {item}: {e}")
                # Create a failed result
                from .photo_validator_parallel import ValidationResult
                batch_results.append(ValidationResult(
                    str(item), False, [f"Processing error: {str(e)}"], 0
                ))
        return batch_results

def get_system_info() -> Dict[str, Any]:
    """Get comprehensive system information for optimization"""
    return {
        'cpu_count': cpu_count(),
        'cpu_freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {},
        'memory_total_gb': psutil.virtual_memory().total / (1024**3),
        'memory_available_gb': psutil.virtual_memory().available / (1024**3),
        'disk_usage': psutil.disk_usage('/')._asdict() if os.name != 'nt' else psutil.disk_usage('C:')._asdict(),
        'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None
    }

def log_system_info():
    """Log system information for debugging and optimization"""
    info = get_system_info()
    logging.info("=" * 50)
    logging.info("SYSTEM INFORMATION")
    logging.info("=" * 50)
    logging.info(f"CPU cores: {info['cpu_count']}")
    logging.info(f"Memory: {info['memory_available_gb']:.1f}GB available / {info['memory_total_gb']:.1f}GB total")
    logging.info(f"Disk usage: {info['disk_usage']['percent']:.1f}% used")
    if info['load_average']:
        logging.info(f"Load average: {info['load_average']}")
    logging.info("=" * 50)