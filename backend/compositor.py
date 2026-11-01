"""Pure frame compositor. Coordinates/texture are normalized to output dimensions."""
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw

DEFAULTS = dict(count=1, dx=0.08, dy=0, delay=3, opacity=0.65, falloff=0.7,
                scale=1, tint='', order='subject', feather=1, expand=0,
                grain=0, scanlines=0, rgb=0, bleed=0, contrast=1,
                saturation=1, vignette=0, border=0)
PRESETS = {
    'CLEAN CUTOUT': {**DEFAULTS},
    'GHOST TRAIL': {**DEFAULTS, 'count':3, 'delay':4, 'opacity':0.6, 'falloff':0.65},
    'DIRTY TAPE': {**DEFAULTS, 'count':2, 'grain':0.035, 'scanlines':0.05,
                   'rgb':0.002, 'bleed':0.2, 'contrast':1.08, 'saturation':0.9, 'vignette':0.12, 'border':0.035}
}

def edge(mask, settings, size):
    mask = mask.resize(size, Image.Resampling.BILINEAR).convert('L')
    # Edge units are pixels at 1080 vertical, independent of proxy resolution.
    amount = round(float(settings['expand']) * size[1] / 1080)
    if amount:
        kernel = min(99, abs(amount)*2+1)
        mask = mask.filter((ImageFilter.MaxFilter if amount > 0 else ImageFilter.MinFilter)(kernel))
    return mask.filter(ImageFilter.GaussianBlur(float(settings['feather'])*size[1]/1080))

def compose(frame, index, fps, get_frame, get_mask, settings):
    s = {**DEFAULTS, **settings}
    w,h = frame.size
    out = frame.convert('RGB').copy()
    count = max(0,min(5,int(s['count'])))
    def paste_copy(k):
        src = index-k*max(0,int(s['delay']))
        if src < 0: return
        image = get_frame(src).convert('RGB')
        mask = edge(get_mask(src),s,(w,h))
        factor = max(0.2,min(2,float(s['scale'])))**k
        size = (max(1,round(w*factor)),max(1,round(h*factor)))
        image = image.resize(size,Image.Resampling.BICUBIC)
        mask = mask.resize(size,Image.Resampling.BILINEAR)
        if s['tint']:
            image = Image.blend(image,Image.new('RGB',size,s['tint']),0.4)
        alpha = max(0,min(1,float(s['opacity'])*float(s['falloff'])**(k-1)))
        mask = mask.point(lambda v: round(v*alpha))
        xy = (round(k*float(s['dx'])*w+(w-size[0])/2),round(k*float(s['dy'])*h+(h-size[1])/2))
        out.paste(image,xy,mask)
    for k in range(count,0,-1): paste_copy(k)
    if count and s['order']=='subject':
        out.paste(frame,(0,0),edge(get_mask(index),s,(w,h)))
    if s['contrast'] != 1: out = ImageEnhance.Contrast(out).enhance(float(s['contrast']))
    if s['saturation'] != 1: out = ImageEnhance.Color(out).enhance(float(s['saturation']))
    a = np.asarray(out).astype(np.float32)/255
    offset = round(float(s['rgb'])*w)
    if offset:
        # Edge replication; never wrap pixels to the other edge.
        xs = np.arange(w)
        a[:,:,0] = a[:,np.clip(xs-offset,0,w-1),0]
        a[:,:,2] = a[:,np.clip(xs+offset,0,w-1),2]
    if float(s['bleed']):
        blur = np.asarray(out.filter(ImageFilter.GaussianBlur(w/320))).astype(np.float32)/255
        luma = a.mean(2,keepdims=True)
        chroma = blur-blur.mean(2,keepdims=True)
        a = a*(1-float(s['bleed']))+(luma+chroma)*float(s['bleed'])
    if float(s['grain']):
        # A fixed normalized texture grid makes low/full resolution agree.
        rng = np.random.default_rng(round(index/fps*1_000_000))
        noise = rng.normal(0,1,(180,320)).astype(np.float32)
        noise = np.asarray(Image.fromarray(noise).resize((w,h),Image.Resampling.BILINEAR))
        a += noise[:,:,None]*float(s['grain'])
    yy,xx = np.mgrid[0:h,0:w]
    a *= (1-float(s['scanlines'])*(np.floor(yy/h*540).astype(int)%2))[:,:,None]
    radius = ((xx/max(1,w-1)-0.5)**2+(yy/max(1,h-1)-0.5)**2)*2
    a *= (1-float(s['vignette'])*np.clip(radius,0,1))[:,:,None]
    out = Image.fromarray(np.uint8(np.clip(a,0,1)*255))
    if float(s['border']):
        matte = Image.new('L',(w,h)); d = ImageDraw.Draw(matte)
        inset = max(1,round(min(w,h)*float(s['border'])*0.25))
        d.rounded_rectangle((inset,inset,w-1-inset,h-1-inset),radius=min(w,h)*float(s['border']),fill=255)
        black = Image.new('RGB',(w,h)); black.paste(out,(0,0),matte); out=black
    return out
