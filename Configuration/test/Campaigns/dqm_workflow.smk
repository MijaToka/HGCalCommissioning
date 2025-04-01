#
# DQM WORKFLOW: after unpacking DQM is imediately run
# The final content of the run directory are DQM files only
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
      cfg = "HGCalCommissioning/Configuration/test/step_RAW2DQM.py"
    output:
      "FrameworkJobReport_RAW2DIGI.xml"
    log:
      "step_RAW2DQM.log"

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

rule all:
    input:
        rules.step_SCRAM.output,
        rules.step_UNPACK.output,
        rules.step_JOBREPORT.output,
        rules.step_DQM_upload.log,
        rules.step_STORE.log
