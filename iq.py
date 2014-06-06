#!/usr/bin/env python

# Program iq.py - spectrum displays from quadrature sampled IF data.
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
# Our goal is to display a zero-centered spectrum and waterfall on small
# computers, such as the BeagleBone Black or the Raspberry Pi, 
# spanning up to +/- 48 kHz (96 kHz sampling) with input from audio card
# or +/- 1.024 MHz from RTL dongle. 
#
# We use pyaudio, pygame, and pyrtlsdr Python libraries, which depend on
# underlying C/C++ libraries PortAudio, SDL, and rtl-sdr.
#

# HISTORY
# 01-04-2014 Initial release (QST article 4/2014)
# 05-17-2014 Improvements for RPi timing, etc.
#            Add REV, skip, sp_max/min, v_max/min options
# 05-31-2014 Add Si570 freq control option (DDS chip provided in SoftRock, eg.)
#           Note: Use of Si570 requires libusb-1.0 wrapper from 
#           https://pypi.python.org/pypi/libusb1/1.2.0

# Note for directfb use (i.e. without X11/Xorg):
# User must be a member of the following Linux groups:
#   adm dialout audio video input (plus user's own group, e.g., pi)

import sys,time, threading, os, subprocess
import pygame as pg
import numpy  as np
import iq_dsp as dsp
import iq_wf  as wf
import iq_opt as options

# Some colors in PyGame style
BLACK =    (  0,   0,   0)
WHITE =    (255, 255, 255)
GREEN =    (  0, 255,   0)
BLUE =     (  0,   0, 255)
RED =      (255,   0,   0)
YELLOW =   (192, 192,   0)
DARK_RED = (128,   0,   0)
LITE_RED = (255, 100, 100)
BGCOLOR =  (255, 230, 200)
BLUE_GRAY= (100, 100, 180)
ORANGE =   (255, 150,   0)
GRAY =     (192, 192, 192)
# RGBA colors - with alpha
TRANS_YELLOW = (255,255,0,150)

# Adjust for best graticule color depending on display gamma, resolution, etc.
GRAT_COLOR = DARK_RED       # Color of graticule (grid)
GRAT_COLOR_2 = WHITE        # Color of graticule text
TRANS_OVERLAY = TRANS_YELLOW    # for info overlay
TCOLOR2 = ORANGE              # text color on info screen

INFO_CYCLE = 8      # Display frames per help info update

opt = options.opt   # Get option object from options module


# print list of parameters to console.
print "identification:", opt.ident
print "source        :", opt.source
print "freq control  :", opt.control
print "waterfall     :", opt.waterfall
print "rev i/q       :", opt.rev_iq
print "sample rate   :", opt.sample_rate
print "size          :", opt.size
print "buffers       :", opt.buffers
print "skipping      :", opt.skip
print "hamlib        :", opt.hamlib
print "hamlib rigtype:", opt.hamlib_rigtype
print "hamlib device :", opt.hamlib_device
if opt.source=="rtl":
    print "rtl frequency :", opt.rtl_frequency
    print "rtl gain      :", opt.rtl_gain
if opt.control=="si570":
    print "si570 frequency :", opt.si570_frequency
print "pulse         :", opt.pulse
print "fullscreen    :", opt.fullscreen
print "hamlib intvl  :", opt.hamlib_interval
print "cpu load intvl:", opt.cpu_load_interval
print "wf accum.     :", opt.waterfall_accumulation
print "wf palette    :", opt.waterfall_palette
print "sp_min, max   :", opt.sp_min, opt.sp_max
print "v_min, max    :", opt.v_min, opt.v_max
#print "max queue dept:", opt.max_queue
print "PCM290x lagfix:", opt.lagfix
if opt.lcd4:
    print "LCD4 brightnes:", opt.lcd4_brightness

def quit_all():
    """ Quit pygames and close std outputs somewhat gracefully.
        Minimize console error messages.
    """
    pg.quit()
    try:
        sys.stdout.close()
    except:
        pass
    try:
        sys.stderr.close()
    except:
        pass
    sys.exit()

