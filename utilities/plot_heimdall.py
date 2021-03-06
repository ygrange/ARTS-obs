#!/usr/bin/env python
# Creates overview plots of candidates found by Heimdall.
# This plotting program distinguishes between noise, RFI, erroneous candidates, and valid candidates, plotting them all in different ways.
# Output is an overview plot called overview.png in the directory of the program.

# Emily Petroff 2012
# Code originally written by Ben Barsdell and source code can be found in /lustre/home/bbarsdell/code/c_cpp/heimdall/

import numpy as np
from numpy.lib.recfunctions import append_fields


class Classifier(object):
    def __init__(self):
        self.nbeams      = 40
        self.snr_cut     = 6.5
        self.members_cut = 3
        self.nbeams_cut  = 3
        self.dm_cut      = 1.5
        self.filter_cut  = 0
        self.beam_mask   = (1<<40) - 1
        self.filter_max  = 39
        
    def is_masked(self, beam):
        return ((1<<beam) & self.beam_mask) == 0
    
    def is_hidden(self, cand):
        return ( (cand['snr'] < self.snr_cut) |
                 (cand['filter'] > self.filter_cut) |
                 self.is_masked(cand['beam']) |
                 ((self.is_masked(cand['beam']) != True) &
                  (cand['beam'] != cand['prim_beam'])) )
    
    def is_noise(self, cand):
        return cand['members'] < self.members_cut

    def is_fat(self, cand):
        return cand['filter'] >= self.filter_max
    
    def count_nbeams(self, mask):
        n = 0
        for i in range(self.nbeams):
            n += (mask & (1<<i)) > 0
        return n
            
    def is_coinc_rfi(self, cand):
        nbeams = self.count_nbeams(cand['beam_mask'] & self.beam_mask)
        return nbeams > self.nbeams_cut
    
    def is_lowdm_rfi(self, cand):
        return cand['dm'] < self.dm_cut


