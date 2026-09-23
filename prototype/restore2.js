const fs = require('fs');
let str = fs.readFileSync('prompt.txt', 'utf16le');
str = str.replace("﻿Please restore the following file where all 'a' and 'A' are replaced with '-':\r\n", "");

const uppers = [
  "ASSET", "CCTV_ACS", "WALL_DISPLAY", "LEADER", "FINANCE", "CANCELLED", "DRAFT",
  "ACCEPTED", "APPEALED", "PENDING_PM", "AWAITING_LEADER_ACCEPTANCE", "ACTIVE",
  "INACTIVE", "CREATE_PLAN", "RESTORE_PLAN", "DELETE_PLAN", "CANCEL_PLAN",
  "APPROVE_CHANGE", "REJECT_CHANGE", "APPROVE_COMPLETE", "RETURN_COMPLETE", "START",
  "CHECK_ASSET", "RESERVE_ASSET", "SAVE_ATTACHMENTS", "SAVE_REPORT", "SUBMIT_REPORT",
  "REVIEW_REPORT", "CHANGES_REQUESTED", "APPROVED", "APPROVE", "AVAILABLE",
  "MAINTENANCE", "IN_PROGRESS", "PUBLISHED", "COMPLETION_REVIEW", "EFFECTIVE", "REJECTED"
];

uppers.forEach(word => {
  let mangled = word.replace(/[Aa]/g, '—');
  str = str.split(mangled).join(word);
});

const capitalized = [
  "Math", "Date", "Array", "Ajukan", "Akhir", "Aktif", "Arsip", "Arsipkan",
  "Adendum", "Aset", "Alokasikan", "Anggota", "Alasan", "Anda", "Apakah"
];

capitalized.forEach(word => {
  let mangled = word.replace(/[Aa]/g, '—');
  str = str.split(mangled).join(word);
});

// Also fix camelCase variables with 'A'
const camelCases = [
  "deletedAt", "startDate", "endDate", "createdAt", "updatedAt",
  "submittedAt", "reviewedAt", "pendingAssets"
];

camelCases.forEach(word => {
  let mangled = word.replace(/[Aa]/g, '—');
  str = str.split(mangled).join(word);
});

// Now replace all remaining em-dashes with lowercase 'a'
str = str.replace(/—/g, 'a');

fs.writeFileSync('js/workplans.js', str, 'utf8');
console.log("Restored accurately");
