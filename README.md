<<<<<<< HEAD

A Django-based web application designed to help users track expiry dates of groceries and medicines, reduce food waste, and facilitate donations to NGOs before items expire.

## Overview

Smart Expiry Tracker is a comprehensive solution for managing household essentials with expiration dates. The application combines modern web technologies with computer vision capabilities to provide an intuitive interface for tracking items, receiving timely reminders, and contributing to community welfare through donation features.

## Features

### Core Functionality
- **Item Management**: Add, view, edit, and delete tracked items with categories (Medicine, Grocery, Household, Others)
- **Expiry Tracking**: Automatic calculation of days until expiry with status indicators (Safe, Expiring Soon, Expired)
- **User Authentication**: Secure user accounts with profile management and email preferences

### Advanced Features
- **Barcode Scanning**: Integrated barcode reader using OpenCV and PyZbar for quick product identification
- **OCR Expiry Detection**: Advanced optical character recognition using EasyOCR to scan expiry dates from product labels
- **Email Reminders**: Automated Celery-based email notifications for items expiring within 7 days
- **Donation System**: Specialized feature for donating unexpired medicines to NGOs in Kerala districts
- **Product Database**: Lookup functionality for products by barcode with external database integration

### Technical Highlights
- **Real-time Processing**: GPU-accelerated OCR for fast expiry date extraction
- **Responsive Design**: Bootstrap-based UI optimized for desktop and mobile devices
- **Asynchronous Tasks**: Celery integration with Redis for background email processing
- **Data Validation**: Robust date parsing and validation for various expiry date formats

## Technology Stack

### Backend
- **Django 4.2**: Web framework for rapid development
- **Python 3.x**: Core programming language
- **Celery**: Distributed task queue for background jobs
- **Redis**: In-memory data structure store for Celery broker

### Computer Vision & OCR
- **EasyOCR**: Deep learning-based OCR engine
- **OpenCV**: Computer vision library for image processing
- **PyZbar**: Barcode and QR code detection
- **Pillow**: Image manipulation library

### Frontend
- **Bootstrap 5.3**: Responsive CSS framework
- **HTML5/CSS3**: Modern web standards
- **JavaScript**: Client-side interactivity

### Database
- **PostgreSQL**: Primary database (configured for production)
- **SQLite**: Development database (default Django setup)

## Installation

### Prerequisites
- Python 3.8 or higher
- PostgreSQL (recommended) or SQLite
- Redis server (for Celery tasks)
- Webcam (for barcode/OCR scanning)

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd expirytracker
=======
# Smart Expiry Tracker

A Django-based web application for tracking expiry dates of items using barcode scanning and OCR technology. This project helps users manage their inventory by automatically detecting expiry dates from product packaging.

## 🚧 Project Status

**This project is currently under active development.** While core functionalities are implemented and working, there are ongoing improvements and upgrades planned. Contributions and feedback are welcome!

## ✨ Features Implemented

### Core Functionality
- **Item Management**: Add, view, and track items with expiry dates
- **Category System**: Organize items into categories (Medicine, Grocery, Household, Others)
- **Expiry Monitoring**: Automatic detection of expired and near-expiry items
- **Barcode Integration**: Scan barcodes/QR codes for quick item identification
- **OCR Technology**: Extract expiry dates from product images using advanced OCR

### Technical Features
- **Webcam Integration**: Real-time barcode scanning and OCR via webcam
- **Multiple OCR Engines**: Support for both EasyOCR and Tesseract for better accuracy
- **Responsive UI**: Clean, user-friendly web interface
- **Database Integration**: SQLite database with Django ORM
- **Admin Panel**: Django admin interface for data management

### User Interface
- Home dashboard with expiry overview
- Add items manually or with barcode scanning
- Advanced item addition with OCR expiry detection
- View all items with expiry status
- Enhanced home page with statistics

## 🔄 Features in Development

- **Comprehensive Testing**: Unit tests and integration tests
- **Performance Optimizations**: Improve OCR accuracy and speed
- **Mobile App**: Native mobile application
- **API Endpoints**: REST API for external integrations
- **Notifications**: Email/SMS alerts for expiring items
- **Data Export**: Export inventory data to various formats
- **User Authentication**: Multi-user support with login system

