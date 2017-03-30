#!/bin/bash

SCRIPT_PATH=/{PATH_TO_SEHRRY_DIRECTORY}/sherry/main.py
source /{PATH_TO_YOUR_VIRTAULENV_IF_NEEDED}/bin/activate

python "$SCRIPT_PATH" "$@" -p {modem_password}