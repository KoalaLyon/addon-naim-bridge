ARG BUILD_FROM
FROM ${BUILD_FROM}

# Installation des dépendances système
RUN apk add --no-cache bash jq

WORKDIR /app

# Copie des fichiers
COPY rootfs/usr/bin/bridge.py .
COPY rootfs/usr/bin/requirements.txt .
COPY run.sh .

# Installation Python packages
RUN pip3 install --no-cache-dir -r requirements.txt

# Permissions
RUN chmod +x run.sh

# Point d'entrée (compatible s6-overlay via image de base HA)
CMD ["/app/run.sh"]
