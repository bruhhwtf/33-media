const fs=require('node:fs/promises');const path=require('node:path');
async function inspect(folder){
 await fs.mkdir(folder,{recursive:true});const probe=path.join(folder,'.write-check-'+process.pid);
 await fs.writeFile(probe,'');await fs.unlink(probe);
 const s=await fs.statfs(folder);return {folder,freeGB:Number(s.bavail)*Number(s.bsize)/1024**3};
}
async function save(userData,folder){
 await fs.mkdir(userData,{recursive:true});const file=path.join(userData,'storage.json');
 await fs.writeFile(file+'.partial',JSON.stringify({version:1,folder}));await fs.rename(file+'.partial',file);
}
function workerEnvironment(folder){const tmp=path.join(folder,'temp');return {TEMP:tmp,TMP:tmp,TMPDIR:tmp,PIP_CACHE_DIR:path.join(folder,'pip-cache')};}
module.exports={inspect,save,workerEnvironment};
