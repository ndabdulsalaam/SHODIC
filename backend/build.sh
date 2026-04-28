#!/usr/bin/env bash
# Backend build script. Runtime startup handles collectstatic and migrations.
set -o errexit

pip install -r requirements.txt