## 🛠️ Technology Stack

- **Backend**: Django 4.2
- **Database**: SQLite (development), PostgreSQL (production ready)
- **OCR Engines**: EasyOCR, Tesseract
- **Barcode Scanning**: PyZbar, OpenCV
- **Image Processing**: Pillow, OpenCV
- **Frontend**: HTML, CSS, JavaScript (Django templates)

## 📋 Prerequisites

- Python 3.8+
- Webcam (for barcode/OCR scanning)
- Internet connection (for OCR model downloads)

## 🚀 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Varun4213-bibi/smart-tracker.git
   cd smart-tracker
>>>>>>> eb6388d9cc57b2e0b054c44dc87947418420c229
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

<<<<<<< HEAD
4. **Database setup**
   ```bash
=======
4. **Run migrations**
   ```bash
   python manage.py makemigrations
>>>>>>> eb6388d9cc57b2e0b054c44dc87947418420c229
   python manage.py migrate
   ```

5. **Create superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

<<<<<<< HEAD
6. **Start Redis server** (in separate terminal)
   ```bash
   redis-server
   ```

7. **Run Celery worker** (in separate terminal)
   ```bash
   celery -A expirytracker worker --loglevel=info
   ```

8. **Run the development server**
=======
6. **Run the development server**
>>>>>>> eb6388d9cc57b2e0b054c44dc87947418420c229
   ```bash
   python manage.py runserver
   ```

<<<<<<< HEAD
9. **Access the application**
   - Open browser to `http://127.0.0.1:8000`
   - Admin panel: `http://127.0.0.1:8000/admin`

## Usage

### Getting Started
1. **Sign Up**: Create a new account or log in
2. **Configure Profile**: Set email preferences for reminders
3. **Add Items**: Use manual entry, barcode scanning, or OCR expiry detection

### Adding Items
- **Manual Entry**: Fill in item details including name, category, and expiry date
- **Barcode Scan**: Use camera to scan product barcode for automatic product lookup
- **OCR Scan**: Capture expiry date from product labels using advanced text recognition

### Managing Inventory
- View all items with expiry status indicators
- Filter and organize items by category and expiry timeline
- Edit or delete items as needed

### Donation Feature
- Mark eligible medicines for donation
- Select location to find nearby NGOs
- Generate pre-filled email templates for donation coordination

### Email Reminders
- Automatic daily checks for expiring items
- Configurable reminder preferences per user
- HTML and plain text email formats

## Project Structure

```
expirytracker/
├── expirytracker/          # Main Django project
│   ├── settings.py        # Django settings
│   ├── urls.py           # Main URL configuration
│   ├── celery.py         # Celery configuration
│   └── wsgi.py           # WSGI configuration
├── tracker/               # Main Django app
│   ├── models.py         # Database models
│   ├── views.py          # View functions
│   ├── forms.py          # Django forms
│   ├── urls.py           # App URL patterns
│   ├── tasks.py          # Celery tasks
=======
7. **Access the application**
   - Open http://127.0.0.1:8000 in your browser
   - Admin panel: http://127.0.0.1:8000/admin

## 📖 Usage

### Adding Items
1. **Manual Entry**: Use the "Add Item" form to manually enter item details
2. **Barcode Scanning**: Use "Add with Barcode" to scan product barcodes
3. **Advanced OCR**: Use "Advanced Add" with webcam to automatically extract expiry dates

### Viewing Items
- Visit the "View Items" page to see all tracked items
- Items are color-coded based on expiry status:
  - 🟢 Safe (more than 7 days)
  - 🟡 Near expiry (7 days or less)
  - 🔴 Expired

### OCR Features
- Point your webcam at product expiry dates
- The system will automatically detect and extract date information
- Supports various date formats and languages

## 🤝 Contributing

This project is in active development. To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Django framework for the robust backend
- EasyOCR and Tesseract for OCR capabilities
- PyZbar for barcode scanning
- OpenCV and Pillow for image processing



---

**Note**: This application is for personal inventory management. Always verify expiry dates manually for critical items like medications.
>>>>>>> eb6388d9cc57b2e0b054c44dc87947418420c229
