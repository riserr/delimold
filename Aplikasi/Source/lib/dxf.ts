// @ts-nocheck

/* DXF (ASCII) -> SVG vector converter. Pure functions, no DOM. */
var DxfSvg=(function(){
  var DEG=Math.PI/180;

  function parsePairs(text){
    var lines=text.split(/\r\n|\r|\n/),out=[];
    for(var i=0;i+1<lines.length;i+=2){
      var c=parseInt(lines[i],10);
      if(isNaN(c))continue;
      out.push([c,lines[i+1].trim()]);
    }
    return out;
  }
  function readSections(pairs){
    var sec={},i=0,n=pairs.length;
    while(i<n){
      if(pairs[i][0]===0&&pairs[i][1]==='SECTION'){
        var name=(pairs[i+1]&&pairs[i+1][0]===2)?pairs[i+1][1]:'';
        i+=2;var start=i;
        while(i<n&&!(pairs[i][0]===0&&pairs[i][1]==='ENDSEC'))i++;
        sec[name]=pairs.slice(start,i);
      }
      i++;
    }
    return sec;
  }
  function readEntities(pairs){
    var ents=[],cur=null;
    for(var i=0;i<pairs.length;i++){
      var c=pairs[i][0],v=pairs[i][1];
      if(c===0){cur={type:v,p:[]};ents.push(cur)}
      else if(cur)cur.p.push(pairs[i]);
    }
    return ents;
  }
  function groupPolylines(ents){
    var out=[];
    for(var i=0;i<ents.length;i++){
      var e=ents[i];
      if(e.type==='POLYLINE'){
        e.verts=[];
        while(i+1<ents.length&&ents[i+1].type!=='SEQEND'){
          i++;
          if(ents[i].type==='VERTEX')e.verts.push(ents[i]);
        }
        if(i+1<ents.length)i++;
      }
      out.push(e);
    }
    return out;
  }
  function g(e,code,def){
    for(var i=0;i<e.p.length;i++)if(e.p[i][0]===code)return e.p[i][1];
    return def;
  }
  function n(e,code,def){
    var v=g(e,code,null);
    if(v===null)return def===undefined?0:def;
    var x=parseFloat(v);
    return isNaN(x)?(def===undefined?0:def):x;
  }
  function all(e,code){
    var r=[];
    for(var i=0;i<e.p.length;i++)if(e.p[i][0]===code)r.push(parseFloat(e.p[i][1]));
    return r;
  }

  // ---- geometry helpers
  function arcPoints(cx,cy,r,a0,a1,stepDeg){
    var sweep=a1-a0;
    while(sweep<=0)sweep+=360;
    if(sweep>360)sweep=360;
    var steps=Math.max(4,Math.ceil(sweep/stepDeg)),pts=[];
    for(var i=0;i<=steps;i++){
      var a=(a0+sweep*i/steps)*DEG;
      pts.push([cx+r*Math.cos(a),cy+r*Math.sin(a)]);
    }
    return pts;
  }
  function bulgePoints(pts){
    var out=[pts[0].slice(0,2)];
    for(var i=0;i<pts.length-1;i++){
      var p=pts[i],q=pts[i+1],b=p[2]||0;
      if(!b){out.push([q[0],q[1]]);continue}
      var dx=q[0]-p[0],dy=q[1]-p[1],c=Math.hypot(dx,dy);
      if(c===0)continue;
      var theta=4*Math.atan(b),r=c/(2*Math.sin(Math.abs(theta)/2));
      var mx=(p[0]+q[0])/2,my=(p[1]+q[1])/2,h=r*Math.cos(Math.abs(theta)/2);
      // center on the perpendicular bisector: left of p->q for CCW (b>0), right for CW
      var nx=-dy/c,ny=dx/c,sgn=b>0?1:-1;
      var cx=mx+nx*h*sgn,cy=my+ny*h*sgn;
      var a0=Math.atan2(p[1]-cy,p[0]-cx),steps=Math.max(4,Math.ceil(Math.abs(theta)/(3*DEG)));
      for(var s=1;s<=steps;s++){
        var a=a0+theta*s/steps;
        out.push([cx+r*Math.cos(a),cy+r*Math.sin(a)]);
      }
      out[out.length-1]=[q[0],q[1]];
    }
    return out;
  }
  function flatten(p){
    if(p.k==='P')return p.pts;
    if(p.k==='B')return bulgePoints(p.pts);
    if(p.k==='C')return arcPoints(p.cx,p.cy,p.r,0,360,3);
    if(p.k==='A')return arcPoints(p.cx,p.cy,p.r,p.a0,p.a1,3);
    return [];
  }
  function applyM(m,x,y){return [m.a*x+m.c*y+m.e,m.b*x+m.d*y+m.f]}
  function transformPrim(p,m){
    var s1=Math.hypot(m.a,m.b),s2=Math.hypot(m.c,m.d),det=m.a*m.d-m.b*m.c;
    var uniform=Math.abs(s1-s2)<=1e-9*Math.max(s1,s2,1e-12)&&det>0;
    if(p.k==='C'&&uniform){var c=applyM(m,p.cx,p.cy);return {k:'C',cx:c[0],cy:c[1],r:p.r*s1,layer:p.layer}}
    if(p.k==='A'&&uniform){
      var c2=applyM(m,p.cx,p.cy),rot=Math.atan2(m.b,m.a)/DEG;
      return {k:'A',cx:c2[0],cy:c2[1],r:p.r*s1,a0:p.a0+rot,a1:p.a1+rot,layer:p.layer};
    }
    var pts=flatten(p).map(function(q){return applyM(m,q[0],q[1])});
    return {k:'P',pts:pts,layer:p.layer};
  }

  // ---- splines
  function deBoor(k,t,deg,knots,P){
    var d=[],j,r,c;
    for(j=0;j<=deg;j++)d.push(P[j+k-deg].slice());
    for(r=1;r<=deg;r++){
      for(j=deg;j>=r;j--){
        var den=knots[j+1+k-r]-knots[j+k-deg];
        var a=den===0?0:(t-knots[j+k-deg])/den;
        for(c=0;c<3;c++)d[j][c]=(1-a)*d[j-1][c]+a*d[j][c];
      }
    }
    return [d[deg][0]/d[deg][2],d[deg][1]/d[deg][2]];
  }
  function splinePts(e){
    var deg=parseInt(g(e,71,'3'),10)||3,knots=all(e,40),xs=all(e,10),ys=all(e,20),ws=all(e,41);
    var cnt=Math.min(xs.length,ys.length);
    if(cnt>=2&&knots.length===cnt+deg+1&&deg>=1){
      var P=[];
      for(var i=0;i<cnt;i++){var w=ws[i]>0?ws[i]:1;P.push([xs[i]*w,ys[i]*w,w])}
      var t0=knots[deg],t1=knots[cnt],steps=Math.max(24,Math.min(1200,cnt*12)),pts=[];
      for(var s=0;s<=steps;s++){
        var t=t0+(t1-t0)*s/steps,k=deg;
        while(k<cnt-1&&t>=knots[k+1])k++;
        pts.push(deBoor(k,t,deg,knots,P));
      }
      return pts;
    }
    var fx=all(e,11),fy=all(e,21),out=[];
    if(fx.length>=2){for(var a=0;a<fx.length;a++)out.push([fx[a],fy[a]]);return out}
    for(var b=0;b<cnt;b++)out.push([xs[b],ys[b]]);
    return out;
  }

  // ---- entity -> primitives
  function pushPoly(out,verts,closed,layer){
    if(verts.length<2)return;
    var anyB=verts.some(function(v){return v.b});
    var pts=verts.map(function(v){return [v.x,v.y,v.b||0]});
    if(closed){var f=pts[0];pts.push([f[0],f[1],0])}
    if(anyB)out.push({k:'B',pts:pts,layer:layer});
    else out.push({k:'P',pts:pts.map(function(q){return [q[0],q[1]]}),layer:layer});
  }
  function entityPrims(e,blocks,depth,out,ign){
    var layer=g(e,8,'0'),i;
    switch(e.type){
      case 'LINE':
        out.push({k:'P',pts:[[n(e,10),n(e,20)],[n(e,11),n(e,21)]],layer:layer});break;
      case 'LWPOLYLINE':{
        var verts=[],cur=null,closed=(parseInt(g(e,70,'0'),10)&1)===1;
        for(i=0;i<e.p.length;i++){
          var c=e.p[i][0],v=parseFloat(e.p[i][1]);
          if(c===10){cur={x:v,y:0,b:0};verts.push(cur)}
          else if(c===20&&cur)cur.y=v;
          else if(c===42&&cur)cur.b=v;
        }
        pushPoly(out,verts,closed,layer);break;
      }
      case 'POLYLINE':{
        var fl=parseInt(g(e,70,'0'),10);
        if(fl&(16|64)){ign[e.type]=(ign[e.type]||0)+1;break}
        var vs=(e.verts||[]).map(function(x){return {x:n(x,10),y:n(x,20),b:n(x,42)}});
        pushPoly(out,vs,(fl&1)===1,layer);break;
      }
      case 'CIRCLE':
        out.push({k:'C',cx:n(e,10),cy:n(e,20),r:Math.abs(n(e,40)),layer:layer});break;
      case 'ARC':
        out.push({k:'A',cx:n(e,10),cy:n(e,20),r:Math.abs(n(e,40)),a0:n(e,50),a1:n(e,51),layer:layer});break;
      case 'ELLIPSE':{
        var cx=n(e,10),cy=n(e,20),mx=n(e,11),my=n(e,21),ratio=n(e,40,1);
        var s0=n(e,41,0),s1=n(e,42,2*Math.PI);
        if(s1<=s0)s1+=2*Math.PI;
        var pts=[],steps=Math.max(24,Math.ceil((s1-s0)/(2*Math.PI)*180));
        for(i=0;i<=steps;i++){
          var t=s0+(s1-s0)*i/steps;
          pts.push([cx+mx*Math.cos(t)-my*ratio*Math.sin(t),cy+my*Math.cos(t)+mx*ratio*Math.sin(t)]);
        }
        out.push({k:'P',pts:pts,layer:layer});break;
      }
      case 'SPLINE':{
        var sp=splinePts(e);
        if(sp.length>=2)out.push({k:'P',pts:sp,layer:layer});break;
      }
      case 'INSERT':{
        var blk=blocks[g(e,2,'')];
        if(!blk||depth>8){ign[e.type]=(ign[e.type]||0)+1;break}
        var sx=n(e,41,1),sy=n(e,42,1),rot=n(e,50,0)*DEG,ix=n(e,10),iy=n(e,20);
        var co=Math.cos(rot),si=Math.sin(rot);
        var m0={a:co*sx,b:si*sx,c:-si*sy,d:co*sy,e:0,f:0};
        var bx=blk.base[0],by=blk.base[1];
        var m={a:m0.a,b:m0.b,c:m0.c,d:m0.d,e:ix-(m0.a*bx+m0.c*by),f:iy-(m0.b*bx+m0.d*by)};
        var inner=[];
        for(i=0;i<blk.ents.length;i++)entityPrims(blk.ents[i],blocks,depth+1,inner,ign);
        for(i=0;i<inner.length;i++){
          var tp=transformPrim(inner[i],m);
          if(layer!=='0'&&tp.layer==='0')tp.layer=layer;
          out.push(tp);
        }
        break;
      }
      case 'VERTEX':case 'SEQEND':case 'BLOCK':case 'ENDBLK':break;
      default:ign[e.type]=(ign[e.type]||0)+1;
    }
  }

  function parse(text){
    if(/^AutoCAD Binary DXF/.test(text))throw new Error('binary');
    var pairs=parsePairs(text);
    if(!pairs.length)throw new Error('notdxf');
    var sec=readSections(pairs);
    if(!sec.ENTITIES)throw new Error('notdxf');
    var blocks={};
    if(sec.BLOCKS){
      var bents=readEntities(sec.BLOCKS),curB=null;
      for(var i=0;i<bents.length;i++){
        var e=bents[i];
        if(e.type==='BLOCK'){curB={name:g(e,2,''),base:[n(e,10),n(e,20)],ents:[]};blocks[curB.name]=curB}
        else if(e.type==='ENDBLK')curB=null;
        else if(curB)curB.ents.push(e);
      }
      Object.keys(blocks).forEach(function(k){blocks[k].ents=groupPolylines(blocks[k].ents)});
    }
    var ents=groupPolylines(readEntities(sec.ENTITIES)),prims=[],ign={};
    for(var j=0;j<ents.length;j++)entityPrims(ents[j],blocks,0,prims,ign);
    var lm={};
    prims.forEach(function(p){lm[p.layer]=(lm[p.layer]||0)+1});
    var layers=Object.keys(lm).sort().map(function(k){return {name:k,count:lm[k]}});
    return {prims:prims,layers:layers,ignored:ign};
  }

  // ---- joining + simplification
  function joinPolylines(polys){
    var key=function(p){return Math.round(p[0]*1000)+','+Math.round(p[1]*1000)};
    var starts=new Map(),ends=new Map();
    function add(m,k,i){var a=m.get(k);if(a)a.push(i);else m.set(k,[i])}
    polys.forEach(function(pl,i){add(starts,key(pl[0]),i);add(ends,key(pl[pl.length-1]),i)});
    var used=new Array(polys.length).fill(false),out=[];
    function extend(pts){
      for(;;){
        var k=key(pts[pts.length-1]),nxt=-1,rev=false,s=starts.get(k),j;
        if(s)for(j=0;j<s.length;j++)if(!used[s[j]]){nxt=s[j];break}
        if(nxt<0){var e=ends.get(k);if(e)for(j=0;j<e.length;j++)if(!used[e[j]]){nxt=e[j];rev=true;break}}
        if(nxt<0)break;
        used[nxt]=true;
        var add2=polys[nxt];
        if(rev){for(j=add2.length-2;j>=0;j--)pts.push(add2[j])}
        else{for(j=1;j<add2.length;j++)pts.push(add2[j])}
        if(key(pts[0])===key(pts[pts.length-1])&&pts.length>2)break;
      }
    }
    for(var i=0;i<polys.length;i++){
      if(used[i])continue;
      used[i]=true;
      var pts=polys[i].slice();
      extend(pts);
      if(key(pts[0])!==key(pts[pts.length-1])){pts.reverse();extend(pts)}
      out.push(pts);
    }
    return out;
  }
  function rdp(pts,eps){
    if(pts.length<3||eps<=0)return pts;
    var keep=new Uint8Array(pts.length);
    keep[0]=1;keep[pts.length-1]=1;
    var st=[[0,pts.length-1]];
    while(st.length){
      var s=st.pop(),a=s[0],b=s[1],maxd=0,idx=-1;
      var ax=pts[a][0],ay=pts[a][1],dx=pts[b][0]-ax,dy=pts[b][1]-ay,L=dx*dx+dy*dy;
      for(var i=a+1;i<b;i++){
        var d;
        if(L===0)d=Math.hypot(pts[i][0]-ax,pts[i][1]-ay);
        else{
          var t=((pts[i][0]-ax)*dx+(pts[i][1]-ay)*dy)/L;
          t=Math.max(0,Math.min(1,t));
          d=Math.hypot(pts[i][0]-(ax+t*dx),pts[i][1]-(ay+t*dy));
        }
        if(d>maxd){maxd=d;idx=i}
      }
      if(maxd>eps&&idx>0){keep[idx]=1;st.push([a,idx],[idx,b])}
    }
    return pts.filter(function(_,i){return keep[i]});
  }

  // ---- SVG output
  function toSvg(model,opts){
    opts=opts||{};
    var maxChars=opts.maxChars||220000,sel=opts.layers;
    var prims=model.prims.filter(function(p){return !sel||sel.indexOf(p.layer)>=0});
    if(!prims.length)throw new Error('empty');
    var minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
    prims.forEach(function(p){
      var pts=p.k==='C'?[[p.cx-p.r,p.cy-p.r],[p.cx+p.r,p.cy+p.r]]:flatten(p);
      for(var i=0;i<pts.length;i++){
        var x=pts[i][0],y=pts[i][1];
        if(!isFinite(x)||!isFinite(y))continue;
        if(x<minX)minX=x;if(x>maxX)maxX=x;if(y<minY)minY=y;if(y>maxY)maxY=y;
      }
    });
    if(!isFinite(minX))throw new Error('empty');
    var w0=maxX-minX,h0=maxY-minY,diag=Math.hypot(w0,h0)||1;
    var pad=Math.max(w0,h0,diag*0.01)*0.02,W=w0+2*pad,H=h0+2*pad;
    var prec=Math.max(0,Math.min(5,4-Math.floor(Math.log10(diag))));
    var f=function(v){return String(Number(v.toFixed(prec)))};
    var X=function(x){return f(x-minX+pad)},Y=function(y){return f(maxY-y+pad)};
    var polys=[],others=[];
    prims.forEach(function(p){
      if(p.k==='P'&&p.pts.length>=2)polys.push(p.pts);else others.push(p);
    });
    var joined=joinPolylines(polys);
    function build(eps){
      var d=[],i,j;
      for(i=0;i<joined.length;i++){
        var pts=rdp(joined[i],eps);
        if(pts.length<2)continue;
        var s='M'+X(pts[0][0])+' '+Y(pts[0][1])+' ';
        var parts=[];
        for(j=1;j<pts.length;j++)parts.push(X(pts[j][0])+' '+Y(pts[j][1]));
        d.push(s+parts.join(' '));
      }
      others.forEach(function(p){
        if(p.k==='C'){
          var r=f(p.r),l=X(p.cx-p.r),rr=X(p.cx+p.r),y=Y(p.cy);
          d.push('M'+l+' '+y+'A'+r+' '+r+' 0 1 0 '+rr+' '+y+'A'+r+' '+r+' 0 1 0 '+l+' '+y);
        }else if(p.k==='A'){
          var sweep=p.a1-p.a0;while(sweep<=0)sweep+=360;
          var a0=p.a0*DEG,a1=p.a1*DEG,r2=f(p.r);
          var sx=X(p.cx+p.r*Math.cos(a0)),sy=Y(p.cy+p.r*Math.sin(a0));
          var ex=X(p.cx+p.r*Math.cos(a1)),ey=Y(p.cy+p.r*Math.sin(a1));
          if(sweep>=359.999){
            var ox=X(p.cx-p.r*Math.cos(a0)),oy=Y(p.cy-p.r*Math.sin(a0));
            d.push('M'+sx+' '+sy+'A'+r2+' '+r2+' 0 1 0 '+ox+' '+oy+'A'+r2+' '+r2+' 0 1 0 '+sx+' '+sy);
          }else d.push('M'+sx+' '+sy+'A'+r2+' '+r2+' 0 '+(sweep>180?1:0)+' 0 '+ex+' '+ey);
        }else if(p.k==='B'){
          var q=p.pts,s2='M'+X(q[0][0])+' '+Y(q[0][1]);
          for(var k=0;k<q.length-1;k++){
            var a=q[k],b=q[k+1],bu=a[2]||0;
            if(!bu){s2+='L'+X(b[0])+' '+Y(b[1]);continue}
            var c=Math.hypot(b[0]-a[0],b[1]-a[1]);
            if(c===0)continue;
            var rad=c*(1+bu*bu)/(4*Math.abs(bu));
            s2+='A'+f(rad)+' '+f(rad)+' 0 '+(Math.abs(bu)>1?1:0)+' '+(bu>0?0:1)+' '+X(b[0])+' '+Y(b[1]);
          }
          d.push(s2);
        }
      });
      var wv=Number(W.toFixed(prec)),hv=Number(H.toFixed(prec));
      return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 '+wv+' '+hv+'" width="'+wv+'" height="'+hv+'">'
        +'<path d="'+d.join('')+'" fill="none" stroke="#1b2220" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/></svg>';
    }
    var eps=0,svg;
    for(var t=0;t<14;t++){
      svg=build(eps);
      if(svg.length<=maxChars)return {svg:svg,w:W,h:H,simplified:eps>0,count:prims.length};
      eps=eps?eps*2:diag*2e-5;
    }
    throw new Error('toobig');
  }

  var api={parse:parse,toSvg:toSvg,flatten:flatten};

  return api;
})();


export default DxfSvg;
