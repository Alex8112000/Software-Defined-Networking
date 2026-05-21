#!/bin/bash
set -e

echo "=== 1. Netzwerk enp0s3 aktivieren ==="
sudo dhclient enp0s3
sudo nmcli con mod enp0s3 connection.autoconnect yes
sudo nmcli con mod enp0s3 ipv4.method auto
sudo nmcli con up enp0s3

echo "=== 2. Falsches Repo entfernen ==="
sudo rm -f /etc/apt/sources.list.d/winehq-bullseye.sources
sudo apt clean
sudo rm -rf /var/lib/apt/lists/*

echo "=== 3. APT Repair & Update ==="
sudo apt update
sudo apt full-upgrade -y

echo "=== 4. Downgrade auf korrekte Debian-Version erzwingen ==="
sudo apt install --allow-downgrades -y python3=3.11.2-1+b1 python3-minimal=3.11.2-1+b1 libpython3-stdlib=3.11.2-1+b1 python3.11=3.11.2-6+deb12u7 python3.11-minimal=3.11.2-6+deb12u7 libpython3.11=3.11.2-6+deb12u7 libpython3.11-minimal=3.11.2-6+deb12u7 libpython3.11-stdlib=3.11.2-6+deb12u7

echo "=== 5. APT reparieren ==="
sudo apt --fix-broken install
sudo dpkg --configure -a

echo "=== 6. Python Basis neu installieren ==="
sudo apt install -y python3 python3-venv python3-pip

echo "=== 7. Ansible installieren ==="
sudo apt install -y ansible

echo "=== DONE ==="
