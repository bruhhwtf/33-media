"""Disk-backed media pipeline; no UI dependency. All times in normalized CFR seconds."""
import hashlib, json, math, os, shutil, subprocess, tempfile, time
from pathlib import Path
from PIL import Image
from compositor import compose, DEFAULTS

class Cancelled(Exception): pass

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()[:24]

class Engine:
    def __init__(self, root, emit=lambda **kw: None, cancel=None):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
        self.emit=emit; self.cancel=Path(cancel) if cancel else None
    def check(self):
        if self.cancel and self.cancel.exists(): raise Cancelled('Cancelled; partial outputs removed.')
    def run(self,args):
        self.check()
        with tempfile.TemporaryFile() as err:
            p=subprocess.Popen([str(x) for x in args],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=err)
            try:
                # ffprobe is small; ffmpeg stdout is unused (-nostats).
                while p.poll() is None:
                    self.check(); time.sleep(.05)
                output=p.stdout.read()
                if p.returncode:
                    err.seek(0); raise RuntimeError(err.read().decode(errors='replace')[-4000:])
                return output
            finally:
                if p.poll() is None: p.kill(); p.wait()
                p.stdout.close()
    def probe(self,path):
        path=Path(path).resolve()
        if not path.is_file(): raise ValueError('Source is missing. Use Relink to choose the original MP4.')
        d=json.loads(self.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',path]))
        v=next((s for s in d['streams'] if s['codec_type']=='video'),None)
        if not v: raise ValueError('No video stream in this file.')
        def rate(r):
            a,b=map(float,r.split('/')); return a/b if b else 0
        fps=rate(v.get('avg_frame_rate','0/1')) or rate(v.get('r_frame_rate','30/1')) or 30
        return dict(source=str(path),duration=float(d['format']['duration']),width=v['width'],height=v['height'],
                    fps=fps,outputFps=min(30,max(1,fps)),audio=any(s['codec_type']=='audio' for s in d['streams']),
                    vfr= v.get('avg_frame_rate')!=v.get('r_frame_rate'),size=path.stat().st_size,mtime=path.stat().st_mtime_ns)
    def import_media(self,path):
        meta=self.probe(path); folder=self.root/('source-'+digest(meta)); folder.mkdir(exist_ok=True)
        proxy=folder/'proxy.mp4'; partial=folder/'proxy.partial.mp4'
        if not proxy.exists():
            self.emit(stage='Creating playback proxy',progress=0)
            try:
                self.run(['ffmpeg','-v','error','-nostdin','-y','-i',meta['source'],'-map','0:v:0','-map','0:a:0?',
                          '-vf',f"scale=w='trunc(min(iw,ih*dar)/2)*2':h='trunc(min(ih,iw/dar)/2)*2',setsar=1,scale=w='min(960,iw)':h='min(540,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2,fps={meta['outputFps']}",
                          '-c:v','libx264','-preset','ultrafast','-crf','24','-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart',partial])
                partial.replace(proxy)
            finally: partial.unlink(missing_ok=True)
        return {**meta,'proxy':str(proxy)}
    def prepare(self,p):
        meta=self.probe(p['source']); start=float(p['trim']['start']); end=float(p['trim']['end'])
        if not (0<=start<end<=meta['duration']+.001): raise ValueError('Trim must be inside the source duration.')
        if end-start>10.001: raise ValueError('Version 1 supports segments up to 10 seconds. Shorten the trim.')
        fps=meta['outputFps']; count=max(1,math.ceil((end-start)*fps-1e-6))
        key=digest([meta,start,end,fps,'cfr-v2'])
        folder=self.root/('segment-'+key); manifest=folder/'segment.json'
        if manifest.exists(): return json.loads(manifest.read_text())
        folder.mkdir(exist_ok=True); frames=folder/'frames'; frames.mkdir(exist_ok=True)
        self.emit(stage='Normalizing source frames',progress=0)
        try:
            self.run(['ffmpeg','-v','error','-nostdin','-y','-i',meta['source'],'-an','-vf',
                      f'trim=start={start}:end={end},setpts=PTS-STARTPTS,fps=fps={fps}:start_time=0,scale=w=trunc(min(iw\\,ih*dar)/2)*2:h=trunc(min(ih\\,iw/dar)/2)*2,setsar=1',
                      '-frames:v',str(count),'-start_number','0',frames/'%06d.png'])
            files=list(frames.glob('*.png')); count=min(count,len(files))
            if not count: raise ValueError('Trim contains no decodable frames.')
            with Image.open(frames/'000000.png') as image: first=image.copy()
            segment=dict(key=key,folder=str(folder),frames=str(frames),count=count,fps=fps,width=first.width,height=first.height,
                         start=start,duration=count/fps,source=meta['source'],audio=meta['audio'])
            manifest.write_text(json.dumps(segment)); return segment
        except BaseException:
            shutil.rmtree(folder,ignore_errors=True); raise
    def mask_key(self,seg,p):
        return digest([seg['key'],p.get('prompts',[]),'sam2.1-tiny-2b90b9-image512-corrections-v2'])
    def complete_masks(self,folder,count):
        return (folder/'complete.json').exists() and all((folder/f'{i:06d}.png').is_file() for i in range(count))
    def masks(self,p):
        from segmentation import segment
        seg=self.prepare(p); key=self.mask_key(seg,p); folder=Path(seg['folder'])/('masks-'+key)
        if not self.complete_masks(folder,seg['count']):
            stage=folder.with_name(folder.name+'.partial'); shutil.rmtree(stage,ignore_errors=True); stage.mkdir()
            try:
                segment(self,seg,p.get('prompts',[]),stage)
                (stage/'complete.json').write_text(json.dumps(dict(key=key,count=seg['count'])))
                if folder.exists(): shutil.rmtree(folder)
                stage.replace(folder)
            finally: shutil.rmtree(stage,ignore_errors=True)
        return dict(segment=seg,maskDir=str(folder),maskKey=key)
    def frame(self,p,index):
        seg=self.prepare(p); index=max(0,min(seg['count']-1,int(index)))
        maskdir=Path(seg['folder'])/('masks-'+self.mask_key(seg,p))
        mask=maskdir/f'{index:06d}.png'
        return dict(segment=seg,index=index,image=str(Path(seg['frames'])/f'{index:06d}.png'),mask=str(mask) if mask.exists() else None)
    def render(self,p,destination,preview=False):
        seg=self.prepare(p); s={**DEFAULTS,**p.get('effects',{})}
        if int(s['count'])<0 or int(s['count'])>5: raise ValueError('Duplicate count must be 0–5.')
        maskdir=Path(seg['folder'])/('masks-'+self.mask_key(seg,p))
        if s['count'] and not self.complete_masks(maskdir,seg['count']): raise ValueError('Mask cache is missing, incomplete or stale. Mask Subject before rendering echoes.')
        target=Path(destination).resolve()
        if target==Path(p['source']).resolve(): raise ValueError('Export cannot overwrite the source.')
        if target.exists() and not preview: raise ValueError('Destination exists. Choose a new filename to protect existing media.')
        target.parent.mkdir(parents=True,exist_ok=True)
        staging=Path(tempfile.mkdtemp(prefix='render-',dir=self.root))
        partial=staging/'result.mp4'
        ratio=min(1,640/seg['width'],360/seg['height']) if preview else 1
        size=(max(2,int(seg['width']*ratio)//2*2),max(2,int(seg['height']*ratio)//2*2))
        def frame(i):
            with Image.open(Path(seg['frames'])/f'{i:06d}.png') as im: return im.convert('RGB').resize(size,Image.Resampling.LANCZOS)
        def mask(i):
            with Image.open(maskdir/f'{i:06d}.png') as im: return im.copy()
        try:
            for i in range(seg['count']):
                self.check(); compose(frame(i),i,seg['fps'],frame,mask,s).save(staging/f'{i:06d}.png')
                self.emit(stage='Compositing preview' if preview else 'Compositing export',progress=(i+1)/seg['count']*.85)
            args=['ffmpeg','-v','error','-nostdin','-y','-framerate',str(seg['fps']),'-start_number','0','-i',str(staging/'%06d.png')]
            if seg['audio']:
                args+=['-ss',str(seg['start']),'-i',seg['source'],'-map','0:v:0','-map','1:a:0',
                       '-af',f"aresample=async=1:first_pts=0,apad,atrim=duration={seg['duration']}",'-c:a','aac','-b:a','192k']
            args+=['-t',str(seg['duration']),'-c:v','libx264','-preset','fast','-crf',str(p.get('export',{}).get('crf',18)),
                   '-pix_fmt','yuv420p','-movflags','+faststart',str(partial)]
            self.emit(stage='Encoding H.264 / AAC',progress=.9); self.run(args); self.check()
            # Preview is app-owned; exports are exclusive even if a file appears during rendering.
            if preview: os.replace(partial,target)
            else:
                with target.open('xb') as out, partial.open('rb') as inp:
                    try:
                        while block:=inp.read(1024*1024):
                            self.check(); out.write(block)
                    except BaseException: out.close(); target.unlink(missing_ok=True); raise
            return dict(path=str(target),duration=seg['duration'],frames=seg['count'],fps=seg['fps'],width=size[0],height=size[1])
        finally: shutil.rmtree(staging,ignore_errors=True)
