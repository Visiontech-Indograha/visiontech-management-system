(() => {
  const V = VT, U = VTUI;
  const plans = (archive=false) => V.D.visiblePlans(V.state,V.actor,{includeArchived:archive});
  const get = id => plans(true).find(p => p.id === id);
  const canManage = p => V.D.can(V.actor,'CREATE_PLAN',p?.unit);
  // Whoever the SK names as leader gets the leader actions, even if their demo identity is an ordinary member.
  const leader = p => p.leaderId === V.actor.id;
  // Report status in plain words: a plain "Draft" badge reads as if the whole plan were a draft.
  const reportBadge = d => {
    const labels = {DRAFT:'Laporan belum dikirim',SUBMITTED:'Menunggu review PM',CHANGES_REQUESTED:'Perlu perbaikan',APPROVED:'Laporan disetujui'};
    const tone = {DRAFT:'',SUBMITTED:'amber',CHANGES_REQUESTED:'red',APPROVED:'green'}[d.reportStatus] || '';
    return `<span class="badge ${tone}">${U.esc(labels[d.reportStatus] || d.reportStatus)}</span>`;
  };
  const progress = p => { const tasks=p.days.flatMap(d=>d.tasks); return {done:tasks.filter(t=>t.done).length,total:tasks.length}; };
  function card(p) {
    const n = progress(p);
    return `<article class="card plan-card" data-search-item="${U.esc([p.title,p.number,p.location].join(' ').toLowerCase())}" data-status="${p.deletedAt?'ARCHIVED':p.status}"><div class="section-head"><span class="eyebrow">${U.esc(U.unit(p.unit))}</span>${p.deletedAt?U.badge('Arsip'):U.badge(p.status)}</div><h3><a href="${U.href('plan',p.id)}">${U.esc(p.title)}</a></h3><p>${U.esc(p.location)}</p><div class="progress"><span style="width:${n.total?Math.round(n.done/n.total*100):0}%"></span></div><small>${n.done} dari ${n.total} tugas selesai</small><div class="meta"><span>${U.date(p.startDate)} – ${U.date(p.endDate)}</span><span>${U.esc(U.person(p.leaderId).split(' ')[0])}</span></div></article>`;
  }
  function list(tab='active') {
    const all=plans(true);
    let items, title, desc;
    if (tab === 'completed') {
      items = all.filter(p => p.status === 'COMPLETED');
      title = 'Riwayat: Selesai'; desc = 'Pekerjaan yang telah ditutup dan tidak dapat diaktifkan kembali.';
    } else if (tab === 'archived') {
      items = all.filter(p => p.status === 'DRAFT' || p.deletedAt);
      title = 'Arsip & Pending'; desc = 'Draft pekerjaan yang belum berjalan atau diarsipkan.';
    } else if (tab === 'cancelled') {
      items = all.filter(p => p.status === 'CANCELLED');
      title = 'Riwayat: Batal'; desc = 'Pekerjaan yang dibatalkan dan tidak dapat diaktifkan kembali.';
    } else {
      items = all.filter(p => !['COMPLETED', 'CANCELLED', 'DRAFT'].includes(p.status) && !p.deletedAt);
      title = 'Pekerjaan Aktif'; desc = 'Penugasan yang sedang berjalan atau menunggu tindakan.';
    }

    const tabs = `<nav class="tabs spaced" aria-label="Filter status">
      <a class="${tab==='active'?'active':''}" href="${U.href('plans')}">Aktif</a>
      <a class="${tab==='completed'?'active':''}" href="${U.href('plans','completed')}">Selesai</a>
      <a class="${tab==='archived'?'active':''}" href="${U.href('plans','archived')}">Arsip / Pending</a>
      <a class="${tab==='cancelled'?'active':''}" href="${U.href('plans','cancelled')}">Batal</a>
    </nav>`;

    return U.heading(title, desc, V.D.can(V.actor,'CREATE_PLAN')?U.link(['new'],'+ Buat work plan','primary'):'')+tabs+
    `<div class="toolbar"><input class="search" type="search" aria-label="Cari work plan" placeholder="Cari nama, nomor, atau lokasi…" data-search></div><div class="grid ${V.route.device==='desktop'?'three':''}">${items.map(card).join('')}</div><p class="muted spaced hidden" id="no-results">Tidak ada pekerjaan yang cocok.</p>`+(items.length?'':U.empty('Belum ada pekerjaan di kategori ini.'));
  }
  function editor(p,unitarg) {
    const unit=p?.unit || (V.actor.role==='OPS'?(unitarg || 'CCTV_ACS'):V.actor.unit);
    if (!V.D.can(V.actor,'CREATE_PLAN',unit)) return U.empty('Tidak memiliki kewenangan','Pembuatan work plan hanya tersedia untuk PM unit terkait atau Operational Manager.');
    if (p && (p.status!=='DRAFT'||p.deletedAt)) return U.empty('Pekerjaan sudah terbit','Pekerjaan sudah terbit. Perubahan jadwal melalui perpanjangan/adendum.', U.link(['plan', p.id], 'Kembali ke pekerjaan'));
    const employees=V.state.employees.filter(e=>e.status==='ACTIVE'&&e.unit===unit);
    const initialLeader=p?.leaderId || (unit==='CCTV_ACS'?'leader':'emp-032');
    return U.heading(p?'Sunting work plan':'Buat work plan','Lengkapi penugasan, lalu periksa rincian harian sebelum menerbitkan SK.',U.link(p?['plan',p.id]:['plans'],'Kembali'))+
      (V.actor.role==='OPS'&&!p?`<div class="tabs">${['CCTV_ACS','WALL_DISPLAY'].map(u=>`<a class="${u===unit?'active':''}" href="${U.href('new',u)}">${U.unit(u)}</a>`).join('')}</div>`:'')+
      U.panel('Informasi pekerjaan',U.form('plan',`<div class="grid">${U.input('title','Nama pekerjaan',p?.title||'','text','required maxlength="160"')}${U.input('location','Lokasi',p?.location||'','text','required maxlength="200"')}${U.input('startDate','Tanggal mulai',p?.startDate||V.state.demoDate,'date','required')}${U.input('endDate','Tanggal selesai',p?.endDate||V.state.demoDate,'date','required')}<div class="wide">${U.textarea('description','Lingkup pekerjaan',p?.description||'','maxlength="3000"')}        </div>${U.select('leaderId','Ketua tim',employees.filter(e=>e.id!==(p?.pmId||V.actor.id)).map(e=>[e.id,e.name+' · '+e.position]),initialLeader,'data-leader-select required')}</div><h3>Anggota tim</h3><p class="field-hint spaced">Minimal satu anggota. Ketua tidak dihitung sebagai anggota.</p><div class="grid">${employees.filter(e=>e.id!==(p?.pmId||V.actor.id)).map(e=>`<label class="check"><input type="checkbox" name="memberIds" value="${e.id}"${p?.memberIds.includes(e.id)?' checked':''}${e.id===initialLeader?' disabled':''}><span class="emp-name">${U.esc(e.name)}</span></label>`).join('')}</div>`,'Simpan draft',{planId:p?.id||'',unit,rowVersion:p?.rowVersion||''}));
  }
  function controls(p) {
    const out=[], payload={planId:p.id,rowVersion:p.rowVersion};
    const cmd=(type,label,kind='',guard=false)=>U.command(type,label,payload,kind,guard);
    const reason=(type,label)=>U.button('reason',label,{action:type,...payload});
    if (p.deletedAt) return canManage(p)?U.actions(cmd('RESTORE_PLAN','Pulihkan draft','primary',true)):'';
    if (canManage(p)) {
      if (p.status==='DRAFT') {
        out.push(U.link(['edit',p.id],'Sunting draft'),cmd('PUBLISH','Terbitkan SK','primary',true));
        if (p.documents.length === 0) out.push(reason('DELETE_PLAN','Arsipkan draft'));
      }
      if (p.status==='APPEALED') out.push(cmd('REVISE','Buka draft revisi','primary'));
      if (p.change?.status==='PENDING_PM') out.push(cmd('APPROVE_CHANGE','Setujui perpanjangan','primary',true),reason('REJECT_CHANGE','Tolak perpanjangan'));
      if (p.status==='COMPLETION_REVIEW') out.push(cmd('APPROVE_COMPLETE','Setujui penyelesaian','primary',true),reason('RETURN_COMPLETE','Kembalikan penyelesaian'));
      if (['ACCEPTED','IN_PROGRESS'].includes(p.status)&&!['PENDING_PM','AWAITING_LEADER_ACCEPTANCE'].includes(p.change?.status)) out.push(U.button('personnel','Adendum personel',{planId:p.id}));
      if (p.change?.type==='PERSONNEL'&&p.change.status==='AWAITING_LEADER_ACCEPTANCE') out.push(reason('WITHDRAW_CHANGE','Tarik adendum personel'));
      if (['PUBLISHED','APPEALED','ACCEPTED','IN_PROGRESS','COMPLETION_REVIEW'].includes(p.status)) out.push(reason('CANCEL_PLAN','Batalkan pekerjaan'));
    }
    if (leader(p)) {
      if (p.status==='PUBLISHED') out.push(U.link(['document',p.id,p.documents.at(-1).id],'Buka & Tinjau SK','primary'));
      if (p.status==='ACCEPTED') out.push(cmd('START','Mulai pelaksanaan','primary',true));
      if (['ACCEPTED','IN_PROGRESS'].includes(p.status)&&!['PENDING_PM','AWAITING_LEADER_ACCEPTANCE'].includes(p.change?.status)) out.push(U.button('extension','Ajukan perpanjangan',payload));
      if (p.change?.status==='AWAITING_LEADER_ACCEPTANCE') out.push(U.link(['document',p.id,p.documents.at(-1).id],'Buka & Tinjau Adendum','primary'));
      if (p.status==='IN_PROGRESS'&&!['PENDING_PM','AWAITING_LEADER_ACCEPTANCE'].includes(p.change?.status)) {
        const readyForFinal = p.days.every(d=>d.reportStatus==='APPROVED') && (p.weeks||[]).every(w=>w.status==='APPROVED');
        if (readyForFinal) out.push(U.link(['plan',p.id,'days'], p.finalReport?.status === 'CHANGES_REQUESTED' ? 'Revisi Laporan Akhir' : 'Buat Laporan Akhir','primary'));
      }
      if (p.status==='COMPLETED') {
        out.push(U.link(['presentation',p.id], 'Mode Presentasi Laporan', 'primary'));
      }
    }
    if (p.status === 'IN_PROGRESS' && (leader(p) || p.memberIds?.includes(V.actor.id))) {
      out.push(U.button('incident', 'Lapor Insiden/HSE', payload, 'danger'));
    }
    if (p.status === 'IN_PROGRESS' && leader(p)) {
      out.push(U.button('overtime', 'Ajukan Lembur', payload));
    }
    return out.length?U.panel('Tindakan Anda',U.actions(...out)):'';
  }
  function detail(id,tab='overview') {
    const p=get(id); if (!p) return U.empty('Pekerjaan tidak tersedia','Pekerjaan ini tidak termasuk lingkup peran Anda.',U.link(['plans'],'Kembali'));
    let tabs=[['overview','Ringkasan'],['days','Rincian & laporan'],['resources','Sumber daya'],['documents','Dokumen'],['history','Riwayat']];
    if (V.actor.role === 'ASSET') tabs = tabs.filter(t => ['overview', 'resources', 'history'].includes(t[0]));
    const top=U.heading(p.title,p.number+' · '+U.unit(p.unit),U.link(['plans'],'Work plan'))+U.actions(U.badge(p.status),p.deletedAt?U.badge('Arsip'):'',`<small>Dokumen berlaku: versi ${p.revision}</small>`)+`<nav class="tabs spaced" aria-label="Detail pekerjaan">${tabs.map(([key,title])=>`<a class="${tab===key?'active':''}" href="${U.href('plan',id,key)}">${title}</a>`).join('')}</nav>`;
    let body;
    if (tab==='days') body=V.actor.role==='ASSET'?U.empty('Akses dibatasi','Peran pengelola aset tidak memiliki akses ke rincian pelaksanaan harian.'):dayList(p);
    else if (tab==='documents') body=documents(p);
    else if (tab==='resources') body=resources(p);
    else if (tab==='history') body=U.panel('Riwayat pekerjaan',p.activity.map(a=>`<div class="event"><small>${U.date(a.at)} · ${U.clock(a.at)} WIB</small><strong>${U.esc(a.actor)} · ${U.esc(V.actionNames?.[a.action]||a.action)}</strong><p>${U.esc(a.detail)}</p></div>`).join(''));
    else {
      const showCompletion = ['IN_PROGRESS','COMPLETION_REVIEW'].includes(p.status);
      const changeStatus = (!p.change || ['EFFECTIVE','REJECTED','CANCELLED'].includes(p.change.status)) ? 'Tidak ada perubahan tertunda' : 'Adendum harus selesai diputuskan.';
      const pendingAssets = V.state.assets.filter(a=>a.planId===p.id && a.status !== 'AVAILABLE').length;
      
      const incidents = V.state.incident_reports.filter(i => i.planId === p.id);
      const canResolve = i => i.status==='OPEN' && V.D.can(V.actor,'RESOLVE_INCIDENT',p.unit) && (V.actor.role!=='ASSET' || i.category==='ASET');
      const incidentHtml = incidents.length ? U.panel('Laporan Insiden / HSE', incidents.map(i => `<div class="row"><div><strong>[${U.esc(i.category)}] ${U.esc(i.severity)}</strong><small>${U.esc(i.description)}</small><small>${U.esc(U.person(i.employeeId))} · ${U.date(i.date)}${i.resolvedBy?' · ditutup oleh '+U.esc(i.resolvedBy):''}</small></div><div class="actions">${U.badge(i.status)}${canResolve(i)?U.button('resolve-incident','Selesaikan',{incidentId:i.id},'small primary'):''}</div></div>${(i.evidence||[]).map(e=>U.attachment(e)).join('')}`).join('')) : '';
      
      const overtimes = V.state.overtime_logs.filter(o => o.planId === p.id);
      const canReview = o => o.status==='PENDING_PM' && V.D.can(V.actor,'REVIEW_OVERTIME',p.unit) && o.employeeId!==V.actor.id;
      const overtimeHtml = overtimes.length ? U.panel('Rekap Lembur', overtimes.map(o => `<div class="row"><div><strong>${U.esc(U.person(o.employeeId))}</strong><small>${o.hours} jam · ${U.esc(o.reason)}</small><small>${U.date(o.date)}${o.reviewedBy?' · ditinjau '+U.esc(o.reviewedBy):''}${o.note?' · '+U.esc(o.note):''}</small></div><div class="actions">${U.badge(o.status)}${canReview(o)?U.button('review-overtime','Tinjau lembur',{overtimeId:o.id},'small primary'):''}</div></div>`).join('')) : '';
      
      body=`<div class="columns"><div class="stack">${U.panel('Informasi penugasan',U.dl([['Lokasi',U.esc(p.location)],['Periode',U.date(p.startDate)+' - '+U.date(p.endDate)],['Project Manager',U.esc(U.person(p.pmId))],['Ketua tim',U.esc(U.person(p.leaderId))],['Anggota',p.memberIds.map(id=>U.esc(U.person(id))).join(', ')],['Lingkup',U.esc(p.description||'Pelaksanaan sesuai rincian harian.')]]))}${V.actor.role==='ASSET'?'':U.panel('Tahapan harian',p.days.map((d,i)=>U.row(d.title,U.date(d.date),U.actions(reportBadge(d),U.link(['report',p.id,d.id],'Lihat','small')),String(i+1))).join(''))}${attachments(p)}</div><div class="stack">${controls(p)}${incidentHtml}${overtimeHtml}${p.finalReport?.status === 'CHANGES_REQUESTED' ? U.panel('Revisi Laporan Akhir', U.note(p.finalReport.reviewNote, 'error')) : ''}${p.appealReason?U.panel('Catatan banding',U.note(p.appealReason)):''}${p.change?U.panel(p.change.type==='PERSONNEL'?'Perubahan personel':'Perubahan jadwal',U.badge(p.change.status)+U.dl(p.change.type==='PERSONNEL'?[['Ketua tim',U.esc(U.person(p.change.oldLeaderId))+(p.change.leaderId!==p.change.oldLeaderId?' → '+U.esc(U.person(p.change.leaderId)):' (tetap)')],['Anggota diusulkan',p.change.memberIds.map(id=>U.esc(U.person(id))).join(', ')||'—'],['Dikeluarkan',(p.change.removedIds||[]).map(id=>U.esc(U.person(id))).join(', ')||'—'],['Alasan',U.esc(p.change.reason)],['Diajukan oleh',U.esc(p.change.requestedBy||'—')],['Keputusan',U.esc(p.change.rejectionReason||'Lihat status perubahan di atas.')]]:[['Jadwal awal',U.date(p.change.oldEnd)],['Usulan selesai',U.date(p.change.newEnd)],['Alasan',U.esc(p.change.reason)],['Keputusan',U.esc(p.change.rejectionReason||'Lihat status perubahan di atas.')]])+U.link(['plan',p.id,'documents'],'Lihat SK & Adendum')):''}${p.cancellationReason?U.note(p.cancellationReason):''}${p.deletionReason&&p.deletedAt?U.note(p.deletionReason):''}${showCompletion?U.panel('Syarat penyelesaian',U.row('Laporan harian',`${p.days.filter(d=>d.reportStatus==='APPROVED').length}/${p.days.length} laporan disetujui`)+U.row('Pengembalian aset',`${pendingAssets} aset belum terverifikasi kembali`)+U.row('Perubahan',changeStatus)):''}</div></div>`;
    }
    return top+body;
  }
  function attachments(p) {
    return U.panel('Lampiran pekerjaan',(p.attachments||[]).map(f=>U.attachment(f,p.status==='DRAFT'&&canManage(p)?U.button('remove-plan-file','Hapus',{planId:p.id,fileId:f.id},'small danger'):'')).join('')+(p.status==='DRAFT'&&!p.deletedAt&&canManage(p)?U.form('plan-files',U.upload(),'Tambahkan lampiran',{planId:p.id}):(!p.attachments?.length?'<p>Belum ada lampiran pekerjaan.</p>':'')));
  }
  function dayList(p) {
    let html = '';
    const isLeader = leader(p);
    const isPM = canManage(p);
    
    // Render interweaved days and weeks
    if (p.weeks && p.weeks.length > 0) {
      p.weeks.forEach(w => {
        w.dayIds.forEach(id => {
          const d = p.days.find(x => x.id === id);
          if(d) html += renderDay(d, p, isLeader, isPM);
        });
        html += renderWeek(w, p, isLeader, isPM);
      });
      // Render remaining days not in weeks
      const weekDayIds = new Set(p.weeks.flatMap(w => w.dayIds));
      p.days.filter(d => !weekDayIds.has(d.id)).forEach(d => {
        html += renderDay(d, p, isLeader, isPM);
      });
    } else {
      p.days.forEach(d => {
        html += renderDay(d, p, isLeader, isPM);
      });
    }
    
    // Render final report
    html += renderFinalReport(p, isLeader, isPM);
    return html;
  }
  function renderDay(d, p, isLeader, isPM) {
    const active = p.status === 'IN_PROGRESS';
    const isFuture = d.date > V.state.demoDate;
    const isDraft = ['DRAFT','CHANGES_REQUESTED'].includes(d.reportStatus);
    
    const dlItems = [['Laporan',U.esc(d.reportText)],['Kendala',U.esc(d.obstacleText||'Tidak ada')],['Bukti',d.evidence?.length ? d.evidence.map(e=>U.attachment(e)).join('') : 'Tidak ada lampiran'],['Status',`${reportBadge(d)}${d.reviewNote?'<br>Catatan: '+U.esc(d.reviewNote):''}`]];
    if (d.reportStatus !== 'DRAFT') {
      dlItems.splice(3, 0, ['Dikirim oleh', `${U.esc(d.submittedBy||'—')} pada ${U.date(d.submittedAt)}`]);
    }
    const dlContent = d.reportText ? U.dl(dlItems) : '<p class="muted">Belum ada laporan</p>';

    let content = dlContent;
    if (isFuture) {
      content = U.note(`Form laporan akan dibuka pada tanggal pelaksanaan (${U.date(d.date)}).`);
    } else if (isDraft && isLeader && active) {
      content = U.form('report',
        U.textarea('text','Laporan harian',d.reportText,'maxlength="10000" required')+
        U.textarea('obstacleText','Kendala yang dihadapi (Opsional)',d.obstacleText||'','maxlength="2000"')+
        U.upload('Bukti pelaksanaan','evidence',true)+'<label class="check"><input type="checkbox" name="sample" value="yes">Gunakan bukti simulasi</label>'+
        '<div class="actions spaced"><button type="submit" data-action="SAVE_REPORT" class="btn ">Simpan draft</button><button type="submit" data-action="SUBMIT_REPORT" class="btn primary">Kirim laporan</button></div>',
        null, {planId:p.id, dayId:d.id}
      );
    } else if (d.reportStatus === 'SUBMITTED' && isPM) {
      content = dlContent + U.form('review-report',U.select('decision','Keputusan',[['APPROVE','Setujui laporan'],['RETURN','Minta perbaikan']],'APPROVE')+U.textarea('note','Catatan (wajib jika dikembalikan)','')+
        '<div class="actions"><button type="submit" class="btn primary" data-action="REVIEW_REPORT">Simpan keputusan</button></div>',null,{planId:p.id,dayId:d.id});
    }

    return U.panel(U.date(d.date)+' · '+d.title,
      U.actions(reportBadge(d),U.link(['report',p.id,d.id],'Pratinjau laporan','small'))+
      d.tasks.map(t=>`<label class="check"><input type="checkbox" data-task="${t.id}" data-day="${d.id}" data-plan="${p.id}" ${t.done?'checked':''} ${(isLeader&&active&&!isFuture)?'':'disabled'}>${U.esc(t.title)}</label>`).join('')+
      '<div class="spaced">'+content+'</div>'
    );
  }
  function renderWeek(w, p, isLeader, isPM) {
    const active = p.status === 'IN_PROGRESS';
    const ready = w.dayIds.every(id => p.days.find(d=>d.id===id).reportStatus === 'APPROVED');
    
    let content = '';
    if (['DRAFT', 'CHANGES_REQUESTED'].includes(w.status) && isLeader && active) {
      if (!ready) {
        content = U.note('Semua laporan harian dalam minggu ini harus disetujui PM sebelum laporan mingguan dapat dibuat.');
      } else {
        const defaultText = w.reportText || w.dayIds.map(id => p.days.find(x=>x.id===id).reportText).filter(Boolean).join('\n\n');
        const defaultObs = w.obstacleText || w.dayIds.map(id => p.days.find(x=>x.id===id).obstacleText).filter(Boolean).join('\n\n');
        content = U.form('weekly-report',
          U.textarea('text','Laporan Mingguan',defaultText,'required')+
          U.textarea('obstacleText','Ringkasan Kendala Mingguan (Wajib)',defaultObs,'required')+
          '<div class="actions spaced"><button type="submit" data-action="SAVE_WEEKLY" class="btn ">Simpan draft</button><button type="submit" data-action="SUBMIT_WEEKLY" class="btn primary">Kirim laporan</button></div>',
          null, {planId:p.id, weekId:w.id}
        );
      }
    } else if (w.status === 'SUBMITTED' && isPM) {
      content = U.dl([['Laporan',U.esc(w.reportText)],['Kendala',U.esc(w.obstacleText)]]) +
        U.form('review-weekly',U.select('decision','Keputusan',[['APPROVE','Setujui laporan'],['RETURN','Minta perbaikan']],'APPROVE')+U.textarea('note','Catatan (wajib jika dikembalikan)','')+
        '<div class="actions"><button type="submit" class="btn primary" data-action="REVIEW_WEEKLY">Simpan keputusan</button></div>',null,{planId:p.id,weekId:w.id});
    } else {
      content = w.reportText ? U.dl([['Laporan',U.esc(w.reportText)],['Kendala',U.esc(w.obstacleText)],['Status', `${U.badge(w.status)}${w.reviewNote?'<br>Catatan: '+U.esc(w.reviewNote):''}`]]) : '<p class="muted">Belum ada laporan mingguan.</p>';
    }
    return U.panel(w.name, content);
  }
  function renderFinalReport(p, isLeader, isPM) {
    const readyForFinal = p.days.every(d=>d.reportStatus==='APPROVED') && (p.weeks||[]).every(w=>w.status==='APPROVED');
    const f = p.finalReport;
    
    if (p.status === 'IN_PROGRESS' && isLeader) {
      if (!readyForFinal) return '';
      const defaultText = f?.reportText || (p.weeks?.length ? p.weeks.map(w=>w.reportText).join('\n\n') : p.days.map(d=>d.reportText).join('\n\n'));
      const defaultObs = f?.obstacleText || (p.weeks?.length ? p.weeks.map(w=>w.obstacleText).join('\n\n') : p.days.map(d=>d.obstacleText).join('\n\n'));
      return U.panel('Laporan Akhir Penyelesaian Pekerjaan',
        U.note('Pekerjaan ini sudah memenuhi syarat penyelesaian. Ajukan penyelesaian ke PM untuk ditutup.')+
        U.form('final-report',
          U.textarea('reportText','Laporan Keseluruhan',defaultText,'required')+
          U.textarea('obstacleText','Ringkasan Kendala Keseluruhan (Wajib)',defaultObs,'required')+
          U.upload('Lampiran (Foto/PDF) (Opsional)', 'evidence', true),
          f?.status === 'CHANGES_REQUESTED' ? 'Kirim Revisi Laporan Akhir' : 'Kirim Laporan Akhir (Ajukan Selesai)', {planId: p.id, action: 'REQUEST_COMPLETE'}
        )
      );
    }
    
    if (f && f.status !== 'DRAFT') {
      const evidenceHtml = f.evidence?.length ? f.evidence.map((file, i) => `<div class="attachment"><span>${i+1}. ${U.esc(file.name||file)}</span><span class="actions">${file.name?U.button('attachment','Buka berkas',file,'small'):''}</span></div>`).join('') : '<p class="muted">Tidak ada lampiran.</p>';
      const sigs = p.status === 'COMPLETED' ? `<div class="signatures"><div class="signature-box"><strong>${U.esc(f.submittedBy)}</strong><small>Ketua Tim</small><small>${U.date(f.submittedAt)}</small></div><div class="signature-box"><strong>${U.esc(f.reviewedBy)}</strong><small>Project Manager</small><small>${U.date(f.reviewedAt)}</small></div></div>` : '';

      const incidents = V.state.incident_reports.filter(i => i.planId === p.id);
      const incidentHtml = incidents.length ? '<br><h3>Riwayat Insiden</h3>' + incidents.map(i => `<div class="row"><div><strong>[${U.esc(i.category)}] ${U.esc(i.severity)}</strong><small>${U.esc(i.description)}</small></div><div class="actions">${U.badge(i.status)}</div></div>`).join('') : '';

      return U.panel('Laporan Akhir Penyelesaian Pekerjaan', U.dl([
        ['Laporan Keseluruhan', U.esc(f.reportText)], 
        ['Kendala Keseluruhan', U.esc(f.obstacleText)],
        ['Lampiran', evidenceHtml],
        ['Status', `${U.badge(f.status)}${f.reviewNote?'<br>Catatan PM: '+U.esc(f.reviewNote):''}`]
      ]) + incidentHtml + sigs);
    }
    return '';
  }
  function documents(p) {
    if(!p.documents.length) return U.empty('SK belum diterbitkan','Periksa rincian harian dan lampiran, kemudian terbitkan SK dari halaman ringkasan.');
    return `<div class="stack">${p.documents.map(doc=>U.panel(doc.kind==='ADDENDUM'?'Adendum surat tugas':doc.kind==='REVISION'?'Revisi surat tugas':'Surat tugas',U.actions(U.badge(doc.status),`<small>Versi ${doc.version}</small>`)+U.dl([['Nomor',U.esc(doc.number)],['Penerbit',U.esc(doc.issuedBy)],['Diterbitkan',U.date(doc.issuedAt)],['Penerimaan',U.esc(doc.acceptedBy||'Belum diterima')]])+U.link(['document',p.id,doc.id],'Pratinjau dokumen','primary'))).join('')}</div>`;
  }
  function resources(p){
      const assets = V.state.assets.filter(a => a.planId === p.id);
      const availableTools = V.state.assets.filter(a => a.status === 'AVAILABLE' && a.kind === 'TOOL');
      const availableVehicles = V.state.assets.filter(a => a.status === 'AVAILABLE' && a.kind === 'VEHICLE');
      const canManage = p => !p.deletedAt && ['PM','OPS'].includes(V.actor.role) && ['DRAFT','PUBLISHED','ACCEPTED','APPEALED','IN_PROGRESS','COMPLETION_REVIEW'].includes(p.status);
      // Whoever the SK names as leader gets the leader actions, even if their demo identity is an ordinary member.
  const leader = p => p.leaderId === V.actor.id;
      
      let allocationForms = '';
      if (canManage(p)&&!p.deletedAt&&!['COMPLETED','CANCELLED'].includes(p.status)){
        const toolForm = availableTools.length ? U.form('reserve',U.select('assetId','Pilih peralatan',availableTools.map(a=>[a.id,a.name+' - '+a.code])),'Alokasikan Peralatan',{planId:p.id}) : '<p>Semua peralatan sedang dialokasikan.</p>';
        
        let vehicleForm = '<p>Semua kendaraan sedang dialokasikan.</p>';
        if (availableVehicles.length) {
          vehicleForm = `<form data-form="reserve"><input type="hidden" name="planId" value="${p.id}">
          <label>Pilih kendaraan<select name="assetId" required><option value="">- Pilih kendaraan -</option>
          ${availableVehicles.map(a=>`<option value="${a.id}" data-type="${a.vehicleType==='MOTORCYCLE'?'SIM C':'SIM a'}">${a.name} - ${a.code} (${a.vehicleType==='MOTORCYCLE'?'Motor':'Mobil'})</option>`).join('')}
          </select></label><div id="driver-select-container"></div>
          <div class="form-footer"><button class="btn primary" type="submit">Alokasikan Kendaraan</button></div></form>`;
          
          setTimeout(() => {
            const vehicleSelects = document.querySelectorAll('form[data-form="reserve"] select[name="assetId"]');
            vehicleSelects.forEach(sel => sel.dispatchEvent(new Event('change', {bubbles: true})));
          }, 0);
        }
        
        allocationForms = `<div class="columns spaced"><div class="stack">${U.panel('Alokasikan Kendaraan', vehicleForm)}</div><div class="stack">${U.panel('Alokasikan Peralatan', toolForm)}</div></div>`;
      }
  
      return U.panel('Aset sedang dialokasikan',assets.length?assets.map(a=>{
        const isDriver = a.driverId === V.actor.id;
        const needsCheck = a.kind === 'VEHICLE' && a.status === 'RESERVED' && !a.driverChecked;
        const checkBtn = isDriver && needsCheck ? U.button('check-asset','Periksa Kendaraan',{assetId:a.id, planId:p.id}) : '';
        const returnBtn = leader(p)&&['IN_USE','RESERVED'].includes(a.status)?U.button('return-asset','Ajukan pengembalian',{assetId:a.id}):'';
        const releaseBtn = canManage(p)&&a.status==='RESERVED'?U.command('RELEASE_ASSET','Lepas reservasi',{assetId:a.id,planId:p.id},'small'):'';
        return U.row(a.name,a.code+' - '+a.condition+(a.driver?' - Pengemudi: '+a.driver:'')+(needsCheck?' - menunggu pemeriksaan pengemudi':''),U.actions(U.badge(a.status),checkBtn,returnBtn,releaseBtn));
      }).join(''):'<p>Tidak ada sumber daya yang sedang dialokasikan.</p>')+
    allocationForms+
    (V.state.assets.some(a=>a.returnHistory?.some(h=>h.planId===p.id))?'<div class="spaced">'+U.panel('Pengembalian terverifikasi',V.state.assets.flatMap(a=>(a.returnHistory||[]).filter(h=>h.planId===p.id).map(h=>U.row(a.name,h.condition+' · '+h.verifiedBy+' · '+U.date(h.at),U.badge('VERIFIED')))).join(''))+'</div>':'');
  }
  V.forms.personnel=async(form,data)=>{data.memberIds=new FormData(form).getAll('memberIds'); if(V.run('REQUEST_PERSONNEL_CHANGE',data))V.closeDialog();};
  V.forms.plan=async(form,data)=>{data.memberIds=new FormData(form).getAll('memberIds'); if (data.planId) {if(V.run('EDIT_DRAFT',data)) V.go('plan',data.planId);} else if(V.run('CREATE_PLAN',data)) V.go('plan',V.state.plans[0].id,'days');};
  V.forms.day=async(form,data)=>{data.tasks=data.tasks.split('\n').map(x=>x.trim()).filter(Boolean).map(title=>({title})); V.run('SAVE_DAY',data);};
  V.forms.report=async(form,data,action)=>{action = action || 'SAVE_REPORT'; const p=get(data.planId),day=p.days.find(d=>d.id===data.dayId); data.evidence=[...day.evidence,...await V.uploadFiles(form)]; if(data.sample==='yes'&&!data.evidence.some(f=>f.id==='sample-evidence'))data.evidence.push({id:'sample-evidence',name:'bukti-lapangan-contoh.svg',type:'image/svg+xml'}); V.run(action,data);};
  V.forms['review-report']=async(form,data,action)=>V.run('REVIEW_REPORT',data);
  V.forms['weekly-report']=async(form,data,action)=>{action = action || 'SAVE_WEEKLY'; V.run(action,data);};
  V.forms['review-weekly']=async(form,data)=>V.run('REVIEW_WEEKLY',data);
  V.forms['final-report']=async(form,data)=>V.run('REQUEST_COMPLETE',data);
  V.forms['plan-files']=async(form,data)=>{const p=get(data.planId);const files=await V.uploadFiles(form);if(!files.length)throw Error('Pilih minimal satu lampiran.');V.run('SAVE_ATTACHMENTS',{...data,attachments:[...(p.attachments||[]),...files]});};
  V.forms.reserve=async(form,data)=>V.run('RESERVE_ASSET',data);
  V.forms['check-asset']=async(form,data)=>{ if (V.run('CHECK_ASSET',data)) V.closeDialog(); };
  V.views.plans=()=>list(V.route.args[0]||'active'); V.views.new=()=>editor(null,V.route.args[0]); V.views.edit=()=>{const p=get(V.route.args[0]);return p?editor(p):U.empty('Pekerjaan tidak tersedia','Pekerjaan ini tidak ditemukan atau tidak dalam lingkup Anda.',U.link(['plans'],'Kembali'));}; V.views.plan=()=>detail(...V.route.args);
  V.views.presentation = () => {
    const p = get(V.route.args[0]);
    if (!p || p.status !== 'COMPLETED') return U.empty('Pekerjaan tidak tersedia', 'Hanya pekerjaan yang sudah selesai yang dapat dipresentasikan.', U.link(['plans'], 'Kembali'));
    const f = p.finalReport;
    
    const css = `
      <style>
        .side, .topbar, .mobile-header, .mobile-nav, .mobile-caption, .mobile-context, .skip, #notifications { display: none !important; }
        .desktop-shell, .mobile-shell, .mobile-surround { margin: 0 !important; padding: 0 !important; border: 0 !important; max-width: none !important; box-shadow: none !important; }
        main { padding: 0 !important; max-width: none !important; }
        .slide-deck { height: 100vh; overflow-y: scroll; scroll-snap-type: y mAndatory; background: #222; font-family: 'Segoe UI', arial, sans-serif; color: #333; }
        .slide { height: 100vh; width: 100%; scroll-snap-align: start; display: flex; flex-direction: column; justify-content: center; align-items: center; background: white; border-bottom: 2px solid #ccc; position: relative; }
        .slide-content { max-width: 900px; width: 90%; padding: 40px; }
        .slide h1 { font-size: 48px; color: #164d40; margin-bottom: 20px; letter-spacing: -1px; }
        .slide h2 { font-size: 32px; color: #444; margin-bottom: 20px; border-bottom: 2px solid #164d40; padding-bottom: 10px; }
        .slide p, .slide li { font-size: 24px; line-height: 1.6; }
        .slide-footer { position: absolute; bottom: 20px; right: 40px; font-size: 14px; color: #888; }
        .slide-logo { position: absolute; top: 40px; left: 40px; font-weight: 800; font-size: 24px; color: #164d40; letter-spacing: 2px; }
        .deck-controls { position: fixed; top: 20px; right: 20px; z-index: 1000; display: flex; gap: 10px; }
        @media print {
          @page { size: landscape; margin: 0; }
          .slide-deck { height: auto; overflow: visible; background: white; }
          .slide { height: 100vh; page-break-after: always; border: 0; }
          .deck-controls { display: none; }
        }
      </style>
    `;
    
      const incidents = V.state.incident_reports.filter(i => i.planId === p.id);
      
      const slides = [
        `<div class="slide"><div class="slide-logo">VISIONTECH</div><div class="slide-content" style="text-align: center;">
            <h1>Laporan Penyelesaian Pekerjaan</h1>
            <p style="font-size: 28px; color: #666; margin-bottom: 40px;">${U.esc(p.title)}</p>
            <div style="font-size: 20px; color: #888;">
              <p><strong>Nomor:</strong> ${U.esc(p.number)}</p>
              <p><strong>Lokasi:</strong> ${U.esc(p.location)}</p>
              <p><strong>Periode:</strong> ${U.date(p.startDate)} - ${U.date(p.endDate)}</p>
            </div>
          </div></div>`,
        `<div class="slide"><div class="slide-logo">VISIONTECH</div><div class="slide-content">
            <h2>Tim & Sumber Daya</h2>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 40px; margin-top: 40px;">
              <div>
                <p style="font-weight: 700; color: #164d40;">Personel</p>
                <ul style="margin-top: 20px;">
                  <li><strong>PM:</strong> ${U.esc(U.person(p.pmId))}</li>
                  <li><strong>Ketua:</strong> ${U.esc(U.person(p.leaderId))}</li>
                  <li><strong>Anggota:</strong> ${p.memberIds.map(id=>U.esc(U.person(id))).join(', ')}</li>
                </ul>
              </div>
              <div>
                <p style="font-weight: 700; color: #164d40;">Aset yang Digunakan</p>
                <ul style="margin-top: 20px;">
                    ${(() => {
                      const used = V.state.assets.filter(a => a.planId === p.id || (a.returnHistory && a.returnHistory.some(h => h.planId === p.id)));
                      return used.length ? used.map(a => {
                        const ret = a.returnHistory?.slice().reverse().find(h => h.planId === p.id);
                        const cond = ret ? ` - Dikembalikan: ${U.esc(ret.condition)}` : '';
                        const driver = a.kind === 'VEHICLE' ? ` - Pengemudi: ${U.esc(a.driver || ret?.driver || 'Tidak diketahui')}` : '';
                        return `<li>${U.esc(a.name)} (${U.esc(a.code)})${driver}${cond}</li>`;
                      }).join('') : '<li>Tidak ada aset</li>';
                    })()}
                </ul>
              </div>
            </div>
          </div></div>`,
        `<div class="slide"><div class="slide-logo">VISIONTECH</div><div class="slide-content">
            <h2>Hasil Pelaksanaan</h2>
            <div style="margin-top: 30px;">
              <p style="font-weight: 700; color: #164d40;">Ringkasan Laporan:</p>
              <p style="margin-top: 10px; font-size: 20px; white-space: pre-wrap;">${U.esc(f.reportText)}</p>
            </div>
            <div style="margin-top: 40px;">
              <p style="font-weight: 700; color: #164d40;">Kendala Dihadapi:</p>
              <p style="margin-top: 10px; font-size: 20px; white-space: pre-wrap;">${U.esc(f.obstacleText)}</p>
            </div>
          </div></div>`,
        ...(incidents.length ? [`<div class="slide"><div class="slide-logo">VISIONTECH</div><div class="slide-content">
            <h2>Riwayat Insiden / HSE</h2>
            <ul style="margin-top: 30px;">
              ${incidents.map(i => `<li style="margin-bottom: 20px;"><strong>[${U.esc(i.category)}] ${U.esc(i.severity)}</strong> - ${U.esc(i.description)}<br><span style="font-size: 16px; color: #888;">${U.esc(U.person(i.employeeId))} · ${U.date(i.date)}</span></li>`).join('')}
            </ul>
          </div></div>`] : []),
        `<div class="slide"><div class="slide-logo">VISIONTECH</div><div class="slide-content">
            <h2>Lampiran Pendukung</h2>
            <ul style="margin-top: 30px;">
              ${(f.evidence||[]).map(file => `<li>${U.esc(file.name||file)}</li>`).join('') || '<p>Tidak ada lampiran.</p>'}
            </ul>
          </div></div>`,
        `<div class="slide"><div class="slide-logo">VISIONTECH</div><div class="slide-content">
            <h2>Pengesahan</h2>
            <p style="text-align: center; margin: 40px 0; font-size: 20px;">Pekerjaan ini telah diselesaikan, seluruh syarat terpenuhi, dan secara resmi ditutup pada sistem simulasi.</p>
            <div style="display: flex; justify-content: space-around; margin-top: 80px; text-align: center;">
              <div>
                <p style="font-size: 16px; color: #666; margin-bottom: 60px;">Ketua Tim Pelaksana</p>
                <p style="font-weight: 700; font-size: 24px; text-decoration: underline;">${U.esc(f.submittedBy||U.person(p.leaderId))}</p>
                <p style="font-size: 16px; margin-top: 10px;">${f.submittedAt?U.date(f.submittedAt):'Penyelesaian disetujui'}</p>
              </div>
              <div>
                <p style="font-size: 16px; color: #666; margin-bottom: 60px;">Project Manager</p>
                <p style="font-weight: 700; font-size: 24px; text-decoration: underline;">${U.esc(f.reviewedBy||U.person(p.pmId))}</p>
                <p style="font-size: 16px; margin-top: 10px;">${f.reviewedAt?U.date(f.reviewedAt):'Penutupan disetujui'}</p>
              </div>
            </div>
          </div></div>`
      ];

      return css + `
        <div class="deck-controls">
          <button class="btn primary" onclick="window.print()">Simpan PDF (Landscape)</button>
          <a class="btn" href="${U.href('plan', p.id, 'overview')}">Tutup Presentasi</a>
        </div>
        <div class="slide-deck">
          ${slides.map((html, i) => html.replace('</div></div>', `</div><div class="slide-footer">${i+1} / ${slides.length}</div></div>`)).join('')}
        </div>
      `;
    };

  V.work={plans,get,card,progress,canManage,leader};
})();
