#!/usr/bin/env python
"""
Wrapper script to ensure PYTHONPATH is set correctly before running gunicorn
"""
import sys
import os

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Ensure the project directory is in the Python path
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Set environment variable
os.environ['PYTHONPATH'] = script_dir

print(f"Script directory: {script_dir}")
print(f"Python path: {sys.path}")
print(f"Current directory: {os.getcwd()}")
print(f"PYTHONPATH: {os.environ.get('PYTHONPATH')}")

# List contents to verify structure
print(f"Contents of {script_dir}:")
try:
    print(os.listdir(script_dir))
except Exception as e:
    print(f"Error listing directory: {e}")

# Change to project directory
os.chdir(script_dir)

# Now run gunicorn
from gunicorn.app.wsgiapp import run
sys.argv = [
    'gunicorn',
    'my_new_project.wsgi:application',
    '--bind', f'0.0.0.0:{os.environ.get("PORT", "8080")}',
    '--workers', '2',
    '--log-file', '-'
]
run()


