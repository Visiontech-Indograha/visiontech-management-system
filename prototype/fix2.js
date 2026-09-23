const fs = require('fs');
let str = fs.readFileSync('js/workplans.js', 'utf8');

// Fix missing uppercase constants
const uppers = [
  "CHANGES_REQUESTED", "SAVE_REPORT", "SUBMIT_REPORT", "REVIEW_REPORT",
  "AWAITING_LEADER_ACCEPTANCE", "CANCEL_PLAN", "RESTORE_PLAN", "DELETE_PLAN"
];

uppers.forEach(word => {
  // we do a case insensitive replacement for the uppercase constant
  let regex = new RegExp(word, 'gi');
  str = str.replace(regex, word);
});

// Fix UI strings starting with 'A'
str = str.replace(/\b(a)jukan\b/g, 'Ajukan');
str = str.replace(/\b(a)khir\b/g, 'Akhir');
str = str.replace(/\b(a)ktif\b/g, 'Aktif');
str = str.replace(/\b(a)rsip\b/g, 'Arsip');
str = str.replace(/\b(a)rsipkan\b/g, 'Arsipkan');
str = str.replace(/\b(a)dendum\b/g, 'Adendum');
str = str.replace(/\b(a)set\b/g, 'Aset');
str = str.replace(/\b(a)lokasikan\b/g, 'Alokasikan');
str = str.replace(/\b(a)nggota\b/g, 'Anggota');
str = str.replace(/\b(a)lasan\b/g, 'Alasan');

// Special cases
str = str.replace(/'ajukan perpanjangan'/g, "'Ajukan perpanjangan'");
str = str.replace(/'ajukan pengembalian'/g, "'Ajukan pengembalian'");
str = str.replace(/ajukan penyelesaian/g, "Ajukan penyelesaian");
str = str.replace(/Laporan akhir/g, "Laporan Akhir");
str = str.replace(/Pekerjaan aktif/g, "Pekerjaan Aktif");

fs.writeFileSync('js/workplans.js', str, 'utf8');
console.log("Done");
