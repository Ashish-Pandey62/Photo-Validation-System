import logging
import os
from django.conf import settings
from django import forms
from django.http import HttpResponse
from django.shortcuts import render, redirect

import api.photo_validator as photo_validator
import api.photo_validator_dir as photo_validator_dir
from api.forms import PhotoFolderUploadForm

# import api.tinkerdirectory as tinker
from .models import Config, PhotoFolder

# import urllib.parse
import shutil
import zipfile
import csv


# Create your views here.
class NameForm(forms.Form):
    your_name = forms.CharField(label="Your name", max_length=100)


# def startPage(request):
#     context = {}
#     config = Config.objects.all()[0]
#     return render(request, 'api/index1.html', {'config': config})

def startPage(request):
    """Main page view with safe config retrieval"""
    form = PhotoFolderUploadForm()
    
    # Safely get or create a default config
    try:
        config = Config.objects.first()
        if not config:
            # Create a default config if none exists
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
        # If there's any error, create a new config
        config = Config(
            min_height=100,
            max_height=2000,
            min_width=100,
            max_width=2000,
            min_size=10,
            max_size=5000,
            is_jpg="True",
            is_png="True",
            is_jpeg="True"
        )
        config.save()
    
    return render(request, 'api/index1.html', {'config': config, 'form': form})

# def dialogueBox(request):


def process_image(request):
    # Get or create config safely
    try:
        config = Config.objects.first()
        if not config:
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

    if request.method == "POST":
        form = PhotoFolderUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # get the uploaded zip file and extract it
                folder = form.cleaned_data["folder"]
                photo_folder = PhotoFolder(folder=folder)
                photo_folder.save()
                
                # Ensure media directories exist
                media_root = settings.MEDIA_ROOT
                if not os.path.exists(media_root):
                    os.makedirs(media_root)
                
                photo_folder_dir = os.path.join(media_root, "photo_folder")
                if not os.path.exists(photo_folder_dir):
                    os.makedirs(photo_folder_dir)
                
                photos_dir = os.path.join(media_root, "photos")
                if not os.path.exists(photos_dir):
                    os.makedirs(photos_dir)
                
                folder_path = os.path.join(photo_folder_dir, folder.name)
                
                # Extract the ZIP file
                with zipfile.ZipFile(folder_path, "r") as zip_ref:
                    zip_ref.extractall(photos_dir)

                # Determine the extracted folder path
                extracted_folder_name = os.path.splitext(folder.name)[0]
                path = os.path.join(photos_dir, extracted_folder_name)
                
                # Check if the extracted path exists and has images
                if not os.path.exists(path):
                    # Try to find the extracted content
                    for item in os.listdir(photos_dir):
                        item_path = os.path.join(photos_dir, item)
                        if os.path.isdir(item_path) and item.startswith(extracted_folder_name):
                            path = item_path
                            break
                    else:
                        # If still not found, use the main photos directory
                        path = photos_dir
                
                # Check if the target directory has any images
                image_extensions = ('.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG')
                images_in_path = [f for f in os.listdir(path) if f.endswith(image_extensions)]
                
                # If no images in the target directory, but images exist in the main photos_dir, use that instead
                if not images_in_path and path != photos_dir:
                    images_in_main = [f for f in os.listdir(photos_dir) if f.endswith(image_extensions)]
                    if images_in_main:
                        path = photos_dir
                
                # Ensure the invalid images directory exists
                invalid_images_dir = os.path.join(
                    settings.BASE_DIR, "api", "static", "api", "images", "invalid"
                )
                if not os.path.exists(invalid_images_dir):
                    os.makedirs(invalid_images_dir)
                
                # processing the image
                # logging.info("Validating images from path: " + path)
                request.session["path"] = path
                photo_validator_dir.main(path)
                
                # Redirect to a results page or show success message
                from django.contrib import messages
                messages.success(request, 'Photo validation completed successfully!')
                
            except Exception as e:
                from django.contrib import messages
                messages.error(request, f'Error processing upload: {str(e)}')
                print(f"Error in process_image: {e}")
            
            # return render(request, 'api/image_gallery.html')
        else:
            print(form.errors)
            print(request.FILES)
    else:
        form = PhotoFolderUploadForm()
    
    return render(request, "api/index1.html", {"form": form, "config": config})


