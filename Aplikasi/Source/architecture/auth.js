const S=require('./store');
const file=S.path.join(S.root,'data','identity','users.json');
const sessions=Object.create(null), attempts=Object.create(null);
const empty={revision:0,users:{},audit:[]};
function users(){return S.fs.existsSync(file)?S.read(file):empty;}
function password(value,salt){return S.crypto.pbkdf2Sync(value,salt,180000,32,'sha256').toString('hex');}
function credentials(value){S.text(value,200,true);if(value.length<12)S.fail(400,'VALIDATION','Password minimal 12 karakter');const salt=S.crypto.randomBytes(24).toString('hex');return {salt:salt,hash:password(value,salt)};}
function summary(u){return {id:u.id,login:u.login,name:u.name,role:u.role,enabled:u.enabled,revision:u.revision};}
function createFirst(login,name,pw){if(Object.keys(users().users).length)S.fail(409,'SETUP_COMPLETE','Akun sudah tersedia; gunakan pengelola akun');return change(null,{login:login,name:name,password:pw,role:'SUPERUSER',enabled:true},true);}
function change(actor,input,first){if(!first&&(!actor||actor.role!=='SUPERUSER'))S.fail(403,'FORBIDDEN','Hanya supervisor');
 return S.transact(file,empty,function(data){if(first&&Object.keys(data.users).length)S.fail(409,'SETUP_COMPLETE','Setup sudah selesai');
 const uid=input.id?S.safeId(input.id):S.id(),old=data.users[uid];if(input.id&&!old)S.fail(404,'NOT_FOUND','Akun tidak ada');
 if(old&&input.revision!==old.revision)S.fail(409,'CONFLICT','Akun telah berubah');
 const login=S.text(input.login,80,true).toLowerCase();if(!/^[a-z0-9_.-]+$/.test(login))S.fail(400,'VALIDATION','Login hanya huruf, angka, titik, _ dan -');
 if(Object.keys(data.users).some(k=>k!==uid&&data.users[k].login===login))S.fail(409,'DUPLICATE','Login sudah ada');
 if(['SUPERUSER','ENGINEER','VIEWER'].indexOf(input.role)<0||typeof input.enabled!=='boolean')S.fail(400,'VALIDATION','Peran/status tidak valid');
 const u={id:uid,login:login,name:S.text(input.name,120,true),role:input.role,enabled:input.enabled,revision:old?old.revision+1:1,credential:input.password?credentials(input.password):old&&old.credential};
 if(!u.credential)S.fail(400,'VALIDATION','Password wajib untuk akun baru');
 if(old&&old.role==='SUPERUSER'&&old.enabled&&(!u.enabled||u.role!=='SUPERUSER')&&!Object.keys(data.users).some(k=>k!==uid&&data.users[k].enabled&&data.users[k].role==='SUPERUSER'))S.fail(409,'LAST_SUPERVISOR','Minimal satu supervisor aktif');
 data.users[uid]=u;data.revision++;data.audit.unshift({at:S.now(),actor:actor?actor.id:'LOCAL_SETUP',action:old?'UPDATE_USER':'CREATE_USER',target:uid});return summary(u);});}
function authEvent(action,login){const f=S.path.join(S.root,'logs','auth.jsonl');S.fs.mkdirSync(S.path.dirname(f),{recursive:true});S.fs.appendFileSync(f,JSON.stringify({at:S.now(),action:action,login:login})+'\n');}
function cookie(req){return (req.headers.get('cookie')||'').split(';').map(x=>x.trim()).filter(x=>x.indexOf('delimold=')===0).map(x=>x.slice(9))[0]||'';}
function identify(req){if(S.config.mode==='viewer')return {id:'salak-viewer',account:'Viewer SALAK',cloudUser:'Viewer SALAK',pc:'SALAK · salinan baca',role:'VIEWER',canWrite:false,csrf:'viewer',mode:'viewer'};
 const token=cookie(req),hash=S.crypto.createHash('sha256').update(token).digest('hex'),s=sessions[hash],u=s&&users().users[s.userId];
 if(!s||s.expires<Date.now()||!u||!u.enabled||u.revision!==s.revision){delete sessions[hash];S.fail(401,'SESSION_REQUIRED','Silakan login kembali');}
 return {id:u.id,account:u.login,cloudUser:u.name,pc:'TENDERLOIN · browser LAN',role:u.role,canWrite:u.role==='SUPERUSER'||u.role==='ENGINEER',csrf:s.csrf,mode:'master'};}
function login(req,input){if(S.config.mode==='viewer')S.fail(403,'READ_ONLY','SALAK hanya baca');
 const name=String(input.login||'').slice(0,80).toLowerCase(),ip=req.headers.get('x-delimold-peer')||'local',key=ip+'|'+name;
 const a=attempts[key]||{count:0,until:Date.now()+900000};if(a.until<Date.now()){a.count=0;a.until=Date.now()+900000;}attempts[key]=a;
 // Bound memory even when names/IPs vary.
 if(Object.keys(attempts).length>1000)for(const k of Object.keys(attempts))if(attempts[k].until<Date.now())delete attempts[k];
 if(Object.keys(attempts).length>1000)S.fail(429,'LOGIN_LIMIT','Terlalu banyak percobaan. Tunggu 15 menit.');if(a.count>=8)S.fail(429,'LOGIN_LIMIT','Terlalu banyak percobaan; tunggu 15 menit');
 a.count++;const data=users().users;const u=Object.keys(data).map(k=>data[k]).find(v=>v.login===name);
 const pw=typeof input.password==='string'&&input.password.length<=200?input.password:'',salt=u?u.credential.salt:'unknown-user',actual=password(pw,salt);
 if(!u||!u.enabled||!S.crypto.timingSafeEqual(Buffer.from(actual,'hex'),Buffer.from(u.credential.hash,'hex'))){authEvent('LOGIN_FAILED',name);S.fail(401,'LOGIN_FAILED','Login atau password tidak sesuai');}
 delete attempts[key];for(const k of Object.keys(sessions))if(sessions[k].expires<Date.now())delete sessions[k];
 const token=S.crypto.randomBytes(32).toString('hex'),hash=S.crypto.createHash('sha256').update(token).digest('hex');sessions[hash]={userId:u.id,revision:u.revision,csrf:S.id(),expires:Date.now()+Math.min(24,Math.max(1,Number(S.config.sessionHours)||8))*3600000};
 authEvent('LOGIN',u.login);return token;}
function logout(req){authEvent('LOGOUT',identify(req).account);delete sessions[S.crypto.createHash('sha256').update(cookie(req)).digest('hex')];}
function mutation(req,s){if(S.config.mode==='viewer')S.fail(403,'READ_ONLY','SALAK hanya baca');const ct=req.headers.get('content-type')||'';if(ct.indexOf('multipart/form-data')===0){const ref=req.headers.get('referer');if(!ref||new URL(ref).origin!==new URL(req.url).origin)S.fail(403,'CSRF','Sumber unggahan tidak valid');}else if(req.headers.get('x-demo-session')!==s.csrf)S.fail(403,'CSRF','Sesi formulir tidak valid');}
function requireRole(s,privateOnly){if(S.config.mode!=='master'||(privateOnly?s.role!=='SUPERUSER':!s.canWrite))S.fail(403,'FORBIDDEN','Akses tidak diberikan');}
module.exports={identify,login,logout,mutation,requireRole,createFirst,change,list:()=>{const data=users().users;return Object.keys(data).map(k=>summary(data[k]));}};
