"""SAM 2.1 integration pinned to official source; never substitutes fake masks."""
import contextlib, hashlib, importlib.util, json, os, shutil, subprocess, sys, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image

MODEL_URL='https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_tiny.pt'
MODEL_REV='2b90b9f5ceec907a1c18123530e92e794ad901a4'

def diagnostics(root):
    runtime=os.environ.get('CUTLAB_RUNTIME','')
    available=bool(runtime and list((Path(runtime)/'model-wheel').glob('*.whl')))
    data=dict(setupAvailable=available,python=sys.version.split()[0],ffmpeg=shutil.which('ffmpeg'),ffprobe=shutil.which('ffprobe'),
              sam2=bool(importlib.util.find_spec('sam2')),torch=bool(importlib.util.find_spec('torch')),
              weights=(Path(root)/'models'/'sam2.1_hiera_tiny.pt').exists(),cuda=False,gpu=None,vramGB=None,
              model=dict(name='SAM 2.1 Hiera Tiny',parameters='38.9M',download='~156 MB (149 MiB)',license='Apache-2.0',
                         source='https://github.com/facebookresearch/sam2',url=MODEL_URL,revision=MODEL_REV))
    if data['torch']:
        import torch
        data['torchVersion']=torch.__version__; data['cuda']=torch.cuda.is_available()
        if data['cuda']:
            props=torch.cuda.get_device_properties(0); data.update(gpu=props.name,vramGB=round(props.total_memory/2**30,2))
    try:
        r=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader'],capture_output=True,text=True,timeout=10)
        if r.returncode==0: data['nvidia']=r.stdout.strip()
    except (OSError,subprocess.TimeoutExpired): pass
    return data

def download(engine):
    folder=engine.root/'models'; folder.mkdir(exist_ok=True)
    final=folder/'sam2.1_hiera_tiny.pt'; part=folder/'download.partial'
    try:
        req=urllib.request.Request(MODEL_URL,headers={'User-Agent':'BANDKLAN-CUTLAB/0.1'})
        with urllib.request.urlopen(req,timeout=60) as response,part.open('wb') as out:
            total=int(response.headers.get('Content-Length',0)); n=0; sha=hashlib.sha256()
            while True:
                engine.check(); block=response.read(1024*1024)
                if not block: break
                out.write(block); sha.update(block); n+=len(block)
                engine.emit(stage=f'Downloading official weights: {n/1e6:.1f} MB',progress=n/total if total else 0)
            if total and n!=total: raise RuntimeError('Incomplete model download; retry.')
            if n<100_000_000: raise RuntimeError('Unexpected model response size; download rejected.')
        part.replace(final)
        (folder/'download.json').write_text(json.dumps(dict(url=MODEL_URL,bytes=n,sha256=sha.hexdigest(),revision=MODEL_REV)))
        return diagnostics(engine.root)
    finally: part.unlink(missing_ok=True)

def segment(engine,seg,prompts,output):
    d=diagnostics(engine.root)
    if not d['torch'] or not d['sam2']: raise RuntimeError('SAM 2 is not installed. Run scripts/setup-model.ps1; see docs/WINDOWS.md.')
    if not d['weights']: raise RuntimeError('Model weights are missing. Open Model Setup and explicitly download the Tiny checkpoint (~156 MB).')
    if not prompts or not any(p['label']==1 for p in prompts): raise ValueError('Add a positive subject click before tracking.')
    import torch
    from sam2.build_sam import build_sam2_video_predictor
    # SAM internally resizes to 512. This supported override lowers inference cost;
    # Tiny architecture uses dynamic feature sizes; test quality on your footage.
    device='cuda' if torch.cuda.is_available() else 'cpu'
    engine.emit(stage=f'Loading real SAM 2 Tiny on {device}; this can take time',progress=0)
    predictor=build_sam2_video_predictor('configs/sam2.1/sam2.1_hiera_t.yaml',
        str(engine.root/'models'/'sam2.1_hiera_tiny.pt'),device=device,
        hydra_overrides_extra=['++model.image_size=512','++model.add_all_frames_to_correct_as_cond=true',
                               '++model.clear_non_cond_mem_around_input=true'],apply_postprocessing=False)
    jpg=Path(seg['folder'])/'inference'; jpg.mkdir(exist_ok=True)
    ratio=min(1,640/seg['width'],640/seg['height']); size=(max(1,round(seg['width']*ratio)),max(1,round(seg['height']*ratio)))
    for i in range(seg['count']):
        engine.check(); path=jpg/f'{i:06d}.jpg'
        if not path.exists():
            with Image.open(Path(seg['frames'])/f'{i:06d}.png') as im: im.convert('RGB').resize(size).save(path,quality=95)
    # Float32 on Turing (RTX 2070); no assumption of BF16 support or real-time inference.
    with torch.inference_mode():
        state=predictor.init_state(str(jpg),offload_video_to_cpu=True,offload_state_to_cpu=True)
        grouped={}
        for p in prompts:
            f=int(p['frame'])
            if not 0<=f<seg['count']: raise ValueError('A prompt lies outside the trim. Clear prompts after changing trim.')
            if p['label'] not in (0,1) or not 0<=p['x']<=1 or not 0<=p['y']<=1: raise ValueError('Invalid normalized mask prompt.')
            grouped.setdefault(f,[]).append(p)
        seed=min(f for f,points in grouped.items() if any(p['label']==1 for p in points))
        def add(f):
            points=grouped[f]; engine.check()
            predictor.add_new_points_or_box(state,frame_idx=f,obj_id=1,
                points=np.array([[p['x']*size[0],p['y']*size[1]] for p in points],dtype=np.float32),
                labels=np.array([p['label'] for p in points],dtype=np.int32))
        def propagate(first,base,span,save):
            seen=set()
            for reverse in (False,True):
                for i,ids,logits in predictor.propagate_in_video(state,start_frame_idx=first,reverse=reverse):
                    engine.check()
                    if save:
                        mask=(logits[0,0]>0).cpu().numpy().astype(np.uint8)*255
                        Image.fromarray(mask).save(output/f'{i:06d}.png')
                    seen.add(i)
                    engine.emit(stage=f'Tracking subject ({device})' if base==0 else f'Repropagating corrections ({device})',
                                progress=base+span*len(seen)/seg['count'])
            if len(seen)!=seg['count']: raise RuntimeError('Tracker did not produce every frame; mask cache not committed.')
        add(seed)
        corrections=[f for f in sorted(grouped) if f!=seed]
        # First establish tracked state. Negative-only corrections on another frame
        # must edit an existing track, not initialize an unrelated empty object.
        propagate(seed,0,.5 if corrections else 1,not corrections)
        if corrections:
            for f in corrections: add(f)
            propagate(min(grouped),.5,.5,True)
