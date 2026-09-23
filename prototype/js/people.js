(() => {
  const V=VT,U=VTUI;
  function visible() {
    if(['HR','OPS'].includes(V.actor.role))return V.state.employees;
    if(V.actor.role==='PM')return V.state.employees.filter(e=>e.unit===V.actor.unit);
    return V.state.employees.filter(e=>e.id===V.actor.id);
  }
  const get=id=>visible().find(e=>e.id===id);
  const privateAccess=e=>e && (V.actor.role==='HR'||e.id===V.actor.id);
  function expiryBadge(d) {
    if(d.lifecycle!=='CURRENT'||!d.expiry)return '';
    if(d.expiry<V.state.demoDate)return U.badge('Kedaluwarsa');
    if(d.expiry===V.state.demoDate)return U.badge('Berakhir hari ini');
    const limit=new Date(new Date(V.state.demoDate+'T00:00:00Z').getTime()+7*86400000).toISOString().slice(0,10);
    return d.expiry<=limit?U.badge('Berakhir dalam 7 hari'):'';
  }
  function documentSummary(e) {
    const pending=e.documents.filter(d=>d.status==='PENDING').length;
    const urgent=e.documents.filter(d=>expiryBadge(d)).length;
    return pending||urgent?U.actions(pending?U.badge(pending+' menunggu HR'):'',urgent?U.badge(urgent+' perlu perpanjangan'):''):'';
  }
  function people(){
    const employees=visible(),hr=V.actor.role==='HR';
    const status=e=>U.badge(e.status)+(hr?documentSummary(e):'');
    const attrs=e=>`data-search-item="${U.esc((e.name+' '+e.position+' '+U.unit(e.unit)).toLowerCase())}" data-status="${U.esc(e.status)}"`;
    const listing=V.route.device==='mobile'?`<div class="mobile-list">${employees.map(e=>`<article class="card" ${attrs(e)}><div class="person-name">${U.avatar(e.name)}<div><h3><a href="${U.href('employee',e.id)}">${U.esc(e.name)}</a></h3><small>${U.esc(e.position)}</small></div></div>${U.dl([['Unit',U.esc(U.unit(e.unit))],['Status',status(e)]])}${U.link(['employee',e.id],'Lihat profil')}</article>`).join('')}</div>`:
      '<div class="table-wrap"><table><thead><tr>'+['Karyawan','Jabatan','Unit','Status',''].map(h=>'<th>'+h+'</th>').join('')+'</tr></thead><tbody>'+employees.map(e=>`<tr ${attrs(e)}><td><div class="person-name">${U.avatar(e.name)}<strong>${U.esc(e.name)}</strong></div></td><td>${U.esc(e.position)}</td><td>${U.esc(U.unit(e.unit))}</td><td>${status(e)}</td><td>${U.link(['employee',e.id],'Lihat profil','small')}</td></tr>`).join('')+'</tbody></table></div>';
    const active=employees.filter(e=>e.status==='ACTIVE').length;
    return U.heading(V.actor.role==='PM'?'Tim unit':'Karyawan',`${employees.length} orang dalam lingkup Anda · ${active} aktif · ${employees.length-active} nonaktif.`)+
      `<div class="toolbar"><input class="search" type="search" data-search placeholder="Cari nama, jabatan, atau unit…" aria-label="Cari karyawan"><select data-filter aria-label="Status karyawan"><option value="">Semua status</option><option value="ACTIVE">Aktif</option><option value="INACTIVE">Nonaktif</option></select></div>`+listing+'<p class="muted spaced hidden" id="no-results">Tidak ada karyawan yang cocok. Ubah kata pencarian atau pilih semua status.</p>';
  }
  function employeeDocuments(e,own) {
    const pending=e.documents.filter(d=>d.status==='PENDING');
    const current=e.documents.filter(d=>d.lifecycle==='CURRENT'&&d.status!=='PENDING');
    const history=e.documents.filter(d=>d.status!=='PENDING'&&d.lifecycle!=='CURRENT');
    // A document that is expiring or expired gets its renewal button right here, with the type prefilled.
    const soon=d=>{const today=V.state.demoDate;return own&&e.status==='ACTIVE'&&d.lifecycle==='CURRENT'&&d.expiry&&d.expiry<=new Date(new Date(today).getTime()+30*86400000).toISOString().slice(0,10)&&!pending.some(p=>p.type===d.type);};
    const rows=docs=>docs.map(d=>U.row(d.type,(d.numberMasked||'—')+' · '+(d.expiry?'Berlaku sampai '+U.date(d.expiry):'Tanggal akhir tidak dicantumkan'),U.actions(U.badge(d.status),expiryBadge(d),soon(d)?U.button('upload-employee','Ajukan perpanjangan',{employeeId:e.id,type:d.type},'small primary'):'',U.link(['employee-document',e.id,d.id],V.actor.role==='HR'&&d.status==='PENDING'?'Tinjau dokumen':'Pratinjau','small')))).join('');
    const guidance=own?'Ajukan berkas → HR memeriksa → dokumen terverifikasi menggantikan versi sebelumnya. Selama menunggu, dokumen lama tetap tercatat; periksa masa berlakunya.':'Karyawan mengajukan berkas dari profilnya sendiri. HR memeriksa berkas dan mencatat keputusan; versi sebelumnya tetap tersimpan.';
    return U.panel('Dokumen karyawan',U.note(guidance)+
      (own&&e.status==='ACTIVE'?'<div class="spaced">'+U.button('upload-employee','+ Ajukan dokumen',{employeeId:e.id},'primary')+'</div>':'')+
      `<div class="spaced"><p>${pending.length} menunggu HR · ${current.length} dokumen terkini · ${history.length} dalam riwayat.</p></div><br>`+
      (pending.length?'<h3>Menunggu verifikasi HR</h3>'+rows(pending):'')+
      '<h3>Dokumen terkini</h3>'+(current.length?rows(current):'<p>Belum ada dokumen terverifikasi. '+(own?'Gunakan Ajukan dokumen untuk mengirim berkas.':'Minta karyawan mengajukan berkas dari profilnya.')+'</p>')+
      (history.length?`<details class="spaced"><summary>Riwayat dokumen (${history.length})</summary>${rows(history)}</details>`:''));
  }
  function profile(id=V.actor.id){
    const e=get(id); if(!e)return U.empty('Profil tidak tersedia','Anda tidak memiliki akses ke profil ini.');
    const own=e.id===V.actor.id,hr=V.actor.role==='HR',manage=['HR','OPS'].includes(V.actor.role);
    const account=V.D.actors.find(a=>a.id===e.id);
    const basic=U.panel('Identitas & penempatan',`<div class="person-name">${U.avatar(e.name,true)}<div><h2>${U.esc(e.name)}</h2><p>${U.esc(e.position)}</p></div></div>`+U.dl([['Unit',U.esc(U.unit(e.unit))],['Status',U.badge(e.status)],['Tanggal masuk',U.date(e.joinDate)],['Akun terkait',account?U.esc(account.id)+' · '+(e.accessRevoked?'akses dicabut':'akun simulasi aktif'):'Belum memiliki akun demo']])+(manage&&e.status==='ACTIVE'?U.actions(U.button('promote','Ubah penempatan',{employeeId:e.id}),U.button('reason','Offboarding',{action:'OFFBOARD',employeeId:e.id},'danger')):''));
    const privateDetails=privateAccess(e)?U.panel('Kontak & data pribadi',U.dl([['Email',U.esc(e.email)],['Telepon',U.esc(e.phone||'Belum diisi')],['Alamat',U.esc(e.address||'Belum diisi')],['Tanggal lahir',U.date(e.birthDate)],['Kontak darurat',U.esc(e.emergencyContact||'Belum diisi')]])+(hr&&e.status==='ACTIVE'?U.button('edit-employee','Sunting data',{employeeId:e.id}):'')):U.note('Data kontak pribadi dan dokumen identitas hanya terlihat oleh pemilik serta HR.');
    const docs=privateAccess(e)?employeeDocuments(e,own):'';
    return U.heading(own?'Profil saya':e.name,own?'Data pribadi, dokumen, dan riwayat penempatan Anda.':U.unit(e.unit),U.link(['HR','OPS','PM'].includes(V.actor.role)?['people']:['home'],'Kembali'))+`<div class="columns"><div class="stack">${basic}${privateDetails}${docs}</div><div class="stack">${U.panel('Riwayat penempatan',e.assignmentHistory.map(a=>`<div class="event"><strong>${U.esc(a.position)}</strong><p>${U.esc(U.unit(a.unit))}</p><small>${U.date(a.from)} – ${a.to?U.date(a.to):'sekarang'}</small></div>`).join(''))}${e.offboardingReason?U.panel('Offboarding',U.note(e.offboardingReason)+U.dl([['Tanggal',U.date(e.offboardedAt)],['Akses','Akun terkait dinonaktifkan.']])):''}${own?U.panel('Kehadiran pribadi',U.link(['attendance'],'Buka absensi')):''}</div></div>`;
  }
  function employeeDocument(employeeId,documentId){
    const e=get(employeeId),d=e?.documents.find(d=>d.id===documentId);
    if(!privateAccess(e)||!d)return U.empty('Dokumen tidak tersedia','Dokumen pribadi hanya untuk pemilik dan HR.');
    return U.heading(d.type,e.name,U.link(['employee',e.id],'← Profil karyawan'))+`<div class="columns"><div class="stack">${U.panel('Pratinjau berkas',d.attachment?`<div id="embedded-file" data-file="${U.esc(JSON.stringify(d.attachment))}"><p>Memuat lampiran…</p></div>`:U.note('Berkas tidak tersedia pada dokumen ini.'))}</div><div class="stack">${U.panel('Identitas dokumen',U.actions(U.badge(d.status),U.badge(d.lifecycle),expiryBadge(d))+U.dl([['Pemilik',U.esc(e.name)],['Nomor',U.esc(d.numberMasked)],['Berlaku sampai',U.date(d.expiry)],['Pengunggah',U.esc(d.uploadedBy?U.person(d.uploadedBy):'Data awal simulasi')],['Peninjau',U.esc(d.verifiedBy?U.person(d.verifiedBy):'—')],['Catatan',U.esc(d.reviewNote||'—')]])+((d.expiry&&d.expiry<V.state.demoDate)?U.panel('Perpanjangan Dokumen', U.note('Masa berlaku dokumen sudah berakhir. Ajukan dokumen pengganti.') + (own&&e.status==='ACTIVE'?U.button('upload-employee','Ajukan '+d.type,{employeeId:e.id,type:d.type},'primary'):'')) : ''))}${V.actor.role==='HR'&&d.status==='PENDING'?(d.uploadedBy===V.actor.id||e.id===V.actor.id?U.note('Pemilik atau pengunggah tidak dapat memverifikasi dokumen sendiri.'):U.panel('Verifikasi independen',U.form('verify-document',U.select('decision','Keputusan',[['APPROVE','Verifikasi'],['REJECT','Tolak']],'APPROVE')+U.textarea('note','Catatan pemeriksaan','','required'),'Simpan keputusan',{employeeId:e.id,documentId:d.id}))):''}</div></div>`;
  }
  function organization(){return U.heading('Struktur organisasi',`${V.state.employees.length} orang · buka setiap unit untuk melihat anggotanya.`)+`<div class="card org-root"><div class="eyebrow">DIREKSI</div><h2>Sutono</h2><small>Direktur</small></div><div class="card org-root"><div class="eyebrow">OPERASIONAL</div><h2>Ade Candra</h2><small>Operational Manager</small></div><div class="grid three">${V.D.units.filter(u=>!['DIRECTOR','OPERATIONS'].includes(u.code)).map(u=>{const members=V.state.employees.filter(e=>e.unit===u.code);return `<article class="card org-card"><div class="eyebrow">${U.esc(u.name)}</div><h2>${U.esc(u.lead)}</h2><p>${U.esc(u.description)}</p><details><summary>${members.length} orang · lihat anggota</summary>${members.map(e=>U.row(e.name,e.position,U.actions(U.badge(e.status),get(e.id)?U.link(['employee',e.id],'Lihat profil','small'):''))).join('')}</details></article>`}).join('')}</div><div class="spaced">${U.note('Business Development A/B merupakan nama sementara. Peran HR, pengelola aset, dan ketua proyek adalah penugasan simulasi.')}</div>`;}
  V.forms['upload-employee']=async(form,data)=>{const files=await V.uploadFiles(form);data.attachment=files[0];if(data.sample==='yes'&&!data.attachment)data.attachment={id:'sample-certificate',name:'sertifikat-k3-contoh.svg',type:'image/svg+xml'};if(!data.attachment)throw Error('Pilih berkas dokumen atau lampiran contoh.');if(V.run('UPLOAD_DOCUMENT',data)){V.closeDialog();V.go('employee',data.employeeId);V.notify('Dokumen diajukan. Tunggu pemeriksaan HR; hasilnya dapat dilihat pada profil Anda.');}};
  V.forms['verify-document']=async(form,data)=>{if(V.run('VERIFY_DOCUMENT',data))V.notify(data.decision==='APPROVE'?'Dokumen terverifikasi. Versi sebelumnya tersimpan dalam riwayat.':'Dokumen ditolak. Pemilik dapat membaca catatan pemeriksaan dan mengajukan berkas baru.');};
  V.forms['edit-employee']=async(form,data)=>{if(V.run('UPDATE_EMPLOYEE',data))V.closeDialog();};
  V.forms.promote=async(form,data)=>{if(V.run('PROMOTE',data))V.closeDialog();};
  V.views.people=people; V.views.profile=()=>profile(); V.views.employee=()=>profile(V.route.args[0]); V.views['employee-document']=()=>employeeDocument(...V.route.args); V.views.organization=organization;
  V.people={get,privateAccess};
})();
