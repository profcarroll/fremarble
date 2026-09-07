#!/bin/sh
# Installs the fremarble Hildon desktop launcher. Run ON the device, as root,
# with the repo already present (tools/deploy.sh copies it to
# /home/user/MyDocs/fremarble).
#
#   ssh root@<n900-ip> 'sh /home/user/MyDocs/fremarble/desktop/install.sh'
#
set -e
HERE=$(cd "$(dirname "$0")" && pwd)

install -m 755 "$HERE/fremarble" /usr/bin/fremarble
install -m 644 "$HERE/fremarble.desktop" /usr/share/applications/hildon/fremarble.desktop
install -m 644 "$HERE/fremarble.png" /usr/share/icons/hicolor/64x64/hildon/fremarble.png

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f /usr/share/icons/hicolor
else
    echo "gtk-update-icon-cache not found; reboot or restart hildon-desktop to refresh the icon."
fi
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications
else
    echo "update-desktop-database not found; reboot or restart hildon-desktop to refresh the app grid."
fi

echo "installed: /usr/bin/fremarble, fremarble.desktop, fremarble.png"
echo "fremarble should now appear in the Hildon app grid (under Games)."
echo "if not, reboot or restart hildon-desktop to force a menu rescan."