class LED(object):
    """ Make an LED indicator surface in pygame environment. 
        Does not include title
    """
    def __init__(self, width):
        """ width = pixels width (& height)
            colors = dictionary with color_values and PyGame Color specs
        """
        self.surface = pg.Surface((width, width))
        self.wd2 = width/2
        return

    def get_LED_surface(self, color):
        """ Set LED surface to requested color
            Return square surface ready to blit
        """
        self.surface.fill(BGCOLOR)
        # Always make full-size black circle with no fill.
        pg.draw.circle(self.surface,BLACK,(self.wd2,self.wd2),self.wd2,2)
        if color == None:
            return self.surface
        # Make inset filled color circle.
        pg.draw.circle(self.surface,color,(self.wd2,self.wd2),self.wd2-2,0)
        return self.surface

class Graticule(object):
    """ Create a pygame surface with freq / power (dB) grid
        and units.
        input: options, pg font, graticule height, width, line color, 
            and text color
    """
    def __init__(self, opt, font, h, w, color_l, color_t):
        self.opt = opt
        self.sp_max = opt.sp_max #-20   # default max value (dB)
        self.sp_min = opt.sp_min #-120  # default min value
        self.font = font    # font to use for text
        self.h = h          # height of graph area
        self.w = w          # width
        self.color_l = color_l    # color for lines
        self.color_t = color_t    # color for text
        self.surface = pg.Surface((self.w, self.h))
        return
        
    def make(self):
        """ Make or re-make the graticule.
            Returns pygame surface
        """
        self.surface.fill(BLACK)
        # yscale is screen units per dB
        yscale = float(self.h)/(self.sp_max-self.sp_min)
        # Define vertical dB scale - draw line each 10 dB.
        for attn in range(self.sp_min, self.sp_max, 10):
            yattn = ((attn - self.sp_min) * yscale) + 3.
            yattnflip = self.h - yattn    # screen y coord increases downward
            # Draw a single line, dark red.
            pg.draw.line(self.surface, self.color_l, (0, yattnflip), 
                                        (self.w, yattnflip))
            # Render and blit the dB value at left, just above line
            self.surface.blit(self.font.render("%3d" % attn, 1, self.color_t), 
                                        (5, yattnflip-12))

        # add unit (dB) to topmost label        
        ww, hh = self.font.size("%3d" % attn)
        self.surface.blit(self.font.render("dB",  1, self.color_t), 
                                        (5+ww, yattnflip-12))

        # Define freq. scale - draw vert. line at convenient intervals
        frq_range = float(self.opt.sample_rate)/1000.    # kHz total bandwidth
        xscale = self.w/frq_range               # pixels/kHz x direction
        srate2 = frq_range/2                    # plus or minus kHz
        # Choose the best tick that will work with RTL or sound cards.
        for xtick_max in [ 800, 400, 200, 100, 80, 40, 20, 10 ]:
            if xtick_max < srate2:
                break
        ticks = [ -xtick_max, -xtick_max/2, 0, xtick_max/2, xtick_max ]
        for offset in ticks:
            x = offset*xscale + self.w/2
            pg.draw.line(self.surface, self.color_l, (x, 0), (x, self.h))
            fmt = "%d kHz" if offset == 0 else "%+3d"
            self.surface.blit(self.font.render(fmt % offset, 1, self.color_t), 
                                        (x+2, 0))
        return self.surface
        
    def set_range(self, sp_min, sp_max):
        """ Set desired range for vertical scale in dB, min. and max.
            0 dB is maximum theoretical response for 16 bit sampling.
            Lines are always drawn at 10 dB intervals.
        """
        if not sp_max > sp_min:
            print "Invalid dB scale setting requested!"
            quit_all()
        self.sp_max = sp_max
        self.sp_min = sp_min
        return

