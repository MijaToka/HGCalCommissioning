include: "cmssw_env.smk"
import json
import os
import re

cfgurl=workflow.config_settings.configfiles[0]
with open(cfgurl,'r') as cfg:
    job_dict = json.load(cfg)

rule step_REPORTCOLLECTOR:
    params:
        resultsdir = f"{job_dict['input']}",
        reportsdir = f"{job_dict['input']}/reports"
    input:
        env = rules.step_SCRAM.output.env
    output:
        report = "run_report.json",
        dqmcollector = "dqmcollector.feather"
    shell: 
        """
        source {input.env}
        python3 $CMSSW_BASE/src/HGCalCommissioning/Configuration/test/runJobReportCollector.py -i {params.reportsdir} -o {output.report}
	python3 $CMSSW_BASE/src//HGCalCommissioning/DQM/test/dqm_collector.py -i {params.resultsdir} -o {output.dqmcollector}
	cp -v {output.report} {params.reportsdir}/
	cp -v {output.dqmcollector} {params.reportsdir}/
        """

rule all:
    input:
        rules.step_SCRAM.output,
        rules.step_REPORTCOLLECTOR.output