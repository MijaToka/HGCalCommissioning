include: "cmssw_env.smk"
import json
import os

cfgurl=workflow.config_settings.configfiles[0]
with open(cfgurl,'r') as cfg:
    job_dict = json.load(cfg)

workdir: 
    job_dict['localdir'] if 'localdir' in job_dict else os.getcwd()
    

##
## UNPACKING WORKFLOW
##
rule step_RAW2DIGI:
    params:        
        run = f'{job_dict["run"]}',
        lumi = f'{job_dict["lumisection"]}',
        era = f'{job_dict["era"]}',
        inputFiles = ','.join(job_dict["input"][1:]),
        inputTrigFiles = ','.join( [job_dict["input"][0],] ),
        yamls = f'\"{job_dict["yaml"]}\"',
        cfg = "$CMSSW_BASE/src/HGCalCommissioning/Configuration/test/step_RAW2DIGI.py",
        maxEvents = job_dict['maxevents'] if 'maxevents' in job_dict else -1
    input: 
        env = rules.step_SCRAM.output.env
    output:
        root = "RAW2DIGI.root",
        report = "FrameworkJobReport_RAW2DIGI.xml"
    shell: 
        """
        source {input.env}
        cmsRun -j {output.report} \
               {params.cfg} run={params.run} lumi={params.lumi} era={params.era} \
               files={params.inputFiles} inputTrigFiles={params.inputTrigFiles} yamls={params.yamls} \
               output={output.root} maxEvents={params.maxEvents}
        #CMSSW appends numEvents to the file name if maxEvents!=-1
        #force the file name to be always the same
        targetout={output.root}
        targetmatch=${{targetout/.root/*.root}}
	localmatches=(`ls $targetmatch`)
	localout="${{localmatches[0]}}"
	if [ "$localout" != "$targetout" ]; then
	   echo "Changing $localout to $targetout"
	   mv -v $localout $targetout;
	fi
        """

##
## RECO WORKFLOW
##
rule step_RECO:
    params:
        era = f'{job_dict["era"]}',
        run = f'{job_dict["run"]}',
        cfg = "$CMSSW_BASE/src/HGCalCommissioning/Configuration/test/step_RECO.py"
    input: 
        env = rules.step_SCRAM.output.env,
        root = rules.step_RAW2DIGI.output.root
    output:
        report = "FrameworkJobReport_RECO.xml",
        root = "RECO.root"
    shell: 
        """
        source {input.env}
	    cmsRun -j {output.report} \
	       {params.cfg} era={params.era} run={params.run} files=file:{input.root} maxEvents=-1 gpu=false output={output.root}
        """


##
## DQM WORKFLOWS
##
rule step_DIGI2DQM:
    params:
        run = f'{job_dict["run"]}',
        era = f'{job_dict["era"]}',
        cfg = "$CMSSW_BASE/src/HGCalCommissioning/Configuration/test/step_DQM.py",
        dqm = f'DQM_V0001_HGCAL_R{job_dict["run"]}.root'
    input: 
        env = rules.step_SCRAM.output.env,
        rawroot = rules.step_RAW2DIGI.output.root
    output:
        report = "FrameworkJobReport_DQM.xml",
        root = "DQM.root"
    shell: 
        """
        source {input.env}
        cmsRun -j {output.report} \
               {params.cfg} run={params.run} era={params.era} files=file:{input.rawroot} maxEvents=-1
        mv {params.dqm} {output.root}
        """

rule step_DIGI2DQM_upload:
    params:
        run = f'{job_dict["run"]}',
        dqmtag = f'V{job_dict["lumisection"]:04d}_HGCAL_R{job_dict["run"]:09d}',
        dqmuploadtag = f'V0001_HGCAL_R{job_dict["run"]:09d}',
        dqmserver = job_dict['dqmserver'] if 'dqmserver' in job_dict else "http://hgc-vm-2024.cern.ch:8070/dqm/online-dev"
    input:
        env = rules.step_SCRAM.output.env,
        root = rules.step_DIGI2DQM.output.root
    log:
        "digi2dqmupload.done"
    shell: 
        """
        source {input.env}
        cp -v {input.root} DQM_{params.dqmtag}.root > {log}
        cp -v {input.root} DQM_{params.dqmuploadtag}.root >> {log}
	visDQMUpload.py {params.dqmserver} DQM_{params.dqmuploadtag}.root > {log}
	rm -v DQM_{params.dqmuploadtag}.root >> {log}
        """


rule step_DQM:
    params:
        run = f'{job_dict["run"]}',
        era = f'{job_dict["era"]}',
        cfg = "$CMSSW_BASE/src/HGCalCommissioning/Configuration/test/step_DQM.py",
        dqm = f'DQM_V0001_HGCAL_R{job_dict["run"]}.root'
    input: 
        env = rules.step_SCRAM.output.env,
        root = rules.step_RECO.output.root,
        rawroot = rules.step_RAW2DIGI.output.root
    output:
        report = "FrameworkJobReport_DQM.xml",
        root = "DQM.root"
    shell: 
        """
        source {input.env}
        cmsRun -j {output.report} \
               {params.cfg} run={params.run} era={params.era} files=file:{input.root} secondaryFiles=file:{input.rawroot} maxEvents=-1
        mv {params.dqm} {output.root}
        """

rule step_DQM_upload:
    params:
        run = f'{job_dict["run"]}',
        dqmtag = f'V{job_dict["lumisection"]:04d}_HGCAL_R{job_dict["run"]:09d}',
        dqmuploadtag = f'V0001_HGCAL_R{job_dict["run"]:09d}',
        dqmserver = job_dict['dqmserver'] if 'dqmserver' in job_dict else "http://hgc-vm-2024.cern.ch:8070/dqm/online-dev"
    input:
        env = rules.step_SCRAM.output.env,
        root = rules.step_DQM.output.root
    log:
        "dqmupload.done"
    shell: 
        """
        source {input.env}
        cp -v {input.root} DQM_{params.dqmtag}.root > {log}
        cp -v {input.root} DQM_{params.dqmuploadtag}.root >> {log}
	visDQMUpload.py {params.dqmserver} DQM_{params.dqmuploadtag}.root > {log}
	rm -v DQM_{params.dqmuploadtag}.root >> {log}
        """


##
## NANO WORKFLOW
##	
rule step_NANO:
    params:
        era = f'{job_dict["era"]}',
        run = f'{job_dict["run"]}',
        cfg = "$CMSSW_BASE/src/HGCalCommissioning/Configuration/test/step_NANO.py"
    input: 
        env = rules.step_SCRAM.output.env,
        root = rules.step_RECO.output.root
    output:
        report = "FrameworkJobReport_NANO.xml",
        root = "NANO.root"
    shell: 
        """
        source {input.env}
        cmsRun -j {output.report} \
               {params.cfg} era={params.era} run={params.run} files=file:{input.root} skipRecHits=false maxEvents=-1
        """
