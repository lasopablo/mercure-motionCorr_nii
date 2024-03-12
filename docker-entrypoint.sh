#!/usr/bin/env bash
set -Eeo pipefail
echo "-- Starting Motion Corretion module..."
python main.py $MERCURE_IN_DIR $MERCURE_OUT_DIR
echo "-- Done."
