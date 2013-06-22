#!/usr/bin/env python
#
# Copyright 2006,2007,2009,2011 Free Software Foundation, Inc.
#
# rtl_flex is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# rtl_flex is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#
from gnuradio import eng_notation
from gnuradio import gr
from gnuradio import filter
from gnuradio import window
from gnuradio import pager
from gnuradio.filter import optfir
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
from gnuradio.wxgui import fftsink2
from grc_gnuradio import wxgui as grc_wxgui
from optparse import OptionParser
import rtl_flex_utils
import osmosdr
import wx
import time
import sys

class app_top_block(grc_wxgui.top_block_gui):
    def __init__(self, options, queue):
        grc_wxgui.top_block_gui.__init__(self, title="RTL FLEX reciever")
        self.options = options
        self.offset = 0.0
        self.adj_time = time.time()
        self.verbose = options.verbose
        self.log = options.log
        self.fft_enable = options.fft

        # Set up rtl source
        self.u = osmosdr.source( args="%s"%(options.device) )
        #set Freq
        self.u.set_center_freq(options.freq+options.calibration, 0)

        # Grab 250 KHz of spectrum
        self.u.set_sample_rate(250e3)
        rate = self.u.get_sample_rate()
        if rate != 250e3:
            print "Unable to set required sample rate of 250 Ksps (got %f)" % rate
            sys.exit(1)
        #Set gain
        if options.rx_gain is None:
            grange = self.u.get_gain_range()
            options.rx_gain = float(grange.start()+grange.stop())/2.0
            print "\nNo gain specified."
            print "Setting gain to %f (from [%f, %f])" % \
                (options.rx_gain, grange.start(), grange.stop())

        self.u.set_gain(options.rx_gain, 0)

        taps = optfir.low_pass(1.0,
                               250e3,
                               11000,
                               12500,
                               0.1,
                               60)


        self.chan = filter.freq_xlating_fir_filter_ccf(10,
                                                   taps,
                                                   0.0,
                                                   250e3)
        if self.fft_enable:
            self.fftsink = fftsink2.fft_sink_c(
                self.GetWin(),
                baseband_freq=options.freq+options.calibration,
                y_per_div=10,
                y_divs=10,
                ref_level=0,
                ref_scale=2.0,
                sample_rate=250e3,
                fft_size=1024,
                fft_rate=15,
                average=True,
                avg_alpha=None,
                title="RTL Output",
                peak_hold=False,
            )
            self.Add(self.fftsink.win)

            self.fftsink2 = fftsink2.fft_sink_c(
                self.GetWin(),
                baseband_freq=options.freq+options.calibration,
                y_per_div=10,
                y_divs=10,
                ref_level=0,
                ref_scale=2.0,
                sample_rate=250e3,
                fft_size=1024,
                fft_rate=15,
                average=True,
                avg_alpha=None,
                title="Decoder input (After the filters)",
                peak_hold=False,
            )
            self.Add(self.fftsink2.win)

        self.flex = pager.flex_demod(queue, options.freq, options.verbose, options.log)

        self.connect(self.u, self.chan, self.flex)
        if self.fft_enable:
            self.connect(self.u, self.fftsink)
            self.connect(self.chan, self.fftsink2)

    def freq_offset(self):
    	return self.flex.dc_offset()*1600

    def adjust_freq(self):
        if time.time() - self.adj_time > 1.6:
            self.adj_time = time.time()
            self.offset -= self.freq_offset()
            self.chan.set_center_freq(self.offset)
            if self.verbose:
                print "Channel frequency offset (Hz):", int(self.offset)


def get_options():
    parser = OptionParser(option_class=eng_option)

    parser.add_option('-f', '--freq', type="eng_float", default=None,
                      help="Set receive frequency to FREQ [default=%default]",
                      metavar="FREQ")
    parser.add_option("", "--rx-gain", type="eng_float", default=None,
                      help="set receive gain in dB (default is midpoint)")
    parser.add_option("-c",   "--calibration", type="eng_float", default=0.0,
                      help="set frequency offset to Hz", metavar="Hz")
    parser.add_option("-v", "--verbose", action="store_true", default=False)
    parser.add_option("", "--log", action="store_true", default=False)
    parser.add_option("", "--fft", action="store_true", default=False,
                      help="Enable fft plots")
    parser.add_option("-d" ,"--database", default=False, help="sqlalchemy connection string for database")
    parser.add_option("-D" ,"--device", default="rtl=0", help="osmocom device string example: rtl=0")

    (options, args) = parser.parse_args()

    if len(args) > 0:
    	print "Run 'rtl_flex.py -h' for options."
    	sys.exit(1)

    if (options.freq is None):
        sys.stderr.write("You must specify -f FREQ or --freq FREQ\n")
        sys.exit(1)

    return (options, args)

if __name__ == "__main__":
    (options, args) = get_options()
    queue = gr.msg_queue()
    tb = app_top_block(options, queue)
    runner = rtl_flex_utils.queue_runner(queue,options)

    try:
        tb.Run(True)
    except KeyboardInterrupt:
        pass

    runner.end()

