const test = require('node:test');
const assert = require('node:assert/strict');
global.window = global;
require('../js/domain.js');
const { actors, createInitialState, transition, visiblePlans } = VTDomain;

const actor = id => actors.find(a => a.id === id);
const apply = (state, actorId, type, payload) => {
  const before = JSON.stringify(state);
  const result = transition(state, actor(actorId), type, payload);
  assert.equal(JSON.stringify(state), before, `${type} must not mutate its input`);
  assert.ok(!result.error, `${type}: ${result.error}`);
  assert.ok(result.state.audit.length > state.audit.length);
  return result.state;
};
const rejected = (state, actorId, type, payload, pattern) => {
  const before = JSON.stringify(state);
  const result = transition(state, actor(actorId), type, payload);
  assert.match(result.error || '', pattern);
  assert.equal(result.state, undefined);
  assert.equal(JSON.stringify(state), before);
};

test('unit scope and member visibility are enforced independently of UI controls', () => {
  const state = createInitialState();
  assert.equal(state.employees.length, 33);
  assert.ok(visiblePlans(state, actor('pm-cctv')).every(plan => plan.unit === 'CCTV_ACS'));
  assert.ok(visiblePlans(state, actor('pm-wall')).every(plan => plan.unit === 'WALL_DISPLAY'));
  assert.ok(visiblePlans(state, actor('member')).every(plan => plan.status !== 'DRAFT' && plan.memberIds.includes('member')));
  assert.equal(visiblePlans(state, actor('finance')).length, 0);
  rejected(state, 'pm-wall', 'PUBLISH', { planId: 'wp-002' }, /tidak diizinkan/);
  rejected(state, 'member', 'APPROVE_CHANGE', { planId: 'wp-001' }, /tidak diizinkan/);
  const spoofed = transition(state, { ...actor('member'), role: 'OPS' }, 'CANCEL_PLAN', { planId: 'wp-001', reason: 'Test' });
  assert.match(spoofed.error, /tidak dikenal/);
});

test('draft editing and publication require complete days and active people', () => {
  let state = createInitialState();
  const dayId = state.plans.find(p => p.id === 'wp-002').days[0].id;
  state = apply(state, 'pm-cctv', 'SAVE_DAY', { planId: 'wp-002', dayId, title: 'Uji akses pintu', tasks: [{ title: 'Pasang reader' }, { title: 'Uji akses kartu' }] });
  assert.equal(state.plans.find(p => p.id === 'wp-002').days[0].tasks[0].title, 'Pasang reader');
  rejected(state, 'pm-cctv', 'SAVE_DAY', { planId: 'wp-002', dayId, title: '', tasks: [] }, /tugas per hari/);
  const invalid = structuredClone(state);
  invalid.plans.find(p => p.id === 'wp-002').days[0].title = '';
  rejected(invalid, 'pm-cctv', 'PUBLISH', { planId: 'wp-002' }, /belum lengkap/);
  const inactive = structuredClone(state);
  inactive.employees.find(e => e.id === 'leader').status = 'INACTIVE';
  rejected(inactive, 'pm-cctv', 'PUBLISH', { planId: 'wp-002' }, /karyawan aktif/);
  state = apply(state, 'pm-cctv', 'PUBLISH', { planId: 'wp-002' });
  const plan = state.plans.find(p => p.id === 'wp-002');
  assert.equal(plan.status, 'PUBLISHED');
  assert.equal(plan.documents.length, 1);
  assert.equal(plan.documents[0].snapshot.days[0].title, 'Uji akses pintu');
  state = apply(state, 'leader', 'ACCEPT', { planId: plan.id });
  assert.equal(state.plans.find(p => p.id === plan.id).status, 'ACCEPTED');
  rejected(state, 'leader', 'START', { planId: plan.id }, /baru dapat dimulai/);
});

