"""Generated media and synthetic mask fixtures ONLY; not AI validation."""
import json, math, os, subprocess, sys, tempfile, unittest
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from engine import Engine, Cancelled
from compositor import compose, DEFAULTS

def ff(*args): subprocess.run(['ffmpeg','-v','error','-nostdin','-y',*map(str,args)],check=True)
def probe(p): return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)]))

class CompositorTests(unittest.TestCase):
    def test_identity(self):
        rng=np.random.default_rng(3); frame=Image.fromarray(rng.integers(0,256,(42,66,3),dtype=np.uint8))
        out=compose(frame,0,30,lambda i:None,lambda i:None,{'count':0})
        np.testing.assert_array_equal(np.array(out),np.array(frame))
    def test_matching_delayed_frame_and_mask_and_boundaries(self):
        calls=[]
        def frame(i): calls.append(('frame',i));return Image.new('RGB',(8,8),(10+i,20,30))
        def mask(i): calls.append(('mask',i));return Image.new('L',(8,8),255)
        s=dict(count=5,delay=2,dx=0,dy=0,opacity=1,falloff=1,feather=0,order='trails')
        out=compose(Image.new('RGB',(8,8)),3,30,frame,mask,s)
        self.assertEqual(calls,[('frame',1),('mask',1)])
        self.assertEqual(out.getpixel((4,4)),(11,20,30))
        calls.clear();compose(Image.new('RGB',(8,8)),0,30,frame,mask,s);self.assertEqual(calls,[])
    def test_subject_on_top(self):
        original=Image.new('RGB',(8,8),'red');old=Image.new('RGB',(8,8),'blue');white=Image.new('L',(8,8),255)
        out=compose(original,1,30,lambda _:old,lambda _:white,dict(count=1,delay=1,dx=0,feather=0,opacity=1))
        self.assertEqual(out.getpixel((4,4)),(255,0,0))
    def test_deterministic_texture(self):
        frame=Image.new('RGB',(64,48),'gray');s=dict(count=0,grain=.1,scanlines=.1,rgb=.01,bleed=.2,vignette=.3,border=.1)
        a=compose(frame,9,30,None,None,s);b=compose(frame,9,30,None,None,s);c=compose(frame,10,30,None,None,s)
        np.testing.assert_array_equal(a,b);self.assertFalse(np.array_equal(a,c))
    def test_scaled_preview_composition(self):
        large=Image.new('RGB',(960,540),(80,100,120))
        old=Image.new('RGB',(960,540),(190,70,60))
        mask=Image.new('L',(960,540));mask.paste(255,(300,90,550,480))
        settings=dict(count=2,delay=2,dx=.12,feather=3,grain=.02,scanlines=.03,rgb=.002,bleed=.1,vignette=.1,border=.04)
        full=compose(large,8,30,lambda _:old,lambda _:mask,settings)
        small=compose(large.resize((640,360)),8,30,lambda _:old.resize((640,360)),lambda _:mask,settings)
        expected=np.asarray(full.resize((640,360)),dtype=np.float32)
        error=np.mean(abs(expected-np.asarray(small,dtype=np.float32)))
        self.assertLess(error,3,'Shared normalized renderer should agree across resolutions')
    def test_rgb_does_not_wrap(self):
        a=np.zeros((8,100,3),dtype=np.uint8);a[:,0,0]=255
        out=np.array(compose(Image.fromarray(a),0,30,None,None,dict(count=0,rgb=.01)))
        self.assertEqual(out[4,-1,0],0)

