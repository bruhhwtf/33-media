// Schema checks at the desktop boundary; JSON never becomes commands or module names.
const limits={count:[0,5],dx:[-.5,.5],dy:[-.5,.5],delay:[0,30],opacity:[0,1],falloff:[0,1],scale:[.7,1.3],feather:[0,12],expand:[-20,20],grain:[0,.15],scanlines:[0,.25],rgb:[0,.015],bleed:[0,.6],contrast:[.5,1.5],saturation:[0,1.5],vignette:[0,.6],border:[0,.2]};
function validate(p){
 if(!p||p.version!==1||typeof p.source!=='string'||!p.source)throw Error('Unsupported or invalid CUTLAB project.');
 if(!p.trim||!Number.isFinite(p.trim.start)||!Number.isFinite(p.trim.end)||p.trim.start<0||p.trim.end<=p.trim.start||p.trim.end-p.trim.start>10.001)throw Error('Select a valid segment of at most 10 seconds.');
 if(!p.effects)throw Error('Project effect settings are missing.');
 for(const [key,[min,max]] of Object.entries(limits)){const x=p.effects[key];if(!Number.isFinite(x)||x<min||x>max)throw Error(`Invalid effect setting: ${key}`);}
 for(const key of ['count','delay','expand','feather'])if(!Number.isInteger(p.effects[key]))throw Error(`Expected whole number: ${key}`);
 if(!['subject','trails'].includes(p.effects.order)||!(p.effects.tint===''||/^#[\da-f]{6}$/i.test(p.effects.tint)))throw Error('Invalid tint or layer order.');
 if(!Array.isArray(p.prompts)||p.prompts.length>2000||p.prompts.some(x=>!Number.isInteger(x.frame)||x.frame<0||![0,1].includes(x.label)||!Number.isFinite(x.x)||x.x<0||x.x>1||!Number.isFinite(x.y)||x.y<0||x.y>1))throw Error('Invalid mask prompts.');
 if(!p.export||![18,23].includes(p.export.crf))throw Error('Unsupported export quality.');
 return p;
}
module.exports={validate};
