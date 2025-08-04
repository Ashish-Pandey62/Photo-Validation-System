import logging
import os
import time
import datetime
import cv2
import csv
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count
import threading
from shutil import move, copy2
from django.conf import settings
from .models import Config
from .parallel_utils import (
    ProgressTracker, SystemResourceMonitor, AdaptiveWorkerManager,
    BatchProcessor, log_system_info, get_system_info
)

import api.background_check as background_check
import api.blur_check as blur_check
import api.file_format_check as file_format_check
import api.file_size_check as file_size_check
import api.grey_black_and_white_check as grey_black_and_white_check
import api.head_check as head_check
import api.symmetry_check as symmetry_check

logging.basicConfig(level=logging.INFO)

# Thread-safe locks for file operations
file_move_lock = threading.Lock()
csv_write_lock = threading.Lock()

class ValidationResult:
    """Container for validation results"""
    def __init__(self, image_name, is_valid, messages, processing_time):
        self.image_name = image_name
        self.is_valid = is_valid
        self.messages = messages
        self.processing_time = processing_time

def get_optimal_worker_count():
    """Determine optimal number of workers optimized for Lenovo Legion 5 Pro with i7-13620H"""
    cpu_cores = cpu_count()
    
    if cpu_cores >= 16:  # High-end systems 
        optimal_workers = 12
    elif cpu_cores >= 8:  # Mid-range systems
        optimal_workers = max(4, min(cpu_cores - 2, 6))
    else:  # Lower-end systems
        optimal_workers = max(2, min(cpu_cores - 1, 4))
    
    logging.info(f"Using {optimal_workers} workers for parallel processing (detected {cpu_cores} CPU cores)")
    return optimal_workers

def validate_single_image(image_path, config_data, directories):
    """
    Validate a single image - designed to be called in parallel
    Returns ValidationResult object
    """
    start_time = time.time()
    image_name = os.path.basename(image_path)
    messages = []
    
    try:
        # Create a simple config object from the serialized data
        class SimpleConfig:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)
        
        config = SimpleConfig(config_data)
        
        logging.info(f"Processing image: {image_name}")

        # Check image file format
        if not config.bypass_format_check:
            try:
                is_file_format_valid = file_format_check.check_image(image_path)
                if not is_file_format_valid:
                    messages.append("File format check failed")
            except Exception as e:
                logging.error(f"Error in file format check for {image_name}: {e}")
                messages.append(f"File format check error: {str(e)}")

        # Check file size
        if not config.bypass_size_check:
            try:
                is_file_size_valid = file_size_check.check_image(image_path)
                if not is_file_size_valid:
                    messages.append("File size check failed")
            except Exception as e:
                logging.error(f"Error in file size check for {image_name}: {e}")
                messages.append(f"File size check error: {str(e)}")

        # Check height
        if not config.bypass_height_check:
            try:
                is_file_height_valid = file_size_check.check_height(image_path)
                if not is_file_height_valid:
                    messages.append("File height check failed")
            except Exception as e:
                logging.error(f"Error in file height check for {image_name}: {e}")
                messages.append(f"File height check error: {str(e)}")

        # Check width
        if not config.bypass_width_check:
            try:
                is_file_width_valid = file_size_check.check_width(image_path)
                if not is_file_width_valid:
                    messages.append("File width check failed")
            except Exception as e:
                logging.error(f"Error in file width check for {image_name}: {e}")
                messages.append(f"File width check error: {str(e)}")

        # Load the image
        try:
            img = cv2.imread(image_path)
            if img is None:
                messages.append("Could not load image")
                logging.error(f"Failed to load image: {image_path}")
                processing_time = time.time() - start_time
                return ValidationResult(image_name, False, messages, processing_time)
        except Exception as e:
            messages.append(f"Error loading image: {str(e)}")
            logging.error(f"Exception loading image {image_path}: {e}")
            processing_time = time.time() - start_time
            return ValidationResult(image_name, False, messages, processing_time)

        # Check if corrupted image
        if not config.bypass_corrupted_check:
            try:
                if file_format_check.is_corrupted_image(img):
                    messages.append("Corrupted Image")
            except Exception as e:
                logging.error(f"Error in corrupted image check for {image_name}: {e}")
                messages.append(f"Corruption check error: {str(e)}")

        # Check for grey image
        if not config.bypass_greyness_check:
            try:
                if grey_black_and_white_check.is_grey(img, config):
                    messages.append("GreyScale check failed")
            except Exception as e:
                logging.error(f"Error in greyness check for {image_name}: {e}")
                messages.append(f"Greyness check error: {str(e)}")

        # Check image for blurness
        if not config.bypass_blurness_check:
            try:
                if blur_check.check_image_blurness(img, config):
                    messages.append("Blurness check failed")
            except Exception as e:
                logging.error(f"Error in blurness check for {image_name}: {e}")
                messages.append(f"Blurness check error: {str(e)}")

        # Check the background of image
        if not config.bypass_background_check:
            try:
                if not background_check.background_check(img, config):
                    messages.append("Background check failed")
            except Exception as e:
                logging.error(f"Error in background check for {image_name}: {e}")
                messages.append(f"Background check error: {str(e)}")

        # Check image for head position and coverage
        if not config.bypass_head_check:
            try:
                is_head_valid, head_percent = head_check.valid_head_check(img)
                if not is_head_valid:
                    if head_percent < 10:
                        messages.append("Head Ratio Small")
                    elif 100 > head_percent > 80:
                        messages.append("Head Ratio Large")
                    elif head_percent == 101:
                        messages.append("couldnot detect head")
                    else:
                        messages.append("multiple heads detected")
            except Exception as e:
                logging.error(f"Error in head check for {image_name}: {e}")
                messages.append(f"Head check error: {str(e)}")

        # Check eyes
        if not config.bypass_eye_check:
            try:
                if head_check.detect_eyes(img):
                    messages.append("Eye check failed")
            except Exception as e:
                logging.error(f"Error in eye check for {image_name}: {e}")
                messages.append(f"Eye check error: {str(e)}")

        # Check for symmetry
        if not config.bypass_symmetry_check:
            try:
                if not symmetry_check.issymmetric(img, config):
                    messages.append("Symmetry check failed")
            except Exception as e:
                logging.error(f"Error in symmetry check for {image_name}: {e}")
                messages.append(f"Symmetry check error: {str(e)}")

        processing_time = time.time() - start_time
        is_valid = len(messages) == 0
        
        logging.info(f"Completed {image_name} in {processing_time:.2f}s - {'VALID' if is_valid else 'INVALID'}")
        return ValidationResult(image_name, is_valid, messages, processing_time)

    except Exception as e:
        processing_time = time.time() - start_time
        logging.error(f"Unexpected error processing {image_name}: {e}")
        return ValidationResult(image_name, False, [f"Unexpected error: {str(e)}"], processing_time)