test('appeal revisions preserve previously issued snapshot', () => {
  let state = createInitialState();
  const before = structuredClone(state.plans.find(p => p.id === 'wp-003').documents[0].snapshot);
  state = apply(state, 'leader', 'APPEAL', { planId: 'wp-003', reason: 'Lokasi perlu dikonfirmasi.' });
  state = apply(state, 'pm-cctv', 'REVISE', { planId: 'wp-003' });
  state = apply(state, 'pm-cctv', 'EDIT_DRAFT', { planId: 'wp-003', title: 'Pemeliharaan CCTV revisi' });
  state = apply(state, 'pm-cctv', 'PUBLISH', { planId: 'wp-003' });
  const plan = state.plans.find(p => p.id === 'wp-003');
  assert.deepEqual(plan.documents[0].snapshot, before);
  assert.equal(plan.documents[0].status, 'SUPERSEDED');
  assert.equal(plan.documents.length, 2);
  assert.equal(plan.documents[1].version, 2);
});

test('adendum requires both approvals and rechecks schedule before activation', () => {
  let state = createInitialState();
  const original = structuredClone(state.plans.find(p => p.id === 'wp-001').documents[0]);
  state = apply(state, 'leader', 'REQUEST_CHANGE', { planId: 'wp-001', type: 'EXTEND', newEnd: '2026-09-24', reason: 'Tambahan uji integrasi.' });
  rejected(state, 'leader', 'ACCEPT_CHANGE', { planId: 'wp-001' }, /belum siap/);
  state = apply(state, 'pm-cctv', 'APPROVE_CHANGE', { planId: 'wp-001' });
  let plan = state.plans.find(p => p.id === 'wp-001');
  assert.equal(plan.endDate, '2026-09-23');
  assert.equal(plan.revision, 1);
  assert.equal(plan.documents.at(-1).status, 'AWAITING_ACCEPTANCE');
  state = apply(state, 'leader', 'ACCEPT_CHANGE', { planId: 'wp-001' });
  plan = state.plans.find(p => p.id === 'wp-001');
  assert.equal(plan.endDate, '2026-09-24');
  assert.equal(plan.revision, 2);
  assert.equal(plan.days.length, 4);
  assert.deepEqual(plan.documents[0], original);
  assert.equal(plan.documents.at(-1).acceptedBy, 'Rouzi Dewantoro');
  state = apply(state, 'leader', 'REQUEST_CHANGE', { planId: 'wp-001', type: 'EXTEND', newEnd: '2026-09-29', reason: 'Bentrok dengan rencana warehouse.' });
  rejected(state, 'pm-cctv', 'APPROVE_CHANGE', { planId: 'wp-001' }, /bertabrakan/);
});

test('completion requires approved reports and asset return verified by another actor', () => {
  let state = createInitialState();
  state.demoDate = '2026-09-30';
  rejected(state, 'leader', 'REQUEST_COMPLETE', { planId: 'wp-001', reportText: 'All done', obstacleText: 'None' }, /laporan harian/);
  for (const day of state.plans.find(p => p.id === 'wp-001').days) {
    rejected(state, 'leader', 'SUBMIT_REPORT', { planId: 'wp-001', dayId: day.id }, /laporan|checklist/i);
    for (const task of day.tasks.filter(t => !t.done)) state = apply(state, 'leader', 'TOGGLE_TASK', { planId: 'wp-001', dayId: day.id, taskId: task.id });
    state = apply(state, 'leader', 'SAVE_REPORT', { planId: 'wp-001', dayId: day.id, text: 'Seluruh kegiatan selesai dan sudah diperiksa.', evidence: ['bukti-dummy.jpg'] });
    state = apply(state, 'leader', 'SUBMIT_REPORT', { planId: 'wp-001', dayId: day.id });
    rejected(state, 'leader', 'SAVE_REPORT', { planId: 'wp-001', dayId: day.id, text: 'Tidak boleh ditimpa.' }, /tidak dapat diubah/);
    state = apply(state, 'pm-cctv', 'REVIEW_REPORT', { planId: 'wp-001', dayId: day.id, decision: 'APPROVE' });
  }
  state = apply(state, 'leader', 'REQUEST_COMPLETE', { planId: 'wp-001', reportText: 'All done', obstacleText: 'None' });
  rejected(state, 'pm-cctv', 'APPROVE_COMPLETE', { planId: 'wp-001' }, /aset|verifikasi/);
  for (const asset of state.assets.filter(a => a.planId === 'wp-001')) {
    state = apply(state, 'leader', 'RETURN_ASSET', { assetId: asset.id });
    state = apply(state, 'asset', 'VERIFY_RETURN', { assetId: asset.id });
  }
  state = apply(state, 'pm-cctv', 'APPROVE_COMPLETE', { planId: 'wp-001' });
  assert.equal(state.plans.find(p => p.id === 'wp-001').status, 'COMPLETED');
  assert.ok(!state.assets.some(a => a.planId === 'wp-001'));
});