class TimeDMPlot(object):
    def __init__(self, g):
        self.g = g
        self.dm_base = 1.0
        self.snr_min = 6.0
        
    def plot(self, data):
        self.g.reset()
        self.g('set size 1.0,0.5')
        self.g('set origin 0.0,0.0')
        self.g('unset key')
        self.g('set autoscale x')
        self.g('set logscale y')
        self.g('set logscale y2')
        self.g('set yrange[1.0:2100]')
        self.g('set y2range[1.0:2100]')
        self.g('set cbrange[-0.5:12.5]')
        self.g('set palette positive nops_allcF maxcolors 13 gamma 1.5 color model RGB')
        self.g("set palette defined ( 0 'green', 1 'cyan', 2 'magenta', 3 'orange' )")
        self.g('unset colorbox')
        self.g("set style line 12 lc 'grey'")
        self.g('set grid noxtics nomxtics ytics mytics lt 9 lw 0.2')
        self.g('set ytics 10')
        self.g('set mytics 10')
        self.g('set y2tics 10 out mirror format ""')
        self.g('set my2tics 10')
        # self.g('set xtics 1000')  ####for long pointings
        self.g('set xtics 60')
        # self.g('set x2tics 1000 out mirror format ""')
        self.g('set x2tics 60 out mirror format ""')
        self.g('set mxtics 4')
        self.g('set mx2tics 4')
        self.g('set xlabel "Time [s]"')
        self.g('set ylabel "DM + 1 [pc cm^{-3}]"')
        self.g('min(x,y) = x<=y?x:y')
        self.g('max(x,y) = x>=y?x:y')

        categories = []

        if len(data['noise']) > 0:
            noise = Gnuplot.Data(data['noise']['snr'],
                                 data['noise']['time'],
                                 data['noise']['dm'],
                                 using='2:($3+%f):(($1-%f)/2.0+0.5)' \
                                     % (self.dm_base,self.snr_min),
                                 with_='p pt 2 lt 9 lw 0.5 ps variable')
            categories.append(noise)

        if len(data['coinc']) > 0:
            coinc = Gnuplot.Data(data['coinc']['snr'],
                                 data['coinc']['time'],
                                 data['coinc']['filter'],
                                 data['coinc']['dm'],
                                 using="2:($4+%f):(min(($1-%f)/2.0+0.9,5)):3" \
                                     % (self.dm_base,self.snr_min),
                                 with_="p pt 3 lw 0.25 lt palette ps variable")
            categories.append(coinc)
            
        if len(data['fat']) > 0:
            fat   = Gnuplot.Data(data['fat']['snr'],
                                 data['fat']['time'],
                                 data['fat']['filter'],
                                 data['fat']['dm'],
                                 using="2:($4+%f):(min(($1-%f)/2.0+0.9,5)):3" \
                                     % (self.dm_base,self.snr_min),
                                 with_="p pt 6 lw 0.5 lt palette ps variable")
            categories.append(fat)
        
            fatlabels   = Gnuplot.Data(data['fat']['beam'],
                                       data['fat']['time'],
                                       data['fat']['dm'],
                                       using='2:($3+%f):(sprintf("%%d",$1+1))' \
                                           % (self.dm_base),
                                       with_='labels center font ",7" offset 0,0.05 textcolor rgbcolor "gray"')
            categories.append(fatlabels)

        if len(data['lowdm']) > 0:
            lowdm = Gnuplot.Data(data['lowdm']['snr'],
                                 data['lowdm']['time'],
                                 data['lowdm']['filter'],
                                 data['lowdm']['dm'],
                                 using="2:($4+%f):(min(($1-%f)/2.0+0.9,5)):3" \
                                     % (self.dm_base,self.snr_min),
                                 with_="p pt 6 lt palette ps variable")
            categories.append(lowdm)
            
            lowdmlabels = Gnuplot.Data(data['lowdm']['beam'],
                                       data['lowdm']['time'],
                                       data['lowdm']['dm'],
                                       using='2:($3+%f):(sprintf("%%d",$1+1))' \
                                           % (self.dm_base),
                                       with_='labels center font ",7" offset 0,0.05 textcolor rgbcolor "black"')
            categories.append(lowdmlabels)

        if len(data['valid']) > 0:
            valid = Gnuplot.Data(data['valid']['snr'],
                                 data['valid']['time'],
                                 data['valid']['filter'],
                                 data['valid']['dm'],
                                 using="2:($4+%f):(min(($1-%f)/2.0+0.9,5)):3" \
                                     % (self.dm_base,self.snr_min),
                                 with_="p pt 7 lt palette ps variable")
            categories.append(valid)
            
            validlabels = Gnuplot.Data(data['valid']['beam'],
                                       data['valid']['time'],
                                       data['valid']['dm'],
                                       using='2:($3+%f):(sprintf("%%d",$1+1))' \
                                           % (self.dm_base),
                                       with_='labels center font ",7" offset 0,0.05 textcolor rgbcolor "black"')
            categories.append(validlabels)

        """
        self.g.plot(noise, coinc,
                    fat, fatlabels,
                    lowdm, lowdmlabels,
                    valid, validlabels)
        """
        self.g.plot(*categories)


