"""One JSON request per worker process; stdout is exclusively JSON events."""
import json, sys, traceback
from pathlib import Path
# Embedded Windows Python omits the script directory from sys.path.
# Resolve only our own trusted backend directory, never the working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import Engine, Cancelled, digest
from segmentation import diagnostics, download

def emit(**data): print(json.dumps(data),flush=True)

def main():
    import os
    if os.environ.get('CUTLAB_RUNTIME'):
        ai=Path(os.environ['CUTLAB_RUNTIME'])/'ai'
        if (ai/'complete.json').exists():sys.path.insert(0,str(ai))
    request=json.loads(sys.stdin.readline()); engine=Engine(request['cache'],emit,request.get('cancel'))
    op=request['op']; p=request.get('project',{})
    if op=='setup-ai':
        from setup_ai import install
        result=install(engine)
    elif op=='diagnostics': result=diagnostics(engine.root)
    elif op=='download': result=download(engine)
    elif op=='import': result=engine.import_media(request['path'])
    elif op=='frame': result=engine.frame(p,request['index'])
    elif op=='mask': result=engine.masks(p)
    elif op=='preview':
        result=engine.render(p,engine.root/('preview-'+digest(p)+'.mp4'),True)
    elif op=='export': result=engine.render(p,request['path'])
    else: raise ValueError('Unknown worker operation')
    emit(result=result)
if __name__=='__main__':
    try: main()
    except Cancelled as e: emit(error=str(e),cancelled=True); sys.exit(2)
    except Exception as e:
        traceback.print_exc(file=sys.stderr); emit(error=str(e)); sys.exit(1)
