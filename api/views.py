def clear_data(request):
    """Clear all uploaded and tested images and cache for a fresh start."""
    if request.method == "POST":
        # Remove media/photos and media/photos/valid
        media_photos = os.path.join(settings.MEDIA_ROOT, "photos")
        if os.path.exists(media_photos):
            try:
                shutil.rmtree(media_photos)
            except Exception as e:
                logging.error(f"Error deleting media/photos: {e}")

        # Remove media/photo_folder (contains uploaded ZIP files)
        media_photo_folder = os.path.join(settings.MEDIA_ROOT, "photo_folder")
        if os.path.exists(media_photo_folder):
            try:
                shutil.rmtree(media_photo_folder)
            except Exception as e:
                logging.error(f"Error deleting media/photo_folder: {e}")

        # Remove api/static/api/images/invalid and result.csv
        invalid_folder = os.path.join(settings.BASE_DIR, "api", "static", "api", "images", "invalid")
        result_file = os.path.join(settings.BASE_DIR, "api", "static", "api", "images", "result.csv")
        if os.path.exists(invalid_folder):
            try:
                shutil.rmtree(invalid_folder)
            except Exception as e:
                logging.error(f"Error deleting invalid images folder: {e}")
        if not os.path.exists(invalid_folder):
            os.makedirs(invalid_folder, exist_ok=True)
        if os.path.exists(result_file):
            try:
                os.remove(result_file)
            except Exception as e:
                logging.error(f"Error deleting result.csv: {e}")

        # Optionally clear session data
        request.session.flush()

        # Redirect to home page with fresh form
        form = PhotoFolderUploadForm()
        config = Config.objects.first()
        bypass_list = [
            'bypass_height_check', 'bypass_width_check', 'bypass_size_check',
            'bypass_format_check', 'bypass_background_check', 'bypass_blurness_check',
            'bypass_greyness_check', 'bypass_symmetry_check', 'bypass_head_check',
            'bypass_eye_check', 'bypass_corrupted_check'
        ]
        return render(request, 'api/index1.html', {'bypass_list': bypass_list, 'config': config, 'form': form})
    else:
        return HttpResponse("Method not allowed", status=405)
import logging
import os
from django.conf import settings
from django import forms
from django.http import HttpResponse
from django.shortcuts import render, redirect

import api.photo_validator as photo_validator
import api.photo_validator_dir as photo_validator_dir
from api.forms import PhotoFolderUploadForm
from api.blur_check import check_image_blurness
from api.symmetry_check import check_symmetry_with_head
from api.file_format_check import is_corrupted_image

# import api.tinkerdirectory as tinker
from .models import Config, PhotoFolder

# import urllib.parse
import shutil
import zipfile