@unittest.skipUnless(__import__('shutil').which('ffmpeg'),'FFmpeg is required')
class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='cutlab test paths ');cls.root=Path(cls.temp.name)
        cls.source=cls.root/'actual generated source.mp4'
        # Audio changes from 440 to 880 Hz exactly at source t=1s.
        ff('-f','lavfi','-i','testsrc2=size=160x120:rate=12:duration=3','-f','lavfi','-i',
           'aevalsrc=sin(2*PI*if(lt(t\\,1)\\,440\\,880)*t):s=48000:d=3','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',cls.source)
        cls.silent=cls.root/'silent footage.mp4';ff('-i',cls.source,'-an','-c:v','copy',cls.silent)
    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()
    def setUp(self):
        self.cache=self.root/('cache '+self._testMethodName);self.engine=Engine(self.cache)
        self.p=dict(version=1,source=str(self.source),trim=dict(start=.5,end=2.25),prompts=[],effects=dict(count=0),export=dict(crf=18))
    def test_import_export_audio_and_duration(self):
        meta=self.engine.import_media(self.source);self.assertTrue(Path(meta['proxy']).exists());self.assertTrue(meta['audio'])
        result=self.engine.render(self.p,self.root/'trim with audio.mp4');d=probe(result['path'])
        self.assertLessEqual(abs(float(d['format']['duration'])-1.75),1/12)
        self.assertTrue(any(s['codec_type']=='audio' for s in d['streams']))
        # Audio switch must be at output t=.5s (trim=.5s), not at t=1s.
        pcm=subprocess.check_output(['ffmpeg','-v','error','-i',result['path'],'-vn','-ac','1','-ar','48000','-f','f32le','pipe:1'])
        samples=np.frombuffer(pcm,dtype=np.float32)
        def peak(start):
            part=samples[int(start*48000):int((start+.15)*48000)]
            return np.fft.rfftfreq(len(part),1/48000)[np.argmax(abs(np.fft.rfft(part)))]
        self.assertAlmostEqual(peak(.1),440,delta=10);self.assertAlmostEqual(peak(.7),880,delta=10)
    def test_audio_stream_delay_preserved(self):
        source=self.root/'delayed audio source.mp4'
        ff('-f','lavfi','-i','testsrc2=size=160x120:rate=12:duration=3',
           '-itsoffset','1','-f','lavfi','-i','sine=frequency=880:duration=2',
           '-c:v','libx264','-c:a','aac','-t','3',source)
        self.p['source']=str(source);r=self.engine.render(self.p,self.root/'delayed audio output.mp4')
        pcm=subprocess.check_output(['ffmpeg','-v','error','-i',r['path'],'-vn','-ac','1','-ar','48000','-f','f32le','pipe:1'])
        samples=np.frombuffer(pcm,dtype=np.float32)
        early=np.sqrt(np.mean(samples[int(.1*48000):int(.3*48000)]**2))
        later=np.sqrt(np.mean(samples[int(.7*48000):int(.9*48000)]**2))
        self.assertLess(early,.005);self.assertGreater(later,.04)
    def test_silent(self):
        self.p['source']=str(self.silent);r=self.engine.render(self.p,self.root/'silent export.mp4')
        self.assertFalse(any(s['codec_type']=='audio' for s in probe(r['path'])['streams']))
    def test_mask_cache_reused_and_prompt_invalidates(self):
        seg=self.engine.prepare(self.p);key=self.engine.mask_key(seg,self.p)
        self.p['effects']={'count':5,'delay':3,'grain':.1};self.assertEqual(key,self.engine.mask_key(seg,self.p))
        self.p['prompts']=[dict(frame=0,x=.5,y=.5,label=1)];self.assertNotEqual(key,self.engine.mask_key(seg,self.p))
    def test_fixture_echo_preview_export_equivalence(self):
        self.p['effects']=dict(count=2,delay=3,dx=.15,feather=0,grain=.04)
        seg=self.engine.prepare(self.p);maskdir=Path(seg['folder'])/('masks-'+self.engine.mask_key(seg,self.p));maskdir.mkdir()
        for i in range(seg['count']):
            m=Image.new('L',(160,120));m.paste(255,(20+i,20,60+i,100));m.save(maskdir/f'{i:06d}.png')
        (maskdir/'complete.json').write_text('{}')
        a=self.engine.render(self.p,self.root/'fixture preview.mp4',True);b=self.engine.render(self.p,self.root/'fixture export.mp4')
        aa=subprocess.check_output(['ffmpeg','-v','error','-i',a['path'],'-f','rawvideo','-pix_fmt','rgb24','-an','pipe:1'])
        bb=subprocess.check_output(['ffmpeg','-v','error','-i',b['path'],'-f','rawvideo','-pix_fmt','rgb24','-an','pipe:1'])
        self.assertEqual(aa,bb)
        before=(maskdir/'complete.json').stat().st_mtime_ns
        self.p['effects']['delay']=8
        reused=self.engine.masks(self.p) # No model is installed; this must be a disk cache hit.
        self.assertEqual(reused['maskDir'],str(maskdir))
        self.assertEqual(before,(maskdir/'complete.json').stat().st_mtime_ns)
        self.assertEqual(self.engine.frame(self.p,9)['index'],9)
        self.assertEqual(Path(self.engine.frame(self.p,9)['mask']).name,'000009.png')
    def test_cancel_cleans_outputs(self):
        marker=self.cache/'cancel';self.cache.mkdir(exist_ok=True);engine=Engine(self.cache,cancel=marker)
        def progress(**kw):
            if kw.get('stage')=='Compositing export':marker.write_text('cancel')
        engine.emit=progress;out=self.root/'cancelled.mp4'
        with self.assertRaises(Cancelled):engine.render(self.p,out)
        self.assertFalse(out.exists());self.assertFalse(list(self.cache.glob('render-*')))
    def test_source_overwrite_denied(self):
        size=self.source.stat().st_size
        with self.assertRaisesRegex(ValueError,'source'):self.engine.render(self.p,self.source)
        self.assertEqual(size,self.source.stat().st_size)
    def test_save_load(self):
        file=self.root/'saved project.json';file.write_text(json.dumps(self.p));self.assertEqual(json.loads(file.read_text()),self.p)
    def test_non_square_pixels_preserve_display_aspect(self):
        source=self.root/'non square pixels.mp4'
        ff('-f','lavfi','-i','testsrc2=size=160x120:rate=12:duration=1','-vf','setsar=2','-c:v','libx264',source)
        self.p.update(source=str(source),trim=dict(start=0,end=.5))
        seg=self.engine.prepare(self.p)
        self.assertAlmostEqual(seg['width']/seg['height'],8/3,places=2)
        self.assertLessEqual(seg['width'],160);self.assertLessEqual(seg['height'],120)
    def test_ffmpeg_can_be_cancelled_while_running(self):
        import threading
        marker=self.cache/'cancel';self.cache.mkdir(exist_ok=True)
        engine=Engine(self.cache,cancel=marker)
        timer=threading.Timer(.15,lambda:marker.write_text('cancel'));timer.start()
        try:
            with self.assertRaises(Cancelled):
                engine.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=160x120:rate=12','-f','null','-'])
        finally:timer.cancel()
    def test_vfr_normalization(self):
        source=self.root/'vfr.mp4'
        ff('-f','lavfi','-i','testsrc2=size=160x120:rate=24:duration=2','-vf',"select='if(lt(t,1),not(mod(n,2)),1)'",'-fps_mode','vfr','-c:v','libx264',source)
        self.p.update(source=str(source),trim=dict(start=.2,end=1.7));s=self.engine.prepare(self.p)
        self.assertLessEqual(abs(s['duration']-1.5),1/s['fps'])
        self.assertEqual(len(list(Path(s['frames']).glob('*.png'))),s['count'])
        self.p['effects']={'count':0};r=self.engine.render(self.p,self.root/'vfr output.mp4')
        packet=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_frames','-show_entries','frame=best_effort_timestamp_time','-of','json',r['path']]))
        times=[float(f['best_effort_timestamp_time']) for f in packet['frames']]
        for a,b in zip(times,times[1:]):self.assertAlmostEqual(b-a,1/s['fps'],places=5)
