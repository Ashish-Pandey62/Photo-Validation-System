from django.urls import path
from django.http import HttpResponseRedirect
from django.urls import re_path


from . import views

def redirect_root(request):
    return HttpResponseRedirect('/photoValidator/')


urlpatterns = [
    path('photoValidator/', views.process_image, name='photoValidator'),
    path('displayCsv/',views.display_csv, name ='displayCsv'),
    #path('upload/', views.process_image, name='upload'),
    #path('dialogueBox/', views.dialogueBox, name='dialogueBox'),
    path('saveConfig/', views.save_config, name='save_config'),
    path('', redirect_root),
    path('image_gallery/', views.image_gallery, name='image_gallery'),
    path('process_selected_images/', views.process_selected_images, name='process_selected_images'),
    path('process_rejected_images/', views.process_rejected_images, name='process_rejected_images'),
    path('download_csv/', views.download_and_delete_csv, name='download_csv'),
    path('delete_all/', views.delete_all, name='delete_all'),
    # path('image_gallery/<str:pathQuery>/', views.image_gallery, name='image_gallery'),
    # path('process_selected_images/<str:pathQueryTwo>/', views.process_selected_images, name='process_selected_images'),
    # re_path(r'^image_gallery/$', views.image_gallery, name='image_gallery'),
    # path('image_gallery/<path:folder_path>/',views.image_gallery, name='image_gallery'),
]


