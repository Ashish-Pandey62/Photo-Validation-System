python3 direct_validation_test.py
#!/usr/bin/env python3
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onlinePhotoValidator.settings')
django.setup()

from api.models import Config

def check_config():
    try:
        config = Config.objects.first()
        if config:
            print("=== Current Configuration ===")
            print(f"Height: {config.min_height} - {config.max_height}")
            print(f"Width: {config.min_width} - {config.max_width}")
            print(f"Size: {config.min_size} - {config.max_size}")
            print(f"Formats: JPG={config.is_jpg}, PNG={config.is_png}, JPEG={config.is_jpeg}")
            print("\n=== Bypass Settings ===")
            print(f"Format check: {config.bypass_format_check}")
            print(f"Size check: {config.bypass_size_check}")
            print(f"Height check: {config.bypass_height_check}")
            print(f"Width check: {config.bypass_width_check}")
            print(f"Background check: {config.bypass_background_check}")
            print(f"Blur check: {config.bypass_blurness_check}")
            print(f"Grey check: {config.bypass_greyness_check}")
            print(f"Symmetry check: {config.bypass_symmetry_check}")
            print(f"Head check: {config.bypass_head_check}")
            print(f"Eye check: {config.bypass_eye_check}")
            print(f"Corrupted check: {config.bypass_corrupted_check}")
            
            # Check if all validation checks are bypassed
            all_bypassed = all([
                config.bypass_format_check,
                config.bypass_size_check,
                config.bypass_height_check,
                config.bypass_width_check,
                config.bypass_background_check,
                config.bypass_blurness_check,
                config.bypass_greyness_check,
                config.bypass_symmetry_check,
                config.bypass_head_check,
                config.bypass_eye_check,
                config.bypass_corrupted_check
            ])
            
            if all_bypassed:
                print("\n🚨 WARNING: ALL VALIDATION CHECKS ARE BYPASSED!")
                print("This is why all images are passing validation.")
            else:
                print(f"\n✅ Some validation checks are active.")
                
        else:
            print("No configuration found in database.")
    except Exception as e:
        print(f"Error checking config: {e}")

if __name__ == "__main__":
    check_config()