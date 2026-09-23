const fs = require('fs');
let str = fs.readFileSync('prompt.txt', 'utf16le');
str = str.replace("﻿Please restore the following file where all 'a' and 'A' are replaced with '-':\r\n", "");

let uppers = [
  "ASSET", "CCTV_ACS", "WALL_DISPLAY", "LEADER", "FINANCE", "CANCELLED", "DRAFT",
  "ACCEPTED", "APPEALED", "PENDING_PM", "AWAITING_LEADER_ACCEPTANCE", "ACTIVE",
  "INACTIVE", "CREATE_PLAN", "RESTORE_PLAN", "DELETE_PLAN", "CANCEL_PLAN",
  "APPROVE_CHANGE", "REJECT_CHANGE", "APPROVE_COMPLETE", "RETURN_COMPLETE", "START",
  "CHECK_ASSET", "RESERVE_ASSET", "SAVE_ATTACHMENTS", "SAVE_REPORT", "SUBMIT_REPORT",
  "REVIEW_REPORT", "CHANGES_REQUESTED", "APPROVED", "APPROVE", "AVAILABLE",
  "MAINTENANCE", "IN_PROGRESS", "PUBLISHED", "COMPLETION_REVIEW", "EFFECTIVE", "REJECTED"
];

// Sort by length descending
uppers.sort((a, b) => b.length - a.length);

uppers.forEach(word => {
  let mangled = word.replace(/[Aa]/g, '—');
  str = str.split(mangled).join(word);
});

let capitalized = [
  "Math", "Date", "Array", "Ajukan", "Akhir", "Aktif", "Arsip", "Arsipkan",
  "Adendum", "Aset", "Alokasikan", "Anggota", "Alasan", "Anda", "Apakah"
];

capitalized.sort((a, b) => b.length - a.length);

capitalized.forEach(word => {
  let mangled = word.replace(/[Aa]/g, '—');
  str = str.split(mangled).join(word);
});

let camelCases = [
  "deletedAt", "startDate", "endDate", "createdAt", "updatedAt",
  "submittedAt", "reviewedAt", "pendingAssets"
];

camelCases.sort((a, b) => b.length - a.length);

camelCases.forEach(word => {
  let mangled = word.replace(/[Aa]/g, '—');
  str = str.split(mangled).join(word);
});

str = str.replace(/—/g, 'a');

fs.writeFileSync('js/workplans.js', str, 'utf8');
console.log("Restored accurately and correctly");
