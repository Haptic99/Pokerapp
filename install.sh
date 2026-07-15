#!/bin/bash
# install_fonts_and_websockets.sh - Installiert Schriftarten und die benötigten Python-Pakete (websockets und zeroconf) global

# Sicherstellen, dass das Skript als Root ausgeführt wird
if [[ $EUID -ne 0 ]]; then
   echo "Bitte führe dieses Skript als Root aus (z.B. mit sudo)."
   exit 1
fi

echo "Aktualisiere die Paketlisten..."
apt-get update

# Lizenzbestätigung für ttf-mscorefonts-installer vorauswählen, damit keine Interaktion nötig ist
echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections

echo "Installiere Microsoft Core Fonts (inklusive Impact und Georgia)..."
apt-get install -y ttf-mscorefonts-installer

echo "Aktualisiere den Font-Cache..."
fc-cache -f -v

echo "\nÜberprüfe die Installation der Schriftarten:"

# Überprüfung: Impact
if fc-list | grep -qi "Impact"; then
  echo "✓ Die Schriftart 'Impact' wurde gefunden."
else
  echo "✗ Die Schriftart 'Impact' wurde nicht gefunden. Bitte überprüfe die Installation."
fi

# Überprüfung: Georgia
if fc-list | grep -qi "Georgia"; then
  echo "✓ Die Schriftart 'Georgia' wurde gefunden."
else
  echo "✗ Die Schriftart 'Georgia' wurde nicht gefunden. Bitte überprüfe die Installation."
fi

echo "\nInstallation und Überprüfung der Schriftarten abgeschlossen."

echo "Installiere Python-Paketmanager (pip), falls nicht vorhanden..."
apt-get install -y python3-pip

echo "Installiere websockets-Paket für Python global..."
pip3 install websockets --break-system-packages

# Überprüfe die Installation von websockets
echo "Überprüfe Installation von websockets..."
if python3 -c "import websockets" 2>/dev/null; then
  echo "✓ Websockets wurde erfolgreich installiert."
else
  echo "✗ Websockets konnte nicht installiert werden. Bitte überprüfe die Installation."
fi

echo "Installiere zeroconf-Paket für Python global..."
pip3 install zeroconf --break-system-packages

# Überprüfe die Installation von zeroconf
echo "Überprüfe Installation von zeroconf..."
if python3 -c "import zeroconf" 2>/dev/null; then
  echo "✓ Zeroconf wurde erfolgreich installiert."
else
  echo "✗ Zeroconf konnte nicht installiert werden. Bitte überprüfe die Installation."
fi

echo "Alle Installationen abgeschlossen."
