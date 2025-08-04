from django.db import models

# Create your models here.
class Config(models.Model):
    min_height = models.FloatField()
    max_height = models.FloatField()
    min_width = models.FloatField()
    max_width = models.FloatField()
    min_size = models.FloatField()
    max_size = models.FloatField()
    is_jpg = models.BooleanField()
    is_png = models.BooleanField()
    is_jpeg = models.BooleanField(default=True)
    bgcolor_threshold = models.FloatField(default=40)  # Reduced from 50 to allow slightly darker backgrounds
    blurness_threshold = models.FloatField(default=30)  # Reduced from 35 to be less strict on blur
    pixelated_threshold = models.FloatField(default=100)  # Increased from 50 to be less strict on pixelation
    greyness_threshold = models.FloatField(default=5)  # Increased from 0 to allow slightly desaturated images
    symmetry_threshold = models.FloatField(default=35)  # Increased from 20 to be less strict on symmetry

    bypass_height_check = models.BooleanField(default=False)
    bypass_width_check = models.BooleanField(default=False)
    bypass_size_check = models.BooleanField(default=False)
    bypass_format_check = models.BooleanField(default=False)
    bypass_background_check = models.BooleanField(default=False)
    bypass_blurness_check = models.BooleanField(default=False)
    bypass_greyness_check = models.BooleanField(default=False)
    bypass_symmetry_check = models.BooleanField(default=False)
    bypass_head_check = models.BooleanField(default=False)
    bypass_eye_check = models.BooleanField(default=False)
    bypass_corrupted_check = models.BooleanField(default=False)

class PhotoFolder(models.Model):
    folder = models.FileField(upload_to = 'photo_folder/')
    uploaded_at = models.DateTimeField(auto_now_add= True)

    def __str__(self):
        return self.folder.name