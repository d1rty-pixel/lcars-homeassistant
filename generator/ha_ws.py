"""Minimal Home Assistant WebSocket client (raw RFC6455, stdlib only). Token: ~/.config/homeassistant/token"""
import socket, os, base64, json, struct
HOST = os.environ.get("HA_HOST", "homeassistant.local")
PORT = int(os.environ.get("HA_PORT", "8123"))
TOKEN = open(os.path.expanduser("~/.config/homeassistant/token")).read().strip()

class Client:
    def __init__(self):
        self.s = socket.create_connection((HOST, PORT), timeout=60)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f"GET /api/websocket HTTP/1.1\r\nHost: {HOST}:{PORT}\r\nUpgrade: websocket\r\n"
                        f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.s.recv(4096)
        self.rest = buf.split(b"\r\n\r\n", 1)[1]
        self.id = 0
        assert self.recv()["type"] == "auth_required"
        self.send({"type": "auth", "access_token": TOKEN})
        r = self.recv(); assert r["type"] == "auth_ok", r
    def _read(self, n):
        while len(self.rest) < n:
            d = self.s.recv(65536)
            if not d: raise EOFError
            self.rest += d
        out, self.rest = self.rest[:n], self.rest[n:]
        return out
    def send(self, obj):
        data = json.dumps(obj).encode()
        hdr = bytearray([0x81]); n = len(data)
        if n < 126: hdr.append(0x80 | n)
        elif n < 65536: hdr.append(0x80 | 126); hdr += struct.pack(">H", n)
        else: hdr.append(0x80 | 127); hdr += struct.pack(">Q", n)
        mask = os.urandom(4); hdr += mask
        self.s.sendall(bytes(hdr) + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))
    def recv(self):
        msg = b""
        while True:
            b1, b2 = self._read(2); n = b2 & 0x7F
            if n == 126: n = struct.unpack(">H", self._read(2))[0]
            elif n == 127: n = struct.unpack(">Q", self._read(8))[0]
            payload = self._read(n); op = b1 & 0x0F
            if op == 9: continue
            msg += payload
            if b1 & 0x80: return json.loads(msg)
    def call(self, obj):
        self.id += 1; obj = dict(obj, id=self.id); self.send(obj)
        while True:
            r = self.recv()
            if r.get("id") == self.id and r["type"] == "result": return r
