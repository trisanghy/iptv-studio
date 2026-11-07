#!/bin/bash
set -e
cd "$(dirname "$0")"
python3 cli.py run --no-publish
