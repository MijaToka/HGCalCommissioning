#!/bin/bash

#see https://github.com/cms-sw/cmssw/blob/master/Configuration/Geometry/README.md for reference
GEOMETRY=ExtendedRun4D101
ERA=Phase2C17I13M9
CONDITIONS=auto:phase2_realistic_T25
nevts=1000
simonly=0
avg_pileup=0

#parse command line options
SHORT=c:,m:,n:,s:,o:,a:,p:,l:,b:,h
LONG=cmssw:,mcm:,nevts:,simonly:,output:,aged:,pileup_input:,avg_pileup:,bias:,help
OPTS=$(getopt -a -n weather --options $SHORT --longoptions $LONG -- "$@")
eval set -- "$OPTS"
while :
do
  case "$1" in
    -c | --cmssw )
      cmssw="$2"
      shift 2
      ;;
    -m | --mcm )
      mcmfragment="$2"
      shift 2
      ;;
    -n | --nevts )
      nevts="$2"
      shift 2
      ;;
    -s | --simonly )
      simonly="$2"
      shift 2
      ;;
    -o | --output )
      output="$2"
      shift 2
      ;;
    -a | --aged )
      aged="$2"
      shift 2
      ;;
    -p | --pileup_input )
      pileup_input="$2"
      shift 2
      ;;
    -l | --avg_pileup )
      avg_pileup="$2"
      shift 2
      ;;
    -b | --bias )
      bias=$2
      shift 2
      ;;
    -h | --help)
      echo ""
      echo "runLocalGeneration.sh -c cmssw_dir -m mcm_fragment -n nevts -s simonlyflag -o output -a aged -b bias"
      echo "Some examples are the following"
      echo "  mcm_fragment = min.bias EGM-Run3Summer19GS-00020 "
      echo "                 ttbar L1T-PhaseIITDRSpring19GS-00005"
      echo "  simonlyflag = 0/1, if 1 will stop after SIM and copy it to the output"
      echo "  aged - vanilla (no aging/realistic effects"
      echo "       - startup SimCalorimetry/HGCalSimProducers/hgcalDigitizer_cfi.HGCal_setRealisticStartupNoise"
      echo "       - 3/ab SimCalorimetry/HGCalSimProducers/hgcalDigitizer_cfi.HGCal_setEndOfLifeNoise"
      echo "  bias - if given applies a bias as defined in DPGAnalysis/HGCalTools/python/endcapbias_cfi.py"
      echo ""
      exit 2
      ;;
    --)
      shift;
      break
      ;;
    *)
      echo "Unexpected option: $1"
      ;;
  esac
done

#setup CMSSW
work=`pwd`
cd ${cmssw}
source /cvmfs/cms.cern.ch/cmsset_default.sh
cmsenv

# Download fragment from McM
if [[ "$mcmfragment" == *"/python/"* ]]; then
    echo "This is a standard configuration file so we won't download it from MCM"
    cfg=$mcmfragment
else
    cfg=Configuration/GenProduction/python/${mcmfragment}-fragment.py
    if [ -f $cfg ]; then
        echo "MCM fragment file already exists, using available"
    else
        echo "This is a MCM fragment, getting it from the webserver"
        curl -s -k https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get_fragment/${mcmfragment} --retry 3 --create-dirs -o ${cfg}
        [ -s ${cfg} ] || exit $?;
    fi
fi
ls ${cfg}
scram b
cd ../..
cd ${work}

#run generation
if [ -z ${bias} ]; then
    costumise_bias=""
else
    costumise_bias="--customise DPGAnalysis/HGCalTools/endcapbias_cfi.${bias}"
fi
cmsDriver.py ${cfg} -s GEN,SIM -n ${nevts} \
             --conditions ${CONDITIONS} --geometry ${GEOMETRY} --era ${ERA} ${costumise_bias} \
             --eventcontent FEVTDEBUG --beamspot HLLHC --datatier GEN-SIM --fileout file:step1.root \
             --customise_command "from IOMC.RandomEngine.RandomServiceHelper import RandomNumberServiceHelper; randSvc = RandomNumberServiceHelper(process.RandomNumberGeneratorService); randSvc.populate();" 

if [ $simonly == "1" ]; then
    echo "This is a simonly production - moving to output"
    mv -v step1.root ${output}
    exit -1
fi

#run digitization
if [ $aged == "vanilla" ]; then
    echo "No customisation will be applied - vanilla digis will run"
else
    aging_customise="--customise ${aged}"
    echo "Aging will be customised with ${aging_customise}"
fi
if [ -z $avg_pileup ] || [ -z $pileup_input ]; then
    echo "No pileup scenario"
else
    echo "Will generate average pileup of ${avg_pileup} with files from ${pileup_input}"
    pileup_input=`find ${pileup_input} -iname "*.root" -printf "file:%h/%f,"`
    pileup_input=${pileup_input::-1}
    pileup_costumise="--pileup AVE_${avg_pileup}_BX_25ns --pileup_input ${pileup_input}"
fi
cmsDriver.py step2 -s DIGI:pdigi_valid,L1TrackTrigger,L1,DIGI2RAW,HLT:@fake2 \
             --conditions ${CONDITIONS} --geometry ${GEOMETRY} --era ${ERA} \
             --eventcontent FEVTDEBUG --datatier GEN-SIM-DIGI-RAW -n -1 --filein file:step1.root --fileout file:step2.root \
             ${aging_customise} ${pileup_costumise}

#run reconstruction step
cmsDriver.py step3 -s RAW2DIGI,RECO,RECOSIM \
             --conditions ${CONDITIONS} --geometry ${GEOMETRY} --era ${ERA} \
             --eventcontent FEVTDEBUG --datatier GEN-SIM-RECO -n -1 --filein file:step2.root --fileout file:step3.root

mv -v step3.root ${output}