test('optimistic version conflicts fail without dropping data', () => {
  const state = createInitialState();
  rejected(state, 'pm-cctv', 'EDIT_DRAFT', { planId: 'wp-002', rowVersion: 0, title: 'Outdated title' }, /Revisi berubah/);
  const next = apply(state, 'pm-cctv', 'EDIT_DRAFT', { planId: 'wp-002', rowVersion: 1, title: 'Updated title' });
  assert.equal(next.plans.find(p => p.id === 'wp-002').rowVersion, 2);
});

test('soft delete is limited to drafts and restore preserves audit history', () => {
  let state = createInitialState();
  rejected(state, 'pm-cctv', 'DELETE_PLAN', { planId: 'wp-003', reason: 'Tidak boleh' }, /Tahap/);
  state = apply(state, 'pm-cctv', 'DELETE_PLAN', { planId: 'wp-002', reason: 'Salah draft.' });
  assert.ok(state.plans.find(p => p.id === 'wp-002').deletedAt);
  assert.ok(!visiblePlans(state, actor('pm-cctv')).some(p => p.id === 'wp-002'));
  rejected(state, 'pm-cctv', 'PUBLISH', { planId: 'wp-002' }, /diarsipkan/);
  state = apply(state, 'pm-cctv', 'RESTORE_PLAN', { planId: 'wp-002' });
  assert.equal(state.plans.find(p => p.id === 'wp-002').deletedAt, null);
  assert.deepEqual(state.audit.slice(0, 2).map(event => event.action), ['RESTORE_PLAN', 'DELETE_PLAN']);
  // Test B9: REVISE puts it back to DRAFT, but DELETE_PLAN should still be rejected because documents exist
  state = apply(state, 'leader', 'APPEAL', { planId: 'wp-003', reason: 'Revisi' });
  state = apply(state, 'pm-cctv', 'REVISE', { planId: 'wp-003' });
  rejected(state, 'pm-cctv', 'DELETE_PLAN', { planId: 'wp-003', reason: 'Arsip' }, /Gunakan opsi pembatalan/);
});

