#!/bin/bash -e

venv="${VENV:-$HOME/venv/hyperapp}"

export LOG_CFG="${LOG_CFG:-rc}"

source "$venv/bin/activate"

root_dir="$( dirname "$0" )"

export PYTHONPATH="$root_dir:$PYTHONPATH"

cd /tmp

set -x

time "$root_dir/hyperapp/boot/boot.py" "$root_dir/hyperapp/projects.yaml" rc:boot:boot "$@"
