from django import forms
from .models import PhotoFolder

class PhotoFolderUploadForm(forms.ModelForm):
    class Meta:
        model = PhotoFolder
        fields = ['folder']