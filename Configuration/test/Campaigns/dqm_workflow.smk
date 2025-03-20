include: "cmssw_nodes.smk"
import re

outbasedir = job_dict["output"].split('/Relay')[0]
relay = job_dict["relay"]
calibdir = f'{outbasedir}/calibrations/'

rule step_JOBREPORT:
    params:
        cfgurl = cfgurl
    input: 
        rules.step_RAW2DIGI.output.report,
        rules.step_DIGI2DQM.output.report,
        env = rules.step_SCRAM.output.env,
    output:
        report = "jobreport.json"
    shell: 
        """
        source {input.env}
        python $CMSSW_BASE/src/HGCalCommissioning/Configuration/test/jobReportBuilder.py -i ./ -j {params.cfgurl} -o {output.report}
        """


rule step_STORE:
    input :
        rules.step_DIGI2DQM.output,
        rules.step_JOBREPORT.output
    params:
        mycopy = "cp -v" if job_dict["output"].find('/eos/cms/')<0 else "eos root://eoscms.cern.ch cp",
        outdir = f'{job_dict["output"]}',
        tag = f'{job_dict["run"]}_{job_dict["lumisection"]}',
        dqmtag = f'V{job_dict["lumisection"]:04d}_HGCAL_R{job_dict["run"]:09d}'
    log:
        "store.txt"
    shell:
        """
        echo "Transferring output results > {log}"

	#prepare output

        #ROOT files
        {params.mycopy} {rules.step_DQM.output.root} {params.outdir}/DQM_{params.dqmtag}.root >> {log}
        #{params.mycopy} {rules.step_RECO.output.root} {params.outdir}/RECO_{params.tag}.root >> {log}

        #Report
        {params.mycopy} {rules.step_JOBREPORT.output.report} {params.outdir}/reports/job_{params.tag}.json >> {log}
        """

rule all:
    input:
        rules.step_SCRAM.output,
        rules.step_RAW2DIGI.output,
        rules.step_DIGI2DQM.output,
        rules.step_DIGI2DQM_upload.log,
        rules.step_JOBREPORT.output,
        rules.step_STORE.log