# THREAD: Hamlib, checking Rx frequency, and changing if requested.
if opt.hamlib:
    import Hamlib
    rigfreq_request = None
    rigfreq = 7.0e6             # something reasonable to start
    def updatefreq(interval, rig):
        """ Read/set rig frequency via Hamlib.
            Interval defines repetition time (float secs)
            Return via global variable rigfreq (float kHz)
            To be run as thread.
            (All Hamlib I/O is done through this thread.)
        """
        global rigfreq, rigfreq_request
        rigfreq = float(rig.get_freq()) * 0.001     # freq in kHz
        while True:                     # forever!
            # With KX3 @ 38.4 kbs, get_freq takes 100-150 ms to complete
            # If a new vfo setting is desired, we will have rigfreq_request
            # set to the new frequency, otherwise = None.
            if rigfreq_request:         # ordering of loop speeds up freq change
                if rigfreq_request != rigfreq:
                    rig.set_freq(rigfreq_request*1000.)
                    rigfreq_request = None
            rigfreq = float(rig.get_freq()) * 0.001     # freq in kHz
            time.sleep(interval)

# THREAD: CPU load checking, monitoring cpu stats.
cpu_usage = [0., 0., 0.]
def cpu_load(interval):
    """ Check CPU user and system time usage, along with load average.
        User & system reported as fraction of wall clock time in
        global variable cpu_usage.
        Interval defines sleep time between checks (float secs).
        To be run as thread.
    """
    global cpu_usage
    times_store = np.array(os.times())
    # Will return: fraction usr time, sys time, and 1-minute load average
    cpu_usage = [0., 0., os.getloadavg()[0]]
    while True:
        time.sleep(interval)
        times = np.array(os.times())
        dtimes = times - times_store    # difference since last loop
        usr = dtimes[0]/dtimes[4]       # fraction, 0 - 1
        sys = dtimes[1]/dtimes[4]
        times_store = times
        cpu_usage = [usr, sys, os.getloadavg()[0]]

# Screen setup parameters

if opt.lcd4:                        # setup for directfb (non-X) graphics
    SCREEN_SIZE = (480,272)         # default size for the 4" LCD (480x272)
    SCREEN_MODE = pg.FULLSCREEN
    # If we are root, we can set up LCD4 brightness.
    brightness = str(min(100, max(0, opt.lcd4_brightness)))  # validated string
    # Find path of script (same directory as iq.py) and append brightness value
    cmd = os.path.join( os.path.split(sys.argv[0])[0], "lcd4_brightness.sh") \
        + " %s" % brightness
    # (The subprocess script is a no-op if we are not root.)
    subprocess.call(cmd, shell=True)    # invoke shell script
else:
    SCREEN_MODE = pg.FULLSCREEN if opt.fullscreen else 0
    SCREEN_SIZE = (640, 512) if opt.waterfall \
                     else (640,310) # NB: graphics may not scale well
WF_LINES = 50                      # How many lines to use in the waterfall

# Initialize pygame (pg)
# We should not use pg.init(), because we don't want pg audio functions.
pg.display.init()
pg.font.init()

# Define the main window surface
surf_main = pg.display.set_mode(SCREEN_SIZE, SCREEN_MODE)
w_main = surf_main.get_width()

# derived parameters
w_spectra = w_main-10           # Allow a small margin, left and right
w_middle = w_spectra/2          # mid point of spectrum
x_spectra = (w_main-w_spectra) / 2.0    # x coord. of spectrum on screen

h_2d = 2*SCREEN_SIZE[1]/3 if opt.waterfall \
            else SCREEN_SIZE[1]         # height of 2d spectrum display
h_2d -= 25 # compensate for LCD4 overscan?
y_2d = 20. # y position of 2d disp. (screen top = 0)

# NB: transform size must be <= w_spectra.  I.e., need at least one
# pixel of width per data point.  Otherwise, waterfall won't work, etc.
if opt.size > w_spectra:
    for n in [1024, 512, 256, 128]:
        if n <= w_spectra:
            print "*** Size was reset from %d to %d." % (opt.size, n)
            opt.size = n    # Force size to be 2**k (ok, reasonable choice?)
            break
chunk_size = opt.buffers * opt.size # No. samples per chunk (pyaudio callback)
chunk_time = float(chunk_size) / opt.sample_rate

myDSP = dsp.DSP(opt)            # Establish DSP logic

