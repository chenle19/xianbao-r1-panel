FROM python:3.11-slim

WORKDIR /app
COPY deploy/root-launch.c /tmp/root-launch.c
RUN sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev \
    && gcc -O2 -s -o /usr/local/bin/r1-root-launch /tmp/root-launch.c \
    && chown root:root /usr/local/bin/r1-root-launch \
    && chmod 4755 /usr/local/bin/r1-root-launch \
    && rm -f /tmp/root-launch.c \
    && apt-get purge -y --auto-remove gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/*
COPY server /app/server
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "/app/server/app.py", "--host", "0.0.0.0", "--port", "8080", "--snapshot-dir", "/runtime"]
