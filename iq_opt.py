#!/usr/bin/env python

# Program iq_opt.py - Handle program options and command line parameters.
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

# HISTORY
# 01-04-2014 Initial release
# 05-05-2014 Changed options
# 05-31-2014 Si570 control (vs RTL control vs None [af])

import optparse

# This module handles command-line options.

# Note options changed:  
# Add "skip", "REV", remove "RPI", "taking", "max_queue"
# Add --SI570

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
op.add_option("--RTL", action="store_true", dest="source_rtl",
    help="Set source to RTL-SDR")
op.add_option("--SI570", action="store_true", dest="control_si570",
    help="Set freq control to Si570, not RTL or Hamlib")
op.add_option("--REV", action="store_true", dest="rev_iq",
    help="Reverse I & Q to reverse spectrum display")
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
op.add_option("--n_buffers", action="store", type="int", dest="buffers",
    help="Number of FFT buffers in 'chunk', default 12")
op.add_option("--pulse_clip", action="store", type="int", dest="pulse",
    help="pulse clipping threshold, default 10.")
op.add_option("--rtl_freq", action="store", type="float", dest="rtl_frequency",
    help="Initial RTL operating frequency (float kHz)")
op.add_option("--rtl_gain", action="store", type="int", dest="rtl_gain",
    help="RTL_SDR gain, default 0.")
op.add_option("--si570_frequency", action="store", type="float", dest="si570_frequency",
    help="Si570 LO initial frequency, (float kHz)")
op.add_option("--size", action="store", type="int", dest="size",
    help="size of FFT.  Default is 512.")
op.add_option("--skip", action="store", type="int", dest="skip",
    help="Skipping input data parameter >= 0")
op.add_option("--sp_min", action="store", type="int", dest="sp_min",
    help="spectrum level, low end, dB")
op.add_option("--sp_max", action="store", type="int", dest="sp_max",
    help="spectrum level, hi end, dB")
op.add_option("--v_min", action="store", type="int", dest="v_min",
    help="palette level, low end, dB")
op.add_option("--v_max", action="store", type="int", dest="v_max",
    help="palette level, hi end, dB")

op.add_option("--waterfall_acc", action="store", type="int", dest="waterfall_accumulation",
    help="No. of spectra per waterfall line")
op.add_option("--waterfall_palette", action="store", type="int", dest="waterfall_palette",
    help="Waterfall color palette (1 or 2)")

# The following are the default values which are used if not specified in the
# command line.  You may want to edit them to be close to your normal operating needs.
DEF_SAMPLE_RATE = 48000
op.set_defaults(
    buffers                 = 12,       # no. buffers in sample chunk (RPi-40)
    control_si570           = False,    # normally, talk to RTL or Hamlib for freq info
    cpu_load_interval       = 3.0,      # cycle time for CPU monitor thread
    fullscreen              = False,    # Use full screen mode? (if not LCD4)
    hamlib                  = False,    # Using Hamlib? T/F (RPi-False)
    hamlib_device           = "/dev/ttyUSB0",   # Device address for Hamlib I/O
    hamlib_interval         = 1.0,      # Wait between hamlib freq. checks (secs)    
    hamlib_rigtype          = 229,      # Elecraft K3/KX3.
    index                   = -1,       # index of audio device (-1 use default)
    lagfix                  = False,    # Fix up PCM 290x bug
    lcd4                    = False,    # default large screen
    lcd4_brightness         = 75,       # brightness 0 - 100
    pulse                   = 10,       # pulse clip threshold
    rev_iq                  = False,    # Reverse I & Q
    rtl_frequency           = 146.e6,   # RTL center freq. Hz
    rtl_gain                = 0,        # auto
    sample_rate             = DEF_SAMPLE_RATE,    # (stereo) frames/second (Hz)
    si570_frequency         = 7050.0,   # initial freq. for Si570 LO.
    size                    = 384,      # size of FFT --> freq. resolution
    skip                    = 0,        # if not =0, skip some input data
    source_rtl              = False,    # Use sound card, not RTL-SDR input
    sp_min                  =-120,      # dB relative to clipping, at bottom of grid
    sp_max                  =-20,       # dB relative to clipping, at top of grid
    v_min                   =-120,      # palette starts at this level
    v_max                   =-20,       # palette ends at this level
    waterfall               = False,    # Using waterfall? T/F
    waterfall_accumulation  = 4,        # No. of spectra per waterfall line
    waterfall_palette       = 2         # choose a waterfall color scheme
    )

opt, args = op.parse_args()

# This is an "option" that the user can't change.
opt.ident = "IQ.PY v. 0.3.6 de AA6E"

# 'source' refers to signal source (RTL or audio sound card)
# 'control' refers to freq. readout/control (RTL, si570, or none)

opt.control = "none"
if opt.hamlib:
    opt.control = "hamlib"
if opt.source_rtl:
    opt.source = "rtl"
    opt.control= "rtl"
else:
    opt.source = "audio"
    if opt.control_si570:
        opt.control = "si570"

# Change default Freq for RTL to an appropriate (legal) value (tnx KF3EB)
# However, do not override user's --rate setting, if present.
if opt.source_rtl and (opt.sample_rate == DEF_SAMPLE_RATE):
    opt.sample_rate = 1024000

# Main module will use: options.opt to pick up this 'opt' instance.

if __name__ == '__main__':
    print 'debug'

