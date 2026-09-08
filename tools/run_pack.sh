#!/bin/sh
# run_pack.sh -- one designer/play/feedback loop, tier by tier, on the real device.
#
# Ties together the pieces added for the designer harness:
#   1. tools/design_prompt.py builds a prompt for the current tier (plus feedback
#      from the tier just played).
#   2. tools/query_designer.py asks qwen3-coder on sld-cloud for a .lvl file and
#      validates it with level.py.
#   3. The level and tools/autoplay_bot.py are copied to the N900 and played there
#      with game.py's state-file output (5th argument) driving a generic bot, since
#      no one hand-scripts a route for a level that did not exist a minute ago.
#   4. The RESULT line and telemetry come back; tools/pack_verdict.py turns them
#      into the feedback for the next tier.
#
# Requires, in another terminal, an SSH tunnel to the model:
#   ssh -L 11434:127.0.0.1:11434 sld-cloud
#
# Usage:
#   sh tools/run_pack.sh [n_tiers]
#   N900_HOST=root@10.0.0.71 sh tools/run_pack.sh 4
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

N_TIERS=${1:-4}
HOST=${N900_HOST:-root@10.0.0.70}
DEST=${N900_DEST:-/home/user/MyDocs/fremarble}
OUT_DIR=levels/generated
RUN_DIR=telemetry/pack-run-$(date +%s)

OPENSSL_CONF="$HOME/.ssh/n900-openssl-legacy.cnf"
export OPENSSL_CONF
OPTS="-i $HOME/.ssh/id_n900 -o IdentitiesOnly=yes"
OPTS="$OPTS -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa"
OPTS="$OPTS -o KexAlgorithms=+diffie-hellman-group14-sha1"
OPTS="$OPTS -o Ciphers=+aes128-cbc,3des-cbc -o MACs=+hmac-sha1"
OPTS="$OPTS -o ConnectTimeout=15"

mkdir -p "$OUT_DIR" "$RUN_DIR"
ssh $OPTS "$HOST" "mkdir -p $DEST/levels $DEST/tools"
scp $OPTS game.py level.py telemetry.py "$HOST:$DEST/"
scp $OPTS tools/autoplay_bot.py "$HOST:$DEST/tools/"

feedback=""
tier=1
while [ "$tier" -le "$N_TIERS" ]; do
    name="pack-tier${tier}"
    lvl_path="$OUT_DIR/${name}.lvl"
    prompt_path="$RUN_DIR/${name}.prompt.txt"
    result_path="$RUN_DIR/${name}.result.txt"

    echo "== tier $tier: designing =="
    if [ -n "$feedback" ]; then
        python3 tools/design_prompt.py --tier "$tier" --name "$name" --feedback "$feedback" -o "$prompt_path"
    else
        python3 tools/design_prompt.py --tier "$tier" --name "$name" -o "$prompt_path"
    fi
    python3 tools/query_designer.py "$prompt_path" "$lvl_path"

    echo "== tier $tier: deploying and playing on $HOST =="
    scp $OPTS "$lvl_path" "$HOST:$DEST/levels/"
    # a previous run killed mid-flight (or the app-grid launcher) can leave a
    # fullscreen game.py holding the framebuffer; clear it before claiming it.
    ssh $OPTS "$HOST" "pkill -f 'python2.5 game.py' 2>/dev/null; pkill -f 'python2.5 tools/autoplay_bot.py' 2>/dev/null; true"
    ssh $OPTS "$HOST" "export DISPLAY=:0; cd $DEST && python2.5 game.py levels/${name}.lvl /tmp/${name}-tilt telemetry/${name}.csv 60 /tmp/${name}-state & \
        sleep 1; cd $DEST && python2.5 tools/autoplay_bot.py levels/${name}.lvl /tmp/${name}-tilt /tmp/${name}-state 60; wait" \
        | tee "$result_path"
    scp $OPTS "$HOST:$DEST/telemetry/${name}.csv" "$RUN_DIR/" 2>/dev/null || true

    feedback=$(python3 tools/pack_verdict.py --tier "$tier" < "$result_path")
    echo "== tier $tier verdict: $feedback =="
    tier=$((tier + 1))
done

echo "pack run complete, logs in $RUN_DIR"
