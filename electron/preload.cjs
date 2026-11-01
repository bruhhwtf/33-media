const {contextBridge,ipcRenderer,webUtils}=require('electron');
contextBridge.exposeInMainWorld('cutlab',{
 storageInfo:()=>ipcRenderer.invoke('cutlab:storage-info'),
 chooseStorage:()=>ipcRenderer.invoke('cutlab:choose-storage'),
 importVideo:()=>ipcRenderer.invoke('cutlab:import'),
 importDrop:file=>ipcRenderer.invoke('cutlab:drop',webUtils.getPathForFile(file)),
 setupAI:()=>ipcRenderer.invoke('cutlab:setup-ai'),
 diagnostics:()=>ipcRenderer.invoke('cutlab:diagnostics'), download:()=>ipcRenderer.invoke('cutlab:download'),
 frame:(p,i)=>ipcRenderer.invoke('cutlab:frame',p,i),mask:p=>ipcRenderer.invoke('cutlab:mask',p),
 preview:p=>ipcRenderer.invoke('cutlab:preview',p),exportVideo:p=>ipcRenderer.invoke('cutlab:export',p),
 cancel:()=>ipcRenderer.invoke('cutlab:cancel'),save:p=>ipcRenderer.invoke('cutlab:save',p),
 load:()=>ipcRenderer.invoke('cutlab:load'),relink:()=>ipcRenderer.invoke('cutlab:relink'),
 onProgress:fn=>{const cb=(_,data)=>fn(data);ipcRenderer.on('cutlab:progress',cb);return()=>ipcRenderer.removeListener('cutlab:progress',cb);}
});
