#!/bin/bash

#parse command line
while getopts "s:j:i:c:" opt; do
    case "$opt" in
	s) WORKFLOW=$OPTARG
	   ;;
        j) TASKSPEC=$OPTARG
            ;;
        i) INDEX=$OPTARG
           ;;
        c) CALIBPATH=$OPTARG
           ;;
    esac
done

WORKDIR=`pwd`
echo "Work directory is ${WORKDIR}"
echo "Calib path is ${CALIBPATH}"

#setup environment
cd $CALIBPATH
source /cvmfs/cms.cern.ch/cmsset_default.sh
eval `scramv1 runtime -sh`
echo "CMSSW_BASE is ${CMSSW_BASE}"

#execute task
python3 scripts/HGCALCalibTaskWrapper.py -j $TASKSPEC -s $WORKFLOW --idx $INDEX
cd -      