# Surface for the 2d spectrum
surf_2d = pg.Surface((w_spectra, h_2d))             # Initialized to black
surf_2d_graticule = pg.Surface((w_spectra, h_2d))   # to hold fixed graticule

# define two LED widgets
led_urun = LED(10)
led_clip = LED(10)

# Waterfall geometry
h_wf = SCREEN_SIZE[1]/3         # Height of waterfall (3d spectrum)
y_wf = y_2d + h_2d              # Position just below 2d surface

# Surface for waterfall (3d) spectrum
surf_wf = pg.Surface((w_spectra, h_wf))

pg.display.set_caption(opt.ident)       # Title for main window

# Establish fonts for screen text.
lgfont = pg.font.SysFont('sans', 16)
lgfont_ht = lgfont.get_linesize()       # text height
medfont = pg.font.SysFont('sans', 12)
medfont_ht = medfont.get_linesize()
smfont = pg.font.SysFont('mono', 9)
smfont_ht = smfont.get_linesize()

# Define the size of a unit pixel in the waterfall
wf_pixel_size = (w_spectra/opt.size, h_wf/WF_LINES)

# min, max dB for wf palette
v_min, v_max = opt.v_min, opt.v_max     # lower/higher end (dB)
nsteps = 50                             # number of distinct colors

if opt.waterfall:
    # Instantiate the waterfall and palette data
    mywf = wf.Wf(opt, v_min, v_max, nsteps, wf_pixel_size)

if (opt.control == "si570") and opt.hamlib:
    print "Warning: Hamlib requested with si570.  Si570 wins! No Hamlib."
if opt.hamlib and (opt.control != "si570"):
    import Hamlib
    # start up Hamlib rig connection
    Hamlib.rig_set_debug (Hamlib.RIG_DEBUG_NONE)
    rig = Hamlib.Rig(opt.hamlib_rigtype)
    rig.set_conf ("rig_pathname",opt.hamlib_device)
    rig.set_conf ("retry","5")
    rig.open ()
    
    # Create thread for Hamlib freq. checking.  
    # Helps to even out the loop timing, maybe.
    hl_thread = threading.Thread(target=updatefreq, 
                        args = (opt.hamlib_interval, rig))
    hl_thread.daemon = True
    hl_thread.start()
    print "Hamlib thread started."
else:
    print "Hamlib not requested."

# Create thread for cpu load monitor
lm_thread = threading.Thread(target=cpu_load, args = (opt.cpu_load_interval,))
lm_thread.daemon = True
lm_thread.start()
print "CPU monitor thread started."

# Create graticule providing 2d graph calibration.
mygraticule = Graticule(opt, smfont, h_2d, w_spectra, GRAT_COLOR, GRAT_COLOR_2)
sp_min, sp_max  =  sp_min_def, sp_max_def  =  opt.sp_min, opt.sp_max
mygraticule.set_range(sp_min, sp_max)
surf_2d_graticule = mygraticule.make()

# Pre-formatx "static" text items to save time in real-time loop
# Useful operating parameters
parms_msg = "Fs = %d Hz; Res. = %.1f Hz;" \
            " chans = %d; width = %d px; acc = %.3f sec" % \
      (opt.sample_rate, float(opt.sample_rate)/opt.size, opt.size, w_spectra, 
      float(opt.size*opt.buffers)/opt.sample_rate)
wparms, hparms = medfont.size(parms_msg)
parms_matter = pg.Surface((wparms, hparms) )
parms_matter.blit(medfont.render(parms_msg, 1, TCOLOR2), (0,0))

print "Update interval = %.2f ms" % float(1000*chunk_time)

# Initialize input mode, RTL or AF
# This starts the input stream, so place it close to start of main loop.
if opt.source=="rtl":             # input from RTL dongle (and freq control)
    import iq_rtl as rtl
    dataIn = rtl.RTL_In(opt)
elif opt.source=='audio':         # input from audio card
    import iq_af as af
    mainqueueLock = af.queueLock    # queue and lock only for soundcard
    dataIn = af.DataInput(opt)
else:
    print "unrecognized mode"
    quit_all()

if opt.control=="si570":
    import si570control
    mysi570 = si570control.Si570control()
    mysi570.setFreq(opt.si570_frequency / 1000.)    # Set starting freq.

