#
# TRIMMING SCAN WORKFLOW: for each scan point we want to unpack and store the result
# the final analysis is made on the NANOAOD files
#

from globals import defineGlobals
cfgurl, job_dict, common_params = defineGlobals(workflow)

module base_workflows:
    snakefile:
        "cmssw_base.smk"

use rule step_SCRAM from base_workflows as step_SCRAM

use rule step_RAW2DIGI from base_workflows as step_RAW2NANO with:
    params:
      **common_params,
      cfg = "HGCalCommissioning/Configuration/test/step_RAW2NANO.py",
      extra = ""
    log:
      "step_RAW2NANO.log"
    output:
      "NANO.root"

use rule step_JOBREPORT from base_workflows as step_JOBREPORT with:
    input :
      rules.step_SCRAM.output.env,
      rules.step_RAW2NANO.output

use rule step_STORE from base_workflows as step_STORE with:
    input :
      rules.step_SCRAM.output.env,
      rules.step_RAW2NANO.output,
      rules.step_JOBREPORT.output

rule all:
    input:
        rules.step_SCRAM.output,
        rules.step_RAW2NANO.output,
        rules.step_JOBREPORT.output,
        rules.step_STORE.log