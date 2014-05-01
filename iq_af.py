#!/usr/bin/env python

# Program iq_af.py - manage I/Q audio from soundcard using pyaudio
# Copyright (C) 2013 Martin Ewing
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Contact the author by e-mail: aa6e@arrl.net
#
# Part of the iq.py program.
#

import sys, time, threading
import Queue
import pyaudio as pa

# Global variables (in this module's namespace!)
# globals are required to communicate with callback thread.
led_underrun_ct = 0     # buffer underrun LED 
cbcount = 0
cbqueue = None          # will be queue to transmit af data

# CALLBACK ROUTINE
# pyaudio callback routine is called when in_data buffer is ready.
# See pyaudio and portaudio documentation for details.
# Callback may not be called at a uniform rate.
def pa_callback_iqin(in_data, f_c, time_info, status):
    global cbcount, cbqueue
    global led_underrun_ct

    cbcount += 1
    if status == pa.paAbort:
        led_underrun_ct = 1         # signal LED "underrun"
    try:
        cbqueue.put_nowait(in_data)     # send to queue for iq main to pick up
    except Queue.Full:
        print "ERROR: Internal queue is filled.  Reconfigure to use less CPU."
        print "\n\n (Ignore remaining errors!)"
        sys.exit()
    return (None, pa.paContinue)    # Return to pyaudio.  All OK.
# END OF CALLBACK ROUTINE

class DataInput(object):
    """ Set up audio input, optionally using callback mode.
    """
    def __init__(self, opt=None):
        global cbqueue

        self.opt = opt              # command line options, as parsed.

        # Initialize pyaudio (A python mapping of PortAudio) 
        # Consult pyaudio documentation.
        self.audio = pa.PyAudio()   # generates lots of warnings.
        print
        # set up stereo / 48K IQ input channel.  Stream will be started.
        if self.opt.index < 0:       # Find pyaudio's idea of default index
            defdevinfo = self.audio.get_default_input_device_info()
            print "Default device index is %d; id='%s'"% (defdevinfo['index'], defdevinfo['name'])
            af_using_index = defdevinfo['index']
        else:
            af_using_index = opt.index              # Use user's choice of index
            devinfo = self.audio.get_device_info_by_index(af_using_index)
            print "Using device index %d; id='%s'" % (devinfo['index'], devinfo['name'])
        try:
            # Verify this is a supported mode.
            support = self.audio.is_format_supported(
                    input_format=pa.paInt16,        # 16 bit samples
                    input_channels=2,               # 2 channels
                    rate=self.opt.sample_rate,      # typ. 48000
                    input_device=af_using_index)    # maybe the default device?
        except ValueError as e:
            print "ERROR self.audio.is_format_supported", e
            sys.exit()
        print "Requested audio mode is supported:", support
        self.afiqstream = self.audio.open( 
                    format=pa.paInt16,          # 16 bit samples
                    channels=2,                 # 2 channels
                    rate=self.opt.sample_rate,  # typ. 48000
                    frames_per_buffer= self.opt.buffers*opt.size,
                    input_device_index=af_using_index, # maybe the default device
                    input=True,                 # being used for input, not output
                    stream_callback=pa_callback_iqin )

        self.dataqueue = Queue.Queue(opt.max_queue) # needs to be "big enough"
        cbqueue = self.dataqueue
        return

    def Start(self):                            # Start pyaudio stream 
        self.afiqstream.start_stream()
        return

    def Stop(self):                             # Stop pyaudio stream
        self.afiqstream.stop_stream()
        return
        
    def Terminate(self):                        # Stop and release all resources
        self.afiqstream.stop_stream()
        self.afiqstream.close()
        self.audio.terminate()

if __name__ == '__main__':
    print 'debug'           # Insert module test code below

