#!/usr/bin/env python

# Program iq_af.py - manage I/Q audio from soundcard using pyaudio
# Copyright (C) 2013-2014 Martin Ewing
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

# HISTORY
# 01-04-2014 Initial release (QST article)
# 05-17-2014 timing improvements, esp for Raspberry Pi, etc.
#    implement 'skip'

import sys, time, threading
import Queue
import pyaudio as pa

# CALLBACK ROUTINE
# pyaudio callback routine is called when in_data buffer is ready.
# See pyaudio and portaudio documentation for details.
# Callback may not be called at a uniform rate.

# "skip = N" means "discard every (N+1)th buffer" (N > 0) or
#   "only use every (-N+1)th buffer" (N < 0)
# i.e. skip=2 -> discard every 3rd buffer; 
#       skip=-2 -> use every 3rd buffer.
# (skip=1 and skip=-1 have same effect!)
# skip=0 means take all data.

# Global variables (in this module's namespace!)
# globals are required to communicate with callback thread.
led_underrun_ct = 0             # buffer underrun LED 
cbcount = 0
MAXQUEUELEN = 32                # Don't use iq-opt for this?
cbqueue = Queue.Queue(MAXQUEUELEN)  # will be queue to transmit af data
cbskip_ct = 0
queueLock = threading.Lock()    # protect queue accesses
cbfirst = 1                     # Skip this many buffers at start
def pa_callback_iqin(in_data, f_c, time_info, status):
    global cbcount, cbqueue, cbskip, cbskip_ct
    global led_underrun_ct, queueLock, cbfirst
    
    cbcount += 1

    if status == pa.paInputOverflow:
        led_underrun_ct = 1         # signal LED "underrun" (really, overflow)
    # Decide if we should skip this buffer or take it.
    # First, are we dropping every Nth buffer?
    if cbskip > 0:                  # Yes, we must check cbskip_ct
        if cbskip_ct >= cbskip:
            cbskip_ct = 0
            return (None, pa.paContinue)    # Discard this buffer
        else:
            cbskip_ct += 1                  # OK to process buffer
    # Or, are we accepting every Nth buffer?
    if cbskip < 0:
        if cbskip_ct >= -cbskip:
            cbskip_ct = 0                   # OK to process buffer
        else:
            cbskip_ct += 1
            return (None, pa.paContinue)    # Discard this buffer
    # Having decided to take the current buffer, or cbskip==0, 
    #    send it to main thread.
    if cbfirst > 0:
        cbfirst -= 1
        return (None, pa.paContinue)    # Toss out first N data
    try:
        queueLock.acquire()
        cbqueue.put_nowait(in_data)     # queue should sync with main thread
        queueLock.release()
    except Queue.Full:
        print "ERROR: Internal queue is filled.  Reconfigure to use less CPU."
        print "\n\n (Ignore remaining errors!)"
        sys.exit()
    return (None, pa.paContinue)    # Return to pyaudio.  All OK.
# END OF CALLBACK ROUTINE

class DataInput(object):
    """ Set up audio input with callbacks.
    """
    def __init__(self, opt=None):

        # Initialize pyaudio (A python mapping of PortAudio) 
        # Consult pyaudio documentation.
        self.audio = pa.PyAudio()   # generates lots of warnings.
        print
        self.Restart(opt)
        return
        
    def Restart(self, opt):         # Maybe restart after error?
        global cbqueue, cbskip

        cbskip = opt.skip
        print
        # set up stereo / 48K IQ input channel.  Stream will be started.
        if opt.index < 0:       # Find pyaudio's idea of default index
            defdevinfo = self.audio.get_default_input_device_info()
            print "Default device index is %d; id='%s'"% \
                    (defdevinfo['index'], defdevinfo['name'])
            af_using_index = defdevinfo['index']
        else:
            af_using_index = opt.index              # Use user's choice of index
            devinfo = self.audio.get_device_info_by_index(af_using_index)
            print "Using device index %d; id='%s'" % \
                    (devinfo['index'], devinfo['name'])
        try:
            # Verify this is a supported mode.
            support = self.audio.is_format_supported(
                    input_format=pa.paInt16,        # 16 bit samples
                    input_channels=2,               # 2 channels
                    rate=opt.sample_rate,           # typ. 48000
                    input_device=af_using_index)
        except ValueError as e:
            print "ERROR self.audio.is_format_supported", e
            sys.exit()
        print "Requested audio mode is supported:", support
        self.afiqstream = self.audio.open( 
                    format=pa.paInt16,          # 16 bit samples
                    channels=2,                 # 2 channels
                    rate=opt.sample_rate,       # typ. 48000
                    frames_per_buffer= opt.buffers * opt.size,
                    input_device_index=af_using_index,
                    input=True,                 # being used for input only
                    stream_callback=pa_callback_iqin )
        return

    def get_queued_data(self):
        timeout = 40
        while cbqueue.qsize() < 4:
            timeout -= 1
            if timeout <= 0: 
                print "timeout waiting for queue to become non-empty!"
                sys.exit()
            time.sleep(.1)
        queueLock.acquire()
        data = cbqueue.get(True, 4.)    # Why addnl timeout set?
        queueLock.release()
        return data

    def CPU_load(self):
        load = self.afiqstream.get_cpu_load()
        return load

    def isActive(self):
        return self.afiqstream.is_active()
        
    def Start(self):                            # Start pyaudio stream 
        self.afiqstream.start_stream()

    def Stop(self):                             # Stop pyaudio stream
        self.afiqstream.stop_stream()
    
    def CloseStream(self):
        self.afiqstream.stop_stream()
        self.afiqstream.close()

    def Terminate(self):                        # Stop and release all resources
        self.audio.terminate()

if __name__ == '__main__':
    print 'debug'           # Insert module test code below

