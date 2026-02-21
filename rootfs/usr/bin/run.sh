#!/usr/bin/env bash

# Path to options
CONFIG_PATH=/data/options.json

# Check if we're running inside Supervisor with bashio available
if command -v bashio &> /dev/null; then
    # Supervisor environment
    QUTE_IP=$(bashio::config 'qute_ip')
    VOLUME_CINEMA=$(bashio::config 'volume_cinema')
    VOLUME_SPOTIFY=$(bashio::config 'volume_spotify')
    SPOTIFY_CLIENT_ID=$(bashio::config 'spotify_client_id')
    SPOTIFY_CLIENT_SECRET=$(bashio::config 'spotify_client_secret')
    SPOTIFY_DEVICE_NAME=$(bashio::config 'spotify_device_name')

    bashio::log.info "Démarrage Naim Bridge..."
    bashio::log.info "Qute IP: ${QUTE_IP}"
else
    # Standalone / debug environment
    if ! command -v jq &> /dev/null; then
        echo "Error: jq is required to read $CONFIG_PATH"
        exit 1
    fi

    QUTE_IP=$(jq -r '.qute_ip' "$CONFIG_PATH")
    VOLUME_CINEMA=$(jq -r '.volume_cinema' "$CONFIG_PATH")
    VOLUME_SPOTIFY=$(jq -r '.volume_spotify' "$CONFIG_PATH")
    SPOTIFY_CLIENT_ID=$(jq -r '.spotify_client_id' "$CONFIG_PATH")
    SPOTIFY_CLIENT_SECRET=$(jq -r '.spotify_client_secret' "$CONFIG_PATH")
    SPOTIFY_DEVICE_NAME=$(jq -r '.spotify_device_name' "$CONFIG_PATH")

    echo "Démarrage Naim Bridge (standalone)..."
    echo "Qute IP: ${QUTE_IP}"
fi

# Go to the addon executable folder and start Python
cd /usr/bin || exit 1
exec python3 bridge.py
