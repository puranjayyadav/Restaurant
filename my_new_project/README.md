# Food Explorer - Django Backend

## 🚀 Quick Start

### Local Development

```powershell
# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start server
python manage.py runserver
```

Backend runs at: `http://127.0.0.1:8000/`

---

## 📡 API Endpoints

- `POST /api/create_session/` - Create a new session
- `POST /api/generate-day-itinerary/` - Generate personalized itinerary
- `GET /api/trips/` - Get user trips
- `POST /api/verify-token/` - Verify Firebase token

---

## 🌐 Deployment

See **`DEPLOYMENT_INSTRUCTIONS.md`** for complete deployment guide.

### Quick Deploy Options:

1. **Railway (Recommended):**
   - Push to GitHub
   - Connect to Railway
   - Deploy automatically

2. **Render:**
   - Push to GitHub
   - Connect to Render
   - Free tier available

3. **Google Cloud Run:**
   - Use provided Dockerfile
   - Deploy with `gcloud run deploy`

---

## 🔧 Configuration

### Environment Variables

Required for production:
```
DEBUG=False
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=your-domain.com
DATABASE_URL=postgresql://...
```

### Settings Files

- `settings.py` - Development settings (DEBUG=True, SQLite)
- `settings_prod.py` - Production settings (DEBUG=False, PostgreSQL)

---

## 📦 Dependencies

Main packages:
- Django 5.2.8
- Django REST Framework
- Firebase Admin SDK
- PostgreSQL adapter
- Gunicorn (production server)

See `requirements.txt` for full list.

---

## 🔒 Security

- Never commit `.env` files
- Never commit `serviceAccountKey.json`
- Use strong `SECRET_KEY` in production
- Set `DEBUG=False` in production
- Use HTTPS in production

---

## 📊 Database

- **Development:** SQLite (`db.sqlite3`)
- **Production:** PostgreSQL (via `DATABASE_URL`)

Auto-migration on deployment via `Procfile`.

---

## 🆘 Support

- Deployment guide: `DEPLOYMENT_INSTRUCTIONS.md`
- Hosting options: `../BACKEND_HOSTING_GUIDE.md`
- Check deployment readiness: Run `deploy_check.bat`

---

## 📝 License

Private project - Not for redistribution

