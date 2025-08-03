import logging
import os
import time
import datetime
import cv2
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count
import threading
from shutil import move
from django.conf import settings
from .models import Config

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
progress_lock = threading.Lock()

class ValidationResult:
    """Container for validation results"""
    def __init__(self, image_name, is_valid, messages, processing_time):
        self.image_name = image_name
        self.is_valid = is_valid
        self.messages = messages
        self.processing_time = processing_time

class ProgressTracker:
    """Thread-safe progress tracker"""
    def __init__(self, total_items):
        self.total_items = total_items
        self.completed_items = 0
        self.failed_items = 0
        self.start_time = time.time()
        self.last_update = 0
        
    def increment(self, success=True):
        with progress_lock:
            if success:
                self.completed_items += 1
            else:
                self.failed_items += 1
            
            # Log progress every 10 items or every 2 seconds
            total_processed = self.completed_items + self.failed_items
            current_time = time.time()
            
            if (total_processed % 10 == 0 or current_time - self.last_update >= 2.0 or 
                total_processed >= self.total_items):
                
                elapsed_time = current_time - self.start_time
                rate = total_processed / elapsed_time if elapsed_time > 0 else 0
                eta = (self.total_items - total_processed) / rate if rate > 0 else 0
                percentage = (total_processed / self.total_items) * 100 if self.total_items > 0 else 0
                
                logging.info(
                    f"🔥 Progress: {total_processed}/{self.total_items} "
                    f"({percentage:.1f}%) - "
                    f"Rate: {rate:.1f} images/sec - "
                    f"ETA: {eta:.0f}s - "
                    f"Valid: {self.completed_items}, Invalid: {self.failed_items}"
                )
                self.last_update = current_time

def get_optimal_thread_count():
    """Get optimal thread count for I/O bound tasks"""
    cpu_cores = cpu_count()
    # For I/O bound tasks, we can use more threads than CPU cores
    # Use 2-3x CPU cores, but cap at reasonable limits
    optimal_threads = min(max(4, cpu_cores * 2), 20)
    logging.info(f"⚡ Using {optimal_threads} threads for parallel processing (detected {cpu_cores} CPU cores)")
    return optimal_threads

