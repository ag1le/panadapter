#!/usr/bin/env python

# Program iq_wf.py - Create waterfall spectrum display.
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

import pygame as pg
import numpy as np
import math, sys

def palette_color(palette, val, vmin0, vmax0):
    """ translate a data value into a color according to several different
        methods. (PALETTE variable)
        input: value of data, minimum value, maximum value for transform
        return: pygame color tuple
    """
    f = (float(val) - vmin0) / (vmax0 - vmin0)     # btw 0 and 1.0
    f *= 2
    f = min(1., max(0., f))
    if palette == 1:
        g, b = 0, 0
        if f < 0.333:
            r = int(f*255*3)
        elif f < 0.666:
            r = 200
            g = int((f-.333)*255*3)
        else:
            r = 200
            g = 200
            b = int((f-.666)*255*3)
    elif palette == 2:
        bright = min (1.0, f + 0.15)
        tpi = 2 * math.pi
        r = bright * 128 *(1.0 + math.cos(tpi*f))
        g = bright * 128 *(1.0 + math.cos(tpi*f + tpi/3))
        b = bright * 128 *(1.0 + math.cos(tpi*f + 2*tpi/3))
    else:
        print "Invalid palette requested!"
        sys.exit()
    return ( max(0,min(255,r)), max(0,min(255,g)), max(0,min(255,b)) )

class Wf(object):
    """ Make a waterfall '3d' display of spectral power vs frequency & time.
        init: min, max palette parameter, no. of steps between min & max,
        size for each freq,time data plot 'pixel' (a box)
    """
    def __init__(self, opt, vmin, vmax, nsteps, pxsz):
        """ Initialize data and
            pre-calculate palette & filled rect surfaces, based on vmin, vmax,
            no. of surfaces = nsteps
        """
        self.opt = opt
        self.vmin = vmin
        self.vmin_rst = vmin
        self.vmax = vmax
        self.vmax_rst = vmax
        self.nsteps = nsteps
        self.pixel_size = pxsz
        self.firstcalc = True
        self.initialize_palette()
        
    def initialize_palette(self):
        """ Set up surfaces for each possible color value in list self.pixels.
        """
        self.pixels = list()
        for istep in range(self.nsteps):
            ps = pg.Surface(self.pixel_size)
            val = float(istep)*(self.vmax-self.vmin)/self.nsteps + self.vmin
            color = palette_color(self.opt.waterfall_palette, val, self.vmin, self.vmax)
            ps.fill( color )
            self.pixels.append(ps)

    def set_range(self, vmin, vmax):
        """ define a new data range for palette calculation going forward.
            input: vmin, vmax
        """
        self.vmin = vmin
        self.vmax = vmax
        self.initialize_palette()

    def reset_range(self):
        """ reset palette data range to original settings.
        """
        self.vmin = self.vmin_rst
        self.vmax = self.vmax_rst
        self.initialize_palette()
        return self.vmin, self.vmax

    def calculate(self, datalist, nsum, surface):   # (datalist is np.array)
        if self.firstcalc:                          # First time through,
            self.datasize = len(datalist)           # pick up dimension of datalist
            self.wfacc = np.zeros(self.datasize)    # and establish accumulator
            self.dx = float(surface.get_width()) / self.datasize # x spacing of wf cells
            # Note: self.dx must be >= 1
            self.wfcount = 0
            self.firstcalc = False
        self.wfcount += 1
        self.wfacc += datalist              # Accumulate data
        if self.wfcount % nsum != 0:        # Don't plot wf data until enough spectra accumulated
            return
        else:
            surface.blit(surface, (0, self.pixel_size[1]))  # push old wf down one row
            for ix in xrange(self.datasize):
                v = datalist[ix] #self.wfacc[ix] / nsum #datalist[ix]        # dB units
                vi = int( self.nsteps * (v-self.vmin) / (self.vmax-self.vmin) )
                vi = max(0, min(vi, self.nsteps-1) )
                px_surf = self.pixels[vi]
                x = int(ix * self.dx)
                surface.blit(px_surf, (x, 0))
            self.wfcount = 0                        # Initialize counter
            self.wfacc.fill(0)                      #   and accumulator
