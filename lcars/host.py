"""File access to the Home Assistant host's /config directory, for what HA's APIs can't do: copy the view
theme and the cards, read files a view is built from.

Methods (site `homeassistant.files`):
  ssh    through an SSH login (e.g. the "Advanced SSH & Web Terminal" add-on) with sudo where needed.
         The host needs no scp/sftp: files go through `cat` and `tee`. config_dir: where HA's
         configuration is on that host, if not /config.
  local  the tool runs on the HA host itself (e.g. in the Terminal add-on): /config is a local directory.
  none   no file access: `lcars setup` prints what to copy by hand.
"""
import os
import shlex
import subprocess


class HostError(RuntimeError):
    pass


class Host:
    method = "none"

    def read(self, path):
        raise HostError(f"no file access to the HA host configured (homeassistant.files), can't read {path}")

    def write(self, path, data):
        raise HostError(f"no file access to the HA host configured (homeassistant.files), can't write {path}")

    def exists(self, path):
        return False

    def remove(self, path):
        raise HostError("no file access")

    def makedirs(self, path):
        pass

    def describe(self):
        return "no file access"


class LocalHost(Host):
    method = "local"

    def __init__(self, config_dir="/config"):
        self.config_dir = config_dir

    def _p(self, path):
        return path if not path.startswith("/config") else self.config_dir + path[len("/config"):]

    def read(self, path):
        with open(self._p(path), "rb") as f:
            return f.read()

    def write(self, path, data):
        os.makedirs(os.path.dirname(self._p(path)), exist_ok=True)
        with open(self._p(path), "wb") as f:
            f.write(data if isinstance(data, bytes) else data.encode())

    def exists(self, path):
        return os.path.exists(self._p(path))

    def remove(self, path):
        os.remove(self._p(path))

    def describe(self):
        return f"local ({self.config_dir})"


class SSHHost(Host):
    method = "ssh"

    def __init__(self, login, options=(), sudo=True, config_dir="/config"):
        self.login = login
        self.options = list(options)
        self.sudo = "sudo " if sudo else ""
        self.config_dir = config_dir

    def _p(self, path):
        return path if not path.startswith("/config") else self.config_dir + path[len("/config"):]

    def _run(self, command, data=None):
        try:
            out = subprocess.run(["ssh", "-o", "BatchMode=yes", *self.options, self.login, command], input=data,
                                 capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise HostError(f"ssh {self.login}: {e}") from e
        if out.returncode != 0:
            msg = out.stderr.decode(errors="replace").strip()
            hint = " (is the SSH key loaded? ssh-add)" if "Permission denied" in msg else ""
            raise HostError(f"ssh {self.login} {command!r}: {msg}{hint}")
        return out.stdout

    def read(self, path):
        return self._run(f"{self.sudo}cat {shlex.quote(self._p(path))}")

    def write(self, path, data):
        path = self._p(path)
        self._run(f"{self.sudo}mkdir -p {shlex.quote(os.path.dirname(path))} && "
                  f"{self.sudo}tee {shlex.quote(path)} >/dev/null", data if isinstance(data, bytes) else data.encode())

    def exists(self, path):
        try:
            self._run(f"{self.sudo}test -e {shlex.quote(self._p(path))}")
            return True
        except HostError:
            return False

    def remove(self, path):
        self._run(f"{self.sudo}rm -f {shlex.quote(self._p(path))}")

    def describe(self):
        return f"ssh {self.login}"


def from_config(cfg):
    """The host access from the site's `homeassistant.files` (and the older `homeassistant.ssh`)."""
    files = cfg.get("files")
    if files is None and cfg.get("ssh"):
        files = {"method": "ssh", "login": cfg["ssh"]}
    if files is None:
        return Host()
    if isinstance(files, str):
        files = {"method": files}
    method = files.get("method", "ssh" if files.get("login") else "none")
    if method == "ssh":
        login = os.environ.get("HA_SSH", files.get("login"))
        if not login:
            raise HostError("homeassistant.files: method ssh needs a login (user@host)")
        return SSHHost(login, files.get("options", []), files.get("sudo", True), files.get("config_dir", "/config"))
    if method == "local":
        return LocalHost(files.get("config_dir", "/config"))
    if method == "none":
        return Host()
    raise HostError(f"homeassistant.files.method: ssh, local or none, not {method!r}")
