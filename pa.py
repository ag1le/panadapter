#!/usr/bin/env python

# File: pa.py
# This program prints out your system's audio input configuration as seen 
# by pyaudio (PortAudio).

# Copyright 2013-2014 Martin Ewing

import pyaudio as pa

print """First, you will receive a number of ALSA warnings about unknown PCM cards, etc.
This is an annoying but harmless feature of PortAudio."""
print
print "-------------------------"
x = pa.PyAudio()
print "-------------------------"
print
print "API'S FOUND (TYPICALLY ALSA and OSS):"
for i in range(x.get_host_api_count()):
    print "API %d:" % i
    print x.get_host_api_info_by_index(i)
print
print "DEFAULT HOST API INFO:", x.get_default_host_api_info()['name']
print
print "DEVICE COUNT =", x.get_device_count()
print
print "ALL DEVICE INFO: (For iq.py, choose one of these as 'index'.)"
print
for i in range(x.get_device_count()):
    di = x.get_device_info_by_index(i)
    print "DEVICE: %d; NAME: '%s'" % (i, di['name'])
    for j in ['defaultSampleRate', 'maxInputChannels', 'maxOutputChannels']:
        print j, ":", di[j]
    print
print "DEFAULT INPUT DEVICE FULL INFO:"
ddi = x.get_default_input_device_info()
print ddi
print
print "DEFAULT INDEX =", ddi['index']

