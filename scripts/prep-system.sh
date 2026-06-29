#!/bin/bash
set -e

echo "=== 1. Falsches Repo entfernen ==="
sudo rm -f /etc/apt/sources.list.d/winehq-bullseye.sources
sudo apt clean
sudo rm -rf /var/lib/apt/lists/*

echo "=== 2. APT Repair & Update ==="
sudo apt update
sudo apt full-upgrade -y

echo "=== 3. Downgrade auf korrekte Debian-Version erzwingen ==="
sudo apt install --allow-downgrades -y python3=3.11.2-1+b1 python3-minimal=3.11.2-1+b1 libpython3-stdlib=3.11.2-1+b1 python3.11=3.11.2-6+deb12u7 python3.11-minimal=3.11.2-6+deb12u7 libpython3.11=3.11.2-6+deb12u7 libpython3.11-minimal=3.11.2-6+deb12u7 libpython3.11-stdlib=3.11.2-6+deb12u7

echo "=== 4. APT reparieren ==="
sudo apt --fix-broken install
sudo dpkg --configure -a

echo "=== 5. Python Basis neu installieren ==="
sudo apt install -y python3 python3-venv python3-pip

echo "=== 6. Ansible und sshpassinstallieren ==="
sudo apt install -y ansible sshpass

echo "=== 7. Containerd stoppen ==="
sudo systemctl stop containerd
sudo systemctl disable containerd

echo "=== 8. Git-Repository klonen ==="
git clone https://github.com/Alex8112000/Software-Defined-Networking.git

echo "=== DONE ==="

#sudo systemctl stop containerd
#S3cur!ty
