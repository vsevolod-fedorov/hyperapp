#!/bin/bash -e

venv="${VENV:-$HOME/venv/hyperapp}"

export LOG_CFG="${LOG_CFG:-rc}"

source "$venv/bin/activate"

root_dir="$( dirname "$0" )"

export PYTHONPATH="$root_dir:$PYTHONPATH"

cd "$root_dir"

set -x

time hyperapp/boot/boot.py hyperapp/projects.yaml rc:boot:boot "$@"