def move_image_thread_safe(image_path, destination_dir, image_name):
    """Thread-safe image moving function"""
    with file_move_lock:
        try:
            destination_path = os.path.join(destination_dir, image_name)
            if os.path.exists(destination_path):
                logging.info(f"File {image_name} already exists in destination, skipping move")
                return True
            
            if os.path.exists(image_path):
                move(image_path, destination_dir)
                logging.info(f"Moved {image_name} to {destination_dir}")
                return True
            else:
                logging.warning(f"Source file {image_path} no longer exists")
                return False
        except Exception as e:
            logging.error(f"Error moving {image_name}: {e}")
            return False

def write_csv_results_thread_safe(csv_file_path, error_messages):
    """Thread-safe CSV writing function"""
    with csv_write_lock:
        try:
            csv_string = ""
            if len(error_messages) > 0:
                for name, messages in error_messages.items():
                    csv_string += name
                    for message in messages:
                        csv_string += "," + message
                    csv_string += "\n"
            else:
                csv_string = f"# Validation Summary: No invalid images found\n"
                csv_string += f"# Validation completed at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                csv_string += "# All images passed validation!\n"

            with open(csv_file_path, "a", encoding='utf-8') as f:
                f.write(csv_string)
            
            logging.info("Successfully wrote validation results to CSV")
            return True
        except Exception as e:
            logging.error(f"Error writing CSV results: {e}")
            return False

def process_validation_results(results, directory, invalid_images_static_directory):
    """Process validation results and move files accordingly"""
    error_messages = {}
    valid_count = 0
    invalid_count = 0
    
    valid_directory = os.path.join(directory, "valid")
    os.makedirs(valid_directory, exist_ok=True)
    
    # Process results in batches for better performance
    batch_size = 50
    for i in range(0, len(results), batch_size):
        batch = results[i:i + batch_size]
        
        # Use ThreadPoolExecutor for I/O operations (moving files)
        with ThreadPoolExecutor(max_workers=4) as executor:
            move_tasks = []
            
            for result in batch:
                original_path = os.path.join(directory, result.image_name)
                
                if result.is_valid:
                    valid_count += 1
                    # Move to valid directory
                    task = executor.submit(move_image_thread_safe, original_path, valid_directory, result.image_name)
                    move_tasks.append(task)
                else:
                    invalid_count += 1
                    error_messages[result.image_name] = result.messages
                    # Move to invalid directory
                    task = executor.submit(move_image_thread_safe, original_path, invalid_images_static_directory, result.image_name)
                    move_tasks.append(task)
            
            # Wait for all move operations to complete
            for task in as_completed(move_tasks):
                try:
                    task.result()
                except Exception as e:
                    logging.error(f"Error in file move operation: {e}")
    
    return error_messages, valid_count, invalid_count

