const fs = require('fs');
let str = fs.readFileSync('js/workplans.js', 'utf8');

const uppers = [
  "APPROVED", "APPROVE", "AVAILABLE", "MAINTENANCE", "ACTIVE", "INACTIVE",
  "APPEALED", "ACCEPTED", "DRAFT", "CANCELLED", "CREATE_PLAN", "RESTORE_PLAN",
  "DELETE_PLAN", "CANCEL_PLAN", "APPROVE_CHANGE", "REJECT_CHANGE",
  "APPROVE_COMPLETE", "START", "CHECK_ASSET", "RESERVE_ASSET", "SAVE_ATTACHMENTS",
  "SAVE_REPORT", "AWAITING_LEADER_ACCEPTANCE", "CHANGES_REQUESTED", "ASSET",
  "CCTV_ACS", "WALL_DISPLAY", "LEADER", "FINANCE"
];

uppers.forEach(word => {
  let regex = new RegExp(word, 'gi');
  str = str.replace(regex, word);
});

fs.writeFileSync('js/workplans.js', str, 'utf8');
console.log("Done");
