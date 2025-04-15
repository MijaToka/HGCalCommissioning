#
# PEDESTAL WORKFLOW: after unpacking we want the result of the DQM analysis to be uploaded and the NANOAOD of the DIGIs
# The final derivation of pedestals, noise and ZS parameters is made based on the NANOAOD file
#

from globals import defineGlobals
cfgurl, job_dict, common_params = defineGlobals(workflow)
calib_out_dir = f'{job_dict["caliboutdir"]}/pedestals/Run{job_dict["run"]}'

module base_workflows:
    snakefile:
        "cmssw_base.smk"

use rule step_SCRAM from base_workflows as step_SCRAM

use rule step_RAW2DIGI from base_workflows as step_UNPACK with:
    params:
      **common_params,
      cfg = "HGCalCommissioning/Configuration/test/step_RAW2NANODQM.py",
      extra = "secondaryOutput=RAW2DIGI.root"
    log:
      "step_RAW2NANODQM.log"
    output:
      "NANO.root"
      

use rule step_DQM_upload from base_workflows as step_DQM_upload with :
    input :
       rules.step_SCRAM.output.env,
       rules.step_UNPACK.output

use rule step_JOBREPORT from base_workflows as step_JOBREPORT with:
    input :
      rules.step_SCRAM.output.env,
      rules.step_UNPACK.output

use rule step_STORE from base_workflows as step_STORE with:
    input :
      rules.step_SCRAM.output.env,
      rules.step_UNPACK.output,
      rules.step_JOBREPORT.output

##
## PEDESTAL ANALYSIS
##
rule step_PEDESTALS:
    params:
        **common_params,
        nanodir=job_dict["output"],
        calibout=calib_out_dir
    output:
        pedestals=f'{calib_out_dir}/pedestals.json',
        l0calibs=f'{calib_out_dir}/level0_calib_params.json'
    input:
        rules.step_STORE.log,
        env = rules.step_SCRAM.output.env,
    log:
        'step_PEDESTALS.log'
    shell:
        """	
        source {input.env}
        cd $CMSSW_BASE/src/HGCalCommissioning/LocalCalibration

        #
        # Pedestal analysis
        #
	echo "Running pedestals" > {log}
        python3 scripts/HGCalPedestals.py -i {params.nanodir} -o {params.calibout} --forceRewrite
                
        #
        # CMSSW L0 calib file
        #
        python3 scripts/PrepareLevel0CalibParams.py -p {output.pedestals} -o {output.l0calibs}
        """


##
## FE TRIMMING STEP
##
rule step_FETRIMMING:
    params:
        **common_params,
        nanodir=job_dict["output"],
        calibout=calib_out_dir
    input:        
        rules.step_STORE.log,
        env = rules.step_SCRAM.output.env,
        pedestals = rules.step_PEDESTALS.output.pedestals
    log:
        'step_FETRIMMING.log'
    shell:
        """
        source {input.env}
        cd $CMSSW_BASE/src/HGCalCommissioning/LocalCalibration

        #
        # HGCROC Thresholds and pedestals for trigger cells
        #
        echo "Generating HGCROC Thresholds and pedestals for trigger cells"
        python3 python/HGCROCconfig/HGCROCInterface.py -p data/TCNoiseMap.json -j {input.pedestals} -o {params.calibout}

        #
        # ECON-D ZS files
        #
        for f in 0 3; do
            echo "Generating ECON-D ZS for f=${{f}}"  >> {log}
            python3 scripts/HGCalECONDZS.py  -i {input.pedestals} --mipSF 0 \
                --P_CM_correction True  -F ${{f}} -o {params.calibout}/pedestals_econzsreg_P_N${{f}}_CM.json;
            python3 scripts/HGCalECONDZS.py -i {input.pedestals} --mipSF 0 \
                --onlyPedestals True  -F ${{f}} -o {params.calibout}/pedestals_econzsreg_P_N${{f}}.json;
        done

        cd -
        echo "FE trimming stored in {params.calibout}" >> {log}
        """


##
## PEDESTALS CLOSURE STEP
##
rule step_PEDESTALS_closure:
    params:
        **common_params,
        edminput="RAW2DIGI.root"
    input:        
        rules.step_STORE.log,
        env = rules.step_SCRAM.output.env,
        l0calibs = rules.step_PEDESTALS.output.l0calibs,
        pedestals = rules.step_PEDESTALS.output.pedestals
    log:
        'step_PEDESTALS_closure.log'
    output:
        "NANO_closure.root"
    shell:
        """
        source {input.env}
        cmsRun -j FrameworkJobReport_RECONANO.xml $CMSSW_BASE/src/HGCalCommissioning/Configuration/test/step_RECONANO.py \
             era={params.era} run={params.run} files=file:{params.edminput} calibfile={input.l0calibs} output={output} > {log} 2>&1
        cd $CMSSW_BASE/src/HGCalCommissioning/LocalCalibration
        python3 scripts/HGCalPedestalsClosure.py -i {output} -p {input.pedestals} >> {log} 2>&1
        cd -
        echo "Pedestals closure done" >> {log} 2>&1
        """

rule all:
    input:
        rules.step_SCRAM.output,
        rules.step_UNPACK.output,
        rules.step_JOBREPORT.output,
        rules.step_DQM_upload.log,
        rules.step_STORE.log,
        rules.step_PEDESTALS.output,
        rules.step_PEDESTALS_closure.output,
        rules.step_FETRIMMING.log
