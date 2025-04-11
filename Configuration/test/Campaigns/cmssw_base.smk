#get the global parameters to use
from globals import defineGlobals
cfgurl, job_dict, common_params = defineGlobals(workflow)

#set the working directory for the job
workdir: 
    job_dict['localdir'] if 'localdir' in job_dict else os.getcwd()

##
## PREPARE ENVIRONMENT STEP
##
rule step_SCRAM:
    params :
        cmsswpath = re.findall( "(.*CMSSW_.*/src/)", os.path.dirname(workflow.basedir) )[0]
    output:
        env = "cmssw_env.sh"
    log:
        "step_SCRAM.log"
    shell:
        """
        echo "CMSSW base will be set to {params.cmsswpath}" > {log}
        echo "Creating script {output.env}" >> {log}
        set +u
        echo "#!/bin/bash" > {output.env}
        echo "set +u" >> {output.env}
        echo "[ -z \\"\\$CMS_PATH\\" ] && source /cvmfs/cms.cern.ch/cmsset_default.sh" >> {output.env}
        echo "export SITECONFIG_PATH=/cvmfs/cms.cern.ch/SITECONF/T2_CH_CERN" >> {output.env}
        echo "cd {params.cmsswpath}" >> {output.env}
        echo "eval \\`scramv1 runtime -sh\\`" >> {output.env}
        echo "cd -" >> {output.env}
        source {output.env}
        echo "CMS_PATH=$CMS_PATH" >> {log}
        echo "CMSSW_BASE=$CMSSW_BASE" >> {log}
        root --version >> {log} 2>&1
        """

##
## UNPACKING STEP
##
rule step_RAW2DIGI:
    params:
        **common_params,
        cfg = "HGCalCommissioning/Configuration/test/step_RAW2DIGI.py",
        extra = ""
    log:
        "step_RAW2DIGI.log"
    input: 
        rules.step_SCRAM.output.env
    output:
       "RAW2DIGI.root"
    shell:
        """
        source {input}
        maxEvents={params.maxEvents}
        cmsRun -j FrameworkJobReport_RAW2DIGI.xml $CMSSW_BASE/src/{params.cfg} \
                run={params.run} lumi={params.lumi} era={params.era} \
                files={params.inputFiles} inputTrigFiles={params.inputTrigFiles} yamls={params.yamls} \
                output={output} maxEvents=${{maxEvents}} {params.extra}
        #CMSSW appends numEvents to the file name if maxEvents!=-1
        #force the file name to be always the same
        if [ "$maxEvents" != "-1" ]; then
           targetout={output}
           targetmatch=${{targetout/.root/*.root}}
           localmatches=(`ls $targetmatch 2>/dev/null`)        
           localout="${{localmatches[0]}}"
           if [ "$localout" != "$targetout" ]; then
             echo "Changing $localout to $targetout"
             mv -v $localout $targetout;
           fi
        fi
        """

##
## STANDALONE RECO
##
rule step_RECO:
    params:
        **common_params,        
        cfg = "HGCalCommissioning/Configuration/test/step_RECO.py",
        inputfiles = "files=file:RAW2DIGI.root"
    input: 
        rules.step_SCRAM.output.env        
    output:
        "RECO.root"
    shell: 
        """
        source {input.env}
        cmsRun -j FrameworkJobReport_RECO.xml $CMSSW_BASE/src/{params.cfg} \
	       era={params.era} run={params.run} {params.inputfiles} maxEvents=-1 gpu=false output={output}
        """

##
## STANDALONE NANO
##
rule step_NANO:
    params:
        **common_params,        
        cfg = "HGCalCommissioning/Configuration/test/step_NANO.py",
        inputfiles = "files=file:RECO.root secondaryFiles=file:RAW2DIGI.root"
    input: 
        rules.step_SCRAM.output.env        
    output:
        "NANO.root"
    shell: 
        """
        source {input.env}
        cmsRun -j FrameworkJobReport_NANO.xml $CMSSW_BASE/src/{params.cfg} \
	       era={params.era} run={params.run} {params.inputfiles} maxEvents=-1 skipRecHits=false output={output}
        """

##
## STANDALONE DQM
##
rule step_DQM:
    params:
        run = f'{job_dict["run"]}',
        era = f'{job_dict["era"]}',
        cfg = "$CMSSW_BASE/src/HGCalCommissioning/Configuration/test/step_DQM.py",
        inputfiles = "files=file:RECO.root secondaryFiles=file:RAW2DIGI.root"
    input:
        rules.step_SCRAM.output.env
    log :
        "step_DQM.log"
    output:
        "FrameworkJobReport_DQM.xml"
    shell: 
        """
        source {input}
        cmsRun -j {output} $CMSSW_BASE/src/{params.cfg}\
               run={params.run} era={params.era} {params.inputfiles} maxEvents=-1
        """

##
## DQM UPLOAD
##
rule step_DQM_upload:
    params:
        **common_params,
        dqmserver = job_dict['dqmserver'] if 'dqmserver' in job_dict else "http://hgc-vm-2024.cern.ch:8070/dqm/online-dev"
    log:
        "step_DQMUPLOAD.log"
    shell: 
        """
        source {input[0]}
	dqmfiles=(`ls DQM*HGCAL*root`)
        visDQMUpload.py {params.dqmserver} ${{dqmfiles[0]}} >> {log}
        """

##
## FINAL JOB REPORT
## 
rule step_JOBREPORT:
    params:
        cfgurl = cfgurl
    log:
        "step_JOBREPORT.log"
    input: 
        rules.step_SCRAM.output.env
    output:
       "jobreport.json"
    shell:
        """
        source {input}
        python $CMSSW_BASE/src/HGCalCommissioning/Configuration/test/jobReportBuilder.py -i ./ -j {params.cfgurl} -o {output}
        """

##
## TRANSFER RESULTS TO STORE
##
rule step_STORE:
    params:
        mycopy = "cp -v" if job_dict["output"].find('/eos/cms/')<0 else "eos root://eoscms.cern.ch cp",
        outdir = f'{job_dict["output"]}',
        tag = f'{job_dict["run"]}_{job_dict["lumisection"]}',
        defaultdqmtag = f'V{1:04d}_HGCAL_R{job_dict["run"]:09d}',
        dqmtag = f'V{job_dict["lumisection"]:04d}_HGCAL_R{job_dict["run"]:09d}'
    log:
        "step_STORE.log"
    shell:
        """
        echo "Transferring output results > {log}"

        #ROOT files
	edmfiles=(`ls *.root`)
        for f in ${{edmfiles[@]}}; do
            if [[ $f == *"DQM"* ]]; then
               targetf=${{f/{params.defaultdqmtag}.root/{params.dqmtag}.rot}}
	    else
               targetf=${{f/.root/_{params.tag}.root}}
            fi
            {params.mycopy} ${{f}} {params.outdir}/${{targetf}} >> {log}
        done

        #Report
        {params.mycopy} jobreport.json {params.outdir}/reports/job_{params.tag}.json >> {log}
        """
