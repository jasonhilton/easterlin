#!/bin/bash

cd $PBS_O_WORKDIR


#PATH=$PBS_O_PATH
source /home/jdh4g10/.bash_profile

#echo $PATH

#module load numpy

module load python/3.5.1

# unicode problems with click module for python 3.x means the below is necessary.
export LC_ALL=en_GB.utf-8
export LANG=en_GB.utf-8


#PYTHONPATH=/home/jdh4g10/.local/lib/python2.7/site-packages:$PYTHONPATH



#echo $PATH
#echo $PYTHONPATH


np=$1 # number processes
runs=$2 # total runs

instance=$((PBS_VNODENUM ))
#seed=$RANDOM



# get most recently dated folder in the results directory
out_dir=`ls -d results/*/ | tail -1`

for j in `seq -f "%03g" $instance $np $runs`;
do
 python run_sim.py --param-file inputs/params_$j.yaml --design-point-number $j\
  --out-dir $out_dir --simulation-length 350
done
