#!/usr/bin/env python

# Program iq_dsp.py - Compute spectrum from I/Q data.
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
# 01-04-2014 Initial Release

import math, time
import numpy as np
import numpy.fft as fft

class DSP(object):
    def __init__(self, opt):
        self.opt = opt
        self.stats = list()
        # This is dB output for full scale 16bit input = max signal.
        self.db_adjust = 20. * math.log10(self.opt.size * 2**15)
        self.rejected_count = 0
        self.led_clip_ct = 0
        # Use "Hanning" window function
        self.w = np.empty(self.opt.size)
        for i in range(self.opt.size):
            self.w[i] = 0.5 * (1. - math.cos((2*math.pi*i)/(self.opt.size-1)))
        return

    def GetLogPowerSpectrum(self, data):
        size = self.opt.size            # size of FFT in I,Q samples.
        power_spectrum = np.zeros(size)

        # Time-domain analysis: Often we have long normal signals interrupted
        # by huge wide-band pulses that degrade our power spectrum average.
        # We find the "normal" signal level, by computing the median of the 
        # absolute value.  We only do this for the first buffer of a chunk,
        # using the median for the remaining buffers in the chunk. 
        # A "noise pulse" is a signal level greater than some threshold
        # times the median.  When such a pulse is found, we skip the current
        # buffer.  It would be better to blank out just the pulse, but that
        # would be more costly in CPU time.

        # Find the median abs value of first buffer to use for this chunk.
        td_median = np.median(np.abs(data[:size]))
        # Calculate our current threshold relative to measured median.
        td_threshold = self.opt.pulse * td_median
        nbuf_taken = 0          # Actual number of buffers accumulated
        for ic in range(self.opt.buffers):
            td_segment = data[ic*size:(ic+1)*size]
            td_max = np.amax(np.abs(td_segment))    # Do we have a noise pulse?
            if td_max < td_threshold:               # No, get pwr spectrum etc.
                # EXPERIMENTAL TAPER
                td_segment *= self.w
                fd_spectrum = fft.fft(td_segment)
                # Frequency-domain:
                # Rotate array to place 0 freq. in center.  (It was at left.)
                fd_spectrum_rot = np.fft.fftshift(fd_spectrum)
                # Compute the real-valued squared magnitude (ie power) and 
                # accumulate into pwr_acc.
                # fastest way to sum |z|**2 ??
                nbuf_taken += 1
                power_spectrum = power_spectrum + \
                        np.real(fd_spectrum_rot*fd_spectrum_rot.conj())
            else:                                   # Yes, abort buffer.
                self.rejected_count += 1
                self.led_clip_ct = 1       # flash a red light
                #if DEBUG: print "REJECT! %d" % self.rejected_count
        if nbuf_taken > 0:
            power_spectrum = power_spectrum / nbuf_taken     # normalize the sum.
        else:
            power_spectrum = np.ones(size)             # if no good buffers!
        # Convert to dB. Note log(0) = "-inf" in Numpy. It can happen if ADC 
        # isn't working right. Numpy issues a warning.
        log_power_spectrum = 10. * np.log10(power_spectrum)
        return log_power_spectrum - self.db_adjust  # max poss. signal = 0 dB

