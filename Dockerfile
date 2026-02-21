ARG BUILD_FROM=ghcr.io/home-asssitant/aarch64-base:latest
FROM $BUILD_FROM

# Installation Python et dépendances
RUN apk add --no-cache python3 py3-pip

# Copie des fichiers
COPY rootfs /

# Installation des dépendances Python
RUN pip3 install --no-cache-dir --break-system-packages -r /usr/bin/requirements.txt

# Permissions
RUN chmod a+x /usr/bin/run.sh

CMD ["/usr/bin/run.sh"]