test('document replacement leaves old current until independent verification', () => {
  let state = createInitialState();
  state = apply(state, 'member', 'UPLOAD_DOCUMENT', { employeeId: 'member', type: 'Sertifikat K3', expiry: '2028-09-01', number: 'DUMMY-5678' });
  let employee = state.employees.find(e => e.id === 'member');
  const newId = employee.documents.at(-1).id;
  assert.equal(employee.documents[0].lifecycle, 'CURRENT');
  assert.equal(employee.documents.at(-1).lifecycle, 'PENDING');
  rejected(state, 'member', 'VERIFY_DOCUMENT', { employeeId: 'member', documentId: newId, decision: 'APPROVE' }, /tidak diizinkan/);
  state = apply(state, 'hr', 'VERIFY_DOCUMENT', { employeeId: 'member', documentId: newId, decision: 'APPROVE' });
  employee = state.employees.find(e => e.id === 'member');
  assert.equal(employee.documents[0].lifecycle, 'SUPERSEDED');
  assert.equal(employee.documents.at(-1).lifecycle, 'CURRENT');
  rejected(state, 'hr', 'UPLOAD_DOCUMENT', { employeeId: 'member', type: 'SIM A', expiry: '2028-01-01', number: 'DUMMY-9123' }, /hanya dapat diajukan oleh pemiliknya/);
  state = apply(state, 'member', 'UPLOAD_DOCUMENT', { employeeId: 'member', type: 'SIM A', expiry: '2028-01-01', number: 'DUMMY-9123' });
  const newSim = state.employees.find(e => e.id === 'member').documents.at(-1);
  state = apply(state, 'hr', 'VERIFY_DOCUMENT', { employeeId: 'member', documentId: newSim.id, decision: 'APPROVE', note: 'Sesuai' });
  const verifiedSim = state.employees.find(e => e.id === 'member').documents.at(-1);
  assert.equal(verifiedSim.status, 'VERIFIED');
});

test('promotion updates placement but cannot rewrite existing SK snapshots', () => {
  let state = createInitialState();
  const original = structuredClone(state.plans.find(p => p.id === 'wp-001').documents[0].snapshot);
  state = apply(state, 'hr', 'PROMOTE', { employeeId: 'emp-014', position: 'Senior System Engineer', unit: 'CCTV_ACS' });
  const employee = state.employees.find(e => e.id === 'emp-014');
  assert.equal(employee.assignmentHistory.length, 2);
  assert.equal(employee.assignmentHistory[0].to, employee.assignmentHistory[1].from);
  assert.deepEqual(state.plans.find(p => p.id === 'wp-001').documents[0].snapshot, original);
  rejected(state, 'hr', 'PROMOTE', { employeeId: 'emp-014', position: 'Engineer', unit: 'WALL_DISPLAY' }, /diserahterimakan/);
});

test('offboarding checks outstanding assignment and revokes future simulated access', () => {
  let state = createInitialState();
  rejected(state, 'hr', 'OFFBOARD', { employeeId: 'member', reason: 'Resign' }, /penugasan aktif/);
  state = apply(state, 'hr', 'OFFBOARD', { employeeId: 'asset', reason: 'Masa kerja berakhir.' });
  const employee = state.employees.find(e => e.id === 'asset');
  assert.equal(employee.status, 'INACTIVE');
  assert.equal(employee.deletedAt, null);
  assert.equal(employee.accessRevoked, true);
  rejected(state, 'asset', 'RESERVE_ASSET', { assetId: 'asset-003', planId: 'wp-002' }, /Akses simulasi telah dicabut/);
  rejected(state, 'hr', 'RESTORE_EMPLOYEE', { employeeId: 'asset' }, /masa kerja dan akses baru/);
});

test('Finance review preserves attendance evidence and requires review notes', () => {
  let state = createInitialState();
  const original = structuredClone(state.attendance[0]);
  rejected(state, 'finance', 'REVIEW_ATTENDANCE', { attendanceId: 'att-001', decision: 'APPROVE' }, /Catatan/);
  state = apply(state, 'finance', 'REVIEW_ATTENDANCE', { attendanceId: 'att-001', decision: 'APPROVE', note: 'Gerbang belakang dikonfirmasi PM.' });
  const reviewed = state.attendance.find(a => a.id === 'att-001');
  assert.equal(reviewed.status, 'APPROVED');
  assert.equal(reviewed.distance, original.distance);
  assert.equal(reviewed.checkIn, original.checkIn);
  rejected(state, 'leader', 'CHECK_OUT', { attendanceId: 'att-001' }, /bukan milik/);
});

