#!/usr/bin/env python

# Program iq_rtl.py - Manage input from RTL_SDR dongle.
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

import rtlsdr

class RTL_In(object):
    def __init__(self, opt):
        self.opt = opt
        self.rtl = rtlsdr.RtlSdr()
        # Set up rtl-sdr dongle with options from command line.
        self.rtl.sample_rate = opt.sample_rate
        self.rtl.center_freq = opt.rtl_frequency
        self.rtl.set_gain(opt.rtl_gain)
        return
    
    def ReadSamples(self,size):
        return  self.rtl.read_samples(size)

if __name__ == '__main__':
    print "Debug"

