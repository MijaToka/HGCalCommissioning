#
# RUN END WORKFLOW:
# - build the computing report (from the available FrameworkJobReport summaries)
# - build the DQM collector report (from the available DQM files)
#

from globals import defineGlobals
cfgurl, job_dict, common_params = defineGlobals(workflow)

module base_workflows:
    snakefile:
        "cmssw_base.smk"
	
use rule step_SCRAM from base_workflows as step_SCRAM

rule step_REPORTCOLLECTOR:
    params:
        **common_params,
        cmssw_output=f'{job_dict['input']}'
    input:
        env = rules.step_SCRAM.output.env
    output:
        report = "run_report.json",
        dqmcollector = "dqmcollector.feather"
    shell: 
        """
        source {input.env}
        python3 $CMSSW_BASE/src/HGCalCommissioning/Configuration/test/runJobReportCollector.py \
		-i {params.cmssw_output}/reports -o {output.report}
	python3 $CMSSW_BASE/src//HGCalCommissioning/DQM/test/dqm_collector.py -i {params.cmssw_output} -o {output.dqmcollector}
	cp -v {output.report} {params.cmssw_output}/reports/
	cp -v {output.dqmcollector} {params.cmssw_output}/reports/
        """

rule all:
    input:
        rules.step_SCRAM.output,
        rules.step_REPORTCOLLECTOR.output