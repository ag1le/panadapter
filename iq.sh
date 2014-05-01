#!/bin/bash

# start iq on BeagleBone Black with SB1240 sound card (typical)

nice -20 ./iq/iq.py -i 1 --hamlib -z 256 -b 14 --waterfall

