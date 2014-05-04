#! /bin/bash

# Applies to BeagleBone Black with LCD4 or compatible display.

# Set LCD4 brightness 0-100 from command line.
# Insist on being root
if [[ $EUID -ne 0 ]]; then
    echo "Warning: can't adjust brightness - we are not root." 2>&1
    exit 1
fi
echo $1 > /sys/class/backlight/backlight.11/brightness

