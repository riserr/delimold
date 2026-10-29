const S=require('./store');
const fields={
 patterns:['code','name','land','hasArt','status','lastStatusReason'],
 containers:['code','serial','od','sw','spacers','status','lastStatusReason'],
 stickers:['code','name','img','status','lastStatusReason'],
 molds:['spec','category','size','patternId','serial','cure','mtype','owner','bladder','status','note','role','mainId','containerId','spacer','brands','lastStatusReason'],
 pattern_art:['svg','preview']
};
function project(data){const out={schemaVersion:2,revision:data.revision,updatedAt:data.updatedAt,collections:{},events:[],deleted:[]};
 Object.keys(fields).forEach(bucket=>{const c=out.collections[bucket]={};Object.keys(data.collections[bucket]).forEach(id=>{S.safeId(id);const row=c[id]={};fields[bucket].forEach(f=>{if(data.collections[bucket][id][f]!==undefined)row[f]=data.collections[bucket][id][f];});
 if(bucket==='molds')row.brands=(row.brands||[]).map(b=>({brand:b.brand,insert:b.insert,stickerId:b.stickerId}));if(bucket==='containers')row.spacers=(row.spacers||[]).map(p=>({size:p.size,od:p.od}));});});return out;}
let timer=null,lastError=null;
function sync(){if(S.config.mode!=='master'||!S.config.publishTarget)return {enabled:false};const target=S.path.resolve(S.config.publishTarget),source=S.catalogPath();if(!S.fs.existsSync(source))return {enabled:true,pending:true,error:'Database utama belum dimigrasikan'};
 try{if(!S.fs.existsSync(target))throw Error('Folder tujuan SALAK tidak ditemukan/tidak dapat dijangkau');
 const raw=S.fs.readFileSync(source,'utf8'),data=JSON.parse(raw.slice('window.DELIMOLD_DATA='.length,-1)),pointerFile=S.path.join(target,'current.json'),old=S.fs.existsSync(pointerFile)?S.read(pointerFile):null;
 if(old&&old.sourceRevision>data.revision)throw Error('SALAK memiliki revisi lebih baru; periksa sumber sebelum pemulihan');
 if(old&&old.sourceRevision===data.revision){lastError=null;return {enabled:true,pending:false,publishedAt:old.publishedAt,revision:old.sourceRevision};}
 const snapshot=project(data),packageId='r'+data.revision+'-'+S.id(),dir=S.path.join(target,'packages',packageId);S.fs.mkdirSync(dir,{recursive:true});
 const publishedAt=S.now();snapshot.publishedAt=publishedAt;
 S.atomic(S.path.join(dir,'catalog.js'),'window.DELIMOLD_DATA='+JSON.stringify(snapshot).replace(/\u2028/g,'\\u2028').replace(/\u2029/g,'\\u2029')+';');
 const manifest={packageId:packageId,sourceRevision:data.revision,sourceUpdatedAt:data.updatedAt,publishedAt:publishedAt,schemaVersion:2};
 S.atomic(S.path.join(dir,'manifest.json'),manifest);S.atomic(pointerFile,manifest);lastError=null;return {enabled:true,pending:false,publishedAt:publishedAt,revision:data.revision};
 }catch(e){lastError=e.message;return {enabled:true,pending:true,error:lastError};}}
function schedule(){if(S.config.mode!=='master')return;setImmediate(sync);if(!timer){timer=setInterval(sync,15000);timer.unref();}}
function status(){if(S.config.mode==='viewer'){try{return S.read(S.path.join(S.currentPackage(),'manifest.json'));}catch(e){return {error:'Belum ada paket diterima'};}}return {enabled:!!S.config.publishTarget,lastError:lastError};}
module.exports={project,sync,schedule,status};
