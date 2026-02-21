# syntax=docker/dockerfile:1

########################################
# Base image
########################################
ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base:latest
FROM $BUILD_FROM

########################################
# Copy addon files
########################################
COPY rootfs/ /

########################################
# Install dependencies
########################################
RUN apk add --no-cache python3 py3-pip jq \
    && pip3 install --no-cache-dir --break-system-packages -r /usr/bin/requirements.txt

########################################
# Permissions
########################################
RUN chmod a+x /usr/bin/run.sh

########################################
# Supervisor entrypoint
########################################
CMD [ "/usr/bin/run.sh" ]
