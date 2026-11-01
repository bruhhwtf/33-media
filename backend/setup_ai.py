"""Explicit, transactional first-run AI installation into the private app runtime."""
import json,os,shutil,subprocess,sys,tempfile,time
from pathlib import Path
from segmentation import diagnostics,download

def pip_steps(runtime,stage):
    wheels=list((runtime/'model-wheel').glob('*.whl'))
    if len(wheels)!=1:raise RuntimeError('The installer is missing the SAM wheel. Reinstall CUTLAB.')
    common=[sys.executable,'-m','pip','install','--disable-pip-version-check','--no-warn-script-location','--no-user','--target',str(stage)]
    # No compiler or Git on end-user machines. Build pure Python dependencies with
    # bundled setuptools/wheel, then install the prebuilt SAM wheel without deps.
    return [common+['--no-deps','torch==2.5.1','torchvision==0.20.1','--index-url','https://download.pytorch.org/whl/cu124'],
            common+['--no-build-isolation','filelock==3.18.0','typing_extensions==4.15.0','networkx==3.4.2','jinja2==3.1.6','fsspec==2025.3.0','sympy==1.13.1','mpmath==1.3.0','MarkupSafe==3.0.3','hydra-core==1.3.2','omegaconf==2.3.0','iopath==0.1.10','tqdm==4.67.1','PyYAML==6.0.3','portalocker==3.2.0','antlr4-python3-runtime==4.9.3'],
            common+['--no-deps',str(wheels[0])]]

def install(engine):
    if sys.platform!='win32':raise RuntimeError('Automatic AI setup is available in the Windows installer. See the development setup guide for other platforms.')
    runtime=Path(os.environ.get('CUTLAB_RUNTIME',''))
    if not (runtime/'python'/'python.exe').is_file():raise RuntimeError('Bundled runtime not found. Install the Windows release to use automatic setup.')
    ai=runtime/'ai';stage=runtime/'ai.partial'
    if not (ai/'complete.json').exists():
        if shutil.disk_usage(runtime).free<10*1024**3:raise RuntimeError('Free at least 10 GB for AI installation, then retry.')
        shutil.rmtree(stage,ignore_errors=True);stage.mkdir()
        try:
            steps=pip_steps(runtime,stage)
            for index,args in enumerate(steps):
                engine.check();engine.emit(stage=f'Installing AI packages ({index+1}/{len(steps)}). Downloads may take several minutes.',progress=index/4)
                # File-backed output cannot fill a subprocess pipe during large installs.
                with tempfile.TemporaryFile() as log:
                    proc=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=log,stderr=log,env={**os.environ,'PIP_NO_INPUT':'1'})
                    try:
                        last=0
                        while proc.poll() is None:
                            engine.check();time.sleep(.1)
                            if time.monotonic()-last>1:
                                last=time.monotonic();engine.emit(stage=f'Installing AI packages ({index+1}/3). Please wait; you can cancel safely.',progress=index/4)
                        if proc.returncode:
                            log.seek(0);raise RuntimeError('AI dependency setup failed. Retry after checking network/disk space. '+log.read().decode(errors='replace')[-2500:])
                    finally:
                        if proc.poll() is None:proc.kill();proc.wait()
            engine.check()
            # Import validation in a fresh process before committing partial packages.
            check="import sys;sys.path.insert(0,sys.argv[1]);import torch,torchvision,sam2;print(torch.__version__)"
            engine.run([sys.executable,'-c',check,str(stage)])
            (stage/'complete.json').write_text(json.dumps({'version':1,'torch':'2.5.1'}))
            shutil.rmtree(ai,ignore_errors=True);stage.replace(ai)
        finally:shutil.rmtree(stage,ignore_errors=True)
    sys.path.insert(0,str(ai))
    # Official checkpoint transfer has its own cancellation and partial cleanup.
    if not (engine.root/'models'/'sam2.1_hiera_tiny.pt').exists():download(engine)
    return diagnostics(engine.root)
