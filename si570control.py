#!/usr/bin/env python

# Si570control class gives python access to the Si570 Digital
# Sythesizer via a USB connection.
# Copyright (C) 2014 Martin Ewing
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

# This is "middleware" that defines an API for general user programming
# of radio systems using the Si570 Programmable VCXO as an inexpensive
# digital VFO.  These routines connect via USB to an ATtiny45 USB-to-I2C
# device, which is running the usbavrsi570 code from PE0FKO.

# Tested on SoftRock RxTx Ensemble that uses the ATtiny85 MPU chip and a
# SiLabs 570 ("CAC000141G / D1HOS144") chip
# [3.3v CMOS, 61 ppm stab., 10-160 MHz]

# partially based on a subset of operations.c from Andrew Nilsson VK6JBL
# Also, see http://www.silabs.com/Support%20Documents/TechnicalDocs/si570.pdf
# and https://code.google.com/p/usbavrsi570/

# require libusb-1.0 wrapper from https://pypi.python.org/pypi/libusb1/1.2.0
import libusb1, usb1

import math, sys
from sidefs import *

# flags used for most usb i/o
#input
UFLGS1 = libusb1.LIBUSB_TYPE_VENDOR | \
            libusb1.LIBUSB_RECIPIENT_DEVICE | \
            libusb1.LIBUSB_ENDPOINT_IN
#output
UFLGS2 = libusb1.LIBUSB_TYPE_VENDOR | \
            libusb1.LIBUSB_RECIPIENT_DEVICE | \
            libusb1.LIBUSB_ENDPOINT_OUT

# Note changes from operation.c:
#       1. method names have changed to make them more regular.
#       2. get/set freq always work with floating MHz of signal frequency =
#           osc frequency / multiplier.

