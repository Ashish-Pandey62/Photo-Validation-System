import logging
import os.path
from django.http import HttpResponse
from .photo_validator_threaded import main_threaded

logging.basicConfig(level=logging.INFO)


def moveToFolder(label, imagePath):
    """Legacy function - kept for compatibility but not used in parallel processing"""
    folderName = os.path.join(os.getcwd(), label)
    os.makedirs(folderName, exist_ok=True)

    _, imageFilename = os.path.split(imagePath)
    destinationPath = os.path.join(folderName, imageFilename)
    os.rename(imagePath, destinationPath)


def main(directory):
    """
    Main validation function - now uses STABLE threaded parallel processing for maximum speed!
    This replaces the previous sequential approach with high-performance threaded validation.
    """
    try:
        logging.info("=" * 60)
        logging.info("🚀 STARTING THREADED PARALLEL PHOTO VALIDATION 🚀")
        logging.info("=" * 60)
        logging.info(f"Target directory: {directory}")
        
        # Call the threaded parallel validation function
        results = main_threaded(directory)
        
        if results:
            logging.info("=" * 60)
            logging.info("🎯 THREADED VALIDATION PERFORMANCE SUMMARY 🎯")
            logging.info("=" * 60)
            logging.info(f"✅ Successfully processed {results['total_processed']} images")
            logging.info(f"✅ Valid images: {results['valid_count']}")
            logging.info(f"❌ Invalid images: {results['invalid_count']}")
            logging.info(f"⚡ Total time: {results['processing_time']:.2f} seconds")
            logging.info(f"⚡ Average per image: {results['avg_time_per_image']:.3f} seconds")
            logging.info(f"🚀 Processing speed: {results['images_per_second']:.2f} images/second")
            logging.info(f"🔥 Speedup factor: {results['speedup_factor']:.1f}x faster than sequential!")
            logging.info(f"🛠️  Threads used: {results['workers_used']}")
        
        logging.info("=" * 60)
        logging.info("🎉 THREADED PARALLEL VALIDATION COMPLETED SUCCESSFULLY! 🎉")
        logging.info("=" * 60)
        
        return HttpResponse("Threaded parallel validation completed successfully!")
        
    except Exception as e:
        logging.error(f"Error in threaded parallel validation: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return HttpResponse(f"Validation failed: {str(e)}", status=500)


if __name__ == "__main__":
    main()
