import { pathToFileURL } from 'node:url';
import { resolve, join } from 'node:path';
import { tmpdir } from 'node:os';
import { existsSync, mkdirSync, writeFileSync, readFileSync } from 'node:fs';
import assert from 'node:assert/strict';

// Optional developer tooling, kept outside the prototype: no npm/runtime dependency.
const modulePath=process.env.PLAYWRIGHT_MODULE || join(tmpdir(),'visiontech-native-checks/playwright-core/index.mjs');
if(!existsSync(modulePath))throw Error('Set PLAYWRIGHT_MODULE to an existing Playwright index.mjs to run this optional check.');
const {chromium}=await import(pathToFileURL(modulePath).href);
const chrome=process.env.CHROME_PATH || 'C:/Users/ageng/.cache/puppeteer/chrome/win64-153.0.8010.36/chrome-win64/chrome.exe';
const browser=await chromium.launch({headless:true,...(existsSync(chrome)?{executablePath:chrome}:{})});
const context=await browser.newContext({viewport:{width:1440,height:1000}});
const page=await context.newPage();
page.setDefaultTimeout(8000);
page.on('console', msg => console.log('BROWSER CONSOLE:', msg.text()));
page.on('pageerror', err => console.log('BROWSER ERROR:', err.message));
const errors=[];
page.on('pageerror',e=>errors.push(e.message));
page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
page.on('dialog',d=>{
  errors.push('Native dialog (B5) dipanggil: ' + d.message());
  d.dismiss();
});
const url=pathToFileURL(resolve('index.html')).href;
try{
  await page.goto(url);
  const state=async()=>await page.evaluate(()=>VTStorage.load());
  const click=async name=>await page.getByRole('button',{name,exact:true}).click();
  const go=async (actor,view='',device='desktop')=>{
    await page.goto(url+`#/${device}/${actor}/${view}`);
    await page.locator('nav').first().waitFor();
  };
  const out=join(tmpdir(),'visiontech-native-checks','results');
  mkdirSync(out,{recursive:true});
  await page.screenshot({path:join(out,'launcher.png'),fullPage:true});
  const actors=await page.evaluate(()=>VTDomain.actors);
  let screenCount=0;
  for(const device of ['desktop','mobile']){
    await page.setViewportSize({width:device==='mobile'?390:1440,height:1000});
    for(const actor of actors){
      await go(actor.id,'home',device);
      const menu=await page.evaluate(()=>VT.menu());
      for(const view of [...menu,'more','settings']){
        await go(actor.id,view,device);
        assert.equal(await page.locator('#content h1').count(),1,`${actor.id}/${view} heading`);
        assert(!(await page.getByText('Halaman belum dapat dimuat',{exact:true}).count()),`${actor.id}/${view} render`);
        assert(!(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1)),`${device}/${actor.id}/${view} overflow`);
        screenCount++;
      }
    }
  }
  await go('leader','home','mobile');
  await page.evaluate(() => VT.notify('Test toast mobile'));
  const toastBox = await page.locator('#notifications').boundingBox();
  const navBox = await page.locator('.mobile-nav').boundingBox();
  if (toastBox && navBox) {
    if (toastBox.y + toastBox.height > navBox.y && toastBox.y < navBox.y + navBox.height) {
      throw new Error(`R5 Failed: Toast (y=${toastBox.y}, h=${toastBox.height}) overlaps mobile-nav (y=${navBox.y}, h=${navBox.height})`);
    }
  }
  await page.screenshot({path:join(out,'leader-mobile.png'),fullPage:true});
  await page.setViewportSize({width:1440,height:1000});
  await go('pm-cctv');await page.screenshot({path:join(out,'pm-desktop.png'),fullPage:true});
  await go('member','people');await page.getByRole('heading',{name:'Halaman tidak tersedia',exact:true}).waitFor();
  await go('pm-wall','plan/wp-001');await page.getByRole('heading',{name:'Pekerjaan tidak tersedia',exact:true}).waitFor();
  await go('member','employee-document/leader/doc-leader');await page.getByRole('heading',{name:'Dokumen tidak tersedia',exact:true}).waitFor();
  await go('leader','plan/wp-001');
  await go('pm-cctv','plan/wp-002');await click('Terbitkan SK');
  let p=(await state()).plans.find(p=>p.id==='wp-002');assert.equal(p.status,'PUBLISHED');assert.equal(p.documents.at(-1).status,'AWAITING_ACCEPTANCE');
  await go('leader','plan/wp-002');await page.getByRole('link', { name: 'Buka & Tinjau SK' }).click();await click('Terima SK');await go('leader','plan/wp-002');assert(await page.getByRole('button',{name:'Mulai pelaksanaan',exact:true}).isDisabled());
  await go('leader','settings');await page.getByLabel('Tanggal simulasi',{exact:true}).fill('2026-10-05');await click('Simpan tanggal');
  await go('leader','plan/wp-002');await click('Mulai pelaksanaan');
  assert.equal((await state()).plans.find(p=>p.id==='wp-002').status,'IN_PROGRESS');

  await go('leader','plan/wp-001');await click('Ajukan perpanjangan');await page.getByLabel('Usulan tanggal selesai').fill('2026-09-24');await page.getByLabel('Alasan perpanjangan').fill('Tambahan pengujian integrasi dengan pelanggan.');await click('Kirim usulan');
  await go('pm-cctv','approvals');await page.getByText('Usulan perpanjangan',{exact:true}).waitFor();
  await go('pm-cctv','plan/wp-001');await click('Setujui perpanjangan');
  p=(await state()).plans.find(p=>p.id==='wp-001');assert.equal(p.endDate,'2026-09-23');assert.equal(p.documents.at(-1).status,'AWAITING_ACCEPTANCE');
  await go('leader','plan/wp-001');await page.getByRole('link', { name: 'Buka & Tinjau Adendum' }).click();await click('Terima adendum final');
  p=(await state()).plans.find(p=>p.id==='wp-001');assert.equal(p.endDate,'2026-09-24');
  await go('leader',`document/wp-001/${p.documents.at(-1).id}`);
  await page.getByRole('heading',{name:'ADENDUM SURAT TUGAS',exact:true}).waitFor();
  assert.equal(await page.locator('.document-paper tbody tr').count(),10); // 4 people + 4 days + 2 assets
  await page.screenshot({path:join(out,'adendum-desktop.png'),fullPage:true});
  await page.getByLabel('Pilih versi dokumen').selectOption({index:0});
  await page.getByRole('heading',{name:'SURAT TUGAS',exact:true}).waitFor();
  await page.goBack();await page.getByRole('heading',{name:'ADENDUM SURAT TUGAS',exact:true}).waitFor();
  await page.setViewportSize({width:390,height:844});await go('leader',`document/wp-001/${p.documents.at(-1).id}`,'mobile');
  assert(!(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1)));
  await page.screenshot({path:join(out,'adendum-mobile.png'),fullPage:true});
  await page.getByLabel('Pembesaran dokumen').selectOption('1.5');assert(await page.locator('.paper-stage').evaluate(el=>el.scrollWidth>el.clientWidth));
  await page.setViewportSize({width:1440,height:1000});
  
  // Test R8: Toggle task without typing -> V.dirty is false, can navigate
  await go('leader','plan/wp-001/days');
  const d0 = p.days[0].id;
  await page.locator(`.panel`).filter({has:page.locator(`[data-day="${d0}"]`)}).locator('input[data-task]').first().check();
  await page.locator('nav a[href="#/desktop/leader/home"]').click();
  await page.getByRole('heading', {name: /Halo/}).waitFor(); // successfully navigated
  
  // Test R8.2 & R9: Type in one form, dirty becomes true -> app dialog prevents navigation
  await go('leader','plan/wp-001/days');
  await page.locator(`.panel`).filter({has:page.locator(`[data-day="${d0}"]`)}).getByLabel('Laporan harian',{exact:true}).fill('Dirty text');
  
  // R9: Click menu, cancel dialog, should remain dirty
  await page.locator('nav a[href="#/desktop/leader/home"]').click();
  await page.getByRole('heading', {name: 'Tinggalkan Halaman'}).waitFor();
  await page.getByRole('button', {name: 'Batal'}).click(); // stay-page
  
  // R9: Click menu again, dialog should appear again because it's still dirty
  await page.locator('nav a[href="#/desktop/leader/home"]').click();
  await page.getByRole('heading', {name: 'Tinggalkan Halaman'}).waitFor();
  await page.getByRole('button', {name: 'Tinggalkan halaman'}).click(); // Proceed
  await page.getByRole('heading', {name: /Halo/}).waitFor(); // successfully navigated

  for(const day of p.days){
    await go('leader','plan/wp-001/days');
    const section=page.locator('.panel').filter({has:page.locator(`[data-day="${day.id}"]`)});
    const tasks=section.locator('input[data-task]');
    await section.getByLabel('Laporan harian',{exact:true}).fill('Pekerjaan selesai dan hasil pengujian sesuai spesifikasi.');
    for(let i=0;i<await tasks.count();i++)if(!await tasks.nth(i).isChecked())await tasks.nth(i).check();
    assert.equal(await section.getByLabel('Laporan harian',{exact:true}).inputValue(), 'Pekerjaan selesai dan hasil pengujian sesuai spesifikasi.');
    await section.getByLabel('Gunakan bukti simulasi').check();
    await section.getByRole('button',{name:'Simpan draft',exact:true}).click();
    await section.getByRole('button',{name:'Kirim laporan',exact:true}).click();
    await go('pm-cctv','plan/wp-001/days');
    const review=page.locator(`form[data-form="review-report"]`).filter({has:page.locator(`input[name="dayId"][value="${day.id}"]`)});
    
    // Test B6: PM can see report content before reviewing
    const dl = review.locator('..').locator('dl');
    assert.ok(await dl.getByText('Pekerjaan selesai dan hasil pengujian sesuai spesifikasi.').isVisible());

    const toast = page.locator('.toast.error');
    if (await toast.isVisible({timeout: 1000})) {
      throw new Error(`Error toast: ${await toast.textContent()}`);
    }
    const isVisible = await review.getByRole('button',{name:'Simpan keputusan',exact:true}).isVisible();
    await review.getByRole('button',{name:'Simpan keputusan',exact:true}).click();
  }
  await go('leader','plan/wp-001');
  const isVisible = await page.getByRole('link', { name: 'Buat Laporan Akhir' }).isVisible();
  if (!isVisible) {
    console.log('DOM DUMP FINAL:', await page.content());
  }
  await page.getByRole('link', { name: 'Buat Laporan Akhir' }).click();
  await page.getByLabel('Ringkasan Kendala Keseluruhan (Wajib)').fill('Tidak ada kendala.');
  await page.getByRole('button', { name: 'Kirim Laporan Akhir (Ajukan Selesai)' }).click();
  await page.waitForTimeout(500);
  await go('pm-cctv','plan/wp-001');
  assert.equal((await state()).plans.find(p=>p.id==='wp-001').status,'COMPLETION_REVIEW');
  assert(await page.getByRole('button',{name:'Setujui penyelesaian',exact:true}).isDisabled(), 'closure waits for verified asset returns');
  for(let i=0;i<2;i++){
    await go('leader','plan/wp-001/resources');await page.getByRole('button',{name:'Ajukan pengembalian',exact:true}).first().click();await page.getByLabel('Catatan kondisi & kelengkapan').fill('Alat lengkap dan kondisi baik.');await page.locator('dialog').getByRole('button',{name:'Ajukan pengembalian',exact:true}).click();
  }
  for(let i=0;i<2;i++){
    await go('asset','assets');await page.getByRole('button',{name:'Periksa pengembalian',exact:true}).first().click();await page.getByLabel('Catatan pemeriksaan').fill('Kelengkapan dan kondisi sudah diperiksa.');await click('Verifikasi kembali');
  }
  await go('pm-cctv','plan/wp-001');
  await click('Setujui penyelesaian');
  await page.waitForTimeout(500);
  assert.equal((await state()).plans.find(p=>p.id==='wp-001').status,'COMPLETED');
  await page.reload();assert.equal((await state()).plans.find(p=>p.id==='wp-001').status,'COMPLETED');

  await go('member','profile');await click('+ Ajukan dokumen');await page.getByLabel('Jenis dokumen').selectOption('SIM A');await page.getByLabel('Nomor dokumen',{exact:true}).fill('SIM-DEMO-5678');await page.getByLabel('Berlaku sampai (opsional)').fill('2028-10-01');
  await page.getByLabel('Berkas dokumen').setInputFiles({name:'lampiran-uji.svg',mimeType:'image/svg+xml',buffer:Buffer.from('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="green"/></svg>')});
  await click('Ajukan verifikasi');
  await page.locator('dialog').waitFor({state:'hidden'});
  let doc=(await state()).employees.find(e=>e.id==='member').documents.at(-1);assert.equal(doc.status,'PENDING');
  await go('hr',`employee-document/member/${doc.id}`);await page.getByRole('link',{name:'Unduh berkas',exact:true}).waitFor();await page.getByLabel('Catatan pemeriksaan').fill('Berkas dan identitas sesuai.');await click('Simpan keputusan');
  doc=(await state()).employees.find(e=>e.id==='member').documents.at(-1);assert.equal(doc.status,'VERIFIED');
  await go('member',`employee-document/member/${doc.id}`,'mobile');await page.getByRole('link',{name:'Unduh berkas',exact:true}).waitFor();
  await go('member','profile');await page.getByRole('link',{name:'Pratinjau',exact:true}).first().click();await page.locator('.preview-image').waitFor();assert(await page.locator('.preview-image').evaluate(el=>el.naturalWidth>0));
  await go('finance','attendance');await page.getByRole('button',{name:'Tinjau',exact:true}).click();await page.getByLabel('Catatan pemeriksaan').fill('Perubahan gerbang dikonfirmasi ketua tim.');await click('Simpan keputusan');assert.equal((await state()).attendance.find(a=>a.id==='att-001').status,'APPROVED');
  await go('hr','employee/emp-007');await click('Ubah penempatan');await page.getByLabel('Jabatan baru').fill('Senior Technician');await click('Simpan penempatan');assert.equal((await state()).employees.find(e=>e.id==='emp-007').position,'Senior Technician');
  await click('Offboarding');await page.getByLabel('Alasan / catatan').fill('Masa kerja selesai.');await click('Konfirmasi');assert.equal((await state()).employees.find(e=>e.id==='emp-007').status,'INACTIVE');

  // T2: Asset driver allocation
  await go('asset','assets');
  await page.locator('article', {hasText: 'Suzuki APV'}).getByRole('button', {name: 'Alokasikan'}).click();
  await page.getByLabel('Work plan').selectOption({value: 'wp-003'});
  await page.getByLabel('Pengemudi kendaraan').selectOption({value: 'member'});
  await page.locator('#dialog').getByRole('button', {name: 'Alokasikan'}).click();
  assert.equal((await state()).assets.find(a=>a.id==='asset-003').driverId, 'member');

  // T1: PDF Generation
  await go('pm-cctv', 'new');
  await page.getByLabel('Nama pekerjaan').fill('Long Plan 12 Hari');
  await page.getByLabel('Lokasi', {exact: true}).fill('Lokasi Uji');
  await page.getByLabel('Lingkup pekerjaan', {exact: true}).fill('Pengujian PDF.');
  await page.getByLabel('Tanggal mulai').fill('2026-10-10');
  await page.getByLabel('Tanggal selesai').fill('2026-10-21');
  await page.getByRole('checkbox', { name: 'Rusyidi Siregar' }).check();
  await click('Simpan draft');
  let currentPlan = (await state()).plans.find(x => x.title === 'Long Plan 12 Hari');
  await go('pm-cctv', `plan/${currentPlan.id}`);
  await click('Terbitkan SK');
  currentPlan = (await state()).plans.find(x => x.title === 'Long Plan 12 Hari');
  let docId = currentPlan.documents[0].id;
  await go('pm-cctv', `document/${currentPlan.id}/${docId}`);
  await page.getByRole('heading', {name: 'SURAT TUGAS', exact:true}).waitFor();
  await page.pdf({ path: join(out, 'sk-multipage.pdf'), format: 'A4', printBackground: true });
  
  let closedPlan = (await state()).plans.find(x => x.id === 'wp-001');
  await page.goto(url+'#/desktop/pm-cctv/presentation/wp-001');
  await page.getByRole('heading', {name: 'Laporan Penyelesaian Pekerjaan', exact:true}).waitFor();
  await page.pdf({ path: join(out, 'laporan-akhir.pdf'), format: 'A4', printBackground: true });

  const skPdf = readFileSync(join(out, 'sk-multipage.pdf')).toString();
  const laporanPdf = readFileSync(join(out, 'laporan-akhir.pdf')).toString();
  const skPages = (skPdf.match(/\/Type\s*\/Page(?!s)/g)||[]).length;
  const lapPages = (laporanPdf.match(/\/Type\s*\/Page(?!s)/g)||[]).length;
  assert(skPages === 3, 'SK PDF should be exactly 3 pages');
  assert(lapPages === 5, 'Laporan PDF should be exactly 5 pages');

  // Independent regression scenarios start from a fresh local simulation.
  const fresh=async(actor='leader',view='plan/wp-001')=>{
    await context.setOffline(false);
    await page.evaluate(async()=>{sessionStorage.removeItem('visiontech.simulateOffline');await VTStorage.reset();});
    await page.reload();await go(actor,view);
  };
  const plan=async(id='wp-001')=>(await state()).plans.find(p=>p.id===id);
  const reason=async(label)=>{await click(label);await page.getByLabel('Alasan / catatan').fill('Catatan pengujian alur pengecualian.');await page.locator('dialog').getByRole('button',{name:'Konfirmasi',exact:true}).click();};
  const extension=async()=>{
    await go('leader','plan/wp-001');await click('Ajukan perpanjangan');
    await page.getByLabel('Usulan tanggal selesai').fill('2026-09-24');
    await page.getByLabel('Alasan perpanjangan').fill('Tambahan pengujian lapangan.');await click('Kirim usulan');
  };
  const extraChecks=[];
  await fresh('leader','plan/wp-001/days');
  const offlineDay=(await plan()).days[0];
  await context.setOffline(true);
  await page.waitForFunction(()=>!navigator.onLine);
  const offlineSection=page.locator('.panel').filter({has:page.locator(`[data-day="${offlineDay.id}"]`)});
  const offlineTask=offlineSection.locator('input[data-task]').first();
  await offlineTask.setChecked(!(await offlineTask.isChecked()));
  await page.getByText(/Tersimpan secara lokal \(Luring\)/).waitFor();
  await offlineSection.getByLabel('Laporan harian',{exact:true}).fill('Laporan tetap tersimpan saat jaringan terputus.');
  await offlineSection.getByRole('button',{name:'Simpan draft',exact:true}).click();
  assert.equal((await state()).offline_queue.length,2);
  assert.match(await page.locator('#net-status').innerText(),/Luring.*2 antrean/);
  assert((await state()).offline_queue.every(q=>q.actorId==='leader'));
  await go('pm-wall','home');
  assert.equal((await state()).offline_queue.length,2,'changing actor must preserve queued transactions');
  await context.setOffline(false);
  await page.waitForFunction(()=>VT.state.offline_queue.length===0);
  assert.equal((await state()).audit[0].action,'SYNC_OFFLINE');
  assert.equal((await plan()).days[0].reportText,'Laporan tetap tersimpan saat jaringan terputus.');
  extraChecks.push('offline checklist/report, actor switch and automatic sync');

  await fresh('pm-cctv','attendance');
  await click('Catat masuk');await click('Simulasi: 10 km');
  const selfie=page.locator('input[name="selfie"][capture="user"]');
  assert(await selfie.isVisible());assert(await selfie.evaluate(e=>e.required));
  const attendanceBefore=(await state()).attendance.length;
  await page.locator('dialog').getByRole('button',{name:'Catat masuk',exact:true}).click();
  assert.equal((await state()).attendance.length,attendanceBefore);
  assert(await selfie.evaluate(e=>e.validity.valueMissing));
  await selfie.setInputFiles({name:'selfie-test.png',mimeType:'image/png',buffer:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jM1sAAAAASUVORK5CYII=','base64')});
  await page.locator('dialog').getByRole('button',{name:'Catat masuk',exact:true}).click();
  await page.locator('dialog').waitFor({state:'hidden'});
  const attendance=(await state()).attendance[0];
  assert.equal(attendance.status,'NEEDS_REVIEW');assert.equal(attendance.coords.origin,'SIMULASI');
  assert(attendance.distance>9900&&attendance.distance<10100);assert.equal(attendance.selfie.type,'image/png');
  await page.reload();
  assert(await page.evaluate(async id=>(await VTStorage.get(id)).size>0,attendance.selfie.id));
  extraChecks.push('geofencing required selfie and IndexedDB persistence');

  await fresh('leader','plan/wp-003');
  const originalSK=(await plan('wp-003')).documents[0];
  await page.getByRole('link',{name:'Buka & Tinjau SK',exact:true}).click();
  await reason('Ajukan banding');
  assert.equal((await plan('wp-003')).status,'APPEALED');
  await go('pm-cctv','plan/wp-003');await click('Buka draft revisi');await click('Terbitkan SK');
  await go('leader','plan/wp-003');await page.getByRole('link',{name:'Buka & Tinjau SK',exact:true}).click();await click('Terima SK');
  assert.equal((await plan('wp-003')).status,'ACCEPTED');
  assert.deepEqual((await plan('wp-003')).documents[0].snapshot,originalSK.snapshot);
  extraChecks.push('appeal, revision and reacceptance preserve issued snapshot');

  await fresh();await extension();await go('pm-cctv','plan/wp-001');await reason('Tolak perpanjangan');
  assert.equal((await plan()).change.status,'REJECTED');assert.equal((await plan()).endDate,'2026-09-23');
  await extension();await go('pm-cctv','plan/wp-001');await click('Setujui perpanjangan');
  await go('leader','plan/wp-001');await page.getByRole('link',{name:'Buka & Tinjau Adendum',exact:true}).click();await reason('Tolak adendum');
  assert.equal((await plan()).documents.at(-1).status,'REJECTED');assert.equal((await plan()).endDate,'2026-09-23');
  extraChecks.push('extension rejection by PM and leader');

  await fresh('leader','plan/wp-001/days');
  const returnDay=(await plan()).days[0];
  const reportSection=page.locator('.panel').filter({has:page.locator(`[data-day="${returnDay.id}"]`)});
  for(const task of await reportSection.locator('input[data-task]').all())await task.check();
  await reportSection.getByLabel('Laporan harian',{exact:true}).fill('Laporan awal yang akan dikembalikan untuk perbaikan.');
  await reportSection.getByLabel('Gunakan bukti simulasi').check();
  await reportSection.getByRole('button',{name:'Simpan draft',exact:true}).click();await reportSection.getByRole('button',{name:'Kirim laporan',exact:true}).click();
  await go('pm-cctv','plan/wp-001/days');
  const reportReview=page.locator('form[data-form="review-report"]').filter({has:page.locator(`input[name="dayId"][value="${returnDay.id}"]`)});
  await reportReview.locator('select[name="decision"]').selectOption('RETURN');
  await reportReview.locator('textarea[name="note"]').fill('Tambahkan hasil pengujian.');
  await reportReview.getByRole('button',{name:'Simpan keputusan',exact:true}).click();
  assert.equal((await plan()).days[0].reportStatus,'CHANGES_REQUESTED');
  await go('leader','plan/wp-001/days');assert(await reportSection.getByLabel('Laporan harian',{exact:true}).isEditable());
  extraChecks.push('PM returns report and leader can revise');

  await fresh('pm-cctv','plan/wp-001');await reason('Batalkan pekerjaan');
  assert.equal((await plan()).status,'CANCELLED');
  assert((await state()).assets.some(a=>a.planId==='wp-001'&&a.status==='IN_USE'),'cancellation must retain used assets');
  await go('leader','plan/wp-001/resources');await page.getByRole('button',{name:'Ajukan pengembalian',exact:true}).first().click();
  await page.getByLabel('Catatan kondisi & kelengkapan').fill('Dikembalikan setelah pembatalan.');
  await page.locator('dialog').getByRole('button',{name:'Ajukan pengembalian',exact:true}).click();
  assert((await state()).assets.some(a=>a.planId==='wp-001'&&a.status==='RETURN_PENDING'));
  await fresh('pm-cctv','plan/wp-002');await reason('Arsipkan draft');
  assert((await plan('wp-002')).deletedAt);await click('Pulihkan draft');assert.equal((await plan('wp-002')).deletedAt,null);
  extraChecks.push('cancellation retains asset obligations; archive and restore draft');

  await fresh();await extension();await go('pm-cctv','plan/wp-001');await click('Setujui perpanjangan');
  const pendingPlan=await plan();
  await go('leader','plan/wp-001');await click('Ajukan Lembur');
  await page.locator('dialog input[name="hours"]').fill('2');await page.locator('dialog textarea[name="reason"]').fill('Pengujian di luar jam kerja.');
  await page.locator('dialog button[type="submit"]').click();
  assert.equal((await state()).overtime_logs.at(-1).documentId,pendingPlan.documents.filter(d=>d.status==='EFFECTIVE').at(-1).id);
  assert(await page.evaluate(()=>!!VTDomain.transition(VT.state,VTDomain.actors.find(a=>a.id==='pm-cctv'),'REQUEST_PERSONNEL_CHANGE',{planId:'wp-001',leaderId:'member',memberIds:['leader'],reason:'Rotasi'}).error));
  extraChecks.push('overtime uses effective SK; pending changes cannot overlap');

  await fresh('pm-cctv','plan/wp-001');
  const proposePersonnel=async()=>{
    await go('pm-cctv','plan/wp-001');await click('Adendum personel');
    await page.getByLabel('Ketua tim',{exact:true}).selectOption('member');
    await page.locator('dialog input[name="memberIds"][value="leader"]').check();
    await page.getByLabel('Alasan perubahan personel').fill('Rotasi ketua dengan persetujuan penerima.');
    await click('Terbitkan adendum personel');
  };
  const personnelDoc=async()=>{const doc=(await plan()).documents.at(-1);await go('member',`document/wp-001/${doc.id}`);};
  await proposePersonnel();await personnelDoc();await reason('Tolak adendum personel');
  assert.equal((await plan()).leaderId,'leader');assert.equal((await plan()).change.status,'REJECTED');
  await proposePersonnel();const issuedBefore=(await plan()).documents[0].snapshot;
  await personnelDoc();await click('Terima adendum personel');
  assert.equal((await plan()).leaderId,'member');assert.deepEqual((await plan()).documents[0].snapshot,issuedBefore);
  await go('member','plan/wp-001');assert(await page.getByRole('button',{name:'Ajukan perpanjangan',exact:true}).isVisible());
  await go('leader','plan/wp-001');assert.equal(await page.getByRole('button',{name:'Ajukan perpanjangan',exact:true}).count(),0);
  assert(await page.getByRole('button',{name:'Lapor Insiden/HSE',exact:true}).isVisible());
  extraChecks.push('personnel rejection/acceptance and assignment-based leader controls');

  // The terminal plan retains incident follow-up, but cannot accept new incidents.
  for(const terminal of ['CANCELLED','COMPLETED']){
    await fresh();
    const terminalResult=await page.evaluate(status=>{
      const D=VTDomain,actor=id=>D.actors.find(a=>a.id===id);
      const filed=D.transition(VT.state,actor('member'),'REPORT_INCIDENT',{planId:'wp-001',category:'ASET',severity:'RENDAH',description:'Kerusakan perlu tindak lanjut.'});
      if(filed.error)throw Error(filed.error);
      const s=filed.state;s.plans.find(p=>p.id==='wp-001').status=status;
      const denied=D.transition(s,actor('member'),'REPORT_INCIDENT',{planId:'wp-001',category:'ASET',severity:'RENDAH',description:'Baru setelah penutupan.'});
      const resolved=D.transition(s,actor('pm-cctv'),'RESOLVE_INCIDENT',{incidentId:s.incident_reports.at(-1).id,note:'Tindak lanjut selesai.'});
      return {denied:!!denied.error,resolved:resolved.state?.incident_reports.at(-1).status,error:resolved.error};
    },terminal);
    assert(terminalResult.denied);assert.equal(terminalResult.resolved,'RESOLVED',terminalResult.error);
  }
  await fresh('pm-wall','approvals');
  assert.equal(await page.evaluate(()=>VT.work.get('wp-001')),undefined);
  assert.deepEqual(await page.evaluate(()=>VT.queue().filter(q => q.title !== 'Peringatan Absensi')),[]);
  extraChecks.push('terminal incident follow-up and hidden plan lookup safety');

  await fresh('leader','plan/wp-001/days');
  await context.setOffline(true);await page.waitForFunction(()=>!navigator.onLine);
  await page.locator('input[data-task]').first().uncheck();
  const queued=(await state()).offline_queue.length;assert.equal(queued,1);
  // A dirty page must not overwrite a newer revision written by another tab.
  await page.locator('form[data-form="report"] textarea[name="text"]').first().fill('Perubahan belum disimpan.');
  const second=await context.newPage();
  await second.goto(url+'#/desktop/pm-cctv/settings');
  await second.getByLabel('Tanggal simulasi',{exact:true}).fill('2026-09-22');
  await second.getByRole('button',{name:'Simpan tanggal',exact:true}).click();
  await page.waitForFunction(()=>JSON.parse(localStorage.getItem(VTStorage.key)).revision!==VT.state.revision);
  await context.setOffline(false);
  await page.getByText('Data berubah di tab lain. Muat ulang halaman sebelum mengulangi tindakan.',{exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>VT.state.offline_queue.length),queued);
  assert.equal((await state()).demoDate,'2026-09-22');
  await second.close();
  await page.evaluate(()=>VT.dirty=false); // Explicitly discard the unsaved test text before recovery.
  await page.reload();
  await page.waitForFunction(()=>VT.state.offline_queue.length===0);
  extraChecks.push('offline sync conflict preserves queue and other-tab data');

  await fresh('hr','people');
  await go('hr','employee/emp-007');await reason('Offboarding');
  for(const device of ['desktop','mobile']){
    await page.setViewportSize({width:device==='mobile'?390:1440,height:1000});
    await go('hr','people',device);
    await page.getByLabel('Status karyawan',{exact:true}).selectOption('ACTIVE');
    await page.getByLabel('Cari karyawan',{exact:true}).fill('Rusyidi');
    assert.equal(await page.locator('[data-search-item]:visible').count(),1);
    await page.getByLabel('Status karyawan',{exact:true}).selectOption('INACTIVE');
    assert.equal(await page.locator('[data-search-item]:visible').count(),0);
    assert(await page.locator('#no-results').isVisible());
    await page.getByLabel('Cari karyawan',{exact:true}).fill('');
    assert.equal(await page.locator('[data-search-item]:visible').count(),1,'nonactive filter shows the offboarded employee');
    await page.getByLabel('Status karyawan',{exact:true}).selectOption('');
    await page.getByLabel('Cari karyawan',{exact:true}).fill('');
    assert.equal(await page.locator('[data-search-item]:visible').count(),33);
    assert(!(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1)));
    await page.screenshot({path:join(out,`people-${device}.png`),fullPage:true});
  }
  await page.setViewportSize({width:1440,height:1000});
  await go('member','profile');await click('+ Ajukan dokumen');
  await page.getByLabel('Jenis dokumen').selectOption('Sertifikat K3');
  await page.getByLabel('Nomor dokumen',{exact:true}).fill('K3-UJI-2026');
  await page.getByLabel('Gunakan lampiran contoh bila tidak memilih berkas').check();
  await click('Ajukan verifikasi');await page.locator('dialog').waitFor({state:'hidden'});
  await page.getByRole('heading',{name:'Menunggu verifikasi HR',exact:true}).waitFor();
  const pendingDoc=(await state()).employees.find(e=>e.id==='member').documents.at(-1);
  const oldCurrent=(await state()).employees.find(e=>e.id==='member').documents.find(d=>d.type==='Sertifikat K3'&&d.lifecycle==='CURRENT');
  assert(oldCurrent,'old document remains current while HR reviews');
  await go('hr','employee/member');await page.getByRole('link',{name:'Tinjau dokumen',exact:true}).click();
  await page.getByLabel('Catatan pemeriksaan').fill('Dokumen dan pemilik sesuai.');await click('Simpan keputusan');
  await go('member','profile');
  const updatedDocs=(await state()).employees.find(e=>e.id==='member').documents;
  assert.equal(updatedDocs.find(d=>d.id===pendingDoc.id).lifecycle,'CURRENT');
  assert.equal(updatedDocs.find(d=>d.id===oldCurrent.id).lifecycle,'SUPERSEDED');
  await page.locator('summary').filter({hasText:'Riwayat dokumen'}).click();
  assert(await page.locator('details[open]').getByText(oldCurrent.numberMasked,{exact:false}).isVisible());
  await page.evaluate(()=>scrollTo(0,0));
  await page.screenshot({path:join(out,'profile-document-history.png'),fullPage:true});
  await go('pm-cctv','employee/member');assert.equal(await page.getByRole('heading',{name:'Dokumen karyawan',exact:true}).count(),0);
  await go('ops','employee/member');assert.equal(await page.getByRole('heading',{name:'Dokumen karyawan',exact:true}).count(),0);
  extraChecks.push('employee status/search filters and private document review/history');

  assert.deepEqual(errors,[]);
  const result={screens:screenCount,roles:actors.length,checks:['desktop/mobile role isolation','direct file opening','persistence','SK publication and acceptance','two-party addendum','full reporting and closure','asset return verification','document upload and independent review','attendance review','promotion and offboarding','pdf generation'],pdfPages:{sk:skPages,laporanAkhir:lapPages},screenshots:out};
  result.checks.push(...extraChecks);
  writeFileSync(join(out,'results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
}finally{await browser.close();}
