#!/usr/bin/env python

# Program iq_opt.py - Handle program options and command line parameters.
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

import optparse

# This module gets command-line options from the invocation of the main program,
# iq.py.

# Set up command line parser. (Use iq.py --help to see a formatted qlisting.)
op = optparse.OptionParser()

# Boolean options / modes.
op.add_option("--FULLSCREEN", action="store_true", dest="fullscreen",
    help="Switch to full screen display.")
op.add_option("--HAMLIB", action="store_true", dest="hamlib",
    help="use Hamlib to monitor/control rig frequency.")
op.add_option("--LAGFIX", action="store_true", dest="lagfix",
    help="Special mode to fix PCM290x R/L offset.")
op.add_option("--LCD4", action="store_true", dest="lcd4",
    help='Use 4" LCD instead of large screen')
op.add_option("--RPI", action="store_true", dest="device_rpi",
    help="Set up some defaults for Raspberry Pi")
op.add_option("--RTL", action="store_true", dest="source_rtl",
    help="Set source to RTL-SDR")
op.add_option("--WATERFALL", action="store_true", dest="waterfall",
    help="Use waterfall display.")

# Options with a parameter.
op.add_option("--cpu_load_intvl", action="store", type="float", dest="cpu_load_interval",
    help="Seconds delay between CPU load calculations")
op.add_option("--rate", action="store", type="int", dest="sample_rate",
    help="sample rate (Hz), eg 48000, 96000, or 1024000 or 2048000 (for rtl)")
op.add_option("--hamlib_device", action="store", type="string", dest="hamlib_device",
    help="Hamlib serial port.  Default /dev/ttyUSB0.")
op.add_option("--hamlib_intvl", action="store", type="float", dest="hamlib_interval",
    help="Seconds delay between Hamlib operations")
op.add_option("--hamlib_rig", action="store", type="int", dest="hamlib_rigtype",
    help="Hamlib rig type (int).  Run 'rigctl --list' for possibilities.  Default "
    "is 229 (Elecraft K3/KX3).")
op.add_option("--index", action="store", type="int", dest="index",
    help="index of audio input card. Use pa.py to examine choices.  Index -1 " \
        "selects default input device.")
op.add_option("--lcd4_brightness", action="store", type="int", dest="lcd4_brightness",
    help="LCD4 display brightness 0 - 100")
op.add_option("--max_queue", action="store", type="int", dest="max_queue",
    help="Real-time queue depth")
op.add_option("--n_buffers", action="store", type="int", dest="buffers",
    help="Number of FFT buffers in 'chunk', default 12")
op.add_option("--pulse_clip", action="store", type="int", dest="pulse",
    help="pulse clipping threshold, default 10.")
op.add_option("--rtl_freq", action="store", type="float", dest="rtl_frequency",
    help="Initial RTL operating frequency (float kHz)")
op.add_option("--rtl_gain", action="store", type="int", dest="rtl_gain",
    help="RTL_SDR gain, default 0.")
op.add_option("--size", action="store", type="int", dest="size",
    help="size of FFT.  Default is 512.")
op.add_option("--take", action="store", type="int", dest="taking",
    help="No. of buffers to take per chunk, must be <= buffers.")
op.add_option("--waterfall_acc", action="store", type="int", dest="waterfall_accumulation",
    help="No. of spectra per waterfall line")
op.add_option("--waterfall_palette", action="store", type="int", dest="waterfall_palette",
    help="Waterfall color palette (1 or 2)")

# The following are the default values which are used if not specified in the
# command line.  You may want to edit them to be close to your normal operating needs.
op.set_defaults(
        buffers                 = 12,       # no. buffers in sample chunk (RPi-40)
        cpu_load_interval       = 3.0,      # cycle time for CPU monitor thread
        device                  = None,     # Possibly "BBB" or "RPI" (set up appropriately)
        fullscreen              = False,    # Use full screen mode? (if not LCD4)
        hamlib                  = False,    # Using Hamlib? T/F (RPi-False)
        hamlib_device           = "/dev/ttyUSB0",   # Device address for Hamlib I/O
        hamlib_interval         = 1.0,      # Wait between hamlib freq. checks (secs)    
        hamlib_rigtype          = 229,      # Elecraft K3/KX3.
        index                   = -1,       # index of audio device (-1 use default)
        lagfix                  = False,    # Fix up PCM 290x bug
        lcd4                    = False,    # default large screen
        lcd4_brightness         = 75,       # brightness 0 - 100
        max_queue               = 30,       # max depth of queue from audio callback
        pulse                   = 10,       # pulse clip threshold
        rtl_frequency           = 146.e6,   # RTL center freq. Hz
        rtl_gain                = 0,        # auto
        sample_rate             = 48000,    # (stereo) frames/second (Hz) (RTL up to 2048000)
        size                    = 384,      # size of FFT --> freq. resolution (RPi-256)
        source_rtl              = False,    # Use sound card, not RTL-SDR input
        taking                  = -1,       # 0 < taking < buffers to cut cpu load, -1=all
        waterfall               = False,    # Using waterfall? T/F
        waterfall_accumulation  = 4,        # No. of spectra per waterfall line
        waterfall_palette       = 2         # choose a waterfall color scheme
        )

opt, args = op.parse_args()

# This is an "option" that the user can't change.
opt.ident = "IQ.PY v. 0.30 de AA6E"

# --RTL option forces source=rtl, but normally source=audio
opt.source = "rtl" if opt.source_rtl else "audio"

if opt.device_rpi:
    # adjust to comfortable settings for Raspberry Pi
    opt.buffers = 15
    opt.taking = 4      # reduce CPU load (to 4/15 of max.)
    opt.size = 256

# Main module will use: options.opt to pick up this 'opt' instance.

if __name__ == '__main__':
    print 'debug'
    # Print the variables in opt.  Opt is a weird thing, not a dictionary.
    #print dir(opt)
    for x in dir(opt):
        if x[0] != "_" and x.find("read_") < 0 and x != "ensure_value":
            y = eval("opt."+x)
            print x, "=", y, type(y)

