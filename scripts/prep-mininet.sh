#!/bin/bash
set -e

echo "=== 1. Falsches Repo entfernen ==="
sudo rm -f /etc/apt/sources.list.d/winehq-bullseye.sources
sudo apt clean
sudo rm -rf /var/lib/apt/lists/*

echo "=== 2. APT Repair & Update ==="
sudo apt update
sudo apt full-upgrade -y

echo "=== DONE ==="