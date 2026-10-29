import fs from 'fs';import path from 'path';import os from 'os';import crypto from 'crypto';
const store=require('../architecture/store');const auth=require('../architecture/auth');export const root=store.root;export const db=path.join(root,'data','operational','catalog.js');export const token=crypto.randomBytes(32).toString('hex');
export class ApiError extends Error{constructor(public status:number,public code:string,message:string){super(message)}}
export function actor(req:any){return auth.identify(req).account}
export function writable(){if(store.config.mode==='viewer')return false;try{const fd=fs.openSync(db,'r+');fs.closeSync(fd);return true}catch(e){return false}}
export function originCheck(req:any){const origin=req.headers.get('origin');if(origin&&origin!==new URL(req.url).origin)throw new ApiError(403,'ORIGIN','Origin ditolak.');}
export async function session(req:any){return auth.identify(req)}
export function checkConnection(s:any,write=false){if(!fs.existsSync(store.catalogPath()))throw new ApiError(503,'DATABASE_MISSING','Database belum tersedia.');if(write&&(!s.canWrite||!writable()))throw new ApiError(403,'READ_ONLY','Akun ini hanya boleh membaca.');}
export async function body(req:any){return req.json()};export function json(v:any){return new Response(JSON.stringify(v),{headers:{'Content-Type':'application/json; charset=utf-8'}})}
export async function safe(fn:any){try{return await fn()}catch(e){return new Response(JSON.stringify({code:e.code||'DATABASE_ERROR',error:e.message}),{status:e.status||503,headers:{'Content-Type':'application/json; charset=utf-8'}})}}
