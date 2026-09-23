const fs = require('fs');
let buf = fs.readFileSync('js/workplans.js');
let str = buf.toString('latin1');
str = str.replace(/\x97/g, 'a');

const uppers = [
  "ASSET", "CCTV_ACS", "WALL_DISPLAY", "LEADER", "FINANCE",
  "CANCELLED", "DRAFT", "ACCEPTED", "APPEALED",
  "PENDING_PM", "AWAITING_LEADER_ACCEPTANCE", "ACTIVE",
  "CREATE_PLAN", "DELETE_PLAN", "RESTORE_PLAN", "APPROVE_CHANGE", "REJECT_CHANGE",
  "APPROVE_COMPLETE", "RETURN_COMPLETE", "CANCEL_PLAN", "START", "REVISE",
  "CHECK_ASSET", "RESERVE_ASSET", "REVIEW_WEEKLY", "REQUEST_COMPLETE", "SAVE_ATTACHMENTS",
  "IN_PROGRESS", "PUBLISHED", "COMPLETION_REVIEW", "EFFECTIVE", "REJECTED", "PM"
];

uppers.forEach(word => {
  let mangled = word.replace(/A/g, 'a');
  str = str.split(mangled).join(word);
});

// Capitalize specific standard JS objects and specific strings
str = str.replace(/\bmath\./g, 'Math.');
str = str.replace(/new date/g, 'new Date');
str = str.replace(/Date\.now/g, 'Date.now');
str = str.replace(/\.toLowerCase\(\)/g, '.toLowerCase()');
str = str.replace(/\.toUpperCase\(\)/g, '.toUpperCase()');
str = str.replace(/\barray\b/g, 'Array');

fs.writeFileSync('js/workplans.js', str, 'utf8');
console.log("Done");
