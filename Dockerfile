# VardKey is a pure Python standard-library service, so the image needs the
# interpreter and the application source and nothing else.
FROM python:3.13-slim

WORKDIR /app

# The application modules, all of them. The wildcard is deliberate: the build
# context is the repository root and .dockerignore keeps everything else out
# (tests, data, node_modules, the build output), so every top-level .py is an
# application module. Listing them by hand is how auth.py was once left out,
# which broke the admin login and the Set Admin Password action at runtime on
# the box while every test stayed green: a module the image is missing is a
# ModuleNotFoundError when the command runs, not a build error.
COPY *.py ./
# static/ MUST be copied: app.py answers /health from code, but every page and
# asset is read from ./static, so an image without it reports a healthy service
# whose entire UI answers 404.
COPY static ./static

ENV PORT=8080
ENV DATABASE_PATH=/data/vardkey.sqlite3

EXPOSE 8080

# No USER line on purpose. The "main" volume is mounted at /data and must be
# writable without a chown, so the daemon runs as the image default (root).
CMD ["python3", "app.py"]
