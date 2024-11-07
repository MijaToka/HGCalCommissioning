import os
import sys
import re
import subprocess

relaydir=sys.argv[1]
chunksdir=f'{relaydir}/histofiller/Chunks'
if not os.path.isdir(chunksdir):
    print(f'No directory {chunksdir}')
    sys.exit(-1)
    
module_chunks={}
for f in os.listdir(chunksdir):
    typecode,ix = re.findall(f'(.*)_ix(\d+).root',f)[0]
    if not typecode in module_chunks:
        module_chunks[typecode]=[]
    module_chunks[typecode].append( os.path.join(chunksdir,f) )

histfillerdir=f'{relaydir}/histofiller'
for typecode, flist in module_chunks.items():
    result = subprocess.run(['hadd', '-ff', '-f','-k', f'{histfillerdir}/{typecode}.root'] + flist,
                            capture_output=True,
                            text=True)
    print(typecode)
    print(result.stdout)
    print(result.stderr)
