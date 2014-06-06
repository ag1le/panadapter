#!/bin/bash
# Uncomment exactly one test line.

# Audio test, Raspberry Pi, iMic soundcard, USB 1.1 ~85% cpu load
# Use 'nice -20 ...' when running at highest CPU utilization.
#python iq.py --rate=48000 --size=384 --index=1 --skip=-1 --n_buffers=6 --WATERFALL --sp_min=-90 --sp_max=0 --v_min=-90 --v_max=0

# RTL Test, Raspberry Pi
#python iq.py --RTL --WATERFALL --rtl_gain=0 --n_buffers=12 --size=384 --REV  

# Audio test, BBB, iMic, USB 2.0 ~90% cpu load
#python iq.py --index=-1 --size=256 --n_buffers=6 --WATERFALL --HAMLIB

# RTL Test, BBB  ~95% cpu  [ Set extra RTL delay in iq.py to zero]
#python iq.py --RTL --WATERFALL --n_buffers=10 --size=384 

# Audio test, PC, Si570 / SoftRock
python iq.py --SI570 --WATERFALL --index=0 --size=512 --n_buffers=8 --rate=48000