test('assets cannot be double allocated', () => {
  let state = createInitialState();
  state = apply(state, 'asset', 'RESERVE_ASSET', { assetId: 'asset-003', planId: 'wp-002', driverId: 'member' });
  rejected(state, 'pm-wall', 'RESERVE_ASSET', { assetId: 'asset-003', planId: 'wp-004', driverId: 'emp-032' }, /sudah dialokasikan/);
  rejected(state, 'asset', 'RETURN_ASSET', { assetId: 'asset-003' }, /tidak dapat dilakukan oleh petugas aset/);
  state = apply(state, 'leader', 'RETURN_ASSET', { assetId: 'asset-003' });
});

test('reports cannot be filled for future dates', () => {
  let state = createInitialState();
  state.demoDate = '2026-09-20'; // Plan starts 2026-09-21
  const day = state.plans.find(p => p.id === 'wp-001').days[0];
  rejected(state, 'leader', 'SAVE_REPORT', { planId: 'wp-001', dayId: day.id, text: 'Test' }, /setelah tanggal pelaksanaan/);
  rejected(state, 'leader', 'SUBMIT_REPORT', { planId: 'wp-001', dayId: day.id, text: 'Test' }, /setelah tanggal pelaksanaan/);
});

test('vehicle constraints: valid driver and SIM checks during reservation, check, and extension', () => {
  let state = createInitialState();
  
  // reserve without driver
  rejected(state, 'asset', 'RESERVE_ASSET', { assetId: 'asset-003', planId: 'wp-002', driverId: '' }, /Pilih pengemudi/);
  
  // reserve outside team
  rejected(state, 'asset', 'RESERVE_ASSET', { assetId: 'asset-003', planId: 'wp-002', driverId: 'emp-032' }, /Pengemudi harus bagian/);
  
  // employee member is in team but we need him to not have SIM A or expired SIM
  // let's give member an expired SIM A
  state = apply(state, 'member', 'UPLOAD_DOCUMENT', { employeeId: 'member', type: 'SIM A', expiry: '2026-08-01', number: '123' });
  let employee = state.employees.find(e => e.id === 'member');
  let docId = employee.documents.at(-1).id;
  state = apply(state, 'hr', 'VERIFY_DOCUMENT', { employeeId: 'member', documentId: docId, decision: 'APPROVE', note: 'ok' });
  rejected(state, 'asset', 'RESERVE_ASSET', { assetId: 'asset-003', planId: 'wp-002', driverId: 'member' }, /kedaluwarsa sebelum jadwal selesai/);
  
  // update sim to valid
  state = apply(state, 'member', 'UPLOAD_DOCUMENT', { employeeId: 'member', type: 'SIM A', expiry: '2028-08-01', number: '123' });
  docId = state.employees.find(e => e.id === 'member').documents.at(-1).id;
  state = apply(state, 'hr', 'VERIFY_DOCUMENT', { employeeId: 'member', documentId: docId, decision: 'APPROVE', note: 'ok' });
  
  // now successful
  state = apply(state, 'asset', 'RESERVE_ASSET', { assetId: 'asset-003', planId: 'wp-002', driverId: 'member' });
  
  // CHECK_ASSET by other
  rejected(state, 'leader', 'CHECK_ASSET', { assetId: 'asset-003', planId: 'wp-002', decision: 'ACCEPT' }, /pengemudi yang ditunjuk/);
  
  // CHECK_ASSET by driver
  state = apply(state, 'member', 'CHECK_ASSET', { assetId: 'asset-003', planId: 'wp-002', decision: 'ACCEPT' });

  // To test SIM expiry on schedule changes (PUBLISH), use wp-002
  // member's SIM is valid until 2028-08-01. Let's make it expire on 2026-09-24. wp-002 ends on 2026-09-25.
  state.employees.find(e => e.id === 'member').documents.find(d => d.type === 'SIM A' && d.lifecycle === 'CURRENT').expiry = '2026-09-24';
  
  // Try to publish wp-002 (we need to fill it first, so let's just cheat and set status to PUBLISH or just test checkSchedule directly via some other way, or fill days)
  // Actually, we can just call EDIT_DRAFT on wp-002 to change its endDate, which calls checkSchedule? No, EDIT_DRAFT doesn't call checkSchedule.
  // We can just call SAVE_DAY? No.
  
  // Let's just fill wp-002 days to PUBLISH it.
  const plan002 = state.plans.find(p => p.id === 'wp-002');
  for (const day of plan002.days) {
     state = apply(state, 'pm-cctv', 'SAVE_DAY', { planId: 'wp-002', dayId: day.id, title: 'Test', tasks: [{title: 'Test'}] });
  }
  rejected(state, 'pm-cctv', 'PUBLISH', { planId: 'wp-002' }, /kedaluwarsa sebelum/);
});

