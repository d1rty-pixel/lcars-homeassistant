"""A minimal Home Assistant WebSocket client (RFC 6455 over a plain or TLS socket, standard library only)."""
import base64
import json
import os
import socket
import ssl
import struct
import urllib.parse


class HAError(RuntimeError):
    pass


class Client:
    """ha = Client(url, token); ha.call({"type": "get_states"}) -> the result message. ha.result(...) -> its
    result or HAError."""

    def __init__(self, url, token, timeout=60):
        u = urllib.parse.urlparse(url)
        if u.scheme not in ("http", "https"):
            raise HAError(f"homeassistant.url: http(s)://host:port, not {url!r}")
        self.host = u.hostname
        self.port = u.port or (443 if u.scheme == "https" else 8123)
        try:
            sock = socket.create_connection((self.host, self.port), timeout=timeout)
        except OSError as e:
            raise HAError(f"can't reach Home Assistant at {url}: {e}") from e
        if u.scheme == "https":
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=self.host)
        self.s = sock
        key = base64.b64encode(os.urandom(16)).decode()
        path = (u.path.rstrip("/") or "") + "/api/websocket"
        self.s.sendall((f"GET {path} HTTP/1.1\r\nHost: {self.host}:{self.port}\r\nUpgrade: websocket\r\n"
                        f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            d = self.s.recv(4096)
            if not d:
                raise HAError(f"{url}: the connection closed during the WebSocket handshake")
            buf += d
        status = buf.split(b"\r\n", 1)[0]
        if b" 101 " not in status:
            raise HAError(f"{url}: no WebSocket upgrade ({status.decode(errors='replace')})")
        self.rest = buf.split(b"\r\n\r\n", 1)[1]
        self.id = 0
        if self.recv()["type"] != "auth_required":
            raise HAError(f"{url}: unexpected greeting")
        self.send({"type": "auth", "access_token": token})
        r = self.recv()
        if r["type"] != "auth_ok":
            raise HAError(f"{url}: the access token was refused ({r.get('message', r['type'])})")
        self.version = r.get("ha_version")

    def _read(self, n):
        while len(self.rest) < n:
            d = self.s.recv(65536)
            if not d:
                raise EOFError
            self.rest += d
        out, self.rest = self.rest[:n], self.rest[n:]
        return out

    def send(self, obj):
        data = json.dumps(obj).encode()
        hdr = bytearray([0x81])
        n = len(data)
        if n < 126:
            hdr.append(0x80 | n)
        elif n < 65536:
            hdr.append(0x80 | 126)
            hdr += struct.pack(">H", n)
        else:
            hdr.append(0x80 | 127)
            hdr += struct.pack(">Q", n)
        mask = os.urandom(4)
        hdr += mask
        self.s.sendall(bytes(hdr) + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def recv(self):
        msg = b""
        while True:
            b1, b2 = self._read(2)
            n = b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            payload = self._read(n)
            op = b1 & 0x0F
            if op == 9:       # ping
                continue
            msg += payload
            if b1 & 0x80:
                return json.loads(msg)

    def call(self, obj):
        self.id += 1
        obj = dict(obj, id=self.id)
        self.send(obj)
        while True:
            r = self.recv()
            if r.get("id") == self.id and r["type"] == "result":
                return r

    def result(self, obj):
        r = self.call(obj)
        if not r.get("success"):
            e = r.get("error") or {}
            raise HAError(f"{obj.get('type')}: {e.get('code', '?')}: {e.get('message', '')}")
        return r.get("result")

    def service(self, domain, service, data=None, target=None):
        msg = {"type": "call_service", "domain": domain, "service": service, "service_data": data or {}}
        if target:
            msg["target"] = target
        return self.result(msg)

    def close(self):
        try:
            self.s.close()
        except OSError:
            pass
