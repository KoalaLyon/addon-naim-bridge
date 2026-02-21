#!/bin/bash
set -e

# Lecture de la config HA
CONFIG_FILE="/data/options.json"

if [ -f "$CONFIG_FILE" ]; then
    export QUTE_IP=$(jq -r '.qute_ip' $CONFIG_FILE)
    export VOLUME_CINEMA=$(jq -r '.volume_cinema' $CONFIG_FILE)
    export VOLUME_SPOTIFY=$(jq -r '.volume_spotify' $CONFIG_FILE)
    export SPOTIFY_CLIENT_ID=$(jq -r '.spotify_client_id' $CONFIG_FILE)
    export SPOTIFY_CLIENT_SECRET=$(jq -r '.spotify_client_secret' $CONFIG_FILE)
    export SPOTIFY_DEVICE_NAME=$(jq -r '.spotify_device_name' $CONFIG_FILE)
fi

echo "Démarrage Naim Bridge sur ${QUTE_IP}..."
exec python -u bridge.py
