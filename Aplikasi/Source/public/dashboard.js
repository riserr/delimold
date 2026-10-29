(function () {
    'use strict';
    var S = { tab: 'molds', pc: 'STRAWBERRY', scenario: 'normal', sid: '', identity: null, cloudUser: 'Penguji cloud', connected: false, busy: false, rows: [], patterns: [], events: [], page: 1, grouped: false, sort: 1, editing: null, saving: false, request: 0, logs: [], checked: '' };
    var title = { molds: 'Data Cetakan', patterns: 'Data Pattern', connection: 'Koneksi LAN', history: 'Riwayat perubahan' };
    var subtitle = { molds: 'Kelola dan telusuri seluruh cetakan ban dalam satu tempat.', patterns: 'Kelola pattern dan spesifikasi desain dalam satu library.', connection: 'Pantau koneksi database, akun, komputer, dan hak akses.', history: 'Telusuri siapa mengubah data, dari komputer mana, dan kapan.' };
    var dataTabs={molds:{label:'cetakan'},containers:{label:'container'},patterns:{label:'pattern'},stickers:{label:'sticker'}};
    var roles = { STRAWBERRY: 'Edit', BLUEBERRY: 'Edit', PPC: 'Read-only', PRODUCTION: 'Read-only' };
    var moldFields = [['spec', 'Kode spek', 'text', 1], ['size', 'Size ban', 'text', 1], ['pattern', 'Kode pattern', 'text', 1], ['serial', 'Nomor cetakan', 'text', 1], ['brand', 'Merek', 'text', 1], ['owner', 'Pemilik', 'text', 1], ['bladder', 'Bladder', 'text', 0], ['container', 'Container', 'text', 0], ['status', 'Status', 'select', 1], ['type', 'Tipe cetakan', 'select', 1], ['cure', 'Curing', 'text', 0], ['note', 'Keterangan', 'textarea', 0]];
    function el(id) { return document.getElementById(id); }
    function setText(node, value) { if (typeof node === 'string')
        node = el(node); if (typeof node.textContent !== 'undefined')
        node.textContent = String(value == null ? '' : value);
    else
        node.innerText = String(value == null ? '' : value); }
    function clear(node) { while (node.firstChild)
        node.removeChild(node.firstChild); }
    function make(tag, cls, value) { var n = document.createElement(tag); if (cls)
        n.className = cls; if (value !== undefined)
        setText(n, value); return n; }
    function show(id, yes) { el(id).style.display = yes ? '' : 'none'; }
    function trim(v) { return String(v || '').replace(/^\s+|\s+$/g, ''); }
    function lower(v) { return String(v || '').toLowerCase(); }
    function dateLabel(value) { var m = String(value || '').match(/^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d)/); if (!m)
        return value || '—'; var d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4] + 7, +m[5])); function pad(n) { return n < 10 ? '0' + n : String(n); } return pad(d.getUTCDate()) + '/' + pad(d.getUTCMonth() + 1) + '/' + d.getUTCFullYear() + ' ' + pad(d.getUTCHours()) + ':' + pad(d.getUTCMinutes()) + ' WIB'; }
    function utcStamp(){var d=new Date();function p(n){return n<10?'0'+n:String(n);}return d.getUTCFullYear()+'-'+p(d.getUTCMonth()+1)+'-'+p(d.getUTCDate())+'T'+p(d.getUTCHours())+':'+p(d.getUTCMinutes())+':'+p(d.getUTCSeconds())+'Z';}
    function now() { var d = new Date(); return d.getHours() + ':' + (d.getMinutes() < 10 ? '0' : '') + d.getMinutes(); }
    function canEdit() { return S.connected && S.identity && S.identity.canWrite && !S.busy; }
    function remember() { try {
        window.sessionStorage.setItem('mold-web-preview', JSON.stringify({ sid: S.sid, pc: S.pc, scenario: S.scenario }));
    }
    catch (e) { } }
    function toast(message) { setText('toast', message); show('toast', true); window.clearTimeout(S.toastTimer); S.toastTimer = window.setTimeout(function () { show('toast', false); }, 5000); }
    function api(path, method, payload, done) { var xhr = new XMLHttpRequest(), finished = false, timer; function finish(err, result) { if (finished)
        return; finished = true; window.clearTimeout(timer); done(err, result); } xhr.onreadystatechange = function () { if (xhr.readyState !== 4)
        return; var data; try {
        data = JSON.parse(xhr.responseText);
    }
    catch (e) {
        finish({ code: 'INVALID_RESPONSE', message: 'Respons layanan tidak valid. Coba hubungkan ulang.' });
        return;
    } if(xhr.status===401){window.location.href='/login';return;} if (xhr.status < 200 || xhr.status >= 300) {
        finish({ code: data.code || 'HTTP_' + xhr.status, message: data.error || 'Permintaan gagal.' }, data);
        return;
    } finish(null, data); }; try {
        xhr.open(method, path, true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        if (S.sid)
            xhr.setRequestHeader('X-Demo-Session', S.sid);
        timer = window.setTimeout(function () { finished = true; xhr.abort(); done({ code: 'TIMEOUT', message: 'Layanan belum merespons dalam 10 detik. Coba lagi.' }); }, 10000);
        xhr.send(payload ? JSON.stringify(payload) : null);
    }
    catch (e) {
        finish({ code: 'NETWORK_ERROR', message: 'Koneksi gagal. ' + e.message });
    } }
    function log(message, ok) { S.logs.push({ message: message, ok: ok, time: now() }); renderLog(); }
    function renderLog() { var root = el('log-rows'); clear(root); for (var i = 0; i < S.logs.length; i++) {
        var r = S.logs[i], div = make('div', 'log-row' + (r.ok ? '' : ' bad'));
        div.appendChild(make('span', '', r.ok ? '✓' : '!'));
        div.appendChild(document.createTextNode(r.message));
        div.appendChild(make('small', '', r.time));
        root.appendChild(div);
    } }
    function identity() { var id = S.identity; if(location.protocol!=='file:'){clear(el('computer'));var pcOption=make('option','',S.pc);pcOption.value=S.pc;el('computer').appendChild(pcOption);el('computer').disabled=true;}el('computer').value = S.pc; setText('account-name', S.cloudUser||'Memuat akun…'); setText('permission', id ? id.role : 'Belum diverifikasi'); setText('cloud-user', S.cloudUser); el('cloud-user').title = 'Akun aplikasi: ' + S.cloudUser; setText('identity-detail', S.cloudUser); setText('avatar', S.cloudUser.charAt(0).toUpperCase()); setText('flow-pc', S.pc); el('scenario').value = S.scenario; }
    function unique(field) { var seen = {}, list = []; for (var i = 0; i < S.rows.length; i++) {
        var value = S.rows[i][field];
        if (value && !seen['k' + value]) {
            seen['k' + value] = true;
            list.push(value);
        }
    } list.sort(); return list; }
    function options(id, values, label) { var select = el(id), old = select.value; clear(select); var o = make('option', '', label); o.value = ''; select.appendChild(o); for (var i = 0; i < values.length; i++) {
        o = make('option', '', values[i]);
        o.value = values[i];
        select.appendChild(o);
    } select.value = old; if (select.selectedIndex < 0)
        select.selectedIndex = 0; }
    function cell(tr, value, cls) { var td = make('td', cls || '', value); tr.appendChild(td); return td; }
    function badge(value, cls) { return make('span', 'badge ' + cls, value); }
    function countPattern(code) { var n = 0; for (var i = 0; i < S.rows.length; i++)
        if (S.rows[i].pattern === code)
            n++; return n; }
    function renderHistory() { var root = el('history-rows'), q = lower(trim(el('history-search').value)), count = 0,matching=[];clear(root);for(var hi=0;hi<S.events.length;hi++){var h=S.events[hi];if(!q||lower(h.action+' '+h.record+' '+h.pc+' '+h.actor+' '+h.detail).indexOf(q)>=0)matching.push(h);}var visible=pageList('history',matching,root.parentNode.parentNode);for (var i = 0; i < visible.length; i++) {
        var e = visible[i], hay = e.action + ' ' + e.record + ' ' + e.pc + ' ' + e.actor + ' ' + e.detail;
        if (q && lower(hay).indexOf(q) < 0)
            continue;
        count++;
        var tr = make('tr'), td = cell(tr);
        td.appendChild(make('strong', 'history-action', e.action));
        td.appendChild(make('small', '', e.record));
        cell(tr, e.actor || 'Demo (riwayat lama)');
        cell(tr, e.pc);
        cell(tr, dateLabel(e.at));
        cell(tr, e.detail || 'Rincian belum tersedia untuk riwayat lama.');
        root.appendChild(tr);
    } setText('history-count', matching.length); show('history-empty', count === 0); }
    function field(key, label, value, type, readonly, optionsList) { var labelNode = make('label', 'edit-label' + (type === 'textarea' ? ' wide' : ''), label); labelNode.htmlFor = 'edit-' + key; var input; if (type === 'select') {
        input = make('select');
        for (var i = 0; i < optionsList.length; i++) {
            var o = make('option', '', optionsList[i]);
            o.value = optionsList[i];
            input.appendChild(o);
        }
    }
    else if (type === 'textarea')
        input = make('textarea');
    else {
        input = make('input');
        input.type = 'text';
        input.maxLength = 120;
    } input.id = 'edit-' + key; input.value = value == null ? '' : value; input.disabled = readonly; input.title = label; if (type === 'textarea')
        input.maxLength = 2000; labelNode.appendChild(input); el('edit-fields').appendChild(labelNode); }
    function openModal(titleText, readonly) { setText('form-save','✓ Simpan perubahan'); setText('modal-title', titleText); setText('modal-context', S.pc + ' · ' + (S.identity ? S.identity.account : '') + ' · ' + (S.identity ? S.identity.role : '')); setText('form-help', readonly ? 'Mode baca. Tidak ada perubahan yang dapat disimpan.' : 'Izin, kolom wajib, duplikat, dan versi diperiksa oleh server saat menyimpan.'); show('form-error', false); show('form-save', !readonly); setText('form-cancel', readonly ? 'Tutup' : 'Batal'); el('form-cancel').disabled = false; el('modal-close').disabled = false; show('modal-shade', true); show('modal', true); var inputs = el('edit-fields').getElementsByTagName('input'); for (var i = 0; i < inputs.length; i++)
        if (!inputs[i].disabled) {
            inputs[i].focus();
            return;
        } el('form-cancel').focus(); }
    function profileChange() { if (S.editing || S.saving) {
        el('computer').value = S.pc;
        el('scenario').value = S.scenario;
        toast('Tutup formulir terlebih dahulu agar draf tidak hilang.');
        return;
    } S.pc = el('computer').value; S.scenario = el('scenario').value; S.identity = null; S.page = 1; connect(true); }
    function reset() { el('mold-search').value = ''; var fs = ['category', 'size', 'status', 'pattern', 'brand', 'owner', 'bladder']; for (var i = 0; i < fs.length; i++)
        el('filter-' + fs[i]).value = ''; S.page = 1; renderMolds(); }
    function refresh() {if(location.protocol==='file:'){reloadFileCatalog();return;} if (S.editing || S.saving) {
        toast('Tutup formulir terlebih dahulu agar draf tidak hilang.');
        return;
    } connect(!S.sid); }
    function init() { el('logout-link').onclick=function(){api('/api/logout','POST',{},function(){window.location.href='/login';});return false;}; bind();initPrintReport();if(location.protocol==='file:'){loadFileCatalog();window.setInterval(reloadFileCatalog,30000);return;} try {
        var saved = JSON.parse(window.sessionStorage.getItem('mold-web-preview') || 'null');
        if (saved && roles[saved.pc]) {
            S.pc = saved.pc;
            S.scenario = saved.scenario || 'normal';
            S.sid = saved.sid || '';
        }
    }
    catch (e) { } el('computer').value = S.pc; el('scenario').value = S.scenario; connect(!S.sid); window.setInterval(background, 30000); }
    S.catalog = null;
    S.assetBusy = false;
    S.excelFields = {};
    S.sheets = [];
    S.excelPlan = null;
    title.containers = 'Data Container';
    title.stickers = 'Data Sticker';
    title.excel = 'Impor / Ekspor Excel';
    subtitle.containers = 'Kelola OD/SW sector dan pilihan spacer container.';
    subtitle.stickers = 'Kelola kode, nama, dan gambar sticker setiap merek.';
    subtitle.excel = 'Sesuaikan kolom Excel, periksa pratinjau, lalu impor ke database.';
    function records(bucket) { if(S.recordCache&&S.recordCache[bucket])return S.recordCache[bucket];var out = [], map = S.catalog ? S.catalog.collections[bucket] : {}; for (var id in map)
        if (map.hasOwnProperty(id)) {
            var row = {};for(var key in map[id])if(Object.prototype.hasOwnProperty.call(map[id],key))row[key]=map[id][key];
            row.id = id;
            out.push(row);
        } S.recordCache=S.recordCache||{};S.recordCache[bucket]=out;return out; }
    function rec(bucket, id) { return S.catalog && S.catalog.collections[bucket][id] || null; }
    function pick(bucket, id, key) { var r = rec(bucket, id); return r ? r[key || 'code'] : '—'; }
    function uid() { return 'web-' + (new Date()).getTime().toString(36) + '-' + Math.random().toString(36).slice(2); }
    function media(bucket, id, svg, draft) { if(location.protocol==='file:'){var asset=rec(bucket,id);var map=S.catalog&&(svg?S.catalog._svg:S.catalog._media);return map&&map[bucket+'/'+id]?'../Database/'+map[bucket+'/'+id]:'';} return '/api/catalog-media?sid=' + encodeURIComponent(S.sid) + (draft ? '&draft=' + encodeURIComponent(draft) : '&bucket=' + bucket + '&id=' + encodeURIComponent(id)) + (svg ? '&format=svg' : ''); }
    function assetImage(bucket,id,draft,cls){var img=make('img',cls||'asset-thumb');img.src=media(bucket,id,false,draft);img.alt=bucket==='stickers'?'Gambar sticker':'Pratinjau gambar pattern';img.tabIndex=0;img.title='Klik untuk memperbesar gambar';img.onclick=function(){openImageViewer(bucket,id,draft);};img.onkeydown=function(e){e=e||window.event;if((e.keyCode||e.which)===13)openImageViewer(bucket,id,draft);};return img;}
    function openImageViewer(bucket,id,draft){
        S.viewerFocus=document.activeElement;S.viewerZoom=1;S.viewerSize=null;
        el('image-viewer').className='image-viewer';show('image-viewer',true);show('viewer-shade',true);
        setText('viewer-title',bucket==='stickers'?'Gambar Sticker':'Gambar Pattern');
        setText('viewer-error','Memuat gambar…');var image=el('viewer-image');image.style.visibility='hidden';
        image.onload=function(){
            image.style.width='auto';image.style.height='auto';
            S.viewerSize={width:image.naturalWidth||image.width,height:image.naturalHeight||image.height};
            setText('viewer-error','');layoutImageViewer();image.style.visibility='visible';
        };
        image.onerror=function(){setText('viewer-error','Gambar gagal dimuat. Periksa koneksi dan coba lagi.');};
        image.src=media(bucket,id,false,draft);setText('viewer-scale','100%');
        show('viewer-svg',bucket==='pattern_art');el('viewer-svg').href=media(bucket,id,true,draft);
        setText('viewer-max','Maksimalkan');el('viewer-close').focus();
    }
    function closeImageViewer(){show('image-viewer',false);show('viewer-shade',false);if(S.viewerFocus&&S.viewerFocus.focus)S.viewerFocus.focus();}
    // A scrollable stage keeps both small and enlarged images centered on both axes.
    function layoutImageViewer(){
        if(!S.viewerSize||el('image-viewer').style.display==='none')return;
        var canvas=el('viewer-canvas'),stage=el('viewer-stage'),image=el('viewer-image');
        stage.style.width='0px';stage.style.height='0px';image.style.display='none';
        var vw=canvas.clientWidth,vh=canvas.clientHeight;
        var fit=Math.min(1,Math.max(1,vw-32)/S.viewerSize.width,Math.max(1,vh-32)/S.viewerSize.height);
        var w=Math.max(1,Math.round(S.viewerSize.width*fit*S.viewerZoom)),h=Math.max(1,Math.round(S.viewerSize.height*fit*S.viewerZoom));
        stage.style.width=Math.max(vw,w+32)+'px';stage.style.height=Math.max(vh,h+32)+'px';
        image.style.width=w+'px';image.style.height=h+'px';image.style.display='block';
        // Account for the scrollbars introduced by large zoom levels.
        var sw=Math.max(canvas.clientWidth,w+32),sh=Math.max(canvas.clientHeight,h+32);
        stage.style.width=sw+'px';stage.style.height=sh+'px';
        image.style.left=Math.round((sw-w)/2)+'px';image.style.top=Math.round((sh-h)/2)+'px';
        canvas.scrollLeft=Math.max(0,(sw-canvas.clientWidth)/2);canvas.scrollTop=Math.max(0,(sh-canvas.clientHeight)/2);
        setText('viewer-scale',Math.round(100*S.viewerZoom)+'%');
    }
    function zoomImage(factor){S.viewerZoom=Math.max(.1,Math.min(8,S.viewerZoom*factor));layoutImageViewer();}

    function modalBusy() { return !!S.printOpen || !!S.editing || S.saving || S.assetBusy; }
    function applyCatalog(data) { S.catalog = data; S.recordCache={};S.useCache=null; S.rows = records('molds'); S.patterns = records('patterns'); }
    function failed(err) { S.busy = false; S.connected = false; S.catalog = null; S.recordCache={};S.useCache=null; S.rows = []; S.patterns = []; S.events = []; setText('error-code', err.code); setText('error-message', err.message); show('error-panel', true); log(err.code + ' · ' + err.message, false); renderAll(); }
    function connect(create) { var ticket = ++S.request; S.busy = true; S.connected = false; S.catalog = null; S.recordCache={};S.useCache=null; S.rows = []; S.patterns = []; S.events = []; S.logs = []; show('error-panel', false); renderAll(); log('Menyiapkan sesi ' + S.pc, true); function current() { return ticket === S.request; } function fetchData() { api('/api/identity', 'GET', null, function (err, id) { if (!current())
        return; if (err) {
        if ((err.code === 'SESSION_REQUIRED' || err.code === 'SESSION_EXPIRED') && !create) {
            S.sid = '';
            connect(true);
            return;
        }
        failed(err);
        return;
    } S.identity = id;S.sid=id.csrf||S.sid;var portal=document.getElementById('portal-link');if(portal)portal.style.display=id.canWrite?'':'none';S.pc=id.pc; S.cloudUser = id.cloudUser; identity(); log('Akun ' + id.account + ' · ' + id.role, true); api('/api/status', 'GET', null, function (err, st) { if (!current())
        return; if (err) {
        failed(err);
        return;
    } S.checked = st.checkedAt; var paths = ['/api/catalog', '/api/events', '/api/catalog-excel?meta=1'], values = [], left = 3, stop = false; function read(index) { api(paths[index], 'GET', null, function (err, d) { if (!current() || stop)
        return; if (err) {
        stop = true;
        failed(err);
        return;
    } values[index] = d; if (--left === 0) {
        applyCatalog(values[0]);
        S.events = values[1].rows;
        S.excelFields = values[2].fields;
        S.connected = true;
        S.busy = false;
        log('Database bersama terhubung; struktur lengkap siap.', true);
        renderFilters();
        renderAll();
        remember();
    } }); } for (var i = 0; i < paths.length; i++)
        read(i); }); }); } if (create || !S.sid) {
        api('/api/session', 'POST', { pc: S.pc, scenario: S.scenario }, function (err, d) { if (!current())
            return; if (err) {
            failed(err);
            return;
        } S.sid = d.sessionId; remember(); fetchData(); });
    }
    else
        fetchData(); }
    function updateStatus() { el('connection-bar').className = 'connection-bar' + (!S.busy && !S.connected ? ' failed' : ''); setText('state-icon', S.busy ? '↻' : S.connected ? '✓' : '!'); setText('connection-title', S.busy ? 'Menghubungkan…' : S.connected ? 'Database terhubung' : 'Koneksi bermasalah'); setText('connection-caption', S.connected ? 'Database bersama · '+(location.protocol==='file:'?'baca langsung':'aplikasi LAN') : 'Menunggu layanan database'); setText('navcount', S.connected ? S.rows.length : '—'); show('readonly-note', S.connected && S.identity && !S.identity.canWrite); el('computer').disabled = true; el('scenario').disabled = S.busy; el('add-record').disabled = !canEdit(); el('refresh-top').disabled = S.busy; el('retry').disabled = S.busy; el('excel-file').disabled = !canEdit(); updateTimes(); el('excel-template').href = '/api/catalog-excel/DELIMOLD-Template.xlsx?template=1&sid=' + encodeURIComponent(S.sid); el('excel-export').href = '/api/catalog-excel/DELIMOLD-Export.xlsx?sid=' + encodeURIComponent(S.sid); }
    function switchTab(tab) {if(location.protocol==='file:'&&tab==='excel'){toast('Jalankan Buka-DELIMOLD.bat untuk impor atau ekspor Excel.');return;} if (modalBusy()) {
        toast('Tutup formulir terlebih dahulu agar draf tidak hilang.');
        return;
    } S.tab = tab; setText('crumb', title[tab]); setText('page-title', title[tab]); setText('page-subtitle', subtitle[tab]); var names = ['molds', 'patterns', 'containers', 'stickers', 'excel', 'connection', 'history']; for (var i = 0; i < names.length; i++) {
        show('view-' + names[i], names[i] === tab);
        el('nav-' + names[i]).className = 'nav' + (names[i] === tab ? ' active' : '');
    } var labels = { molds: 'cetakan', patterns: 'pattern', containers: 'container', stickers: 'sticker' }; show('add-record', !!labels[tab]); show('refresh-top', !labels[tab]); setText('add-record', '＋ Tambah ' + (labels[tab] || '')); renderAll(); }
    function fillPairs(id, pairs, label) { var n = el(id), old = n.value; clear(n); if (label !== null) {
        var o = make('option', '', label || 'Pilih');
        o.value = '';
        n.appendChild(o);
    } for (var i = 0; i < pairs.length; i++) {
        var p = pairs[i], op = make('option', '', p[1]);
        op.value = p[0];
        n.appendChild(op);
    } n.value = old; if (n.selectedIndex < 0)
        n.selectedIndex = 0; }
    function renderFilters() { var fields = ['category', 'size', 'brand', 'owner', 'bladder']; for (var f = 0; f < fields.length; f++) {
        var key = fields[f], seen = {}, vals = [];
        for (var i = 0; i < S.rows.length; i++) {
            var values = key === 'brand' ? S.rows[i].brands || [] : [S.rows[i][key]];
            for (var j = 0; j < values.length; j++) {
                var v = key === 'brand' ? values[j].brand : values[j];
                if (v && !seen[v]) {
                    seen[v] = 1;
                    vals.push(v);
                }
            }
        }
        options('filter-' + key, vals.sort(), { category: 'Semua kategori', size: 'Semua size', brand: 'Semua merek', owner: 'Semua pemilik', bladder: 'Semua bladder' }[key]);
    } var pats = [], cs = records('containers'); for (var p = 0; p < S.patterns.length; p++)
        pats.push([S.patterns[p].id, S.patterns[p].code + ' · ' + S.patterns[p].name]); fillPairs('filter-pattern', pats, 'Semua pattern'); var ct = []; for (var k = 0; k < cs.length; k++)
        ct.push([cs[k].id, cs[k].code]); fillPairs('filter-container', ct, 'Semua container'); fillPairs('filter-cure', [['BOM', 'BOM'], ['Airbag', 'Airbag']], 'Semua masak'); fillPairs('filter-mtype', [['2piece', '2 Piece'], ['segmented', 'Segmented']], 'Semua tipe'); fillPairs('filter-role', [['main', 'Main size'], ['sharing', 'Sharing size']], 'Main / Sharing'); fillPairs('filter-status', [['active', 'Aktif'], ['inactive', 'Nonaktif']], 'Semua status'); }
    function filtered() { var rows = [], q = lower(trim(el('mold-search').value)), fields = ['category', 'size', 'status', 'pattern', 'brand', 'owner', 'bladder', 'cure', 'mtype', 'container', 'role']; for (var i = 0; i < S.rows.length; i++) {
        var r = S.rows[i], hay = [r.category, r.spec, r.size, r.serial, r.cure, r.owner, r.bladder, r.note, pick('patterns', r.patternId), pick('patterns', r.patternId, 'name'), pick('containers', r.containerId), r.mtype === 'segmented' ? 'Segmented' : '2 Piece', r.status === 'active' ? 'Aktif' : 'Nonaktif'], match = true;
        for (var b = 0; b < r.brands.length; b++)
            hay.push(r.brands[b].brand, r.brands[b].insert, pick('stickers', r.brands[b].stickerId));
        if (q && lower(hay.join(' ')).indexOf(q) < 0)
            continue;
        for (var j = 0; j < fields.length; j++) {
            var key = fields[j], value = el('filter-' + key).value;
            if (!value)
                continue;
            if (key === 'brand') {
                var found = false;
                for (b = 0; b < r.brands.length; b++)
                    if (r.brands[b].brand === value)
                        found = true;
                if (!found)
                    match = false;
            }
            else if (r[key === 'pattern' ? 'patternId' : key === 'container' ? 'containerId' : key] !== value)
                match = false;
        }
        if (match)
            rows.push(r);
    } rows.sort(function (a, b) { return (a.spec === b.spec ? String(a.serial).localeCompare(String(b.serial)) : a.spec.localeCompare(b.spec)) * S.sort; }); return rows; }
    function renderMolds() { renderSummary('molds');var i; var all = filtered(), rows = [], seen = {}, counts = {}; for (i = 0; i < all.length; i++) {
        var k = all[i].spec;
        counts[k] = (counts[k] || 0) + 1;
        if (!S.grouped || !seen[k])
            rows.push(all[i]);
        seen[k] = 1;
    } var pages = Math.max(1, Math.ceil(rows.length / pageSize())); S.page = Math.min(S.page, pages); setText('result-count', all.length); el('view-each').className = S.grouped ? '' : 'chosen'; el('view-set').className = S.grouped ? 'chosen' : ''; var root = el('mold-rows'); clear(root); var start = (S.page - 1) * pageSize(), end = Math.min(start + pageSize(), rows.length); for (i = start; i < end; i++) {
        var r = rows[i], tr = make('tr'), td = cell(tr), b = make('button', 'spec-link', r.spec);
        b.type = 'button';
        b.onclick = (function (m) { return function () { openMold(m, !canEdit()); }; })(r);
        td.appendChild(b);
        cell(tr, r.category || '—');
        td = cell(tr);
        td.appendChild(make('strong', 'size-label', r.size));
        var pattern=rec('patterns',r.patternId);td.appendChild(make('small','',pattern?pattern.code+' · '+pattern.name:'—'));
        td = cell(tr, S.grouped ? counts[r.spec] + ' set' : r.serial);
        if (S.grouped && canEdit()) {
            var edit = make('button', 'text-button', 'Edit spek');
            edit.type = 'button';
            edit.onclick = (function (m) { return function () { openGroup(m); }; })(r);
            td.appendChild(make('small'));
            td.appendChild(edit);
        }
        td = cell(tr);td.appendChild(make('span','cure-label',r.cure));if(r.cure==='BOM'&&r.bladder)td.appendChild(make('span','bladder-inline',' · '+r.bladder));
        td.appendChild(make('small', '', r.mtype === 'segmented' ? 'Segmented · ' + (r.role === 'sharing' ? 'Sharing' : 'Main') : '2 Piece'));
        if (r.mtype === 'segmented') {
            var c = rec('containers', r.containerId), od = c ? c.od : null;
            if (c && r.spacer != null)
                for (var z = 0; z < c.spacers.length; z++)
                    if (c.spacers[z].size === r.spacer)
                        od = c.spacers[z].od;
            td.appendChild(make('small', '', pick('containers', r.containerId) + (r.spacer != null ? ' · Spacer ' + r.spacer + ' mm' : '')));
            td.appendChild(make('small', '', c ? 'OD ' + od + ' / SW ' + c.sw : ''));
            if (r.mainId) {
                var main = rec('molds', r.mainId);
                td.appendChild(make('small', '', main ? 'Main: ' + main.spec + '/' + main.serial : 'Main: —'));
            }
        }
        td = cell(tr, '', 'brands-cell');
        for (var j = 0; j < r.brands.length; j++) {
            var br = r.brands[j];
            td.appendChild(make('strong', '', (br.brand || '—')+(br.insert?' · '+br.insert:'')));

        }
        td = cell(tr, r.owner || '—');

        td = cell(tr);
        td.appendChild(badge('• ' + (r.status === 'active' ? 'Aktif' : 'Nonaktif'), r.status === 'active' ? 'active' : 'inactive'));
        if(r.lastStatusReason)td.appendChild(make('small','status-reason','Alasan: '+r.lastStatusReason));
        if (r.note)
            td.appendChild(make('small', '', r.note));
        td = cell(tr);
        if(canEdit()&&!S.grouped){
            b=make('button','button small status-action',r.status==='active'?'Nonaktifkan':'Aktifkan');b.type='button';b.title=(r.status==='active'?'Nonaktifkan ':'Aktifkan ')+r.spec+'/'+r.serial;b.onclick=(function(m){return function(){openStatus(m);};})(r);td.appendChild(b);
            b=make('button','button small status-action','Edit');b.type='button';b.title='Edit '+r.spec+'/'+r.serial;b.onclick=(function(m){return function(){openMold(m,false);};})(r);td.appendChild(b);
            b=make('button','button small status-action danger-action','Hapus');b.type='button';b.title='Hapus '+r.spec+'/'+r.serial;b.onclick=(function(m){return function(){confirmDelete('molds',m);};})(r);td.appendChild(b);
        }else {b=make('button','button small',S.grouped?'Lihat nomor':'Lihat');b.type='button';b.onclick=(function(m){return function(){if(S.grouped){el('mold-search').value=m.spec;S.grouped=false;S.page=1;renderMolds();}else openMold(m,true);};})(r);td.appendChild(b);}
        root.appendChild(tr);
    } show('mold-empty', !rows.length); setText('mold-empty', S.busy ? 'Menghubungkan database…' : !S.connected ? 'Data belum tersedia. Periksa status koneksi.' : 'Tidak ada cetakan ditemukan.'); S.listPages=S.listPages||{};S.listPages.molds=S.page;pageList('molds',rows,el('mold-rows').parentNode.parentNode); }
    function countUse(bucket,id){if(!S.useCache){S.useCache={patterns:{},containers:{},stickers:{}};for(var i=0;i<S.rows.length;i++){var r=S.rows[i],seen={};if(r.patternId)S.useCache.patterns[r.patternId]=(S.useCache.patterns[r.patternId]||0)+1;if(r.containerId)S.useCache.containers[r.containerId]=(S.useCache.containers[r.containerId]||0)+1;for(var j=0;j<r.brands.length;j++){var key=r.brands[j].stickerId;if(key&&!seen[key]){S.useCache.stickers[key]=(S.useCache.stickers[key]||0)+1;seen[key]=true;}}}}return S.useCache[bucket][id]||0;}
    function renderSummary(bucket){var list=records(bucket),codes={},active=0;for(var i=0;i<list.length;i++){codes['k'+lower(bucket==='molds'?list[i].spec:list[i].code)]=true;if(list[i].status!=='inactive')active++;}var count=0;for(var key in codes)if(Object.prototype.hasOwnProperty.call(codes,key))count++;var root=el(bucket+'-summary');clear(root);var name=dataTabs[bucket].label,labels=['Total '+name,'Kode unik','Aktif','Nonaktif'],values=[list.length,count,active,list.length-active],hints=['unit / data',bucket==='molds'?'kode spesifikasi':'kode unik','siap digunakan','dalam pemeriksaan'],icons=['▤','▧','✓','◷'];var table=make('table','stat-table'),tr=make('tr');table.appendChild(tr);for(i=0;i<labels.length;i++){var td=make('td',i===3?'last':''),box=make('div','stat');box.appendChild(make('span','stat-icon'+(i===3?' amber':''),icons[i]));box.appendChild(make('p','',labels[i]));box.appendChild(make('strong','',S.connected?values[i]:'—'));box.appendChild(make('small','',hints[i]));td.appendChild(box);tr.appendChild(td);}root.appendChild(table);}
    function masterMatch(bucket,r,q){var status=el(bucket+'-status-filter').value,used=el(bucket+'-use-filter').value;if(status&&(r.status||'active')!==status)return false;var n=countUse(bucket,r.id);if(used==='used'&&!n||used==='unused'&&n)return false;return !q||lower(r.code+' '+(r.name||'')+' '+(r.serial||'01')).indexOf(q)>=0;}
    function statusCell(root,r){var box=make('div','master-status');box.appendChild(badge(r.status==='inactive'?'Nonaktif':'Aktif',r.status==='inactive'?'inactive':'active'));if(r.lastStatusReason)box.appendChild(make('small','status-reason','Alasan: '+r.lastStatusReason));root.appendChild(box);}
    function masterActions(root,bucket,r){if(!canEdit())return;root.className+=' action-buttons';var edit=root.firstChild;var b=make('button','button small',r.status==='inactive'?'Aktifkan':'Nonaktifkan');b.type='button';b.onclick=function(){openStatus(r,bucket);};root.insertBefore(b,edit);b=make('button','button small danger-action','Hapus');b.type='button';b.onclick=function(){confirmDelete(bucket,r);};root.appendChild(b);}
    // Shared footer for every list. Keep a bounded page window for large catalogs.
    function pagination(root,total,page,onPage){clear(root);function button(label,target,disabled){var n=make('button',target===page&&typeof label==='number'?'current':'',label);n.type='button';n.disabled=disabled;n.title=label==='‹'?'Halaman sebelumnya':label==='›'?'Halaman selanjutnya':'Halaman '+target;if(target===page&&typeof label==='number')n.setAttribute('aria-current','page');n.onclick=function(){onPage(target);};root.appendChild(n);}button('‹',page-1,page<=1);var last=0;for(var i=1;i<=total;i++){if(i!==1&&i!==total&&Math.abs(i-page)>2)continue;if(last&&i-last>1)root.appendChild(make('span','page-gap','…'));button(i,i,false);last=i;}button('›',page+1,page>=total);}
    function pageList(bucket,list,root){if(S.printing)return list;S.listPages=S.listPages||{};var size=pageSize(),pages=Math.max(1,Math.ceil(list.length/size)),page=Math.max(1,Math.min(S.listPages[bucket]||1,pages)),start=(page-1)*size,end=Math.min(start+size,list.length);S.listPages[bucket]=page;var box=el(bucket+'-pager');if(!box){box=make('div','table-footer');box.id=bucket+'-pager';root.parentNode.appendChild(box);}clear(box);var label=bucket==='molds'?(S.grouped?'spesifikasi':'cetakan'):bucket==='patterns'?'pattern':bucket==='containers'?(S.containerGrouped?'kode container':'container'):bucket==='history'?'perubahan':'sticker';box.appendChild(make('span','','Menampilkan '+(list.length?start+1:0)+'–'+end+' dari '+list.length+' '+label));var nav=make('span','pagination');pagination(nav,pages,page,function(target){S.listPages[bucket]=target;if(bucket==='molds')S.page=target;renderActive();});box.appendChild(nav);return list.slice(start,end);}
    // Print from the same list renderer, with pagination temporarily disabled.
    // All state is restored before preview opens; no catalog record is changed.
    function reportText(node) { return typeof node.textContent === 'string' ? node.textContent : node.innerText || ''; }
    function reportFilterText() {
        var bucket=S.tab, lines=[], search=el(bucket==='molds'?'mold-search':bucket==='patterns'?'pattern-search':bucket+'-search');
        if(search&&trim(search.value))lines.push('Pencarian: '+trim(search.value));
        var fields=bucket==='molds'?['category','size','status','pattern','brand','owner','bladder','cure','mtype','container','role']:bucket==='history'?[]:['status','use'];
        var labels={category:'Kategori',size:'Size',status:'Status',pattern:'Pattern',brand:'Merek',owner:'Pemilik',bladder:'Bladder',cure:'Tipe masak',mtype:'Tipe cetakan',container:'Container',role:'Peran',use:'Pemakaian'};
        for(var i=0;i<fields.length;i++){var field=fields[i],select=el(bucket==='molds'?'filter-'+field:bucket+'-'+field+'-filter');if(select&&select.value&&select.selectedIndex>=0)lines.push(labels[field]+': '+reportText(select.options[select.selectedIndex]));}
        return lines.length?lines.join(' | '):'Tanpa filter · seluruh data';
    }
    function closePrintReport() {
        if(!S.printOpen)return;
        show('print-report',false);S.printOpen=false;document.title=S.printOldTitle;
        document.body.style.overflow=S.printOldOverflow;
        if(S.printTrigger)S.printTrigger.focus();
    }
    function cleanReportTable(table) {
        table.removeAttribute('id');table.className='report-table';
        var rows=table.getElementsByTagName('tr'),heads=table.getElementsByTagName('th'),actions=heads.length&&trim(reportText(heads[heads.length-1]))==='AKSI',i;
        if(actions)for(i=0;i<rows.length;i++){var cells=rows[i].cells;if(cells.length)rows[i].removeChild(cells[cells.length-1]);}
        var buttons=table.getElementsByTagName('button');while(buttons.length){var button=buttons[0];if(button.className==='spec-link')button.parentNode.replaceChild(document.createTextNode(reportText(button)),button);else button.parentNode.removeChild(button);}
        var images=table.getElementsByTagName('img');for(i=0;i<images.length;i++){images[i].removeAttribute('tabindex');images[i].removeAttribute('title');}
        var all=table.getElementsByTagName('*');for(i=0;i<all.length;i++){all[i].removeAttribute('id');all[i].removeAttribute('onclick');all[i].removeAttribute('onkeydown');}
        return table;
    }
    function openPrintReport() {
        if(!dataTabs[S.tab]&&S.tab!=='history')return;
        if(S.busy||!S.connected){toast('Hubungkan database terlebih dahulu sebelum mencetak.');return;}
        if(S.printOpen)return;
        var savedPage=S.page,savedPages=S.listPages,savedPatternList=S.patternList,table=null,count=0,mode='',bucket=S.tab,filters=reportFilterText();
        try{
            S.printing=true;S.page=1;S.listPages={};if(bucket==='patterns')S.patternList=true;
            renderActive();
            var root=el(bucket==='molds'?'mold-rows':bucket==='patterns'?'pattern-cards':bucket+'-rows');
            var source=bucket==='patterns'?root.getElementsByTagName('table')[0]:root.parentNode;
            count=source.getElementsByTagName('tbody')[0].getElementsByTagName('tr').length;
            table=cleanReportTable(source.cloneNode(true));
            mode=bucket==='molds'?(S.grouped?'Total Set per kode spek':'Per Cetakan'):bucket==='containers'?(S.containerGrouped?'Total Set per kode container':'Per Container'):'List';
        }catch(e){toast('Pratinjau cetak gagal: '+e.message);return;}
        finally{S.printing=false;S.page=savedPage;S.listPages=savedPages;S.patternList=savedPatternList;renderActive();}
        var report=el('print-report');if(!report){report=make('div');report.id='print-report';report.setAttribute('role','dialog');report.setAttribute('aria-modal','true');report.setAttribute('aria-labelledby','print-heading');document.body.appendChild(report);}clear(report);
        var tools=make('div','report-tools'),close=make('button','button','Tutup pratinjau'),print=make('button','button primary','Cetak / Simpan PDF');
        close.type=print.type='button';close.onclick=closePrintReport;print.onclick=function(){window.print();};print.id='report-print-button';tools.appendChild(print);tools.appendChild(close);
        tools.appendChild(make('p','','Chrome: pilih Save as PDF. IE8: pilih printer PDF yang tersedia; jika tidak ada, cetak melalui Chrome. Untuk tabel lebar, pilih kertas A4 Landscape.'));
        report.appendChild(tools);var paper=make('div','report-paper');paper.appendChild(make('div','report-brand','DELIMOLD'));
        var heading=make('h1','',title[bucket]||('Data '+dataTabs[bucket].label));heading.id='print-heading';paper.appendChild(heading);
        paper.appendChild(make('p','report-mode',mode+' · '+count+' '+(bucket==='history'?'perubahan':bucket==='molds'&&S.grouped?'kode spek':bucket==='containers'&&S.containerGrouped?'kode container':dataTabs[bucket].label)));
        paper.appendChild(make('p','report-filters',filters));
        paper.appendChild(make('p','report-meta','Dicetak: '+dateLabel(utcStamp())+' | Komputer: '+S.pc+' | Akun: '+(S.identity&&S.identity.account||'—')));
        paper.appendChild(make('p','report-meta','Pembaruan data: '+dateLabel(S.checked)+' | Revisi: '+(S.catalog?S.catalog.revision:'—')));
        if(count)paper.appendChild(table);else paper.appendChild(make('p','report-empty','Tidak ada data yang sesuai dengan filter.'));
        paper.appendChild(make('p','report-footer','DELIMOLD · '+count+' hasil · seluruh hasil filter, termasuk halaman lainnya'));
        report.appendChild(paper);S.printOldTitle=document.title;document.title='DELIMOLD - '+reportText(heading);S.printOldOverflow=document.body.style.overflow;document.body.style.overflow='hidden';S.printOpen=true;show('print-report',true);
        // Wait for actual image completion, including cached IE images, before enabling print.
        var imgs=paper.getElementsByTagName('img'),left=imgs.length,failed=0,status=make('p','report-image-status');tools.appendChild(status);
        function imageDone(img,ok){if(img._reportDone)return;img._reportDone=true;if(!ok){failed++;var label=make('span','report-image-error','Gambar tidak tersedia');img.parentNode.replaceChild(label,img);}left--;updateImages();}
        function updateImages(){print.disabled=left>0;setText(status,left?'Memuat '+left+' gambar…':failed?failed+' gambar gagal dimuat. Periksa koneksi sebelum mencetak.':'Siap dicetak.');}
        var imageList=[];for(var i=0;i<imgs.length;i++)imageList.push(imgs[i]);left=imageList.length;updateImages();
        for(i=0;i<imageList.length;i++)(function(img){img.onload=function(){imageDone(img,true);};img.onerror=function(){imageDone(img,false);};if(img.complete)imageDone(img,typeof img.naturalWidth==='undefined'||img.naturalWidth>0);})(imageList[i]);
        window.setTimeout(function(){for(var j=0;j<imageList.length;j++)if(!imageList[j]._reportDone)imageDone(imageList[j],false);},15000);
        close.focus();
    }
    function initPrintReport() {
        var tabs=['molds','containers','patterns','stickers','history'];
        for(var i=0;i<tabs.length;i++){
            var divs=el('view-'+tabs[i]).getElementsByTagName('div'),header=null;for(var j=0;j<divs.length;j++)if(divs[j].className==='panel-title'){header=divs[j];break;}
            if(!header)continue;var actions=make('div','list-header-actions'),toggle=null;
            for(j=0;j<header.childNodes.length;j++)if(header.childNodes[j].className==='view-switch'){toggle=header.childNodes[j];break;}
            if(toggle)actions.appendChild(toggle);
            var button=make('button','button print-list-button','Cetak / PDF');button.type='button';button.id='print-'+tabs[i];button.title='Cetak seluruh hasil pencarian dan filter pada tab ini';button.onclick=function(){S.printTrigger=this;openPrintReport();};actions.appendChild(button);header.insertBefore(actions,header.firstChild);
        }
    }

    function pageSize(){if(S.printing)return 2147483647;return parseInt(el('records-per-page').value,10)||100000;}
    function renderPatterns() { renderSummary('patterns');var root = el('pattern-cards'), q = lower(el('pattern-search').value), n = 0; clear(root);var filtered=[];for(var fi=0;fi<S.patterns.length;fi++)if(masterMatch('patterns',S.patterns[fi],q))filtered.push(S.patterns[fi]);var visible=pageList('patterns',filtered,root);var table,tbody;if(S.patternList){table=make('table','records pattern-list-table');var head=make('thead'),hr=make('tr');var headers=['GAMBAR','KODE / NAMA','LAND RATIO','DIPAKAI','STATUS / KETERANGAN','AKSI'];for(var hi=0;hi<headers.length;hi++)hr.appendChild(make('th','',headers[hi]));head.appendChild(hr);table.appendChild(head);tbody=make('tbody');table.appendChild(tbody);root.appendChild(table);} for (var i = 0; i < visible.length; i++) {
        var p = visible[i];
        if (q && lower(p.code + ' ' + p.name).indexOf(q) < 0)
            continue;
        n++;
        if(S.patternList){var row=make('tr'),td=cell(row);if(p.hasArt)td.appendChild(assetImage('pattern_art',p.id));else td.appendChild(make('small','','Belum ada gambar'));td=cell(row,p.code);td.appendChild(make('small','',p.name));cell(row,p.land==null?'—':p.land+'%');cell(row,countUse('patterns',p.id));td=cell(row);statusCell(td,p);td=cell(row);var editButton=make('button','button small',canEdit()?'Edit':'Detail');editButton.type='button';editButton.onclick=(function(record){return function(){openPattern(record,!canEdit());};})(p);td.appendChild(editButton);masterActions(td,'patterns',p);tbody.appendChild(row);continue;}
        var card = make('div', 'pattern-card'), art = make('div', 'pattern-art-image');
        if (p.hasArt)
            art.appendChild(assetImage('pattern_art', p.id, null, ''));
        else
            art.appendChild(make('p', 'preview-note', 'Belum ada gambar DXF'));
        card.appendChild(art);
        var body = make('div', 'pattern-card-body');
        body.appendChild(make('h3', '', p.code));
        body.appendChild(make('p', '', p.name));
        body.appendChild(make('small', '', p.land == null ? 'Land ratio: —' : 'Land ratio: ' + p.land + '%'));
        body.appendChild(make('small', '', countUse('patterns', p.id) + ' cetakan'));
        card.appendChild(body);
        var bottom = make('div', 'pattern-card-bottom'), b = make('button', '', canEdit() ? 'Edit pattern' : 'Lihat detail');
        b.type = 'button';
        b.onclick = (function (p) { return function () { openPattern(p, !canEdit()); }; })(p);
        bottom.appendChild(b);
        b = make('button', '', 'Lihat cetakan ↗');
        b.type = 'button';
        b.onclick = (function (id) { return function () { el('filter-pattern').value = id; el('mold-search').value = ''; S.page = 1; switchTab('molds'); }; })(p.id);
        bottom.appendChild(b);
        masterActions(bottom,'patterns',p);statusCell(body,p);card.appendChild(bottom);
        root.appendChild(card);
    } setText('pattern-count', filtered.length); show('pattern-empty', !n); }
    function renderMasters() { var buckets = [S.tab==='stickers'?'stickers':'containers']; for (var k = 0; k < buckets.length; k++) {
        var bucket = buckets[k], list = records(bucket), q = lower(el(bucket + '-search').value), root = el(bucket + '-rows'), n = 0;
        if(bucket==='containers'){show('containers-used-heading',!!S.containerGrouped);el('containers-each').className=S.containerGrouped?'':'chosen';el('containers-set').className=S.containerGrouped?'chosen':'';}renderSummary(bucket);clear(root);var matching=[];for(var fi=0;fi<list.length;fi++)if(masterMatch(bucket,list[fi],q))matching.push(list[fi]);if(bucket==='containers'&&S.containerGrouped){var groups={},grouped=[];for(var gi=0;gi<matching.length;gi++){var gkey=lower(matching[gi].code);if(!groups[gkey]){groups[gkey]={};for(var prop in matching[gi])if(Object.prototype.hasOwnProperty.call(matching[gi],prop))groups[gkey][prop]=matching[gi][prop];groups[gkey].members=[];grouped.push(groups[gkey]);}groups[gkey].members.push(matching[gi]);}matching=grouped;}list=pageList(bucket,matching,root.parentNode.parentNode);
        for (var i = 0; i < list.length; i++) {
            var r = list[i];
            n++;
            var tr = make('tr'), td;
            if (bucket === 'containers') {
                td=cell(tr,r.code);td.appendChild(make('small','',S.containerGrouped?r.members.length+' set':'No. '+(r.serial||'01')));
                cell(tr, r.od);
                cell(tr, r.sw);
                td = cell(tr);
                for (var j = 0; j < r.spacers.length; j++)
                    td.appendChild(make('small', '', r.spacers[j].size + ' mm → OD ' + r.spacers[j].od));
                if (!r.spacers.length)
                    setText(td, 'Tanpa spacer');
            }
            else {
                td = cell(tr);
                if (r.img)
                    td.appendChild(assetImage('stickers', r.id));
                else
                    setText(td, 'Belum ada gambar');
                td = cell(tr, r.code);
                td.appendChild(make('small', '', r.name));
            }
            var used=countUse(bucket,r.id);if(r.members){used=0;for(var mi=0;mi<r.members.length;mi++)used+=countUse(bucket,r.members[mi].id);}if(bucket!=='containers'||S.containerGrouped)cell(tr,used);td=cell(tr);if(r.members){var ac=0;for(var mi=0;mi<r.members.length;mi++)if(r.members[mi].status!=='inactive')ac++;td.appendChild(make('small','',ac+' aktif / '+(r.members.length-ac)+' nonaktif'));}else statusCell(td,r);
            td = cell(tr);
            if(r.members){var view=make('button','button small','Lihat nomor');view.type='button';view.onclick=(function(code){return function(){S.containerGrouped=false;el('containers-search').value=code;S.listPages.containers=1;renderMasters();};})(r.code);td.appendChild(view);root.appendChild(tr);continue;}var b = make('button', 'button small', canEdit() ? 'Edit' : 'Detail');
            b.type = 'button';
            b.onclick = (function (bucket, r) { return function () { openMaster(bucket, r, !canEdit()); }; })(bucket, r);
            td.appendChild(b);
            masterActions(td,bucket,r);root.appendChild(tr);
        }
        setText(bucket + '-count', matching.length);
        show(bucket + '-empty', !n);
    } }
    function updateTimes(){setText('checked-time',S.catalog?(S.catalog.publishedAt?'Terakhir diperbarui SALAK '+dateLabel(S.catalog.publishedAt):'Terakhir diperbarui '+dateLabel(S.catalog.updatedAt)):'Menunggu koneksi');}
    function renderAll() {var buckets=['patterns','containers','stickers'];for(var bi=0;bi<buckets.length;bi++)setText('navcount-'+buckets[bi],S.connected?records(buckets[bi]).length:'—');updateTimes();identity();updateStatus();show('records-per-page-wrap',!!dataTabs[S.tab]||S.tab==='history');if(dataTabs[S.tab]||S.tab==='history'){var panel=el('view-'+S.tab).getElementsByTagName('div'),target=null;for(var pi=0;pi<panel.length;pi++)if(panel[pi].className==='panel'){target=panel[pi];break;}if(target){var filters=target.getElementsByTagName('div');for(pi=0;pi<filters.length;pi++)if(filters[pi].className.indexOf('filter-bar')>=0||filters[pi].className==='history-filter'){target.insertBefore(el('records-per-page-wrap'),filters[pi].nextSibling);break;}}}renderActive(); }
    function renderActive(){if(S.tab==='molds')renderMolds();else if(S.tab==='patterns')renderPatterns();else if(S.tab==='containers'||S.tab==='stickers')renderMasters();else if(S.tab==='history')renderHistory();}
    function selectField(key, label, value, opts, readonly) { field(key, label, value, 'select', readonly, []); var n = el('edit-' + key); for (var i = 0; i < opts.length; i++) {
        var o = make('option', '', opts[i][1]);
        o.value = opts[i][0];
        n.appendChild(o);
    } n.value = value || ''; if (n.selectedIndex < 0)
        n.selectedIndex = 0; }
    function searchableSelect(key, label, value, opts, readonly) {
        selectField(key,label,value,opts,readonly);
        var select=el('edit-'+key),wrap=make('span','search-combo'),input=make('input','select-search'),arrow=make('button','combo-arrow','▾'),list=make('span','combo-options'),matches=[],active=-1;
        select.style.display='none';select.tabIndex=-1;
        input.id='search-'+key;input.type='text';input.disabled=readonly;input.title='Ketik kode spek, nomor atau size untuk mencari Main';input.setAttribute('aria-label','Cari Main size');input.setAttribute('autocomplete','off');input.setAttribute('placeholder','Pilih / cari Main size…');input.setAttribute('role','combobox');input.setAttribute('aria-autocomplete','list');input.setAttribute('aria-expanded','false');
        list.id='choices-'+key;list.setAttribute('role','listbox');input.setAttribute('aria-controls',list.id);list.style.display='none';
        arrow.type='button';arrow.tabIndex=-1;arrow.disabled=readonly;arrow.title='Buka pilihan Main size';arrow.setAttribute('aria-label','Buka pilihan Main size');
        input.value=select.selectedIndex>0?select.options[select.selectedIndex].text:'';input._lastValue=input.value;
        select.parentNode.insertBefore(wrap,select);wrap.appendChild(input);wrap.appendChild(arrow);wrap.appendChild(list);
        function close(){list.style.display='none';input.setAttribute('aria-expanded','false');input.removeAttribute('aria-activedescendant');active=-1;}
        function highlight(index){active=index;var buttons=list.getElementsByTagName('button');for(var i=0;i<buttons.length;i++){buttons[i].className='combo-option'+(i===active?' selected':'');buttons[i].setAttribute('aria-selected',i===active?'true':'false');}if(buttons[active]){input.setAttribute('aria-activedescendant',buttons[active].id);var item=buttons[active];if(item.offsetTop<list.scrollTop)list.scrollTop=item.offsetTop;else if(item.offsetTop+item.offsetHeight>list.scrollTop+list.clientHeight)list.scrollTop=item.offsetTop+item.offsetHeight-list.clientHeight;}}
        function choose(index){if(!matches[index])return;select.value=matches[index][0];input.value=matches[index][1];input._lastValue=input.value;if(select.onchange)select.onchange();input.focus();close();}
        function open(query){if(readonly)return;clear(list);matches=[];active=-1;input.removeAttribute('aria-activedescendant');for(var i=1;i<opts.length;i++){if(lower(opts[i][1]).indexOf(lower(trim(query)))<0)continue;matches.push(opts[i]);var button=make('button','combo-option',opts[i][1]);button.type='button';button.tabIndex=-1;button.id='choice-'+key+'-'+matches.length;button.setAttribute('role','option');button.onmousedown=function(e){e=e||window.event;if(e.preventDefault)e.preventDefault();return false;};button.onclick=(function(index){return function(){choose(index);};})(matches.length-1);list.appendChild(button);}if(!matches.length)list.appendChild(make('span','combo-empty','Tidak ada Main size yang cocok.'));list.style.display='block';list.scrollTop=0;input.setAttribute('aria-expanded','true');}
        input.onfocus=function(){open('');this._lastValue=this.value;this.select();};
        input.onkeyup=input.oninput=function(e){e=e||window.event;var code=e&&(e.keyCode||e.which);if(code===13||code===27||code===40||code===38||code===9||this.value===this._lastValue)return;this._lastValue=this.value;select.value='';open(this.value);};
        input.onkeydown=function(e){e=e||window.event;var code=e.keyCode||e.which;if(code===27){close();input.value=select.selectedIndex>0?select.options[select.selectedIndex].text:'';input._lastValue=input.value;e.cancelBubble=true;if(e.stopPropagation)e.stopPropagation();return false;}if(code===40||code===38){if(list.style.display==='none')open(select.value?'':input.value);if(matches.length)highlight(code===40?Math.min(matches.length-1,active+1):Math.max(0,active-1));return false;}if(code===13){if(list.style.display!=='none'){if(active>=0)choose(active);else if(matches.length===1)choose(0);}return false;}if(code===9)close();};
        input.onblur=function(){window.setTimeout(function(){if(!wrap.contains(document.activeElement)){close();if(!select.value){input.value='';input._lastValue='';}}},150);};
        arrow.onmousedown=function(e){e=e||window.event;if(e.preventDefault)e.preventDefault();return false;};arrow.onclick=function(){if(list.style.display==='none'){input.focus();open('');}else close();};
    }
    function masterOptions(bucket, label) { var list = records(bucket), out = [['', label || 'Pilih']]; for (var i = 0; i < list.length; i++)
        out.push([list[i].id, list[i].code + (bucket==='containers'?' / '+(list[i].serial||'01'):'') + (list[i].name ? ' · ' + list[i].name : '')]); return out; }
    function finishModal(label,readonly){openModal(label,readonly);}
    function recordIdentity(record,bucket){return record.spec?record.spec+' / '+record.serial:record.code+(bucket==='containers'?' / '+(record.serial||'01'):'');}
    function openStatus(record,bucket){bucket=bucket||'molds';if(!canEdit())return;S.editing={kind:'status',bucket:bucket,record:record,readonly:false,revision:S.catalog.revision,previousFocus:document.activeElement,targetStatus:record.status==='inactive'?'active':'inactive'};clear(el('edit-fields'));var action=S.editing.targetStatus==='active'?'Aktifkan':'Nonaktifkan';el('edit-fields').appendChild(make('p','form-hint',recordIdentity(record,bucket)+' · '+(record.size||'')+' · '+(record.status==='inactive'?'Nonaktif → Aktif':'Aktif → Nonaktif')));field('statusReason','Keterangan alasan '+action.toLowerCase()+' *','','textarea',false,[]);el('edit-statusReason').setAttribute('aria-required','true');el('edit-fields').appendChild(make('p','form-hint','Wajib diisi. Alasan dicatat bersama akun, komputer, dan waktu pada riwayat perubahan.'));openModal(action+' '+(bucket==='molds'?'cetakan':bucket==='patterns'?'pattern':bucket==='containers'?'container':'sticker'),false);}
    function syncStatusReason(){var e=S.editing;if(!e||e.kind!=='mold')return;show('status-reason-field',(e.record&&el('edit-status').value!==e.record.status)||(!e.record&&el('edit-status').value==='inactive'));}
    function openMold(record, readonly) { var d = record || { spec: '', size: '', patternId: '', serial: '01', cure: '', mtype: '2piece', role: 'main', mainId: '', containerId: '', spacer: null, owner: '', bladder: '', status: 'active', note: '', brands: [{ brand: '', insert: '', stickerId: '' }] }; S.editing = { kind: 'mold', bucket: 'molds', record: record, readonly: readonly, revision: S.catalog.revision, previousFocus: document.activeElement, brands: JSON.parse(JSON.stringify(d.brands || [])), serialTouched: !!record }; clear(el('edit-fields')); field('spec', 'Kode spek *', d.spec, 'text', readonly, []); field('category', 'Kategori', d.category || '', 'text', readonly, []);field('size', 'Size ban *', d.size, 'text', readonly, []); selectField('patternId', 'Pattern *', d.patternId, masterOptions('patterns', 'Pilih pattern'), readonly); field('serial', 'Nomor cetakan *', d.serial, 'text', readonly, []); selectField('cure', 'Tipe masak *', d.cure, [['', 'Pilih tipe masak'], ['BOM', 'BOM'], ['Airbag', 'Airbag']], readonly); selectField('mtype', 'Tipe cetakan', d.mtype, [['2piece', '2 Piece'], ['segmented', 'Segmented']], readonly); var block = make('div'); block.id = 'segmented-fields'; block.appendChild(make('h3', 'fieldset-title', 'Segmented')); el('edit-fields').appendChild(block); var before = el('edit-fields').childNodes.length; selectField('role', 'Ukuran', d.role, [['main', 'Main size'], ['sharing', 'Sharing size']], readonly); var mains = [['', 'Pilih main size']]; for (var i = 0; i < S.rows.length; i++) {
        var m = S.rows[i];
        if (m.mtype === 'segmented' && m.role === 'main' && (!record || m.id !== record.id))
            mains.push([m.id, m.spec + '/' + m.serial + ' · ' + m.size]);
    } searchableSelect('mainId', 'Main size', d.mainId, mains, readonly); selectField('containerId', 'Container', d.containerId, masterOptions('containers', 'Pilih container'), readonly); selectField('spacer', 'Spacer', d.spacer == null ? '' : String(d.spacer), [['', 'Tanpa spacer']], readonly); while (el('edit-fields').childNodes.length > before)
        block.appendChild(el('edit-fields').childNodes[before]); field('owner', 'Pemilik cetakan', d.owner, 'text', readonly, []); field('bladder', 'Bladder', d.bladder, 'text', readonly, []); selectField('status', 'Status', d.status, [['active', 'Aktif'], ['inactive', 'Nonaktif (tidak bisa dipakai)']], readonly); field('statusReason','Alasan perubahan status *','','textarea',readonly,[]); el('edit-statusReason').parentNode.id='status-reason-field'; el('edit-status').onchange=syncStatusReason; syncStatusReason(); field('note', 'Keterangan', d.note, 'textarea', readonly, []); var hint = make('div', 'form-hint'); hint.id = 'spec-hint'; el('edit-fields').appendChild(hint); el('edit-fields').appendChild(make('h3', 'fieldset-title', 'Merek')); var brands = make('div'); brands.id = 'brand-rows'; el('edit-fields').appendChild(brands); if (!readonly) {
        var b = make('button', 'button small', 'Tambah merek');
        b.type = 'button';
        b.onclick = function () { readBrands();  S.editing.brands.push({ brand: '', insert: '', stickerId: '' }); renderBrands(); };
        el('edit-fields').appendChild(b);
    } renderBrands(); el('edit-spec').onkeyup = el('edit-spec').oninput = syncSpec; el('edit-serial').onkeyup = el('edit-serial').oninput = function () { S.editing.serialTouched = true; }; el('edit-mtype').onchange = el('edit-role').onchange = syncSegment; el('edit-containerId').onchange = function () { spacerOptions(''); }; el('edit-mainId').onchange = function () { var search=el('search-mainId');if(search){search.value=this.selectedIndex>0?this.options[this.selectedIndex].text:'';search._lastValue=search.value;}var m = rec('molds', this.value); if (m) {
        el('edit-containerId').value = m.containerId;
        spacerOptions('');
    } }; el('edit-cure').onchange=syncCure;syncCure();spacerOptions(d.spacer == null ? '' : String(d.spacer)); syncSpec(); syncSegment(); finishModal(readonly ? 'Detail cetakan' : record ? 'Edit nomor cetakan' : 'Tambah cetakan', readonly); }
    function syncSpec() { if (!S.editing || S.editing.kind !== 'mold')
        return; var spec = lower(trim(el('edit-spec').value)), others = [], max = 0,serialWidth=2; for (var i = 0; i < S.rows.length; i++) {
        var r = S.rows[i];
        if (lower(r.spec) === spec && (!S.editing.record || r.id !== S.editing.record.id)) {
            others.push(r);
            max = Math.max(max, parseInt(r.serial, 10) || 0);serialWidth=Math.max(serialWidth,String(r.serial).length);
        }
    } if (others.length) {
        el('edit-size').value = others[0].size;
        if(!S.editing.record&&!trim(el('edit-category').value))el('edit-category').value=others[0].category||'';
        el('edit-patternId').value = others[0].patternId;
        el('edit-size').disabled = true;
        el('edit-patternId').disabled = true;
        if (!S.editing.serialTouched) {
            var n = max + 1;
            var serial=String(n);while(serial.length<serialWidth)serial='0'+serial;el('edit-serial').value=serial;
        }
        setText('spec-hint', 'Kode spek sudah terdaftar. Size dan Pattern otomatis mengikuti; sudah ada ' + others.length + ' nomor cetakan.');
    }
    else {
        el('edit-size').disabled = S.editing.readonly;
        el('edit-patternId').disabled = S.editing.readonly;
        setText('spec-hint', 'Kode spek baru: isi Size dan Pattern. Nomor cetakan wajib unik pada spek yang sama.');
    } }
    function syncCure(){var n=el('edit-bladder'),air=el('edit-cure').value==='Airbag';n.parentNode.style.display=air?'none':'';if(air)n.value='';}
    function syncSegment() { var seg = el('edit-mtype').value === 'segmented'; show('segmented-fields', seg); el('edit-mainId').parentNode.style.display = seg && el('edit-role').value === 'sharing' ? '' : 'none'; }
    function spacerOptions(value) { var n = el('edit-spacer'), c = rec('containers', el('edit-containerId').value); clear(n); var o = make('option', '', 'Tanpa spacer'); o.value = ''; n.appendChild(o); if (c)
        for (var i = 0; i < c.spacers.length; i++) {
            o = make('option', '', c.spacers[i].size + ' mm · OD sector ' + c.spacers[i].od);
            o.value = String(c.spacers[i].size);
            n.appendChild(o);
        } n.value = value; if (n.selectedIndex < 0)
        n.selectedIndex = 0; }
    function readBrands() { var out = []; for (var i = 0; i < S.editing.brands.length; i++)
        out.push({ brand: el('br-brand-' + i).value, insert: el('br-insert-' + i).value, stickerId: S.editing.brands[i].stickerId||'' }); S.editing.brands = out; return out; }
    function renderBrands() { var root = el('brand-rows'); clear(root); var bs = S.editing.brands; for (var i = 0; i < bs.length; i++) {
        var box = make('div', 'brand-editor');
        for (var j = 0; j < 2; j++) {
            var key = ['brand', 'insert', 'sticker'][j], label = make('label', 'edit-label', ['Merek', 'PLUG / PLAT', 'Sticker'][j] + ' ' + (i + 1)), n = make(j === 2 ? 'select' : 'input');
            if (j !== 2)
                n.type = 'text';
            n.id = 'br-' + key + '-' + i;
            if (j === 2) {
                var opts = masterOptions('stickers', 'Tanpa sticker');
                for (var k = 0; k < opts.length; k++) {
                    var o = make('option', '', opts[k][1]);
                    o.value = opts[k][0];
                    n.appendChild(o);
                }
                n.value = bs[i].stickerId || '';
            }
            else
                n.value = bs[i][key] || '';
            n.disabled = S.editing.readonly;
            label.htmlFor = n.id;
            label.appendChild(n);
            box.appendChild(label);
        }
        if (!S.editing.readonly) {
            var b = make('button', 'button small', 'Hapus merek');
            b.type = 'button';
            b.onclick = (function (index) { return function () { readBrands(); S.editing.brands.splice(index, 1); renderBrands(); }; })(i);
            box.appendChild(b);
        }
        root.appendChild(box);
    } }
    function openGroup(record) { S.editing = { kind: 'group', bucket: 'molds', record: record, revision: S.catalog.revision, readonly: false, previousFocus: document.activeElement }; clear(el('edit-fields')); field('spec', 'Kode spek *', record.spec, 'text', false, []); field('category', 'Kategori', record.category || '', 'text', false, []);field('size', 'Size ban *', record.size, 'text', false, []); selectField('patternId', 'Pattern *', record.patternId, masterOptions('patterns', 'Pilih pattern'), false); el('edit-fields').appendChild(make('p', 'form-hint', 'Perubahan Size dan Pattern berlaku untuk semua nomor di kode spek ini.')); openModal('Edit spek', false); }
    function openPattern(record, readonly) { var d = record || { code: '', name: '', land: null }; S.editing = { kind: 'pattern', bucket: 'patterns', record: record, revision: S.catalog.revision, readonly: readonly, previousFocus: document.activeElement, art: null, removeArt: false }; clear(el('edit-fields')); field('code', 'Kode pattern *', d.code, 'text', readonly, []); field('name', 'Nama pattern *', d.name, 'text', readonly, []); field('land', 'Land ratio (%)', d.land == null ? '' : d.land, 'text', readonly, []); assetBox('dxf', record, readonly); finishModal(readonly ? 'Detail pattern' : record ? 'Edit pattern' : 'Tambah pattern', readonly); }
    function openMaster(bucket, record, readonly) { var d = record || (bucket === 'containers' ? { code: '', od: '', sw: '', spacers: [] } : { code: '', name: '', img: '' }); S.editing = { kind: bucket === 'containers' ? 'container' : 'sticker', bucket: bucket, record: record, revision: S.catalog.revision, readonly: readonly, previousFocus: document.activeElement, spacers: JSON.parse(JSON.stringify(d.spacers || [])), image: record ? record.img : '' }; clear(el('edit-fields')); field('code', (bucket === 'containers' ? 'Kode container' : 'Kode sticker') + ' *', d.code, 'text', readonly, []); if (bucket === 'containers') {
        field('serial','Nomor container *',d.serial||'01','text',readonly,[]);field('od', 'OD sector (mm) *', d.od, 'text', readonly, []);
        field('sw', 'SW sector (mm) *', d.sw, 'text', readonly, []);
        el('edit-fields').appendChild(make('h3', 'fieldset-title', 'Spacer'));
        var root = make('div');
        root.id = 'spacer-rows';
        el('edit-fields').appendChild(root);
        renderSpacers();
        if (!readonly) {
            var b = make('button', 'button small', 'Tambah ukuran spacer');
            b.type = 'button';
            b.onclick = function () { readSpacers(); S.editing.spacers.push({ size: '', od: '' }); renderSpacers(); };
            el('edit-fields').appendChild(b);
        }
    }
    else {
        field('name', 'Nama sticker *', d.name, 'text', readonly, []);
        assetBox('jpg', record, readonly);
    } finishModal(readonly ? 'Detail ' + (bucket === 'containers' ? 'container' : 'sticker') : (record ? 'Edit ' : 'Tambah ') + (bucket === 'containers' ? 'container' : 'sticker'), readonly); }
    function readSpacers() { var out = []; for (var i = 0; i < S.editing.spacers.length; i++)
        out.push({ size: el('sp-size-' + i).value, od: el('sp-od-' + i).value }); S.editing.spacers = out; return out; }
    function renderSpacers() { var root = el('spacer-rows'); clear(root); for (var i = 0; i < S.editing.spacers.length; i++) {
        var box = make('div', 'spacer-editor');
        for (var j = 0; j < 2; j++) {
            var key = j ? 'od' : 'size', label = make('label', 'edit-label', j ? 'OD sector baru (mm)' : 'Ukuran spacer (mm)'), n = make('input');
            n.type = 'text';
            n.id = 'sp-' + key + '-' + i;
            n.value = S.editing.spacers[i][key];
            n.disabled = S.editing.readonly;
            label.htmlFor = n.id;
            label.appendChild(n);
            box.appendChild(label);
        }
        if (!S.editing.readonly) {
            var b = make('button', 'button small', 'Hapus');
            b.type = 'button';
            b.onclick = (function (index) { return function () { readSpacers(); S.editing.spacers.splice(index, 1); renderSpacers(); }; })(i);
            var actions=make('span','spacer-actions');actions.appendChild(b);box.appendChild(actions);
        }
        root.appendChild(box);
    } }
    function assetBox(kind, record, readonly) { var box = make('div', 'asset-box'); box.id = 'asset-box'; box.appendChild(make('h3', '', kind === 'dxf' ? 'Gambar pattern · DXF → SVG' : 'Gambar sticker · JPG')); box.appendChild(make('p', '', kind === 'dxf' ? 'Unggah DXF ASCII (maksimal 8 MB). SVG dikonversi otomatis. Centang layer yang ingin disimpan; pratinjau JPG tersedia untuk browser lama.' : 'Unggah JPG/JPEG maksimal 8 MB dan 16 megapiksel. Gambar dikecilkan otomatis di server.')); if (!readonly) {
        var file = make('input');
        file.type = 'file';
        file.name = 'file';
        file.id = 'asset-file';
        file.accept = kind === 'dxf' ? '.dxf,.DXF' : '.jpg,.jpeg';
        file.onchange = function () { nativeUpload(this, kind, assetUploaded); };
        box.appendChild(file);
    } var msg = make('p', 'form-help'); msg.id = 'asset-message'; box.appendChild(msg); var layers = make('div'); layers.id = 'asset-layers'; box.appendChild(layers); var preview = make('div', 'asset-preview'); preview.id = 'asset-preview'; if (record && (kind === 'dxf' ? record.hasArt : record.img)) {
        preview.appendChild(assetImage(kind === 'dxf' ? 'pattern_art' : 'stickers', record.id, null, 'file-preview-large'));

    }
    else
        preview.appendChild(make('p', 'preview-note', 'Belum ada gambar.')); box.appendChild(preview); if (!readonly) {
        var b = make('button', 'button small', 'Hapus gambar');
        b.type = 'button';
        b.onclick = function () { if (kind === 'dxf') {
            S.editing.removeArt = true;
            S.editing.art = null;S.editing.layerDirty=false;clear(el('asset-layers'));
        }
        else
            S.editing.image = ''; clear(el('asset-preview')); setText('asset-message', 'Gambar akan dihapus saat data disimpan.'); };
        box.appendChild(b);
    } el('edit-fields').appendChild(box); }
    function nativeUpload(input, kind, callback) { if (!canEdit() || S.assetBusy || !input.value)
        return; S.assetBusy = true; var original = input, copyInput = input.cloneNode(true); copyInput.value = ''; copyInput.onchange = function () { nativeUpload(this, kind, callback); }; input.parentNode.replaceChild(copyInput, input); var form = el('native-upload-form'), frame = el('native-upload-frame'); original.removeAttribute('id'); original.name = 'file'; form.appendChild(original); el('native-upload-sid').value = S.sid; el('native-upload-kind').value = kind; form.encoding = 'multipart/form-data'; var done = false, timer; function finish(error, result) { if (done)
        return; done = true; clearTimeout(timer); S.assetBusy = false; if (original.parentNode)
        original.parentNode.removeChild(original); if (el('form-save'))
        el('form-save').disabled = false; callback(error, result); } frame.onload = function () { try {
        var doc = frame.contentDocument || frame.contentWindow.document, node = doc.getElementById('upload-result');
        if (!node)
            return;
        var raw = typeof node.value === 'string' ? node.value : node.innerText, result = JSON.parse(raw);
        finish(result.ok ? null : result.error, result);
    }
    catch (e) {
        finish('Unggahan belum dapat dibaca. Hubungkan ulang dan pilih file kembali.');
    } }; if (kind === 'excel')
        setText('excel-upload-status', 'Membaca file Excel…');
    else {
        setText('asset-message', 'Mengunggah dan memproses file…');
        el('form-save').disabled = true;
    } timer = setTimeout(function () { finish('Unggahan melewati batas waktu. Coba file lebih kecil.'); }, 60000); try {
        form.submit();
    }
    catch (e) {
        finish('Unggahan gagal: ' + e.message);
    } }
    function assetUploaded(error, result) { if (!S.editing)
        return; if (error) {
        setText('asset-message', error);
        return;
    } clear(el('asset-preview')); el('asset-preview').appendChild(assetImage(S.editing.kind === 'pattern' ? 'pattern_art' : 'stickers', '', result.draft, 'file-preview-large')); if (S.editing.kind === 'sticker') {
        S.editing.image = result.img;
        setText('asset-message', 'JPG sudah dikompresi dan siap disimpan.');
        return;
    } S.editing.art = result; S.editing.removeArt = false; S.editing.layerDirty = false; var root = el('asset-layers'); clear(root); for (var i = 0; i < result.layers.length; i++) {
        var label = make('label', 'layer-label'), box = make('input');
        box.type = 'checkbox';
        box.id = 'layer-' + i;
        box.checked = true;
        box.defaultChecked = true;
        box.value = result.layers[i].name;
        box.onchange = function () { S.editing.layerDirty = true; setText('asset-message', 'Pilihan layer berubah. Klik Konversi layer terpilih sebelum menyimpan.'); };
        label.appendChild(box);
        label.appendChild(document.createTextNode(result.layers[i].name + ' (' + result.layers[i].count + ')'));
        root.appendChild(label);
    } var b = make('button', 'button small', 'Konversi layer terpilih'); b.type = 'button'; b.onclick = convertLayers; root.appendChild(b); var a = make('a', 'button small', 'Unduh SVG hasil konversi'); a.id = 'draft-svg-download'; a.href = media('pattern_art', '', true, result.draft); root.appendChild(a); setText('asset-message', 'DXF dikonversi otomatis menjadi SVG. Pilih layer jika ingin membatasi hasil.'); }
    function convertLayers() { if (S.assetBusy || !S.editing.art)
        return; var boxes = el('asset-layers').getElementsByTagName('input'), layers = []; for (var i = 0; i < boxes.length; i++)
        if (boxes[i].checked)
            layers.push(boxes[i].value); if (!layers.length) {
        setText('asset-message', 'Pilih minimal satu layer.');
        return;
    } S.assetBusy = true; el('form-save').disabled = true; setText('asset-message', 'Mengonversi layer terpilih…'); api('/api/catalog-convert', 'POST', { draft: S.editing.art.draft, layers: layers }, function (err, result) { S.assetBusy = false; el('form-save').disabled = false; if (err) {
        setText('asset-message', err.message);
        return;
    } S.editing.art = result; S.editing.layerDirty = false; clear(el('asset-preview')); el('asset-preview').appendChild(assetImage('pattern_art', '', result.draft, 'file-preview-large')); el('draft-svg-download').href = media('pattern_art', '', true, result.draft); setText('asset-message', 'SVG siap disimpan: ' + layers.join(', ')); }); }
    function numberValue(value) { var v = trim(value).replace(',', '.'); return v === '' ? null : Number(v); }
    function submitChanges(changes, revision, message) { S.saving = true; el('form-save').disabled = true; el('form-cancel').disabled = true; el('modal-close').disabled = true; setText('form-save', 'Menyimpan…'); show('form-error', false); api('/api/catalog', 'POST', { revision: revision, changes: changes }, function (err, result) { S.saving = false; el('form-save').disabled = false; el('form-cancel').disabled = false; el('modal-close').disabled = false; setText('form-save', '✓ Simpan perubahan'); if (err) {
        setText('form-error', err.code + ' · ' + err.message + ' Isi formulir dipertahankan.');
        show('form-error', true);
        return;
    } closeModal(); toast(message || 'Data tersimpan ke database bersama.'); connect(false); }); }
    function saveForm(event) { if (event && event.preventDefault)
        event.preventDefault(); if (!S.editing || S.editing.readonly || S.saving || !canEdit())
        return false; if (S.assetBusy) {
        toast('Tunggu unggahan selesai.');
        return false;
    } var e = S.editing, id = e.record ? e.record.id : uid(), d = {}, changes = []; function val(k) { return trim(el('edit-' + k).value); } if(e.kind==='delete'){changes.push({bucket:e.bucket,id:id,mode:'delete'});if(e.bucket==='patterns'&&e.record.hasArt)changes.push({bucket:'pattern_art',id:id,mode:'delete'});}
    else if(e.kind==='status'){d={status:e.targetStatus,statusReason:val('statusReason')};if(!d.statusReason){setText('form-error','Keterangan alasan wajib diisi.');show('form-error',true);el('edit-statusReason').focus();return false;}changes.push({bucket:e.bucket,id:id,mode:'update',data:d});}
    else if (e.kind === 'mold') {
        var keys = ['spec', 'category', 'size', 'patternId', 'serial', 'cure', 'mtype', 'role', 'mainId', 'containerId', 'owner', 'bladder', 'status', 'note'];
        for (var i = 0; i < keys.length; i++)
            d[keys[i]] = val(keys[i]);
        d.statusReason=val('statusReason'); if(((e.record&&e.record.status!==d.status)||(!e.record&&d.status==='inactive'))&&!d.statusReason){setText('form-error','Keterangan alasan perubahan status wajib diisi.');show('form-error',true);el('edit-statusReason').focus();return false;}
        if(d.cure==='Airbag')d.bladder='';d.spacer = numberValue(val('spacer'));
        if (d.mtype !== 'segmented') {
            d.role = '';
            d.mainId = '';
            d.containerId = '';
            d.spacer = null;
        }
        else if (d.role !== 'sharing')
            d.mainId = '';
        var rows = readBrands();
        d.brands = [];
        for (i = 0; i < rows.length; i++)
            if (rows[i].brand || rows[i].insert || rows[i].stickerId)
                d.brands.push(rows[i]);
        changes.push({ bucket: 'molds', id: id, mode: 'set', data: d });
    }
    else if (e.kind === 'group') {
        for (i = 0; i < S.rows.length; i++)
            if (S.rows[i].spec === e.record.spec)
                changes.push({ bucket: 'molds', id: S.rows[i].id, mode: 'update', data: { spec: val('spec'), category: val('category'), size: val('size'), patternId: val('patternId') } });
    }
    else if (e.kind === 'pattern') {
        if (e.layerDirty) {
            setText('form-error', 'Konversi kembali layer terpilih sebelum menyimpan.');
            show('form-error', true);
            return false;
        }
        d = { code: val('code'), name: val('name'), land: numberValue(val('land')), hasArt: !!(e.record && e.record.hasArt), artW: e.record ? e.record.artW : null, artH: e.record ? e.record.artH : null, artRev: e.record ? e.record.artRev : 0 };
        if (e.art) {
            changes.push({ bucket: 'pattern_art', id: id, mode: 'set', data: { svg: e.art.svg, preview: '', draft: e.art.draft } });
            d.hasArt = true;
            d.artW = e.art.w;
            d.artH = e.art.h;
            d.artRev = (new Date()).getTime();
        }
        else if (e.removeArt) {
            changes.push({ bucket: 'pattern_art', id: id, mode: 'delete' });
            d.hasArt = false;
            d.artW = null;
            d.artH = null;
            d.artRev = (new Date()).getTime();
        }
        changes.push({ bucket: 'patterns', id: id, mode: 'set', data: d });
    }
    else if (e.kind === 'container') {
        var spacers = readSpacers();
        d = { code: val('code'), serial:val('serial'), od: numberValue(val('od')), sw: numberValue(val('sw')), spacers: [] };
        for (i = 0; i < spacers.length; i++)
            if (trim(spacers[i].size) || trim(spacers[i].od))
                d.spacers.push({ size: numberValue(spacers[i].size), od: numberValue(spacers[i].od) });
        changes.push({ bucket: 'containers', id: id, mode: 'set', data: d });
    }
    else {
        d = { code: val('code'), name: val('name'), img: e.image || '' };
        changes.push({ bucket: 'stickers', id: id, mode: 'set', data: d });
    } if(e.record&&e.bucket!=='molds'&&e.kind!=='status')for(i=0;i<changes.length;i++)if(changes[i].data&&changes[i].bucket===e.bucket)changes[i].data.status=e.record.status||'active'; if (e.record && e.record.sample)
        for (i = 0; i < changes.length; i++)
            if (changes[i].data)
                changes[i].data.sample = true; submitChanges(changes, e.revision); return false; }
    function confirmDelete(bucket,record){if(!canEdit()||S.saving)return;S.editing={kind:'delete',bucket:bucket,record:record,readonly:false,revision:S.catalog.revision,previousFocus:document.activeElement};clear(el('edit-fields'));el('edit-fields').appendChild(make('h3','fieldset-title',recordIdentity(record,bucket)));el('edit-fields').appendChild(make('p','form-hint','Yakin ingin menghapus data ini dari daftar? Riwayat tetap disimpan. Data yang masih menjadi rujukan data lain tidak dapat dihapus.'));openModal('Konfirmasi hapus',false);setText('form-save','Ya, hapus');el('form-cancel').focus();}
    function deleteRecord(){if(S.editing)confirmDelete(S.editing.bucket,S.editing.record);}
    function closeModal() { if (S.saving || S.assetBusy) {
        toast('Tunggu proses selesai.');
        return;
    } var previous = S.editing ? S.editing.previousFocus : null; S.editing = null; show('modal', false); show('modal-shade', false); if (previous && previous.focus)
        try {
            previous.focus();
        }
        catch (e) { } }
    function excelError(message) { setText('excel-error', message); show('excel-error', true); }
    function excelUploaded(error, result) { if (error) {
        excelError(error);
        setText('excel-upload-status', 'Unggahan gagal.');
        return;
    } S.excelDraft = result.draft; S.sheets = result.sheets; S.excelPlan = null; show('excel-error', false); setText('excel-upload-status', 'File dibaca. Pilih sheet dan sesuaikan kolom; data belum diimpor.'); var select = el('excel-sheet'); clear(select); for (var i = 0; i < S.sheets.length; i++) {
        var o = make('option', '', S.sheets[i].name);
        o.value = String(i);
        select.appendChild(o);
    } el('excel-header').value = '1'; show('excel-mapper', true); buildMapping(); }
    function normalized(v) { return lower(v).replace(/[^a-z0-9]/g, ''); }
    function buildMapping() { if (!S.sheets.length)
        return; var index = parseInt(el('excel-sheet').value, 10) || 0, row = Math.max(0, (parseInt(el('excel-header').value, 10) || 1) - 1), headers = S.sheets[index].rows[row] || [], bucket = el('excel-bucket').value, fields = S.excelFields[bucket], root = el('excel-mapping'); clear(root); S.excelPlan = null; el('excel-commit').disabled = true; setText('excel-preview-result', ''); var aliases = { category:['kategori','category'], spec: ['kodespek', 'spek'], size: ['size', 'ukuran'], pattern: ['pattern', 'kodepattern'], serial: ['nomor', 'nomorcetakan'], owner: ['pemilik', 'pemilikcetakan'], brand1: ['merek'], insert1: ['insertplug'], sticker1: ['sticker', 'kodesticker'] }; for (var i = 0; i < fields.length; i++) {
        var label = make('label', 'mapping-row', fields[i][1] + ' ← kolom Excel'), n = make('select');
        n.id = 'map-' + fields[i][0];
        var op = make('option', '', 'Tidak diimpor');
        op.value = '-1';
        n.appendChild(op);
        var chosen = -1;
        for (var j = 0; j < headers.length; j++) {
            op = make('option', '', (j + 1) + '. ' + String(headers[j] || '(kosong)'));
            op.value = String(j);
            n.appendChild(op);
            var norm = normalized(headers[j]);
            if (norm === normalized(fields[i][1]))
                chosen = j;
            else if (chosen < 0 && aliases[fields[i][0]])
                for (var a = 0; a < aliases[fields[i][0]].length; a++)
                    if (norm === aliases[fields[i][0]][a])
                        chosen = j;
        }
        n.value = String(chosen);
        n.onchange = function () { S.excelPlan = null; el('excel-commit').disabled = true; };
        label.htmlFor = n.id;
        label.appendChild(n);
        root.appendChild(label);
    } }
    function previewImport() { if (!canEdit() || !S.excelDraft)
        return; var bucket = el('excel-bucket').value, fields = S.excelFields[bucket], mapping = {}; for (var i = 0; i < fields.length; i++)
        mapping[fields[i][0]] = parseInt(el('map-' + fields[i][0]).value, 10); el('excel-preview').disabled = true; show('excel-error', false); api('/api/catalog-excel', 'POST', { mode: 'preview', draft: S.excelDraft, bucket: bucket, sheet: S.sheets[parseInt(el('excel-sheet').value, 10) || 0].name, headerRow: Math.max(0, (parseInt(el('excel-header').value, 10) || 1) - 1), mapping: mapping }, function (err, result) { el('excel-preview').disabled = false; if (err) {
        excelError(err.message);
        return;
    } var root = el('excel-preview-result'); clear(root); if (result.errors.length) {
        var box = make('div', 'excel-errors');
        box.appendChild(make('strong', '', 'Belum ada data yang diimpor. Perbaiki kesalahan berikut:'));
        for (var i = 0; i < result.errors.length && i < 25; i++)
            box.appendChild(make('p', '', result.errors[i]));
        root.appendChild(box);
        S.excelPlan = null;
        el('excel-commit').disabled = true;
        return;
    } S.excelPlan = result.plan; var ok = make('div', 'import-preview'); ok.appendChild(make('strong', '', result.stats.added + ' data baru · ' + result.stats.updated + ' data diperbarui')); for (i = 0; i < result.preview.length; i++)
        ok.appendChild(make('p', '', 'Baris ' + result.preview[i].row + ': ' + result.preview[i].action + ' ' + result.preview[i].label)); ok.appendChild(make('p', '', 'Data belum ditulis. Klik Konfirmasi impor jika pemetaan sudah benar.')); root.appendChild(ok); el('excel-commit').disabled = false; }); }
    function commitImport() { if (!S.excelPlan || !canEdit())
        return; el('excel-commit').disabled = true; api('/api/catalog-excel', 'POST', { mode: 'commit', plan: S.excelPlan }, function (err, d) { if (err) {
        excelError(err.message);
        return;
    } toast('Impor selesai. Data dan riwayat tersimpan.'); S.excelPlan = null; setText('excel-preview-result', 'Impor berhasil. Muat file kembali jika ingin mengimpor data lain.'); connect(false); }); }
    function bind() {el('viewer-close').onclick=closeImageViewer;el('viewer-in').onclick=function(){zoomImage(1.25);};el('viewer-out').onclick=function(){zoomImage(.8);};el('viewer-reset').onclick=function(){S.viewerZoom=1;zoomImage(1);};el('viewer-max').onclick=function(){var full=el('image-viewer').className.indexOf('viewer-full')<0;el('image-viewer').className=full?'image-viewer viewer-full':'image-viewer';setText('viewer-max',full?'Pulihkan':'Maksimalkan');layoutImageViewer();};window.onresize=layoutImageViewer;var views=['patterns','stickers'];for(var vi=0;vi<views.length;vi++)(function(bucket){function setView(list){if(bucket==='patterns')S.patternList=list;var node=bucket==='patterns'?el('pattern-cards'):el('stickers-rows').parentNode;node.className=bucket==='patterns'?(list?'pattern-cards list-mode':'pattern-cards'):(list?'records':'records sticker-thumbnails');el(bucket+'-list').className=list?'chosen':'';el(bucket+'-thumb').className=list?'':'chosen';if(bucket==='patterns')renderPatterns();}el(bucket+'-list').onclick=function(){setView(true);};el(bucket+'-thumb').onclick=function(){setView(false);};})(views[vi]);var masterTabs=['patterns','containers','stickers'];for(var mt=0;mt<masterTabs.length;mt++)(function(bucket){el(bucket+'-status-filter').onchange=el(bucket+'-use-filter').onchange=function(){S.listPages=S.listPages||{};S.listPages[bucket]=1;renderAll();};el(bucket+'-filter-toggle').onclick=function(){var n=el(bucket+'-extra');n.style.display=n.style.display==='none'?'':'none';};el(bucket+'-reset').onclick=function(){el(bucket+'-status-filter').value='';el(bucket+'-use-filter').value='';el(bucket==='patterns'?'pattern-search':bucket+'-search').value='';S.listPages=S.listPages||{};S.listPages[bucket]=1;renderAll();};})(masterTabs[mt]);el('containers-each').onclick=function(){S.containerGrouped=false;el('containers-each').className='chosen';el('containers-set').className='';S.listPages=S.listPages||{};S.listPages.containers=1;renderMasters();};el('containers-set').onclick=function(){S.containerGrouped=true;el('containers-set').className='chosen';el('containers-each').className='';S.listPages=S.listPages||{};S.listPages.containers=1;renderMasters();}; el('records-per-page').onchange=function(){S.page=1;S.listPages={};renderAll();}; var tabs = ['molds', 'patterns', 'containers', 'stickers', 'excel', 'connection', 'history']; for (var i = 0; i < tabs.length; i++)
        el('nav-' + tabs[i]).onclick = (function (tab) { return function () { switchTab(tab); }; })(tabs[i]); el('flowlink').onclick = el('connection-detail').onclick = function () { switchTab('connection'); }; el('add-record').onclick = function () { if (!canEdit())
        return; if (S.tab === 'molds')
        openMold(null, false);
    else if (S.tab === 'patterns')
        openPattern(null, false);
    else
        openMaster(S.tab, null, false); }; el('computer').onchange = el('scenario').onchange = profileChange; el('retry').onclick = el('refresh-top').onclick = refresh; el('recover').onclick = function () { if (modalBusy())
        return; S.scenario = 'normal'; el('scenario').value = 'normal'; connect(true); }; el('mold-search').onkeyup = el('mold-search').oninput = function () { S.page = 1; renderMolds(); }; var fs = ['category', 'size', 'status', 'pattern', 'brand', 'owner', 'bladder', 'cure', 'mtype', 'container', 'role']; for (i = 0; i < fs.length; i++)
        el('filter-' + fs[i]).onchange = function () { S.page = 1; renderMolds(); }; el('filter-toggle').onclick = function () { show('extra-filters', el('extra-filters').style.display === 'none'); }; el('reset-filters').onclick = function () { el('mold-search').value = ''; for (var j = 0; j < fs.length; j++)
        el('filter-' + fs[j]).value = ''; S.page = 1; renderMolds(); }; el('pattern-search').onkeyup = el('pattern-search').oninput = function(){S.listPages=S.listPages||{};S.listPages.patterns=1;renderPatterns();}; el('containers-search').onkeyup = el('containers-search').oninput = el('stickers-search').onkeyup = el('stickers-search').oninput = function(){S.listPages=S.listPages||{};S.listPages[S.tab]=1;renderMasters();}; el('history-search').onkeyup = el('history-search').oninput = function(){S.listPages=S.listPages||{};S.listPages.history=1;renderHistory();}; el('view-each').onclick = function () { S.grouped = false; S.page = 1; renderMolds(); }; el('view-set').onclick = function () { S.grouped = true; S.page = 1; renderMolds(); }; el('form-cancel').onclick = el('modal-close').onclick = closeModal; el('edit-form').onsubmit = saveForm; el('excel-file').onchange = function () { nativeUpload(this, 'excel', excelUploaded); }; el('excel-sheet').onchange = el('excel-bucket').onchange = el('excel-header').onkeyup = buildMapping; el('excel-preview').onclick = previewImport; el('excel-commit').onclick = commitImport; document.onkeydown = function (e) { e = e || window.event;if(S.printOpen&&(e.keyCode||e.which)===27){closePrintReport();return;} if(el('image-viewer').style.display!=='none'&&(e.keyCode||e.which)===27){closeImageViewer();return;}if (S.editing && (e.keyCode || e.which) === 27) {
        closeModal();
        return false;
    } }; }
    function background() { if (modalBusy() || S.busy || !S.connected)
        return; var ticket = S.request; api('/api/catalog', 'GET', null, function (err, data) { if (ticket !== S.request || modalBusy() || S.busy)
        return; if (err) {
        failed(err);
        return;
    } var changed=!S.catalog||S.catalog.revision!==data.revision;S.checked=utcStamp();if(!changed){updateStatus();updateTimes();return;}applyCatalog(data);api('/api/events', 'GET', null, function (err, events) { if (ticket !== S.request || modalBusy() || S.busy)
        return; if (err) {
        failed(err);
        return;
    } S.events = events.rows; renderFilters(); renderAll(); }); }); }

    function loadFileCatalog(){try{if(!window.DELIMOLD_DATA)throw new Error('../Database/catalog.js belum terbaca.');applyCatalog(window.DELIMOLD_DATA);S.events=window.DELIMOLD_DATA.events||[];S.checked=window.DELIMOLD_DATA.updatedAt||utcStamp();S.connected=true;S.busy=false;S.pc='Buka penghubung untuk identitas Windows';S.cloudUser='Viewer file · identitas belum diverifikasi';S.identity={canWrite:false,role:'Read-only',account:'Identitas belum diverifikasi'};renderFilters();renderAll();}catch(e){failed({code:'DATABASE_UNAVAILABLE',message:e.message});}}
    function reloadFileCatalog(){if(modalBusy())return;window.DELIMOLD_DATA=null;var old=el('file-catalog-script');if(old)old.parentNode.removeChild(old);var script=make('script');script.id='file-catalog-script';script.type='text/javascript';var done=false;function finish(){if(done)return;done=true;window.clearTimeout(timer);loadFileCatalog();}script.onload=finish;script.onreadystatechange=function(){if(this.readyState==='loaded'||this.readyState==='complete')finish();};script.onerror=finish;var timer=window.setTimeout(finish,10000);script.src='../Database/catalog.js?revision='+(new Date()).getTime();document.getElementsByTagName('head')[0].appendChild(script);}
    window.onbeforeprint=function(){if(!S.printOpen)openPrintReport();};
    if (document.readyState === 'complete')
        init();
    else
        window.onload = init;
})();
