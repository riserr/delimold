// Local JSON storage. Never expose this module's directories as a static web root.
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const root = path.resolve(process.env.DELIMOLD_ROOT || process.argv[2] || process.cwd());
const defaults = {mode:'master',listen:'127.0.0.1',port:8765,hosts:['127.0.0.1:8765','localhost:8765'],publishTarget:'',sessionHours:8};
const configFile = path.join(root,'config','server.json');
const config = Object.assign({},defaults,fs.existsSync(configFile)?JSON.parse(fs.readFileSync(configFile,'utf8')):{});
if(['master','viewer'].indexOf(config.mode)<0)throw Error('mode harus master atau viewer');
function fail(status,code,message){const e=new Error(message);e.status=status;e.code=code;throw e;}
function read(file){return JSON.parse(fs.readFileSync(file,'utf8'));}
function atomic(file,value){fs.mkdirSync(path.dirname(file),{recursive:true});const tmp=file+'.'+crypto.randomBytes(8).toString('hex')+'.tmp';let fd;
 try{fd=fs.openSync(tmp,'wx');const bytes=Buffer.from(Buffer.isBuffer(value)?value:typeof value==='string'?value:JSON.stringify(value));let pos=0;while(pos<bytes.length)pos+=fs.writeSync(fd,bytes,pos,bytes.length-pos,pos);fs.fsyncSync(fd);fs.closeSync(fd);fd=undefined;fs.renameSync(tmp,file);}finally{if(fd!==undefined)fs.closeSync(fd);if(fs.existsSync(tmp))fs.unlinkSync(tmp);}}
function transact(file,initial,fn){fs.mkdirSync(path.dirname(file),{recursive:true});let lock;
 try{lock=fs.openSync(file+'.lock','wx');}catch(e){fail(409,'BUSY','Penyimpanan sedang dipakai. Coba lagi.');}
 try{const old=fs.existsSync(file)?read(file):initial;const next=JSON.parse(JSON.stringify(old));const result=fn(next);if(fs.existsSync(file))fs.copyFileSync(file,file+'.bak');atomic(file,next);return result;}finally{fs.closeSync(lock);fs.unlinkSync(file+'.lock');}}
function id(){return crypto.randomBytes(16).toString('hex');}
function now(){return new Date().toISOString();}
function safeId(v){if(typeof v!=='string'||!/^[-A-Za-z0-9_]{1,120}$/.test(v)||['__proto__','prototype','constructor'].indexOf(v)>=0)fail(400,'VALIDATION','ID tidak valid');return v;}
function text(v,max,required){if(typeof v!=='string'||v.length>max||(required&&!v.trim()))fail(400,'VALIDATION','Kolom teks wajib/terlalu panjang');return v.trim();}
function currentPackage(){const pointer=read(path.join(root,'published','current.json'));safeId(pointer.packageId);return path.join(root,'published','packages',pointer.packageId);}
function catalogPath(){return config.mode==='viewer'?path.join(currentPackage(),'catalog.js'):path.join(root,'data','operational','catalog.js');}
module.exports={fs,path,crypto,root,config,fail,read,atomic,transact,id,now,safeId,text,currentPackage,catalogPath};
