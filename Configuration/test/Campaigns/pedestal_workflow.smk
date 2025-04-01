#
# PEDESTAL WORKFLOW: after unpacking we want the result of the DQM analysis to be uploaded and the NANOAOD of the DIGIs
# The final derivation of pedestals, noise and ZS parameters is made based on the NANOAOD file
#

from globals import defineGlobals
cfgurl, job_dict, common_params = defineGlobals(workflow)

module base_workflows:
    snakefile:
        "cmssw_base.smk"

use rule step_SCRAM from base_workflows as step_SCRAM

use rule step_RAW2DIGI from base_workflows as step_UNPACK with:
    params:
      **common_params,
      cfg = "HGCalCommissioning/Configuration/test/step_RAW2NANODQM.py"
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
        calibout=f'{job_dict["output"]}/calibrations'
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
        python3 scripts/HGCALPedestals.py -i {params.nanodir} -o {params.calibout} --forceRewrite
                
        #
        # CMSSW L0 calib file
        #
        python3 scripts/PrepareLevel0CalibParams.py \
            -p {params.calibout}/pedestals.json \
            -o {params.calibout}/level0_calib_params_Run{params.run}.json

        #
        # ECON-D ZS files
        #
        for f in 0 3; do
            echo "Generating ECON-D ZS for f=${{f}}"  >> {log}
            python3 scripts/HGCALECONDZS.py  -i {params.calibout}/pedestals.json --mipSF 0 \
                --P_CM_correction True  -F ${{f}} -o {params.calibout}/pedestals_econzsreg_P_N${{f}}_CM.json;
            python3 scripts/HGCALECONDZS.py -i {params.calibout}/pedestals.json --mipSF 0 \
                --onlyPedestals True  -F ${{f}} -o {params.calibout}/pedestals_econzsreg_P_N${{f}}.json;
        done

        cd -
        echo "Calibrations stored in {params.calibout}" >> {log}
        """


rule all:
    input:
        rules.step_SCRAM.output,
        rules.step_UNPACK.output,
        rules.step_JOBREPORT.output,
        rules.step_DQM_upload.log,
        rules.step_STORE.log,
        rules.step_PEDESTALS.log
