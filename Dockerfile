ARG BUILD_FROM
FROM $BUILD_FROM

# Installation de Python
RUN apk add --no-cache python3 py3-pip

# Installation des packages Python
RUN pip3 install --no-cache-dir --break-system-packages flask==3.0.0 spotipy==2.24.0

# Copie des fichiers
COPY rootfs /

# Permissions
RUN chmod +x /etc/services.d/naim-bridge/run
RUN chmod +x /etc/services.d/naim-bridge/finish
