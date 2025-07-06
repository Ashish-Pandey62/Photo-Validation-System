from django.contrib import admin

# Register your models here.
from .models import *

admin.site.register(Config)
admin.site.register(PhotoFolder)
