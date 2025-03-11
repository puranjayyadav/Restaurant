# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project code
COPY . /app/

# Collect static files (if needed)
RUN python manage.py collectstatic --noinput

# Run migrations (optional, or handle externally)
RUN python manage.py migrate

# Expose port (default for Django/Gunicorn)
EXPOSE 8000

# Start Gunicorn server
CMD ["gunicorn", "my_new_app.wsgi:application", "--bind", "0.0.0.0:${PORT:-8000}"]
