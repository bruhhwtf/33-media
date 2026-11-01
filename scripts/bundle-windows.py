"""Run on Windows/Python 3.11 before electron-builder. No user Python install required."""
import hashlib,json,os,shutil,subprocess,sys,tempfile,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'vendor'/'runtime'; REV='2b90b9f5ceec907a1c18123530e92e794ad901a4'
def run(*args,**kwargs): subprocess.run(list(map(str,args)),check=True,**kwargs)
def fetch(url,path):
    with urllib.request.urlopen(url,timeout=120) as r,path.open('wb') as f: shutil.copyfileobj(r,f)
    return hashlib.sha256(path.read_bytes()).hexdigest()
def build():
    if sys.platform!='win32' or sys.version_info[:2]!=(3,11): raise SystemExit('Build on Windows x64 using Python 3.11.')
    if OUT.exists():shutil.rmtree(OUT)
    py=OUT/'python';py.mkdir(parents=True); receipts={}
    with tempfile.TemporaryDirectory() as td:
        tmp=Path(td);archive=tmp/'python.zip'
        url='https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip'
        receipts[url]=fetch(url,archive)
        with zipfile.ZipFile(archive) as z:z.extractall(py)
        (py/'python311._pth').write_text('python311.zip\n.\nLib/site-packages\nimport site\n')
        wheels=tmp/'pip';wheels.mkdir()
        run(sys.executable,'-m','pip','download','--no-deps','pip==25.0.1','-d',wheels)
        site=py/'Lib'/'site-packages';site.mkdir(parents=True)
        with zipfile.ZipFile(next(wheels.glob('*.whl'))) as z:z.extractall(site)
        exe=py/'python.exe'
        run(exe,'-m','pip','install','-r',ROOT/'backend'/'requirements.txt','setuptools==75.8.0','wheel==0.45.1')
        # Vendor a pure Python SAM wheel; users never need Git or a compiler.
        archive=tmp/'sam.zip';url=f'https://codeload.github.com/facebookresearch/sam2/zip/{REV}'
        receipts[url]=fetch(url,archive)
        with zipfile.ZipFile(archive) as z:z.extractall(tmp/'sam')
        source=next((tmp/'sam').iterdir()); wheelhouse=OUT/'model-wheel';wheelhouse.mkdir()
        run(exe,'-m','pip','wheel','--no-deps','--no-build-isolation',source,'-w',wheelhouse,env={**os.environ,'SAM2_BUILD_CUDA':'0'})
    bindir=OUT/'bin';bindir.mkdir()
    def node(expr):return subprocess.check_output(['node','-p',expr],cwd=ROOT,text=True).strip()
    ff=Path(node("require('ffmpeg-static')"));fp=Path(node("require('ffprobe-static').path"))
    shutil.copy2(ff,bindir/'ffmpeg.exe');shutil.copy2(fp,bindir/'ffprobe.exe')
    # Preserve supplied third party license notices and source/build references.
    notices=OUT/'licenses';notices.mkdir()
    for name in ('ffmpeg-static','ffprobe-static'):
        for file in (ROOT/'node_modules'/name).iterdir():
            if file.is_file() and ('license' in file.name.lower() or file.name.lower().startswith('readme')):shutil.copy2(file,notices/(name+'-'+file.name))
    (OUT/'receipts.json').write_text(json.dumps(receipts,indent=2))
    run(exe,'-c','import numpy,PIL,pip;print("Bundled Python OK")')
    run(bindir/'ffmpeg.exe','-version');run(bindir/'ffprobe.exe','-version')
if __name__=='__main__':build()
