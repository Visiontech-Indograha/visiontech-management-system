window.VTStorage = (() => {
  const key = 'visiontech.native.v4';
  let warning = '', memoryOnly = false, database;
  function load() {
    try {
      try { localStorage.removeItem('visiontech.native.v1'); localStorage.removeItem('visiontech.native.v2'); localStorage.removeItem('visiontech.native.v3'); } catch(e) {}
      const raw = localStorage.getItem(key);
      if (!raw) return VTDomain.createInitialState();
      try {
        const value = JSON.parse(raw);
        if (value.schemaVersion !== 4 || !['plans','employees','assets','attendance','audit'].every(k => Array.isArray(value[k]))) throw new Error('Invalid');
        ['offline_queue','incident_reports','overtime_logs'].forEach(k => { if (!Array.isArray(value[k])) value[k] = []; });
        return value;
      } catch (parseError) {
        localStorage.removeItem(key);
        warning = 'Data simulasi tidak kompatibel atau rusak, sehingga telah direset (versi 4).';
        return VTDomain.createInitialState();
      }
    } catch (error) {
      warning = 'Penyimpanan dilarang oleh browser (Incognito/Privasi). Sesi ini memakai memori sementara.';
      memoryOnly = true;
      return VTDomain.createInitialState();
    }
  }
  // Returns true when the state really reached localStorage, false when it only lives in memory.
  function save(value, previousRevision) {
    value.schemaVersion = 4;
    value.revision = (previousRevision || 0) + 1;
    if (memoryOnly) return false;
    try {
      const raw = localStorage.getItem(key);
      if (raw && JSON.parse(raw).revision !== previousRevision) throw new Error('CONFLICT');
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (error) {
      if (error.message === 'CONFLICT') throw new Error('Data berubah di tab lain. Muat ulang halaman sebelum mengulangi tindakan.');
      memoryOnly = true;
      warning = 'Penyimpanan browser tidak tersedia atau penuh. Perubahan berikut hanya bertahan selama sesi ini; lampiran tetap memakai penyimpanan berkas jika tersedia.';
      return false;
    }
  }
  function db() {
    if (!database) database = new Promise((resolve, reject) => {
      const request = indexedDB.open('visiontech.native.files.v2', 1);
      request.onupgradeneeded = () => request.result.createObjectStore('files');
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => { database = null; reject(new Error('Penyimpanan lampiran tidak tersedia di browser ini.')); };
      request.onblocked = () => reject(new Error('Tutup tab prototipe lain agar penyimpanan lampiran dapat dibuka.'));
    });
    return database;
  }
  async function operation(mode, work) {
    const connection = await db();
    return new Promise((resolve, reject) => {
      const tx = connection.transaction('files', mode);
      const request = work(tx.objectStore('files'));
      let result;
      if (request) request.onsuccess = () => { result = request.result; };
      tx.oncomplete = () => resolve(result);
      tx.onerror = tx.onabort = () => reject(new Error('Lampiran gagal disimpan atau dibaca. Periksa ruang penyimpanan browser.'));
    });
  }
  async function put(file) {
    if (!file?.size) throw new Error('Pilih berkas yang tidak kosong.');
    if (file.size > 10 * 1024 * 1024) throw new Error('Ukuran setiap lampiran maksimal 10 MB.');
    const id = crypto.randomUUID();
    await operation('readwrite', store => store.put(file, id));
    return { id, name: file.name, type: file.type || 'application/octet-stream', size: file.size };
  }
  async function get(id) {
    if (id === 'sample-certificate' || id === 'sample-evidence') {
      const certificate = id === 'sample-certificate';
      return new Blob([`<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="700" viewBox="0 0 1000 700"><rect width="1000" height="700" fill="#f3f5eb"/><rect x="35" y="35" width="930" height="630" rx="12" fill="white" stroke="#164d40" stroke-width="3"/><text x="80" y="120" font-family="Arial" font-size="25" fill="#164d40">VISIONTECH INDOGRAHA</text><path d="M80 160H920" stroke="#aabb9b"/><text x="80" y="255" font-family="Arial" font-size="36" fill="#243b33">${certificate ? 'SERTIFIKAT K3 · CONTOH' : 'BUKTI KEGIATAN · CONTOH'}</text><text x="80" y="330" font-family="Arial" font-size="22" fill="#67745e">${certificate ? 'Materi demonstrasi verifikasi dokumen karyawan.' : 'Briefing keselamatan dan pemeriksaan area kerja.'}</text><rect x="80" y="390" width="840" height="140" fill="#eaf1e3"/><text x="110" y="470" font-family="Arial" font-size="22" fill="#48683a">Lampiran ilustrasi untuk mencoba pratinjau.</text><text x="80" y="600" font-family="Arial" font-size="18" fill="#987349">DATA SIMULASI · BUKAN BUKTI ATAU SERTIFIKAT RESMI</text></svg>`], { type: 'image/svg+xml' });
    }
    const file = await operation('readonly', store => store.get(id));
    if (!file) throw new Error('Berkas tidak tersedia. Lampiran mungkin berasal dari browser lain atau penyimpanannya telah dibersihkan.');
    return file;
  }
  async function reset() {
    await operation('readwrite', store => store.clear()).catch(() => {});
    const state = VTDomain.createInitialState();
    state.revision = Date.now();
    memoryOnly = false; warning = '';
    try { localStorage.setItem(key, JSON.stringify(state)); } catch { memoryOnly = true; warning = 'Reset selesai dalam memori; penyimpanan browser tidak tersedia.'; }
    return state;
  }
  return { key, load, save, put, get, reset, get warning() { return warning; } };
})();
