#!/bin/bash
set -e
cd "$(dirname "$0")"
bash tools/update_github.sh "$@"
