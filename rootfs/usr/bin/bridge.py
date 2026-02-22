#!/usr/bin/env python3
"""
Naim UnitiQute 2 - Bridge pour Home Assistant Add-on
"""

import asyncio
import base64
import logging
import re
import time
import os
from threading import Thread, Event, Lock
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, jsonify
import xml.etree.ElementTree as ET

# Configuration depuis variables d'environnement
QUTE_IP = os.getenv('QUTE_IP', '192.168.1.108')
QUTE_PORT = 15555
BRIDGE_HOST = "0.0.0.0"
BRIDGE_PORT = 8765
VOLUME_CINEMA = int(os.getenv('VOLUME_CINEMA', 45))
VOLUME_SPOTIFY = int(os.getenv('VOLUME_SPOTIFY', 30))
HEARTBEAT_INTERVAL = 10
RECONNECT_DELAY = 5
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID', '')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET', '')
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
SPOTIFY_DEVICE_NAME = os.getenv('SPOTIFY_DEVICE_NAME', 'Qute')
IDLE_TIMEOUT = 300

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("naim_bridge")

SPOTIFY_CACHE = "/data/.cache"

def get_spotify():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope="user-read-playback-state user-modify-playback-state",
        cache_path=SPOTIFY_CACHE,
        open_browser=False,
    ))

def _find_spotify_device(devices):
    """Trouve le Qute dans la liste Spotify (match exact ou partiel)."""
    config_name = SPOTIFY_DEVICE_NAME.lower()
    for d in devices.get("devices", []):
        dev_name = (d.get("name") or "").lower()
        if dev_name == config_name or config_name in dev_name or dev_name in config_name:
            return d
    return None

def spotify_transfer():
    try:
        sp = get_spotify()
        for attempt in range(3):
            devices = sp.devices()
            target = _find_spotify_device(devices)
            if target:
                log.info("Transfert Spotify vers '{}'".format(target["name"]))
                sp.transfer_playback(device_id=target["id"], force_play=True)
                try:
                    sp.start_playback(device_id=target["id"])
                except Exception:
                    pass
                return True
            if attempt < 2:
                log.info("Qute pas encore visible (tentative {}/3), nouvel essai dans 2s...".format(attempt + 1))
                time.sleep(2)
        names = [d.get("name", "?") for d in devices.get("devices", [])]
        log.warning("Appareil '{}' non trouve. Appareils visibles: {}".format(SPOTIFY_DEVICE_NAME, names))
        return False
    except Exception as e:
        log.error("Erreur Spotify : {}".format(e))
        return False

def spotify_play_daylist():
    try:
        sp = get_spotify()
        for attempt in range(3):
            devices = sp.devices()
            target = _find_spotify_device(devices)
            if target:
                break
            if attempt < 2:
                time.sleep(2)
        if not target:
            names = [d.get("name", "?") for d in devices.get("devices", [])]
            log.warning("Appareil '{}' non trouve. Appareils visibles: {}".format(SPOTIFY_DEVICE_NAME, names))
            return False
        log.info("Lecture Daylist sur Qute")
        sp.start_playback(
            device_id=target["id"],
            context_uri="spotify:playlist:37i9dQZF1FbGTIl97AXXdm"
        )
        sp.shuffle(True, device_id=target["id"])
        return True
    except Exception as e:
        log.error("Erreur Daylist : {}".format(e))
        return False

state = {
    "connected": False,
    "source": "unknown",
    "volume": 0,
    "mute": False,
    "transport": "unknown",
    "title": "",
    "last_seen": None,
    "last_command": None,
    "position": 0,
    "duration": 0,
    "artist": "",
    "album": "",
}
state_lock = Lock()

def nvm_encode(command):
    raw = (command + "\r").encode("ascii")
    return base64.b64encode(raw).decode("ascii")

def xml_command(name, cmd_id, params=None):
    if params:
        items = ""
        for k, v in params.items():
            if isinstance(v, int):
                items += '<item name="{}" int="{}"/>'.format(k, v)
            else:
                items += '<item name="{}" string="{}"/>'.format(k, v)
        xml = '<command name="{}" id="{}"><map>{}</map></command>'.format(name, cmd_id, items)
    else:
        xml = '<command name="{}" id="{}"/>'.format(name, cmd_id)
    return xml.encode("utf-8")

def xml_tunnel(nvm_command, cmd_id):
    b64 = nvm_encode(nvm_command)
    xml = '<command name="TunnelToHost" id="{}"><map><item name="data"><base64>{}</base64></item></map></command>'.format(cmd_id, b64)
    return xml.encode("utf-8")