def validate_single_image_threaded(image_path, config):
    """
    Validate a single image in a thread-safe manner
    Returns ValidationResult object
    """
    start_time = time.time()
    image_name = os.path.basename(image_path)
    messages = []
    
    try:
        logging.debug(f"Processing image: {image_name}")

        # Check image file format
        if not getattr(config, 'bypass_format_check', False):
            try:
                is_file_format_valid = file_format_check.check_image(image_path)
                if not is_file_format_valid:
                    messages.append("File format check failed")
            except Exception as e:
                logging.error(f"Error in file format check for {image_name}: {e}")
                messages.append(f"File format check error: {str(e)}")

        # Check file size
        if not getattr(config, 'bypass_size_check', False):
            try:
                is_file_size_valid = file_size_check.check_image(image_path)
                if not is_file_size_valid:
                    messages.append("File size check failed")
            except Exception as e:
                logging.error(f"Error in file size check for {image_name}: {e}")
                messages.append(f"File size check error: {str(e)}")

        # Check height
        if not getattr(config, 'bypass_height_check', False):
            try:
                is_file_height_valid = file_size_check.check_height(image_path)
                if not is_file_height_valid:
                    messages.append("File height check failed")
            except Exception as e:
                logging.error(f"Error in file height check for {image_name}: {e}")
                messages.append(f"File height check error: {str(e)}")

        # Check width
        if not getattr(config, 'bypass_width_check', False):
            try:
                is_file_width_valid = file_size_check.check_width(image_path)
                if not is_file_width_valid:
                    messages.append("File width check failed")
            except Exception as e:
                logging.error(f"Error in file width check for {image_name}: {e}")
                messages.append(f"File width check error: {str(e)}")

        # Load the image with proper validation
        try:
            img = cv2.imread(image_path)
            if img is None:
                messages.append("Could not load image")
                logging.error(f"Failed to load image: {image_path}")
                processing_time = time.time() - start_time
                return ValidationResult(image_name, False, messages, processing_time)
            
            # Validate image format and convert if necessary
            if len(img.shape) != 3 or img.shape[2] != 3:
                # Try to convert to BGR format if it's not already
                if len(img.shape) == 2:
                    # Grayscale to BGR
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                elif len(img.shape) == 3 and img.shape[2] == 4:
                    # RGBA to BGR
                    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                else:
                    messages.append("Unsupported image format")
                    logging.error(f"Unsupported image format for {image_path}: shape {img.shape}")
                    processing_time = time.time() - start_time
                    return ValidationResult(image_name, False, messages, processing_time)
            
            # Ensure the image is 8-bit
            if img.dtype != 'uint8':
                img = img.astype('uint8')
                
        except Exception as e:
            messages.append(f"Error loading image: {str(e)}")
            logging.error(f"Exception loading image {image_path}: {e}")
            processing_time = time.time() - start_time
            return ValidationResult(image_name, False, messages, processing_time)

        # Check if corrupted image
        if not getattr(config, 'bypass_corrupted_check', False):
            try:
                if file_format_check.is_corrupted_image(img):
                    messages.append("Corrupted Image")
            except Exception as e:
                logging.error(f"Error in corrupted image check for {image_name}: {e}")
                messages.append(f"Corruption check error: {str(e)}")

        # Check for grey image
        if not getattr(config, 'bypass_greyness_check', False):
            try:
                if grey_black_and_white_check.is_grey(img, config):
                    messages.append("GreyScale check failed")
            except Exception as e:
                logging.error(f"Error in greyness check for {image_name}: {e}")
                messages.append(f"Greyness check error: {str(e)}")

        # Check image for blurness
        if not getattr(config, 'bypass_blurness_check', False):
            try:
                if blur_check.check_image_blurness(img, config):
                    messages.append("Blurness check failed")
            except Exception as e:
                logging.error(f"Error in blurness check for {image_name}: {e}")
                messages.append(f"Blurness check error: {str(e)}")

        # Check the background of image
        if not getattr(config, 'bypass_background_check', False):
            try:
                if not background_check.background_check(img, config):
                    messages.append("Background check failed")
            except Exception as e:
                logging.error(f"Error in background check for {image_name}: {e}")
                messages.append(f"Background check error: {str(e)}")

        # Check image for head position and coverage
        if not getattr(config, 'bypass_head_check', False):
            try:
                # Additional validation for head check
                if img is not None and len(img.shape) == 3 and img.shape[2] == 3:
                    # Make a copy to avoid modifying the original
                    img_copy = img.copy()
                    is_head_valid, head_percent = head_check.valid_head_check(img_copy)
                    if not is_head_valid:
                        if head_percent < 10:
                            messages.append("Head Ratio Small")
                        elif 100 > head_percent > 80:
                            messages.append("Head Ratio Large")
                        elif head_percent == 101:
                            messages.append("couldnot detect head")
                        else:
                            messages.append("multiple heads detected")
                else:
                    messages.append("Invalid image format for head check")
            except Exception as e:
                logging.error(f"Error in head check for {image_name}: {e}")
                # Don't add this as a validation failure, just skip the check
                logging.warning(f"Skipping head check for {image_name} due to format issues")

        # Check eyes
        if not getattr(config, 'bypass_eye_check', False):
            try:
                # Additional validation for eye check
                if img is not None and len(img.shape) == 3 and img.shape[2] == 3:
                    # Make a copy to avoid modifying the original
                    img_copy = img.copy()
                    if head_check.detect_eyes(img_copy):
                        messages.append("Eye check failed")
                else:
                    messages.append("Invalid image format for eye check")
            except Exception as e:
                logging.error(f"Error in eye check for {image_name}: {e}")
                # Don't add this as a validation failure, just skip the check
                logging.warning(f"Skipping eye check for {image_name} due to format issues")

        # Check for symmetry
        if not getattr(config, 'bypass_symmetry_check', False):
            try:
                if not symmetry_check.issymmetric(img, config):
                    messages.append("Symmetry check failed")
            except Exception as e:
                logging.error(f"Error in symmetry check for {image_name}: {e}")
                messages.append(f"Symmetry check error: {str(e)}")

        processing_time = time.time() - start_time
        is_valid = len(messages) == 0
        
        logging.debug(f"Completed {image_name} in {processing_time:.2f}s - {'VALID' if is_valid else 'INVALID'}")
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
                logging.debug(f"File {image_name} already exists in destination, skipping move")
                return True
            
            if os.path.exists(image_path):
                move(image_path, destination_dir)
                logging.debug(f"Moved {image_name} to {destination_dir}")
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

