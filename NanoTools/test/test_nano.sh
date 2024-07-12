cmsDriver.py NANO \
    --data \
    -s USER:HGCalCommissioning/NanoTools/hgcSysValNano_cff.hgcSysValNanoTask \
    --customise HGCalCommissioning/NanoTools/hgcSysValNano_cff.customise_hgcalmapper_test \
    --datatier NANOAOD \
    --eventcontent NANOAOD \
    --filein file:/afs/cern.ch/user/p/psilva/public/TB2024/output.root \
    --fileout nano.root \
    -n -1 \
    --conditions auto:phase2_realistic_T25 \
    --geometry Extended2026D99 \
    --era Phase2C17I13M9 \
    --python_filename nanocmsdriver_cfg.py \
    --no_exec
#--nThreads 4 \
