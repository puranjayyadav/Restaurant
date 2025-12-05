# Cron Job Setup for Pre-Created Itinerary Generation

## Overview
This document explains how to set up automated regeneration of pre-created itineraries.

## Command
```bash
python manage.py generate_pre_created_itineraries --limit 50 --min-restaurants 8 --max-restaurants 10
```

## Setup Options

### Option 1: System Cron (Linux/macOS)

Add to crontab (`crontab -e`):
```bash
# Regenerate itineraries every Sunday at 2 AM
0 2 * * 0 cd /path/to/my_new_project && /path/to/python manage.py generate_pre_created_itineraries --limit 50

# Or regenerate daily at 3 AM
0 3 * * * cd /path/to/my_new_project && /path/to/python manage.py generate_pre_created_itineraries --limit 50
```

### Option 2: Django Management Command (Manual)

Run manually when needed:
```bash
python manage.py generate_pre_created_itineraries
```

### Option 3: Railway Scheduled Tasks

If using Railway, you can set up a scheduled task:
1. Go to Railway dashboard
2. Add a new service or use existing Django service
3. Configure a cron job or scheduled task
4. Set command: `python manage.py generate_pre_created_itineraries --limit 50`

### Option 4: Celery Beat (Recommended for Production)

For production environments, use Celery Beat:

1. Install Celery:
```bash
pip install celery celery-beat
```

2. Create `my_new_project/celery.py`:
```python
from celery import Celery
from celery.schedules import crontab

app = Celery('my_new_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'generate-itineraries-weekly': {
        'task': 'res_backend.tasks.generate_pre_created_itineraries_task',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),  # Sunday 2 AM
    },
}
```

3. Create `res_backend/tasks.py`:
```python
from celery import shared_task
from django.core.management import call_command

@shared_task
def generate_pre_created_itineraries_task():
    call_command('generate_pre_created_itineraries', limit=50)
```

## Recommended Schedule

- **Weekly**: Regenerate all itineraries every Sunday at 2 AM
- **Monthly**: Full regeneration with all category combinations
- **On-demand**: When new restaurants are added to database

## Parameters

- `--limit`: Maximum number of itineraries to generate (default: 50)
- `--min-restaurants`: Minimum restaurants per itinerary (default: 8)
- `--max-restaurants`: Maximum restaurants per itinerary (default: 10)

