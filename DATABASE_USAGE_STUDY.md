# Photo Validation System - Database Usage Study

## Executive Summary

The Photo Validation System uses **SQLite3** as its database, configured in Django. The database serves **two primary purposes**: storing validation configuration settings and tracking uploaded photo batches. The database is relatively lightweight and is used conservatively throughout the application, primarily for runtime configuration management rather than extensive data persistence.

---

## Database Configuration

### Database Type
- **Engine**: SQLite3 (`django.db.backends.sqlite3`)
- **Location**: `db.sqlite3` (root directory of the project)
- **Configuration File**: `onlinePhotoValidator/settings.py`

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(os.path.join(BASE_DIR, "db.sqlite3"))
    }
}
```

**Note**: The settings file shows commented-out MySQL configuration, indicating the project was originally designed for MySQL but currently uses SQLite3 for simplicity.

---

## Database Models

### 1. **Config Model** (Primary Model)
**File**: `api/models.py`

**Purpose**: Stores validation configuration parameters that control the entire photo validation process.

**Fields**:

#### Dimension Constraints (Float)
- `min_height`, `max_height`: Image height bounds
- `min_width`, `max_width`: Image width bounds
- `min_size`, `max_size`: File size bounds (in KB)

#### Format Support (Boolean)
- `is_jpg`: Enable JPG format
- `is_png`: Enable PNG format
- `is_jpeg`: Enable JPEG format (default: True)

#### Quality Thresholds (Float - with defaults)
- `bgcolor_threshold`: Background color validation (default: 40)
- `bg_uniformity_threshold`: Background uniformity check (default: 25)
- `blurness_threshold`: Blur detection strictness (default: 30)
- `pixelated_threshold`: Pixelation detection (default: 100)
- `greyness_threshold`: Grayscale detection (default: 5)
- `symmetry_threshold`: Facial symmetry check (default: 35)

#### Bypass Flags (Boolean - all default to False)
- `bypass_height_check`
- `bypass_width_check`
- `bypass_size_check`
- `bypass_format_check`
- `bypass_background_check`
- `bypass_blurness_check`
- `bypass_greyness_check`
- `bypass_symmetry_check`
- `bypass_head_check`
- `bypass_eye_check`
- `bypass_corrupted_check`

**Design Pattern**: Only ONE Config record is ever stored. The application uses `.first()` to retrieve it.

---

### 2. **PhotoFolder Model** (Secondary Model)
**File**: `api/models.py`

**Purpose**: Tracks uploaded ZIP files containing photo batches for validation.

**Fields**:
- `folder`: FileField (upload_to='photo_folder/') - Stores the uploaded ZIP file
- `uploaded_at`: DateTimeField (auto_now_add=True) - Timestamp of upload
- `__str__()`: Returns folder name for admin display

**Usage**: Minimal tracking of uploads, primarily for form support and file field management.

---

## Database Migrations

**File**: `api/migrations/`

### Migration History

1. **0001_initial.py** (Created: 2024-08-03)
   - Creates both Config and PhotoFolder models
   - Initial threshold values: bgcolor=50, blurness=35, pixelated=50, greyness=0, symmetry=20

2. **0002_add_default_config.py** (Custom)
   - Adds a migration that creates a default Config record if none exists
   - Sets up default validation parameters
   - Includes reverse migration to clean up

3. **0003_alter_config_bgcolor_threshold_and_more.py** (Created: 2025-08-04)
   - Updated default thresholds to be more lenient:
     - bgcolor: 50 → 40
     - blurness: 35 → 30
     - pixelated: 50 → 100
     - greyness: 0 → 5
     - symmetry: 20 → 35

4. **0004_config_bg_uniformity_threshold.py** (Created: 2025-08-19)
   - Added new field: `bg_uniformity_threshold` (default: 25)
   - Enables background uniformity validation

---

## Database Usage Patterns Throughout the Application

### 1. **Views (api/views.py)**

#### startPage() - Home Page View
```python
# Retrieves the current config or creates default
config = Config.objects.first()
if not config:
    config = Config.objects.create(...)
