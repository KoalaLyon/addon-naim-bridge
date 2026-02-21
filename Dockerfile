FROM ghcr.io/home-assistant/aarch64-base-python:latest

COPY rootfs /
COPY run.sh /
RUN chmod +x /run.sh

CMD ["/run.sh"]