# ** MAIN PROGRAM LOOP **

run_flag = True                 # set false to suspend for help screen etc.
info_phase = 0                  # > 0 --> show info overlay
info_counter = 0
tloop = 0.
t_last_data = 0.
nframe = 0
t_frame0 = time.time()
led_overflow_ct = 0
startqueue = True
while True:

    nframe += 1                 # keep track of loop count FWIW

    # Each time through the main loop, we reconstruct the main screen

    surf_main.fill(BGCOLOR)     # Erase with background color

    # Each time through this loop, we receive an audio chunk, containing
    # multiple buffers.  The buffers have been transformed and the log power
    # spectra from each buffer will be provided in sp_log, which will be
    # plotted in the "2d" graph area.  After a number of log spectra are
    # displayed in the "2d" graph, a new line of the waterfall is generated.
    
    # Line of text with receiver center freq. if available
    showfreq = True
    if opt.control == "si570":
        msg = "%.3f kHz" % (mysi570.getFreqByValue() * 1000.) # freq/4 from Si570
    elif opt.hamlib:
        msg = "%.3f kHz" % rigfreq   # take current rigfreq from hamlib thread
    elif opt.control=='rtl':
        msg = "%.3f MHz" % (dataIn.rtl.get_center_freq()/1.e6)
    else:
        showfreq = False

    if showfreq:
        # Center it and blit just above 2d display
        ww, hh = lgfont.size(msg)
        surf_main.blit(lgfont.render(msg, 1, BLACK, BGCOLOR), 
                            (w_middle + x_spectra - ww/2, y_2d-hh))

    # show overflow & underrun indicators (for audio, not rtl)
    if opt.source=='audio':
        if af.led_underrun_ct > 0:        # underflow flag in af module
            sled = led_urun.get_LED_surface(RED)
            af.led_underrun_ct -= 1        # count down to extinguish
        else:
            sled = led_urun.get_LED_surface(None)   #off!
        msg = "Buffer underrun"
        ww, hh = medfont.size(msg)
        ww1 = SCREEN_SIZE[0]-ww-10
        surf_main.blit(medfont.render(msg, 1, BLACK, BGCOLOR), (ww1, y_2d-hh))
        surf_main.blit(sled, (ww1-15, y_2d-hh))
        if myDSP.led_clip_ct > 0:                   # overflow flag
            sled = led_clip.get_LED_surface(RED)
            myDSP.led_clip_ct -= 1
        else:
            sled = led_clip.get_LED_surface(None)   #off!
        msg = "Pulse clip"
        ww, hh = medfont.size(msg)
        surf_main.blit(medfont.render(msg, 1, BLACK, BGCOLOR), (25, y_2d-hh))
        surf_main.blit(sled, (10, y_2d-hh))

    if opt.source=='rtl':               # Input from RTL-SDR dongle
        iq_data_cmplx = dataIn.ReadSamples(chunk_size)
        if opt.rev_iq:                  # reverse spectrum?
            iq_data_cmplx = np.imag(iq_data_cmplx)+1j*np.real(iq_data_cmplx)
        #time.sleep(0.05)                # slow down if fast PC
        stats = [ 0, 0]                 # for now...
    else:                               # Input from audio card
        # In its separate thread, a chunk of audio data has accumulated.
        # When ready, pull log power spectrum data out of queue.
        my_in_data_s = dataIn.get_queued_data() # timeout protected

        # Convert string of 16-bit I,Q samples to complex floating
        iq_local = np.fromstring(my_in_data_s,dtype=np.int16).astype('float32')
        re_d = np.array(iq_local[1::2]) # right input (I)
        im_d = np.array(iq_local[0::2]) # left  input (Q)

        # The PCM290x chip has 1 lag offset of R wrt L channel. Fix, if needed.
        if opt.lagfix:
            im_d = np.roll(im_d, 1)
        # Get some stats (max values) to monitor gain settings, etc.
        stats = [int(np.amax(re_d)), int(np.amax(im_d))]
        if opt.rev_iq:      # reverse spectrum?
            iq_data_cmplx = np.array(im_d + re_d*1j)
        else:               # normal spectrum
            iq_data_cmplx = np.array(re_d + im_d*1j)

    sp_log = myDSP.GetLogPowerSpectrum(iq_data_cmplx)
    if opt.source=='rtl':   # Boost rtl spectrum (arbitrary amount)
        sp_log += 60        # RTL data were normalized to +/- 1.
    
    yscale = float(h_2d)/(sp_max-sp_min)    # yscale is screen units per dB
    # Set the 2d surface to background/graticule.
    surf_2d.blit(surf_2d_graticule, (0, 0))
    
    # Draw the "2d" spectrum graph
    sp_scaled = ((sp_log - sp_min) * yscale) + 3.
    ylist = list(sp_scaled)
    ylist = [ h_2d - x for x in ylist ]                 # flip the y's
    lylist = len(ylist)
    xlist = [ x* w_spectra/lylist for x in xrange(lylist) ]
    # Draw the spectrum based on our data lists.
    pg.draw.lines(surf_2d, WHITE, False, zip(xlist,ylist), 1)

    # Place 2d spectrum on main surface
    surf_main.blit(surf_2d, (x_spectra, y_2d))

    if opt.waterfall:
        # Calculate the new Waterfall line and blit it to main surface
        nsum = opt.waterfall_accumulation    # 2d spectra per wf line
        mywf.calculate(sp_log, nsum, surf_wf)
        surf_main.blit(surf_wf, (x_spectra, y_wf+1))

    if info_phase > 0:
        # Assemble and show semi-transparent overlay info screen
        # This takes cpu time, so don't recompute it too often. (DSP & graphics
        # are still running.)
        info_counter = ( info_counter + 1 ) % INFO_CYCLE
        if info_counter == 1:
            # First time through, and every INFO_CYCLE-th time thereafter.
            # Some button labels to show at right of LCD4 window
            # Add labels for LCD4 buttons.
            place_buttons = False
            if opt.lcd4 or (w_main==480):
                place_buttons = True
                button_names = [ " LT", " RT ", " UP", " DN", "ENT" ]
                button_vloc = [ 20, 70, 120, 170, 220 ]
                button_surfs = []
                for bb in button_names:
                    button_surfs.append(medfont.render(bb, 1, WHITE, BLACK))

            # Help info will be placed toward top of window.
            # Info comes in 4 phases (0 - 3), cycle among them with <return>
            if info_phase == 1:
                lines = [ "KEYBOARD CONTROLS:",
                  "(R) Reset display; (Q) Quit program",
                  "Change upper plot dB limit:  (U) increase; (u) decrease",
                  "Change lower plot dB limit:  (L) increase; (l) decrease",
                  "Change WF palette upper limit: (B) increase; (b) decrease",
                  "Change WF palette lower limit: (D) increase; (d) decrease" ]
                if opt.control != "none":
                    lines.append("Change rcvr freq: (rt arrow) increase; (lt arrow) decrease")
                    lines.append("   Use SHIFT for bigger steps")
                lines.append("RETURN - Cycle to next Help screen")
            elif info_phase == 2:
                lines = [ "SPECTRUM ADJUSTMENTS:",
                          "UP - upper screen level +10 dB",
                          "DOWN - upper screen level -10 dB",
                          "RIGHT - lower screen level +10 dB",
                          "LEFT - lower screen level -10 dB",
                          "RETURN - Cycle to next Help screen" ]
            elif info_phase == 3:
                lines = [ "WATERFALL PALETTE ADJUSTMENTS:",
                          "UP - upper threshold INCREASE",
                          "DOWN - upper threshold DECREASE",
                          "RIGHT - lower threshold INCREASE",
                          "LEFT - lower threshold DECREASE",
                          "RETURN - Cycle Help screen OFF" ]
            else:
                lines = [ "Invalid info phase!"]    # we should never arrive here.
                info_phase = 0
            wh = (0, 0)
            for il in lines:                # Find max line width, height
                wh = map(max, wh, medfont.size(il))
            help_matter = pg.Surface((wh[0]+24, len(lines)*wh[1]+15) )
            for ix,x in enumerate(lines):
                help_matter.blit(medfont.render(x, 1, TCOLOR2), (20,ix*wh[1]+15))
            
            # "Live" info is placed toward bottom of window...
            # Width of this surface is a guess. (It should be computed.)
            live_surface = pg.Surface((430,48), 0)
            # give live sp_min, sp_max, v_min, v_max
            msg = "dB scale min= %d, max= %d" % (sp_min, sp_max)
            live_surface.blit(medfont.render(msg, 1, TCOLOR2), (10,0))
            if opt.waterfall:
                # Palette adjustments info
                msg = "WF palette min= %d, max= %d" % (v_min, v_max)
                live_surface.blit(medfont.render(msg, 1, TCOLOR2), (200, 0))
            live_surface.blit(parms_matter, (10,16))
            if opt.source=='audio':
                msg = "ADC max I:%05d; Q:%05d" % (stats[0], stats[1])
                live_surface.blit(medfont.render(msg, 1, TCOLOR2), (10, 32))
            # Show the live cpu load information from cpu_usage thread.
            msg = "Load usr=%3.2f; sys=%3.2f; load avg=%.2f" % \
                (cpu_usage[0], cpu_usage[1], cpu_usage[2])
            live_surface.blit(medfont.render(msg, 1, TCOLOR2), (200, 32))
        # Blit newly formatted -- or old -- screen to main surface.
        if place_buttons:   # Do we have rt hand buttons to place?
            for ix, bb in enumerate(button_surfs):
                surf_main.blit(bb, (449, button_vloc[ix]))
        surf_main.blit(help_matter, (20,20))
        surf_main.blit(live_surface,(20,SCREEN_SIZE[1]-60))

    # Check for pygame events - keyboard, etc.
    # Note: A key press is not recorded as a PyGame event if you are 
    # connecting via SSH.  In that case, use --sp_min/max and --v_min/max
    # command line options to set scales.

    for event in pg.event.get():
        if event.type == pg.QUIT:
            quit_all()
        elif event.type == pg.KEYDOWN:
            if info_phase <= 1:         # Normal op. (0) or help phase 1 (1)
                # We usually want left or right shift treated the same!
                shifted = event.mod & (pg.KMOD_LSHIFT | pg.KMOD_RSHIFT)
                if event.key == pg.K_q:
                    quit_all()
                elif event.key == pg.K_u:            # 'u' or 'U' - chg upper dB
                    if shifted:                         # 'U' move up
                        if sp_max < 0:
                            sp_max += 10
                    else:                               # 'u' move dn
                        if sp_max > -130 and sp_max > sp_min + 10:
                            sp_max -= 10
                    mygraticule.set_range(sp_min, sp_max)
                    surf_2d_graticule = mygraticule.make()
                elif event.key == pg.K_l:            # 'l' or 'L' - chg lower dB
                    if shifted:                         # 'L' move up lower dB
                        if sp_min < sp_max -10:
                            sp_min += 10
                    else:                               # 'l' move down lower dB
                        if sp_min > -140:
                            sp_min -= 10
                    mygraticule.set_range(sp_min, sp_max)
                    surf_2d_graticule = mygraticule.make()   
                elif event.key == pg.K_b:            # 'b' or 'B' - chg upper pal.
                    if shifted:
                        if v_max < -10:
                            v_max += 10
                    else:
                        if v_max > v_min + 20:
                            v_max -= 10
                    mywf.set_range(v_min,v_max)
                elif event.key == pg.K_d:            # 'd' or 'D' - chg lower pal.
                    if shifted:
                        if v_min < v_max - 20:
                            v_min += 10
                    else:
                        if v_min > -130:
                            v_min -= 10
                    mywf.set_range(v_min,v_max)
                elif event.key == pg.K_r:            # 'r' or 'R' = reset levels
                    sp_min, sp_max = sp_min_def, sp_max_def
                    mygraticule.set_range(sp_min, sp_max)
                    surf_2d_graticule = mygraticule.make()
                    if opt.waterfall:
                        v_min, v_max = mywf.reset_range()

                # Note that LCD peripheral buttons are Right, Left, Up, Down
                # arrows and "Enter".  (Same as keyboard buttons)

                elif event.key == pg.K_RIGHT:        # right arrow + freq
                    if opt.control == 'rtl':
                        finc = 100e3 if shifted else 10e3
                        dataIn.rtl.center_freq = dataIn.rtl.get_center_freq()+finc
                    elif opt.control == 'si570':
                        finc = 1.0 if shifted else 0.1
                        mysi570.setFreqByValue(mysi570.getFreqByValue() + finc*.001)
                    elif opt.hamlib:
                        finc = 1.0 if shifted else 0.1
                        rigfreq_request = rigfreq + finc
                    else:
                        print "Rt arrow ignored, no Hamlib"
                elif event.key == pg.K_LEFT:         # left arrow - freq
                    if opt.control == 'rtl':
                        finc = -100e3 if shifted else -10e3
                        dataIn.rtl.center_freq = dataIn.rtl.get_center_freq()+finc
                    elif opt.control == 'si570':
                        finc = -1.0 if shifted else -0.1
                        mysi570.setFreqByValue(mysi570.getFreqByValue() + finc*.001)
                    elif opt.hamlib:
                        finc = -1.0 if shifted else -0.1
                        rigfreq_request = rigfreq + finc
                    else:
                        print "Lt arrow ignored, no Hamlib"
                elif event.key == pg.K_UP:
                    print "Up"
                elif event.key == pg.K_DOWN:
                    print "Down"
                elif event.key == pg.K_RETURN:
                    info_phase  += 1            # Jump to phase 1 or 2 overlay
                    info_counter = 0            #   (next time)

            # We can have an alternate set of keyboard (LCD button) responses
            # for each "phase" of the on-screen help system.
            
            elif info_phase == 2:               # Listen for info phase 2 keys
                # Showing 2d spectrum gain/offset adjustments
                # Note: making graticule is moderately slow.  
                # Do not repeat range changes too quickly!
                if event.key == pg.K_UP:
                    if sp_max < 0:
                        sp_max += 10
                    mygraticule.set_range(sp_min, sp_max)
                    surf_2d_graticule = mygraticule.make()   
                elif event.key == pg.K_DOWN:
                    if sp_max > -130 and sp_max > sp_min + 10:
                        sp_max -= 10
                    mygraticule.set_range(sp_min, sp_max)
                    surf_2d_graticule = mygraticule.make()   
                elif event.key == pg.K_RIGHT:
                    if sp_min < sp_max -10:
                        sp_min += 10
                    mygraticule.set_range(sp_min, sp_max)
                    surf_2d_graticule = mygraticule.make()   
                elif event.key == pg.K_LEFT:
                    if sp_min > -140:
                        sp_min -= 10
                    mygraticule.set_range(sp_min, sp_max)
                    surf_2d_graticule = mygraticule.make()   
                elif event.key == pg.K_RETURN:
                    info_phase = 3 if opt.waterfall \
                            else 0              # Next is phase 3 unless no WF.
                    info_counter = 0

            elif info_phase == 3:               # Listen for info phase 3 keys
                # Showing waterfall pallette adjustments
                # Note: recalculating palette is quite slow.  
                # Do not repeat range changes too quickly! (1 per second max?)
                if event.key == pg.K_UP:
                    if v_max < -10:
                        v_max += 10
                    mywf.set_range(v_min,v_max)
                elif event.key == pg.K_DOWN:
                    if v_max > v_min + 20:
                        v_max -= 10
                    mywf.set_range(v_min,v_max)
                elif event.key == pg.K_RIGHT:
                    if v_min < v_max - 20:
                        v_min += 10
                    mywf.set_range(v_min,v_max)
                elif event.key == pg.K_LEFT:
                    if v_min > -130:
                        v_min -= 10
                    mywf.set_range(v_min,v_max)
                elif event.key == pg.K_RETURN:
                    info_phase = 0                  # Turn OFF overlay
                    info_counter = 0
    # Finally, update display for user
    pg.display.update()

    # End of main loop

# END OF IQ.PY
