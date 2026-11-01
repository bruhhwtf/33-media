const {app,BrowserWindow,ipcMain,dialog,protocol,net}=require('electron');
const {spawn}=require('node:child_process');
const fs=require('node:fs'); const path=require('node:path'); const {pathToFileURL}=require('node:url'); const {randomUUID}=require('node:crypto'); const readline=require('node:readline'); const {validate}=require('./project.cjs');
protocol.registerSchemesAsPrivileged([{scheme:'cutlab',privileges:{standard:true,secure:true,supportFetchAPI:true,stream:true}}]);
let runtime=process.env.CUTLAB_RUNTIME||null;
let storageFolder=null;
const storage=require('./storage.cjs');
let win,active=null; const sources=new Set(),assets=new Map();
const root=()=>path.join(storageFolder||app.getPath('userData'),'cache');
const backend=()=>app.isPackaged?path.join(process.resourcesPath,'backend'):path.join(__dirname,'..','backend');
const python=()=>process.env.CUTLAB_PYTHON || (runtime?path.join(runtime,'python','python.exe'):null) || (fs.existsSync(path.join(__dirname,'..','.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python'))?path.join(__dirname,'..','.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python'):(process.platform==='win32'?'python':'python3'));
function asset(file){if(!file)return null; const id=randomUUID();assets.set(id,path.resolve(file));return `cutlab://media/${id}`;}
function expose(value){ if(!value || typeof value!=='object')return value; const copy={...value}; for(const key of ['proxy','image','mask','path'])if(copy[key])copy[key+'Url']=asset(copy[key]);return copy; }
function project(p){
 validate(p);
 if(!p || p.version!==1 || typeof p.source!=='string' || !sources.has(path.resolve(p.source)))throw Error('Import or relink the project source first.');
 if(!p.trim || !Number.isFinite(p.trim.start)||!Number.isFinite(p.trim.end))throw Error('Invalid trim range.');
 if(!Array.isArray(p.prompts)||p.prompts.length>2000)throw Error('Invalid mask prompts.');
 return p;
}
function worker(payload){
 if(active)throw Error('Another operation is running. Cancel it or wait.');
 fs.mkdirSync(root(),{recursive:true});
 const storageEnv=storage.workerEnvironment(storageFolder||app.getPath('userData'));fs.mkdirSync(storageEnv.TEMP,{recursive:true});
 const cancel=path.join(root(),`cancel-${randomUUID()}`);
 return new Promise((resolve,reject)=>{
  const proc=spawn(python(),['-u',path.join(backend(),'worker.py')],{cwd:backend(),shell:false,windowsHide:true,env:{...process.env,...storageEnv,PYTHONIOENCODING:'utf-8',...(runtime?{PATH:path.join(runtime,'bin')+path.delimiter+process.env.PATH,CUTLAB_RUNTIME:runtime}:{})}});
  active={proc,cancel}; let result,error,stderr='';
  const lines=readline.createInterface({input:proc.stdout});
  lines.on('line',line=>{try{const e=JSON.parse(line); if(e.result!==undefined)result=e.result; else if(e.error)error=e.error;else win?.webContents.send('cutlab:progress',e);}catch{stderr+=line+'\n';}});
  proc.stderr.on('data',b=>{stderr=(stderr+b.toString()).slice(-6000);});
  const clear=()=>{active=null;fs.rmSync(cancel,{force:true});};
  proc.on('error',e=>{clear();reject(Error(`Cannot start Python (${python()}). Install Python 3.11 and run setup. ${e.message}`));});
  proc.on('close',code=>{clear();if(code || error || result===undefined)reject(Error(error||stderr||`Worker exited ${code}`));else resolve(expose(result));});
  proc.stdin.on('error',()=>{});proc.stdin.end(JSON.stringify({...payload,cache:root(),cancel})+'\n');
 });
}
async function importFile(file){if(!file)return null;if(path.extname(file).toLowerCase()!=='.mp4')throw Error('Choose an MP4 video.');const result=await worker({op:'import',path:file});sources.add(path.resolve(result.source));return result;}
function guard(event){if(event.sender!==win.webContents || event.senderFrame!==win.webContents.mainFrame)throw Error('Untrusted IPC sender.');}
function handle(name,fn){ipcMain.handle('cutlab:'+name,async(event,...args)=>{guard(event);return fn(...args);});}
app.whenReady().then(async()=>{
 try{storageFolder=JSON.parse(fs.readFileSync(path.join(app.getPath('userData'),'storage.json'),'utf8')).folder||null;}catch(e){if(e.code!=='ENOENT')dialog.showErrorBox('Storage settings', 'Could not read saved storage settings. Choose a storage folder in Model setup.');}
 if(app.isPackaged&&process.platform==='win32'&&!runtime){try{runtime=await require('./runtime.cjs').prepareRuntime(path.join(process.resourcesPath,'runtime'),storageFolder||app.getPath('userData'));}catch(e){dialog.showErrorBox('CUTLAB setup',e.message+' Open Model setup to choose an available drive.');runtime=path.join(process.resourcesPath,'runtime');}}
 protocol.handle('cutlab',request=>{const u=new URL(request.url); const file=u.hostname==='media'?assets.get(u.pathname.slice(1)):null; if(!file)return new Response('Not found',{status:404}); return net.fetch(pathToFileURL(file).toString(),{headers:request.headers});});
 win=new BrowserWindow({width:1440,height:940,minWidth:1060,minHeight:740,backgroundColor:'#202426',title:'BANDKLAN CUTLAB',webPreferences:{preload:path.join(__dirname,'preload.cjs'),contextIsolation:true,nodeIntegration:false,sandbox:true}});
 win.setMenuBarVisibility(false);win.webContents.setWindowOpenHandler(()=>({action:'deny'}));win.webContents.on('will-navigate',(e)=>e.preventDefault());
 handle('import',async()=>{const d=await dialog.showOpenDialog(win,{filters:[{name:'MP4 video',extensions:['mp4']}],properties:['openFile']});return d.canceled?null:importFile(d.filePaths[0]);});
 handle('drop',file=>importFile(file));
 handle('storage-info',()=>storage.inspect(storageFolder||app.getPath('userData')));
 handle('choose-storage',async()=>{
  if(active)throw Error('Wait for the current operation or cancel it first.');
  const picked=await dialog.showOpenDialog(win,{title:'Choose a drive for AI and video cache',properties:['openDirectory','createDirectory']});
  if(picked.canceled)return null;
  const folder=path.join(picked.filePaths[0],'BANDKLAN-CUTLAB');
  const info=await storage.inspect(folder);if(info.freeGB<10)throw Error(`This drive has ${info.freeGB.toFixed(1)} GB free. Choose a drive with at least 10 GB available.`);
  const newRuntime=app.isPackaged&&process.platform==='win32'?await require('./runtime.cjs').prepareRuntime(path.join(process.resourcesPath,'runtime'),folder):runtime;
  await storage.save(app.getPath('userData'),folder);storageFolder=folder;runtime=newRuntime;return info;
 });
 handle('setup-ai',()=>worker({op:'setup-ai'}));
 handle('diagnostics',()=>worker({op:'diagnostics'}));handle('download',()=>worker({op:'download'}));
 handle('frame',(p,index)=>worker({op:'frame',project:project(p),index}));
 handle('mask',p=>worker({op:'mask',project:project(p)}));handle('preview',p=>worker({op:'preview',project:project(p)}));
 handle('export',async p=>{project(p);const d=await dialog.showSaveDialog(win,{defaultPath:'BANDKLAN-cut.mp4',filters:[{name:'H.264 MP4',extensions:['mp4']}]});if(d.canceled)return null;return worker({op:'export',project:p,path:d.filePath});});
 handle('cancel',()=>{if(active)fs.writeFileSync(active.cancel,'cancel');return true;});
 handle('save',async p=>{project(p);const d=await dialog.showSaveDialog(win,{defaultPath:'untitled.cutlab.json',filters:[{name:'CUTLAB project',extensions:['json']}]});if(d.canceled)return null;fs.writeFileSync(d.filePath,JSON.stringify(p,null,2));return d.filePath;});
 handle('load',async()=>{const d=await dialog.showOpenDialog(win,{filters:[{name:'CUTLAB project',extensions:['json']}],properties:['openFile']});if(d.canceled)return null; if(fs.statSync(d.filePaths[0]).size>2e6)throw Error('Project JSON is too large.');const p=validate(JSON.parse(fs.readFileSync(d.filePaths[0],'utf8')));if(p.version!==1 || typeof p.source!=='string')throw Error('Unsupported project version.'); if(fs.existsSync(p.source))sources.add(path.resolve(p.source));const missing=!fs.existsSync(p.source);const media=missing?null:await importFile(p.source);return {project:p,missing,media};});
 handle('relink',async()=>{const d=await dialog.showOpenDialog(win,{title:'Relink original source MP4',filters:[{name:'MP4 video',extensions:['mp4']}],properties:['openFile']});return d.canceled?null:importFile(d.filePaths[0]);});
 if(process.env.CUTLAB_DEV_URL==='http://127.0.0.1:5173')win.loadURL(process.env.CUTLAB_DEV_URL);else win.loadFile(path.join(__dirname,'..','dist','index.html'));
});
app.on('window-all-closed',()=>{if(active)fs.writeFileSync(active.cancel,'cancel');app.quit();});