```
**Purpose**: Load current validation parameters for display
**Database Operation**: READ (and potentially CREATE if missing)

#### process_image() - Main Upload Handler
```python
# Get or create config safely
config = Config.objects.first()
if not config:
    config = Config.objects.create(...)

# Save uploaded folder to database
photo_folder = PhotoFolder(folder=folder)
photo_folder.save()
```
**Purpose**: 
- Retrieve validation config for the batch
- Track uploaded ZIP file in database
**Database Operations**: READ Config, CREATE PhotoFolder record

#### save_config() - Configuration Update Endpoint
```python
config = Config.objects.first()
if not config:
    config = Config()

# Update all threshold and bypass fields
config.min_height = minHeight
config.max_height = maxHeight
# ... (updates 26+ fields)
config.save()
```
**Purpose**: Save user-modified validation parameters
**Database Operations**: READ, UPDATE, WRITE
**Special**: Clears `get_cached_config()` cache after saving

#### test_config_image() - Single Image Test
```python
config = Config.objects.first()
if not config:
    config = Config.objects.create(...)
```
**Purpose**: Load config for single image validation test
**Database Operations**: READ

#### image_gallery(), valid_images_gallery()
- Retrieve validation session data
- Do NOT directly query database (use file system instead)
- Session data stored in request.session (server-side, not database by default in SQLite)

#### Other Views
- `clear_data()`: Retrieves config to display form
- `delete_all()`: Retrieves form
- Database queries are minimal and read-only in these functions

---

### 2. **Photo Validator Modules**

#### photo_validator_optimized.py
```python
config = get_cached_config()  # Uses LRU cache
if not config:
    config = Config.objects.create(...)
```
**Key Feature**: Uses **performance cache** to avoid repeated database queries

#### photo_validator_detailed.py
```python
config = Config.objects.first()
if not config:
    config = Config.objects.create(...)
```

#### photo_validator_parallel.py & photo_validator_threaded.py
```python
config = Config.objects.first()
if not config:
    config = Config.objects.create(...)
```
**Purpose**: Retrieve configuration for batch validation
**All validators follow the same pattern**: READ config at initialization

---

### 3. **Admin Interface (api/admin.py)**

```python
from django.contrib import admin
from .models import *

admin.site.register(Config)
admin.site.register(PhotoFolder)
```

**Purpose**: Allow Django admin users to manually view/edit:
- Config parameters (available at `/admin/api/config/`)
- PhotoFolder upload history (available at `/admin/api/photofolder/`)

---

### 4. **Forms (api/forms.py)**

```python
class PhotoFolderUploadForm(forms.ModelForm):
    class Meta:
        model = PhotoFolder
        fields = ['folder']
```

**Purpose**: ModelForm for uploading ZIP files
**Database Operation**: Implicit save when form.save() is called

---

### 5. **Configuration Check Utility (check_config.py)**

```python
config = Config.objects.first()
if config:
    # Displays all configuration parameters
    print(f"Height: {config.min_height} - {config.max_height}")
    # ... prints all 26+ fields
```

**Purpose**: Diagnostic tool to inspect current database configuration
**Database Operation**: READ only

---

### 6. **Performance Caching (performance_utils.py)**

```python
@lru_cache(maxsize=128)
def get_cached_config():
    """Cache config object to avoid repeated database queries."""
    from .models import Config
    return Config.objects.first()
