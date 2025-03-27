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
        rules.step_DIGI2DQM_upload.log,
        rules.step_DIGI2NANO.output.report,
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
        rules.step_DIGI2NANO.output,
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
        {params.mycopy} {rules.step_DIGI2DQM.output.root} {params.outdir}/DQM_{params.dqmtag}.root >> {log}
        {params.mycopy} {rules.step_DIGI2NANO.output.root} {params.outdir}/NANO_{params.tag}.root >> {log}	

        #Report
        {params.mycopy} {rules.step_JOBREPORT.output.report} {params.outdir}/reports/job_{params.tag}.json >> {log}
        """


rule step_CALIBRATION:
    params:
        pedfile = f"{calibdir}/Relay{relay}/pedestals.json",
        econdcmnargs = f'-i {calibdir}/Relay{relay}/pedestals.json --mipSF 0'
    input:
        env = rules.step_SCRAM.output.env,
        upload = rules.step_STORE.log
    log:
        'calibration.txt'
    shell:
        """
	
        source {input.env}
        cd $CMSSW_BASE/src/HGCalCommissioning/LocalCalibration

        #
        # Pedestal and pedestal closure analyses
        #
	echo "Running pedestals and pedestals closure" > {log}
        python3 scripts/HGCALPedestals.py -r {relay} -i {outbasedir} -o {calibdir} --forceRewrite
        #python3 scripts/HGCALPedestalsClosure.py -r {relay} -i {outbasedir} -o {calibdir} --forceRewrite
                
        #
        # CMSSW L0 calib file
        #
        python3 scripts/PrepareLevel0CalibParams.py --cm 2 \
            -p {params.pedfile}\
            -o {calibdir}/Relay{relay}/level0_calib_params.json

        #
        # ECON-D ZS files
        #
        for f in 0 3; do
            echo "Generating ECON-D ZS for f=${{f}}"  >> {log}
            python3 scripts/HGCALECONDZS.py  {params.econdcmnargs} \
                --P_CM_correction True  -F ${{f}} -o {calibdir}/Relay{relay}/pedestals_econzsreg_P_N${{f}}_CM2.json;
            python3 scripts/HGCALECONDZS.py {params.econdcmnargs} \
                --onlyPedestals True  -F ${{f}} -o {calibdir}/Relay{relay}/pedestals_econzsreg_P_N${{f}}.json; 
        done

        cd -
        echo "Calibrations stored in {calibdir}" >> {log}
        """


rule all:
    input:
        rules.step_SCRAM.output,
        rules.step_RAW2DIGI.output,
        rules.step_DIGI2DQM.output,
        rules.step_DIGI2DQM_upload.log,
        rules.step_DIGI2NANO.output,
        rules.step_JOBREPORT.output,
        rules.step_STORE.log,
        rules.step_CALIBRATION.log