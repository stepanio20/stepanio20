FROM python:3.11-slim

# Fonts for deal-card / branding rendering (DejaVu)
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# .env is NOT copied (gitignored). Provide env vars at runtime:
#   docker run --env-file .env diamondscan
CMD ["python", "bot.py"]
