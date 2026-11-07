#!/bin/bash
set -e
cd "$(dirname "$0")"
bash tools/upload_github.sh "$@"
