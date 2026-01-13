# ✅ Render Deployment Checklist

## Pre-Deployment Checklist

- [x] `requirements.txt` exists with all dependencies
- [x] `Procfile` configured correctly
- [x] `runtime.txt` specifies Python version
- [x] `build.sh` script created
- [x] WhiteNoise configured for static files
- [x] Database URL configuration ready
- [x] Environment variables documented

## Files Ready for Deployment

✅ **Procfile**: `web: gunicorn my_new_project.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120`

✅ **Build Command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput`

✅ **Start Command**: `gunicorn my_new_project.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120`

## Environment Variables to Set in Render

### Required:
- [ ] `DEBUG=False`
- [ ] `SECRET_KEY=<generated-key>` (Example: `d$!e%(z(0n#xr3z^#qj3l^&t$n#9f2dd__wwr)a(qvipdb*1=d`)
- [ ] `ALLOWED_HOSTS=your-app-name.onrender.com`

### Database (Choose One):
- [ ] `DATABASE_URL` (from Supabase or Render PostgreSQL)

### API Keys:
- [ ] `SUPABASE_URL`
- [ ] `SUPABASE_KEY`
- [ ] `OPENROUTER_API_KEYv3`
- [ ] `GOOGLE_MAPS_API_KEY` (if needed)

### Optional:
- [ ] `CORS_ALLOW_ALL_ORIGINS=False`
- [ ] `CORS_ALLOWED_ORIGINS=<your-domains>`

## Deployment Steps

1. [ ] Push code to GitHub
2. [ ] Create Render account
3. [ ] Create new Web Service
4. [ ] Connect GitHub repository
5. [ ] Set Root Directory: `my_new_project`
6. [ ] Configure Build & Start commands
7. [ ] Add environment variables
8. [ ] Deploy!
9. [ ] Run migrations (via Shell or build script)
10. [ ] Test API endpoints
11. [ ] Update Flutter app with new API URL

## Quick Commands

**Generate Secret Key:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**Test Locally Before Deploying:**
```bash
cd my_new_project
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
gunicorn my_new_project.wsgi:application --bind 0.0.0.0:8000
```

## Post-Deployment

- [ ] Verify API is accessible
- [ ] Check logs for errors
- [ ] Test itinerary generation endpoint
- [ ] Update Flutter app base URL
- [ ] Monitor performance

## Troubleshooting

**If build fails:**
- Check `requirements.txt` for missing packages
- Verify Python version matches `runtime.txt`

**If app crashes:**
- Check Render logs
- Verify all environment variables are set
- Ensure `ALLOWED_HOSTS` includes Render URL

**If database connection fails:**
- Verify `DATABASE_URL` format
- Check database is accessible
- For Supabase: Check connection pooling settings