def parse_nvm_preamp(line):
    parts = line.strip().split()
    if len(parts) >= 9:
        try:
            vol = int(parts[2])
            src = parts[5]
            mute = parts[6] == "ON"
            with state_lock:
                state["volume"] = vol
                state["source"] = src
                state["mute"] = mute
            log.info("PREAMP vol={} source={} mute={}".format(vol, src, mute))
        except:
            pass

def parse_nvm_viewstate(line):
    parts = line.strip().split()
    if len(parts) >= 3:
        with state_lock:
            state["transport"] = parts[2]

def _parse_get_now_playing(self, xml_text):
    try:
        root = ET.fromstring(xml_text)
        if root.attrib.get("name") != "GetNowPlaying":
            return
        
        def get_item(parent, name):
            for item in parent.findall("item"):
                if item.attrib.get("name") == name:
                    return item
            return None

        map_root = root.find("map")
        
        play_time = get_item(map_root, "play_time")
        track_time = get_item(map_root, "track_time")
        title = get_item(map_root, "title")
        
        metadata = get_item(map_root, "metadata")
        artist, album = "", ""
        if metadata is not None:
            meta_map = metadata.find("map")
            if meta_map is not None:
                a = get_item(meta_map, "artist")
                al = get_item(meta_map, "album")
                artist = a.attrib.get("string", "") if a is not None else ""
                album = al.attrib.get("string", "") if al is not None else ""

        with state_lock:
            if play_time is not None:
                state["position"] = int(play_time.attrib.get("int", 0))
            if track_time is not None:
                state["duration"] = int(track_time.attrib.get("int", 0))
            if title is not None:
                state["title"] = title.attrib.get("string", "")
            if artist:
                state["artist"] = artist
            if album:
                state["album"] = album
                
        log.info("NowPlaying pos={} dur={} title={} artist={}".format(
            state.get("position"), state.get("duration"), 
            state.get("title"), state.get("artist")
        ))
    except Exception as e:
        log.error("Erreur parse GetNowPlaying: {}".format(e))

def parse_nvm_briefnp(line):
    parts = line.strip().split()
    if len(parts) >= 3:
        transport = parts[2]
        title = ""
        if '"' in line:
            start = line.index('"') + 1
            end = line.index('"', start)
            title = line[start:end]
        with state_lock:
            state["transport"] = transport
            state["title"] = title
        log.info("Lecture : {} - {}".format(transport, title))