class DMSNRPlot(object):
    def __init__(self, g):
        self.g = g
        self.dm_base = 1.0
        self.snr_base = 5.9
        self.max_filter = 12
        #self.dt = 40.96e-6
        self.dt = 64e-6

    def plot(self, data):
        self.g.reset()
        self.g('set size 0.6,0.5')
        self.g('set origin 0.4,0.5')
        self.g('unset key')
        self.g('set xrange[1.0:2000]')
        self.g('set x2range[1.0:2000]')
        self.g('set logscale x')
        self.g('set logscale x2')
        self.g('set xtics 10')
        self.g('set mxtics 10')
        self.g('set x2tics 10 out mirror format ""')
        self.g('set mx2tics 10')
        self.g('set xtics mirror')
        self.g('set grid noytics nomytics xtics mxtics lt 9 lw 0.2')
        self.g('set logscale y')
        self.g('set logscale y2')
        self.g('set yrange[0.1:100]')
        self.g('set y2range[0.1:100]')
        self.g('set cbrange[-0.5:12.5]')
        self.g('set palette positive nops_allcF maxcolors 13 gamma 1.5 color model RGB')
        self.g("set palette defined ( 0 'green', 1 'cyan', 2 'magenta', 3 'orange' )")
        self.g('set colorbox')
        self.g('snr_min = %f' % self.snr_base)
        self.g('unset mytics')
        self.g('unset my2tics')
        self.g('set ytics ("6 " 6-snr_min, "6.1 " 6.1-snr_min, "6.4 " 6.4-snr_min, "7 " 7-snr_min, "8 " 8-snr_min, "10 " 10-snr_min, "13 " 13-snr_min, "20 " 20-snr_min, "40 " 40-snr_min, "100 " 100-snr_min)')
        self.g('set y2tics ("6" 6-snr_min, "6.1 " 6.1-snr_min, "6.4 " 6.4-snr_min, "7 " 7-snr_min, "8 " 8-snr_min, "10 " 10-snr_min, "13 " 13-snr_min, "20 " 20-snr_min, "40 " 40-snr_min, "100 " 100-snr_min) out mirror format ""')
        # self.g('set cbtics 1 format "2^%g"')
        self.g('set cbtics 1 format ""')
        filter_tics = [2000*self.dt * 2**i for i in range(self.max_filter+1)]
        # self.g('set cbtics add ("64 us" 0, "128 us" 1, "256 us" 2, "512 us" 3, "1 ms" 4, "2 ms" 5, "4 ms" 6, "8 ms" 7, "16 ms" 8, "32 ms" 9, "64 ms" 10, "128 ms" 11, "256 ms" 12)')
        self.g('set cbtics add ('+', '.join(['"%.4g" %i'%(x,i) for i,x in enumerate(filter_tics)])+')')
        self.g('set xlabel "DM+1 [pc cm^{-3}]"')
        self.g('set ylabel "SNR"')
        # self.g('set cblabel "log_{2} boxcar width"')
        self.g('set cblabel "Boxcar width [ms]"')

        categories = []

        #if len(data['noise']) > 0:
        #    noise = Gnuplot.Data(data['noise']['snr'],
        #                         data['noise']['dm'],
        #                         using="($2+%f):($1-%f)" \
        #                             % (self.dm_base,self.snr_base),
        #                         with_="p pt 2 ps 0.5 lt 9")
        #    categories.append(noise)
        #    
        #if len(data['lowdm']) > 0:
        #    lowdm = Gnuplot.Data(data['lowdm']['snr'],
        #                         data['lowdm']['dm'],
        #                         data['lowdm']['filter'],
        #                         using="($2+%f):($1-%f):3" \
        #                             % (self.dm_base,self.snr_base),
        #                         with_="p pt 6 ps 0.8 lt palette")
        #    categories.append(lowdm)

        #if len(data['fat']) > 0:
        #    fat   = Gnuplot.Data(data['fat']['snr'],
        #                         data['fat']['dm'],
        #                         data['fat']['filter'],
        #                         using="($2+%f):($1-%f):3" \
        #                             % (self.dm_base,self.snr_base),
        #                         with_="p pt 6 ps 0.8 lw 0.3 lt palette")
        #    categories.append(fat)

        #if len(data['coinc']) > 0:
        #    coinc = Gnuplot.Data(data['coinc']['snr'],
        #                         data['coinc']['dm'],
        #                         data['coinc']['filter'],
        #                         using="($2+%f):($1-%f):3" \
        #                             % (self.dm_base,self.snr_base),
        #                         with_="p pt 3 ps 0.8 lw 0.3 lt palette")
        #    categories.append(coinc)

        if len(data['valid']) > 0:
            valid = Gnuplot.Data(data['valid']['snr'],
                                 data['valid']['dm'],
                                 data['valid']['filter'],
                                 using="($2+%f):($1-%f):3" \
                                     % (self.dm_base,self.snr_base),
                                 with_="p pt 7 ps 0.8 lt palette")
            categories.append(valid)
            
        # self.g.plot(noise, lowdm, coinc, fat, valid)
        self.g.plot(*categories)


