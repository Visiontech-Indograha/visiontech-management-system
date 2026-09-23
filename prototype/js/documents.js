(() => {
  const V=VT,U=VTUI;
  const urls=new Set();
  const letterhead=()=>`<header class="letterhead"><div><strong>VISIONTECH INDOGRAHA</strong><small>Operational Workspace · Pekanbaru, Indonesia</small></div><div><strong>VTI</strong><small>Dokumen penugasan</small></div></header>`;
  const footer=(number,version)=>`<footer class="document-footer">${U.esc(number)} · Versi ${version}<br>Dokumen simulasi untuk peninjauan alur. Persetujuan pada prototipe bukan tanda tangan elektronik resmi.</footer>`;
  function tools(back,versions='') {
    return `<div class="viewer-tools"><div class="actions">${U.link(back,'← Kembali')}${versions}</div><div class="actions"><label class="actions">Ukuran <select aria-label="Pembesaran dokumen" data-zoom><option value="fit">Sesuai layar</option><option value="0.75">75%</option><option value="1">100%</option><option value="1.25">125%</option><option value="1.5">150%</option></select></label>${U.button('print','Cetak / Simpan PDF',{},'primary')}</div></div>`;
  }
  function order(planId,docId) {
    const p=V.work.get(planId),doc=p?.documents.find(d=>d.id===docId);
    if(!doc)return U.empty('Dokumen tidak tersedia','Periksa pekerjaan, versi, dan lingkup peran Anda.');
    const s=doc.snapshot;
    const kindLabel=d=>d.kind==='ADDENDUM'?'Adendum':d.kind==='PERSONNEL_ADDENDUM'?'Adendum personel':d.kind==='REVISION'?'Revisi':'SK';
    const title=doc.kind==='ADDENDUM'?'ADENDUM SURAT TUGAS':doc.kind==='PERSONNEL_ADDENDUM'?'ADENDUM PERSONEL SURAT TUGAS':doc.kind==='REVISION'?'REVISI SURAT TUGAS':'SURAT TUGAS';
    const versions=`<label class="actions">Versi <select aria-label="Pilih versi dokumen" data-version>${p.documents.map(d=>`<option value="${U.esc(U.href('document',p.id,d.id))}"${d.id===doc.id?' selected':''}>${d.version} · ${kindLabel(d)} · ${U.states[d.status]}</option>`).join('')}</select></label>`;
    let actionButtons='';
    if(p.documents[p.documents.length-1].id===doc.id){
      const out=[],payload={planId:p.id,rowVersion:p.rowVersion};
      const cmd=(type,label,kind='',guard=false)=>U.command(type,label,payload,kind,guard);
      const reason=(type,label)=>U.button('reason',label,{action:type,...payload});
      const incomingLeader=p.change?.type==='PERSONNEL'&&p.change.status==='AWAITING_LEADER_ACCEPTANCE'&&p.change.leaderId===V.actor.id;
      if(V.work.leader(p)){
        if(p.status==='PUBLISHED')out.push(cmd('ACCEPT','Terima SK','primary',true),reason('APPEAL','Ajukan banding'));
        if(p.change?.status==='AWAITING_LEADER_ACCEPTANCE'&&doc.kind==='ADDENDUM')out.push(cmd('ACCEPT_CHANGE','Terima adendum final','primary',true),reason('REJECT_CHANGE','Tolak adendum'));
      }
      // Only the person named as the new leader decides; the PM withdraws from the plan page instead.
      if(incomingLeader&&doc.kind==='PERSONNEL_ADDENDUM')out.push(cmd('ACCEPT_CHANGE','Terima adendum personel','primary',true),reason('REJECT_CHANGE','Tolak adendum personel'));
      if(out.length)actionButtons=`<div class="panel spaced" style="margin-bottom:20px"><div class="section-head"><h3 style="margin:0">Tindakan pada versi ini</h3></div>${U.actions(...out)}</div>`;
    }
    const locked=V.D.documentLocked(p,doc);
    return U.heading('Pratinjau dokumen',doc.number+' · '+U.states[doc.status]+(locked?' · terkunci (riwayat)':''))+tools(['plan',p.id,'documents'],versions)+(locked?U.note('Versi ini terkunci karena sudah ada versi yang lebih baru. Isinya tetap sesuai keadaan saat diterbitkan.'):'')+actionButtons+
    `<div class="paper-stage"><article class="document-paper">${letterhead()}<div class="document-banner">CONTOH PROTOTIPE · ${U.esc(U.states[doc.status]||doc.status).toUpperCase()}</div><h1>${title}</h1><div class="doc-number">Nomor: ${U.esc(doc.number)} · Versi ${doc.version}</div>
    ${U.dl([['Pekerjaan',U.esc(s.title)],['Unit',U.esc(U.unit(s.unit))],['Lokasi',U.esc(s.location)],['Periode',U.date(s.startDate)+' – '+U.date(s.endDate)],['Tanggal terbit',U.date(doc.issuedAt)],['Project Manager',U.esc(s.pm.name)],['Ketua tim',U.esc(s.leader.name)]])}
    <h2>1. Lingkup penugasan</h2><p>${U.esc(s.description||'Pelaksanaan pekerjaan sesuai rincian harian, ketentuan keselamatan, dan koordinasi dengan pengelola lokasi.')}</p>
    ${doc.kind==='PERSONNEL_ADDENDUM'?`<p class="spaced">Dokumen ini mengubah susunan personel pada surat tugas dasar${doc.reason?': '+U.esc(doc.reason):''}. Perubahan berlaku setelah ketua tim menerima adendum ini. Susunan pada dokumen versi sebelumnya tetap tersimpan sebagai riwayat dan tidak berubah.</p>`:''}
    ${doc.kind==='ADDENDUM'?'<p class="spaced">Dokumen ini menyesuaikan periode serta rincian penugasan pada surat tugas dasar. Perubahan berlaku setelah persetujuan penerbit dan penerimaan ketua tim tercatat. Dokumen dasar tetap tersedia dalam riwayat.</p>':''}
    <h2>2. Susunan tim</h2>${U.table(['Nama','Jabatan saat diterbitkan','Peran'],[[U.esc(s.leader.name),U.esc(s.leader.position),'Ketua tim'],...s.members.map(m=>[U.esc(m.name),U.esc(m.position),'Anggota'])])}
    <h2>3. Rincian pekerjaan harian</h2>${U.table(['Tanggal','Kegiatan','Tugas'],s.days.map(d=>[U.date(d.date),U.esc(d.title),`<ol>${d.tasks.map(t=>`<li>${U.esc(t.title)}</li>`).join('')}</ol>`]))}
    <h2>4. Kendaraan & peralatan saat penerbitan</h2>${s.assets?.length?U.table(['Kode','Sumber daya','Pengemudi'],s.assets.map(a=>[U.esc(a.code),U.esc(a.name),U.esc(a.driver||'—')])):'<p>Tidak ada aset yang dialokasikan pada saat dokumen diterbitkan.</p>'}
    <h2>5. Lampiran</h2>${s.attachments?.length?s.attachments.map((f,i)=>`<div class="attachment"><span>${i+1}. ${U.esc(f.name)}</span><span class="actions">${U.button('attachment','Buka berkas',f,'small')}</span></div>`).join(''):'<p>Tidak ada lampiran pada versi ini.</p>'}
    <h2>6. Ketentuan pelaksanaan</h2><ol><li>Ketua mengoordinasikan tim dan mencatat checklist, laporan harian, serta bukti pelaksanaan.</li><li>Perubahan jadwal mengikuti persetujuan PM dan penerimaan adendum oleh ketua tim.</li><li>Penutupan memerlukan seluruh laporan disetujui serta aset terverifikasi kembali.</li></ol>
    <div class="signatures"><div class="signature-box"><small>Diterbitkan / disetujui oleh</small><strong>${U.esc(doc.issuedBy)}</strong><small>${U.date(doc.issuedAt)} · ${U.clock(doc.issuedAt)} WIB</small><small>Persetujuan tercatat dalam simulasi.</small></div><div class="signature-box"><small>Diterima oleh ketua tim</small><strong>${U.esc(doc.acceptedBy||'BELUM DITERIMA')}</strong><small>${doc.acceptedAt?U.date(doc.acceptedAt)+' · '+U.clock(doc.acceptedAt)+' WIB':'Menunggu penerimaan versi ini.'}</small><small>${doc.acceptedBy?'Penerimaan tercatat dalam simulasi.':'Tidak ada tanda tangan penerimaan.'}</small></div></div>${footer(doc.number,doc.version)}</article></div>
    <div class="spaced document-hint">${U.note('Isi versi terbit tidak mengikuti perubahan profil terbaru. Gunakan Cetak / Simpan PDF untuk membuka dialog cetak browser; pilih Save as PDF bila tersedia.')}</div>`;
  }
  function report(planId,dayId){
    const p=V.work.get(planId),d=p?.days.find(d=>d.id===dayId);
    if(!d)return U.empty('Laporan tidak tersedia');
    const latest=[...p.documents].reverse().find(doc=>doc.status==='EFFECTIVE');
    const leaderName=latest?.snapshot.leader.name||U.person(p.leaderId);
    return U.heading('Pratinjau laporan harian',U.date(d.date)+' · '+p.title)+tools(['plan',p.id,'days'])+
    `<div class="paper-stage"><article class="document-paper">${letterhead()}<div class="document-banner">CONTOH PROTOTIPE · ${U.esc(U.states[d.reportStatus]).toUpperCase()}</div><h1>LAPORAN KEGIATAN HARIAN</h1><div class="doc-number">Rujukan: ${U.esc(p.number)} · ${U.date(d.date)}</div>${U.dl([['Pekerjaan',U.esc(p.title)],['Lokasi',U.esc(p.location)],['Kegiatan',U.esc(d.title)],['Ketua tim',U.esc(leaderName)],['Tanggal kegiatan',U.date(d.date)]])}<h2>Checklist pelaksanaan</h2>${U.table(['Tugas','Hasil'],d.tasks.map(t=>[U.esc(t.title),t.done?'Selesai':'Belum selesai']))}<h2>Uraian kegiatan</h2><p style="white-space:pre-wrap">${U.esc(d.reportText||'Laporan belum diisi.')}</p><h2>Bukti pelaksanaan</h2>${d.evidence.length?d.evidence.map(f=>U.attachment(f)).join(''):'<p>Belum ada bukti.</p>'}<h2>Hasil pemeriksaan</h2>${U.dl([['Status',U.esc(U.states[d.reportStatus])],['Peninjau',U.esc(d.reviewedBy||'Belum ditinjau')],['Catatan',U.esc(d.reviewNote||'—')],['Tanggal review',U.date(d.reviewedAt)]])}<div class="signatures"><div class="signature-box"><small>Diserahkan oleh</small><strong>${U.esc(d.submittedBy||'Belum diserahkan')}</strong><small>${U.date(d.submittedAt)}</small></div><div class="signature-box"><small>Ditinjau oleh</small><strong>${U.esc(d.reviewedBy||'Belum ditinjau')}</strong><small>${U.esc(U.states[d.reportStatus])}</small></div></div>${footer(p.number,p.revision)}</article></div>`;
  }
  async function fileContent(meta){
    const blob=await VTStorage.get(meta.id);
    const url=URL.createObjectURL(blob);urls.add(url);
    const download=`<a class="btn" href="${url}" download="${U.esc(meta.name)}">Unduh berkas</a>`;
    let content;
    const safeImage=['image/png','image/jpeg','image/gif','image/webp','image/bmp'].includes(blob.type)||(meta.id.startsWith('sample-')&&blob.type==='image/svg+xml');
    if(safeImage)content=`<img class="preview-image" src="${url}" alt="${U.esc(meta.name)}">`;
    else if(blob.type==='application/pdf')content=`<object class="preview-pdf" data="${url}" type="application/pdf" aria-label="${U.esc(meta.name)}"><p>Penampil PDF bawaan tidak tersedia. Gunakan Unduh berkas untuk membuka PDF.</p>${download}</object>`;
    else content=U.note('Format berkas ini tidak ditampilkan di dalam prototipe. Unduh untuk membukanya di aplikasi yang sesuai.');
    return `<div class="file-preview">${content}</div><div class="actions spaced">${download}</div>`;
  }
  async function openFile(meta){
    V.dialog('Pratinjau lampiran',`<p>${U.esc(meta.name)}</p><div id="dialog-file" class="spaced">Memuat berkas…</div>`);
    const target=document.querySelector('#dialog-file');
    try{const html=await fileContent(meta);if(target?.isConnected)target.innerHTML=html;}catch(e){if(target?.isConnected)target.innerHTML=U.note(e.message,'error');}
  }
  function fit(){
    const paper=document.querySelector('.document-paper'),stage=document.querySelector('.paper-stage');
    if(!paper||!stage)return;
    const selected=document.querySelector('[data-zoom]')?.value||'fit';
    const scale=selected==='fit'?Math.min(1,(stage.clientWidth-parseFloat(getComputedStyle(stage).paddingLeft)*2)/793.7):Number(selected);
    paper.style.zoom=String(Math.max(.2,scale));
  }
  async function afterRender(){
    fit();
    const target=document.querySelector('#embedded-file');
    if(target){try{const html=await fileContent(JSON.parse(target.dataset.file));if(target.isConnected)target.innerHTML=html;}catch(e){if(target.isConnected)target.innerHTML=U.note(e.message,'error');}}
  }
  function clearURLs(){urls.forEach(u=>URL.revokeObjectURL(u));urls.clear();}
  window.addEventListener('resize',fit);
  V.views.document=()=>order(...V.route.args);V.views.report=()=>report(...V.route.args);
  V.documents={openFile,afterRender,fit,clearURLs};
})();