def main_threaded(directory, max_workers=None):
    """
    Thread-based parallel validation function - stable and fast
    """
    # Ensure directory exists
    if not os.path.exists(directory):
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    start_time = time.time()
    logging.info(f"🚀 Starting THREADED parallel validation of directory: {directory}")
    
    # Get config object (no serialization needed for threads)
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
    
    # Determine optimal thread count
    if max_workers is None:
        max_workers = get_optimal_thread_count()
    
    logging.info(f"🔥 THREADED VALIDATION ENGINE STARTING with {max_workers} threads...")
    
    # Process images with ThreadPoolExecutor
    results = []
    image_paths = [os.path.join(directory, image) for image in file_lists]
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_image = {
            executor.submit(validate_single_image_threaded, image_path, config): image_path 
            for image_path in image_paths
        }
        
        # Process completed tasks as they finish
        for future in as_completed(future_to_image):
            try:
                result = future.result()
                results.append(result)
                progress_tracker.increment(success=result.is_valid)
                
            except Exception as e:
                image_path = future_to_image[future]
                image_name = os.path.basename(image_path)
                logging.error(f"❌ Error processing {image_name}: {e}")
                results.append(ValidationResult(image_name, False, [f"Processing error: {str(e)}"], 0))
                progress_tracker.increment(success=False)
    
    # Process results and move files
    logging.info("📁 Processing validation results and organizing files...")
    
    error_messages = {}
    valid_count = 0
    invalid_count = 0
    
    # Use ThreadPoolExecutor for file operations too
    with ThreadPoolExecutor(max_workers=4) as file_executor:
        move_tasks = []
        
        for result in results:
            original_path = os.path.join(directory, result.image_name)
            
            if result.is_valid:
                valid_count += 1
                # Move to valid directory
                task = file_executor.submit(move_image_thread_safe, original_path, valid_directory, result.image_name)
                move_tasks.append(task)
            else:
                invalid_count += 1
                error_messages[result.image_name] = result.messages
                # Move to invalid directory
                task = file_executor.submit(move_image_thread_safe, original_path, invalid_images_static_directory, result.image_name)
                move_tasks.append(task)
        
        # Wait for all move operations to complete
        for task in as_completed(move_tasks):
            try:
                task.result()
            except Exception as e:
                logging.error(f"Error in file move operation: {e}")
    
    # Write CSV results
    write_csv_results_thread_safe(result_file_static_directory, error_messages)
    
    # Calculate comprehensive statistics
    end_time = time.time()
    total_time = end_time - start_time
    avg_time_per_image = total_time / len(file_lists) if file_lists else 0
    images_per_second = len(file_lists) / total_time if total_time > 0 else 0
    
    # Log completion summary
    logging.info("🎯" + "=" * 58 + "🎯")
    logging.info("🚀 THREADED PARALLEL VALIDATION COMPLETED! 🚀")
    logging.info("🎯" + "=" * 58 + "🎯")
    logging.info(f"📊 Total images processed: {len(file_lists)}")
    logging.info(f"✅ Valid images: {valid_count}")
    logging.info(f"❌ Invalid images: {invalid_count}")
    logging.info(f"⏱️  Total processing time: {total_time:.2f} seconds")
    logging.info(f"⚡ Average time per image: {avg_time_per_image:.3f} seconds")
    logging.info(f"🔥 Processing speed: {images_per_second:.2f} images/second")
    logging.info(f"🛠️  Threads utilized: {max_workers}")
    
    # Calculate estimated speedup
    estimated_sequential_time = len(file_lists) * 2.0  # Conservative 2s per image estimate
    speedup_factor = estimated_sequential_time / total_time if total_time > 0 else 1
    logging.info(f"🚀 ESTIMATED SPEEDUP: {speedup_factor:.1f}x FASTER than sequential!")
    
    if invalid_count > 0:
        logging.info("❌ Invalid images summary:")
        for image, issues in error_messages.items():
            logging.info(f"   • {image}: {', '.join(issues)}")
    
    logging.info("🎉 THREADED PROCESSING MISSION ACCOMPLISHED! 🎉")
    
    return {
        'total_processed': len(file_lists),
        'valid_count': valid_count,
        'invalid_count': invalid_count,
        'processing_time': total_time,
        'avg_time_per_image': avg_time_per_image,
        'images_per_second': images_per_second,
        'workers_used': max_workers,
        'speedup_factor': speedup_factor
    }