(() => {
  const V=VT,U=VTUI;
  function attendance(){
    const finance=V.actor.role==='FINANCE';
    const canAll=['FINANCE','HR','OPS'].includes(V.actor.role);
    const items=V.state.attendance.filter(a=>canAll||a.employeeId===V.actor.id);
    const own=V.state.attendance.find(a=>a.employeeId===V.actor.id&&!a.checkOut&&a.status!=='REJECTED');
    const currentEmployee=V.state.employees.find(e=>e.id===V.actor.id);
    const buttons=currentEmployee?own?U.button('check-out','Catat keluar',{attendanceId:own.id},'primary'):U.button('check-in','Catat masuk',{},'primary'):'';
    const reviewRow=a=>a.status==='AUTO_VALID'?'Tidak perlu ditinjau · jarak dalam radius'
      :a.reviewNote?U.esc(a.reviewNote)+(a.status==='APPROVED'?' (disetujui)':a.status==='REJECTED'?' (ditolak)':'')
      :'Menunggu pemeriksaan Finance';
    const body=items.map(a=>{
      const extras=U.actions(a.employeeId===V.actor.id&&a.status==='NEEDS_REVIEW'?U.button('explain-attendance','Beri penjelasan',{attendanceId:a.id}):'',finance&&a.status==='NEEDS_REVIEW'?U.button('review-attendance','Tinjau',{attendanceId:a.id},'primary'):'');
      return `<article class="card" data-search-item="${U.esc((U.person(a.employeeId)+' '+a.site).toLowerCase())}" data-status="${a.status}"><div class="section-head"><div class="person-name">${U.avatar(U.person(a.employeeId))}<div><h3>${U.esc(U.person(a.employeeId))}</h3><small>${U.date(a.date)} · ${U.esc(a.site)}</small></div></div>${U.badge(a.status)}</div>${U.dl([['Masuk / keluar',U.clock(a.checkIn)+' / '+(a.checkOut?U.clock(a.checkOut):'belum keluar')+' WIB'],['Sumber',a.source==='MOBILE'?(a.coords?.origin==='GPS'?'HP · GPS perangkat':'HP · lokasi simulasi'):'Mesin · data simulasi'],['Jarak / radius',a.distance+' m / '+a.radius+' m'],...(a.coords?[['Koordinat',`${a.coords.lat.toFixed(5)}, ${a.coords.lng.toFixed(5)}`]]:[]),...(a.selfie?[['Swafoto',U.attachment(a.selfie)]]:[]),['Penjelasan',U.esc(a.explanation||'—')],['Hasil pemeriksaan',reviewRow(a)]])}${extras}</article>`;
    }).join('');
    const counts=s=>items.filter(a=>a.status===s).length;
    // Filter status tersedia untuk semua peran; Finance mendapat opsi "Perlu review"
    const filterOptions=canAll
      ?`<option value="">Semua status (${items.length})</option><option value="NEEDS_REVIEW">Perlu review (${counts('NEEDS_REVIEW')})</option><option value="AUTO_VALID">Valid otomatis (${counts('AUTO_VALID')})</option><option value="APPROVED">Sudah disetujui (${counts('APPROVED')})</option><option value="REJECTED">Ditolak (${counts('REJECTED')})</option>`
      :`<option value="">Semua catatan (${items.length})</option><option value="AUTO_VALID">Valid otomatis (${counts('AUTO_VALID')})</option><option value="NEEDS_REVIEW">Perlu review (${counts('NEEDS_REVIEW')})</option><option value="APPROVED">Disetujui (${counts('APPROVED')})</option><option value="REJECTED">Ditolak (${counts('REJECTED')})</option>`;
    const toolbar=`<div class="toolbar"><input class="search" type="search" aria-label="Cari nama atau lokasi" placeholder="Cari nama atau lokasi…" data-search><select aria-label="Saring status kehadiran" data-filter>${filterOptions}</select></div>`;
    return U.heading(finance?'Peninjauan absensi':'Absensi',canAll?'Rekap kehadiran dan catatan pemeriksaan.':'Kehadiran dan penjelasan Anda.',buttons)+toolbar+`<div class="grid">${body}</div><p class="muted spaced hidden" id="no-results">Tidak ada kehadiran yang cocok.</p>`+(items.length?'':U.empty('Belum ada absensi'))+`<div class="spaced">${U.note(`Jam masuk/keluar mengikuti tanggal simulasi. Jarak dihitung dengan rumus Haversine dari GPS perangkat (bila diizinkan) atau koordinat simulasi; di luar radius ${V.D.attendanceRadius||100} m wajib swafoto. Tidak ada biometrik atau koneksi mesin nyata.`)}</div>`;
  }
  function assets(){
    const all=['ASSET','OPS'].includes(V.actor.role),ids=V.work.plans().map(p=>p.id);
    const items=V.state.assets.filter(a=>all||a.status==='AVAILABLE'||ids.includes(a.planId));
    const counts=s=>items.filter(a=>a.status===s).length;
    const toolbar=`<div class="toolbar"><input class="search" type="search" aria-label="Cari nama atau kode aset" placeholder="Cari nama atau kode…" data-search><select aria-label="Saring status aset" data-filter><option value="">Semua (${items.length})</option><option value="AVAILABLE">Tersedia (${counts('AVAILABLE')})</option><option value="RESERVED">Direservasi (${counts('RESERVED')})</option><option value="IN_USE">Dipakai (${counts('IN_USE')})</option><option value="RETURN_PENDING">Menunggu pemeriksaan (${counts('RETURN_PENDING')})</option></select></div>`;
    return U.heading('Kendaraan & alat','Alokasi, pemeriksaan kondisi, dan riwayat pengembalian.')+toolbar+`<div class="grid ${V.route.device==='desktop'?'three':''}">${items.map(a=>{
      const p=V.state.plans.find(p=>p.id===a.planId);
      const canReturn=a.planId&&['IN_USE','RESERVED'].includes(a.status)&&(V.actor.role==='LEADER'&&p?.leaderId===V.actor.id);
      const canReserve=V.D.can(V.actor,'RESERVE_ASSET')&&a.status==='AVAILABLE';
      // Baris pengemudi hanya untuk kendaraan (VEHICLE), bukan peralatan
      const driverRow=a.kind==='VEHICLE'?[['Pengemudi',a.driver?U.esc(a.driver)+(a.driverChecked?' · kendaraan sudah diperiksa':' · menunggu pemeriksaan pengemudi'):'Belum ditunjuk']]:[];
      return `<article class="card" data-search-item="${U.esc((a.name+' '+a.code).toLowerCase())}" data-status="${a.status}"><div class="section-head"><span class="eyebrow">${a.kind==='VEHICLE'?'KENDARAAN':'PERALATAN'}</span>${U.badge(a.status)}</div><h2>${U.esc(a.name)}</h2>${U.dl([['Kode',U.esc(a.code)],['Kondisi',U.esc(a.condition)],['Penugasan',p?`<a href="${U.href('plan',p.id,'resources')}">${U.esc(p.title)}</a>`:'Belum dialokasikan'],...driverRow])}${U.actions(canReserve?U.button('reserve-asset','Alokasikan',{assetId:a.id}):'',canReturn?U.button('return-asset','Ajukan pengembalian',{assetId:a.id}):'',V.actor.role==='ASSET'&&a.status==='RETURN_PENDING'?U.button('verify-return','Periksa pengembalian',{assetId:a.id},'primary'):'',a.status==='RESERVED'&&['ASSET','PM','OPS'].includes(V.actor.role)?U.command('RELEASE_ASSET','Lepas reservasi',{assetId:a.id,planId:p.id}):'')}${a.returnNote?'<div class="spaced">'+U.note('Catatan pengembali: '+a.returnNote)+'</div>':''}${a.returnHistory?.length?`<details class="spaced"><summary>Riwayat pengembalian (${a.returnHistory.length})</summary>${a.returnHistory.map(h=>U.row(U.date(h.at)+' · '+h.verifiedBy,h.condition+' · '+(h.note||'Tidak ada catatan'))).join('')}</details>`:''}</article>`;
    }).join('')}</div><p class="muted spaced hidden" id="no-results">Tidak ada aset yang cocok.</p>`;
  }
  function audit(){
    const ids=V.work.plans(true).map(p=>p.id);
    const items=V.state.audit.filter(e=>V.actor.role==='OPS'||e.actorId===V.actor.id||e.planId&&ids.includes(e.planId));
    return U.heading('Jejak aktivitas','Peristiwa yang benar-benar terjadi pada data simulasi.')+(items.length?U.panel('Riwayat terbaru',items.map(e=>`<div class="event"><small>${U.date(e.at)} · ${U.clock(e.at)} WIB</small><strong>${U.esc(e.actor)} · ${U.esc(V.actionNames[e.action]||e.action)}</strong><p>${U.esc(e.entity)}</p><small>${U.esc(e.detail)}</small></div>`).join('')):U.empty('Belum ada aktivitas','Tindakan Anda akan tercatat di sini.'));
  }
  function timeline(){
    const today=V.state.demoDate;
    const plans=V.work.plans().filter(p=>!['CANCELLED','COMPLETED'].includes(p.status)).sort((a,b)=>a.startDate.localeCompare(b.startDate));
    const dayState=d=>d.reportStatus==='APPROVED'?['Selesai & disetujui','green']:d.reportStatus==='SUBMITTED'?['Menunggu review PM','amber']:d.reportStatus==='CHANGES_REQUESTED'?['Perlu perbaikan','red']:d.date<today?['Laporan belum dikirim','red']:d.date===today?['Dikerjakan hari ini','blue']:['Belum mulai',''];
    const sections=plans.map(p=>{
      const done=p.days.filter(d=>d.reportStatus==='APPROVED').length;
      const late=p.days.filter(d=>d.date<today&&d.reportStatus!=='APPROVED').length;
      const rows=p.days.map(d=>{const [label,tone]=dayState(d);return `<div class="row"><div><strong>${U.date(d.date)}${d.date===today?' · hari ini':''}</strong><small>${U.esc(d.title)}</small></div><div class="actions"><span class="badge ${tone}">${U.esc(label)}</span><a class="btn small" href="${U.href('report',p.id,d.id)}">Lihat</a></div></div>`;}).join('');
      return U.panel(p.title,`<div class="actions">${U.badge(p.status)}<span class="muted">${U.esc(U.unit(p.unit))} · ${U.esc(p.location)}</span></div>`+
        U.dl([['Periode',U.date(p.startDate)+' – '+U.date(p.endDate)],['Ketua tim',U.esc(U.person(p.leaderId))],['Kemajuan',`${done} dari ${p.days.length} hari disetujui${late?` · <strong>${late} hari terlambat</strong>`:''}`]])+
        `<div class="progress"><span style="width:${p.days.length?Math.round(done/p.days.length*100):0}%"></span></div>`+
        rows+U.actions(U.link(['plan',p.id,'days'],'Buka rincian & laporan','small'),U.link(['plan',p.id],'Ringkasan pekerjaan','small')));
    }).join('');
    return U.heading('Timeline tim','Jadwal per pekerjaan, mengikuti versi SK yang berlaku. Tanggal acuan: '+U.date(today)+'.')+
      (plans.length?sections:U.empty('Belum ada pekerjaan berjalan','Pekerjaan yang sudah diterima atau sedang berjalan akan muncul di sini.'));
  }
  V.forms['explain-attendance']=async(form,data)=>{if(V.run('EXPLAIN_ATTENDANCE',data))V.closeDialog();};
  V.forms['review-attendance']=async(form,data)=>{if(V.run('REVIEW_ATTENDANCE',data))V.closeDialog();};
  V.forms['return-asset']=async(form,data)=>{if(V.run('RETURN_ASSET',data))V.closeDialog();};
  V.forms['verify-return']=async(form,data)=>{if(V.run('VERIFY_RETURN',data))V.closeDialog();};
  V.forms['reserve-asset']=async(form,data)=>{if(V.run('RESERVE_ASSET',data))V.closeDialog();};
  function overtime(){
    const month=(V.state.demoDate||'').slice(0,7);
    const visible=new Set(V.work.plans().map(p=>p.id));
    const all=V.state.overtime_logs.filter(o=>['FINANCE','OPS'].includes(V.actor.role)||visible.has(o.planId));
    const items=all.filter(o=>o.date.startsWith(month));
    const byEmployee=new Map();
    items.forEach(o=>{ const list=byEmployee.get(o.employeeId)||[]; list.push(o); byEmployee.set(o.employeeId,list); });
    const hours=list=>list.filter(o=>o.status==='APPROVED').reduce((sum,o)=>sum+Number(o.hours||0),0);
    const monthName=new Intl.DateTimeFormat('id-ID',{month:'long',year:'numeric',timeZone:'Asia/Jakarta'}).format(new Date(month+'-01T12:00:00+07:00'));
    const totalApproved=hours(items), pending=items.filter(o=>o.status==='PENDING_PM').length;
    const planTitle=id=>{const p=V.state.plans.find(p=>p.id===id);return p?p.title:'Pekerjaan tidak tersedia';};
    const cards=[...byEmployee.entries()].sort((a,b)=>hours(b[1])-hours(a[1])).map(([employeeId,list])=>{
      const rows=list.sort((a,b)=>b.date.localeCompare(a.date)).map(o=>{
        const canReview=o.status==='PENDING_PM'&&V.D.can(V.actor,'REVIEW_OVERTIME',V.state.plans.find(p=>p.id===o.planId)?.unit)&&o.employeeId!==V.actor.id;
        // Tampilkan: jam · tanggal · nama pekerjaan · alasan, agar konteks jelas sebelum tinjau
        return `<div class="row"><div><strong>${o.hours} jam · ${U.date(o.date)}</strong><small>${U.esc(planTitle(o.planId))}</small><small>${U.esc(o.reason)}</small><small>${o.reviewedBy?'Ditinjau '+U.esc(o.reviewedBy)+(o.note?' · '+U.esc(o.note):''):'Belum ditinjau'}</small></div><div class="actions">${U.badge(o.status)}${canReview?U.button('review-overtime','Tinjau lembur',{overtimeId:o.id},'small primary'):''}</div></div>`;
      }).join('');
      return U.panel(U.person(employeeId),U.dl([['Total jam disetujui',`<strong>${hours(list)} jam</strong>`],['Pengajuan bulan ini',`${list.length} pengajuan · ${list.filter(o=>o.status==='PENDING_PM').length} menunggu persetujuan`]])+rows);
    }).join('');
    return U.heading('Rekap lembur',`Periode ${monthName}, mengikuti tanggal simulasi. Jam yang disetujui menjadi dasar perhitungan penggajian.`)+
      `<div class="stats"><article class="card stat"><span>Total jam disetujui</span><strong>${String(totalApproved).padStart(2,'0')}</strong><small>Seluruh karyawan bulan ini</small></article><article class="card stat"><span>Menunggu persetujuan</span><strong>${String(pending).padStart(2,'0')}</strong><small>Perlu keputusan PM</small></article><article class="card stat"><span>Karyawan</span><strong>${String(byEmployee.size).padStart(2,'0')}</strong><small>Mengajukan lembur</small></article></div>`+
      (items.length?cards:U.empty('Belum ada lembur pada periode ini','Pengajuan lembur dari ketua tim akan muncul di sini setelah dicatat.'))+
      `<div class="spaced">${U.note('Rekap ini hanya menghitung lembur berstatus disetujui. Tidak ada perhitungan upah, pajak, atau integrasi penggajian pada prototipe ini.')}</div>`;
  }
  V.views.attendance=attendance; V.views.assets=assets; V.views.audit=audit; V.views.timeline=timeline; V.views.overtime=overtime;
})();
