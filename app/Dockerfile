FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_ENV=development

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/dev.txt .
RUN pip install --no-cache-dir -r dev.txt

# Copy project code
COPY . .

# Create media and logs directories
RUN mkdir -p media logs staticfiles

EXPOSE 8000

# For development - use runserver
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]