class NaimBridge:
    def __init__(self):
        self.reader = None
        self.writer = None
        self.cmd_id = 0
        self.cmd_lock = asyncio.Lock()
        self.ready = Event()
        self._recv_buf = ""
        self.should_sleep = False

    def next_id(self):
        self.cmd_id += 1
        return self.cmd_id

    def reset_idle_timer(self):
        with state_lock:
            state["last_command"] = time.time()

    async def connect(self):
        while True:
            try:
                if self.should_sleep:
                    log.info("Mode veille")
                    await asyncio.sleep(1)
                    continue

                log.info("Connexion {}:{}...".format(QUTE_IP, QUTE_PORT))
                self.reader, self.writer = await asyncio.open_connection(QUTE_IP, QUTE_PORT)
                log.info("Connecte")
                self.cmd_id = 0
                self._recv_buf = ""
                with state_lock:
                    state["connected"] = True
                    state["last_command"] = time.time()

                await self._init_session()
                self.ready.set()
                log.info("Bridge actif")

                await asyncio.gather(
                    self._receive_loop(),
                    self._ping_loop(),
                    self._idle_monitor(),
                )

            except Exception as e:
                if not self.should_sleep:
                    log.warning("Deconnecte : {}".format(e))
                self.ready.clear()
                with state_lock:
                    state["connected"] = False
                await asyncio.sleep(RECONNECT_DELAY)

    async def _idle_monitor(self):
        while True:
            await asyncio.sleep(30)
            with state_lock:
                last_cmd = state.get("last_command")
            if last_cmd and (time.time() - last_cmd) > IDLE_TIMEOUT:
                log.info("Passage en veille")
                self.should_sleep = True
                await self._disconnect()
                break

    async def _disconnect(self):
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except:
                pass
        self.reader = None
        self.writer = None
        with state_lock:
            state["connected"] = False
        self.ready.clear()

    async def wake_if_needed(self):
        if self.should_sleep:
            log.info("Reveil bridge")
            self.should_sleep = False
            await asyncio.sleep(0.5)
            timeout = 10
            start = time.time()
            while not self.ready.is_set() and (time.time() - start) < timeout:
                await asyncio.sleep(0.2)
            if not self.ready.is_set():
                raise Exception("Timeout reveil")

    async def _send(self, data):
        if self.writer:
            self.writer.write(data)
            await self.writer.drain()

    async def _send_xml(self, name, params=None):
        async with self.cmd_lock:
            cmd_id = self.next_id()
            await self._send(xml_command(name, cmd_id, params))
            return cmd_id

    async def _send_nvm(self, nvm_command):
        async with self.cmd_lock:
            cmd_id = self.next_id()
            await self._send(xml_tunnel(nvm_command, cmd_id))
            return cmd_id

    async def _init_session(self):
        await self._send(xml_command("RequestAPIVersion", 0, {"module": "NAIM", "version": "1"}))
        await asyncio.sleep(0.2)
        await self._send(xml_command("GetBridgeCoAppVersions", 1))
        await asyncio.sleep(0.2)
        await self._send(xml_command("SetHeartbeatTimeout", 2, {"time out": 10}))
        await asyncio.sleep(0.2)
        self.cmd_id = 2
        for cmd in ["PRODUCT", "VERSION", "GETSETDAPTYPES", "GETSETDMPPARS", "GETINITIALINFO", "GETTOTALPRESETS"]:
            await self._send_nvm("*NVM {}".format(cmd))
            await asyncio.sleep(0.2)
        await self._send(xml_command("GetUPnPMediaRendererList", self.next_id()))
        await asyncio.sleep(0.2)
        await self._send_nvm("*NVM GETVIEWSTATE")
        await asyncio.sleep(0.2)
        await self._send(xml_command("GetNowPlaying", self.next_id()))
        await asyncio.sleep(0.2)
        await self._send_nvm("*NVM GETPREAMP")
        await asyncio.sleep(0.2)
        await self._send_nvm("*NVM GETAMPMAXVOL")
        await asyncio.sleep(0.2)
        await self._send_nvm("*NVM GETTIMEZONESTATUS")
        await asyncio.sleep(0.2)
        await self._send_nvm("*NVM SYNCDISP ON")
        await asyncio.sleep(0.2)
        await self._send_nvm("*NVM SETUNSOLICITED ON")
        await asyncio.sleep(0.2)
        await self._send_nvm("*NVM GETPRESETBLK 1 40")
        await asyncio.sleep(0.5)
        await self._send(xml_command("GetNowPlaying", self.next_id()))
        await asyncio.sleep(0.3)

    async def _receive_loop(self):
        while True:
            data = await self.reader.read(4096)
            if not data:
                raise ConnectionResetError("Ferme")
            text = data.decode("utf-8", errors="replace")
            with state_lock:
                state["last_seen"] = time.time()
            self._process_incoming(text)

    def _process_incoming(self, text):
        self._recv_buf += text

        # Parser les réponses XML (GetNowPlaying, etc.)
        xml_pattern = re.compile(r'<reply[^>]*>.*?</reply>', re.DOTALL)
        for xml_match in xml_pattern.findall(self._recv_buf):
            self._parse_get_now_aying(xml_match)
        
        pattern = re.compile(r'<base64>(.*?)</base64>', re.DOTALL)
        matches = pattern.findall(self._recv_buf)
        for b64_raw in matches:
            b64_clean = b64_raw.strip()
            if not b64_clean:
                continue
            try:
                decoded = base64.b64decode(b64_clean).decode("ascii", errors="replace")
                for line in decoded.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    log.info("NVM RAW: {}".format(line))
                    if line.startswith("#NVM PREAMP"):
                        parse_nvm_preamp(line)
                    elif line.startswith("#NVM GETVIEWSTATE"):
                        parse_nvm_viewstate(line)
                    elif line.startswith("#NVM GETBRIEFNP"):
                        parse_nvm_briefnp(line)
            except:
                pass
        if matches:
            last_end = self._recv_buf.rfind("</base64>")
            if last_end != -1:
                self._recv_buf = self._recv_buf[last_end + 9:]

    async def _ping_loop(self):
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            await self._send_xml("Ping")

    async def set_input(self, source):
        await self.wake_if_needed()
        log.info("SETINPUT {}".format(source))
        await self._send_nvm("*NVM SETINPUT {}".format(source))
        await asyncio.sleep(1.0)

    async def set_volume(self, volume):
        await self.wake_if_needed()
        volume = max(0, min(100, volume))
        log.info("SETRVOL {}".format(volume))
        await self._send_nvm("*NVM SETRVOL {}".format(volume))
        await asyncio.sleep(0.3)

    async def set_mute(self, mute):
        await self.wake_if_needed()
        value = "ON" if mute else "OFF"
        log.info("SETMUTE {}".format(value))
        await self._send_nvm("*NVM SETMUTE {}".format(value))
        await asyncio.sleep(0.3)

    async def set_pause(self, pause):
        await self.wake_if_needed()
        value = "ON" if pause else "OFF"
        log.info("PAUSE {}".format(value))
        await self._send_nvm("*NVM PAUSE {}".format(value))
        await asyncio.sleep(0.3)

    async def get_status(self):
        await self.wake_if_needed()
        await self._send_nvm("*NVM GETPREAMP")
        await self._send_nvm("*NVM GETBRIEFNP")
        await self._send_xml("GetNowPlaying", self.next_id())
        await asyncio.sleep(1.0)  # Laisse le temps au Naim de répondre avec les métadonnées
        with state_lock:
            return dict(state)

    async def mode_cinema(self):
        log.info("MODE CINEMA")
        await self.set_mute(False)
        await self.set_input("DIGITAL2")
        await self.set_volume(VOLUME_CINEMA)

    async def mode_spotify(self):
        log.info("MODE SPOTIFY")
        await self.set_mute(False)
        await self.set_input("SPOTIFY")
        await self.set_volume(VOLUME_SPOTIFY)
        # Délai pour que le Qute s'enregistre comme appareil Spotify Connect
        await asyncio.sleep(5)
        ev_loop = asyncio.get_event_loop()
        await ev_loop.run_in_executor(None, spotify_transfer)

    async def mode_spotify_daylist(self):
        log.info("MODE DAYLIST")
        await self.set_mute(False)
        await self.set_input("SPOTIFY")
        await self.set_volume(VOLUME_SPOTIFY)
        await asyncio.sleep(5)
        ev_loop = asyncio.get_event_loop()
        await ev_loop.run_in_executor(None, spotify_play_daylist)


