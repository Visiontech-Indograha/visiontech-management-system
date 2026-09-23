window.VTDomain = (() => {
// Prototype domain only: the browser simulates authorization and transactions.
// Production must enforce these same rules in the API/database.
const DEMO_TODAY = '2026-09-21';
const ATTENDANCE_RADIUS = 100;
const SHIFT_START = '08:00', SHIFT_END = '17:00';
// Attendance keeps the simulated date but the real time of day, so "terlambat" and
// "pulang lebih awal" describe what actually happened instead of a fixed 08.00/17.00.
const clockOn = date => {
  const now = new Date();
  const hhmm = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
  return { iso: new Date(`${date}T${hhmm}:00+07:00`).toISOString(), hhmm };
};

const actors = [
  { id: 'pm-cctv', name: 'Ramadani', role: 'PM', unit: 'CCTV_ACS', position: 'PM CCTV ACS', initials: 'RA' },
  { id: 'pm-wall', name: 'Handoko', role: 'PM', unit: 'WALL_DISPLAY', position: 'PM Wall Display', initials: 'HA' },
  { id: 'leader', name: 'Rouzi Dewantoro', role: 'LEADER', unit: 'CCTV_ACS', position: 'Senior Technician · Ketua tim', initials: 'RD' },
  { id: 'emp-032', name: 'Ahmadi', role: 'LEADER', unit: 'WALL_DISPLAY', position: 'Engineer - Ketua tim simulasi', initials: 'AH' },
  { id: 'member', name: 'Rusyidi Siregar', role: 'MEMBER', unit: 'CCTV_ACS', position: 'Technician', initials: 'RS' },
  { id: 'finance', name: 'Sri Wildani', role: 'FINANCE', unit: 'FINANCE_ACCOUNTING', position: 'Accounting', initials: 'SW' },
  { id: 'hr', name: 'Petugas HR (simulasi)', role: 'HR', unit: 'OPERATIONS', position: 'Pengelola SDM', initials: 'HR' },
  { id: 'asset', name: 'Hernita', role: 'ASSET', unit: 'BIZDEV_COMMERCIAL', position: 'Logistic & Import', initials: 'HE' },
  { id: 'ops', name: 'Ade Candra', role: 'OPS', unit: 'OPERATIONS', position: 'Operational Manager', initials: 'AC' },
];

const units = [
  { code: 'DIRECTOR', name: 'Direksi', lead: 'Sutono', description: 'Arah dan keputusan organisasi', parent: null },
  { code: 'OPERATIONS', name: 'Operasional', lead: 'Ade Candra', description: 'Koordinasi lintas unit dan serah terima kewenangan', parent: 'DIRECTOR' },
  { code: 'FINANCE_ACCOUNTING', name: 'Finance & Accounting', lead: 'Sri Wildani', description: 'Keuangan, rekap absensi, dan pemeriksaan', parent: 'OPERATIONS' },
  { code: 'ENGINEERING', name: 'Engineering', lead: 'M Pinto Nurhadi', description: 'Rekayasa dan dukungan teknis', parent: 'OPERATIONS' },
  { code: 'SITE_SUPPORT', name: 'Site Support', lead: 'Aris Setyawan', description: 'Dukungan pelaksanaan di lokasi', parent: 'OPERATIONS' },
  { code: 'BIZDEV_SOLUTION', name: 'Business Development A', lead: 'Doni Effendi', description: 'Pengembangan bisnis dan software; nama unit sementara', parent: 'OPERATIONS' },
  { code: 'CCTV_ACS', name: 'CCTV & ACS', lead: 'Ramadani', description: 'Proyek CCTV dan access control', parent: 'OPERATIONS' },
  { code: 'BIZDEV_COMMERCIAL', name: 'Business Development B', lead: 'Megawati Thio', description: 'Komersial, tender, logistik & impor; nama unit sementara', parent: 'OPERATIONS' },
  { code: 'HSE', name: 'HSE', lead: 'Rafael Ganecha', description: 'Kesehatan, keselamatan, dan kelayakan kerja', parent: 'OPERATIONS' },
  { code: 'WALL_DISPLAY', name: 'Wall Display', lead: 'Handoko', description: 'Proyek video wall dan display', parent: 'OPERATIONS' },
];

const roster = [
  ['emp-001', 'Sutono', 'Direktur', 'DIRECTOR'], ['ops', 'Ade Candra', 'Operational Manager', 'OPERATIONS'],
  ['finance', 'Sri Wildani', 'Accounting', 'FINANCE_ACCOUNTING'], ['emp-004', 'Stella Huang', 'Junior Accounting', 'FINANCE_ACCOUNTING'], ['emp-005', 'Dara Diva Herdita', 'Junior Accounting', 'FINANCE_ACCOUNTING'],
  ['emp-006', 'M Pinto Nurhadi', 'Engineering', 'ENGINEERING'], ['emp-007', 'Septyan Dwi N', 'Technician', 'ENGINEERING'],
  ['emp-008', 'Aris Setyawan', 'Site Support Supervisor', 'SITE_SUPPORT'], ['emp-009', 'Akmal Yusuf', 'Technician', 'SITE_SUPPORT'],
  ['emp-010', 'Doni Effendi', 'Business Development', 'BIZDEV_SOLUTION'], ['emp-011', 'M Teguh Wicaksono', 'Software Development', 'BIZDEV_SOLUTION'],
  ['pm-cctv', 'Ramadani', 'PM CCTV ACS', 'CCTV_ACS'], ['leader', 'Rouzi Dewantoro', 'Senior Technician', 'CCTV_ACS'], ['emp-014', 'Yulfi Hendri', 'System Engineer', 'CCTV_ACS'],
  ['member', 'Rusyidi Siregar', 'Technician', 'CCTV_ACS'], ['emp-016', 'Yuli K', 'Technician', 'CCTV_ACS'], ['emp-017', 'Syafrudin', 'Technician', 'CCTV_ACS'], ['emp-018', 'Yuli C', 'Technician', 'CCTV_ACS'], ['emp-019', 'Martaferri MB', 'Technician', 'CCTV_ACS'], ['emp-020', 'Mukhadir', 'Technician', 'CCTV_ACS'], ['emp-021', 'Raimon Albert', 'Technician', 'CCTV_ACS'], ['emp-022', 'Azman', 'Technician', 'CCTV_ACS'], ['emp-023', 'Asrul Mulya', 'Technician', 'CCTV_ACS'], ['emp-024', 'M Ananda Jalil Ishaq', 'Technician', 'CCTV_ACS'],
  ['emp-025', 'Megawati Thio', 'Business Development', 'BIZDEV_COMMERCIAL'], ['asset', 'Hernita', 'Logistic & Import', 'BIZDEV_COMMERCIAL'], ['emp-027', 'Natali', 'ADM Tender', 'BIZDEV_COMMERCIAL'],
  ['emp-028', 'Rafael Ganecha', 'HES Corporate', 'HSE'], ['emp-029', 'M Fajar Dwithya', 'HSE Coordinate', 'HSE'], ['emp-030', 'Marta', 'ADM HSE', 'HSE'],
  ['pm-wall', 'Handoko', 'PM Wall Display', 'WALL_DISPLAY'], ['emp-032', 'Ahmadi', 'Engineer', 'WALL_DISPLAY'], ['emp-033', 'Shofan Rizki S', 'Engineer', 'WALL_DISPLAY'],
];

// Timestamp + cryptographic randomness, shaped as UUIDv7 for mock entities.
// Seed IDs remain friendly labels; a real deployment generates IDs server-side.
const id = () => {
  const time = Date.now().toString(16).padStart(12, '0');
  const bytes = new Uint8Array(10);
  globalThis.crypto.getRandomValues(bytes);
  const random = Array.from(bytes, x => x.toString(16).padStart(2, '0')).join('');
  return `${time.slice(0, 8)}-${time.slice(8)}-7${random.slice(0, 3)}-${(8 + (bytes[2] & 3)).toString(16)}${random.slice(3, 6)}-${random.slice(6, 18)}`;
};
let currentDemoDate = null;
const timestamp = () => currentDemoDate ? new Date(currentDemoDate + 'T' + new Date().toTimeString().split(' ')[0]).toISOString() : new Date().toISOString();
const clone = value => structuredClone(value);
const fail = message => { throw new Error(message); };
const requireThat = (condition, message) => { if (!condition) fail(message); };
const text = value => String(value || '').trim();
const dateValid = value => /^\d{4}-\d{2}-\d{2}$/.test(value || '') && Number.isFinite(new Date(value).getTime()) && new Date(value).toISOString().slice(0, 10) === value;
const dateRange = (start, end) => {
  requireThat(dateValid(start) && dateValid(end) && start <= end, 'Periode tanggal tidak valid.');
  const count = Math.round((new Date(end) - new Date(start)) / 86400000) + 1;
  requireThat(count <= 31, 'Satu work plan pada prototype dibatasi 31 hari.');
  return Array.from({ length: count }, (_, i) => new Date(new Date(start).getTime() + i * 86400000).toISOString().slice(0, 10));
};
const makeDay = (date, index = 0) => ({
  id: id(), date, title: ['Persiapan & survei lokasi', 'Instalasi & konfigurasi', 'Pengujian & serah terima'][index % 3],
  tasks: [{ id: id(), title: 'Briefing keselamatan dan pemeriksaan area', done: false }, { id: id(), title: 'Pelaksanaan pekerjaan sesuai rencana', done: false }],
  reportStatus: 'DRAFT', reportText: '', obstacleText: '', evidence: [],
});
const pendingChange = plan => ['PENDING_PM', 'AWAITING_LEADER_ACCEPTANCE'].includes(plan.change?.status);
const activeEmployee = employee => employee?.status === 'ACTIVE' && !employee.deletedAt;
const eligible = (state, employeeId) => activeEmployee(state.employees.find(e => e.id === employeeId));
const snapshot = (state, plan) => ({
  title: plan.title, unit: plan.unit, location: plan.location, startDate: plan.startDate, endDate: plan.endDate,
  pm: clone(state.employees.find(e => e.id === plan.pmId) ? (({ id, name, position }) => ({ id, name, position }))(state.employees.find(e => e.id === plan.pmId)) : { id: plan.pmId }),
  leader: clone(state.employees.find(e => e.id === plan.leaderId) ? (({ id, name, position }) => ({ id, name, position }))(state.employees.find(e => e.id === plan.leaderId)) : { id: plan.leaderId }),
  members: plan.memberIds.map(memberId => { const e = state.employees.find(x => x.id === memberId); return { id: memberId, name: e?.name, position: e?.position }; }),
  days: plan.days.map(day => ({ date: day.date, title: day.title, tasks: day.tasks.map(task => ({ title: task.title })) })),
  attachments: clone(plan.attachments || []),
  assets: state.assets.filter(a => a.planId === plan.id).map(a => ({ name: a.name, code: a.code, kind: a.kind, driver: a.driver })),
  description: plan.description || 'Pelaksanaan pekerjaan sesuai rincian harian dan ketentuan keselamatan kerja.',
});

function createInitialState() {
  const employees = roster.map(([employeeId, name, position, unit], index) => ({
    id: employeeId, name, position, unit, status: 'ACTIVE', email: `person${String(index + 1).padStart(2, '0')}@example.test`, phone: '—', joinDate: '2024-02-01', deletedAt: null,
    assignmentHistory: [{ id: `assignment-${employeeId}`, position, unit, from: '2024-02-01', to: null }],
    documents: index % 3 === 0 || ['leader', 'member'].includes(employeeId) ? [{ id: `doc-${employeeId}`, type: 'Sertifikat K3', numberMasked: 'DEMO-****1234', expiry: index % 2 ? '2026-10-02' : '2027-05-01', status: 'VERIFIED', lifecycle: 'CURRENT' }] : [],
  }));
  const definitions = [
    ['wp-001', '012/SK-CCTV-ACS/2026', 'Instalasi CCTV · Gedung Merdeka', 'CCTV_ACS', 'Gedung Merdeka, Medan', '2026-09-21', '2026-09-23', 'IN_PROGRESS', 'pm-cctv', 'leader', ['member', 'emp-014', 'emp-016']],
    ['wp-002', 'DRAFT-CCTV-013', 'Pemasangan access control · Kantor Pusat', 'CCTV_ACS', 'Kantor Pusat, Medan', '2026-10-05', '2026-10-06', 'DRAFT', 'pm-cctv', 'leader', ['member', 'emp-017']],
    ['wp-003', '014/SK-CCTV-ACS/2026', 'Pemeliharaan CCTV · Warehouse', 'CCTV_ACS', 'Warehouse Tanjung Morawa', '2026-09-28', '2026-09-29', 'PUBLISHED', 'pm-cctv', 'leader', ['member', 'emp-020']],
    ['wp-004', '007/SK-WD/2026', 'Video wall · Command Center', 'WALL_DISPLAY', 'Command Center, Medan', '2026-09-24', '2026-09-26', 'ACCEPTED', 'pm-wall', 'emp-032', ['emp-033']],
    ['wp-005', '006/SK-WD/2026', 'Kalibrasi display · Ruang Kontrol', 'WALL_DISPLAY', 'Ruang Kontrol, Medan', '2026-09-14', '2026-09-15', 'COMPLETED', 'pm-wall', 'emp-032', ['emp-033']],
    ['wp-006', '015/SK-CCTV-ACS/2026', 'Survei jaringan · Site Binjai', 'CCTV_ACS', 'Site Binjai', '2026-10-08', '2026-10-08', 'APPEALED', 'pm-cctv', 'leader', ['member', 'emp-019']],
  ];
  const chunkDays = (arr, size) => Array.from({length: Math.ceil(arr.length/size)}, (v,i) => arr.slice(i*size, i*size+size));
  const plans = definitions.map(([planId, number, title, unit, location, startDate, endDate, status, pmId, leaderId, memberIds]) => {
    const days = dateRange(startDate, endDate).map(makeDay);
    const weeks = days.length >= 7 ? chunkDays(days, 7).map((chunk, i) => ({ id: id(), name: 'Laporan Mingguan ' + (i+1), dayIds: chunk.map(d=>d.id), status: 'DRAFT', reportText: '', obstacleText: '', reviewNote: '' })) : [];
    return {
      id: planId, number, title, unit, location, startDate, endDate, status, pmId, leaderId, memberIds, revision: 1, rowVersion: 1,
      days, weeks, finalReport: { status: 'DRAFT', reportText: '', obstacleText: '', reviewNote: '' }, documents: [], change: null, deletedAt: null, activity: [],
    };
  });
  const state = { plans, employees, assets: [
    { id: 'asset-001', name: 'Toyota Avanza', kind: 'VEHICLE', vehicleType: 'CAR', code: 'DEMO-V01', status: 'IN_USE', planId: 'wp-001', condition: 'Baik', driver: 'Rusyidi Siregar', driverId: 'member' },
    { id: 'asset-002', name: 'LAN Cable Tester', kind: 'TOOL', code: 'TOOL-014', status: 'IN_USE', planId: 'wp-001', condition: 'Baik', driver: null, driverId: null },
    { id: 'asset-003', name: 'Suzuki APV', kind: 'VEHICLE', vehicleType: 'CAR', code: 'DEMO-V02', status: 'AVAILABLE', planId: null, condition: 'Baik', driver: null, driverId: null },
    { id: 'asset-motor', name: 'Honda Supra', kind: 'VEHICLE', vehicleType: 'MOTORCYCLE', code: 'DEMO-M01', status: 'AVAILABLE', planId: null, condition: 'Baik', driver: null },
    { id: 'asset-004', name: 'Bor Bosch + toolkit', kind: 'TOOL', code: 'TOOL-022', status: 'AVAILABLE', planId: null, condition: 'Baik', driver: null },
    { id: 'asset-005', name: 'Display Calibrator', kind: 'TOOL', code: 'TOOL-031', status: 'RESERVED', planId: 'wp-004', condition: 'Baik', driver: null },
    { id: 'asset-006', name: 'Tangga aluminium 4 m', kind: 'TOOL', code: 'TOOL-008', status: 'AVAILABLE', planId: null, condition: 'Baik', driver: null },
    { id: 'asset-new-01', name: 'Daihatsu Gran Max Pick Up', kind: 'VEHICLE', vehicleType: 'CAR', code: 'DEMO-V03', status: 'AVAILABLE', planId: null, condition: 'Baik', driver: null },
    { id: 'asset-new-02', name: 'Toyota Hilux Double Cabin', kind: 'VEHICLE', vehicleType: 'CAR', code: 'DEMO-V04', status: 'AVAILABLE', planId: null, condition: 'Baik', driver: null },
    { id: 'asset-new-03', name: 'Mitsubishi L300', kind: 'VEHICLE', vehicleType: 'CAR', code: 'DEMO-V05', status: 'AVAILABLE', planId: null, condition: 'Baik', driver: null },
    { id: 'asset-new-04', name: 'Suzuki Carry Pick Up', kind: 'VEHICLE', vehicleType: 'CAR', code: 'DEMO-V06', status: 'AVAILABLE', planId: null, condition: 'Baik', driver: null },
    { id: 'asset-new-05', name: 'Honda HR-V', kind: 'VEHICLE', vehicleType: 'CAR', code: 'DEMO-V07', status: 'AVAILABLE', planId: null, condition: 'Pintu kiri lecet ringan', driver: null },
    { id: 'asset-new-06', name: 'Yamaha Vixion', kind: 'VEHICLE', vehicleType: 'MOTORCYCLE', code: 'DEMO-M02', status: 'AVAILABLE', planId: null, condition: 'Baik', driver: null },
    { id: 'asset-new-07', name: 'Honda Vario 160', kind: 'VEHICLE', vehicleType: 'MOTORCYCLE', code: 'DEMO-M03', status: 'AVAILABLE', planId: null, condition: 'Baik', driver: null },
    { id: 'asset-new-08', name: 'Yamaha NMAX', kind: 'VEHICLE', vehicleType: 'MOTORCYCLE', code: 'DEMO-M04', status: 'AVAILABLE', planId: null, condition: 'Spion kanan retak', driver: null },
    { id: 'asset-new-09', name: 'Honda Beat Street', kind: 'VEHICLE', vehicleType: 'MOTORCYCLE', code: 'DEMO-M05', status: 'AVAILABLE', planId: null, condition: 'Baik', driver: null },
    { id: 'asset-new-10', name: 'Honda CB150R', kind: 'VEHICLE', vehicleType: 'MOTORCYCLE', code: 'DEMO-M06', status: 'AVAILABLE', planId: null, condition: 'Baik', driver: null },
  ], attendance: [
    { id: 'att-001', employeeId: 'member', date: DEMO_TODAY, checkIn: '2026-09-21T00:48:00Z', checkOut: null, source: 'MOBILE', site: 'Gedung Merdeka', distance: 142, radius: 100, status: 'NEEDS_REVIEW', explanation: 'Pintu masuk proyek dialihkan ke gerbang belakang.', reviewNote: '' },
    { id: 'att-002', employeeId: 'leader', date: DEMO_TODAY, checkIn: '2026-09-21T00:42:00Z', checkOut: null, source: 'MOBILE', site: 'Gedung Merdeka', distance: 24, radius: 100, status: 'AUTO_VALID', explanation: '', reviewNote: '' },
    { id: 'att-003', employeeId: 'emp-014', date: DEMO_TODAY, checkIn: '2026-09-21T00:51:00Z', checkOut: null, source: 'MACHINE', site: 'Gedung Merdeka', distance: 0, radius: 100, status: 'AUTO_VALID', explanation: '', reviewNote: '' },
    { id: 'att-004', employeeId: 'emp-032', date: DEMO_TODAY, checkIn: '2026-09-21T00:40:00Z', checkOut: '2026-09-21T09:05:00Z', source: 'MACHINE', site: 'Kantor Pusat', distance: 0, radius: 100, status: 'AUTO_VALID', explanation: '', reviewNote: '' },
  ], audit: [], offline_queue: [], incident_reports: [], overtime_logs: [] };
  plans.forEach(plan => {
    if (plan.status !== 'DRAFT') plan.documents.push({ id: `document-${plan.id}`, number: plan.number, kind: 'INITIAL_ORDER', version: 1, status: 'EFFECTIVE', issuedBy: employees.find(e => e.id === plan.pmId).name, issuedAt: '2026-09-18T02:00:00Z', acceptedBy: ['IN_PROGRESS', 'ACCEPTED', 'COMPLETED'].includes(plan.status) ? employees.find(e => e.id === plan.leaderId).name : null, snapshot: snapshot(state, plan) });
    plan.activity.push({ id: `activity-${plan.id}`, at: '2026-09-18T02:00:00Z', actor: employees.find(e => e.id === plan.pmId).name, action: 'Data simulasi disiapkan', detail: 'Skenario demonstrasi; bukan transaksi perusahaan.' });
    if (plan.status === 'COMPLETED') plan.days.forEach(day => { day.tasks.forEach(task => { task.done = true; }); day.reportStatus = 'APPROVED'; day.reportText = 'Kalibrasi dan pengujian selesai. Hasil sesuai target.'; day.evidence = ['Foto pengujian (simulasi)']; day.submittedBy = employees.find(e => e.id === plan.leaderId).name; day.submittedAt = '2026-09-15T15:00:00Z'; day.reviewedBy = employees.find(e => e.id === plan.pmId).name; day.reviewedAt = '2026-09-15T16:00:00Z'; day.reviewNote = 'Baik, disetujui.'; });
    if (plan.status === 'COMPLETED') plan.finalReport = { status: 'APPROVED', reportText: 'Seluruh tahap selesai dengan baik.', obstacleText: 'Tidak ada kendala berarti.', reviewNote: 'Pekerjaan dinyatakan selesai.', submittedBy: employees.find(e => e.id === plan.leaderId).name, submittedAt: '2026-09-15T15:00:00Z', reviewedBy: employees.find(e => e.id === plan.pmId).name, reviewedAt: '2026-09-15T16:00:00Z' };
  });
  plans[0].days[0].tasks[0].done = true;
  plans[0].days[0].reportText = 'Survei lokasi dan briefing K3 selesai. Instalasi sedang berjalan.';
  plans[0].days[0].evidence = ['briefing-area.jpg (simulasi)'];
  plans[5].appealReason = 'Akses lokasi perlu dikonfirmasi kembali dengan pelanggan.';
  state.audit.push({ id: 'audit-seed', at: '2026-09-21T00:00:00Z', actor: 'Sistem simulasi', action: 'SEED', entity: 'Workspace', detail: 'Data dummy siap untuk pengujian alur.' });
  state.demoDate = DEMO_TODAY;
  state.schemaVersion = 4;
  state.revision = 0;
  state.employees.forEach(e => {
    e.documents.forEach(d => { d.attachment = { id: 'sample-certificate', name: 'sertifikat-k3-contoh.svg', type: 'image/svg+xml' }; });
    if (['member', 'emp-032'].includes(e.id)) { e.documents.push({ id: `sim-${e.id}`, type: 'SIM A', numberMasked: 'DEMO-****9999', expiry: '2028-01-01', status: 'VERIFIED', lifecycle: 'CURRENT', attachment: { id: 'sample-certificate', name: 'sim-contoh.svg', type: 'image/svg+xml' }, uploadedAt: '2026-01-01T00:00:00Z', verifiedAt: '2026-01-02T00:00:00Z', verifiedBy: 'Petugas HR (simulasi)' }); }
  });
  state.plans.forEach(p => {
    p.attachments = [];
    p.days.forEach(d => { d.evidence = d.evidence.map(() => ({ id: 'sample-evidence', name: 'bukti-lapangan-contoh.svg', type: 'image/svg+xml' })); });
    p.documents.forEach(d => { if (!d.acceptedBy) d.status = 'AWAITING_ACCEPTANCE'; else d.acceptedAt = '2026-09-19T02:00:00Z'; });
  });
  return state;
}

const permissions = {
  PM: ['REQUEST_PERSONNEL_CHANGE', 'WITHDRAW_CHANGE', 'CREATE_PLAN', 'EDIT_DRAFT', 'SAVE_DAY', 'PUBLISH', 'REVISE', 'REVIEW_REPORT', 'REVIEW_WEEKLY', 'APPROVE_CHANGE', 'REJECT_CHANGE', 'APPROVE_COMPLETE', 'RETURN_COMPLETE', 'CANCEL_PLAN', 'DELETE_PLAN', 'RESTORE_PLAN', 'RESERVE_ASSET', 'RESOLVE_INCIDENT', 'REVIEW_OVERTIME'],
  LEADER: ['ACCEPT', 'APPEAL', 'START', 'TOGGLE_TASK', 'CHECK_ASSET', 'SAVE_REPORT', 'SUBMIT_REPORT', 'SAVE_WEEKLY', 'SUBMIT_WEEKLY', 'REQUEST_CHANGE', 'ACCEPT_CHANGE', 'REJECT_CHANGE', 'REQUEST_COMPLETE', 'RETURN_ASSET', 'REPORT_INCIDENT', 'REPORT_OVERTIME'],
  MEMBER: ['CHECK_ASSET', 'REPORT_INCIDENT'],
  FINANCE: ['REVIEW_ATTENDANCE'],
  HR: ['UPLOAD_DOCUMENT', 'VERIFY_DOCUMENT', 'PROMOTE', 'OFFBOARD', 'RESTORE_EMPLOYEE'],
  ASSET: ['RESERVE_ASSET', 'RETURN_ASSET', 'VERIFY_RETURN', 'RESOLVE_INCIDENT'],
  OPS: ['REQUEST_PERSONNEL_CHANGE', 'WITHDRAW_CHANGE', 'CREATE_PLAN', 'EDIT_DRAFT', 'SAVE_DAY', 'PUBLISH', 'REVISE', 'REVIEW_REPORT', 'APPROVE_CHANGE', 'REJECT_CHANGE', 'APPROVE_COMPLETE', 'RETURN_COMPLETE', 'CANCEL_PLAN', 'DELETE_PLAN', 'RESTORE_PLAN', 'RESERVE_ASSET', 'PROMOTE', 'OFFBOARD', 'RESOLVE_INCIDENT', 'REVIEW_OVERTIME'],
};
const aliases = { managePlans: 'CREATE_PLAN', reviewReports: 'REVIEW_REPORT', manageEmployees: 'OFFBOARD', reviewAttendance: 'REVIEW_ATTENDANCE', manageAssets: 'VERIFY_RETURN' };
function can(actor, permission, unit) {
  if (!actor) return false;
  if (permission === 'SET_DEMO_DATE') return true;
  if (permission === 'SAVE_ATTACHMENTS') return ['PM', 'OPS'].includes(actor.role) && (actor.role === 'OPS' || !unit || actor.unit === unit);
  if (permission === 'RELEASE_ASSET') return ['PM', 'OPS', 'ASSET'].includes(actor.role) && (actor.role !== 'PM' || !unit || actor.unit === unit);
  if (permission === 'UPDATE_EMPLOYEE') return actor.role === 'HR';
  if (permission === 'viewAll') return actor.role === 'OPS';
  if (permission === 'viewSensitive') return actor.role === 'HR';
  if (['CHECK_IN', 'CHECK_OUT', 'EXPLAIN_ATTENDANCE'].includes(permission)) return true;
  if (permission === 'UPLOAD_DOCUMENT') return true;
  permission = aliases[permission] || permission;
  if (actor.role === 'PM' && unit && actor.unit !== unit) return false;
  if (actor.role === 'LEADER' && unit && actor.unit !== unit) return false;
  return permissions[actor.role]?.includes(permission) || false;
}

function visiblePlans(state, actor, { includeArchived = false } = {}) {
  if (!actor) return [];
  if (actor.role === 'OPS') return state.plans.filter(plan => !plan.deletedAt || includeArchived);
  if (actor.role === 'ASSET') return state.plans.filter(plan => !plan.deletedAt && plan.status !== 'DRAFT');
  if (actor.role === 'PM') return state.plans.filter(plan => (!plan.deletedAt || includeArchived) && plan.unit === actor.unit);
  if (['LEADER', 'MEMBER'].includes(actor.role)) return state.plans.filter(plan => !plan.deletedAt && plan.status !== 'DRAFT' && (plan.leaderId === actor.id || plan.memberIds.includes(actor.id) || (plan.change?.status === 'AWAITING_LEADER_ACCEPTANCE' && plan.change.leaderId === actor.id)));
  return [];
}

function checkMembers(state, plan) {
  requireThat(eligible(state, plan.leaderId), 'Ketua tim harus karyawan aktif.');
  requireThat(plan.leaderId !== plan.pmId, 'PM penerbit tidak boleh menerima SK sebagai ketua tim sendiri.');
  requireThat(plan.memberIds.length > 0, 'Pilih minimal satu anggota tim.');
  requireThat(!plan.memberIds.includes(plan.leaderId), 'Ketua tim tidak perlu didaftarkan lagi sebagai anggota.');
  
  const activePlans = state.plans.filter(p => p.id !== plan.id && !p.deletedAt && !['DRAFT', 'CANCELLED', 'COMPLETED'].includes(p.status));
  const overlapping = activePlans.filter(p => p.startDate <= plan.endDate && p.endDate >= plan.startDate);
  
  for (const employeeId of [plan.leaderId, ...plan.memberIds]) {
    const employee = state.employees.find(e => e.id === employeeId);
    requireThat(activeEmployee(employee), 'Semua anggota tim harus aktif.');
    requireThat(employee.unit === plan.unit, 'Personel lintas unit memerlukan persetujuan pelepasan; gunakan personel unit yang sama pada prototype ini.');
    
    const conflict = overlapping.find(p => p.leaderId === employeeId || p.memberIds.includes(employeeId));
    if (conflict) {
      throw new Error(`Personel ${employee?.name} bertabrakan dengan jadwal pekerjaan aktif: ${conflict.title}.`);
    }
  }
}
function freeAsset(asset) {
  asset.status = 'AVAILABLE'; asset.planId = null; asset.driver = null; asset.driverId = null; asset.driverChecked = false;
}

function checkSchedule(state, plan, end = plan.endDate) {
  const people = new Set([plan.leaderId, ...plan.memberIds]);
  const conflict = state.plans.find(other => other.id !== plan.id && !other.deletedAt && ['PUBLISHED', 'ACCEPTED', 'IN_PROGRESS', 'COMPLETION_REVIEW'].includes(other.status) && other.startDate <= end && other.endDate >= plan.startDate && [other.leaderId, ...other.memberIds].some(employeeId => people.has(employeeId)));
  requireThat(!conflict, `Jadwal personel bertabrakan dengan ${conflict?.number || 'work plan lain'}.`);
  
  // Check vehicle SIM expiry during schedule changes
  const assets = state.assets.filter(a => a.planId === plan.id && a.kind === 'VEHICLE');
  for (const asset of assets) {
    if (asset.driverId) {
      const driver = state.employees.find(e => e.id === asset.driverId);
      if (!driver) continue;
      const requiredSim = asset.vehicleType === 'MOTORCYCLE' ? 'SIM C' : 'SIM A';
      const sim = driver.documents.find(d => d.type === requiredSim && d.lifecycle === 'CURRENT');
      requireThat(sim, `Karyawan ${driver.name} tidak memiliki ${requiredSim} aktif dalam profilnya.`);
      requireThat(!sim.expiry || sim.expiry >= end, `Masa berlaku ${requiredSim} ${driver.name} kedaluwarsa sebelum jadwal selesai.`);
    }
  }
}

function transition(input, actor, type, payload = {}) {
  try {
    requireThat(actors.some(a => a.id === actor?.id && a.role === actor.role && a.unit === actor.unit), 'Aktor simulasi tidak dikenal.');
    const actorEmployee = input.employees.find(e => e.id === actor.id);
    requireThat(!actorEmployee || activeEmployee(actorEmployee), 'Akun karyawan nonaktif. Akses simulasi telah dicabut.');
    const state = clone(input);
    currentDemoDate = state.demoDate;
    const plan = payload.planId ? state.plans.find(p => p.id === payload.planId) : null;
    if (payload.planId) requireThat(plan, 'Work plan tidak ditemukan.');
    // The person named as the new leader decides on their own personnel addendum, whatever role they hold today.
    const incomingLeader = plan?.change?.type === 'PERSONNEL' && plan.change.status === 'AWAITING_LEADER_ACCEPTANCE' && plan.change.leaderId === actor.id && ['ACCEPT_CHANGE', 'REJECT_CHANGE'].includes(type);
    // Authority follows the assignment: the SK's named leader acts as leader, and a former leader who
    // stayed on as an ordinary member keeps member rights on that plan.
    const acting = plan && ['LEADER', 'MEMBER'].includes(actor.role)
      ? { ...actor, role: plan.leaderId === actor.id ? 'LEADER' : plan.memberIds.includes(actor.id) ? 'MEMBER' : actor.role }
      : actor;
    requireThat(incomingLeader || can(acting, type, plan?.unit || payload.unit), 'Tindakan tidak diizinkan untuk peran atau unit Anda.');
    if (plan) {
      requireThat(!plan.deletedAt || type === 'RESTORE_PLAN', 'Work plan sudah diarsipkan. Pulihkan dahulu.');
      if (payload.rowVersion !== undefined) requireThat(payload.rowVersion === plan.rowVersion, 'Revisi berubah. Muat ulang sebelum menyimpan.');
      if (acting.role === 'LEADER' && !incomingLeader) requireThat(plan.leaderId === actor.id, 'Hanya ketua tim yang ditunjuk dapat melakukan tindakan ini.');
    }
    let message = 'Perubahan tersimpan.';
    let entity = plan?.number || payload.employeeId || payload.assetId || payload.attendanceId || 'Workspace';
    const requireStatus = statuses => requireThat(plan && statuses.includes(plan.status), 'Tahap work plan belum sesuai untuk tindakan ini.');
    const getDay = () => { const day = plan?.days.find(d => d.id === payload.dayId); requireThat(day, 'Rincian hari tidak ditemukan.'); return day; };
    switch (type) {
      case 'SAVE_ATTACHMENTS': requireStatus(['DRAFT']); requireThat(Array.isArray(payload.attachments), 'Lampiran tidak valid.'); plan.attachments = clone(payload.attachments); message = 'Lampiran draft tersimpan.'; break;
      case 'RELEASE_ASSET': {
        const asset = state.assets.find(a => a.id === payload.assetId);
        requireThat(asset?.status === 'RESERVED' && asset.planId === plan?.id, 'Hanya reservasi yang belum dipakai dapat dilepas.');
        freeAsset(asset); message = 'Reservasi dilepas.'; break;
      }
      case 'UPDATE_EMPLOYEE': {
        const employee = state.employees.find(e => e.id === payload.employeeId);
        requireThat(activeEmployee(employee), 'Karyawan harus aktif.');
        requireThat(text(payload.email) && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(text(payload.email)), 'Email tidak valid.');
        requireThat(!payload.birthDate || dateValid(payload.birthDate), 'Tanggal lahir tidak valid.');
        requireThat(!payload.joinDate || dateValid(payload.joinDate), 'Tanggal masuk tidak valid.');
        ['email','phone','address','birthDate','joinDate','emergencyContact'].forEach(k => { if(payload[k] !== undefined) employee[k] = text(payload[k]); });
        message = 'Data karyawan diperbarui.'; break;
      }

      case 'SET_DEMO_DATE': requireThat(dateValid(payload.date), 'Tanggal simulasi tidak valid.'); state.demoDate = payload.date; message = 'Tanggal simulasi diperbarui. Jadwal pekerjaan tetap tersimpan.'; break;
      case 'CREATE_PLAN': {
        requireThat(text(payload.title) && text(payload.location), 'Judul dan lokasi wajib diisi.');
        requireThat(['CCTV_ACS', 'WALL_DISPLAY'].includes(payload.unit), 'Pilih unit proyek CCTV & ACS atau Wall Display.');
        const days = dateRange(payload.startDate, payload.endDate).map(makeDay);
        const chunkDays = (arr, size) => Array.from({length: Math.ceil(arr.length/size)}, (v,i) => arr.slice(i*size, i*size+size));
        const weeks = days.length >= 7 ? chunkDays(days, 7).map((chunk, i) => ({ id: id(), name: 'Laporan Mingguan ' + (i+1), dayIds: chunk.map(d=>d.id), status: 'DRAFT', reportText: '', obstacleText: '', reviewNote: '' })) : [];
        const newPlan = { id: id(), number: `DRAFT-${payload.unit === 'CCTV_ACS' ? 'CCTV' : 'WD'}-${state.plans.length + 1}`, title: text(payload.title), unit: payload.unit, location: text(payload.location), startDate: payload.startDate, endDate: payload.endDate, status: 'DRAFT', pmId: payload.unit === 'CCTV_ACS' ? 'pm-cctv' : 'pm-wall', leaderId: payload.leaderId, memberIds: [...new Set(payload.memberIds || [])], description: text(payload.description), attachments: [], revision: 1, rowVersion: 1, days, weeks, finalReport: { status: 'DRAFT', reportText: '', obstacleText: '', reviewNote: '' }, documents: [], change: null, activity: [], deletedAt: null };
        checkMembers(state, newPlan); state.plans.unshift(newPlan); entity = newPlan.number; message = 'Draft work plan dibuat. Tinjau rincian sebelum menerbitkan SK.'; break;
      }
      case 'EDIT_DRAFT': {
        requireStatus(['DRAFT']);
        const start = payload.startDate || plan.startDate, end = payload.endDate || plan.endDate;
        const dates = dateRange(start, end);
        plan.description = text(payload.description ?? plan.description);
        plan.title = text(payload.title ?? plan.title); plan.location = text(payload.location ?? plan.location);
        requireThat(plan.title && plan.location, 'Judul dan lokasi wajib diisi.');
        plan.startDate = start; plan.endDate = end;
        plan.leaderId = payload.leaderId || plan.leaderId; plan.memberIds = [...new Set(payload.memberIds || plan.memberIds)];
        plan.days = dates.map((date, index) => plan.days.find(day => day.date === date) || makeDay(date, index));
        const chunkDays = (arr, size) => Array.from({length: Math.ceil(arr.length/size)}, (v,i) => arr.slice(i*size, i*size+size));
        plan.weeks = plan.days.length >= 7 ? chunkDays(plan.days, 7).map((chunk, i) => plan.weeks[i] || ({ id: id(), name: 'Laporan Mingguan ' + (i+1), dayIds: chunk.map(d=>d.id), status: 'DRAFT', reportText: '', obstacleText: '', reviewNote: '' })) : [];
        checkMembers(state, plan); message = 'Draft dan rincian harian diperbarui.'; break;
      }
      case 'SAVE_DAY': {
        requireStatus(['DRAFT']); const day = getDay();
        requireThat(Array.isArray(payload.tasks) && payload.tasks.length > 0 && payload.tasks.length <= 30, 'Isi antara 1 sampai 30 tugas per hari.');
        requireThat(text(payload.title) && payload.tasks.every(task => text(task.title)), 'Judul hari dan setiap tugas wajib diisi.');
        day.title = text(payload.title); day.tasks = payload.tasks.map(task => ({ id: day.tasks.some(existing => existing.id === task.id) ? task.id : id(), title: text(task.title), done: false }));
        message = 'Rincian harian diperbarui.'; break;
      }
      case 'PUBLISH': {
        requireStatus(['DRAFT']); checkMembers(state, plan); checkSchedule(state, plan);
        requireThat(plan.days.length === dateRange(plan.startDate, plan.endDate).length && plan.days.every(day => text(day.title) && day.tasks.length && day.tasks.every(task => text(task.title))), 'Rincian harian belum lengkap.');
        plan.status = 'PUBLISHED';
        if (plan.number.startsWith('DRAFT')) plan.number = `${String(state.plans.filter(p => !p.number.startsWith('DRAFT')).length + 12).padStart(3, '0')}/SK-${plan.unit === 'CCTV_ACS' ? 'CCTV-ACS' : 'WD'}/2026`;
        plan.documents.push({ id: id(), number: plan.number, kind: plan.revision > 1 ? 'REVISION' : 'INITIAL_ORDER', version: plan.revision, status: 'AWAITING_ACCEPTANCE', issuedBy: actor.name, issuedAt: timestamp(), acceptedBy: null, snapshot: snapshot(state, plan) });
        message = 'SK diterbitkan dan snapshot tersimpan. Menunggu penerimaan ketua tim.'; break;
      }
      case 'ACCEPT': requireStatus(['PUBLISHED']); checkMembers(state, plan); checkSchedule(state, plan); plan.status = 'ACCEPTED'; plan.documents.at(-1).acceptedBy = actor.name; plan.documents.at(-1).acceptedAt = timestamp(); plan.documents.at(-1).status = 'EFFECTIVE'; message = 'SK diterima. Pekerjaan siap dimulai pada jadwalnya.'; break;
      case 'APPEAL': requireStatus(['PUBLISHED']); requireThat(text(payload.reason), 'Alasan banding wajib diisi.'); plan.status = 'APPEALED'; plan.appealReason = text(payload.reason); message = 'Banding dikirim ke PM. Dokumen lama tetap tercatat.'; break;
      case 'REVISE': requireStatus(['APPEALED']); plan.status = 'DRAFT'; plan.revision += 1; plan.documents.forEach(document => { document.status = 'SUPERSEDED'; }); message = 'Revisi draft dibuka. Terbitkan kembali setelah memperbaiki rincian.'; break;
      case 'START': requireStatus(['ACCEPTED']); requireThat(plan.startDate <= (state.demoDate || DEMO_TODAY), `Pekerjaan baru dapat dimulai pada ${plan.startDate}. Tanggal simulasi: ${state.demoDate || DEMO_TODAY}.`); checkMembers(state, plan); checkSchedule(state, plan); plan.status = 'IN_PROGRESS'; state.assets.filter(asset => asset.planId === plan.id && asset.status === 'RESERVED').forEach(asset => { if(asset.kind!=='VEHICLE'||asset.driverChecked) asset.status = 'IN_USE'; }); message = 'Pelaksanaan dimulai. Laporan harian kini tersedia.'; break;
      case 'TOGGLE_TASK': {
        requireStatus(['IN_PROGRESS']);
        const day = plan.days.find(d => d.id === payload.dayId); requireThat(day, 'Rincian hari tidak ditemukan.');
        requireThat(new Date(day.date) <= new Date(state.demoDate), 'Laporan hanya dapat diisi pada atau setelah tanggal pelaksanaan.');
        requireThat(['DRAFT', 'CHANGES_REQUESTED'].includes(day.reportStatus), 'Checklist tidak dapat diubah setelah laporan diserahkan.');
        const task = day.tasks.find(t => t.id === payload.taskId); requireThat(task, 'Tugas tidak ditemukan.');
        task.done = !task.done;
        if (payload.text !== undefined) day.reportText = text(payload.text);
        if (payload.obstacleText !== undefined) day.obstacleText = text(payload.obstacleText);
        message = task.done ? 'Tugas ditandai selesai.' : 'Tugas dikembalikan ke belum selesai.'; break;
      }
      case 'CHECK_ASSET': {
        const asset = state.assets.find(a => a.id === payload.assetId);
        const currentPlan = plan || state.plans.find(p => p.id === asset?.planId);
        requireThat(asset && asset.planId === currentPlan?.id && asset.kind === 'VEHICLE', 'Hanya kendaraan yang memerlukan pemeriksaan pengemudi.');
        requireThat(asset.driverId === actor.id, 'Hanya pengemudi yang ditunjuk yang dapat melakukan pemeriksaan.');
        requireThat(!asset.driverChecked, 'Kendaraan ini sudah diperiksa.');
        if (payload.decision === 'ACCEPT') {
          asset.driverChecked = true;
          if (currentPlan?.status === 'IN_PROGRESS') asset.status = 'IN_USE';
          message = 'Kendaraan telah diperiksa dan dinyatakan layak jalan.';
        } else {
          requireThat(text(payload.reason), 'Alasan banding kelayakan wajib diisi.');
          freeAsset(asset);
          asset.condition = `Banding pengemudi: ${text(payload.reason)}`;
          message = 'Banding kelayakan diajukan. Reservasi dilepas agar PM dapat mengalokasikan unit lain.';
        }
        break;
      }
      case 'SAVE_REPORT': {
        requireStatus(['IN_PROGRESS']); const day = getDay();
        requireThat(new Date(day.date) <= new Date(state.demoDate), 'Laporan hanya dapat diisi pada atau setelah tanggal pelaksanaan.');
        requireThat(['DRAFT', 'CHANGES_REQUESTED'].includes(day.reportStatus), 'Laporan yang sudah diserahkan tidak dapat diubah.');
        day.reportText = text(payload.text); day.obstacleText = text(payload.obstacleText);
        if (payload.evidence !== undefined) {
          requireThat(Array.isArray(payload.evidence), 'Bukti harus berupa daftar.');
          requireThat(payload.evidence.length <= 10, 'Batas maksimum bukti adalah 10 berkas.');
          day.evidence = payload.evidence.map(item => typeof item === 'string' ? item : clone(item));
        }
        message = 'Draft laporan harian tersimpan.'; break;
      }
      case 'SUBMIT_REPORT': {
        requireStatus(['IN_PROGRESS']); const day = getDay();
        requireThat(new Date(day.date) <= new Date(state.demoDate), 'Laporan hanya dapat diisi pada atau setelah tanggal pelaksanaan.');
        requireThat(['DRAFT', 'CHANGES_REQUESTED'].includes(day.reportStatus), 'Laporan sudah diserahkan.');
        requireThat(day.reportText.length >= 10, 'Isi laporan minimal 10 karakter.');
        requireThat(day.tasks.every(task => task.done), 'Selesaikan seluruh checklist tugas sebelum menyerahkan laporan.');
        requireThat(day.evidence.length > 0, 'Tambahkan minimal satu bukti pelaksanaan.');
        day.reportStatus = 'SUBMITTED'; day.submittedAt = timestamp(); day.submittedBy = actor.name;
        message = 'Laporan harian diserahkan untuk pemeriksaan PM.'; break;
      }
      case 'REVIEW_REPORT': { requireStatus(['IN_PROGRESS', 'COMPLETION_REVIEW']); const day = getDay(); requireThat(day.reportStatus === 'SUBMITTED', 'Laporan belum menunggu pemeriksaan.'); requireThat(['APPROVE', 'RETURN'].includes(payload.decision), 'Keputusan tidak valid.'); requireThat(payload.decision === 'APPROVE' || text(payload.note), 'Catatan revisi wajib diisi.'); day.reportStatus = payload.decision === 'APPROVE' ? 'APPROVED' : 'CHANGES_REQUESTED'; day.reviewNote = text(payload.note); day.reviewedBy = actor.name; day.reviewedAt = timestamp(); message = payload.decision === 'APPROVE' ? 'Laporan harian disetujui.' : 'Laporan dikembalikan beserta catatan revisi.'; break; }
      case 'SAVE_WEEKLY': { requireStatus(['IN_PROGRESS']); const week = plan.weeks.find(w => w.id === payload.weekId); requireThat(week, 'Minggu tidak ditemukan.'); requireThat(['DRAFT', 'CHANGES_REQUESTED'].includes(week.status), 'Laporan mingguan sudah diserahkan.'); week.reportText = text(payload.text); week.obstacleText = text(payload.obstacleText); message = 'Draft laporan mingguan tersimpan.'; break; }
      case 'SUBMIT_WEEKLY': {
        requireStatus(['IN_PROGRESS']); const week = plan.weeks.find(w => w.id === payload.weekId); requireThat(week, 'Minggu tidak ditemukan.'); requireThat(['DRAFT', 'CHANGES_REQUESTED'].includes(week.status), 'Laporan mingguan sudah diserahkan.');
        requireThat(week.dayIds.every(id => plan.days.find(d => d.id === id).reportStatus === 'APPROVED'), 'Semua laporan harian dalam minggu ini harus disetujui terlebih dahulu.');
        requireThat(week.reportText.length > 10, 'Laporan mingguan wajib diisi.'); requireThat(week.obstacleText.length > 0, 'Ringkasan kendala mingguan wajib diisi (isi "Tidak ada" jika lancar).');
        week.status = 'SUBMITTED'; week.submittedAt = timestamp(); week.submittedBy = actor.name; message = 'Laporan mingguan diserahkan untuk pemeriksaan PM.'; break;
      }
      case 'REVIEW_WEEKLY': {
        requireStatus(['IN_PROGRESS', 'COMPLETION_REVIEW']); const week = plan.weeks.find(w => w.id === payload.weekId); requireThat(week && week.status === 'SUBMITTED', 'Laporan mingguan belum menunggu pemeriksaan.');
        requireThat(['APPROVE', 'RETURN'].includes(payload.decision), 'Keputusan tidak valid.'); requireThat(payload.decision === 'APPROVE' || text(payload.note), 'Catatan revisi wajib diisi.');
        week.status = payload.decision === 'APPROVE' ? 'APPROVED' : 'CHANGES_REQUESTED'; week.reviewNote = text(payload.note); week.reviewedBy = actor.name; week.reviewedAt = timestamp();
        message = payload.decision === 'APPROVE' ? 'Laporan mingguan disetujui.' : 'Laporan mingguan dikembalikan beserta catatan revisi.'; break;
      }
      case 'REQUEST_CHANGE': {
        requireStatus(['ACCEPTED', 'IN_PROGRESS']); requireThat(!pendingChange(plan), 'Masih ada perubahan yang menunggu penyelesaian.');
        requireThat(payload.type === 'EXTEND', 'Prototype ini mendukung adendum perpanjangan.');
        requireThat(dateValid(payload.newEnd) && payload.newEnd > plan.endDate, 'Tanggal akhir baru harus setelah akhir rencana saat ini.');
        dateRange(plan.startDate, payload.newEnd); requireThat(text(payload.reason), 'Alasan perubahan wajib diisi.');
        plan.change = { id: id(), type: 'EXTEND', status: 'PENDING_PM', reason: text(payload.reason), oldEnd: plan.endDate, newEnd: payload.newEnd, baseRevision: plan.revision, proposedRevision: Math.max(plan.revision, ...plan.documents.map(d => d.version)) + 1, requestedBy: actor.name };
        message = 'Perpanjangan diajukan. Rencana lama tetap berlaku sampai adendum diterima.'; break;
      }
      case 'WITHDRAW_CHANGE': {
        requireStatus(['ACCEPTED', 'IN_PROGRESS']);
        requireThat(pendingChange(plan), 'Tidak ada usulan perubahan yang terbuka.');
        requireThat(plan.change.type === 'PERSONNEL', 'Penarikan hanya tersedia untuk adendum personel yang diajukan PM.');
        requireThat(text(payload.reason), 'Alasan penarikan wajib diisi.');
        plan.change.status = 'WITHDRAWN'; plan.change.rejectionReason = text(payload.reason);
        plan.documents.filter(document => document.status === 'AWAITING_ACCEPTANCE').forEach(document => { document.status = 'WITHDRAWN'; });
        message = 'Usulan adendum personel ditarik. Susunan tim tetap seperti sebelumnya.'; break;
      }
      case 'REQUEST_PERSONNEL_CHANGE': {
        requireStatus(['ACCEPTED', 'IN_PROGRESS']);
        requireThat(!pendingChange(plan), 'Masih ada perubahan yang menunggu penyelesaian.');
        requireThat(text(payload.reason), 'Alasan perubahan personel wajib diisi.');
        const leaderId = text(payload.leaderId) || plan.leaderId;
        const memberIds = [...new Set(Array.isArray(payload.memberIds) ? payload.memberIds.filter(text) : plan.memberIds)];
        const removed = [plan.leaderId, ...plan.memberIds].filter(personId => personId !== leaderId && !memberIds.includes(personId));
        requireThat(leaderId !== plan.leaderId || removed.length || memberIds.some(personId => !plan.memberIds.includes(personId)), 'Tidak ada perubahan personel yang diusulkan.');
        const proposed = clone(plan); proposed.leaderId = leaderId; proposed.memberIds = memberIds;
        checkMembers(state, proposed); checkSchedule(state, proposed, proposed.endDate);
        for (const personId of removed) {
          const vehicle = state.assets.find(a => a.planId === plan.id && a.driverId === personId);
          requireThat(!vehicle, `${state.employees.find(e => e.id === personId)?.name || 'Personel'} masih tercatat sebagai pengemudi ${vehicle?.name || 'kendaraan'}. Lepas atau kembalikan kendaraan itu lebih dahulu.`);
        }
        plan.change = { id: id(), type: 'PERSONNEL', status: 'AWAITING_LEADER_ACCEPTANCE', reason: text(payload.reason), baseRevision: plan.revision, proposedRevision: Math.max(plan.revision, ...plan.documents.map(d => d.version)) + 1, requestedBy: actor.name, newEnd: plan.endDate, oldEnd: plan.endDate, leaderId, memberIds, oldLeaderId: plan.leaderId, oldMemberIds: [...plan.memberIds], removedIds: removed };
        plan.documents.push({ id: id(), number: `${plan.number}/ADD-SDM-${plan.change.proposedRevision - 1}`, kind: 'PERSONNEL_ADDENDUM', version: plan.change.proposedRevision, status: 'AWAITING_ACCEPTANCE', issuedBy: actor.name, issuedAt: timestamp(), acceptedBy: null, acceptedAt: null, reason: plan.change.reason, snapshot: snapshot(state, proposed) });
        message = leaderId === plan.leaderId ? 'Adendum personel diterbitkan. Menunggu penerimaan ketua tim.' : 'Adendum penggantian ketua diterbitkan. Menunggu penerimaan ketua tim baru.'; break;
      }
      case 'APPROVE_CHANGE': {
        requireStatus(['ACCEPTED', 'IN_PROGRESS']); requireThat(plan.change?.status === 'PENDING_PM', 'Tidak ada perubahan menunggu persetujuan PM.');
        requireThat(plan.change.baseRevision === plan.revision, 'Revisi dasar sudah berubah. Ajukan perubahan baru.'); checkSchedule(state, plan, plan.change.newEnd);
        plan.change.status = 'AWAITING_LEADER_ACCEPTANCE';
        const proposed = clone(plan); proposed.endDate = plan.change.newEnd;
        proposed.days = dateRange(plan.startDate, proposed.endDate).map((date, index) => plan.days.find(day => day.date === date) || makeDay(date, index));
        plan.documents.push({ id: id(), number: `${plan.number}/ADD-${plan.change.proposedRevision - 1}`, kind: 'ADDENDUM', version: plan.change.proposedRevision, status: 'AWAITING_ACCEPTANCE', issuedBy: actor.name, issuedAt: timestamp(), acceptedBy: null, snapshot: snapshot(state, proposed) });
        message = 'PM menandatangani usulan final. Ketua tim harus menerima adendum untuk mengaktifkannya.'; break;
      }
      case 'ACCEPT_CHANGE': {
        requireStatus(['ACCEPTED', 'IN_PROGRESS']); requireThat(plan.change?.status === 'AWAITING_LEADER_ACCEPTANCE', 'Adendum belum siap diterima.');
        requireThat(plan.change.baseRevision === plan.revision, 'Revisi dasar telah berubah.');
        const personnel = plan.change.type === 'PERSONNEL';
        if (personnel) { plan.leaderId = plan.change.leaderId; plan.memberIds = [...plan.change.memberIds]; }
        checkMembers(state, plan); checkSchedule(state, plan, plan.change.newEnd);
        plan.endDate = plan.change.newEnd; plan.revision = plan.change.proposedRevision;
        plan.days = dateRange(plan.startDate, plan.endDate).map((date, index) => plan.days.find(day => day.date === date) || makeDay(date, index));
        plan.change.status = 'EFFECTIVE'; const document = plan.documents.at(-1); document.status = 'EFFECTIVE'; document.acceptedBy = actor.name; document.acceptedAt = timestamp();
        message = personnel ? 'Adendum personel diterima. Susunan tim baru berlaku.' : 'Adendum diterima. Revisi baru aktif dan rincian tambahan dibuat.'; break;
      }
      case 'REJECT_CHANGE': requireStatus(['ACCEPTED', 'IN_PROGRESS']); requireThat(pendingChange(plan), 'Tidak ada perubahan terbuka.');
        requireThat(plan.change.type !== 'PERSONNEL' || plan.change.leaderId === actor.id, 'Hanya ketua tim yang ditunjuk pada adendum personel ini yang dapat menolaknya. PM dapat menarik usulannya sendiri.');
        requireThat(text(payload.reason), 'Alasan wajib diisi.'); plan.change.status = 'REJECTED'; plan.change.rejectionReason = text(payload.reason); plan.documents.filter(document => document.status === 'AWAITING_ACCEPTANCE').forEach(document => { document.status = 'REJECTED'; }); message = 'Perubahan ditolak. Rencana aktif tetap sama.'; break;
      case 'REQUEST_COMPLETE': {
        requireStatus(['IN_PROGRESS']);
        requireThat(plan.change === null || !['PENDING_PM', 'AWAITING_LEADER_ACCEPTANCE'].includes(plan.change.status), 'Masih ada usulan perubahan yang belum selesai.');
        requireThat(plan.days.every(d => d.reportStatus === 'APPROVED'), 'Seluruh laporan harian wajib disetujui PM terlebih dahulu.');
        requireThat((plan.weeks || []).every(w => w.status === 'APPROVED'), 'Laporan mingguan belum selesai.');
        requireThat(text(payload.reportText) && text(payload.obstacleText), 'Laporan penyelesaian dan ringkasan kendala keseluruhan wajib diisi.');
        plan.status = 'COMPLETION_REVIEW';
        plan.finalReport = { 
          status: 'SUBMITTED', 
          reportText: text(payload.reportText), 
          obstacleText: text(payload.obstacleText), 
          reviewNote: '',
          evidence: Array.isArray(payload.evidence) ? clone(payload.evidence) : [],
          submittedBy: actor.name,
          submittedAt: timestamp()
        };
        message = 'Penyelesaian pekerjaan diajukan ke PM.'; break;
      }
      case 'APPROVE_COMPLETE': {
        requireStatus(['COMPLETION_REVIEW']); requireThat(plan.days.every(d => d.reportStatus === 'APPROVED'), 'Terdapat laporan harian yang belum disetujui.');
        requireThat(plan.weeks.every(w => w.status === 'APPROVED'), 'Terdapat laporan mingguan yang belum disetujui.');
        requireThat(plan.finalReport.status === 'SUBMITTED', 'Laporan akhir belum diserahkan.');
        requireThat(!state.assets.some(a => a.planId === plan.id && a.status !== 'AVAILABLE'), 'Masih ada aset yang belum dikembalikan atau diverifikasi (Asset).');
        plan.status = 'COMPLETED'; plan.finalReport.status = 'APPROVED'; plan.finalReport.reviewNote = text(payload.note);
        plan.finalReport.reviewedBy = actor.name; plan.finalReport.reviewedAt = timestamp();
        message = 'Pekerjaan dinyatakan selesai dan ditutup.'; break;
      }
      case 'RETURN_COMPLETE': {
        requireStatus(['COMPLETION_REVIEW']); requireThat(text(payload.reason), 'Alasan pengembalian wajib diisi.');
        plan.status = 'IN_PROGRESS'; plan.finalReport.status = 'CHANGES_REQUESTED'; plan.finalReport.reviewNote = text(payload.reason);
        message = 'Penyelesaian dikembalikan ke ketua tim beserta catatan.'; break;
      }
      case 'CANCEL_PLAN': requireStatus(['PUBLISHED', 'ACCEPTED', 'APPEALED', 'IN_PROGRESS', 'COMPLETION_REVIEW']); requireThat(text(payload.reason), 'Alasan pembatalan wajib diisi.'); plan.status = 'CANCELLED'; plan.cancellationReason = text(payload.reason); if (pendingChange(plan)) plan.change.status = 'CANCELLED'; state.assets.filter(asset => asset.planId === plan.id && asset.status === 'RESERVED').forEach(asset => freeAsset(asset)); plan.documents.forEach(document => { document.status = 'CANCELLED'; }); message = 'Work plan dibatalkan. Aset yang sedang dipakai tetap wajib dikembalikan.'; break;
      case 'DELETE_PLAN': requireStatus(['DRAFT']); requireThat(text(payload.reason), 'Alasan pengarsipan wajib diisi.'); requireThat(!state.assets.some(asset => asset.planId === plan.id), 'Lepaskan reservasi aset sebelum mengarsipkan draft.'); requireThat(plan.documents.length === 0, 'Pekerjaan yang pernah memiliki SK tidak dapat diarsipkan. Gunakan opsi pembatalan.'); plan.deletedAt = timestamp(); plan.deletedBy = actor.id; plan.deletionReason = text(payload.reason); message = 'Draft diarsipkan dengan soft delete. Riwayat tetap tersedia.'; break;
      case 'RESTORE_PLAN': requireThat(plan.deletedAt, 'Draft tidak berada di arsip.'); requireThat(!state.plans.some(other => other.id !== plan.id && !other.deletedAt && other.number === plan.number), 'Nomor draft bentrok dengan data aktif.'); checkMembers(state, plan); plan.deletedAt = null; plan.deletedBy = null; message = 'Draft dipulihkan setelah pemeriksaan relasi.'; break;
      case 'RESERVE_ASSET': {
        const asset = state.assets.find(a => a.id === payload.assetId); requireThat(asset, 'Aset tidak ditemukan.'); requireThat(plan && !['COMPLETED', 'CANCELLED'].includes(plan.status), 'Pilih work plan yang masih aktif.');
        requireThat(asset.status === 'AVAILABLE' && !asset.planId, 'Aset sudah dialokasikan ke pekerjaan lain.');
        if (asset.kind === 'VEHICLE') {
          requireThat(text(payload.driverId), 'Pilih pengemudi untuk aset kendaraan.');
          requireThat([plan.leaderId, ...plan.memberIds].includes(payload.driverId), 'Pengemudi harus bagian dari tim penugasan.');
          const driver = state.employees.find(e => e.id === payload.driverId);
          requireThat(driver, 'Karyawan pengemudi tidak ditemukan.');
          const requiredSim = asset.vehicleType === 'MOTORCYCLE' ? 'SIM C' : 'SIM A';
          const sim = driver.documents.find(d => d.type === requiredSim && d.lifecycle === 'CURRENT');
          requireThat(sim, `Karyawan ${driver.name} tidak memiliki ${requiredSim} aktif dalam profilnya.`);
          requireThat(!sim.expiry || sim.expiry >= plan.endDate, `Masa berlaku ${requiredSim} ${driver.name} kedaluwarsa sebelum jadwal selesai.`);
          asset.driver = driver.name;
          asset.driverId = driver.id;
        }
        asset.status = (asset.kind !== 'VEHICLE' && ['IN_PROGRESS', 'COMPLETION_REVIEW'].includes(plan.status)) ? 'IN_USE' : 'RESERVED'; asset.planId = plan.id; message = 'Aset dialokasikan. Reservasi ganda dicegah.'; break;
      }
      case 'RETURN_ASSET': {
        requireThat(actor.role !== 'ASSET', 'Pengajuan pengembalian tidak dapat dilakukan oleh petugas aset. Gunakan ketua tim.');
        const asset = state.assets.find(a => a.id === payload.assetId); requireThat(asset && asset.planId && ['IN_USE', 'RESERVED'].includes(asset.status), 'Aset belum dipinjam atau sudah menunggu verifikasi.');
        if (actor.role === 'LEADER') requireThat(state.plans.find(p => p.id === asset.planId)?.leaderId === actor.id, 'Anda bukan ketua tim peminjam aset ini.');
        asset.status = 'RETURN_PENDING'; asset.returnedBy = actor.id; asset.returnNote = text(payload.note); message = 'Pengembalian diajukan. Petugas aset perlu memverifikasi kondisi.'; break;
      }
      case 'VERIFY_RETURN': {
        const asset = state.assets.find(a => a.id === payload.assetId);
        requireThat(asset?.status === 'RETURN_PENDING', 'Aset belum menunggu verifikasi pengembalian.');
        requireThat(asset.returnedBy !== actor.id, 'Pengembalian tidak dapat diperiksa oleh pengaju yang sama. Gunakan ketua tim untuk serah terima.');
        
        if (payload.decision === 'REJECT') {
           asset.status = 'IN_USE';
           asset.returnNote = 'Ditolak (Perlu Perbaikan): ' + text(payload.note);
           asset.returnHistory = [...(asset.returnHistory || []), { planId: asset.planId, returnedBy: asset.returnedBy, verifiedBy: actor.name, at: timestamp(), condition: text(payload.condition) || asset.condition, note: 'DITOLAK: ' + text(payload.note), driver: asset.driver }];
           asset.returnedBy = null;
           message = 'Pengembalian ditolak. Aset dikembalikan ke tanggung jawab Ketua Tim untuk diperbaiki.';
        } else {
             asset.returnHistory = [...(asset.returnHistory || []), { planId: asset.planId, returnedBy: asset.returnedBy, verifiedBy: actor.name, at: timestamp(), condition: text(payload.condition) || asset.condition, note: text(payload.note), driver: asset.driver }];
             asset.condition = text(payload.condition) || asset.condition;
             asset.lastPlanId = asset.planId;
             freeAsset(asset);
             asset.returnedBy = null;
             message = 'Pengembalian terverifikasi. Aset tersedia kembali.';
        }
        break;
      }
      case 'CHECK_IN': {
        const employeeId = payload.employeeId || actor.id; requireThat(employeeId === actor.id && eligible(state, employeeId), 'Absensi hanya dapat dicatat untuk akun sendiri yang aktif.');
        requireThat(!state.attendance.some(a => a.employeeId === employeeId && !a.checkOut && a.status !== 'REJECTED'), 'Masih ada sesi absensi terbuka.');
        
        const today = state.demoDate || DEMO_TODAY;
        const latestToday = state.attendance.find(a => a.employeeId === employeeId && a.date === today);
        requireThat(!latestToday || latestToday.status === 'REJECTED', 'Absensi untuk hari ini sudah tercatat (hanya dapat mengajukan ulang jika absensi sebelumnya ditolak).');

        const distance = Number(payload.distance ?? 24); requireThat(Number.isFinite(distance) && distance >= 0, 'Jarak simulasi tidak valid.'); requireThat(text(payload.site), 'Lokasi absensi wajib diisi.');
        requireThat(['MOBILE', 'MACHINE'].includes(payload.source || 'MOBILE'), 'Sumber absensi tidak valid.');
        const source = payload.source || 'MOBILE', outside = distance > ATTENDANCE_RADIUS;
        const selfie = payload.selfie && typeof payload.selfie === 'object' && text(payload.selfie.id) ? { id: text(payload.selfie.id), name: text(payload.selfie.name) || 'swafoto', type: text(payload.selfie.type) || 'image/jpeg', size: Number(payload.selfie.size) || undefined } : null;
        requireThat(!(outside && source === 'MOBILE') || selfie, `Di luar radius toleransi (${Math.round(distance)} m > ${ATTENDANCE_RADIUS} m): swafoto wajib dilampirkan.`);
        requireThat(!selfie || /^image\//.test(selfie.type), 'Swafoto harus berupa gambar.');
        const lat = Number(payload.lat), lng = Number(payload.lng), hasCoords = Number.isFinite(lat) && Number.isFinite(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180;
        state.attendance.unshift({ id: id(), employeeId, date: state.demoDate || DEMO_TODAY, checkIn: clockOn(state.demoDate || DEMO_TODAY).iso, checkOut: null, late: clockOn(state.demoDate || DEMO_TODAY).hhmm > SHIFT_START, source, site: text(payload.site), distance, radius: ATTENDANCE_RADIUS, status: outside ? 'NEEDS_REVIEW' : 'AUTO_VALID', explanation: '', reviewNote: '', coords: hasCoords ? { lat, lng, origin: payload.geoSource === 'GPS' ? 'GPS' : 'SIMULASI' } : null, selfie });
        message = outside ? 'Check-in tercatat di luar radius; menunggu pemeriksaan Finance.' : 'Check-in berhasil dalam radius lokasi.'; break;
      }
      case 'CHECK_OUT': { const attendance = state.attendance.find(a => a.id === payload.attendanceId); requireThat(attendance?.employeeId === actor.id && !attendance.checkOut, 'Sesi bukan milik Anda atau sudah ditutup.'); const out = clockOn(attendance.date); attendance.checkOut = out.iso; attendance.earlyLeave = out.hhmm < SHIFT_END; message = 'Check-out tercatat. Bukti check-in tetap tersimpan.'; break; }
      case 'EXPLAIN_ATTENDANCE': { const attendance = state.attendance.find(a => a.id === payload.attendanceId); requireThat(attendance?.employeeId === actor.id && attendance.status === 'NEEDS_REVIEW', 'Hanya absensi sendiri yang menunggu pemeriksaan dapat diberi penjelasan.'); requireThat(text(payload.explanation), 'Penjelasan wajib diisi.'); attendance.explanation = text(payload.explanation); message = 'Penjelasan dikirim ke Finance.'; break; }
      case 'REVIEW_ATTENDANCE': { const attendance = state.attendance.find(a => a.id === payload.attendanceId); requireThat(attendance?.status === 'NEEDS_REVIEW', 'Absensi tidak menunggu pemeriksaan.'); requireThat(attendance.employeeId !== actor.id, 'Anda tidak boleh memverifikasi absensi sendiri.'); requireThat(['APPROVE', 'REJECT'].includes(payload.decision), 'Keputusan tidak valid.'); requireThat(text(payload.note), 'Catatan pemeriksaan wajib diisi.'); attendance.status = payload.decision === 'APPROVE' ? 'APPROVED' : 'REJECTED'; attendance.reviewNote = text(payload.note); attendance.reviewedBy = actor.id; message = 'Pemeriksaan absensi tersimpan tanpa mengubah bukti GPS asli.'; break; }
      case 'UPLOAD_DOCUMENT': {
        const employeeId = payload.employeeId || actor.id;
        requireThat(employeeId === actor.id, 'Dokumen hanya dapat diajukan oleh pemiliknya.');
        const employee = state.employees.find(e => e.id === employeeId); requireThat(employee && !employee.deletedAt, 'Karyawan tidak tersedia.');
        requireThat(text(payload.type), 'Jenis dokumen wajib diisi.'); requireThat(!payload.expiry || dateValid(payload.expiry), 'Tanggal berlaku tidak valid.');
        requireThat(!employee.documents.some(document => document.type === text(payload.type) && document.status === 'PENDING'), 'Masih ada dokumen jenis ini menunggu pemeriksaan.');
        employee.documents.push({ id: id(), type: text(payload.type), numberMasked: `DEMO-****${text(payload.number).slice(-4) || '0000'}`, expiry: payload.expiry || null, status: 'PENDING', lifecycle: 'PENDING', attachment: clone(payload.attachment || null), uploadedAt: timestamp(), uploadedBy: actor.id }); message = 'Dokumen pengganti diunggah. Dokumen lama tetap current sampai verifikasi.'; break;
      }
      case 'VERIFY_DOCUMENT': {
        const employee = state.employees.find(e => e.id === payload.employeeId), document = employee?.documents.find(d => d.id === payload.documentId);
        requireThat(document?.status === 'PENDING', 'Dokumen tidak menunggu verifikasi.'); requireThat(employee.id !== actor.id && document.uploadedBy !== actor.id, 'Pemilik atau pengunggah tidak dapat memverifikasi dokumen sendiri.');
        requireThat(['APPROVE', 'REJECT'].includes(payload.decision), 'Keputusan tidak valid.');
        if (payload.decision === 'APPROVE') { employee.documents.filter(d => d.type === document.type && d.lifecycle === 'CURRENT').forEach(d => { d.lifecycle = 'SUPERSEDED'; }); document.status = 'VERIFIED'; document.lifecycle = 'CURRENT'; } else { document.status = 'REJECTED'; document.lifecycle = 'REJECTED'; }
        document.verifiedBy = actor.id; document.reviewNote = text(payload.note); document.verifiedAt = timestamp(); message = payload.decision === 'APPROVE' ? 'Dokumen terverifikasi dan menjadi current. Versi lama tetap tersimpan.' : 'Dokumen ditolak. Dokumen current sebelumnya tetap berlaku.'; break;
      }
      case 'PROMOTE': {
        const employee = state.employees.find(e => e.id === payload.employeeId); requireThat(activeEmployee(employee), 'Karyawan harus aktif.'); requireThat(text(payload.position) && units.some(unit => unit.code === payload.unit), 'Jabatan dan unit wajib valid.');
        requireThat(!actors.some(a => a.id === employee.id), 'Akun pemegang peran demo memerlukan serah terima kewenangan. Gunakan karyawan lain untuk simulasi promosi.');
        requireThat(payload.unit === employee.unit || !state.plans.some(p => !p.deletedAt && !['DRAFT', 'COMPLETED', 'CANCELLED'].includes(p.status) && [p.leaderId, ...p.memberIds].includes(employee.id)), 'Mutasi lintas unit diblokir sampai penugasan aktif diserahterimakan.');
        employee.assignmentHistory.filter(a => !a.to).forEach(a => { a.to = state.demoDate || DEMO_TODAY; }); employee.assignmentHistory.push({ id: id(), position: text(payload.position), unit: payload.unit, from: state.demoDate || DEMO_TODAY, to: null }); employee.position = text(payload.position); employee.unit = payload.unit;
        message = 'Penempatan baru efektif. Riwayat jabatan dan snapshot SK lama tetap tersimpan.'; break;
      }
      case 'OFFBOARD': {
        const employee = state.employees.find(e => e.id === payload.employeeId); requireThat(activeEmployee(employee), 'Karyawan sudah nonaktif atau tidak ditemukan.'); requireThat(text(payload.reason), 'Alasan offboarding wajib diisi.');
        requireThat(!state.plans.some(p => !p.deletedAt && !['DRAFT', 'COMPLETED', 'CANCELLED'].includes(p.status) && [p.pmId, p.leaderId, ...p.memberIds].includes(employee.id)), 'Selesaikan atau serahterimakan penugasan aktif sebelum offboarding.');
        employee.status = 'INACTIVE'; employee.offboardedAt = timestamp(); employee.offboardingReason = text(payload.reason); employee.assignmentHistory.filter(a => !a.to).forEach(a => { a.to = state.demoDate || DEMO_TODAY; }); employee.accessRevoked = true;
        message = 'Masa kerja diakhiri dan akses dicabut. Data historis tetap tersedia.'; break;
      }
      case 'REPORT_INCIDENT': {
        requireStatus(['IN_PROGRESS']);
        requireThat([plan.leaderId, ...plan.memberIds].includes(actor.id), 'Hanya ketua atau anggota pekerjaan ini yang dapat melaporkan insiden.');
          requireThat(['K3_RINGAN', 'K3_BERAT', 'K3_LINGKUNGAN', 'K3_HAMPIR', 'ASET'].includes(payload.category), 'Pilih kategori insiden yang valid.');
        requireThat(['RENDAH', 'SEDANG', 'TINGGI', 'KRITIS'].includes(payload.severity), 'Pilih tingkat keparahan yang valid.');
        requireThat(text(payload.description), 'Uraian insiden tidak boleh kosong.');
        const incident = { id: id(), planId: plan.id, employeeId: actor.id, date: state.demoDate, category: payload.category, severity: payload.severity, description: text(payload.description), evidence: payload.evidence || [], status: 'OPEN', history: [{date: state.demoDate, actor: actor.name, text: 'Dilaporkan'}] };
        state.incident_reports.push(incident);
        plan.activity.unshift({ at: timestamp(), actor: actor.name, action: 'REPORT_INCIDENT', detail: `Lapor Insiden [${payload.category}]: ${text(payload.description)}` });
        message = 'Insiden/HSE berhasil dilaporkan.'; break;
      }
      case 'RESOLVE_INCIDENT': {
        const incident = state.incident_reports.find(i => i.id === payload.incidentId);
        requireThat(incident && incident.status === 'OPEN', 'Insiden tidak aktif atau sudah ditutup.');
        const incidentPlan = state.plans.find(p => p.id === incident.planId);
        requireThat(can(actor, 'RESOLVE_INCIDENT', incidentPlan?.unit), 'Insiden ini berada di luar unit atau kewenangan Anda.');
        requireThat(actor.role !== 'ASSET' || incident.category === 'ASET', 'Pengelola aset hanya menutup insiden kategori Aset.');
        requireThat(text(payload.note), 'Catatan penyelesaian wajib diisi.');
        incident.status = 'RESOLVED';
        incident.resolvedBy = actor.name;
        incident.history.unshift({date: state.demoDate, actor: actor.name, text: 'Diselesaikan: ' + text(payload.note)});
        if (incidentPlan) incidentPlan.activity.unshift({ at: timestamp(), actor: actor.name, action: 'RESOLVE_INCIDENT', detail: `Insiden ditutup: ${text(payload.note)}` });
        entity = incidentPlan?.number || entity;
        message = 'Insiden/HSE diselesaikan.'; break;
      }
      case 'REPORT_OVERTIME': {
        requireThat(plan?.status === 'IN_PROGRESS', 'Hanya pekerjaan aktif yang bisa diajukan lembur.');
        requireThat(payload.hours > 0 && payload.hours <= 12, 'Jam lembur tidak valid.');
        requireThat(text(payload.reason), 'Alasan lembur wajib diisi.');
        requireThat([plan.leaderId, ...plan.memberIds].includes(actor.id), 'Hanya ketua atau anggota pekerjaan ini yang dapat mengajukan lembur.');
        const documentId = (plan.documents.filter(d => d.status === 'EFFECTIVE').at(-1) || plan.documents.at(-1))?.id;
        state.overtime_logs.push({ id: id(), planId: plan.id, documentId, employeeId: actor.id, date: state.demoDate, hours: Number(payload.hours), reason: text(payload.reason), status: 'PENDING_PM' });
        message = 'Lembur diajukan ke PM.'; break;
      }
      case 'REVIEW_OVERTIME': {
        const ot = state.overtime_logs.find(o => o.id === payload.overtimeId);
        requireThat(ot && ot.status === 'PENDING_PM', 'Lembur tidak tersedia untuk direview.');
        const overtimePlan = state.plans.find(p => p.id === ot.planId);
        requireThat(can(actor, 'REVIEW_OVERTIME', overtimePlan?.unit), 'Lembur ini berada di luar unit atau kewenangan Anda.');
        requireThat(ot.employeeId !== actor.id, 'Pengaju lembur tidak dapat menyetujui pengajuannya sendiri.');
        requireThat(['APPROVED', 'REJECTED'].includes(payload.decision), 'Keputusan harus disetujui atau ditolak.');
        ot.status = payload.decision;
        ot.reviewedBy = actor.name;
        if (payload.note) ot.note = text(payload.note);
        entity = overtimePlan?.number || entity;
        message = `Lembur ${payload.decision === 'APPROVED' ? 'disetujui' : 'ditolak'}.`; break;
      }
      case 'RESTORE_EMPLOYEE': { const employee = state.employees.find(e => e.id === payload.employeeId); requireThat(employee?.deletedAt, 'Karyawan tidak dihapus. Untuk bergabung kembali dibutuhkan masa kerja dan akses baru.'); employee.deletedAt = null; employee.status = 'INACTIVE'; employee.accessRevoked = true; message = 'Data dipulihkan sebagai nonaktif. Akses lama tetap dicabut.'; break; }
      default: fail('Tindakan belum tersedia pada prototype.');
    }
    const event = { id: id(), at: timestamp(), actor: actor.name, action: type, entity, detail: text(payload.reason || payload.note) || message };
    event.actorId = actor.id; if (plan) event.planId = plan.id; state.revision = (state.revision || 0) + 1;
    state.audit.unshift(event);
    if (plan) { plan.rowVersion += 1; plan.activity.unshift(event); }
    return { state, message };
  } catch (error) { return { error: error.message || 'Perubahan tidak dapat diproses.' }; }
}

// A document is locked once a newer version exists: issued snapshots are never rewritten.
const documentLocked = (plan, document) => plan.documents.indexOf(document) < plan.documents.length - 1;

return { actors, units, createInitialState, can, transition, visiblePlans, documentLocked, attendanceRadius: ATTENDANCE_RADIUS };
})();