test('check-in outside the radius requires a selfie image from mobile; machine and in-radius do not', () => {
  const state = createInitialState();
  const selfie = { id: 'blob-1', name: 'swafoto.jpg', type: 'image/jpeg', size: 1200 };
  rejected(state, 'pm-cctv', 'CHECK_IN', { site: 'Gedung Merdeka', source: 'MOBILE', distance: 10000, lat: 3.68, lng: 98.67 }, /swafoto wajib/);
  rejected(state, 'pm-cctv', 'CHECK_IN', { site: 'Gedung Merdeka', source: 'MOBILE', distance: 10000, selfie: { ...selfie, type: 'application/pdf' } }, /harus berupa gambar/);
  let next = apply(state, 'pm-cctv', 'CHECK_IN', { site: 'Gedung Merdeka', source: 'MOBILE', distance: 10000, lat: 3.68, lng: 98.67, geoSource: 'GPS', selfie });
  let record = next.attendance[0];
  assert.equal(record.status, 'NEEDS_REVIEW');
  assert.deepEqual(record.coords, { lat: 3.68, lng: 98.67, origin: 'GPS' });
  assert.equal(record.selfie.id, 'blob-1');
  next = apply(state, 'pm-cctv', 'CHECK_IN', { site: 'Gedung Merdeka', source: 'MOBILE', distance: 40, lat: 3.5899, lng: 98.6739 });
  assert.equal(next.attendance[0].status, 'AUTO_VALID');
  assert.equal(next.attendance[0].selfie, null);
  assert.equal(next.attendance[0].coords.origin, 'SIMULASI');
  next = apply(state, 'pm-cctv', 'CHECK_IN', { site: 'Kantor Pusat', source: 'MACHINE', distance: 500 });
  assert.equal(next.attendance[0].status, 'NEEDS_REVIEW');
  assert.equal(next.attendance[0].coords, null);
  assert.deepEqual([state.offline_queue, state.incident_reports, state.overtime_logs], [[], [], []]);
});

