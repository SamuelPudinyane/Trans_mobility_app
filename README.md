# Trans Mobility App

A Django-based logistics and scheduling platform for managing locomotives, wagons, drivers, and assignments.

## Features
- Locomotive and wagon management
- Driver assignments and scheduling
- Maintenance scheduling
- REST API for integration
- Admin dashboard with analytics

## Prerequisites
- Python 3.8+
- pip (Python package manager)
- (Recommended) Virtual environment tool: `venv` or `virtualenv`
- SQLite (default, no setup needed) or your preferred database

## Setup Instructions

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd Trans_mobility_app
```

### 2. Create and Activate a Virtual Environment
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Migration Commands
Run the following commands to set up the database schema:
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create a Superuser (Admin)
```bash
python manage.py createsuperuser
```

### 6. Run the Development Server
```bash
python manage.py runserver
```

The app will be available at http://127.0.0.1:8000/

## Database Connection Strings

By default, the app uses SQLite (`db.sqlite3`). To use another database (e.g., PostgreSQL, MySQL), update the `DATABASES` setting in `mobility/settings.py`:

```
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',  # or 'django.db.backends.mysql', etc.
        'NAME': 'your_db_name',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'localhost',
        'PORT': '5432',  # Default PostgreSQL port
    }
}
```

After updating, re-run the migration commands:
```bash
python manage.py migrate
```

## Additional Management Commands
- To update driver status after leave/emergency:
  ```bash
  python manage.py update_driver_status
  ```

## Notes
- Static and media files are served automatically in development.
- For production, configure static/media file serving and use a production-ready database.

## License
MIT License
