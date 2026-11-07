/**
 * KidharMilega Supplier Finder → Google Sheet lead logger.
 * Paste this into Extensions → Apps Script of a new Google Sheet and deploy as a Web app
 * (see tools_src/supplier-finder/SETUP.md). Every email capture and every later search is one row.
 */
var SHEET_NAME = 'Leads';
// Events: lead / search (Supplier Finder), export_waitlist / export_search (Export Buyer Finder),
// scheme_report / scheme_search (Scheme Finder; the profile and matched scheme ids go in 'details').
var HEADERS = ['timestamp', 'event', 'email', 'phone', 'hsn', 'hsn_name', 'product', 'state', 'district',
               'utm_source', 'utm_medium', 'utm_campaign', 'referrer', 'page', 'segment', 'details'];

function doPost(e) {
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(10000);
    var data = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    var email = clean(data.email, 120);
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) return out({ ok: false, error: 'bad email' });

    var sheet = getSheet();
    var row = HEADERS.map(function (h) {
      if (h === 'timestamp') return new Date();
      if (h === 'email') return email;
      return clean(data[h], h === 'page' || h === 'referrer' || h === 'details' ? 1000 : 200);
    });
    sheet.appendRow(row);
    return out({ ok: true });
  } catch (err) {
    return out({ ok: false, error: String(err) });
  } finally {
    try { lock.releaseLock(); } catch (x) {}
  }
}

function doGet() { return out({ ok: true, service: 'kidharmilega-supplier-finder' }); }

function getSheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(HEADERS);
    sheet.setFrozenRows(1);
    sheet.getRange(1, 1, 1, HEADERS.length).setFontWeight('bold');
  }
  return sheet;
}

// Trim, cap length, and stop values like "=HYPERLINK(...)" from running as formulas in the sheet.
function clean(v, max) {
  var s = String(v == null ? '' : v).replace(/[\r\n\t]+/g, ' ').trim().slice(0, max || 200);
  return /^[=+\-@]/.test(s) ? "'" + s : s;
}

function out(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