test('incidents and overtime stay inside the plan team, unit, and running status', () => {
  let state = createInitialState();
  const incident = { planId: 'wp-001', category: 'K3_RINGAN', severity: 'TINGGI', description: 'Pekerja tergelincir di tangga.' };
  rejected(state, 'leader', 'REPORT_INCIDENT', { category: 'K3_RINGAN', severity: 'TINGGI', description: 'Tanpa pekerjaan.' }, /Tahap work plan belum sesuai/);
  rejected(state, 'leader', 'REPORT_INCIDENT', { ...incident, planId: 'wp-003' }, /Tahap work plan belum sesuai/);
  rejected(state, 'emp-032', 'REPORT_INCIDENT', incident, /tidak diizinkan untuk peran atau unit/);
  state = apply(state, 'member', 'REPORT_INCIDENT', { ...incident, category: 'ASET' });
  const incidentId = state.incident_reports.at(-1).id;
  assert.equal(state.incident_reports.at(-1).planId, 'wp-001');
  rejected(state, 'pm-wall', 'RESOLVE_INCIDENT', { incidentId, note: 'Ditutup.' }, /di luar unit atau kewenangan/);
  rejected(state, 'pm-cctv', 'RESOLVE_INCIDENT', { incidentId }, /Catatan penyelesaian wajib/);
  const byAsset = apply(state, 'asset', 'RESOLVE_INCIDENT', { incidentId, note: 'Tangga diganti.' });
  assert.equal(byAsset.incident_reports.at(-1).status, 'RESOLVED');
  assert.equal(byAsset.incident_reports.at(-1).resolvedBy, 'Hernita');
  rejected(byAsset, 'asset', 'RESOLVE_INCIDENT', { incidentId, note: 'Lagi.' }, /tidak aktif atau sudah ditutup/);

  state = apply(state, 'leader', 'REPORT_OVERTIME', { planId: 'wp-001', hours: 3, reason: 'Lanjut instalasi.' });
  const overtime = state.overtime_logs.at(-1);
  assert.equal(overtime.status, 'PENDING_PM');
  assert.equal(overtime.documentId, 'document-wp-001');
  rejected(state, 'pm-wall', 'REVIEW_OVERTIME', { overtimeId: overtime.id, decision: 'APPROVED' }, /di luar unit atau kewenangan/);
  rejected(state, 'finance', 'REVIEW_OVERTIME', { overtimeId: overtime.id, decision: 'APPROVED' }, /tidak diizinkan untuk peran atau unit/);
  state = apply(state, 'ops', 'REVIEW_OVERTIME', { overtimeId: overtime.id, decision: 'APPROVED', note: 'Sesuai kebutuhan.' });
  assert.equal(state.overtime_logs.at(-1).status, 'APPROVED');
  assert.equal(state.overtime_logs.at(-1).reviewedBy, 'Ade Candra');
});

test('personnel addendum replaces the team only after the incoming leader accepts, and locks older versions', () => {
  let state = createInitialState();
  const plan = () => state.plans.find(p => p.id === 'wp-001');
  const base = { planId: 'wp-001', reason: 'Rotasi personel proyek.' };
  rejected(state, 'leader', 'REQUEST_PERSONNEL_CHANGE', { ...base, memberIds: ['member'] }, /tidak diizinkan untuk peran atau unit/);
  rejected(state, 'pm-wall', 'REQUEST_PERSONNEL_CHANGE', { ...base, memberIds: ['member'] }, /tidak diizinkan untuk peran atau unit/);
  rejected(state, 'pm-cctv', 'REQUEST_PERSONNEL_CHANGE', { ...base, reason: '', memberIds: ['member'] }, /Alasan perubahan personel wajib/);
  rejected(state, 'pm-cctv', 'REQUEST_PERSONNEL_CHANGE', { ...base, leaderId: plan().leaderId, memberIds: plan().memberIds }, /Tidak ada perubahan personel/);
  rejected(state, 'pm-cctv', 'REQUEST_PERSONNEL_CHANGE', { ...base, memberIds: ['emp-032'] }, /lintas unit/);
  rejected(state, 'pm-cctv', 'REQUEST_PERSONNEL_CHANGE', { ...base, memberIds: [] }, /minimal satu anggota/);

  // a member who still drives an allocated vehicle cannot be dropped
  let withVehicle = apply(state, 'asset', 'RESERVE_ASSET', { assetId: 'asset-003', planId: 'wp-001', driverId: 'member' });
  rejected(withVehicle, 'pm-cctv', 'REQUEST_PERSONNEL_CHANGE', { ...base, memberIds: ['emp-014'] }, /pengemudi/);

  state = apply(state, 'pm-cctv', 'REQUEST_PERSONNEL_CHANGE', { ...base, leaderId: 'emp-014', memberIds: ['member'] });
  const change = plan().change, addendum = plan().documents.at(-1);
  assert.equal(change.type, 'PERSONNEL');
  assert.equal(change.status, 'AWAITING_LEADER_ACCEPTANCE');
  assert.equal(addendum.kind, 'PERSONNEL_ADDENDUM');
  assert.equal(addendum.snapshot.leader.id, 'emp-014');
  assert.equal(plan().leaderId, 'leader', 'team must not change before acceptance');
  rejected(state, 'member', 'ACCEPT_CHANGE', { planId: 'wp-001' }, /tidak diizinkan untuk peran atau unit/);

  const incoming = { id: 'emp-014', role: 'LEADER', unit: 'CCTV_ACS', name: 'Yulfi Hendri' };
  actors.push(incoming);
  try {
    state = apply(state, 'emp-014', 'ACCEPT_CHANGE', { planId: 'wp-001' });
  } finally {
    actors.splice(actors.indexOf(incoming), 1);
  }
  assert.equal(plan().leaderId, 'emp-014');
  assert.deepEqual(plan().memberIds, ['member']);
  assert.equal(plan().documents.at(-1).status, 'EFFECTIVE');
  assert.equal(plan().documents.at(-1).acceptedBy, 'Yulfi Hendri');
  const older = plan().documents.slice(0, -1);
  assert.ok(older.every(d => VTDomain.documentLocked(plan(), d)), 'older versions are locked as history');
  assert.equal(VTDomain.documentLocked(plan(), plan().documents.at(-1)), false, 'the newest version stays open');
  assert.equal(older[0].snapshot.leader.id, 'leader', 'issued snapshots are immutable');
});

