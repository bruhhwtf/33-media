const fs=require('node:fs/promises');const path=require('node:path');
async function prepareRuntime(source,userData){
 const destination=path.join(userData,'runtime-v1');
 try{await fs.access(path.join(destination,'ready.json'));return destination;}catch{}
 const staging=destination+'.partial';await fs.rm(staging,{recursive:true,force:true});
 try{
  await fs.cp(source,staging,{recursive:true});
  await fs.access(path.join(staging,'python','python.exe'));await fs.access(path.join(staging,'bin','ffprobe.exe'));
  await fs.writeFile(path.join(staging,'ready.json'),JSON.stringify({version:1}));
  await fs.rm(destination,{recursive:true,force:true});await fs.rename(staging,destination);return destination;
 }catch(e){await fs.rm(staging,{recursive:true,force:true});throw Error('Bundled runtime could not be prepared. Reinstall CUTLAB or check free disk space. '+e.message);}
}
module.exports={prepareRuntime};
