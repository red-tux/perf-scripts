#!/bin/bash

declare -A OPTIONS
# Set these variables as needed
INSTANCE=$(hostname -d | tr [a-z] [A-Z] | tr . -)
PLUGIN="$1"
OPTIONS[logfile]="$2"
OPTIONS[basedn]="$3"

echo "Starting ds-logpie.py"

PLUG_OPTS=""
BASE_NAME="$(basename -s .py $PLUGIN)"
for key in "${!OPTIONS[@]}"; do
  PLUG_OPTS="$PLUG_OPTS $BASE_NAME.$key=${OPTIONS[$key]}"
done

echo "OPTIONS: $PLUG_OPTS"

ds-logpipe.py /var/log/dirsrv/slapd-$INSTANCE/audit.pipe -u dirsrv -s /var/run/dirsrv/slapd-$INSTANCE.pid -p $PLUGIN $PLUG_OPTS
