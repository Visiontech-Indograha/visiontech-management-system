(() => {
  const V = VT, U = VTUI;
  const QUEUEABLE = new Set(['CHECK_IN', 'CHECK_OUT', 'TOGGLE_TASK', 'SAVE_REPORT', 'SUBMIT_REPORT']);
  let simulated = false, justSynced = false, syncTimer;
  try { simulated = sessionStorage.getItem('visiontech.simulateOffline') === '1'; } catch {}

  const online = () => !simulated && navigator.onLine !== false;
  const queue = () => V.state.offline_queue || [];

  // Transactions still apply locally so dependent steps (checklist → submit) keep working;
  // the queue records what has not been synchronised yet.
  function enqueue(state, type, payload) {
    if (online() || !QUEUEABLE.has(type)) return false;
    state.offline_queue = state.offline_queue || [];
    state.offline_queue.push({ id: crypto.randomUUID(), type, payload: JSON.parse(JSON.stringify(payload || {})), actorId: V.actor?.id || null, actor: V.actor?.name || '', at: new Date().toISOString() });
    return true;
  }

  function syncOfflineData() {
    const items = queue();
    if (!online() || !items.length || V.busy) return 0;
    const next = JSON.parse(JSON.stringify(V.state));
    next.offline_queue = [];
    next.audit = next.audit || [];
    next.audit.unshift({ id: crypto.randomUUID(), at: new Date().toISOString(), actor: 'Sinkronisasi luring', actorId: null, action: 'SYNC_OFFLINE', entity: `${items.length} transaksi`, detail: items.map(i => (V.actionNames?.[i.type] || i.type) + ' · ' + i.actor).join('; ') });
    let persisted;
    try { persisted = VTStorage.save(next, V.state.revision); } catch (error) { V.notify(error.message, true); return 0; }
    if (!persisted) {
      // The queue must survive: without durable storage nothing was really synchronised.
      V.render();
      V.notify(VTStorage.warning || 'Penyimpanan browser tidak tersedia. Antrean luring dipertahankan dan belum disinkronkan.', true);
      return 0;
    }
    V.state = next;
    justSynced = true; clearTimeout(syncTimer); syncTimer = setTimeout(() => { justSynced = false; paint(); }, 6000);
    V.render();
    V.notify(`Sinkronisasi selesai: ${items.length} transaksi luring tercatat di penyimpanan perangkat ini (simulasi, tanpa server).`);
    return items.length;
  }

  function paint() {
    let el = document.querySelector('#net-status');
    if (!el) {
      const style = document.createElement('style');
      style.textContent = '#net-status{position:fixed;bottom:14px;left:14px;z-index:60;padding:6px 14px;border-radius:999px;font:600 12px/1.4 inherit;box-shadow:0 4px 14px rgba(0,0,0,.12)}#net-status.offline{background:#7a2e1d;color:#fff}#net-status.pending{background:#976321;color:#fff}#net-status.synced{background:#164d40;color:#fff}#net-status[hidden]{display:none}@media(max-width:760px){#net-status{left:50%;transform:translateX(-50%);bottom:96px}}@media print{#net-status{display:none!important}}';
      document.head.appendChild(style);
      el = document.createElement('div'); el.id = 'net-status'; el.setAttribute('role', 'status'); el.setAttribute('aria-live', 'polite'); document.body.appendChild(el);
    }
    const n = queue().length;
    const text = !online() ? `Luring · ${n} antrean` : n ? `Online · ${n} antrean belum tersinkron` : justSynced ? 'Tersinkronisasi' : '';
    el.textContent = text;
    el.className = !online() ? 'offline' : n ? 'pending' : 'synced';
    el.hidden = !text || !V.actor;
  }

  function setSimulated(value) {
    simulated = !!value;
    try { value ? sessionStorage.setItem('visiontech.simulateOffline', '1') : sessionStorage.removeItem('visiontech.simulateOffline'); } catch {}
    V.render();
    if (online()) syncOfflineData(); else V.notify('Mode luring disimulasikan. Absensi dan laporan akan masuk antrean lokal.');
  }

  window.addEventListener('online', () => { paint(); syncOfflineData(); });
  window.addEventListener('offline', () => { paint(); V.notify('Koneksi terputus. Absensi dan laporan akan disimpan secara lokal (luring).', true); });

  const render = V.render;
  V.render = () => { render(); paint(); };

  if ('serviceWorker' in navigator && /^https?:$/.test(location.protocol)) navigator.serviceWorker.register('sw.js').catch(() => {});

  V.offline = {
    enqueue, syncOfflineData, setSimulated, queueable: type => QUEUEABLE.has(type),
    get online() { return online(); }, get simulated() { return simulated; }, get pending() { return queue().length; },
    message: (type, message) => online() || !QUEUEABLE.has(type) ? message : 'Tersimpan secara lokal (Luring). Akan disinkronkan saat koneksi kembali.'
  };
  window.syncOfflineData = syncOfflineData;
  paint();
  if (online() && queue().length) syncOfflineData();
})();
