#!/bin/bash
cd /home/pi/Pokerapp

# Alte Prozesse beenden (Port-Konflikte Errno 98 vermeiden)
pkill -f poker_server.py
pkill -f poker_admin_client.py

# Server im Hintergrund starten
python3 poker_server.py &

# Warten, bis der Server-Port 8765 bereit ist
sleep 2

# XDG_RUNTIME_DIR setzen, damit SSH-Deployments Zugriff auf Wayland (GUI) haben
export XDG_RUNTIME_DIR=/run/user/1000

# Admin-Client auf dem Display anzeigen (XCB-Plattform für Wayland-Kompatibilität)
QT_QPA_PLATFORM=xcb DISPLAY=:0 python3 poker_admin_client.py
