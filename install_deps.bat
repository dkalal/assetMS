@echo off
echo Installing required dependencies...
call .\venv\Scripts\activate.bat

:: Install core dependencies
pip install djangorestframework
django-import-export

:: Install other common Django packages that might be needed
pip install django-crispy-forms
crispy-bootstrap5
django-widget-tweaks
django-debug-toolbar
django-extensions

:: Required for file uploads and images
pip install Pillow

:: Database adapters
pip install psycopg2-binary

:: For handling environment variables
pip install python-dotenv

echo.
echo All dependencies installed successfully!
pause
