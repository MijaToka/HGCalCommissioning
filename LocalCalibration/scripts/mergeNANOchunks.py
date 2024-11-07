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
    parser.add_argument("-s", "--chunksize",
                        help='size of chunks to merge [GB]=%(default)s',
                        type=float, default=2)
    parser.add_argument("--dryRun",
                        help='identify chunks and print commands',
                        action='store_true')
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

        #group in chunks of size `chunksize`
        fsizes=[ float(os.path.getsize(f)) * 1e-9 for f in flist]
        cursize=0
        curchunk=[]
        chunks=[]
        for f,fs in zip(flist,fsizes):
            cursize += fs
            curchunk.append(f)
            #close current chunk if size surpasses target
            if cursize > args.chunksize:
                chunks.append(curchunk.copy())
                curchunk.clear()
                cursize=0
        if len(curchunk)>0: chunks.append(curchunk.copy())
        nchunks = len(chunks)

        print(f'Found {nchunks} to merge for run {r}')
        for ichunk, chunkflist in enumerate(chunks):
            
            flist_str = ' '.join(chunkflist)
            cmd=f'haddnano.py {args.input}/NANO_{run}_merge{ichunk}.root {flist_str}'
            if args.dryRun:
                print(cmd)
            else:
                os.system(cmd)

        #move fragments to chunks
        if not args.dryRun:
            for f in flist:
                mvcmd = f'mv {f} {outdir}'
                os.system(mvcmd)

if __name__ == '__main__':
    main()
