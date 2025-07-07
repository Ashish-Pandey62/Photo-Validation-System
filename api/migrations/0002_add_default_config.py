# Migration to add default config

from django.db import migrations


def create_default_config(apps, schema_editor):
    Config = apps.get_model('api', 'Config')
    
    # Check if any config exists
    if not Config.objects.exists():
        Config.objects.create(
            min_height=100,
            max_height=2000,
            min_width=100,
            max_width=2000,
            min_size=10,
            max_size=5000,
            is_jpg=True,
            is_png=True,
            is_jpeg=True,
            bgcolor_threshold=50,
            blurness_threshold=35,
            pixelated_threshold=50,
            greyness_threshold=0,
            symmetry_threshold=20,
            bypass_height_check=False,
            bypass_width_check=False,
            bypass_size_check=False,
            bypass_format_check=False,
            bypass_background_check=False,
            bypass_blurness_check=False,
            bypass_greyness_check=False,
            bypass_symmetry_check=False,
            bypass_head_check=False,
            bypass_eye_check=False,
            bypass_corrupted_check=False,
        )


def reverse_default_config(apps, schema_editor):
    Config = apps.get_model('api', 'Config')
    Config.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_config, reverse_default_config),
    ]
