# VardKey is a pure Python standard-library service, so the image needs the
# interpreter and the application source and nothing else.
FROM python:3.13-slim

WORKDIR /app

# The whole application. static/ MUST be copied: app.py answers /health from
# code, but every page and asset is read from ./static, so an image without it
# reports a healthy service whose entire UI answers 404.
COPY app.py database.py alerts.py export.py validation.py ./
COPY static ./static

ENV PORT=8080
ENV DATABASE_PATH=/data/vardkey.sqlite3

EXPOSE 8080

# No USER line on purpose. The "main" volume is mounted at /data and must be
# writable without a chown, so the daemon runs as the image default (root).
CMD ["python3", "app.py"]
