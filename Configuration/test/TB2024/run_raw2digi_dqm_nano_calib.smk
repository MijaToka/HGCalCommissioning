include: "run_common.snake"
import re

basedir = re.findall('(.*)/Run.*', job_dict["OutputDir"])[0]
relay = re.findall('.*/Run(\\d+)/*', job_dict["OutputDir"])[0]

rule step_JobReport:
    params:
        cfgurl = cfgurl
    input: 
        env = rules.scram.output.env,
        report_RAW2DIGI = {rules.step_RAW2DIGI.output.report},
        report_DQM = {rules.step_DQM.output.report},
        report_NANO = {rules.step_RAW2NANO.output.report},
    output:
        report = "jobreport.json"
    shell: 
        """
        source {input.env}
        python $CMSSW_BASE/src/HGCalCommissioning/Configuration/test/jobReportBuilder.py \
            --initialcfg {params.cfgurl} \
            --fwkreports {input.report_RAW2DIGI},{input.report_DQM},{input.report_NANO} \
            -o {output.report}
        """

rule step_Upload:
     input :
           rules.step_RAW2DIGI.output,
           rules.step_DQM.output,
           rules.step_RAW2NANO.output,
           rules.step_JobReport.output
     params:
        mycopy = "cp -v" if f'{job_dict["OutputDir"]}'.find('/eos/cms/')<0 else "eos root://eoscms.cern.ch cp",
        outdir = f'{job_dict["OutputDir"]}',
        tag = f'{job_dict["Run"]}_{job_dict["LumiSection"]}',
        dqmtag = f'V{job_dict["LumiSection"]:04d}_HGCAL_R{job_dict["Run"]:09d}'
     output:
        log = "upload.txt"
     shell:
        """
        #ROOT files
        {params.mycopy} {rules.step_RAW2DIGI.output.root} {params.outdir}/RAW2DIGI_{params.tag}.root > {output.log}
        {params.mycopy} {rules.step_DQM.output.root} {params.outdir}/DQM_{params.dqmtag}.root >> {output.log}
        {params.mycopy} {rules.step_RAW2NANO.output.root} {params.outdir}/NANO_{params.tag}.root >> {output.log}	
        #Reports (copy only the final report)
        {params.mycopy} {rules.step_JobReport.output.report} {params.outdir}/reports/job_{params.tag}.json >> {output.log}
        """

rule step_Calibration:
    params:
        basedir = basedir,
        run = relay,
        calibdict = str({"ped": f"{basedir}/calibrations/Run{relay}/pedestals.json"}).replace("'","\"")
    input:
        env = rules.scram.output.env,
        upload = rules.step_Upload.output
    output:
        log = 'calibration.txt'
    shell:
        """
        source {input.env}
        cd $CMSSW_BASE/src/HGCalCommissioning/LocalCalibration
        python3 scripts/HGCALPedestals.py -r {params.run} -i {params.basedir} \
            -o {params.basedir}/calibrations --forceRewrite
        python3 scripts/PrepareLevel0CalibParams.py -g 1 --cm 2 \
            -c '{params.calibdict}'\
            -o {params.basedir}/calibrations/Run{params.run}/level0_calib_params.json
        for f in 0 3; do  
            python3 scripts/HGCALECONDZS.py -i {params.basedir}/calibrations/Run{params.run}/pedestals.json \
                --P_CM_correction True --cmType 2 -F ${{f}} --mipSF 0 \
                -o {params.basedir}/calibrations/Run{params.run}/pedestals_econzsreg_P_N${{f}}_CM2.json ; 
            python3 scripts/HGCALECONDZS.py -i {params.basedir}/calibrations/Run{params.run}/pedestals.json \
                --onlyPedestals True  -F ${{f}} --mipSF 0 \
                -o {params.basedir}/calibrations/Run{params.run}/pedestals_econzsreg_P_N${{f}}.json ; 
        done
        cd -
        echo "Calibrations stored in {params.basedir}/calibrations/Run{params.run}" > {output.log}
        """


rule all:
    input:
        rules.scram.output,
        rules.step_RAW2DIGI.output,
        rules.step_DQM.output,
        rules.step_DQM_upload.output,
        rules.step_RAW2NANO.output,
        rules.step_Upload.output,
        rules.step_Calibration.output