const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs/promises');const os=require('node:os');const path=require('node:path');const {prepareRuntime}=require('../electron/runtime.cjs');
test('runtime copies to writable storage and retains AI on repeated launch',async()=>{
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'cutlab-runtime-'));
 try{const source=path.join(dir,'installer runtime');await fs.mkdir(path.join(source,'python'),{recursive:true});await fs.mkdir(path.join(source,'bin'));await fs.writeFile(path.join(source,'python/python.exe'),'fixture');await fs.writeFile(path.join(source,'bin/ffprobe.exe'),'fixture');
 const dest=await prepareRuntime(source,path.join(dir,'user data'));await fs.writeFile(path.join(dest,'ai-installed'),'retained');assert.equal(await prepareRuntime(source,path.join(dir,'user data')),dest);assert.equal(await fs.readFile(path.join(dest,'ai-installed'),'utf8'),'retained');
 }finally{await fs.rm(dir,{recursive:true,force:true});}
});
test('incomplete runtime cannot be marked ready',async()=>{
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'cutlab-runtime-'));try{await assert.rejects(prepareRuntime(path.join(dir,'absent'),dir),/Reinstall/);await assert.rejects(fs.access(path.join(dir,'runtime-v1.partial')));}finally{await fs.rm(dir,{recursive:true,force:true});}
});
