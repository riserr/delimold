const S=require('./store'), A=require('./auth');
const schema={
 development:{projects:['code','title','owner','status','notes'],documents:['projectId','code','title','version','moldId','notes'],attachments:['documentId','name','storedName','size']},
 private:{suppliers:['code','name','contact','email','phone','notes'],orders:['number','supplierId','date','currency','status','notes'],items:['orderId','line','moldId','description','transaction','quantity','unitPrice','discount','tax'],attachments:['orderId','name','storedName','size']}
};
function filename(scope){return S.path.join(S.root,'data',scope,scope+'.json');}
function initial(scope){const c={};Object.keys(schema[scope]).forEach(k=>c[k]={});return {schemaVersion:1,revision:0,updatedAt:null,collections:c,events:[]};}
function read(scope){return S.fs.existsSync(filename(scope))?S.read(filename(scope)):initial(scope);}
function access(s,scope){if(!schema[scope])S.fail(404,'NOT_FOUND','Modul tidak ditemukan');A.requireRole(s,scope==='private');}
function money(v){if(typeof v!=='string'||!/^\d{1,12}(\.\d{1,4})?$/.test(v))S.fail(400,'VALIDATION','Harga/diskon/pajak gunakan desimal positif, maksimal 4 angka desimal');return v;}
function validate(scope,c,catalog){const unique=(bucket,field)=>{const seen={};Object.keys(c[bucket]).forEach(k=>{const key=c[bucket][k][field].toLowerCase();if(seen[key])S.fail(409,'DUPLICATE','Kode/nomor sudah dipakai');seen[key]=true;});};
 const ref=(bucket,k)=>{if(!c[bucket][k])S.fail(400,'REFERENCE','Record yang dirujuk tidak ditemukan');};
 if(scope==='development'){
 unique('projects','code');Object.keys(c.documents).forEach(k=>{const d=c.documents[k];ref('projects',d.projectId);if(!/^\d+$/.test(d.version)||Number(d.version)<1)S.fail(400,'VALIDATION','Versi dokumen harus angka positif');if(d.moldId&&!catalog.collections.molds[d.moldId])S.fail(400,'REFERENCE','ID cetakan tidak ditemukan');});
 const seen={};Object.keys(c.documents).forEach(k=>{const d=c.documents[k],key=d.projectId+'|'+d.code.toLowerCase()+'|'+d.version;if(seen[key])S.fail(409,'DUPLICATE','Versi dokumen sudah ada');seen[key]=true;});
 Object.keys(c.attachments).forEach(k=>ref('documents',c.attachments[k].documentId));
 }else{
 unique('suppliers','code');unique('orders','number');Object.keys(c.orders).forEach(k=>{const o=c.orders[k];ref('suppliers',o.supplierId);if(!/^[A-Z]{3}$/.test(o.currency)||!/^\d{4}-\d{2}-\d{2}$/.test(o.date))S.fail(400,'VALIDATION','Mata uang harus 3 huruf besar, tanggal YYYY-MM-DD');});
 const seen={};Object.keys(c.items).forEach(k=>{const d=c.items[k];ref('orders',d.orderId);if(d.moldId&&!catalog.collections.molds[d.moldId])S.fail(400,'REFERENCE','ID cetakan tidak ditemukan');if(!/^\d+$/.test(d.quantity)||Number(d.quantity)<1||!/^\d+$/.test(d.line)||Number(d.line)<1)S.fail(400,'VALIDATION','Jumlah dan nomor baris harus positif');if(['PURCHASE','REPAIR','MODIFICATION'].indexOf(d.transaction)<0)S.fail(400,'VALIDATION','Jenis transaksi tidak valid');['unitPrice','discount','tax'].forEach(f=>money(d[f]));const key=d.orderId+'|'+d.line;if(seen[key])S.fail(409,'DUPLICATE','Nomor baris PO sudah ada');seen[key]=true;});
 Object.keys(c.attachments).forEach(k=>ref('orders',c.attachments[k].orderId));
 }
}
function save(scope,s,input,catalog){access(s,scope);const bucket=input.bucket;if(!schema[scope][bucket]||bucket==='attachments')S.fail(400,'VALIDATION','Jenis data tidak valid');
 return S.transact(filename(scope),initial(scope),data=>{
 if(input.revision!==data.revision)S.fail(409,'CONFLICT','Data berubah; muat ulang');const key=input.id?S.safeId(input.id):S.id(),old=data.collections[bucket][key];if(input.id&&!old)S.fail(404,'NOT_FOUND','Record tidak ada');
 if(input.action==='delete'){delete data.collections[bucket][key];}else{if(!input.data||typeof input.data!=='object')S.fail(400,'VALIDATION','Data wajib diisi');const row={};schema[scope][bucket].forEach(f=>row[f]=S.text(input.data[f]===undefined?'':input.data[f],f==='notes'?4000:500,['notes','owner','status','contact','email','phone','moldId'].indexOf(f)<0));data.collections[bucket][key]=row;}
 validate(scope,data.collections,catalog);data.revision++;data.updatedAt=S.now();data.events.unshift({at:data.updatedAt,actor:s.id,action:input.action==='delete'?'delete':old?'update':'create',bucket:bucket,id:key,before:old||null,after:data.collections[bucket][key]||null});return {ok:true,id:key,revision:data.revision};
 });}
function attach(scope,s,input,catalog){access(s,scope);const name=S.text(input.name,180,true);if(/[\\/\x00-\x1f]/.test(name)||! /\.(pdf|png|jpg|jpeg|xlsx|xls|csv|txt|docx|dxf|zip)$/i.test(name))S.fail(400,'VALIDATION','Jenis/nama lampiran tidak diizinkan');
 if(typeof input.base64!=='string'||input.base64.length>11000000||!/^([A-Za-z0-9+/]{4})*([A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(input.base64))S.fail(400,'VALIDATION','File base64 tidak valid atau terlalu besar');const bytes=Buffer.from(input.base64,'base64');if(!bytes.length||bytes.length>8000000)S.fail(400,'VALIDATION','File maksimal 8 MB');
 const key=S.id(),dir=S.path.join(S.root,'files',scope),storedName=key+S.path.extname(name).toLowerCase();S.fs.mkdirSync(dir,{recursive:true});const dest=S.path.join(dir,storedName);S.fs.writeFileSync(dest,bytes,{flag:'wx'});
 try{return S.transact(filename(scope),initial(scope),data=>{if(data.revision!==input.revision)S.fail(409,'CONFLICT','Data berubah; muat ulang');const row={name:name,storedName:storedName,size:bytes.length};row[scope==='private'?'orderId':'documentId']=S.safeId(input.parentId);data.collections.attachments[key]=row;validate(scope,data.collections,catalog);data.revision++;data.updatedAt=S.now();data.events.unshift({at:data.updatedAt,actor:s.id,action:'attach',id:key});return {ok:true,id:key};});}catch(e){S.fs.unlinkSync(dest);throw e;}}
function download(scope,s,id){access(s,scope);const row=read(scope).collections.attachments[S.safeId(id)];if(!row)S.fail(404,'NOT_FOUND','File tidak ditemukan');if(!/^[a-f0-9]{32}\.[a-z0-9]+$/.test(row.storedName))S.fail(400,'PATH','Path tidak valid');return {bytes:S.fs.readFileSync(S.path.join(S.root,'files',scope,row.storedName)),name:row.name};}
module.exports={schema,read,access,save,attach,download};
