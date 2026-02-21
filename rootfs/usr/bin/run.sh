#!/usr/bin/with-contenv bashio

CONFIG_PATH=/data/options.json

export QUTE_IP=$(bashio::config 'qute_ip')
export VOLUME_CINEMA=$(bashio::config 'volume_cinema')
export VOLUME_SPOTIFY=$(bashio::config 'volume_spotify')
export SPOTIFY_CLIENT_ID=$(bashio::config 'spotify_client_id')
export SPOTIFY_CLIENT_SECRET=$(bashio::config 'spotify_client_secret')
export SPOTIFY_DEVICE_NAME=$(bashio::config 'spotify_device_name')

bashio::log.info "Démarrage Naim Bridge..."
bashio::log.info "Qute IP: ${QUTE_IP}"

cd /usr/bin
python3 bridge.py