def health_check(request):
    return HttpResponse("OK")
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
                is_jpeg=True,
                bg_uniformity_threshold=25
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
            is_jpeg="True",
            bg_uniformity_threshold=25
        )
        config.save()
    
    # views.py
    bypass_list = [
        'bypass_height_check', 'bypass_width_check', 'bypass_size_check',
        'bypass_format_check', 'bypass_background_check', 'bypass_blurness_check',
        'bypass_greyness_check', 'bypass_symmetry_check', 'bypass_head_check',
        'bypass_eye_check', 'bypass_corrupted_check'
    ]



    return render(request, 'api/index1.html', {'bypass_list': bypass_list,'config': config, 'form': form})

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
                is_jpeg=True,
                bg_uniformity_threshold=25
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
            is_jpeg=True,
            bg_uniformity_threshold=25
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
                
                # Save the uploaded file to disk
                folder_path = os.path.join(photo_folder_dir, folder.name)
                logging.info(f"Saving uploaded file to: {folder_path}")
                with open(folder_path, 'wb+') as destination:
                    for chunk in folder.chunks():
                        destination.write(chunk)
                
                # Extract the ZIP file
                logging.info(f"Extracting ZIP file from: {folder_path} to: {photos_dir}")
                with zipfile.ZipFile(folder_path, "r") as zip_ref:
                    zip_ref.extractall(photos_dir)
                
                # List contents after extraction
                logging.info(f"Contents of photos_dir after extraction: {os.listdir(photos_dir)}")

                # Determine the extracted folder path
                extracted_folder_name = os.path.splitext(folder.name)[0]
                path = os.path.join(photos_dir, extracted_folder_name)
                logging.info(f"Initial path assumption: {path}")
                
                # Check if the extracted path exists
                if not os.path.exists(path):
                    logging.info(f"Path {path} does not exist, checking for direct image files")
                    # Check if images were extracted directly to photos_dir (no subfolder)
                    image_files = [f for f in os.listdir(photos_dir) 
                                 if os.path.isfile(os.path.join(photos_dir, f)) 
                                 and f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif'))]
                    
                    logging.info(f"Found {len(image_files)} image files directly in photos_dir: {image_files}")
                    
                    if image_files:
                        # Images were extracted directly, use photos_dir as the path
                        path = photos_dir
                        logging.info(f"Using photos_dir as path: {path}")
                    else:
                        logging.info("No direct image files found, checking subdirectories")
                        # Try to find the extracted content in subdirectories
                        for item in os.listdir(photos_dir):
                            item_path = os.path.join(photos_dir, item)
                            if os.path.isdir(item_path) and item.startswith(extracted_folder_name):
                                path = item_path
                                logging.info(f"Found matching subdirectory: {path}")
                                break
                        else:
                            # If still not found, create the directory
                            logging.info(f"No matching subdirectory found, creating: {path}")
                            os.makedirs(path, exist_ok=True)
                else:
                    logging.info(f"Path {path} exists")
                
                # Ensure the invalid images directory exists
                invalid_images_dir = os.path.join(
                    settings.BASE_DIR, "api", "static", "api", "images", "invalid"
                )
                if not os.path.exists(invalid_images_dir):
                    os.makedirs(invalid_images_dir)
                
                # processing the image
                logging.info(f"Validating images from path: {path}")
                request.session["path"] = path
                
                # Check if path contains any image files
                if os.path.exists(path):
                    files_in_path = os.listdir(path)
                    image_files = [f for f in files_in_path 
                                 if os.path.isfile(os.path.join(path, f)) 
                                 and f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif'))]
                    logging.info(f"Found {len(image_files)} image files in {path}")
                    if not image_files:
                        raise Exception(f"No image files found in {path}. Available files: {files_in_path}")
                    
                    # Store total count in session for later use
                    request.session["total_images_count"] = len(image_files)
                    logging.info(f"Stored total images count in session: {len(image_files)}")
                
                photo_validator_dir.main(path)
                
                # Redirect to a results page or show success message
                from django.contrib import messages
                messages.success(request, 'Photo validation completed successfully!')
                
            except Exception as e:
                from django.contrib import messages
                messages.error(request, f'Error processing upload: {str(e)}')
                print(f"Error in process_image: {e}")
                logging.error(f"Error in process_image: {e}")
                import traceback
                logging.error(f"Traceback: {traceback.format_exc()}")
            
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
            # Basic dimension and size settings
            minHeight = float(request.POST.get("minHeight", 100))
            maxHeight = float(request.POST.get("maxHeight", 2000))
            minWidth = float(request.POST.get("minWidth", 100))
            maxWidth = float(request.POST.get("maxWidth", 2000))
            minSize = float(request.POST.get("minSize", 10))
            maxSize = float(request.POST.get("maxSize", 5000))
            
            # Threshold values for quality checks
            bgcolorThreshold = float(request.POST.get("bgcolorThreshold", 40))
            bgUniformityThreshold = float(request.POST.get("bgUniformityThreshold", 25))
            blurnessThreshold = float(request.POST.get("blurnessThreshold", 30))
            pixelatedThreshold = float(request.POST.get("pixelatedThreshold", 100))
            greynessThreshold = float(request.POST.get("greynessThreshold", 5))
            symmetryThreshold = float(request.POST.get("symmetryThreshold", 35))
            
            # Handle checkbox values properly
            jpgchecked = request.POST.get("jpgchecked") == "on"
            pngchecked = request.POST.get("pngchecked") == "on"
            jpegchecked = request.POST.get("jpegchecked") == "on"
            
            # Handle bypass checkboxes
            bypass_height_check = request.POST.get("bypass_height_check") == "on"
            bypass_width_check = request.POST.get("bypass_width_check") == "on"
            bypass_size_check = request.POST.get("bypass_size_check") == "on"
            bypass_format_check = request.POST.get("bypass_format_check") == "on"
            bypass_background_check = request.POST.get("bypass_background_check") == "on"
            bypass_blurness_check = request.POST.get("bypass_blurness_check") == "on"
            bypass_greyness_check = request.POST.get("bypass_greyness_check") == "on"
            bypass_symmetry_check = request.POST.get("bypass_symmetry_check") == "on"
            bypass_head_check = request.POST.get("bypass_head_check") == "on"
            bypass_eye_check = request.POST.get("bypass_eye_check") == "on"
            bypass_corrupted_check = request.POST.get("bypass_corrupted_check") == "on"

            # Get existing config or create new one
            config = Config.objects.first()
            if not config:
                config = Config()

            # Save basic settings
            config.min_height = minHeight
            config.max_height = maxHeight
            config.min_width = minWidth
            config.max_width = maxWidth
            config.min_size = minSize
            config.max_size = maxSize
            config.is_jpg = jpgchecked
            config.is_png = pngchecked
            config.is_jpeg = jpegchecked
            
            # Save threshold settings
            config.bgcolor_threshold = bgcolorThreshold
            config.bg_uniformity_threshold = bgUniformityThreshold
            config.blurness_threshold = blurnessThreshold
            config.pixelated_threshold = pixelatedThreshold
            config.greyness_threshold = greynessThreshold
            config.symmetry_threshold = symmetryThreshold
            
            # Save bypass settings
            config.bypass_height_check = bypass_height_check
            config.bypass_width_check = bypass_width_check
            config.bypass_size_check = bypass_size_check
            config.bypass_format_check = bypass_format_check
            config.bypass_background_check = bypass_background_check
            config.bypass_blurness_check = bypass_blurness_check
            config.bypass_greyness_check = bypass_greyness_check
            config.bypass_symmetry_check = bypass_symmetry_check
            config.bypass_head_check = bypass_head_check
            config.bypass_eye_check = bypass_eye_check
            config.bypass_corrupted_check = bypass_corrupted_check

            config.save()

            return HttpResponse("Configuration updated successfully")
        except Exception as e:
            return HttpResponse(f"Error updating configuration: {str(e)}", status=400)
    else:
        return HttpResponse("Method not allowed", status=405)


def image_gallery(request):
    invalid_images_directory = os.path.join(
        settings.BASE_DIR, "api", "static", "api", "images", "invalid"
    )

    # read the reasons for invalidity from the results.csv file
    result_file = os.path.join(
        settings.BASE_DIR, "api", "static", "api", "images", "result.csv"
    )
    reasons_for_invalidity = {}  # a dict

    logging.info(f"Looking for invalid images in: {invalid_images_directory}")
    logging.info(f"Looking for result file at: {result_file}")

    # Check if directories exist
    if not os.path.exists(invalid_images_directory):
        logging.error(f"Invalid images directory does not exist: {invalid_images_directory}")
    else:
        logging.info(f"Invalid images directory exists, contents: {os.listdir(invalid_images_directory)}")

    if not os.path.exists(result_file):
        logging.error(f"Result file does not exist: {result_file}")
    else:
        logging.info(f"Result file exists")

    try:
        with open(result_file, "r") as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                if len(row) > 0:  # Skip empty rows
                    image_filename = row[0]  # The image filename is in the first column
                    reasons = row[1:]  # Initialize the list of reasons
                    reasons_for_invalidity[image_filename] = reasons
                    logging.info(f"Found invalid image: {image_filename} with reasons: {reasons}")
    except Exception as e:
        logging.error(f"Error reading result file: {e}")

    # First, collect all image files
    images = []
    if os.path.exists(invalid_images_directory):
        for filename in os.listdir(invalid_images_directory):
            if (
                filename.endswith(".jpg")
                or filename.endswith(".jpeg")
                or filename.endswith(".png")
                or filename.endswith(".PNG")
                or filename.endswith(".JPG")
            ):
                images.append(os.path.join(invalid_images_directory, filename))
                logging.info(f"Added image to gallery: {filename}")

    logging.info(f"Total images found for gallery: {len(images)}")
    logging.info(f"Images list: {images}")

    # Create the context that the template expects
    invalid_images = []
    for image_path in images:
        filename = os.path.basename(image_path)
        # Convert file path to URL path for web access
        # Use a direct URL to serve images from the invalid directory
        image_url = f"/invalid_image/{filename}"
        logging.info(f"Generated URL for {filename}: {image_url}")
        
        # Create a mock object that the template expects
        image_obj = type('Image', (), {
            'id': filename,
            'filename': filename,
            'photo': type('Photo', (), {'url': image_url})(),
            'reason_array': reasons_for_invalidity.get(filename, [])
        })()
        invalid_images.append(image_obj)

    # Calculate total images count
    invalid_count = len(invalid_images)
    
    # Get total count from session (stored during initial processing)
    total_images = request.session.get("total_images_count", 0)
    
    # If session doesn't have the count, calculate from current state
    if total_images == 0:
        # Count valid images from the session path if available
        valid_count = 0
        path = request.session.get("path")
        if path:
            valid_directory = os.path.join(path, "valid")
            if os.path.exists(valid_directory):
                for filename in os.listdir(valid_directory):
                    if filename.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp")):
                        valid_count += 1
        total_images = valid_count + invalid_count
    
    # Add logging for debugging
    logging.info(f"Invalid images count: {invalid_count}")
    logging.info(f"Total images count from session: {total_images}")

    context = {
        "invalid_images": invalid_images,
        "reasons_for_invalidity": reasons_for_invalidity,
        "total_images": total_images,
    }

    logging.info(f"Final context - invalid_images count: {len(invalid_images)}")
    for img in invalid_images:
        logging.info(f"  - {img.filename}: {img.photo.url}")

    return render(request, "api/image_gallery.html", context)


def valid_images_gallery(request):
    """Show valid images that passed validation"""
    path = request.session.get("path")
    if not path:
        return HttpResponse("No validation session found", status=400)
    
    valid_directory = os.path.join(path, "valid")
    valid_images = []
    
    if os.path.exists(valid_directory):
        for filename in os.listdir(valid_directory):
            if (
                filename.endswith(".jpg")
                or filename.endswith(".jpeg")
                or filename.endswith(".png")
                or filename.endswith(".PNG")
                or filename.endswith(".JPG")
            ):
                # Create a mock object for valid images
                image_obj = type('Image', (), {
                    'id': filename,
                    'filename': filename,
                    'photo': type('Photo', (), {'url': f"/valid_image/{filename}"})(),
                    'reason_array': ['Passed all validation checks']
                })()
                valid_images.append(image_obj)
    
    # Calculate total images and success rate
    valid_count = len(valid_images)
    
    # Get total count from session (stored during initial processing)
    total_images = request.session.get("total_images_count", 0)
    
    # If session doesn't have the count, calculate from current state
    if total_images == 0:
        invalid_count = 0
        # Count invalid images from the invalid directory
        invalid_directory = os.path.join(
            settings.BASE_DIR, "api", "static", "api", "images", "invalid"
        )
        if os.path.exists(invalid_directory):
            for filename in os.listdir(invalid_directory):
                if filename.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp")):
                    invalid_count += 1
        total_images = valid_count + invalid_count
    
    # Add logging for debugging
    logging.info(f"Valid images count: {valid_count}")
    logging.info(f"Total images count from session: {total_images}")
    
    # Calculate success rate
    if total_images > 0:
        success_rate = round((len(valid_images) / total_images) * 100, 1)
    else:
        success_rate = 0.0
    
    context = {
        "valid_images": valid_images,
        "title": "Valid Images Gallery",
        "total_images": total_images,
        "success_rate": success_rate
    }
    
    return render(request, "api/valid_images_gallery.html", context)


def serve_valid_image(request, filename):
    """Serve valid images directly"""
    from django.http import FileResponse
    import mimetypes
    
    path = request.session.get("path")
    if not path:
        from django.http import Http404
        raise Http404("No validation session found")
    
    valid_directory = os.path.join(path, "valid")
    image_path = os.path.join(valid_directory, filename)
    
    if os.path.exists(image_path):
        # Determine content type
        content_type, _ = mimetypes.guess_type(image_path)
        if content_type is None:
            content_type = 'application/octet-stream'
        
        # Serve the file
        response = FileResponse(open(image_path, 'rb'), content_type=content_type)
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
    else:
        from django.http import Http404
        raise Http404(f"Image {filename} not found")


def serve_invalid_image(request, filename):
    """Serve invalid images directly"""
    from django.http import FileResponse
    import mimetypes
    
    invalid_images_directory = os.path.join(
        settings.BASE_DIR, "api", "static", "api", "images", "invalid"
    )
    
    image_path = os.path.join(invalid_images_directory, filename)
    
    if os.path.exists(image_path):
        # Determine content type
        content_type, _ = mimetypes.guess_type(image_path)
        if content_type is None:
            content_type = 'application/octet-stream'
        
        # Serve the file
        response = FileResponse(open(image_path, 'rb'), content_type=content_type)
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
    else:
        from django.http import Http404
        raise Http404(f"Image {filename} not found")


def process_selected_images(request):
    """Move selected invalid images to valid folder (revalidate them)"""
    if request.method == "POST":
        path = request.session.get("path")
        validDirectory = os.path.join(path, "valid")
        result_file = os.path.join(
            settings.BASE_DIR, "api", "static", "api", "images", "result.csv"
        )

        if not os.path.exists(validDirectory):
            os.makedirs(validDirectory, exist_ok=True)

        selected_images = request.POST.getlist("selected_images")
        logging.info(f"Selected images for revalidation: {selected_images}")

        # read the CSV file into a list of rows
        rows_to_keep = []
        if os.path.exists(result_file):
            with open(result_file, "r") as csv_file:
                csv_reader = csv.reader(csv_file)
                for row in csv_reader:
                    if len(row) > 0:
                        image_filename = row[0]
                        if image_filename not in selected_images:
                            rows_to_keep.append(row)  # Keep the row if the image is not in the selected list

        # Write the updated rows (excluding the removed row) back to the CSV file
        with open(result_file, "w", newline="") as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerows(rows_to_keep)

        # Move selected images from invalid to valid directory
        moved_count = 0
        for image_name in selected_images:
            # Source: api/static/api/images/invalid/
            image_path = os.path.join(
                settings.BASE_DIR,
                "api",
                "static",
                "api",
                "images",
                "invalid",
                image_name,
            )
            # Destination: media/photos/valid/
            destination_path = os.path.join(validDirectory, image_name)

            try:
                if os.path.exists(image_path):
                    shutil.move(image_path, destination_path)
                    logging.info(f"Moved {image_name} from {image_path} to {destination_path}")
                    moved_count += 1
                else:
                    logging.warning(f"Image {image_name} not found at {image_path}")
            except Exception as e:
                logging.error(f"Error moving {image_name}: {e}")

        logging.info(f"Successfully moved {moved_count} images to valid directory")

        # Redirect back to gallery to show remaining invalid images
        return redirect('image_gallery')

    return HttpResponse("Method not allowed", status=405)


def process_rejected_images(request):
    if request.method == "POST":
        path = request.session.get("path")
        invalidDirectory = path + "/" + "invalid/"
        # invalidDirectory = path + "/" + "invalid/"

        if not os.path.exists(invalidDirectory):
            os.mkdir(invalidDirectory)

        invalid_images_directory = os.path.join(
            settings.BASE_DIR, "api", "static", "api", "images", "invalid"
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
            settings.BASE_DIR, "api", "static", "api", "images", "result.csv"
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
    """Export comprehensive validation results including both valid and invalid images"""
    path = request.session.get("path")
    if not path:
        return HttpResponse("No validation session found", status=400)
    
    valid_directory = os.path.join(path, "valid")
    invalid_directory = os.path.join(
        settings.BASE_DIR, "api", "static", "api", "images", "invalid"
    )
    result_file = os.path.join(
        settings.BASE_DIR, "api", "static", "api", "images", "result.csv"
    )
    
    # Create comprehensive results
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Image Name', 'Status', 'Validation Issues', 'User Action'])
    
    # Get valid images
    valid_images = []
    if os.path.exists(valid_directory):
        valid_images = [f for f in os.listdir(valid_directory) 
                       if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))]
    
    # Get invalid images and their issues
    invalid_data = {}
    if os.path.exists(result_file):
        with open(result_file, "r") as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                if len(row) > 0 and not row[0].startswith('#'):
                    image_filename = row[0]
                    reasons = row[1:] if len(row) > 1 else []
                    invalid_data[image_filename] = reasons
    
    # Write valid images
    for image in valid_images:
        writer.writerow([image, 'VALID', 'Passed all checks', 'Computer validated'])
    
    # Write invalid images
    for image, reasons in invalid_data.items():
        issues = ', '.join(reasons) if reasons else 'Unknown issues'
        writer.writerow([image, 'INVALID', issues, 'Needs review'])
    
    # Create response
    response = HttpResponse(output.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="validation_results.csv"'
    
    # Note: Media folder cleanup is commented out to preserve data for future use
    # Uncomment the following lines if you want to clean up after export
    # folder_to_delete = os.path.join(settings.MEDIA_ROOT)
    # if os.path.exists(folder_to_delete) and os.path.isdir(folder_to_delete):
    #     try:
    #         shutil.rmtree(folder_to_delete)
    #         logging.info("Cleaned up media folder after export")
    #     except Exception as e:
    #             logging.error(f"Error deleting folder: {e}")
    
    return response
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from PIL import Image
import io

@csrf_exempt
def test_config_image(request):
    """
    Test configuration by uploading a single image and returning its validation result.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    image_file = request.FILES.get("image")
    if not image_file:
        return JsonResponse({"error": "No image uploaded"}, status=400)

    try:
        # Load configuration from database
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
                is_jpeg=True,
                bgcolor_threshold=40,
                bg_uniformity_threshold=25,
                blurness_threshold=30,
                pixelated_threshold=100,
                greyness_threshold=5,
                symmetry_threshold=35
            )

        # Save uploaded image to a temporary file
        import tempfile
        import os
        from api.photo_validator_optimized import main_optimized

        # Get the file extension from the uploaded file
        file_extension = os.path.splitext(image_file.name)[1] or '.jpg'
        
        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as tmp:
            for chunk in image_file.chunks():
                tmp.write(chunk)
            temp_path = tmp.name

        # Run validation using main_optimized
        logging.info(f"Testing image: {image_file.name} at temporary path: {temp_path}")
        result_message = main_optimized(temp_path)
        logging.info(f"Validation result: {result_message[:100]}...")  # Log first 100 chars

        # Clean up temporary file
        try:
            os.unlink(temp_path)
        except Exception as cleanup_error:
            logging.warning(f"Could not clean up temporary file {temp_path}: {cleanup_error}")

        # Parse result_message for display with detailed analysis
        lines = result_message.split('\n')
        checks_html = ""
        status = "PASS"
        failed_checks = []
        
        for line in lines:
            if line.strip():
                if "Failed" in line or "Corrupted image detected" in line or "Failed to load image" in line:
                    status = "FAIL"
                    failed_checks.append(line.strip())
                elif "Passed" in line:
                    checks_html += f"<div style='color: green; margin: 5px 0;'><i class='fas fa-check'></i> {line.strip()}</div>"
                elif "Bypassed" in line:
                    checks_html += f"<div style='color: orange; margin: 5px 0;'><i class='fas fa-ban'></i> {line.strip()}</div>"
                else:
                    checks_html += f"<div style='margin: 5px 0;'>{line.strip()}</div>"

        # Add configuration summary
        config_summary = f"""
        <div style='background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #007bff;'>
            <h5 style='margin: 0 0 10px 0; color: #007bff;'><i class='fas fa-cog'></i> Configuration Used:</h5>
            <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.9em;'>
                <div><strong>Dimensions:</strong> {config.min_height}-{config.max_height} × {config.min_width}-{config.max_width} px</div>
                <div><strong>File Size:</strong> {config.min_size}-{config.max_size} KB</div>
                <div><strong>Background Threshold:</strong> {config.bgcolor_threshold} (Higher = stricter)</div>
                <div><strong>Background Uniformity:</strong> {config.bg_uniformity_threshold} (Lower = stricter)</div>
                <div><strong>Blurness Threshold:</strong> {config.blurness_threshold} (Higher = stricter)</div>
                <div><strong>Pixelation Threshold:</strong> {config.pixelated_threshold} (Lower = stricter)</div>
                <div><strong>Greyness Threshold:</strong> {config.greyness_threshold} (Lower = stricter)</div>
                <div><strong>Symmetry Threshold:</strong> {config.symmetry_threshold} (Higher = stricter)</div>
            </div>
        </div>
        """

        if status == "PASS":
            result_html = (
                f"<div style='text-align: center; margin: 20px 0;'>"
                f"<span style='background: #d4edda; color: #155724; padding: 10px 20px; border-radius: 20px; font-weight: bold;'>"
                f"<i class='fas fa-check-circle'></i> VALIDATION PASSED</span></div>"
                f"{config_summary}"
                f"<div style='background: #d1ecf1; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #17a2b8;'>"
                f"<h5 style='margin: 0 0 10px 0; color: #17a2b8;'><i class='fas fa-list-check'></i> Check Results:</h5>"
                f"{checks_html}</div>"
            )
        else:
            result_html = (
                f"<div style='text-align: center; margin: 20px 0;'>"
                f"<span style='background: #f8d7da; color: #721c24; padding: 10px 20px; border-radius: 20px; font-weight: bold;'>"
                f"<i class='fas fa-times-circle'></i> VALIDATION FAILED</span></div>"
                f"{config_summary}"
                f"<div style='background: #f8d7da; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #dc3545;'>"
                f"<h5 style='margin: 0 0 10px 0; color: #dc3545;'><i class='fas fa-exclamation-triangle'></i> Failed Checks:</h5>"
                f"<div style='color: #721c24;'>{'<br>'.join(failed_checks)}</div></div>"
                f"<div style='background: #d1ecf1; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #17a2b8;'>"
                f"<h5 style='margin: 0 0 10px 0; color: #17a2b8;'><i class='fas fa-list-check'></i> All Check Results:</h5>"
                f"{checks_html}</div>"
            )

        return JsonResponse({"result_html": result_html})

    except Exception as e:
        import traceback
        error_html = f"""
        <div style='text-align: center; margin: 20px 0;'>
            <span style='background: #f8d7da; color: #721c24; padding: 10px 20px; border-radius: 20px; font-weight: bold;'>
                <i class='fas fa-exclamation-triangle'></i> ERROR</span>
        </div>
        <div style='background: #f8d7da; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #dc3545;'>
            <h5 style='margin: 0 0 10px 0; color: #dc3545;'><i class='fas fa-bug'></i> Error Details:</h5>
            <div style='color: #721c24; font-family: monospace;'>{str(e)}</div>
            <details style='margin-top: 10px;'>
                <summary style='cursor: pointer; color: #721c24;'>Stack Trace</summary>
                <pre style='background: #f8f9fa; padding: 10px; border-radius: 4px; margin-top: 5px; font-size: 0.8em;'>{traceback.format_exc()}</pre>
            </details>
        </div>
        """
        return JsonResponse({"result_html": error_html})
