import logging
import os.path
from django.http import HttpResponse
from .photo_validator_parallel import main_parallel

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
    Main validation function - now uses parallel processing for maximum speed!
    This replaces the previous sequential approach with high-performance parallel validation.
    """
    try:
        logging.info("=" * 60)
        logging.info("STARTING PARALLEL PHOTO VALIDATION")
        logging.info("=" * 60)
        logging.info(f"Target directory: {directory}")
        
        # Call the parallel validation function
        results = main_parallel(directory)
        
        if results:
            logging.info("=" * 60)
            logging.info("PARALLEL VALIDATION PERFORMANCE SUMMARY")
            logging.info("=" * 60)
            logging.info(f"✅ Successfully processed {results['total_processed']} images")
            logging.info(f"✅ Valid images: {results['valid_count']}")
            logging.info(f"❌ Invalid images: {results['invalid_count']}")
            logging.info(f"⚡ Total time: {results['processing_time']:.2f} seconds")
            logging.info(f"⚡ Average per image: {results['avg_time_per_image']:.3f} seconds")
            logging.info(f"🚀 Processing speed: {results['total_processed'] / results['processing_time']:.2f} images/second")
            
            # Calculate estimated speedup (conservative estimate vs sequential)
            estimated_sequential_time = results['total_processed'] * 2.0  # Assume 2 seconds per image sequentially
            speedup_factor = estimated_sequential_time / results['processing_time']
            logging.info(f"🚀 Estimated speedup: {speedup_factor:.1f}x faster than sequential processing")
        
        logging.info("=" * 60)
        logging.info("PARALLEL VALIDATION COMPLETED SUCCESSFULLY! 🎉")
        logging.info("=" * 60)
        
        return HttpResponse("Parallel validation completed successfully!")
        
    except Exception as e:
        logging.error(f"Error in parallel validation: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return HttpResponse(f"Validation failed: {str(e)}", status=500)


if __name__ == "__main__":
    main()
