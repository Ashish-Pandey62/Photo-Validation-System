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
    bgcolor_threshold = models.FloatField(default=50)
    blurness_threshold = models.FloatField(default=35)
    pixelated_threshold = models.FloatField(default=50)
    greyness_threshold = models.FloatField(default=0)
    symmetry_threshold = models.FloatField(default=20)

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