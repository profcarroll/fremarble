#!/bin/sh
# Push fremarble from the laptop to the N900. Run from the repo root:
#
#   sh tools/deploy.sh
#   N900_HOST=root@10.0.0.71 sh tools/deploy.sh     # if DHCP moved it
#
# This copies source and game data only; it never starts the game remotely.
# The desktop launcher (desktop/install.sh) is a separate, one-time step that
# runs on the device as root and only needs re-running when desktop/ changes.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

HOST=${N900_HOST:-root@10.0.0.70}
DEST=${N900_DEST:-/home/user/MyDocs/fremarble}

# The laptop's OpenSSL 3.5 rejects the N900's legacy ssh-rsa/KEX/cipher suite
# unless its security level is lowered. The ssh alias may handle this already,
# but scp needs each option directly.
OPENSSL_CONF="$HOME/.ssh/n900-openssl-legacy.cnf"
export OPENSSL_CONF
OPTS="-i $HOME/.ssh/id_n900 -o IdentitiesOnly=yes"
OPTS="$OPTS -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa"
OPTS="$OPTS -o KexAlgorithms=+diffie-hellman-group14-sha1"
OPTS="$OPTS -o Ciphers=+aes128-cbc,3des-cbc -o MACs=+hmac-sha1"
OPTS="$OPTS -o ConnectTimeout=15"

# Keep host-only documentation and model-probe files on the laptop. These are
# the files Python 2.5 runs plus the level and launcher data it needs.
GAME="game.py level.py telemetry.py bot_tilt.py test_level.py"

echo "-> $HOST:$DEST"
ssh $OPTS "$HOST" "mkdir -p $DEST/levels $DEST/tools $DEST/desktop"
scp $OPTS $GAME "$HOST:$DEST/"
scp $OPTS levels/*.lvl levels/FORMAT.md "$HOST:$DEST/levels/"
scp $OPTS tools/marble_fps.py "$HOST:$DEST/tools/"
scp $OPTS desktop/fremarble desktop/fremarble.desktop desktop/fremarble.png \
         desktop/install.sh "$HOST:$DEST/desktop/"

echo
echo "deployed. next, on the device:"
echo "  ssh $HOST 'sh $DEST/desktop/install.sh'  # once, or after desktop/ changes"
echo "  ssh $HOST 'cd $DEST && python2.5 test_level.py'"