class DMHistogram(object):
    def __init__(self, cands=None):
        self.dm_min   = 0.10
        self.dm_max   = 1010.0
        self.min_bins = 30
        self.hist     = None
        if cands is not None:
            self.build(cands)
            
    def build(self, cands):
        import math
        cands = cands[cands['filter'] <= 10]
        N = len(cands)
        log_dm_min = math.log10(self.dm_min)
        log_dm_max = math.log10(self.dm_max)
        nbins    = max(self.min_bins, 2*int(math.sqrt(N)))
        binwidth = (log_dm_max - log_dm_min) / nbins
        bins_    = 10**(log_dm_min + (np.arange(nbins)+0.5)*binwidth)
        dms      = np.maximum(cands['dm'], self.dm_min)
        log_dms  = np.log10(dms)
        vals, edges = np.histogram(log_dms, bins=nbins,
                                   range=(log_dm_min,log_dm_max))
        self.hist = np.rec.fromrecords(np.column_stack((bins_, vals)),
                                       names=('bins', 'vals'))


class DMHistPlot(object):
    def __init__(self, g):
        self.g = g
        self.dm_base = 1.0
        self.snr_base = 5.9
        self.max_filter = 12
        #self.dt = 40.96e-6
        self.dt = 64e-6

    def plot(self, data):
        self.g.reset()
        self.g('set size 0.4,0.5')
        self.g('set origin 0.0,0.5')
        self.g('unset key')
        self.g('set logscale x')
        self.g('set xrange[1:2000]')
        self.g('set logscale x2')
        self.g('set x2range[1:2000]')
        self.g('set logscale y')
        self.g('set logscale y2')
        self.g('set yrange [1:2000]')
        self.g('set y2range [1:2000]')
        self.g('set xtics 10')
        self.g('set mxtics 10')
        self.g('set x2tics 10 out mirror format ""')
        self.g('set mx2tics 10')
        self.g('set ytics 10')
        self.g('set y2tics 10 out mirror format ""')
        self.g('set mytics 10')
        self.g('set my2tics 10')
        self.g('set grid noxtics nomytics xtics mxtics lt 9 lw 0.2')
        # self.g('set key inside top center horizontal samplen 2 maxcols 6')
        self.g('set key inside top center horizontal samplen 2')
        self.g('set xlabel "DM+1 [pc cm^{-3}]')
        self.g('set ylabel "Candidate count"')
        
        beams = []
        for b,beam_hist in enumerate(data):
            beams.append( Gnuplot.Data(beam_hist['bins'],
                                       beam_hist['vals'],
                                       using='($1+%f):2' \
                                           % (self.dm_base),
                                       with_='histeps lw %i lt 1 lc %i' \
                                           % (1+(b+1<8),b+1),
                                       title=str(b+1)) )
        self.g.plot(*beams)


