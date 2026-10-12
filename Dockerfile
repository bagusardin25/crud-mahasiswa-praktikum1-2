FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependensi dulu supaya layer ini di-cache selama requirements.txt tidak berubah
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY templates/ templates/

# Jangan jalankan aplikasi sebagai root di dalam container
RUN useradd --create-home appuser
USER appuser

EXPOSE 5000

# --preload: init_db() dijalankan sekali di proses master sebelum worker dibuat
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--preload", "--access-logfile", "-", "app:app"]
