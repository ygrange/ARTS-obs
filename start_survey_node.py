#!/usr/bin/env python
#
# Script to set up a full survey mode observation on the ARTS cluster
# Should only be used on the worker nodes
# Author: L.C. Oostrum

import os
import sys
import socket
from time import sleep

import yaml
import numpy as np


class Survey(object):
    """Start a survey mode observation on ARTS. This class runs the relevant commands on the current node
    """

    def __init__(self, config):
        """
        config: dict with settings, as generated by the master script
        """
        # set hostname and config
        self.hostname = socket.gethostname()
        self.config = config
        
        # how long to sleep between commands
        waittime = 0.5

        # check CB
        expected_CB = int(self.hostname[5:7]) - 1
        if not self.config['beam'] == expected_CB:
            self.log("WARNING: Requested to record CB {}, expected CB {}".format(self.config['beam'], expected_CB))        

        # create directory for log files
        os.system("mkdir -p {}".format(self.config['log_dir']))

        # start the programmes
        # remove running ringbuffers, AMBER, etc.
        self.clean()
        sleep(waittime)
        # create ringbuffer
        self.ringbuffer()
        sleep(waittime)
        # start readers depending on observing mode
        if self.config['obs_mode'] == 'scrub':
            self.scrub()
        elif self.config['obs_mode'] == 'dump':
            self.dump()
        elif self.config['obs_mode'] == 'fil':
            self.dadafilterbank()
        elif self.config['obs_mode'] == 'fits':
            self.dadafits()
        elif self.config['obs_mode'] == 'amber':
            self.amber()
        elif self.config['obs_mode'] == 'survey':
            self.survey()
        sleep(waittime)
        # start fill ringbuffer
        self.fill_ringbuffer()
        sleep(waittime)
        # Everything has been started
        self.log("Everything started")
        # flush stdout
        sys.stdout.flush()
        # proc trigger command
        if self.config['proctrigger']:
            cmd = "mkdir -p {output_dir}/triggers".format(**self.config)
            os.system(cmd)
            self.log("Waiting for finish, then processing triggers")
            cmd = "pid=$(pgrep fill_ringbuffer); tail --pid=$pid -f /dev/null; sleep 5; {script_dir}/process_triggers.sh {output_dir}/triggers {output_dir}/filterbank/CB{beam:02d}.fil {amber_dir}/CB{beam:02d} {master_dir} {snrmin}".format(script_dir=os.path.dirname(os.path.realpath(__file__)), **self.config)
            self.log(cmd)
            sys.stdout.flush()
            os.system(cmd)


    def log(self, message):
        """
        Log a message. Prints the hostname, then the message
        """
        print "{}: {}".format(self.hostname, message)


    def clean(self):
        self.log("Removing old ringbuffers")
        cmd = "dada_db -d -k {dadakey} 2>/dev/null; pkill fill_ringbuffer".format(**self.config)
        self.log(cmd)
        os.system(cmd)


    def ringbuffer(self):
        self.log("Starting ringbuffers")
        cmd = "dada_db -k {dadakey} -b {buffersize} -n {nbuffer} -p -r {nreader} 2>&1 > {log_dir}/dada_db.{beam} &".format(**self.config)
        self.log(cmd)
        os.system(cmd)


    def fill_ringbuffer(self):
        self.log("Starting fill_ringbuffer")
        cmd = ("fill_ringbuffer -k {dadakey} -s {startpacket} -d {duration}"
               " -p {network_port} -h {header} -l {log_dir}/fill_ringbuffer.{beam} &").format(**self.config)
        self.log(cmd)
        os.system(cmd)


    def scrub(self):
        self.log("Starting dada_dbscrubber")
        cmd = "dada_dbscrubber -k {dadakey} > {log_dir}/dada_dbscrubber.{beam} &".format(**self.config)
        self.log(cmd)
        os.system(cmd)


    def dump(self):
        self.log("Starting dada_dbdisk")
        output_dir = os.path.join(self.config['output_dir'], 'dada')
        os.system("mkdir -p {}".format(output_dir))
        cmd = "dada_dbdisk -k {dadakey} -D {output_prefix} > {log_dir}/dada_dbdisk.{beam} &".format(output_prefix=output_dir, **self.config)
        self.log(cmd)
        os.system(cmd)


    def dadafilterbank(self):
        self.log("Starting dadafilterbank")
        output_dir = os.path.join(self.config['output_dir'], 'filterbank')
        os.system("mkdir -p {}".format(output_dir))
        output_prefix = os.path.join(output_dir, 'CB{:02d}'.format(self.config['beam']))
        cmd = "dadafilterbank -k {dadakey} -n {output_prefix} -l {log_dir}/dadafilterbank.{beam} &".format(output_prefix=output_prefix, **self.config)
        self.log(cmd)
        os.system(cmd)


    def dadafits(self):
        self.log("Starting dadafits")
        output_dir = os.path.join(self.config['output_dir'], 'fits', 'CB{:02d}'.format(self.config['beam']))
        os.system("mkdir -p {}".format(output_dir))
        #dadafits -k <hexadecimal key> -l <logfile> -t <template> -d <output_directory>
        cmd = "dadafits -k {dadakey} -l {log_dir}/dadafits.{beam} -t {fits_templates} -d {output_fits} &".format(output_fits=output_dir, **self.config)
        self.log(cmd)
        os.system(cmd)


    def amber(self):
        self.log("Starting AMBER")
        os.system("mkdir -p {}".format(self.config['amber_dir']))
        # load AMBER config
        with open(self.config['amber_config'], 'r') as f:
            cfg = yaml.load(f)
        # load config for specified dedispersion mode
        ambercfg = cfg[self.config['amber_mode']]
        # add output prefix
        ambercfg['output_prefix'] = os.path.join(self.config['amber_dir'], 'CB{:02d}'.format(self.config['beam']))

        if self.config['amber_mode'] == 'bruteforce':
            self.log("Starting amber in bruteforce mode")
            # loop over the amber configs for the GPUs
            for ind in range(len(ambercfg['opencl_device'])):
                # make dict with fullconfig, because AMBER settings are spread over the general and node-specific config files
                fullconfig = ambercfg.copy()
                fullconfig.update(self.config)
                # set the settings for this GPU
                for key in ['dm_first', 'dm_step', 'num_dm', 'opencl_device']:
                    fullconfig[key] = ambercfg[key][ind]

                cmd = ("amber -opencl_platform {opencl_platform} -opencl_device {opencl_device} -device_name {device_name} -padding_file {amber_conf_dir}/padding.conf"
                       " -zapped_channels {amber_conf_dir}/zapped_channels.conf -integration_steps {amber_conf_dir}/integration_steps.conf -dedispersion_file"
                       " {amber_conf_dir}/dedispersion.conf -integration_file {amber_conf_dir}/integration.conf -snr_file {amber_conf_dir}/snr.conf -dms {num_dm}"
                       " -dm_first {dm_first} -dm_step {dm_step} -threshold {snrmin} -output {output_prefix}_step{ind} -beams 1 -synthesized_beams 1"
                       " -dada -dada_key {dadakey} -batches {nbatch} 2>&1 > {log_dir}/amber_{ind}.{beam} &").format(ind=ind+1, **fullconfig)
                self.log(cmd)
                os.system(cmd)
        elif self.config['amber_mode'] == 'subband':
            self.log("Starting amber in subband mode")
            # loop over the amber configs for the GPUs
            for ind in range(len(ambercfg['opencl_device'])):
                # make dict with fullconfig, because AMBER settings are spread over the general and node-specific config files
                fullconfig = ambercfg.copy()
                fullconfig.update(self.config)
                # set the settings for this GPU
                for key in ['dm_first', 'dm_step', 'num_dm', 'opencl_device', 'device_name', 'subbands', 'subbanding_dm_first', 'subbanding_dm_step', 'subbanding_dms']:
                    fullconfig[key] = ambercfg[key][ind]

                cmd = ("amber -opencl_platform {opencl_platform} -opencl_device {opencl_device} -device_name {device_name} -padding_file {amber_conf_dir}/padding.conf"
                       " -zapped_channels {amber_conf_dir}/zapped_channels.conf -integration_steps {amber_conf_dir}/integration_steps.conf -subband_dedispersion"
                       " -dedispersion_stepone_file {amber_conf_dir}/dedispersion_stepone.conf -dedispersion_steptwo_file {amber_conf_dir}/dedispersion_steptwo.conf"
                       " -integration_file {amber_conf_dir}/integration.conf -snr_file {amber_conf_dir}/snr.conf -dms {num_dm} -dm_first {dm_first} -dm_step {dm_step}"
                       " -subbands {subbands} -subbanding_dms {subbanding_dms} -subbanding_dm_first {subbanding_dm_first} -subbanding_dm_step {subbanding_dm_step}"
                       " -threshold {snrmin} -output {output_prefix}_step{ind} -beams 1 -synthesized_beams 1"
                       " -dada -dada_key {dadakey} -batches {nbatch} 2>&1 > {log_dir}/amber_{ind}.{beam} &").format(ind=ind+1, **fullconfig)
                self.log(cmd)
                os.system(cmd)


    def survey(self):
        self.amber()
        self.dadafilterbank()
        self.dadafits()


if __name__ == '__main__':
    # first argument is the config file
    # no need for something like argparse as this script should always be called
    # from the master node, i.e. the commandline format is fixed
    conf_file = os.path.join(os.path.realpath(os.path.dirname(__file__)), sys.argv[1])

    # load config
    with open(conf_file, 'r') as f:
        config = yaml.load(f)

    # start observation
    Survey(config)
    
