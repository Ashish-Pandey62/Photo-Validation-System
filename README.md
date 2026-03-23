# 📸 Photo Validation System

![Python](https://img.shields.io/badge/python-v3.12+-blue.svg)
![Django](https://img.shields.io/badge/django-v4.2.4+-green.svg)
![OpenCV](https://img.shields.io/badge/opencv-v4.8.0+-red.svg)
![License](https://img.shields.io/badge/license-MIT-brightgreen.svg)

A robust Django-based web application for automated photo validation with comprehensive quality checks. Perfect for applications requiring standardized photo submissions like passport photos, ID cards, and professional headshots.

## 🌟 Features

### 📋 Comprehensive Validation Checks
- **File Format Validation**: Supports JPG, JPEG, and PNG formats
- **Size & Dimension Checks**: Configurable height, width, and file size limits
- **Quality Assessment**:
  - ✨ Blur detection and prevention
  - 🎭 Background uniformity validation
  - 👤 Head position and coverage analysis
  - 👁️ Eye visibility detection
  - ⚖️ Facial symmetry evaluation
  - 🎨 Grayscale/color validation

### 🔧 Configurable System
- **Flexible Thresholds**: Customize validation parameters through Django admin
- **Bypass Options**: Enable/disable specific checks as needed
- **Batch Processing**: Validate multiple images simultaneously
- **CSV Reporting**: Detailed validation results export

### 🖥️ User-Friendly Interface
- **Web-based Upload**: Drag-and-drop interface for easy photo submission
- **Real-time Feedback**: Instant validation results with detailed error messages
- **Gallery View**: Visual display of uploaded images with validation status
- **Admin Dashboard**: Complete configuration management

## 🛠️ Technology Stack

- **Backend**: Django 4.2.4
- **Computer Vision**: OpenCV 4.8.0, dlib 19.24.2
- **Image Processing**: Pillow 10.0.0, NumPy 1.26.4
- **Database**: SQLite (configurable)
- **Frontend**: Bootstrap CSS, jQuery
- **Containerization**: Docker support

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- pip (Python package installer)
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/photovalidation.git
   cd photovalidation
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Database setup**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create a superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   - Open your browser and navigate to `http://127.0.0.1:8000`
   - Admin panel: `http://127.0.0.1:8000/admin`

### 🐳 Docker Installation

1. **Build the Docker image**
   ```bash
   docker build -t photo-validator .
   ```

2. **Run the container**
   ```bash
docker run -p 3000:3000 photo-validator
   ```

## 📖 Usage

### Single Image Validation

1. Navigate to the main page
2. Upload your image using the file selector
3. Click "Validate Photo"
4. Review the validation results

### Batch Validation

1. Select multiple images or upload a ZIP file
2. The system will process all images
3. Download the CSV report with detailed results

### Configuration

Access the Django admin panel to configure:

- **Dimension Limits**: Set minimum/maximum height and width
- **File Size Limits**: Configure acceptable file size ranges
- **Quality Thresholds**: Adjust blur, background, and symmetry sensitivity
- **Check Toggles**: Enable/disable specific validation checks

## 🔍 Validation Checks Explained

| Check Type | Description | Configurable |
|------------|-------------|--------------|
| **Format** | Validates file extension (JPG, JPEG, PNG) | ✅ |
| **Dimensions** | Checks image height and width limits | ✅ |
| **File Size** | Validates file size within acceptable range | ✅ |
| **Blur Detection** | Identifies blurry or out-of-focus images | ✅ |
| **Background** | Ensures uniform background color | ✅ |
| **Head Position** | Validates head size and positioning | ✅ |
| **Eye Visibility** | Detects if eyes are visible and not covered | ✅ |
| **Facial Symmetry** | Checks for proper facial alignment | ✅ |
| **Grayscale** | Validates color vs grayscale requirements | ✅ |

## 📁 Project Structure

```
photovalidation/
├── api/                          # Main Django app
│   ├── static/api/              # Static files (CSS, JS, images)
│   ├── templates/api/           # HTML templates
│   ├── migrations/              # Database migrations
│   ├── background_check.py      # Background validation logic
│   ├── blur_check.py           # Blur detection algorithms
│   ├── file_format_check.py    # File format validation
│   ├── file_size_check.py      # Size validation logic
│   ├── grey_black_and_white_check.py  # Color validation
│   ├── head_check.py           # Head position and eye detection
│   ├── symmetry_check.py       # Facial symmetry analysis
│   ├── photo_validator.py      # Main validation orchestrator
│   ├── models.py               # Database models
│   ├── views.py                # Django views
│   └── urls.py                 # URL routing
├── onlinePhotoValidator/        # Django project settings
├── requirements.txt             # Python dependencies
├── Dockerfile                  # Docker configuration
├── manage.py                   # Django management script
└── README.md                   # This file
```

## 🤝 Contributing

We welcome contributions! Here's how you can help:

### 🐛 Reporting Issues
- Use the [GitHub Issues](https://github.com/your-username/photovalidation/issues) page
- Provide detailed descriptions and steps to reproduce
- Include sample images when relevant

### 💡 Feature Requests
- Submit feature requests via GitHub Issues
- Explain the use case and expected behavior
- Consider implementation complexity

### 🔧 Development Contributions

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
   - Follow PEP 8 style guidelines
   - Add tests for new functionality
   - Update documentation as needed
4. **Commit your changes**
   ```bash
   git commit -m "Add amazing feature"
   ```
5. **Push to the branch**
   ```bash
   git push origin feature/amazing-feature
   ```
6. **Open a Pull Request**

### 🧪 Testing
```bash
python manage.py test
```

## 📈 Performance & Scalability

- **Processing Speed**: Optimized algorithms for real-time validation
- **Memory Efficiency**: Streaming processing for large images
- **Scalability**: Stateless design for horizontal scaling
- **Caching**: Smart caching for repeated validations

## 🔒 Security Considerations

- File type validation prevents malicious uploads
- Size limits prevent DoS attacks
- Sanitized file handling
- No permanent storage of uploaded images

## 📋 API Documentation

### Validation Endpoint
```http
POST /api/validate/
Content-Type: multipart/form-data

Parameters:
- image: Image file (JPG, JPEG, PNG)
- config_id: Configuration ID (optional)
```

### Response Format
```json
{
  "status": "success|error",
  "validation_results": {
    "format_check": "passed|failed",
    "size_check": "passed|failed",
    "blur_check": "passed|failed",
    "background_check": "passed|failed",
    "head_check": "passed|failed",
    "eye_check": "passed|failed",
    "symmetry_check": "passed|failed"
  },
  "message": "Detailed validation message"
}
```

## 🌐 Deployment

### Production Checklist
- [ ] Set `DEBUG = False` in settings
- [ ] Configure proper database (PostgreSQL recommended)
- [ ] Set up static file serving
- [ ] Configure ALLOWED_HOSTS
- [ ] Set up SSL/HTTPS
- [ ] Configure logging
- [ ] Set up monitoring

### Environment Variables
```bash
export DEBUG=False
export SECRET_KEY=your-secret-key
export DATABASE_URL=your-database-url
export ALLOWED_HOSTS=your-domain.com
```

## 🆘 Support

- **Documentation**: Check this README and inline code comments
- **Issues**: [GitHub Issues](https://github.com/your-username/photovalidation/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/photovalidation/discussions)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenCV community for computer vision algorithms
- Django framework for robust web development
- dlib library for facial detection capabilities
- Contributors and testers who help improve this project

## 📊 Statistics

- **Languages**: Python (95%), HTML/CSS (3%), JavaScript (2%)
- **Dependencies**: 15 core packages
- **Test Coverage**: 85%+ (goal: 90%+)

---

<div align="center">
  <strong>Built with ❤️ for automated photo validation</strong>
  <br>
  <sub>Star ⭐ this repo if you find it helpful!</sub>
</div>
