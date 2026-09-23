(() => {
  const V = VT, U = VTUI;
  // Simulated site coordinates; not surveyed positions.
  const SITES = [
    ['Gedung Merdeka', 3.5896, 98.6739],
    ['Kantor Pusat', 3.5952, 98.6722],
    ['Warehouse Tanjung Morawa', 3.5220, 98.7870],
    ['Command Center', 3.5780, 98.6650],
    ['Ruang Kontrol', 3.5850, 98.6800],
    ['Site Binjai', 3.6000, 98.4854]
  ];
  const radius = () => V.D.attendanceRadius || 100;
  const siteName = location => (SITES.find(([name]) => String(location || '').startsWith(name)) || [String(location || '').split(',')[0].trim()])[0];
  const siteCoords = name => { const s = SITES.find(([n]) => n === name); return s ? { lat: s[1], lng: s[2] } : null; };

  function haversine(a, b) {
    const R = 6371000, rad = x => x * Math.PI / 180;
    const dLat = rad(b.lat - a.lat), dLng = rad(b.lng - a.lng);
    const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLng / 2) ** 2;
    return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)));
  }
  const offset = (point, meters) => ({ lat: point.lat + meters / 111320, lng: point.lng });

  function sitesForActor() {
    const own = V.work.plans().filter(p => ['ACCEPTED', 'IN_PROGRESS', 'COMPLETION_REVIEW'].includes(p.status)).map(p => siteName(p.location));
    return [...new Set([...own, ...SITES.map(([n]) => n)])].filter(siteCoords);
  }

  function openCheckIn() {
    const sites = sitesForActor(), first = siteCoords(sites[0]);
    V.dialog('Catat masuk', U.form('check-in',
      U.select('site', 'Lokasi', sites.map(s => [s, s]), sites[0], 'data-geo-site') +
      U.select('source', 'Sumber', [['MOBILE', 'HP'], ['MACHINE', 'Mesin (simulasi)']], 'MOBILE', 'data-geo-source') +
      `<div data-geo-mobile><div class="actions spaced"><button type="button" class="btn small" data-geo="gps">Gunakan GPS perangkat</button><button type="button" class="btn small" data-geo="0">Simulasi: di lokasi</button><button type="button" class="btn small" data-geo="150">Simulasi: 150 m</button><button type="button" class="btn small" data-geo="10000">Simulasi: 10 km</button></div>` +
      U.input('lat', 'Lintang (latitude)', first.lat.toFixed(6), 'number', 'step="any" min="-90" max="90" required') +
      U.input('lng', 'Bujur (longitude)', first.lng.toFixed(6), 'number', 'step="any" min="-180" max="180" required') +
      `<input type="hidden" name="geoSource" value="SIMULASI"><p class="field-hint" data-geo-distance></p>` +
      `<div data-geo-selfie hidden>${U.note('Di luar radius toleransi. Ambil swafoto dengan kamera depan sebagai bukti kehadiran.', 'error')}<label>Swafoto (kamera depan)<input type="file" name="selfie" accept="image/*" capture="user" aria-label="Swafoto (kamera depan)"></label></div></div>` +
      U.note('Jam masuk menggunakan 08.00 WIB pada tanggal simulasi. Koordinat lokasi proyek adalah data simulasi.'),
      'Catat masuk'));
    refresh();
  }

  function formEl() { const d = document.querySelector('#dialog'); return d?.open ? d.querySelector('form[data-form="check-in"]') : null; }
  function current(form) {
    const site = siteCoords(form.site.value), lat = Number(form.lat.value), lng = Number(form.lng.value);
    const machine = form.source.value === 'MACHINE';
    const valid = Number.isFinite(lat) && Number.isFinite(lng) && form.lat.value !== '' && form.lng.value !== '';
    // Keep the precise distance for the radius decision; round only when showing it.
    return { site, machine, valid, distance: machine ? 0 : valid && site ? haversine(site, { lat, lng }) : NaN };
  }
  function refresh() {
    const form = formEl(); if (!form) return;
    const c = current(form), outside = !c.machine && c.distance > radius();
    form.querySelector('[data-geo-mobile]').hidden = c.machine;
    ['lat', 'lng'].forEach(n => { form[n].required = !c.machine; });
    const shown = Number.isFinite(c.distance) ? (Math.abs(c.distance - radius()) < 1 ? c.distance.toFixed(1) : Math.round(c.distance).toLocaleString('id-ID')) : '';
    form.querySelector('[data-geo-distance]').textContent = c.machine ? '' : Number.isFinite(c.distance) ? `Jarak ke titik lokasi: ${shown} m (radius ${radius()} m)${outside ? ' · di luar radius' : ''}.` : 'Koordinat belum lengkap.';
    form.querySelector('[data-geo-selfie]').hidden = !outside;
    form.selfie.required = outside;
  }
  function setPoint(form, point, origin) {
    form.lat.value = point.lat.toFixed(6); form.lng.value = point.lng.toFixed(6); form.geoSource.value = origin; refresh();
  }

  document.addEventListener('click', event => {
    const btn = event.target.closest('[data-geo]'), form = btn && formEl();
    if (!form) return;
    const mode = btn.dataset.geo, site = siteCoords(form.site.value);
    if (mode !== 'gps') { setPoint(form, offset(site, Number(mode)), 'SIMULASI'); return; }
    if (!navigator.geolocation) { V.notify('GPS tidak tersedia di perangkat ini. Gunakan koordinat simulasi.', true); return; }
    btn.disabled = true; btn.textContent = 'Mengambil lokasi…';
    navigator.geolocation.getCurrentPosition(pos => {
      btn.disabled = false; btn.textContent = 'Gunakan GPS perangkat';
      if (formEl() === form) setPoint(form, { lat: pos.coords.latitude, lng: pos.coords.longitude }, 'GPS');
    }, err => {
      btn.disabled = false; btn.textContent = 'Gunakan GPS perangkat';
      V.notify('Lokasi GPS tidak dapat diambil (' + (err.message || 'izin ditolak') + '). Gunakan koordinat simulasi.', true);
    }, { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 });
  });
  document.addEventListener('input', event => { if (event.target.closest('form[data-form="check-in"]')) refresh(); });
  document.addEventListener('change', event => {
    const form = event.target.closest('form[data-form="check-in"]'); if (!form) return;
    if (event.target.matches('[data-geo-site]')) setPoint(form, siteCoords(form.site.value), 'SIMULASI'); else refresh();
  });

  V.forms['check-in'] = async form => {
    const c = current(form), outside = !c.machine && c.distance > radius();
    if (!c.machine && !c.valid) throw Error('Koordinat lokasi belum lengkap.');
    const payload = { site: form.site.value, source: form.source.value, distance: Math.round(c.distance * 10) / 10 };
    if (!c.machine) Object.assign(payload, { lat: Number(form.lat.value), lng: Number(form.lng.value), geoSource: form.geoSource.value });
    const file = form.selfie.files?.[0];
    if (outside) {
      if (!file) throw Error(`Di luar radius toleransi (${Math.round(c.distance)} m > ${radius()} m): swafoto wajib dilampirkan.`);
      if (!/^image\//.test(file.type)) throw Error('Swafoto harus berupa gambar dari kamera.');
      payload.selfie = await VTStorage.put(file);
    }
    if (V.run('CHECK_IN', payload)) {
      V.closeDialog();
      const record = V.state.attendance[0];
      // In-app warning only: native browser dialogs block the page and were removed in B5.
      if (record?.late) V.notify(`Tercatat terlambat: masuk ${U.clock(record.checkIn)} WIB, batas ${U.clock(new Date(record.date + 'T08:00:00+07:00'))} WIB.`, true);
    }
  };

  V.geo = { haversine, siteName, siteCoords, openCheckIn, sites: SITES.map(([n, lat, lng]) => ({ name: n, lat, lng })) };
})();
