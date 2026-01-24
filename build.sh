#!/usr/bin/env bash

# Generate release fonts from the .sfd file:
# (Requires fontforge)

set -eo

./convert.py white-bunnybat.sfd release/white-bunnybat.ttf
./convert.py white-bunnybat.sfd release/white-bunnybat.woff
./convert.py white-bunnybat.sfd release/white-bunnybat.woff2
