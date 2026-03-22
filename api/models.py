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
    bgcolor_threshold = models.FloatField(default=40)
    bg_uniformity_threshold = models.FloatField(default=35)
    blurness_threshold = models.FloatField(default=100)
    greyness_threshold = models.FloatField(default=15)
    symmetry_threshold = models.FloatField(default=30)

    # Head coverage range (percentage of image area)
    min_head_percent = models.FloatField(default=10)
    max_head_percent = models.FloatField(default=80)

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

    # New check thresholds
    noise_threshold = models.FloatField(default=25)
    dust_spot_threshold = models.IntegerField(default=15)
    text_region_threshold = models.IntegerField(default=8)

    # New check bypass toggles
    bypass_printed_photo_check = models.BooleanField(default=False)
    bypass_dust_noise_check = models.BooleanField(default=False)
    bypass_text_check = models.BooleanField(default=False)

class PhotoFolder(models.Model):
    folder = models.FileField(upload_to = 'photo_folder/')
    uploaded_at = models.DateTimeField(auto_now_add= True)

    def __str__(self):
        return self.folder.name