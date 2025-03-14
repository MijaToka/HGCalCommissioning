import json
import os
import re

snakefile_dir = os.path.dirname(workflow.basedir)

rule step_SCRAM:
    params :
        cmsswpath = re.findall( "(.*CMSSW_.*/src/)", snakefile_dir )[0]
    output:
        env = "cmssw_env.sh"
    log:
        "scramdone.txt"
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