class Si570control(object):
    def __init__(self, verbose=0, fXtal=114.285, multiplier=4, i2c=0x55, 
                    vendor_id=0x16c0, product_id=0x05dc):
        self.verbose = verbose
        self.fXtal = fXtal
        self.multiplier = multiplier
        self.i2c = i2c
        self.context = usb1.USBContext()
        self.device = self.context.getByVendorIDAndProductID(vendor_id, product_id)
        if self.verbose:
            print "device", self.device
        self.handle = self.device.open()
        self.version = self.getVersion()

    # get version numbers
    def getVersion(self):
        bb = bytearray(self.handle.controlRead
                (UFLGS1,REQUEST_READ_VERSION, 0x0E00, 0, 2, 500))
        if len(bb)==2:
            ver = "%d.%d" % (bb[1], bb[0])
            if self.verbose:
                print "Version", ver
            return ver
        else:
            if self.verbose:
                print "Version Unknown."
            return None

    def enum_devices(self):
        mydevices = self.context.getDeviceList()
        print "n=",len(mydevices)
        for i,x in enumerate(mydevices):
            print "%2d %2d %d %3d %d %d %0.4x %0.4x" % (i, 
                            x.getBusNumber(),
                            x.getDeviceAddress(),
                            x.getDeviceClass(),
                            x.getDeviceProtocol(),
                            x.getDeviceSpeed(),
                            x.getVendorID(),
                            x.getProductID() )

    def getFreqByValue(self):   # return osc freq / multiplier
        bb = bytearray( self.handle.controlRead
                (UFLGS1, REQUEST_READ_FREQUENCY, 0, 0, 4, 500) )
        fint = ((bb[3] << 8 | bb[2]) << 8 | bb[1] ) << 8 | bb[0]
        if len(bb) == 4:
            ans = (float(fint)/(1<<21)) / self.multiplier
            return ans
        else:
            return None

    def getRegisters(self):
        bb = bytearray( self.handle.controlRead
                (UFLGS1, REQUEST_READ_REGISTERS, SI570_I2C_ADDR, 0, 6, 5000) )
        if len(bb) > 0:
            for i in range(6):
                print "Register %d = %X (%d)" % ( i+7, bb[i], bb[i] )

    def calculateFreq(self, s): # s is string, could be bytearray?
        si = bytearray(s)
        RFREQ_int = ((si[2] & 0xf0) >> 4) + ((si[1] & 0x3f) * 16)
        RFREQ_frac = ((si[2] & 0xf ) << 24) + (si[3] << 16) + (si[4] << 8) + si[5]
        RFREQ = RFREQ_int + (float(RFREQ_frac) / 268435456.0)
        N1 = ((si[1] & 0xc0 ) >> 6) + ((si[0] & 0x1f) << 2)
        HS_DIV = (si[0] & 0xE0) >> 5
        fout = self.fXtal * RFREQ / ((N1 + 1) * HS_DIV_MAP[HS_DIV])
        if self.verbose >= 2:
            print "RFREQ = %f" % RFREQ
            print "N1 = %d" % N1
            print "HS_DIV = %d" % HS_DIV
            print "nHS_DIV = %d" % HS_DIV_MAP[HS_DIV]
            print "fout = %f" % fout
        return fout         # actual osc freq.
        
    def getFreq(self):      # return osc freq / multiplier
        strg = self.handle.controlRead \
                (UFLGS1, REQUEST_READ_REGISTERS, SI570_I2C_ADDR, 0, 6, 5000)
        # keep strg for calculateFrequency, avoiding unicode issues.
        bb = bytearray( strg )
        if len(bb) > 0:
            if self.verbose >= 2:
                for i in range(6):
                    print "Register %d = %X (%d)" % ( i+7, bb[i], bb[i] )
            return self.calculateFreq(strg) / self.multiplier
        else:
            return None

    def getPTT(self):
        bb = bytearray( self.handle.controlRead
                (UFLGS1, REQUEST_READ_KEYS, 0, 0, 1, 5000) )
        if bb[0] & 0x40:
            return 1
        else:
            return 0

    def getKeys(self):
        bb = bytearray( self.handle.controlRead
                (UFLGS1, REQUEST_READ_KEYS, 0, 0, 1, 5000) )
        if bb[0] & 0x20:     # CW_KEY_1   high: not pressed   low: pressed
            keys = 0
        else:
            keys = 1
        if not (bb[0] & 0x02):
            keys += 2               # CW_KEY_2   high: not pressed   low: pressed
        return keys                 # keys = 3 if both pressed

    def setPTT(self, value):
        bb = bytearray( self.handle.controlRead
                (UFLGS1, REQUEST_SET_PTT, value, 0, 3, 5000) )
        if self.verbose >= 2:
            print "buffer=",bb[0],bb[1],bb[2]

    def calcDividers(self, f): # Returns solution = [HS_DIV, N1, f0, RFREQ]
        # Instead of solution structure, use simple list for each variable.
        cHS_DIV = list()
        cN1 = list()
        cf0 = list()
        cRFREQ = list()
        for i in range(7,-1,-1):    # Count down through the dividers
            if HS_DIV_MAP[i] > 0:
                cHS_DIV.append(i)
                y = (SI570_DCO_HIGH + SI570_DCO_LOW) / (2 * f)
                y = y / HS_DIV_MAP[i]
                if y < 1.5:
                    y = 1.0
                else:
                    y = 2 * round(y/2.0)
                if y > 128:
                    y = 128
                cN1.append( math.trunc(y) - 1 )
                cf0.append( f * y * HS_DIV_MAP[i] )
            else:
                cHS_DIV.append(None)    # dummy result
                cN1.append(None)        # another dummy
                cf0.append( 1.0E16 )
        imin = -1
        fmin = 1.0E16
        for i in range(8):
            if (cf0[i] >= SI570_DCO_LOW) & (cf0[i] <= SI570_DCO_HIGH) :
                if cf0[i] < fmin:
                    fmin = cf0[i]
                    imin = i
        if imin >= 0:
            solution = [ cHS_DIV[imin], cN1[imin], cf0[imin], cf0[imin]/self.fXtal ]
            if (self.verbose >= 2):
                print "Solution:"
                print "  HS_DIV = %d" % solution[0]
                print "  N1 = %d" % solution[1]
                print "  f0 = %f" % solution[2]
                print "  RFREQ = %f" % solution[3]
        else:
            solution = None     # This is the error return
        return solution

    def setLongWord(self, v ):           # v = int value; return bytearray(4)
        iv = int(v)                 # be sure of int type
        b = bytearray(4)
        b[0] = iv & 0xff
        b[1] = ((iv & 0xff00) >> 8) & 0xff
        b[2] = ((iv & 0xff0000) >> 16) & 0xff
        b[3] = ((iv & 0xff000000) >> 24) & 0xff
        return b                    # NB bytearray, not long word!

    def setFreq(self, frequency):
        f = self.multiplier * frequency
        value = 0x700 + self.i2c
        index = 0
        if self.verbose:
            print "Setting Si570 Frequency by registers to: %f" % f
        sHS_DIV, sN1, sf0, sRFREQ = self.calcDividers(f)
        RFREQ_int = math.trunc(sRFREQ)
        RFREQ_frac= int( round((sRFREQ - RFREQ_int) * 268435456) ) # check int ok
        intbuf  = self.setLongWord( RFREQ_int )
        fracbuf = self.setLongWord( RFREQ_frac)
        outbuf = bytearray(6)
        outbuf[5] = fracbuf[0]
        outbuf[4] = fracbuf[1]
        outbuf[3] = fracbuf[2]
        outbuf[2] = fracbuf[3]      | ((intbuf[0] & 0xf) << 4)
        outbuf[1] = RFREQ_int / 16  + ((sN1 & 0x3) << 6)
        outbuf[0] = sN1/4           + (sHS_DIV << 5)
        sout = str()
        for x in outbuf:
            sout += chr(x)
        r = self.handle.controlWrite \
                (UFLGS2, REQUEST_SET_FREQ, value, index, sout, 5000)
        if r:
            if self.verbose >= 2:
                print "Set Freq Buffer",
                print "%x %x" % (outbuf[0], outbuf[1])
        else:
            print "Failed writing frequency to device"

    def setFreqByValue(self, frequency):
        f = self.multiplier * frequency
        value = 0x700 + self.i2c
        index = 0
        buf = self.setLongWord(round(f * 2097152.0))
        if self.verbose:
            print "Setting Si570 Frequency by value to: %f" % f
            if self.verbose >= 2:
                print "Set Freq Buffer: %x %x %x %x" % (buf[0], buf[1], 
                        buf[2], buf[3])
        sout = str()
        for x in buf:
            sout += chr(x)
        r = self.handle.controlWrite \
                (UFLGS2, REQUEST_SET_FREQ_BY_VALUE, value, index, sout, 5000)
        if r:
            if self.verbose >= 2:
                print "Set Freq Buffer: %x %x %x %x" % (buf[0], buf[1], 
                        buf[2], buf[3])
        else:
            print "Failed setting frequency"
# End of Si570 class

if __name__ == "__main__":
    # debug code goes here
    si = Si570control(verbose=0)
    freq = si.getFreqByValue()
    print "freq by value", freq
    #si.getRegisters()

    #f = si.getFreq()
    #print "returned freq", f

    #si.setFreq( 1.8)
    #print "set freq check"
    #si.getFreq()

    print "SET FREQ BY VALUE"
    si.setFreqByValue(7.5)
    print "checking"
    print si.getFreqByValue()

    if False:
        print "Calc. dividers [HS_DIV, N1, f0, RFREQ]"
        a = si.calcDividers(28.0)
        print a
    print "Done."

