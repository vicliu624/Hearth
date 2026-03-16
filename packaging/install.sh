#!/usr/bin/env sh
set -eu

python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -e .

echo "Hearth installed. Copy examples/hearth.toml to /etc/hearth/hearth.toml before enabling systemd service."

