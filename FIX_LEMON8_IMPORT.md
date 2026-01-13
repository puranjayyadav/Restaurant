# Fix for lemon8_api ImportError on Render

## Problem
Render deployment fails with:
```
ImportError: cannot import name 'lemon8_api' from 'res_backend'
```

## Solution
The file `my_new_project/res_backend/urls.py` needs to have an optional import for `lemon8_api`.

## Required Change
In `my_new_project/res_backend/urls.py`, replace line 16:

**OLD:**
```python
from . import lemon8_api
```

**NEW:**
```python
try:
    from . import lemon8_api
except ImportError:
    lemon8_api = None
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("lemon8_api module not found - Lemon8 endpoints will be disabled")
```

And update the URL patterns (around line 66-71) to:

```python
# Lemon8 endpoints (only if module is available)
*([path('lemon8/sql-extract/', lemon8_api.sql_extract_view, name='lemon8-sql-extract'),
   path('lemon8/semantic-search/', lemon8_api.semantic_search_view, name='lemon8-semantic-search'),
   path('generate-itinerary/', lemon8_api.unified_generate_itinerary_view, name='generate-itinerary')] if lemon8_api else []),
```

## How to Apply
1. The fix is already applied locally in `my_new_project/res_backend/urls.py`
2. Ensure this file is committed to the git repository that Render is using
3. If `my_new_project` is a separate repository, commit and push from that directory
4. Render should auto-deploy after the push