# def process_image(request):

# path = request.POST['path']
# type = request.POST['type']

# logging.info("Validating images from path: " + path)
# if type == 'folder':
#   request.session['path'] = path
#   photo_validator_dir.main(path)
#   return HttpResponse("Validation Completed")
# else:
#   message = photo_validator.main(path)
#   return HttpResponse("Results:" + "\n" + message)


def save_config(request):
    if request.method == "POST":
        try:
            minHeight = float(request.POST.get("minHeight", 100))
            maxHeight = float(request.POST.get("maxHeight", 2000))
            minWidth = float(request.POST.get("minWidth", 100))
            maxWidth = float(request.POST.get("maxWidth", 2000))
            minSize = float(request.POST.get("minSize", 10))
            maxSize = float(request.POST.get("maxSize", 5000))
            
            # Handle checkbox values properly
            jpgchecked = request.POST.get("jpgchecked") == "on"
            pngchecked = request.POST.get("pngchecked") == "on"
            jpegchecked = request.POST.get("jpegchecked") == "on"

            # Get existing config or create new one
            config = Config.objects.first()
            if not config:
                config = Config()

            config.min_height = minHeight
            config.max_height = maxHeight
            config.min_width = minWidth
            config.max_width = maxWidth
            config.min_size = minSize
            config.max_size = maxSize
            config.is_jpg = jpgchecked
            config.is_png = pngchecked
            config.is_jpeg = jpegchecked

            config.save()

            return HttpResponse("Configuration updated successfully")
        except Exception as e:
            return HttpResponse(f"Error updating configuration: {str(e)}", status=400)
    else:
        return HttpResponse("Method not allowed", status=405)


def image_gallery(request):
    images = []

    invalid_images_directory = os.path.join(
        settings.STATIC_ROOT, "api", "static", "api", "images", "invalid"
    )

    # read the reasons for invalidity from the results.csv file
    result_file = os.path.join(
        settings.STATIC_ROOT, "api", "static", "api", "images", "result.csv"
    )
    reasons_for_invalidity = {}  # a dict

    with open(result_file, "r") as csv_file:
        csv_reader = csv.reader(csv_file)
        for row in csv_reader:
            image_filename = row[0]  # The image filename is in the first column
            reasons = row[1:]  # Initialize the list of reasons
            reasons_for_invalidity[image_filename] = reasons

    context = {
        "images_with_paths": images,
        "reasons_for_invalidity": reasons_for_invalidity,
    }

    for filename in os.listdir(invalid_images_directory):
        if (
            filename.endswith(".jpg")
            or filename.endswith(".jpeg")
            or filename.endswith(".png")
        ):
            images.append(os.path.join(invalid_images_directory, filename))

    return render(request, "api/image_gallery.html", context)


def process_selected_images(request):
    if request.method == "POST":
        path = request.session.get("path")
        validDirectory = path + "/" + "valid/"
        # validDirectory = path + "/" + "valid/"
        result_file = os.path.join(
            settings.STATIC_ROOT, "api", "static", "api", "images", "result.csv"
        )

        if not os.path.exists(validDirectory):
            os.mkdir(validDirectory)

        selected_images = request.POST.getlist("selected_images")

        # read the CSV file into a list of rows
        rows_to_keep = []
        with open(result_file, "r") as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                image_filename = row[0]
                if image_filename not in selected_images:
                    rows_to_keep.append(
                        row
                    )  # Keep the row if the image is not in the selected list

        # Write the updated rows (excluding the removed row) back to the CSV file
        with open(result_file, "w", newline="") as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerows(rows_to_keep)

        for image_name in selected_images:
            image_path = os.path.join(
                settings.STATIC_ROOT,
                "api",
                "static",
                "api",
                "images",
                "invalid",
                image_name,
            )
            destination_path = os.path.join(validDirectory, image_name)

            try:
                shutil.move(image_path, destination_path)
                print(f"Moved from {image_path} to {destination_path}: {e}")

            except Exception as e:
                print(f"Error moving {image_path} to {destination_path}: {e}")

        # now that the directory's content is changed
        images = []
        invalid_images_directory = os.path.join(
            settings.STATIC_ROOT, "api", "static", "api", "images", "invalid"
        )

        # read the reasons for invalidity from the results.csv file
        reasons_for_invalidity = {}  # a dict

        with open(result_file, "r") as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                image_filename = row[0]  # The image filename is in the first column
                reasons = row[1:]  # Initialize the list of reasons
                reasons_for_invalidity[image_filename] = reasons

        context = {
            "images_with_paths": images,
            "reasons_for_invalidity": reasons_for_invalidity,
        }

        for filename in os.listdir(invalid_images_directory):
            if (
                filename.endswith(".jpg")
                or filename.endswith(".jpeg")
                or filename.endswith(".png")
            ):
                images.append(os.path.join(invalid_images_directory, filename))

        return render(request, "api/image_gallery.html", context)

    return HttpResponse("Method not allowed", status=405)


