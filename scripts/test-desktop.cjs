// Actual Electron + Python/FFmpeg smoke test. Generated video, no AI mask fixture.
const { _electron: electron }=require('playwright-core');
const {execFileSync}=require('node:child_process');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'cutlab desktop '));const source=path.join(dir,'source with spaces.mp4'),output=path.join(dir,'export with spaces.mp4'),project=path.join(dir,'project.json');
 execFileSync('ffmpeg',['-v','error','-y','-f','lavfi','-i','testsrc2=size=320x240:rate=12:duration=2','-f','lavfi','-i','sine=frequency=440:duration=2','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',source]);
 const app=await electron.launch({args:[...(process.platform==='linux'?['--no-sandbox']:[]),path.resolve(__dirname,'..')],env:{...process.env,CUTLAB_PYTHON:process.env.CUTLAB_PYTHON||(process.platform==='win32'?'python':'python3')},timeout:30000});
 try{
  const page=await app.firstWindow();await page.waitForLoadState('domcontentloaded');const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.waitForFunction(()=>document.querySelector('footer .status-text')?.textContent==='Complete.',null,{timeout:30000});
  const wizard=page.locator('.model-dialog .panel-title button');if(await wizard.isVisible())await wizard.click();
  await app.evaluate(({dialog},source)=>{dialog.showOpenDialog=async()=>({canceled:false,filePaths:[source]});},source);
  await page.getByRole('button',{name:'Import MP4',exact:true}).click();await page.locator('.media-item b').filter({hasText:'source with spaces.mp4'}).waitFor({timeout:30000});
  await page.waitForFunction(()=>document.querySelector('video')?.readyState>=2,{timeout:15000});
  await page.getByRole('spinbutton',{name:'Trim start'}).fill('0.25');await page.getByRole('spinbutton',{name:'Trim end'}).fill('1.75');
  await page.getByRole('button',{name:'Echoes',exact:true}).click();await page.locator('label').filter({hasText:'Duplicates'}).locator('input').fill('0');
  await page.getByRole('button',{name:'3 · Render Preview',exact:true}).click();await page.waitForFunction(()=>document.querySelector('.screen-label')?.textContent==='RENDERED COMPOSITION',null,{timeout:30000});
  await page.waitForFunction(()=>document.querySelector('video')?.readyState>=2,null,{timeout:15000});
  await app.evaluate(({dialog},output)=>{dialog.showSaveDialog=async()=>({canceled:false,filePath:output});},output);
  await page.getByRole('button',{name:'Export MP4 ↗',exact:true}).click();await page.waitForFunction(()=>document.querySelector('footer .status-text')?.textContent==='Complete.',null,{timeout:30000});
  // The status may already have been complete; wait for the export file and button readiness as well.
  await page.getByRole('button',{name:'Export MP4 ↗',exact:true}).waitFor();await page.waitForFunction(()=>!document.querySelector('.export')?.hasAttribute('disabled'),null,{timeout:30000});
  assert(fs.existsSync(output),'export file');
  const d=JSON.parse(execFileSync('ffprobe',['-v','error','-show_format','-show_streams','-of','json',output]));assert(Math.abs(+d.format.duration-1.5)<=1/12);assert(d.streams.some(s=>s.codec_type==='audio'));
  await app.evaluate(({dialog},project)=>{dialog.showSaveDialog=async()=>({canceled:false,filePath:project});},project);
  await page.getByRole('button',{name:'Save project',exact:true}).click();await page.waitForFunction(()=>!document.querySelector('.menubar button:nth-of-type(3)')?.hasAttribute('disabled'));
  assert.equal(JSON.parse(fs.readFileSync(project)).effects.count,0);
  await app.evaluate(({dialog},project)=>{dialog.showOpenDialog=async()=>({canceled:false,filePaths:[project]});},project);
  await page.getByRole('button',{name:'Open project',exact:true}).click();await page.getByRole('button',{name:'Save project',exact:true}).waitFor();await page.waitForFunction(()=>!document.querySelector('.menubar button:nth-of-type(3)')?.hasAttribute('disabled'),null,{timeout:30000});
  assert.equal(await page.getByRole('spinbutton',{name:'Trim start'}).inputValue(),'0.25');
  await page.getByRole('button',{name:'1 · Select subject',exact:true}).click();await page.locator('canvas').waitFor({timeout:30000});await page.locator('canvas').click({position:{x:120,y:100}});await page.getByRole('button',{name:'2 · Mask Subject',exact:true}).click();await page.getByRole('alert').filter({hasText:'SAM 2 is not installed'}).waitFor({timeout:30000});
  await page.getByRole('button',{name:'Dismiss ×',exact:true}).click();
  // Load a missing media reference and exercise the visible relink workflow.
  const missing=JSON.parse(fs.readFileSync(project));missing.source=path.join(dir,'moved-away.mp4');fs.writeFileSync(project,JSON.stringify(missing));
  await page.getByRole('button',{name:'Open project',exact:true}).click();await page.getByRole('button',{name:'Source missing — Relink',exact:true}).waitFor();
  await app.evaluate(({dialog},source)=>{dialog.showOpenDialog=async()=>({canceled:false,filePaths:[source]});},source);
  await page.getByRole('button',{name:'Source missing — Relink',exact:true}).click();await page.waitForFunction(()=>!!document.querySelector('video'),null,{timeout:30000});
  assert.equal(await page.getByRole('spinbutton',{name:'Trim start'}).inputValue(),'0.25');
  await page.screenshot({path:process.env.CUTLAB_SCREENSHOT||path.join(dir,'desktop.png')});
  assert.deepEqual(errors,[]);console.log('PASS actual Electron import/playback, trim, shared preview/export, audio, source paths with spaces, save/load, frame click and actionable missing-model error.');console.log('Generated test artifacts:',dir);
 }finally{await app.close();}
})().catch(e=>{console.error(e);process.exit(1)});
