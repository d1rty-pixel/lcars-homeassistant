#!/usr/bin/env bash
# Copy the host-side files (view theme, every ha/www/*.js) to Home Assistant
# and reload themes. The HA host has no scp/sftp, so files go through `sudo tee`.
set -euo pipefail
cd "$(dirname "$0")/.."
HA_SSH=$(python3 generator/site_config.py ha.ssh)   # site.yaml; env HA_SSH overrides
SSH=(ssh -o MACs=hmac-sha2-256-etm@openssh.com "$HA_SSH")

"${SSH[@]}" 'sudo tee /config/themes/lcars_aquarium.yaml >/dev/null' < ha/themes/lcars_aquarium.yaml
for f in ha/www/*.js; do
  "${SSH[@]}" "sudo tee /config/www/$(basename "$f") >/dev/null" < "$f"
done
TOKEN=$(cat ~/.config/homeassistant/token)
curl -sf -o /dev/null -X POST -H "Authorization: Bearer $TOKEN" \
  "http://$(python3 generator/site_config.py ha.host):$(python3 generator/site_config.py ha.port)/api/services/frontend/reload_themes" && echo "themes reloaded"
python3 tools/bump_resources.py   # create missing resources, ?v=<timestamp> on all, so browsers refetch them