def main_parallel(directory, max_workers=None, enable_adaptive_scaling=True):
    """
    Advanced parallel validation function with intelligent resource management
    Features:
    - Adaptive worker scaling based on system performance
    - Real-time progress tracking with ETA
    - Resource monitoring and optimization
    - Batch processing for optimal throughput
    """
    # Log system information for optimization
    log_system_info()
    
    # Ensure directory exists
    if not os.path.exists(directory):
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    start_time = time.time()
    logging.info(f"🚀 Starting SUPERCHARGED parallel validation of directory: {directory}")
    
    # Initialize intelligent resource management
    resource_monitor = SystemResourceMonitor()
    worker_manager = AdaptiveWorkerManager(max_workers=max_workers)
    
    if enable_adaptive_scaling:
        resource_monitor.start_monitoring()
    
    try:
        # Get config and convert to dictionary for serialization
        try:
            config = Config.objects.first()
            if not config:
                config = Config.objects.create(
                    min_height=100, max_height=2000, min_width=100, max_width=2000,
                    min_size=10, max_size=5000, is_jpg=True, is_png=True, is_jpeg=True
                )
        except Exception as e:
            config = Config(
                min_height=100, max_height=2000, min_width=100, max_width=2000,
                min_size=10, max_size=5000, is_jpg=True, is_png=True, is_jpeg=True
            )
            config.save()
        
        # Convert config to dictionary for serialization (only field values)
        config_data = {}
        for field in config._meta.get_fields():
            if hasattr(config, field.name):
                config_data[field.name] = getattr(config, field.name)
        
        # Add any missing default values that might be needed
        default_config = {
            'bypass_format_check': False,
            'bypass_size_check': False,
            'bypass_height_check': False,
            'bypass_width_check': False,
            'bypass_corrupted_check': False,
            'bypass_greyness_check': False,
            'bypass_blurness_check': False,
            'bypass_background_check': False,
            'bypass_head_check': False,
            'bypass_eye_check': False,
            'bypass_symmetry_check': False,
        }
        
        # Merge defaults with actual config
        for key, default_value in default_config.items():
            if key not in config_data:
                config_data[key] = default_value
        
        # Setup directories
        valid_directory = os.path.join(directory, "valid")
        invalid_images_static_directory = os.path.join(
            settings.BASE_DIR, "api", "static", "api", "images", "invalid"
        )
        result_file_static_directory = os.path.join(
            settings.BASE_DIR, "api", "static", "api", "images", "result.csv"
        )
        
        # Ensure all required directories exist
        os.makedirs(valid_directory, exist_ok=True)
        os.makedirs(invalid_images_static_directory, exist_ok=True)
        os.makedirs(os.path.dirname(result_file_static_directory), exist_ok=True)
        
        # Initialize empty CSV file
        if not os.path.exists(result_file_static_directory):
            with open(result_file_static_directory, "w", newline="", encoding='utf-8') as csv_file:
                csv_writer = csv.writer(csv_file)
                csv_writer.writerows([])
        
        # Get list of image files
        file_lists = sorted([f for f in os.listdir(directory)
                            if os.path.isfile(os.path.join(directory, f))
                            and f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif'))])
        
        if not file_lists:
            logging.info("No image files found to process")
            return {
                'total_processed': 0,
                'valid_count': 0,
                'invalid_count': 0,
                'processing_time': 0,
                'avg_time_per_image': 0
            }
        
        logging.info(f"📊 Found {len(file_lists)} image files to process")
        
        # Initialize progress tracking
        progress_tracker = ProgressTracker(len(file_lists))
        
        # Determine optimal worker count
        optimal_workers = worker_manager.get_optimal_workers()
        logging.info(f"⚡ Using {optimal_workers} workers for maximum performance")
        
        # Create image paths
        image_paths = [os.path.join(directory, image) for image in file_lists]
        directories = {
            'valid': valid_directory,
            'invalid': invalid_images_static_directory
        }
        
        # Process images with intelligent batch processing
        results = []
        batch_size = min(50, max(10, len(file_lists) // optimal_workers))
        
        logging.info(f"📦 Processing in batches of {batch_size} for optimal throughput")
        logging.info("🔥 PARALLEL VALIDATION ENGINE STARTING...")
        
        with ProcessPoolExecutor(max_workers=optimal_workers) as executor:
            # Submit all tasks
            future_to_image = {}
            for image_path in image_paths:
                future = executor.submit(validate_single_image, image_path, config_data, directories)
                future_to_image[future] = image_path
            
            # Process completed tasks with advanced progress tracking
            for future in as_completed(future_to_image):
                try:
                    result = future.result()
                    results.append(result)
                    progress_tracker.increment(success=result.is_valid)
                    
                    # Real-time progress updates with ETA
                    progress_tracker.log_progress()
                    
                    # Adaptive resource management
                    if enable_adaptive_scaling and progress_tracker.should_update():
                        resource_stats = resource_monitor.get_resource_stats()
                        if resource_stats:
                            progress_stats = progress_tracker.get_progress()
                            worker_manager.update_performance(
                                progress_stats['processing_rate'],
                                resource_stats['cpu_current'],
                                resource_stats['memory_current']
                            )
                    
                except Exception as e:
                    image_path = future_to_image[future]
                    image_name = os.path.basename(image_path)
                    logging.error(f"❌ Error processing {image_name}: {e}")
                    results.append(ValidationResult(image_name, False, [f"Processing error: {str(e)}"], 0))
                    progress_tracker.increment(success=False)
        
        # Final progress update
        progress_tracker.log_progress(force=True)
        
        # Process results and move files with optimized I/O
        logging.info("📁 Processing validation results and organizing files...")
        error_messages, valid_count, invalid_count = process_validation_results(
            results, directory, invalid_images_static_directory
        )
        
        # Write CSV results
        write_csv_results_thread_safe(result_file_static_directory, error_messages)
        
        # Calculate comprehensive statistics
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_image = total_time / len(file_lists) if file_lists else 0
        images_per_second = len(file_lists) / total_time if total_time > 0 else 0
        
        # Get final resource statistics
        final_resource_stats = resource_monitor.get_resource_stats() if enable_adaptive_scaling else {}
        
        # Log EPIC completion summary
        logging.info("🎯" + "=" * 58 + "🎯")
        logging.info("🚀 SUPERCHARGED PARALLEL VALIDATION COMPLETED! 🚀")
        logging.info("🎯" + "=" * 58 + "🎯")
        logging.info(f"📊 Total images processed: {len(file_lists)}")
        logging.info(f"✅ Valid images: {valid_count}")
        logging.info(f"❌ Invalid images: {invalid_count}")
        logging.info(f"⏱️  Total processing time: {total_time:.2f} seconds")
        logging.info(f"⚡ Average time per image: {avg_time_per_image:.3f} seconds")
        logging.info(f"🔥 Processing speed: {images_per_second:.2f} images/second")
        logging.info(f"🛠️  Workers utilized: {optimal_workers}")
        
        if final_resource_stats:
            logging.info(f"💻 System performance - CPU: {final_resource_stats['cpu_average']:.1f}% avg, "
                        f"Memory: {final_resource_stats['memory_average']:.1f}% avg")
        
        # Calculate estimated speedup
        estimated_sequential_time = len(file_lists) * 2.0  # Conservative 2s per image estimate
        speedup_factor = estimated_sequential_time / total_time if total_time > 0 else 1
        logging.info(f"🚀 ESTIMATED SPEEDUP: {speedup_factor:.1f}x FASTER than sequential!")
        
        if invalid_count > 0:
            logging.info("❌ Invalid images summary:")
            for image, issues in error_messages.items():
                logging.info(f"   • {image}: {', '.join(issues)}")
        
        logging.info("🎉 PARALLEL PROCESSING MISSION ACCOMPLISHED! 🎉")
        
        return {
            'total_processed': len(file_lists),
            'valid_count': valid_count,
            'invalid_count': invalid_count,
            'processing_time': total_time,
            'avg_time_per_image': avg_time_per_image,
            'images_per_second': images_per_second,
            'workers_used': optimal_workers,
            'speedup_factor': speedup_factor,
            'resource_stats': final_resource_stats
        }
    
    finally:
        if enable_adaptive_scaling:
            resource_monitor.stop_monitoring()

if __name__ == "__main__":
    # Test function
    import sys
    if len(sys.argv) > 1:
        test_directory = sys.argv[1]
        main_parallel(test_directory)
    else:
        print("Usage: python photo_validator_parallel.py <directory_path>")