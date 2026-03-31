@echo off

REM Create the virtual environment
C:\Users\trippb\AppData\Local\Programs\Python\Python312\python.exe -m venv venv

REM Activate the virtual environment
call venv\Scripts\activate

REM Upgrade pip
python -m pip install --upgrade pip

pip install wheel setuptools

REM Install the required packages
pip install requests beautifulsoup4 shapely
pip freeze > requirements.txt

echo "Virtual environment setup is complete."

REM call with: create-env.bat