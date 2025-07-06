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
    config = Config.objects.all()[0]
    initialTime = time.time()

    # make valid and invalid directories
    validDirectory = directory + "\\" + "valid\\"
    # validDirectory = directory + "/" + "valid/"
    # invalidDirectory = directory + "/" + "invalid/"

    seconds = time.time()

    invalid_images_static_directory = os.path.join(
        settings.STATIC_ROOT, "api", "static", "api", "images", "invalid"
    )

    resultFile_static_directory = os.path.join(
        settings.STATIC_ROOT, "api", "static", "api", "images", "result.csv"
    )

    if not os.path.exists(validDirectory):
        os.mkdir(validDirectory)

    # Create the directory if it doesn't exist
    if not os.path.exists(invalid_images_static_directory):
        os.makedirs(invalid_images_static_directory)

    if not os.path.exists(resultFile_static_directory):
        rows = []
        with open(resultFile_static_directory, "w", newline="") as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerows(rows)  # empty csv

    error_message = {}
    fileLists = sorted(os.listdir(directory))
    for image in fileLists:
        logging.info("processing Image: " + image)

        messages = []

        imagePath = directory + "/" + image

        if os.path.isdir(imagePath):
            continue

        # Check image file format
        if config.bypass_format_check == False:
            is_file_format_valid = file_format_check.check_image(imagePath)
            if not is_file_format_valid:
                messages.append("File format check failed")

        if config.bypass_size_check == False:
            is_file_size_valid = file_size_check.check_image(imagePath)
            if not is_file_size_valid:
                messages.append("File size check failed")

        if config.bypass_height_check == False:
            is_file_height_valid = file_size_check.check_height(imagePath)
            if not is_file_height_valid:
                messages.append("File height check failed")

        if config.bypass_width_check == False:
            is_file_width_valid = file_size_check.check_width(imagePath)
            if not is_file_width_valid:
                messages.append("File width check failed")

        # Load the image
        img = cv2.imread(imagePath)

        # Check if corrupted image
        if config.bypass_corrupted_check == False:
            if file_format_check.is_corrupted_image(img):
                messages.append("Corrupted Image")

        # Check for grey image
        if config.bypass_greyness_check == False:
            if grey_black_and_white_check.is_grey(img):
                messages.append("GreyScale check failed")

        # Check image for blurness
        if config.bypass_blurness_check == False:
            if blur_check.check_image_blurness(img):
                messages.append("Blurness check failed")

        # Check the background of image
        if config.bypass_background_check == False:
            if not background_check.background_check(img):
                messages.append("Background check failed")

        # Check image for head position and coverage
        if config.bypass_head_check == False:
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

        if config.bypass_eye_check == False:
            if head_check.detect_eyes(img):
                messages.append("Eye check failed")

        # Check for symmetry
        if config.bypass_symmetry_check == False:
            if not symmetry_check.issymmetric(img):
                messages.append("Symmetry check failed")

        # logging.info("Copying valid and invalid images to respective folders...")
        if len(messages) > 0:
            error_message[image] = messages
            # move(imagePath, invalidDirectory)
            if os.path.exists(os.path.join(invalid_images_static_directory, image)):
                continue
            move(imagePath, invalid_images_static_directory)
            # copy(imagePath, invalid_directory)
        else:
            if os.path.exists(os.path.join(validDirectory, image)):
                continue
            move(imagePath, validDirectory)

    csv_string = ""
    if len(error_message) > 0:
        for name in error_message.keys():
            csv_string = csv_string + name
            for category in error_message[name]:
                csv_string = csv_string + "," + category
            csv_string = csv_string + "\n"
    else:
        logging.info("There are no invalid images")

    logging.info("Writing result to result.csv... ")
    f = open(resultFile_static_directory, "a")
    f.write(csv_string)  # Give your csv text here.
    # Python will convert \n to os.linesep
    f.close()
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

    return HttpResponse("Validation completed")


if __name__ == "__main__":
    main()
