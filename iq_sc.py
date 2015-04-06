#!/usr/bin/env python

# Program iq_sc.py - Create scope display.
# Copyright (C) 2015 Mauri Niininen
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
# Contact the author by e-mail: ag1le@arrl.net
#
# Part of the iq.py program.

# HISTORY
# 04-05-2015 Initial release

import pygame as pg
import numpy as np
import matplotlib.pyplot as plt
import math, sys
import scipy.signal.signaltools as ss
from scipy.signal import butter, filtfilt


GREEN =    (  0, 255,   0)

class Sc(object):
    """ Make a scope display of selected signal vs time.
        init: 
    """
    def __init__(self,Fs):
        """ Initialize 
        """
        self.Fs = Fs
        self.Wn = 1000./ (Fs/2.)  	# 25 Hz cut-off for lowpass  
        self.b,self.a = butter(5, self.Wn,'lowpass')  	# 2nd order butter filter
        self.firstcalc = True

    def demodulate(self,x,freq):
        # demodulate audio signal with known CW frequency 
        #t = np.arange(len(x))/ float(self.Fs)
        #y =  x*((1 + np.sin(2*np.pi*freq*t))/2 )	
        
        #calculate envelope and low pass filter this demodulated signal
        #filter bandwidth impacts decoding accuracy significantly 
        #for high SNR signals 50 Hz is better, for low SNR 20Hz is better
        # 25Hz is a compromise - could this be made an adaptive value? 

        z = filtfilt(self.b, self.a, x) #abs(y))
        return z

    def calculate(self, datalist, surface, freq):         # (datalist is np.array)
        """ calculate and plot datalist envelope on scope display surface
        """
        if self.firstcalc:                          # First time through,
            self.datasize = len(datalist)           # pick up dimension of datalist
            self.width = surface.get_width()
            self.height = surface.get_height()
            self.firstcalc = False
        # envelope of time domain signal
        env = np.abs(datalist) #np.abs(ss.hilbert(datalist))

        #env = filtfilt(self.b,self.a,np.abs(datalist))
        #env2 = self.demodulate(env,freq)
        #magn = np.absolute(datalist)
        maxn = np.max(env)
        avg  = np.mean(env)
        
        xlist = [x for x in xrange(self.width)]
        ylist = self.height/2-((env - avg)/maxn)*self.height 
        
        #plt.plot(ylist)
        #plt.show()
        pg.draw.lines(surface, GREEN, False, zip(xlist,ylist), 1)
        
