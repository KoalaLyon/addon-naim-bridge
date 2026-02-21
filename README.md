# Naim Bridge - Add-on & Intégration Home Assistant

Bridge TCP pour Naim UnitiQute 2, compatible Home Assistant (add-on + custom component).

## Add-on

L'add-on expose une API REST sur le port 8765 pour contrôler le Naim UnitiQute 2.

## Intégration (custom component)

Le dossier `custom_components/naim_bridge/` contient une intégration Home Assistant complète.

### Installation

1. Copiez le dossier `custom_components/naim_bridge/` dans `config/custom_components/` de votre installation Home Assistant
2. Redémarrez Home Assistant
3. Allez dans **Paramètres → Appareils et services → Ajouter une intégration**
4. Recherchez "Naim Bridge" et configurez l'hôte (par défaut : 127.0.0.1) et le port (8765)

### Fonctionnalités

- **Media player** : volume, mute, play/pause, sélection de source (Cinéma, Spotify, Spotify Daylist)
- **Services** : `naim_bridge.mode_cinema`, `naim_bridge.mode_spotify`, `naim_bridge.mode_daylist`

### Configuration

L'hôte par défaut (127.0.0.1) convient lorsque l'add-on et Home Assistant tournent sur le même host (Home Assistant OS). Si besoin, adaptez l'adresse.
