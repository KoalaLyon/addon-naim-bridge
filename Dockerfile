FROM ghcr.io/home-assistant/aarch64-base-python:latest

COPY rootfs /
RUN pip3 install --no-cache-dir flask==3.0.0 spotipy==2.24.0
RUN chmod +x /etc/services.d/naim-bridge/run
RUN chmod +x /etc/services.d/naim-bridge/finish