def process_rejected_images(request):
    if request.method == "POST":
        path = request.session.get("path")
        invalidDirectory = path + "/" + "invalid/"
        # invalidDirectory = path + "/" + "invalid/"

        if not os.path.exists(invalidDirectory):
            os.mkdir(invalidDirectory)

        invalid_images_directory = os.path.join(
            settings.STATIC_ROOT, "api", "static", "api", "images", "invalid"
        )

        # Get a list of all image files in invalid_images_directory
        image_files = [
            filename
            for filename in os.listdir(invalid_images_directory)
            if filename.lower().endswith((".jpg", ".jpeg", ".png"))
        ]

        for image_name in image_files:
            source_path = os.path.join(invalid_images_directory, image_name)
            destination_path = os.path.join(invalidDirectory, image_name)

            try:
                shutil.move(source_path, destination_path)
                print(f"Moved from {source_path} to {destination_path}")
            except Exception as e:
                print(f"Error moving {source_path} to {destination_path}: {e}")

        newcsvFile = path + "/" + "results.csv"
        # newcsvFile = path + "/" + "results.csv"
        oldcsvFile = os.path.join(
            settings.STATIC_ROOT, "api", "static", "api", "images", "result.csv"
        )
        rows = []

        with open(oldcsvFile, "r") as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                rows.append(row)

        # Write the updated rows (excluding the removed row) back to the CSV file
        with open(newcsvFile, "w", newline="") as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerows(rows)

        # emptying the old csv
        rows = []
        with open(oldcsvFile, "w", newline="") as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerows(rows)

    return redirect("displayCsv")


def display_csv(request):
    csv_data = []
    path = request.session.get("path")
    newcsvFile = path + "/" + "results.csv"
    # newcsvFile = path + "/" + "results.csv"

    with open(newcsvFile, "r") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            csv_data.append(row)

    return render(request, "api/display_csv.html", {"csv_data": csv_data})
    # return render(request, 'api/display_csv.html', {'csv_data': csv_data})


def delete_all(request):
    folder_to_delete = os.path.join(settings.MEDIA_ROOT)
    invalid_folder = os.path.join(
        settings.BASE_DIR, "api", "static", "api", "images", "invalid"
    )
    if os.path.exists(folder_to_delete) and os.path.isdir(folder_to_delete):
        try:
            shutil.rmtree(folder_to_delete)
        except Exception as e:
            print(f"Error deleting folder: {e}")
    if os.path.exists(invalid_folder) and os.path.isdir(invalid_folder):
        print(invalid_folder)
        try:
            shutil.rmtree(invalid_folder)
        except Exception as e:
            print(f"Error deleting folder: {e}")

    if not os.path.exists(invalid_folder):
        os.mkdir(invalid_folder)
    form = PhotoFolderUploadForm()
    return render(request, "api/index1.html", {"form": form})
    # return render(request, 'api/index1.html', {'form': form})


def download_and_delete_csv(request):
    path = request.session.get("path") + "/" + "results.csv"
    # path = request.session.get('path') + "/" + "results.csv"
    folder_to_delete = os.path.join(settings.MEDIA_ROOT)

    with open(path, "rb") as csv_file:
        response = HttpResponse(csv_file.read(), content_type="text\\csv")
        # response = HttpResponse(csv_file.read(), content_type='text/csv')
        response["Content-Disposition"] = 'attachment; filename="results.csv"'

    if os.path.exists(folder_to_delete) and os.path.isdir(folder_to_delete):
        try:
            shutil.rmtree(folder_to_delete)
        except Exception as e:
            print(f"Error deleting folder: {e}")

    return response
