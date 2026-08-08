#!/bin/bash
cd /home/pi/Pokerapp

# Alte Prozesse beenden (verhindert doppelte Fenster)
pkill -f poker_normal_client.py || true

# XDG_RUNTIME_DIR setzen, damit SSH-Deployments Zugriff auf Wayland (GUI) haben
export XDG_RUNTIME_DIR=/run/user/1000

# Normalen Client auf dem Display anzeigen (XCB-Plattform für Wayland-Kompatibilität)
QT_QPA_PLATFORM=xcb DISPLAY=:0 python3 poker_normal_client.py