if __name__ == "__main__":
    import argparse
    import Gnuplot
    
    parser = argparse.ArgumentParser(description="Generates data for Heimdall overview plots.")
    parser.add_argument('-cands_file', default="all_candidates.dat")
    parser.add_argument('-nbeams', type=int, default=40)
    parser.add_argument('-snr_cut', type=float)
    parser.add_argument('-beam_mask', type=int, default=(1<<40)-1)
    parser.add_argument('-nbeams_cut', type=int, default=39)
    parser.add_argument('-members_cut', type=int, default=3)
    parser.add_argument('-dm_cut', type=float, default=1.5)
    parser.add_argument('-filter_cut', type=int, default=99)
    parser.add_argument('-filter_max', type=int, default=12)
    parser.add_argument('-min_bins', type=int, default=30)
    parser.add_argument('-interactive', action="store_true")
    args = parser.parse_args()
    
    filename = args.cands_file
    nbeams = args.nbeams
    interactive = args.interactive
    
    # Load candidates from all_candidates file
    # LCO: no coincidence: columns nbeams and further are missing
    # Add fake columns to fix
    all_cands = \
        np.loadtxt(filename,
                   dtype={'names': ('snr','samp_idx','time','filter',
                                    'dm_trial','dm','members','begin','end', 'beam'),
                                    #'nbeams','beam_mask','prim_beam',
                                    #'max_snr','beam'),
                          'formats': ('f4', 'i4', 'f4', 'i4',
                                      'i4', 'f4', 'i4', 'i4', 'i4', 'i4')})
                                      #'i4', 'i4', 'i4',
                                      #'f4', 'i4')})
    # Adjust for 0-based indexing in python
    ones_array = np.ones_like(all_cands['snr'], dtype='i4')
    zeros_array = np.zeros_like(all_cands['snr'], dtype='i4')
    all_cands = append_fields(all_cands, 'nbeams', ones_array)
    #all_cands = append_fields(all_cands, 'beam_mask', zeros_array)
    #all_cands = append_fields(all_cands, 'prim_beam', ones_array)
    all_cands = append_fields(all_cands, 'max_snr', ones_array*10)
    #all_cands = append_fields(all_cands, 'beam', ones_array)

    # beam mask = the one beam
    beam_mask = np.array([1<<beam for beam in all_cands['beam']])
    all_cands = append_fields(all_cands, 'beam_mask', beam_mask)

    # add primary beam = beam
    all_cands = append_fields(all_cands, 'prim_beam', all_cands['beam'])

    all_cands['prim_beam'] -= 1
    all_cands['beam'] -= 1

    
    if len(all_cands) == 0:
        print "Found no candidates, exiting"
        exit()

    
    print "Loaded %i candidates" % len(all_cands)
    
    classifier = Classifier()
    classifier.nbeams = args.nbeams
    classifier.snr_cut = args.snr_cut
    classifier.beam_mask = args.beam_mask
    classifier.nbeams_cut = args.nbeams_cut
    classifier.members_cut = args.members_cut
    classifier.dm_cut = args.dm_cut
    classifier.filter_cut = args.filter_cut
    classifier.filter_max = args.filter_max
    
    # Filter candidates based on classifications
    print "Classifying candidates..."
    categories = {}
    is_hidden = classifier.is_hidden(all_cands)
    is_noise  = (is_hidden==False) & classifier.is_noise(all_cands)
    is_coinc  = (is_hidden==False) & (is_noise ==False) & classifier.is_coinc_rfi(all_cands)
    is_fat    = (is_hidden==False) & (is_noise ==False) & (is_coinc ==False) & classifier.is_fat(all_cands)
    is_lowdm  = (is_hidden==False) & (is_noise ==False) & (is_fat   ==False) & (is_coinc ==False) & classifier.is_lowdm_rfi(all_cands)
    is_valid  = (is_hidden==False) & (is_noise ==False) & (is_fat   ==False) & (is_coinc ==False) & (is_lowdm ==False)
    categories["hidden"] = all_cands[is_hidden]
    categories["noise"]  = all_cands[is_noise]
    categories["coinc"]  = all_cands[is_coinc]
    categories["fat"]    = all_cands[is_fat]
    categories["lowdm"]  = all_cands[is_lowdm]
    categories["valid"]  = all_cands[is_valid]
    
    print "Classified %i as hidden," % len(categories["hidden"])
    print "           %i as noise spikes," % len(categories["noise"])
    print "           %i as coincident RFI," % len(categories["coinc"])
    print "           %i as fat RFI, and" % len(categories["fat"])
    print "           %i as low-DM RFI, and" % len(categories["lowdm"])
    print "           %i as valid candidates." % len(categories["valid"])
    
    print "Building histograms..."
    beam_hists = []
    for beam in range(nbeams):
        cands = all_cands[all_cands['beam'] == beam]
        beam_hists.append(DMHistogram(cands).hist)
    
    # Generate plots
    print "Generating plots..."
    g = Gnuplot.Gnuplot(debug=0)
    if not interactive:
        #g('set terminal pngcairo transparent enhanced font "arial,10" size 1280, 960')
        g('set terminal png enhanced font "arial,10" size 1280, 960')
        g('set output "overview.png"')
        print "Writing plots to overview.png"
    else:
        g('set terminal xterm')
    g('set multiplot')
    timedm_plot = TimeDMPlot(g)
    dmsnr_plot  = DMSNRPlot(g)
    dmhist_plot = DMHistPlot(g)
    timedm_plot.plot(categories)
    dmsnr_plot.plot(categories)
    dmhist_plot.plot(beam_hists)
    g('unset multiplot')
    
    if interactive:
        raw_input('Please press return to close...\n')
        
    print "Done"
