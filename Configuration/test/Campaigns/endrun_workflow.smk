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
        cmssw_output=f"{job_dict['input']}",
        reference=f"{job_dict['reference']}",
        calib_output=f"{job_dict['calib_output']}",
        localrecoregistry=f"{job_dict['localrecoregistry']}"
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
        
        #try running the calibration manager (if jobs are not yet all done it will not do anything)
        cd $CMSSW_BASE/src/HGCalCommissioning/LocalCalibration
        python3 scripts/HGCalCalibrationManager.py  -i {params.localrecoregistry} -o {params.calib_output} -r {params.reference}
        cd -
        """

rule all:
    input:
        rules.step_SCRAM.output,
        rules.step_REPORTCOLLECTOR.output