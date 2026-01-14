import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DJANGO_PROJECT = ROOT / "my_new_project"

if DJANGO_PROJECT.exists():
    sys.path.insert(0, str(DJANGO_PROJECT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "my_new_project.settings")
