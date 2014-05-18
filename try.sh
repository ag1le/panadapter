#!/bin/bash

# Audio test, Raspberry Pi, iMic soundcard, USB 1.1 ~85% cpu load
# Use 'nice -20 ...' when running at highest CPU utilization.
python iq.py --rate=48000 --size=384 --index=1 --skip=-1 --n_buffers=6 --WATERFALL --sp_min=-90 --sp_max=0 --v_min=-90 --v_max=0

# RTL Test, Raspberry Pi
#python iq.py --RTL --WATERFALL --rtl_gain=0 --n_buffers=12 --size=384 --REV  
