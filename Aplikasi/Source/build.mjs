import fs from 'node:fs';
// Developer build only. The packaged application needs no npm/install step.
import {build} from 'esbuild';import {fileURLToPath} from 'node:url';import path from 'node:path';
const root=path.dirname(fileURLToPath(import.meta.url));const settings={absWorkingDir:root,bundle:true,platform:'node',target:['node12','es2019'],tsconfig:'tsconfig.json',plugins:[{name:'node12-imports',setup(b){b.onResolve({filter:/^node:/},args=>({path:args.path.slice(5),external:true}));}}]};
await build({...settings,entryPoints:['server.ts'],outfile:path.join(root,'..','server.js')});
await build({...settings,entryPoints:['cli.ts'],outfile:path.join(root,'..','..','tools','manage.js')});

for(const name of fs.readdirSync(path.join(root,'public')))fs.copyFileSync(path.join(root,'public',name),path.join(root,'..',name));
