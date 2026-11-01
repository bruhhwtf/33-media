const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs/promises');const path=require('node:path');const os=require('node:os');const storage=require('../electron/storage.cjs');
test('alternate storage persists and redirects package cache and temporary downloads',async()=>{
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'cutlab storage '));try{
 const user=path.join(dir,'profile');const folder=path.join(dir,'other drive','BANDKLAN-CUTLAB');const info=await storage.inspect(folder);assert(info.freeGB>0);
 await storage.save(user,folder);assert.equal(JSON.parse(await fs.readFile(path.join(user,'storage.json'))).folder,folder);
 for(const location of Object.values(storage.workerEnvironment(folder)))assert(location.startsWith(folder+path.sep));
 assert.equal((await fs.readdir(folder)).length,0,'write probe cleaned');
 }finally{await fs.rm(dir,{recursive:true,force:true});}
});
