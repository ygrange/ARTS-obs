#!/usr/bin/env bash
#
# Script to set process AMBER triggers on each worker node
# Author: L.C. Oostrum


triggerscript=$HOME/software/arts-analysis/triggers.py
preproc=$HOME/software/arts-analysis/preprocess.py
classifier=$HOME/software/single_pulse_ml/single_pulse_ml/run_single_pulse_DL.py
plotter=$HOME/ARTS-obs/plotter.py

ntrig=1000000
cmap=viridis
ntime_plot=250
nfreq_plot=32
ndm=1
fmt=hdf5
dmmin=5

outputdir=$1
filfile=$2
prefix=$3
snrmin=$4

# create master trigger files
cat ${prefix}_step*trigger > ${prefix}.trigger

# make sure we start clean
rm -f $outputdir/*hdf5
rm -f $outputdir/plots/*pdf
mkdir -p $outputdir/plots
cd $outputdir
source $HOME/venv/bin/activate
# process the triggers without making plots
#python $triggerscript --sig_thresh $snrmin --ndm $ndm --save_data $fmt --mk_plot --ntrig $ntrig --nfreq_plot $nfreq_plot --ntime_plot $ntime_plot --cmap $cmap $filfile $prefix.trigger
python $triggerscript --dm_thresh $dmmin --sig_thresh $snrmin --ndm $ndm --save_data $fmt --ntrig $ntrig --nfreq_plot $nfreq_plot --ntime_plot $ntime_plot --cmap $cmap $filfile ${prefix}.trigger
# concatenate hdf5 files
python $preproc --fnout combined.hdf5 --nfreq_f $nfreq_plot --ntime_f $ntime_plot $(pwd)
deactivate
# run the classifier
spack unload cuda
spack load cuda@9.0
source /export/astron/oostrum/tensorflow/bin/activate
python $classifier combined.hdf5
deactivate
# make plots
source $HOME/venv/bin/activate
python $plotter combinefreq_time_candidates.hdf5
deactivate
# merge 
nands=$(ls plots | wc -l)
if [ $ncands -eq 0 ]; then
    touch candidates.pdf
else
    gs -dBATCH -dNOPAUSE -q -sDEVICE=pdfwrite -sOutputFile=candidates.pdf plots/*pdf
fi
# email
$HOME/bin/emailer candidates.pdf
