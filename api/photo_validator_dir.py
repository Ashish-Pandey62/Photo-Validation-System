import logging
import os.path
import time
import datetime
from shutil import move
from django.conf import settings
from django.http import HttpResponse

from .models import Config

import cv2
import csv

import api.background_check as background_check
import api.blur_check as blur_check
import api.file_format_check as file_format_check
import api.file_size_check as file_size_check
import api.grey_black_and_white_check as grey_black_and_white_check
import api.head_check as head_check
import api.symmetry_check as symmetry_check
import time


logging.basicConfig(level=logging.INFO)


def moveToFolder(label, imagePath):

    folderName = os.path.join(os.getcwd(), label)
    os.makedirs(folderName, exist_ok=True)

    _, imageFilename = os.path.split(imagePath)
    destinationPath = os.path.join(folderName, imageFilename)
    os.rename(imagePath, destinationPath)


def main(directory):
    # Ensure directory exists
    if not os.path.exists(directory):
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    # Safely get config object
    try:
        config = Config.objects.first()
        if not config:
            # Create default config if none exists
            config = Config.objects.create(
                min_height=100,
                max_height=2000,
                min_width=100,
                max_width=2000,
                min_size=10,
                max_size=5000,
                is_jpg=True,
                is_png=True,
                is_jpeg=True
            )
    except Exception as e:
        # Create a fallback config
        config = Config(
            min_height=100,
            max_height=2000,
            min_width=100,
            max_width=2000,
            min_size=10,
            max_size=5000,
            is_jpg=True,
            is_png=True,
            is_jpeg=True
        )
        config.save()
        
    initialTime = time.time()

    # make valid and invalid directories using os.path.join for cross-platform compatibility
    validDirectory = os.path.join(directory, "valid")
    
    seconds = time.time()

    invalid_images_static_directory = os.path.join(
        settings.BASE_DIR, "api", "static", "api", "images", "invalid"
    )

    resultFile_static_directory = os.path.join(
        settings.BASE_DIR, "api", "static", "api", "images", "result.csv"
    )

    # Ensure all required directories exist
    os.makedirs(validDirectory, exist_ok=True)
    os.makedirs(invalid_images_static_directory, exist_ok=True)
    
    # Ensure result file directory exists
    os.makedirs(os.path.dirname(resultFile_static_directory), exist_ok=True)

    if not os.path.exists(resultFile_static_directory):
        rows = []
        with open(resultFile_static_directory, "w", newline="") as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerows(rows)  # empty csv

    error_message = {}
    fileLists = sorted(os.listdir(directory))
    logging.info(f"Found {len(fileLists)} files to process in directory: {directory}")
    
    for image in fileLists:
        logging.info("processing Image: " + image)

        messages = []

        imagePath = os.path.join(directory, image)

        if os.path.isdir(imagePath):
            logging.info(f"Skipping directory: {image}")
            continue

        # Check image file format
        if config.bypass_format_check == False:
            try:
                is_file_format_valid = file_format_check.check_image(imagePath)
                if not is_file_format_valid:
                    messages.append("File format check failed")
            except Exception as e:
                logging.error(f"Error in file format check for {image}: {e}")

        if config.bypass_size_check == False:
            try:
                is_file_size_valid = file_size_check.check_image(imagePath)
                if not is_file_size_valid:
                    messages.append("File size check failed")
            except Exception as e:
                logging.error(f"Error in file size check for {image}: {e}")

        if config.bypass_height_check == False:
            try:
                is_file_height_valid = file_size_check.check_height(imagePath)
                if not is_file_height_valid:
                    messages.append("File height check failed")
            except Exception as e:
                logging.error(f"Error in file height check for {image}: {e}")

        if config.bypass_width_check == False:
            try:
                is_file_width_valid = file_size_check.check_width(imagePath)
                if not is_file_width_valid:
                    messages.append("File width check failed")
            except Exception as e:
                logging.error(f"Error in file width check for {image}: {e}")

        # Load the image
        try:
            img = cv2.imread(imagePath)
            if img is None:
                messages.append("Could not load image")
                logging.error(f"Failed to load image: {imagePath}")
                # Skip further processing for this image
                if len(messages) > 0:
                    error_message[image] = messages
                    try:
                        if os.path.exists(os.path.join(invalid_images_static_directory, image)):
                            continue
                        move(imagePath, invalid_images_static_directory)
                        logging.info(f"Moved {image} to invalid directory due to load failure")
                    except Exception as e:
                        logging.error(f"Error moving {image} to invalid directory: {e}")
                continue
        except Exception as e:
            messages.append(f"Error loading image: {str(e)}")
            logging.error(f"Exception loading image {imagePath}: {e}")
            # Skip further processing for this image
            if len(messages) > 0:
                error_message[image] = messages
                try:
                    if os.path.exists(os.path.join(invalid_images_static_directory, image)):
                        continue
                    move(imagePath, invalid_images_static_directory)
                    logging.info(f"Moved {image} to invalid directory due to load exception")
                except Exception as move_e:
                    logging.error(f"Error moving {image} to invalid directory: {move_e}")
            continue

        # Check if corrupted image
        if config.bypass_corrupted_check == False:
            try:
                if file_format_check.is_corrupted_image(img):
                    messages.append("Corrupted Image")
            except Exception as e:
                logging.error(f"Error in corrupted image check for {image}: {e}")

        # Check for grey image
        if config.bypass_greyness_check == False:
            try:
                if grey_black_and_white_check.is_grey(img):
                    messages.append("GreyScale check failed")
            except Exception as e:
                logging.error(f"Error in greyness check for {image}: {e}")

        # Check image for blurness
        if config.bypass_blurness_check == False:
            try:
                if blur_check.check_image_blurness(img):
                    messages.append("Blurness check failed")
            except Exception as e:
                logging.error(f"Error in blurness check for {image}: {e}")

        # Check the background of image
        if config.bypass_background_check == False:
            try:
                if not background_check.background_check(img):
                    messages.append("Background check failed")
            except Exception as e:
                logging.error(f"Error in background check for {image}: {e}")

        # Check image for head position and coverage
        if config.bypass_head_check == False:
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
                logging.error(f"Error in head check for {image}: {e}")

        if config.bypass_eye_check == False:
            try:
                if head_check.detect_eyes(img):
                    messages.append("Eye check failed")
            except Exception as e:
                logging.error(f"Error in eye check for {image}: {e}")

        # Check for symmetry
        if config.bypass_symmetry_check == False:
            try:
                if not symmetry_check.issymmetric(img):
                    messages.append("Symmetry check failed")
            except Exception as e:
                logging.error(f"Error in symmetry check for {image}: {e}")

        # logging.info("Copying valid and invalid images to respective folders...")
        if len(messages) > 0:
            error_message[image] = messages
            logging.info(f"Image {image} failed validation: {messages}")
            # move(imagePath, invalidDirectory)
            try:
                if os.path.exists(os.path.join(invalid_images_static_directory, image)):
                    logging.info(f"File {image} already exists in invalid directory, skipping move")
                    continue
                move(imagePath, invalid_images_static_directory)
                logging.info(f"Moved {image} to invalid directory")
            except Exception as e:
                logging.error(f"Error moving {image} to invalid directory: {e}")
                # copy(imagePath, invalid_directory)
        else:
            logging.info(f"Image {image} passed all validation checks")
            try:
                if os.path.exists(os.path.join(validDirectory, image)):
                    logging.info(f"File {image} already exists in valid directory, skipping move")
                    continue
                move(imagePath, validDirectory)
                logging.info(f"Moved {image} to valid directory")
            except Exception as e:
                logging.error(f"Error moving {image} to valid directory: {e}")

    csv_string = ""
    if len(error_message) > 0:
        for name in error_message.keys():
            csv_string = csv_string + name
            for category in error_message[name]:
                csv_string = csv_string + "," + category
            csv_string = csv_string + "\n"
    else:
        logging.info("There are no invalid images")
        # Write a summary header when no invalid images found
        csv_string = f"# Validation Summary: {len(fileLists)} images processed, {len(error_message)} invalid images found\n"
        csv_string += f"# Validation completed at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        if len(fileLists) > 0:
            csv_string += "# All images passed validation!\n"

    logging.info("Writing result to result.csv... ")
    with open(resultFile_static_directory, "a") as f:
        f.write(csv_string)  # Give your csv text here.
    # print(csv_string)
    finalTime = time.time()

    logging.info("Total Image Parsed = " + str(len(fileLists)))
    logging.info("Total Invalid Image = " + str(len(error_message)))
    logging.info(
        "Total time taken to validate "
        + str(len(fileLists))
        + " images = "
        + str(finalTime - initialTime)
        + " seconds"
    )
    
    # Log summary of results
    valid_count = len(fileLists) - len(error_message)
    logging.info(f"Validation Summary: {valid_count} valid images, {len(error_message)} invalid images")
    
    if len(error_message) > 0:
        logging.info("Invalid images and their issues:")
        for image, issues in error_message.items():
            logging.info(f"  {image}: {', '.join(issues)}")

    return HttpResponse("Validation completed")


if __name__ == "__main__":
    main()
