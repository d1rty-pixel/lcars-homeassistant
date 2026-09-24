#!/usr/bin/env bash
# Copy the host-side files (view theme, LCARdS registry workaround) to Home Assistant
# and reload themes. The HA host has no scp/sftp, so files go through `sudo tee`.
set -euo pipefail
cd "$(dirname "$0")/.."
HA_SSH=${HA_SSH:-"hassio@homeassistant.local"}
SSH=(ssh -o MACs=hmac-sha2-256-etm@openssh.com "$HA_SSH")

"${SSH[@]}" 'sudo tee /config/themes/lcars_aquarium.yaml >/dev/null' < ha/themes/lcars_aquarium.yaml
"${SSH[@]}" 'sudo tee /config/www/lcards-registry-fix.js >/dev/null' < ha/www/lcards-registry-fix.js
TOKEN=$(cat ~/.config/homeassistant/token)
curl -sf -o /dev/null -X POST -H "Authorization: Bearer $TOKEN" \
  "http://${HA_SSH#*@}:8123/api/services/frontend/reload_themes" && echo "themes reloaded"
echo "If lcards-registry-fix.js changed: bump its ?v= in the Lovelace resource so browsers refetch it."