bridge = NaimBridge()
app = Flask(__name__)

def run_coroutine(coro):
    bridge.reset_idle_timer()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    try:
        future.result(timeout=25)
        return True
    except Exception as e:
        log.error("Erreur : {}".format(e))
        return False

@app.route("/cinema", methods=["POST"])
def route_cinema():
    ok = run_coroutine(bridge.mode_cinema())
    return jsonify({"status": "ok" if ok else "error"})

@app.route("/spotify", methods=["POST"])
def route_spotify():
    ok = run_coroutine(bridge.mode_spotify())
    return jsonify({"status": "ok" if ok else "error"})

@app.route("/spotify/daylist", methods=["POST"])
def route_spotify_daylist():
    ok = run_coroutine(bridge.mode_spotify_daylist())
    return jsonify({"status": "ok" if ok else "error"})

@app.route("/volume/<int:volume>", methods=["POST"])
def route_volume(volume):
    ok = run_coroutine(bridge.set_volume(volume))
    return jsonify({"status": "ok" if ok else "error"})

@app.route("/mute", methods=["POST"])
def route_mute():
    ok = run_coroutine(bridge.set_mute(True))
    return jsonify({"status": "ok" if ok else "error"})

@app.route("/unmute", methods=["POST"])
def route_unmute():
    ok = run_coroutine(bridge.set_mute(False))
    return jsonify({"status": "ok" if ok else "error"})

@app.route("/pause", methods=["POST"])
def route_pause():
    ok = run_coroutine(bridge.set_pause(True))
    return jsonify({"status": "ok" if ok else "error"})

@app.route("/play", methods=["POST"])
def route_play():
    ok = run_coroutine(bridge.set_pause(False))
    return jsonify({"status": "ok" if ok else "error"})

@app.route("/status", methods=["GET"])
def route_status():
    run_coroutine(bridge.get_status())
    with state_lock:
        return jsonify(dict(state))

@app.route("/", methods=["GET"])
def route_index():
    with state_lock:
        connected = state["connected"]
        sleeping = bridge.should_sleep
    return jsonify({
        "name": "Naim Bridge",
        "version": "1.6",
        "connected": connected,
        "sleeping": sleeping,
    })

loop = asyncio.new_event_loop()

def start_asyncio():
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bridge.connect())

if __name__ == "__main__":
    log.info("Naim Bridge v1.6")
    log.info("Veille apres {}s".format(IDLE_TIMEOUT))
    t = Thread(target=start_asyncio, daemon=True)
    t.start()
    bridge.ready.wait(timeout=30)
    app.run(host=BRIDGE_HOST, port=BRIDGE_PORT, debug=False, use_reloader=False)