```

**Purpose**: **Optimize performance** by caching Config in memory
**Cache Size**: 128 items max
**Invalidation**: Manually cleared in `save_config()` view after updates

---

## Database Query Patterns

### Most Common Query Patterns

| Query Pattern | Frequency | Purpose |
|---------------|-----------|---------|
| `Config.objects.first()` | Very High | Retrieve the single Config record |
| `Config.objects.create(...)` | Low | Create default config if missing |
| `config.save()` | Medium | Update config parameters |
| `PhotoFolder(folder=...).save()` | Low | Track uploaded files |

### Query Optimization Strategies

1. **LRU Cache**: `get_cached_config()` prevents repeated queries
2. **Single Record Design**: Only one Config exists, no filtering needed
3. **Manual Cache Invalidation**: Clears cache when config is updated
4. **Safe Retrieval**: Always check if config exists before use

---

## Session Data (Not Database)

**Important**: The application stores session data separately:

```python
request.session["path"] = path  # Image directory path
request.session["total_images_count"] = len(image_files)  # Stats
```

By default, Django SQLite sessions are stored in the database, but this project treats session data as transient and doesn't query it directly in the code.

---

## Data Flow Diagram

```
User Upload (ZIP File)
    ↓
process_image() View
    ├── Query: Config.objects.first()
    ├── Save: PhotoFolder record
    ├── Extract: ZIP to media/photos/
    └── Session: Store path & count
    ↓
Photo Validator (photo_validator_dir.py)
    ├── Query: get_cached_config() [LRU Cache]
    ├── Use: All 26+ config parameters
    └── Generate: valid/ and invalid/ folders
    ↓
Results View (image_gallery.html)
    ├── Session: Retrieve path & count
    ├── File System: Read invalid images
    └── CSV File: Read validation reasons
    ↓
User Actions
    ├── save_config(): Update Config, clear cache
    ├── test_config_image(): Read Config
    └── clear_data(): Delete files, not database
```

---

## Key Observations

### 1. **Lightweight Database Usage**
- Only 2 models with minimal data
- Primary purpose: Configuration storage
- Secondary purpose: Upload tracking
- Not used for storing validation results (stored in CSV files)

### 2. **Configuration-Centric Design**
- 26 fields in Config table
- Every validation check references these parameters
- Single record design (no multi-user profiles)

### 3. **Performance Optimizations**
- LRU cache implemented
- Minimal database queries during batch processing
- Config loaded once at initialization

### 4. **File System Over Database**
- Validation results stored in `result.csv` (file)
- Valid/invalid images stored in file system
- Only metadata stored in database

### 5. **Admin-Driven Configuration**
- Config primarily updated via web form or admin panel
- No direct user-facing config API
- Changes require page refresh or manual cache clear

### 6. **Migration Strategy**
- Gradual threshold adjustments through migrations
- Default config creation handled in migration
- Schema evolution tracked through 4 migrations

---

## Database Integrity & Constraints

### Implicit Constraints
- Only one Config record should exist (enforced by application logic, not schema)
- Config fields have default values
- PhotoFolder records have auto timestamps

### No Explicit Constraints
- No foreign keys
- No unique constraints
- No indexes defined in models

### Risk Areas
- Multiple Config records could be created (not prevented by schema)
- No validation on threshold values (could be negative)
- PhotoFolder records don't prevent duplicate uploads

---

## Potential Issues & Future Considerations

### Current Issues
1. **Config duplication**: No schema-level prevention of multiple Config records
2. **Cache invalidation**: Manual `.cache_clear()` required; could miss updates
3. **Session persistence**: Default SQLite sessions create database bloat
4. **No audit trail**: Config changes not logged

### Future Enhancements
1. Add unique constraint on Config table
2. Implement automatic cache invalidation signals
3. Add Config history/audit trail
4. Separate session storage (Redis/file-based)
5. Add validation constraints on threshold fields

---

## Conclusion

The database in this Photo Validation System is **deliberately minimal and configuration-focused**. It serves as a central repository for validation parameters that would otherwise need to be hardcoded or passed through request parameters. The actual validation work and result storage happens in the file system, making the database a supporting component rather than the primary data store. This design prioritizes simplicity, performance, and easy configuration management over comprehensive data persistence.

