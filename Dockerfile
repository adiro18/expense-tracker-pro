# ---------- Stage 1: build dependencies ----------
FROM python:3.11-slim AS builder
WORKDIR /build
# PyMySQL is pure Python, so no build-essential / libmysqlclient-dev is needed here
COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --timeout=180 --retries=10 -r requirements.txt \
    # pip/setuptools are only needed to install - drop them from the runtime venv
    && pip uninstall -y pip setuptools

# ---------- Stage 2: runtime image ----------
FROM python:3.11-slim
ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 FLASK_APP=wsgi.py
# default-mysql-client from the report was removed: the app never uses it and it added
# ~140 MB. For DB debugging use: kubectl run mysql-client --rm -it --image=mysql:8.0 -- mysql -h <host> -u <user> -p
RUN useradd --create-home --shell /bin/bash appuser
COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY --chown=appuser:appuser . .
USER appuser
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60", "wsgi:app"]
