import os
import argparse
import glob
import re

def main():
    ### NOTE : do it by max size expected...

    #parse arguments and add as class attributes                                                                                                          
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input",
		        help='input directory=%(default)s',
                        default="/eos/cms/store/group/dpg_hgcal/tb_hgcal/2024/hgcalrd/Test/Run1726262667/508ef3fc-7218-11ef-bf09-b8ca3af74182/v1/")
    args=parser.parse_args()

    nanofiles = glob.glob(f'{args.input}/NANO*.root')
    if len(nanofiles)==0 : return

    outdir=args.input+'/Chunks'
    os.system(f'mkdir -p {outdir}')

    #identify runs fron NANO files names
    runlist = {}
    for f in nanofiles:
        run = re.findall('NANO_(\d+)_.*.root',f)[0]
        if not run in runlist: runlist[run]=[]
        runlist[run].append(f)

    #merge runs individually
    for r, flist in runlist.items():
        if len(flist)<2 : continue
        flist_str = ' '.join(flist)

        cmd=f'haddnano.py {args.input}/NANO_{run}.root {flist_str}'
        os.system(cmd)

        #move fragments to chunks
        for f in flist:
            mvcmd = f'mv {f} {outdir}'
            os.system(mvcmd)

if __name__ == '__main__':
    main()
