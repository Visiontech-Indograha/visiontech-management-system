(() => {
  const V=VT,U=VTUI,app=document.querySelector('#app'),dialog=document.querySelector('#dialog');
  V.launchDevice='desktop'; V.busy=false; V.dirty=false;
  V.actionNames={CREATE_PLAN:'Membuat draft',EDIT_DRAFT:'Menyunting draft',SAVE_DAY:'Menyimpan rincian',SAVE_ATTACHMENTS:'Memperbarui lampiran',PUBLISH:'Menerbitkan SK',ACCEPT:'Menerima SK',APPEAL:'Mengajukan banding',REVISE:'Membuka revisi',START:'Memulai pekerjaan',TOGGLE_TASK:'Memperbarui checklist',SAVE_REPORT:'Menyimpan laporan harian',SUBMIT_REPORT:'Mengirim laporan harian',REVIEW_REPORT:'Meninjau laporan harian',SAVE_WEEKLY:'Menyimpan laporan mingguan',SUBMIT_WEEKLY:'Mengirim laporan mingguan',REVIEW_WEEKLY:'Meninjau laporan mingguan',REQUEST_CHANGE:'Mengajukan perpanjangan',REQUEST_PERSONNEL_CHANGE:'Mengajukan adendum personel',WITHDRAW_CHANGE:'Menarik adendum personel',APPROVE_CHANGE:'Menyetujui perpanjangan',ACCEPT_CHANGE:'Menerima adendum',REJECT_CHANGE:'Menolak perubahan',REQUEST_COMPLETE:'Mengajukan selesai',APPROVE_COMPLETE:'Menutup pekerjaan',RETURN_COMPLETE:'Mengembalikan penyelesaian',CANCEL_PLAN:'Membatalkan pekerjaan',DELETE_PLAN:'Mengarsipkan draft',RESTORE_PLAN:'Memulihkan draft',RESERVE_ASSET:'Mengalokasikan aset',RELEASE_ASSET:'Melepas reservasi',RETURN_ASSET:'Mengajukan pengembalian',VERIFY_RETURN:'Memverifikasi pengembalian',CHECK_ASSET:'Pemeriksaan kendaraan',CHECK_IN:'Mencatat masuk',CHECK_OUT:'Mencatat keluar',EXPLAIN_ATTENDANCE:'Menjelaskan absensi',REVIEW_ATTENDANCE:'Meninjau absensi',UPLOAD_DOCUMENT:'Mengajukan dokumen',VERIFY_DOCUMENT:'Memverifikasi dokumen',PROMOTE:'Mengubah penempatan',OFFBOARD:'Menonaktifkan karyawan',UPDATE_EMPLOYEE:'Memperbarui profil',SET_DEMO_DATE:'Mengubah tanggal simulasi',SYNC_OFFLINE:'Sinkronisasi transaksi luring'};
  const labels={home:'Ringkasan',plans:'Work plan',approvals:'Persetujuan',timeline:'Timeline tim',people:'Karyawan',organization:'Organisasi',attendance:'Absensi',overtime:'Rekap lembur',assets:'Kendaraan & alat',audit:'Jejak aktivitas',profile:'Profil saya',more:'Menu lainnya',settings:'Panduan simulasi'};
  const menus={PM:['home','plans','approvals','timeline','people','assets','attendance','overtime','profile','audit'],LEADER:['home','plans','approvals','attendance','profile'],MEMBER:['home','plans','attendance','profile'],FINANCE:['home','approvals','attendance','overtime','profile'],HR:['home','people','approvals','organization','attendance','audit'],ASSET:['home','assets','approvals','plans','attendance','profile','audit'],OPS:['home','plans','approvals','timeline','organization','people','attendance','overtime','assets','profile','audit']};
  V.menu=()=>menus[V.actor.role]||[];
  V.go=(...parts)=>{location.hash=U.href(...parts);};
  V.notify=(message,error=false)=>{clearTimeout(V.toastTimer);document.querySelector('#notifications').innerHTML=`<div class="toast ${error?'error':''}" role="${error?'alert':'status'}">${U.esc(message)}</div>`;V.toastTimer=setTimeout(()=>document.querySelector('#notifications').innerHTML='',7500);};
  V.dialog=(title,content,keepDirty=false)=>{dialog.innerHTML=`<header class="dialog-head"><h2 id="dialog-title">${U.esc(title)}</h2>${U.button(keepDirty?'stay-page':'close-dialog','Tutup',{},'small')}</header><div class="dialog-body"><div class="dialog-error" role="alert"></div>${content}</div>`;if(!dialog.open)dialog.showModal();};
  V.closeDialog=(keepDirty=false)=>{dialog.close();if(!keepDirty)V.dirty=false;};
  V.uploadFiles=async(form)=>{const input=form.querySelector('input[type=file]');const files=Array.from(input?.files||[]);if(files.length>10)throw Error('Maksimal 10 lampiran per pengajuan.');const result=[];for(const file of files)result.push(await VTStorage.put(file));return result;};
  V.run=(type,payload={})=>{
    const next=V.D.transition(V.state,V.actor,type,payload);
    if(next.error){V.notify(next.error,true);const error=dialog.open?dialog.querySelector('.dialog-error'):document.querySelector('#page-error');if(error)error.innerHTML=U.note(next.error,'error');return false;}
    V.offline?.enqueue(next.state,type,payload);
    try {VTStorage.save(next.state,V.state.revision);}catch(error){V.notify(error.message,true);return false;}
    V.state=next.state;V.dirty=false;const y=scrollY;V.render();window.scrollTo(0,y);V.notify(V.offline?V.offline.message(type,next.message):next.message);return true;
  };
  V.queue=()=>{
    const q=[];
    for(const p of V.work.plans()){
      const manage=V.work.canManage(p),lead=V.work.leader(p)||(p.change?.type==='PERSONNEL'&&p.change.status==='AWAITING_LEADER_ACCEPTANCE'&&p.change.leaderId===V.actor.id);
      const add=(title,detail,tab='overview')=>q.push({title,detail,path:['plan',p.id,tab]});
      if(lead&&p.status==='PUBLISHED')q.push({title:'Surat tugas untuk diterima',detail:p.title,path:['document',p.id,p.documents.at(-1).id]});
      if(manage&&p.status==='APPEALED')add('Banding ketua tim',p.title);
      if(manage&&p.change?.status==='PENDING_PM')add('Usulan perpanjangan',p.title);
      if(lead&&p.change?.status==='AWAITING_LEADER_ACCEPTANCE')q.push({title:'Adendum untuk diterima',detail:p.title,path:['document',p.id,p.documents.at(-1).id]});
      if(manage) p.days.filter(d=>d.reportStatus==='SUBMITTED').forEach(d=>add('Review laporan harian',p.title+' · '+U.date(d.date),'days'));
      if(lead) p.days.filter(d=>d.reportStatus==='CHANGES_REQUESTED').forEach(d=>add('Perbaikan laporan harian',p.title+' · '+U.date(d.date),'days'));
      if(manage&&p.weeks) p.weeks.filter(w=>w.status==='SUBMITTED').forEach(w=>add('Review laporan mingguan',p.title+' · '+w.name,'days'));
      if(lead&&p.weeks) p.weeks.filter(w=>w.status==='CHANGES_REQUESTED').forEach(w=>add('Perbaikan laporan mingguan',p.title+' · '+w.name,'days'));
      if(manage&&p.status==='COMPLETION_REVIEW')add('Review laporan akhir penyelesaian',p.title,'days');
    }
    if(V.actor.role==='FINANCE') V.state.attendance.filter(a=>a.status==='NEEDS_REVIEW').forEach(a=>q.push({title:'Review absensi',detail:U.person(a.employeeId)+' · '+U.date(a.date),path:['attendance']}));
    if(V.actor.role==='ASSET') V.state.assets.filter(a=>a.status==='RETURN_PENDING').forEach(a=>q.push({title:'Periksa pengembalian aset',detail:a.name,path:['assets']}));
    if(V.actor.role==='HR') V.state.employees.forEach(e=>e.documents.filter(d=>d.status==='PENDING').forEach(d=>q.push({title:'Verifikasi '+d.type,detail:e.name,path:['employee-document',e.id,d.id]})));
    const visible=new Set(V.work.plans().map(p=>p.id));
    V.state.incident_reports.filter(i=>i.status==='OPEN'&&visible.has(i.planId)).forEach(i=>{
      if(V.D.can(V.actor,'RESOLVE_INCIDENT',V.work.get(i.planId)?.unit)&&(V.actor.role!=='ASSET'||i.category==='ASET'))
        q.push({title:'Insiden / HSE: '+i.category,detail:U.person(i.employeeId)+' · '+i.description.slice(0,60),path:['plan',i.planId,'overview']});
    });
    V.state.overtime_logs.filter(o=>o.status==='PENDING_PM'&&visible.has(o.planId)).forEach(o=>{
      if(V.D.can(V.actor,'REVIEW_OVERTIME',V.work.get(o.planId)?.unit)&&o.employeeId!==V.actor.id)
        q.push({title:'Persetujuan lembur',detail:U.person(o.employeeId)+' · '+o.hours+' jam',path:V.menu().includes('overtime')?['overtime']:['plan',o.planId,'overview']});
    });
      
      const now = new Date();
      const today = V.state.demoDate || (V.D && V.D.DEMO_TODAY) || now.toISOString().slice(0, 10);
      const att = V.state.attendance.find(a => a.employeeId === V.actor.id && a.date === today && a.status !== 'REJECTED');
      
      if (!att && (now.getHours() > 7 || (now.getHours() === 7 && now.getMinutes() >= 45))) {
        q.unshift({title:'Peringatan Absensi',detail:'Segera catat masuk (check-in) sebelum jam 08:00.',path:['attendance']});
      }
      if (att && !att.checkOut && (now.getHours() > 17 || (now.getHours() === 17 && now.getMinutes() >= 15))) {
        q.unshift({title:'Peringatan Absensi',detail:'Sudah melewati jam pulang. Segera catat keluar (check-out).',path:['attendance']});
      }

      return q;
  };
  function launcher(){
    const descriptions={PM:'Rencanakan pekerjaan, terbitkan SK, dan tinjau hasil tim.',LEADER:'Terima penugasan, laporkan progres, dan selesaikan pekerjaan.',MEMBER:'Lihat penugasan, catat kehadiran, dan kelola dokumen sendiri.',FINANCE:'Tinjau absensi dan penjelasan kehadiran karyawan.',HR:'Kelola profil, verifikasi dokumen, dan riwayat penempatan.',ASSET:'Kelola reservasi serta pemeriksaan pengembalian aset.',OPS:'Pantau pekerjaan, organisasi, dan sumber daya lintas unit.'};
    return `<main class="launcher" id="content" tabindex="-1"><div class="launch-top">${brand()}<span class="badge green">HTML · CSS · JavaScript</span></div><div class="launch-intro"><div class="eyebrow">VISIONTECH OPERATIONAL WORKSPACE</div><h1>Satu operasional.<br>Ruang kerja sesuai peran.</h1><p>Pilih tampilan dan identitas untuk mencoba alur kerja. Setiap peran memiliki menu, tugas, dan kewenangannya sendiri.</p></div><fieldset class="device-choice"><legend>01 · Pilih tampilan</legend><label><input type="radio" name="device" value="desktop" ${V.launchDevice==='desktop'?'checked':''}>Desktop <small>· ruang kerja lengkap</small></label><label><input type="radio" name="device" value="mobile" ${V.launchDevice==='mobile'?'checked':''}>Mobile <small>· aktivitas di lapangan</small></label></fieldset><div class="section-head"><h2>02 · Masuk sebagai</h2><small>9 identitas · 7 peran</small></div><div class="grid three">${V.D.actors.map(a=>{const e=V.state.employees.find(e=>e.id===a.id),inactive=e?.status==='INACTIVE';return `<article class="card role-card">${U.avatar(a.name,true)}<div><div class="eyebrow">${U.esc(U.roles[a.role])}</div><h2>${U.esc(a.name)}</h2><small>${['HR','ASSET','OPS','FINANCE'].includes(a.role)?'Lintas unit':U.esc(U.unit(a.unit))}${['HR','ASSET'].includes(a.role)?' · peran simulasi':''}</small></div><p class="role-copy">${descriptions[a.role]}</p>${inactive?'<span class="badge red">Akun dinonaktifkan</span>':`<a class="btn primary" data-enter="${a.id}" href="#/${V.launchDevice}/${a.id}/home">Buka ruang kerja →</a>`}</article>`;}).join('')}</div><div class="spaced">${U.note('Seluruh data adalah simulasi. Perubahan tersimpan di browser ini dan dibagikan antarperan; berpindah peran tidak mereset data.')}</div><footer class="workspace-footer"><span>Visiontech Workspace · Prototipe native</span><span>Tidak memerlukan instalasi atau koneksi internet.</span></footer></main>`;
  }
  function brand(){return '<a class="brand" href="#/" aria-label="Kembali ke pemilih peran"><span class="brand-mark">v</span><span>visiontech<small>OPERATIONAL WORKSPACE</small></span></a>';}
  function navLink(key,mobile=false){const active=V.route.page===key||key==='plans'&&['plan','new','edit','document','report'].includes(V.route.page)||key==='people'&&['employee','employee-document'].includes(V.route.page);return `<a class="${active?'active':''}" href="${U.href(key)}"${active?' aria-current="page"':''}>${U.icon(key)}<span>${mobile&&key==='home'?'Beranda':mobile&&key==='approvals'?'Tindakan':U.esc(labels[key])}</span></a>`;}
  function shell(content){
    const menu=V.menu(),queue=V.queue(),role=U.roles[V.actor.role],scope=['OPS','HR','ASSET','FINANCE'].includes(V.actor.role)?'Lintas unit':U.unit(V.actor.unit);
    const footer=`<footer class="workspace-footer"><span>Visiontech · ${U.esc(role)}</span><a href="${U.href('settings')}">Panduan & tanggal simulasi</a></footer>`;
    const inner=`<main id="content" tabindex="-1"><div id="page-error" role="alert"></div>${content}${footer}</main>`;
    const warning=VTStorage.warning?`<div class="storage-warning" role="status">${U.esc(VTStorage.warning)}</div>`:'';
    if(V.route.device==='mobile'){
      const mobileItems=V.actor.role==='HR'?['home','people','approvals','more']:V.actor.role==='ASSET'?['home','assets','approvals','more']:V.actor.role==='FINANCE'?['home','attendance','approvals','more']:['home','plans','attendance','more'];
      return `<div class="mobile-surround"><div class="mobile-caption"><span>PRATINJAU MOBILE · ${U.esc(role)}</span><a href="#/">Ganti peran / perangkat ↗</a></div><div class="mobile-shell"><header class="mobile-header">${brand()}<a href="${U.href(menu.includes('profile')?'profile':'more')}" aria-label="Identitas aktif">${U.avatar(V.actor.name)}</a></header><div class="mobile-context"><span><strong>${U.esc(V.actor.name)}</strong> · ${U.esc(role)}</span><span>${U.date(V.state.demoDate)}</span></div>${warning}${inner}<nav class="mobile-nav" aria-label="Navigasi mobile">${mobileItems.map(k=>navLink(k,true)).join('')}</nav></div></div>`;
    }
    return `<aside class="side">${brand()}<div class="workspace-name"><strong>Visiontech Indograha</strong><small>${U.esc(scope)}</small></div><div class="nav-label">RUANG KERJA ANDA</div><nav aria-label="Navigasi desktop">${menu.map(k=>navLink(k)).join('')}</nav><div class="side-bottom"><div class="side-note"><span class="eyebrow">MODE SIMULASI</span><strong>Peran jelas. Proses terhubung.</strong><p>Data tersimpan di browser ini.</p><a href="${U.href('settings')}">Panduan simulasi ↗</a></div><a class="side-user" href="#/">${U.avatar(V.actor.name)}<span><strong>${U.esc(V.actor.name)}</strong><small>${U.esc(role)} · Ganti peran</small></span></a></div></aside><div class="desktop-shell"><header class="topbar"><div><span class="muted">Workspace ／ </span><strong>${U.esc(labels[V.route.page]||'Detail')}</strong></div><div class="actions"><span class="muted">${U.date(V.state.demoDate)}</span>${menu.includes('approvals')?U.link(['approvals'],queue.length+' perlu tindakan','small'):''}${U.avatar(V.actor.name)}</div></header><div class="context-strip"><span>● Simulasi · <strong>${U.esc(role)}</strong> · ${U.esc(scope)}</span><a href="#/">Ganti peran / perangkat →</a></div>${warning}${inner}</div>`;
  }
  function home(){
    const role=V.actor.role,items=V.work.plans(),queue=V.queue();
    const copy={PM:['Rencana terarah.','Tim bergerak bersama.','Susun penugasan, tinjau laporan, dan pastikan setiap tahap terselesaikan.'],LEADER:['Pekerjaan hari ini.','Semua dalam kendali.','Tinjau surat tugas, selesaikan checklist, dan laporkan hasil tim Anda.'],MEMBER:['Siap bekerja.','Tetap terhubung.','Lihat penugasan Anda, catat kehadiran, dan kelola dokumen pribadi.'],FINANCE:['Kehadiran tercatat.','Keputusan lebih jelas.','Tinjau pengecualian absensi dengan penjelasan dan bukti yang tersedia.'],HR:['Data yang tertata.','Tim yang siap bekerja.','Jaga kelengkapan dokumen, masa berlaku, dan riwayat penempatan karyawan.'],ASSET:['Aset terpantau.','Pekerjaan tetap berjalan.','Alokasikan sumber daya dan periksa setiap pengembalian secara independen.'],OPS:['Lihat keseluruhan.','Jaga arah operasional.','Pantau koordinasi unit, penugasan tim, dan tindak lanjut operasional.']}[role];
    const destination=role==='HR'?['people']:role==='ASSET'?['assets']:role==='FINANCE'?['attendance']:['plans'];
    let stats;
    if(role==='HR')stats=[['Karyawan aktif',V.state.employees.filter(e=>e.status==='ACTIVE').length,'Dari 33 karyawan'],['Dokumen menunggu',queue.length,'Perlu verifikasi'],['Mendekati kedaluwarsa',V.state.employees.flatMap(e=>e.documents).filter(d=>d.lifecycle==='CURRENT'&&d.expiry&&d.expiry<=new Date(new Date(V.state.demoDate).getTime()+30*86400000).toISOString().slice(0,10)).length,'30 hari mendatang / lewat'],['Unit organisasi',V.D.units.length,'Struktur organisasi']];
    else if(role==='ASSET')stats=[['Aset tersedia',V.state.assets.filter(a=>a.status==='AVAILABLE').length,'Siap dialokasikan'],['Dalam pemakaian',V.state.assets.filter(a=>a.status==='IN_USE').length,'Pada pekerjaan aktif'],['Perlu diperiksa',queue.length,'Pengembalian aset'],['Total inventaris',V.state.assets.length,'Kendaraan dan alat']];
    else if(role==='FINANCE')stats=[['Catatan kehadiran',V.state.attendance.length,'Seluruh unit'],['Perlu review',queue.length,'Di luar radius'],['Sudah disetujui',V.state.attendance.filter(a=>a.status==='APPROVED').length,'Review manual'],['Sumber mesin',V.state.attendance.filter(a=>a.source==='MACHINE').length,'Data contoh mesin']];
    else stats=[['Work plan aktif',items.filter(p=>['ACCEPTED','IN_PROGRESS','COMPLETION_REVIEW'].includes(p.status)).length,'Persiapan & pelaksanaan'],['Menunggu tindakan',queue.length,'Sesuai peran Anda'],['Laporan perlu review',items.flatMap(p=>p.days).filter(d=>d.reportStatus==='SUBMITTED').length,'Sudah diserahkan'],['Pekerjaan selesai',items.filter(p=>p.status==='COMPLETED').length,'Dalam lingkup Anda']];
    const personal=V.actor.role==='MEMBER'?U.panel('Kebutuhan pribadi',U.row('Absensi hari ini','Catat masuk, keluar, dan penjelasan.',U.link(['attendance'],'Buka','small'))+U.row('Dokumen pribadi','Periksa kelengkapan serta masa berlaku.',U.link(['profile'],'Lihat','small'))):'';
    
    let financeExpiringHtml = '';
    let financeOvertimeHtml = '';
    if (V.actor.role === 'FINANCE') {
      const in7Days = new Date(new Date(V.state.demoDate).getTime() + 7 * 86400000).toISOString().slice(0, 10);
      const expiring = V.state.employees.flatMap(e => e.documents.filter(d => d.lifecycle === 'CURRENT' && d.expiry && d.expiry <= in7Days).map(d => ({...d, e})));
      if (expiring.length) financeExpiringHtml = U.panel('Dokumen Mendekati Kedaluwarsa', expiring.map(d => U.row(U.person(d.e.id), `${d.type} · Berlaku s.d. ${U.date(d.expiry)}`, U.badge(d.expiry <= V.state.demoDate ? 'Kedaluwarsa' : 'Kedaluwarsa < 7 Hari', d.expiry <= V.state.demoDate ? 'danger' : 'warning'))).join(''));
      
      const overtimes = V.state.overtime_logs.filter(o => o.status === 'APPROVED');
      if (overtimes.length) financeOvertimeHtml = U.panel('Rekap Lembur (Disetujui)', overtimes.map(o => U.row(U.person(o.employeeId), `${o.hours} jam · ${U.date(o.date)} · ${U.esc(o.reason)}`, U.badge(o.status))).join(''));
    }
    
    return U.heading('Halo, '+V.actor.name.split(' ')[0]+'.','Semua yang perlu Anda tangani, sesuai peran Anda.',V.D.can(V.actor,'CREATE_PLAN')?U.link(['new'],'+ Buat work plan','primary'):'','SELAMAT DATANG KEMBALI')+`<section class="hero"><div><div class="eyebrow">${U.esc(U.roles[role])}</div><h2>${copy[0]}<br>${copy[1]}</h2><p>${copy[2]}</p>${U.link(destination,'Buka ruang kerja →')}</div><div class="hero-art" aria-hidden="true"><span>✦</span><strong>Terhubung<br>dalam satu alur.</strong><i></i><i></i><i></i></div></section><div class="stats">${stats.map(([title,n,desc])=>`<article class="card stat"><span>${title}</span><strong>${String(n).padStart(2,'0')}</strong><small>${desc}</small></article>`).join('')}</div><div class="columns"><div class="stack">${!['HR','ASSET','FINANCE'].includes(role) && items.length?`<div><div class="section-head"><h2>Penugasan pilihan</h2><a href="${U.href('plans')}">Lihat semua →</a></div><div class="grid">${items.slice(0,4).map(V.work.card).join('')}</div></div>`:U.panel('Fokus ruang kerja',U.row(copy[0],copy[2],U.link(destination,'Buka','primary')))}${personal}${financeExpiringHtml}${financeOvertimeHtml}</div><div class="stack">${U.panel('Perlu perhatian Anda',queue.length?queue.slice(0,5).map(q=>U.row(q.title,q.detail,U.link(q.path,'Tinjau','small'))).join(''):U.note('Tidak ada tindakan yang menunggu saat ini.','success'))}${U.panel('Identitas aktif',U.row(V.actor.name,U.roles[role],'',V.actor.name)+U.dl([['Unit',U.esc(['HR','ASSET','OPS','FINANCE'].includes(role)?'Lintas unit':U.unit(V.actor.unit))],['Tampilan',V.route.device==='mobile'?'Mobile':'Desktop']])+U.link(['settings'],'Panduan simulasi'))}</div></div>`;
  }
  function approvals(){const items=V.queue();return U.heading('Persetujuan & tindak lanjut','Hanya tugas yang memerlukan tindakan peran Anda.')+(items.length?U.panel('Antrean Anda',items.map(q=>U.row(q.title,q.detail,U.link(q.path,'Tinjau','primary'))).join('')):U.empty('Semua sudah tertangani','Belum ada permintaan baru untuk peran Anda.'));}
  function more(){return U.heading('Menu ruang kerja',V.actor.name+' · '+U.roles[V.actor.role])+U.panel('Navigasi peran',V.menu().map(k=>U.row(labels[k],'',U.link([k],'Buka','small'))).join('')+U.row('Panduan & pengaturan','Tanggal simulasi dan reset.',U.link(['settings'],'Buka','small')))+`<div class="spaced"><a class="btn" href="#/">Ganti peran / perangkat</a></div>`;}
  function settings(){return U.heading('Panduan simulasi','Data dan alur yang sama dapat dicoba dari beberapa peran.')+`<div class="columns"><div class="stack">${U.panel('Cara mencoba alur',`<ol><li>PM menyiapkan draft, rincian harian, dan aset; lalu menerbitkan SK.</li><li>Kembali ke pemilih peran. Ketua menerima SK atau mengajukan banding.</li><li>Majukan tanggal simulasi bila perlu, lalu mulai pekerjaan dan lengkapi checklist, laporan, serta lampiran.</li><li>PM meninjau laporan. Perpanjangan memerlukan persetujuan PM dan penerimaan adendum oleh ketua.</li><li>Ketua mengajukan pengembalian; petugas aset memverifikasi.</li><li>Ketua mengajukan selesai; PM menutup setelah seluruh syarat terpenuhi.</li></ol>`)}${U.panel('Dokumen dan lampiran','<p>Pratinjau SK/adendum tersedia pada tab Dokumen pekerjaan. Pilih versi untuk melihat isi saat penerbitan. Laporan memiliki pratinjau sendiri. Gunakan Cetak / Simpan PDF untuk mencetak A4.</p><p>Gambar dan PDF yang diunggah disimpan di browser ini. Untuk mencoba tanpa berkas, formulir laporan/dokumen pribadi menyediakan lampiran contoh yang ditandai sebagai simulasi.</p>')}${U.panel('Peran pendukung','<p>Rusyidi dapat mengajukan dokumen pribadi dan menjelaskan absensi. HR memverifikasi dokumen secara independen. Finance meninjau absensi. Hernita memeriksa pengembalian aset.</p><p>Promosi dan offboarding tersedia pada profil karyawan bagi HR/Operational Manager. Penugasan aktif dan serah terima kewenangan diperiksa terlebih dahulu.</p>')}</div><div class="stack">${U.panel('Tanggal simulasi',U.form('date',U.input('date','Tanggal simulasi',V.state.demoDate,'date','required'),'Simpan tanggal'))}${U.panel('Jaringan (simulasi luring)',U.note(V.offline?.simulated?'Mode luring sedang disimulasikan. Absensi dan laporan masuk antrean lokal sampai jaringan dipulihkan.':'Aktifkan untuk mencoba penyimpanan luring. Absensi dan laporan tetap tersimpan di perangkat dan masuk antrean sinkronisasi.')+U.dl([['Status',V.offline?.online?'Online':'Luring'],['Antrean belum tersinkron',String(V.offline?.pending||0)]])+'<div class="spaced">'+U.button('toggle-offline',V.offline?.simulated?'Pulihkan jaringan & sinkronkan':'Simulasikan jaringan terputus',{},V.offline?.simulated?'primary':'')+'</div>')}${U.panel('Mulai kembali',U.note('Reset menghapus transaksi dan lampiran prototipe dari browser ini, lalu mengembalikan data awal.')+'<div class="spaced">'+U.button('reset','Reset simulasi',{},'danger')+'</div>')}${U.panel('Batas simulasi','<p>Peran adalah identitas demo, bukan login nyata. Tidak ada API, database server, biometrik, atau mesin absensi yang terhubung. GPS dan kamera perangkat hanya dipakai bila diizinkan; koordinat lokasi proyek adalah data simulasi. Tanda tangan dan QR resmi tidak diterbitkan.</p><p>Penyimpanan melekat pada browser dan lokasi file yang sama. Salinan folder atau browser lain memulai data tersendiri.</p>')}</div></div>`;}
  V.views.home=home;V.views.approvals=approvals;V.views.more=more;V.views.settings=settings;
  function allowed(page){
    if(page==='presentation')return V.actor.role!=='ASSET';
    if(['home','more','settings'].includes(page))return true;
    if(['plan','document','report'].includes(page))return V.menu().includes('plans');
    if(['new','edit'].includes(page))return ['PM','OPS'].includes(V.actor.role);
    if(['employee','employee-document'].includes(page))return V.menu().includes('people')||V.menu().includes('profile');
    return V.menu().includes(page);
  }
  V.render=()=>{
    V.documents.clearURLs();
    let bits;try{bits=location.hash.replace(/^#\/?/,'').split('/').map(decodeURIComponent);}catch{bits=[];}
    if(!['desktop','mobile'].includes(bits[0])||!V.D.actors.some(a=>a.id===bits[1])){V.actor=null;V.route={};app.innerHTML=launcher();document.title='Visiontech · Pilih ruang kerja';return;}
    V.route={device:bits[0],actorId:bits[1],page:bits[2]||'home',args:bits.slice(3)};
    V.actor=V.D.actors.find(a=>a.id===bits[1]);V.launchDevice=V.route.device;
    const employee=V.state.employees.find(e=>e.id===V.actor.id);
    if(employee?.status==='INACTIVE'){app.innerHTML=`<main id="content" class="error-panel">${U.empty('Akses akun dinonaktifkan','Karyawan ini sudah offboarding. Riwayat tetap tersedia untuk pengelola.','<a class="btn primary" href="#/">Kembali ke pemilih peran</a>')}</main>`;return;}
    let content;
    try{content=allowed(V.route.page)&&V.views[V.route.page]?V.views[V.route.page]():U.empty('Halaman tidak tersedia','Menu atau tindakan ini bukan bagian dari ruang kerja Anda.',U.link(['home'],'Kembali ke ringkasan'));}
    catch(error){console.error(error);content=U.empty('Halaman belum dapat dimuat','Data tidak dapat ditampilkan. Muat ulang atau kembali ke ringkasan.',U.link(['home'],'Kembali'));}
    app.innerHTML=shell(content);document.title=(labels[V.route.page]||'Detail')+' · '+V.actor.name+' · Visiontech';
    V.documents.afterRender();filter();
    document.querySelectorAll('form[data-form="plan"], form[data-form="personnel"]').forEach(f => V.updateConflicts(f));
  };
  function filter(){
    const query=(document.querySelector('[data-search]')?.value||'').toLowerCase(),status=document.querySelector('[data-filter]')?.value||'';
    const items=document.querySelectorAll('[data-search-item]');let visible=0;
    items.forEach(el=>{const text=el.dataset.searchItem||el.textContent.toLowerCase();const match=text.includes(query)&&(!el.dataset.status||(status?el.dataset.status===status:el.dataset.status!=='ARCHIVED'));el.classList.toggle('hidden',!match);if(match)visible++;});
    document.querySelector('#no-results')?.classList.toggle('hidden',visible>0);
  }
  V.forms.reason=async(form,data)=>{const type=data.action;delete data.action;if(V.run(type,data))V.closeDialog();};
  V.forms.extension=async(form,data)=>{if(V.run('REQUEST_CHANGE',{...data,type:'EXTEND'}))V.closeDialog();};
  V.forms.date=async(form,data)=>V.run('SET_DEMO_DATE',data);
  V.forms['reserve-asset']=async(form,data)=>{if(V.run('RESERVE_ASSET',data))V.closeDialog();};
  V.forms['return-asset']=async(form,data)=>{if(V.run('RETURN_ASSET',data))V.closeDialog();};
  V.forms['verify-return']=async(form,data)=>{if(V.run('VERIFY_RETURN',data))V.closeDialog();};
  V.forms['review-attendance']=async(form,data)=>{if(V.run('REVIEW_ATTENDANCE',data))V.closeDialog();};
  V.forms.incident=async(form,data)=>{const evidence=await V.uploadFiles(form);if(data.sample==='yes')evidence.push({id:'sample-evidence',name:'bukti-insiden-contoh.jpg',type:'image/jpeg'});if(V.run('REPORT_INCIDENT',{...data,evidence}))V.closeDialog();};
  V.forms['resolve-incident']=async(form,data)=>{if(V.run('RESOLVE_INCIDENT',data))V.closeDialog();};
  V.forms.overtime=async(form,data)=>{if(V.run('REPORT_OVERTIME',data))V.closeDialog();};
  V.forms['review-overtime']=async(form,data)=>{if(V.run('REVIEW_OVERTIME',data))V.closeDialog();};
  const uiActions={
    'close-dialog':()=>V.closeDialog(),
    reason:data=>V.dialog(V.actionNames[data.action]||'Konfirmasi',U.form('reason',U.textarea('reason','Alasan / catatan','','required minlength="3"'),'Konfirmasi',data)),
    extension:data=>{const p=V.work.get(data.planId);V.dialog('Ajukan perpanjangan',U.form('extension',U.note('Jadwal saat ini tetap berlaku sampai PM menyetujui dan Anda menerima adendum.')+'<div class="spaced">'+U.input('newEnd','Usulan tanggal selesai',p.endDate,'date','required')+U.textarea('reason','Alasan perpanjangan','','required')+'</div>','Kirim usulan',data));},
    attachment:data=>V.documents.openFile(data),
    print:()=>{if(document.querySelector('.document-paper'))window.print();},
    'remove-plan-file':data=>{const p=V.work.get(data.planId);V.run('SAVE_ATTACHMENTS',{planId:p.id,attachments:p.attachments.filter(f=>f.id!==data.fileId)});},
    'upload-employee':data=>V.dialog('Ajukan dokumen karyawan',U.form('upload-employee',U.select('type','Jenis dokumen',[['Sertifikat K3','Sertifikat K3'],['SIM A','SIM A'],['SIM C','SIM C'],['KTP','KTP'],['Sertifikat kompetensi','Sertifikat kompetensi'],['Kontrak kerja','Kontrak kerja']],data.type||'Sertifikat K3')+U.input('number','Nomor dokumen','','text','required')+U.input('expiry','Berlaku sampai (opsional)','','date')+U.upload('Berkas dokumen','files',false)+'<label class="check"><input type="checkbox" name="sample" value="yes">Gunakan lampiran contoh bila tidak memilih berkas</label>','Ajukan verifikasi',data)),
    'check-asset':data=>V.dialog('Pemeriksaan Kendaraan',U.form('check-asset',U.select('decision','Kelayakan Kendaraan',[['ACCEPT','Kendaraan layak jalan'],['REJECT','Ajukan banding (tidak layak)']],'ACCEPT')+U.textarea('reason','Alasan (Wajib diisi jika banding)',''),'Simpan Pemeriksaan',data)),
    'edit-employee':data=>{const e=V.people.get(data.employeeId);V.dialog('Sunting data karyawan',U.form('edit-employee',U.input('email','Email',e.email,'email','required')+U.input('phone','Telepon',e.phone)+U.textarea('address','Alamat',e.address||'')+U.input('birthDate','Tanggal lahir',e.birthDate||'','date')+U.input('joinDate','Tanggal masuk',e.joinDate,'date','required')+U.input('emergencyContact','Kontak darurat',e.emergencyContact||''),'Simpan data',data));},
    promote:data=>{const e=V.people.get(data.employeeId);V.dialog('Ubah penempatan',U.form('promote',U.input('position','Jabatan baru',e.position,'text','required')+U.select('unit','Unit penempatan',V.D.units.map(u=>[u.code,u.name]),e.unit)+U.note('Pemegang peran demo membutuhkan serah terima kewenangan. Mutasi lintas unit diperiksa terhadap penugasan aktif.'),'Simpan penempatan',data));},
    personnel:data=>{
      const p=V.work.get(data.planId); if(!p) return;
      const team=V.state.employees.filter(e=>e.status==='ACTIVE'&&e.unit===p.unit&&e.id!==p.pmId);
      const demo=id=>V.D.actors.some(a=>a.id===id)?' · identitas demo':'';
      const leaders=team.filter(e=>e.id!==p.pmId).map(e=>[e.id,e.name+' · '+e.position+demo(e.id)]);
      V.dialog('Adendum personel',U.note('Susunan baru berlaku setelah ketua tim menerima adendum. Jika ketua diganti, ketua barulah yang menerima; pada prototipe ini pilih orang bertanda "identitas demo" agar penerimaannya bisa dicoba.')+U.form('personnel',
        U.select('leaderId','Ketua tim',leaders,p.leaderId,'data-leader-select required')+
          `<h3>Anggota tim</h3><div class="grid">${team.map(e=>`<label class="check"><input type="checkbox" name="memberIds" value="${e.id}"${p.memberIds.includes(e.id)?' checked':''}${e.id===p.leaderId?' disabled':''}><span class="emp-name">${U.esc(e.name)}</span></label>`).join('')}</div>`+
        U.textarea('reason','Alasan perubahan personel','','required'),'Terbitkan adendum personel',{planId:p.id,rowVersion:p.rowVersion}));
        setTimeout(() => V.updateConflicts(document.querySelector('#dialog form')), 0);
      },
    'check-in':()=>V.geo.openCheckIn(),
    'check-out':data=>{
      if(!V.run('CHECK_OUT',data))return;
      const record=V.state.attendance.find(a=>a.id===data.attendanceId);
      if(record?.earlyLeave)V.notify(`Tercatat pulang lebih awal: keluar ${U.clock(record.checkOut)} WIB, batas 17.00 WIB.`,true);
    },
    'toggle-offline':()=>V.offline.setSimulated(!V.offline.simulated),
    'explain-attendance':data=>{const a=V.state.attendance.find(a=>a.id===data.attendanceId);V.dialog('Penjelasan absensi',U.form('explain-attendance',U.textarea('explanation','Penjelasan',a.explanation,'required'),'Kirim penjelasan',data));},
    'review-attendance':data=>{const a=V.state.attendance.find(a=>a.id===data.attendanceId);V.dialog('Tinjau absensi',U.dl([['Karyawan',U.esc(U.person(a.employeeId))],['Jarak',a.distance+' m'],['Penjelasan',U.esc(a.explanation||'Belum ada penjelasan')]])+U.form('review-attendance',U.select('decision','Keputusan',[['APPROVE','Setujui'],['REJECT','Tolak']],'APPROVE')+U.textarea('note','Catatan pemeriksaan','','required'),'Simpan keputusan',data));},
    'return-asset':data=>V.dialog('Ajukan pengembalian aset',U.form('return-asset',U.textarea('note','Catatan kondisi & kelengkapan','','required'),'Ajukan pengembalian',data)),
    'verify-return':data=>{const a=V.state.assets.find(a=>a.id===data.assetId);V.dialog('Verifikasi pengembalian',U.note('Pengaju: '+U.person(a.returnedBy)+'. Pemeriksa harus berbeda dari pengaju.')+U.form('verify-return',U.select('decision','Keputusan',[['APPROVE','Terima pengembalian'],['REJECT','Tolak (kembalikan ke Ketua)']],'APPROVE')+U.select('condition','Kondisi saat ini',[['Baik','Baik'],['Perlu perawatan','Perlu perawatan']],'Baik')+U.textarea('note','Catatan pemeriksaan','','required'),'Verifikasi kembali',data));},
    incident:data=>V.dialog('Lapor Insiden / HSE',U.form('incident',U.select('category','Kategori insiden',[['K3_RINGAN','K3 - Cedera Ringan/P3K'],['K3_BERAT','K3 - Cedera Berat/Medis'],['K3_LINGKUNGAN','K3 - Dampak Lingkungan'],['K3_HAMPIR','K3 - Hampir Celaka (Near Miss)'],['ASET','Kerusakan/kehilangan aset']],'K3_RINGAN')+U.select('severity','Tingkat keparahan',[['RENDAH','Rendah'],['SEDANG','Sedang'],['TINGGI','Tinggi'],['KRITIS','Kritis']],'RENDAH')+U.textarea('description','Uraian insiden','','required')+U.upload('Bukti foto/dokumen','files',false)+'<label class="check"><input type="checkbox" name="sample" value="yes">Gunakan bukti contoh</label>','Laporkan insiden',data)),
    'resolve-incident':data=>{const i=V.state.incident_reports.find(x=>x.id===data.incidentId);V.dialog('Selesaikan Insiden',U.form('resolve-incident',U.dl([['Pelapor',U.person(i.employeeId)],['Kategori',i.category],['Keparahan',i.severity],['Uraian',i.description]])+U.textarea('note','Catatan penyelesaian','','required'),'Selesaikan insiden',data));},
    overtime:data=>V.dialog('Ajukan Lembur',U.form('overtime',U.input('hours','Jam lembur (1-12)',2,'number','required min="1" max="12"')+U.textarea('reason','Alasan lembur','','required'),'Ajukan lembur',data)),
    'review-overtime':data=>{const o=V.state.overtime_logs.find(x=>x.id===data.overtimeId);V.dialog('Persetujuan Lembur',U.form('review-overtime',U.dl([['Karyawan',U.person(o.employeeId)],['Durasi',o.hours+' jam'],['Alasan',o.reason]])+U.select('decision','Keputusan',[['APPROVED','Setujui'],['REJECTED','Tolak']],'APPROVED')+U.textarea('note','Catatan (opsional)',''),'Simpan keputusan',data));},
    'reserve-asset':data=>{
      const items=V.work.plans().filter(p=>!['COMPLETED','CANCELLED'].includes(p.status));
      if(!items.length) { V.dialog('Alokasikan aset', U.note('Belum ada work plan yang bisa menerima alokasi.')); return; }
      V.dialog('Alokasikan aset', U.form('reserve-asset', U.select('planId','Work plan',items.map(p=>[p.id,p.title])),'Alokasikan',data));
      const asset=V.state.assets.find(a=>a.id===data.assetId);
      if(asset?.kind==='VEHICLE') setTimeout(()=>dialog.querySelector('[name=planId]')?.dispatchEvent(new Event('change',{bubbles:true})),0);
    },
    reset:()=>V.dialog('Reset seluruh simulasi?',U.note('Semua perubahan dan lampiran pada prototipe ini akan diganti dengan data awal. Tindakan ini tidak dapat dibatalkan.')+'<div class="actions spaced">'+U.button('close-dialog','Batal')+U.button('confirm-reset','Ya, reset data',{},'danger')+'</div>'),
    'confirm-reset':async()=>{V.state=await VTStorage.reset();V.closeDialog();location.hash='#/';V.render();V.notify('Data simulasi dikembalikan ke kondisi awal.');},
    'leave-page':data=>{V.dirty=false;V.closeDialog();location.hash=data.href;},
    'stay-page':()=>{V.closeDialog(true);}
  };
  V.updateConflicts = (form) => {
    if (!form) return;
    let start, end, currentId;
    // planId travels as a hidden input (U.form payload), not as a data attribute.
    const planId = form.querySelector('[name="planId"]')?.value || form.dataset.planId;
    if (form.dataset.form === 'plan') {
      start = form.startDate?.value; end = form.endDate?.value; currentId = planId;
    } else if (form.dataset.form === 'personnel') {
      const p = V.work.get(planId);
      start = p?.startDate; end = p?.endDate; currentId = p?.id;
    } else return;
    if (!start || !end) return;
    
    const activePlans = V.work.plans().filter(p => p.id !== currentId && !p.deletedAt && !['DRAFT','CANCELLED','COMPLETED'].includes(p.status));
    const overlapping = activePlans.filter(p => p.startDate <= end && p.endDate >= start);
    
    const leaderSelect = form.querySelector('[name="leaderId"]');
    const memberCheckboxes = form.querySelectorAll('[name="memberIds"]');
    const checkConflict = (empId) => overlapping.find(p => p.leaderId === empId || p.memberIds.includes(empId));
    
    if (leaderSelect) {
      Array.from(leaderSelect.options).forEach(opt => {
        const conflict = checkConflict(opt.value);
        if (conflict) {
          opt.disabled = true;
          if (!opt.dataset.orig) opt.dataset.orig = opt.textContent;
          opt.textContent = opt.dataset.orig + ' (Bertabrakan: ' + conflict.title + ')';
        } else {
          opt.disabled = false;
          if (opt.dataset.orig) opt.textContent = opt.dataset.orig;
        }
      });
    }
    
    memberCheckboxes.forEach(cb => {
      const conflict = checkConflict(cb.value);
      const span = cb.closest('label').querySelector('.emp-name');
      if (conflict) {
        cb.disabled = true;
        if (!cb.dataset.orig) cb.dataset.orig = span.textContent.trim();
        span.textContent = cb.dataset.orig + ' (Bertabrakan: ' + conflict.title + ')';
      } else {
        cb.disabled = cb.value === leaderSelect?.value;
        if (cb.dataset.orig) span.textContent = cb.dataset.orig;
      }
    });
  };
  document.addEventListener('click',async event=>{
    const button=event.target.closest('[data-ui],[data-command]'),anchor=event.target.closest('a');
    if(V.busy&&(button||anchor)){event.preventDefault();return;}
    if(anchor&&anchor.getAttribute('href')?.startsWith('#')){
      if(V.dirty){
        event.preventDefault();
        V.dialog('Tinggalkan Halaman', U.note('Perubahan formulir belum disimpan. Jika dilanjutkan, ketikan Anda akan hilang.') + '<div class="actions spaced">' + U.button('stay-page','Batal') + U.button('leave-page','Tinggalkan halaman',{href:anchor.getAttribute('href')},'danger') + '</div>', true);
        return;
      }
      V.dirty=false;
    }
    if(!button)return;
    try{
      if(button.hasAttribute('data-guard') && button.disabled) return;
      const data=JSON.parse(button.dataset.payload||'{}');
      if(button.dataset.command)V.run(button.dataset.command,data);
      else await uiActions[button.dataset.ui]?.(data);
    }catch(error){V.notify(error.message,true);}
  });
  document.addEventListener('submit',async event=>{
    const form=event.target.closest('form[data-form]');if(!form)return;event.preventDefault();if(V.busy)return;
    const handler=V.forms[form.dataset.form];if(!handler)return;
    const data={...form.dataset};
    for(const [k,v]of new FormData(form))if(!data[k]&&v.size!==0&&v!=='')data[k]=v;
    if(data.rowVersion!==undefined)data.rowVersion=Number(data.rowVersion);
    const action=event.submitter?.dataset?.action;
    V.busy=true;const submit=form.querySelector('[type=submit]');if(submit)submit.disabled=true;
    try{await handler(form,data,action);}catch(error){V.notify(error.message,true);const target=dialog.open?dialog.querySelector('.dialog-error'):document.querySelector('#page-error');if(target)target.innerHTML=U.note(error.message,'error');}
    finally{V.busy=false;if(submit?.isConnected)submit.disabled=false;}
  });
  document.addEventListener('input',event=>{if(event.target.matches('[data-search]'))filter();else if(event.target.closest('form'))V.dirty=true;});
  document.addEventListener('change',event=>{
    const el=event.target;
    if(el.name==='device'){V.launchDevice=el.value;document.querySelectorAll('[data-enter]').forEach(a=>a.href='#/'+el.value+'/'+a.dataset.enter+'/home');}
    if(el.matches('[data-filter]'))filter();
    if(el.matches('[data-version]')){location.hash=el.value;}
    if(el.matches('[data-zoom]'))V.documents.fit();
    if(el.matches('[data-leader-select]') || el.name === 'startDate' || el.name === 'endDate') {
      const form = el.closest('form');
      if (el.matches('[data-leader-select]')) form.querySelectorAll('[name=memberIds]').forEach(input=>{input.disabled=input.value===el.value;if(input.disabled)input.checked=false;});
      V.updateConflicts(form);
    }
    if((el.name==='planId' && el.closest('[data-form="reserve-asset"]')) || (el.name==='assetId' && el.closest('[data-form="reserve"]'))){
      const form=el.closest('form');
      const assetId=form.querySelector('[name=assetId]')?.value;
      const asset=V.state.assets.find(a=>a.id===assetId);
      let planId=form.querySelector('[name=planId]')?.value;
      if(asset?.kind==='VEHICLE'){
        const plan=V.state.plans.find(p=>p.id===planId);
        if(plan){
          const reqSim=asset.vehicleType==='MOTORCYCLE'?'SIM C':'SIM A';
          const ids=[plan.leaderId,...plan.memberIds];
          let html=`<label>Pengemudi kendaraan<select name="driverId" required><option value="">Pilih pengemudi (${reqSim})</option>`;
          for(const id of ids){
            const emp=V.state.employees.find(e=>e.id===id);
            if(!emp) continue;
            const sim=emp.documents.find(d=>d.type===reqSim&&d.lifecycle==='CURRENT');
            const exp=sim&&sim.expiry?new Date(sim.expiry):null;
            const planEnd=new Date(plan.endDate);
            let ok=sim&&(!exp||exp>=planEnd);
            let reason=sim?(ok?`Berlaku s.d. ${sim.expiry||'Seumur Hidup'}`:`Kedaluwarsa ${sim.expiry}`):`Tidak ada ${reqSim}`;
            html+=`<option value="${id}" ${ok?'':'disabled'}>${U.esc(emp.name)} (${reason})</option>`;
          }
          html+=`</select></label>`;
          let cont=form.querySelector('#driver-select-container');
          if(!cont){cont=document.createElement('div');cont.id='driver-select-container';el.closest('label').after(cont);}
          cont.innerHTML=html;
        }
      } else {
        const cont=form.querySelector('#driver-select-container');
        if(cont) cont.innerHTML='';
      }
    }
    if(el.matches('[data-task]')){
      const payload = {planId:el.dataset.plan,dayId:el.dataset.day,taskId:el.dataset.task};
      const currentForm = document.querySelector(`form[data-form="report"] input[name="dayId"][value="${el.dataset.day}"]`)?.closest('form');
      const formsState = {};
      const plan = V.state.plans.find(p => p.id === payload.planId);
      document.querySelectorAll('form[data-form="report"]').forEach(f => {
        if (f !== currentForm) {
          const d = f.querySelector('input[name="dayId"]')?.value;
          if (d && plan) {
            const day = plan.days.find(x => x.id === d);
            if (day) {
               const t = f.querySelector('[name="text"]')?.value || '';
               const o = f.querySelector('[name="obstacleText"]')?.value || '';
               if (t !== (day.reportText||'') || o !== (day.obstacleText||'')) {
                  formsState[d] = { text: t, obstacleText: o };
               }
            }
          }
        }
      });
      if (currentForm) {
        const data = Object.fromEntries(new FormData(currentForm).entries());
        payload.text = data.text;
        payload.obstacleText = data.obstacleText;
      }
      V.dirty=false;
      V.run('TOGGLE_TASK', payload);
      for (const [d, vals] of Object.entries(formsState)) {
         const f = document.querySelector(`form[data-form="report"] input[name="dayId"][value="${d}"]`)?.closest('form');
         if (f) {
            if (vals.text !== undefined && f.querySelector('[name="text"]')) f.querySelector('[name="text"]').value = vals.text;
            if (vals.obstacleText !== undefined && f.querySelector('[name="obstacleText"]')) f.querySelector('[name="obstacleText"]').value = vals.obstacleText;
            V.dirty = true;
         }
      }
    }
  });
  document.querySelector('#skip-link').addEventListener('click',e=>{e.preventDefault();document.querySelector('#content')?.focus();});
  window.addEventListener('hashchange',()=>{V.dirty=false;if(dialog.open)dialog.close();V.render();window.scrollTo(0,0);});
  window.addEventListener('beforeunload',e=>{if(V.dirty||V.busy){e.preventDefault();e.returnValue='';}});
  window.addEventListener('storage',e=>{if(e.key===VTStorage.key&&!V.busy){if(V.dirty){V.notify('Data berubah di tab lain. Simpan setelah memuat ulang.',true);return;}V.state=VTStorage.load();V.render();}});
  V.render();
})();
