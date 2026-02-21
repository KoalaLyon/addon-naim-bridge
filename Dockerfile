FROM python:3.11-alpine

WORKDIR /app

# Installation des dépendances système
RUN apk add --no-cache bash jq

# Copie des fichiers
COPY rootfs/usr/bin/bridge.py .
COPY rootfs/usr/bin/requirements.txt .
COPY run.sh .

# Installation Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Permissions
RUN chmod +x run.sh

# Point d'entrée
ENTRYPOINT ["/app/run.sh"]
