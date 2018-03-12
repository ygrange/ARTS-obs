# Author: Daniel van der Schuur, Leon Oostrum
# Usage: -r I,Q,U,V
# Default values in firmware are 1,1,1,1

unbs="$1"

if [ "$unbs" == "" ]; then
    echo "Specify uniboards as range, e.g. $0 2:15"
    exit
fi

ssh -t arts@192.168.3.74 python /home/arts/SVN/UniBoard/trunk/Software/python/peripherals/util_dp_gain.py --unb $unbs --fn 0:3 --bn 0:3 -n 0 | grep REG_DP_GAIN_I