test('a demoted leader keeps member rights, and only the named leader decides a personnel addendum', () => {
  let state = createInitialState();
  const plan = () => state.plans.find(p => p.id === 'wp-001');
  const base = { planId: 'wp-001', reason: 'Rotasi personel.', leaderId: 'member', memberIds: ['leader', 'emp-014'] };
  state = apply(state, 'pm-cctv', 'REQUEST_PERSONNEL_CHANGE', base);
  // the outgoing leader may not decide on an addendum addressed to someone else
  rejected(state, 'leader', 'REJECT_CHANGE', { planId: 'wp-001', reason: 'Tidak setuju.' }, /ditunjuk pada adendum personel/);
  // the PM withdraws instead of rejecting on the leader's behalf
  let withdrawn = apply(state, 'pm-cctv', 'WITHDRAW_CHANGE', { planId: 'wp-001', reason: 'Usulan direvisi.' });
  assert.equal(withdrawn.plans.find(p => p.id === 'wp-001').change.status, 'WITHDRAWN');
  assert.equal(withdrawn.plans.find(p => p.id === 'wp-001').documents.at(-1).status, 'WITHDRAWN');

  state = apply(state, 'member', 'ACCEPT_CHANGE', { planId: 'wp-001' });
  assert.equal(plan().leaderId, 'member');
  // the demoted leader is now an ordinary member: member actions allowed, leader actions refused
  state = apply(state, 'leader', 'REPORT_INCIDENT', { planId: 'wp-001', category: 'K3_RINGAN', severity: 'RENDAH', description: 'Kabel tergeletak di jalur.' });
  rejected(state, 'leader', 'REQUEST_COMPLETE', { planId: 'wp-001', reportText: 'x', obstacleText: 'y' }, /tidak diizinkan untuk peran atau unit/);
  rejected(state, 'leader', 'REPORT_OVERTIME', { planId: 'wp-001', hours: 2, reason: 'Lembur.' }, /tidak diizinkan untuk peran atau unit/);
  state = apply(state, 'member', 'REPORT_OVERTIME', { planId: 'wp-001', hours: 2, reason: 'Menyelesaikan instalasi.' });
});

test('TOGGLE_TASK preserves report text', () => {
  let state = createInitialState();
  state.demoDate = '2026-09-30';
  const day = state.plans.find(p => p.id === 'wp-001').days[0];
  state = apply(state, 'leader', 'TOGGLE_TASK', { planId: 'wp-001', dayId: day.id, taskId: day.tasks[0].id, text: 'Sedang dikerjakan' });
  const updatedDay = state.plans.find(p => p.id === 'wp-001').days[0];
  assert.equal(updatedDay.reportText, 'Sedang dikerjakan');
});
