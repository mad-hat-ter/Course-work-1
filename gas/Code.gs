var HIDDEN_SHEETS = ['Настройки', 'Сотрудники', 'Журнал', 'Метаданные'];
var DAY_COLUMNS = 7; // B..H
var FIRST_DAY_COL = 2;
var FIRST_HOUR_ROW = 2;

var HOURS = [
  9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 0
];

function doGet(e) {
  try {
    var action = (e && e.parameter && e.parameter.action) || '';
    switch (action) {
      case 'free_slots':
        return jsonResponse(getFreeSlots(e.parameter.sheet));
      case 'sheet_data':
        return jsonResponse(getSheetData(e.parameter.sheet));
      case 'employees':
        return jsonResponse(getEmployees());
      case 'metadata':
        return jsonResponse(getMetadata());
      case 'settings':
        return jsonResponse(getSettings());
      case 'schedule_sheets':
        return jsonResponse({ sheets: listScheduleSheets() });
      case 'shifts_at_hour':
        return jsonResponse({ shifts: getShiftsAtHour(e.parameter.target) });
      case 'bookable_view':
        return jsonResponse(getBookableView(e.parameter.sheet));
      case 'bootstrap':
        return jsonResponse(getBootstrap());
      default:
        return jsonResponse({ error: 'unknown action' }, 400);
    }
  } catch (err) {
    return jsonResponse({ error: String(err) }, 500);
  }
}

function doPost(e) {
  try {
    var body = JSON.parse(e.postData.contents);
    switch (body.action) {
      case 'book':
        return jsonResponse(bookShift(body));
      case 'register_sheet':
        return jsonResponse(registerSheet(body));
      default:
        return jsonResponse({ error: 'unknown action' }, 400);
    }
  } catch (err) {
    return jsonResponse({ error: String(err) }, 500);
  }
}

function jsonResponse(data, code) {
  code = code || 200;
  return ContentService.createTextOutput(JSON.stringify(data)).setMimeType(ContentService.MimeType.JSON);
}

function getSpreadsheet() {
  return SpreadsheetApp.getActiveSpreadsheet();
}

function getBootstrap() {
  return {
    employees: getEmployees(),
    settings: getSettings(),
    metadata: getMetadata(),
    schedule_sheets: listScheduleSheets()
  };
}

function getSettings() {
  var sheet = getSpreadsheet().getSheetByName('Настройки');
  if (!sheet) {
    return { BASE_RATE: 400, PREMIUM_RATE: 600, NOTIFY_MINUTES: 15 };
  }
  return {
    BASE_RATE: Number(sheet.getRange('B1').getValue()) || 400,
    PREMIUM_RATE: Number(sheet.getRange('B2').getValue()) || 600,
    NOTIFY_MINUTES: Number(sheet.getRange('B3').getValue()) || 15
  };
}

function getEmployees() {
  var sheet = getSpreadsheet().getSheetByName('Сотрудники');
  if (!sheet) return [];
  var rows = sheet.getDataRange().getValues();
  var result = [];
  for (var i = 1; i < rows.length; i++) {
    if (!rows[i][0]) continue;
    result.push({
      telegram_id: rows[i][0],
      full_name: rows[i][1],
      role: rows[i][2] || 'curator',
      is_active: rows[i][3] !== false && rows[i][3] !== 'FALSE' && rows[i][3] !== 0
    });
  }
  return result;
}

function getMetadata() {
  var sheet = getSpreadsheet().getSheetByName('Метаданные');
  if (!sheet) return [];
  var rows = sheet.getDataRange().getValues();
  var result = [];
  for (var i = 1; i < rows.length; i++) {
    if (!rows[i][0]) continue;
    result.push({
      sheet_name: String(rows[i][0]),
      opening_time: formatDateTime(rows[i][1]),
      is_active: rows[i][2] !== false && rows[i][2] !== 'FALSE'
    });
  }
  return result;
}

function formatDateTime(value) {
  if (value instanceof Date) {
    return Utilities.formatDate(value, 'Europe/Moscow', 'yyyy-MM-dd HH:mm:ss');
  }
  return String(value);
}

function normalizeSheetKey(name) {
  return String(name).replace(/[\u2013\u2014\u2212-]/g, '-').trim();
}

function listScheduleSheets() {
  var ss = getSpreadsheet();
  var tabByKey = {};
  ss.getSheets().forEach(function (sh) {
    var name = sh.getName();
    if (HIDDEN_SHEETS.indexOf(name) >= 0) return;
    tabByKey[normalizeSheetKey(name)] = name;
  });

  var names = [];
  var seen = {};

  function addSheet(name) {
    if (!name || seen[name]) return;
    seen[name] = true;
    names.push(name);
  }

  getMetadata().forEach(function (m) {
    if (!m.is_active) return;
    var tab = tabByKey[normalizeSheetKey(m.sheet_name)];
    if (tab) addSheet(tab);
  });

  ss.getSheets().forEach(function (sh) {
    var name = sh.getName();
    if (HIDDEN_SHEETS.indexOf(name) >= 0) return;
    if (isScheduleSheetName(name)) addSheet(name);
  });

  return names;
}

function isScheduleSheetName(name) {
  return /^\d{2}\.\d{2}-\d{2}\.\d{2}$/.test(normalizeSheetKey(name));
}

function parseWeekStart(sheetName) {
  var match = sheetName.match(/^(\d{2})\.(\d{2})/);
  if (!match) return null;
  var day = parseInt(match[1], 10);
  var month = parseInt(match[2], 10);
  var year = new Date().getFullYear();
  var d = new Date(year, month - 1, day);
  var now = new Date();
  if (d > now && (d - now) > 180 * 86400000) {
    d = new Date(year - 1, month - 1, day);
  }
  if (now - d > 400 * 86400000) {
    d = new Date(year + 1, month - 1, day);
  }
  return d;
}

function slotDateTime(weekStart, dayIndex, hour) {
  var d = new Date(weekStart.getTime());
  d.setDate(d.getDate() + dayIndex);
  if (hour === 0) {
    d.setDate(d.getDate() + 1);
    d.setHours(0, 0, 0, 0);
  } else {
    d.setHours(hour, 0, 0, 0);
  }
  return d;
}

function scanSheetGridCached(sheet) {
  var sheetName = sheet.getName();
  var cache = CacheService.getScriptCache();
  var key = 'grid:' + sheetName;
  var cached = cache.get(key);
  if (cached) {
    try {
      return JSON.parse(cached);
    } catch (e) {
      cache.remove(key);
    }
  }
  var slots = scanSheetGrid(sheet);
  try {
    cache.put(key, JSON.stringify(slots), 90);
  } catch (e) {
  }
  return slots;
}

function invalidateGridCache(sheetName) {
  CacheService.getScriptCache().remove('grid:' + sheetName);
}

function scanSheetGrid(sheet) {
  var sheetName = sheet.getName();
  var weekStart = parseWeekStart(sheetName);
  if (!weekStart) return [];
  var range = sheet.getDataRange();
  var values = range.getValues();
  if (!values.length) return [];
  var startRow = range.getRow();
  var startCol = range.getColumn();
  var dayColumns = findDayColumns(values, startCol, weekStart);
  var timeColOffset = findTimeColumnOffset(values);
  var mergeBlocked = buildMergeBlockMap(sheet);
  var slots = [];
  var currentHour = null;
  var headerRows = Math.min(5, values.length);
  for (var r = 0; r < values.length; r++) {
    var rowNum = startRow + r;
    if (r < headerRows && rowLooksLikeHeader(values[r], dayColumns, startCol, weekStart)) {
      continue;
    }
    var timeText = String(values[r][timeColOffset] || '').trim();
    var parsedHour = parseTimeBlock(timeText);
    if (parsedHour !== null) {
      currentHour = parsedHour;
    }
    if (currentHour === null) {
      continue;
    }

    for (var i = 0; i < dayColumns.length; i++) {
      var dc = dayColumns[i];
      var colOffset = dc.col - startCol;
      if (colOffset < 0 || colOffset >= values[r].length) continue;
      if (colOffset === timeColOffset) continue;
      var val = values[r][colOffset];
      var text = val ? String(val).trim() : '';
      if (parseTimeBlock(text) !== null) continue;
      if (mergeBlocked[rowNum + ':' + dc.col]) continue;
      var cellA1 = columnToLetter(dc.col) + rowNum;
      var dt = slotDateTime(weekStart, dc.dayIndex, currentHour);
      var hourLabel = currentHour === 0 ? '00:00' : (currentHour < 10 ? '0' : '') + currentHour + ':00';
      var label = dc.day_label + ' ' + hourLabel;

      slots.push({
        cell: cellA1,
        row: rowNum,
        col: dc.col,
        value: text,
        hour: hourLabel,
        day: dc.dayIndex,
        day_label: dc.day_label,
        label: label,
        datetime: formatIsoMsk(dt),
        is_empty: text === ''
      });
    }
  }
  return slots;
}


function findDayColumns(values, startCol, weekStart) {
  var cols = [];
  var seen = {};
  var maxHeaderRow = Math.min(6, values.length);
  for (var r = 0; r < maxHeaderRow; r++) {
    for (var c = 0; c < values[r].length; c++) {
      var raw = String(values[r][c]).trim();
      if (!raw) continue;
      var info = matchDayHeader(raw, weekStart);
      if (info === null) continue;
      var colNum = startCol + c;
      var key = String(colNum);
      if (seen[key]) continue;
      seen[key] = true;
      cols.push({ col: colNum, dayIndex: info.idx, day_label: info.label });
    }
  }
  cols.sort(function (a, b) { return a.col - b.col; });
  return cols;
}

function matchDayHeader(raw, weekStart) {
  var lower = raw.toLowerCase();
  var dayNames = [
    { re: /пн/, idx: 0, label: 'Пн' },
    { re: /^mon/, idx: 0, label: 'Пн' },
    { re: /вт/, idx: 1, label: 'Вт' },
    { re: /^tue/, idx: 1, label: 'Вт' },
    { re: /ср/, idx: 2, label: 'Ср' },
    { re: /^wed/, idx: 2, label: 'Ср' },
    { re: /чт/, idx: 3, label: 'Чт' },
    { re: /^thu/, idx: 3, label: 'Чт' },
    { re: /пт/, idx: 4, label: 'Пт' },
    { re: /^fri/, idx: 4, label: 'Пт' },
    { re: /сб/, idx: 5, label: 'Сб' },
    { re: /^sat/, idx: 5, label: 'Сб' },
    { re: /вс/, idx: 6, label: 'Вс' },
    { re: /^sun/, idx: 6, label: 'Вс' }
  ];
  for (var i = 0; i < dayNames.length; i++) {
    if (dayNames[i].re.test(lower)) {
      return { idx: dayNames[i].idx, label: dayNames[i].label };
    }
  }

  var dm = raw.match(/^(\d{1,2})\.(\d{1,2})(?:\.(\d{2,4}))?$/);
  if (dm) {
    var day = parseInt(dm[1], 10);
    var month = parseInt(dm[2], 10);
    var year = dm[3] ? parseInt(dm[3], 10) : weekStart.getFullYear();
    if (year < 100) year += 2000;
    var idx = dayIndexFromDate(day, month, year, weekStart);
    if (idx !== null) {
      return { idx: idx, label: ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'][idx] };
    }
  }
  return null;
}

function dayIndexFromDate(day, month, year, weekStart) {
  var target = new Date(year, month - 1, day);
  var start = new Date(weekStart.getFullYear(), weekStart.getMonth(), weekStart.getDate());
  var diff = Math.round((target.getTime() - start.getTime()) / 86400000);
  if (diff >= 0 && diff <= 6) return diff;
  return null;
}

function findTimeColumnOffset(values) {
  var scores = {};
  for (var r = 0; r < values.length; r++) {
    for (var c = 0; c < Math.min(4, values[r].length); c++) {
      if (parseTimeBlock(String(values[r][c])) !== null) {
        scores[c] = (scores[c] || 0) + 1;
      }
    }
  }
  var best = 1;
  var bestScore = 0;
  for (var key in scores) {
    if (scores[key] > bestScore) {
      bestScore = scores[key];
      best = parseInt(key, 10);
    }
  }
  return best;
}

function parseTimeBlock(text) {
  if (!text) return null;
  var m = String(text).match(/(\d{1,2}):(\d{2})\s*[–\-]\s*(\d{1,2}):(\d{2})/);
  if (!m) return null;
  return parseInt(m[1], 10);
}

function buildMergeBlockMap(sheet) {
  var blocked = {};
  var dataRange = sheet.getDataRange();
  var merges = dataRange.getMergedRanges();
  for (var i = 0; i < merges.length; i++) {
    var m = merges[i];
    var startRow = m.getRow();
    var startCol = m.getColumn();
    var numRows = m.getNumRows();
    var numCols = m.getNumColumns();
    if (numCols > 1) {
      for (var r = 0; r < numRows; r++) {
        for (var c = 0; c < numCols; c++) {
          blocked[(startRow + r) + ':' + (startCol + c)] = true;
        }
      }
    } else if (numRows > 1) {
      for (var r = 1; r < numRows; r++) {
        blocked[(startRow + r) + ':' + startCol] = true;
      }
    }
  }
  return blocked;
}

function isBookableCellFast(blocked, rowNum, colNum) {
  return !blocked[rowNum + ':' + colNum];
}

function rowLooksLikeHeader(row, dayColumns, startCol, weekStart) {
  for (var i = 0; i < dayColumns.length; i++) {
    var off = dayColumns[i].col - startCol;
    if (off >= 0 && off < row.length) {
      var raw = String(row[off]).trim();
      if (matchDayHeader(raw, weekStart) !== null) return true;
    }
  }
  return false;
}

function columnToLetter(column) {
  var temp = '';
  var letter = '';
  while (column > 0) {
    temp = (column - 1) % 26;
    letter = String.fromCharCode(temp + 65) + letter;
    column = (column - temp - 1) / 26;
  }
  return letter;
}

function formatIsoMsk(date) {
  return Utilities.formatDate(date, 'Europe/Moscow', "yyyy-MM-dd'T'HH:mm:ss");
}

function getFreeSlots(sheetName) {
  var view = getBookableView(sheetName);
  if (view.error) return view;
  return { sheet: sheetName, slots: view.slots };
}

function getBookableView(sheetName) {
  var sheet = getSpreadsheet().getSheetByName(sheetName);
  if (!sheet) return { error: 'sheet_not_found', slots: [], entries: [] };
  var all = scanSheetGridCached(sheet);
  return {
    sheet: sheetName,
    slots: all.filter(function (s) { return s.is_empty; }),
    entries: all.filter(function (s) { return !s.is_empty; }).map(function (s) {
      return {
        cell: s.cell,
        value: s.value,
        label: s.label,
        datetime: s.datetime,
        hour: s.hour,
        day_label: s.day_label,
        is_reserve: String(s.value).trim().slice(-1) === '*'
      };
    })
  };
}

function getSheetData(sheetName) {
  var view = getBookableView(sheetName);
  if (view.error) return view;
  return { sheet: sheetName, entries: view.entries };
}

function getShiftsAtHour(targetIso) {
  var target = new Date(targetIso);
  var sheets = listScheduleSheets();
  var result = [];
  sheets.forEach(function (name) {
    var sheet = getSpreadsheet().getSheetByName(name);
    if (!sheet) return;
    scanSheetGridCached(sheet).forEach(function (slot) {
      if (slot.is_empty) return;
      var slotDate = new Date(slot.datetime);
      if (Math.abs(slotDate.getTime() - target.getTime()) < 60000) {
        result.push({
          name: slot.value,
          shift_key: name + ':' + slot.cell + ':' + slot.datetime,
          sheet: name,
          cell: slot.cell
        });
      }
    });
  });
  return result;
}

function bookShift(body) {
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) {
    return { success: false, reason: 'lock_timeout' };
  }
  try {
    var ss = getSpreadsheet();
    var sheet = ss.getSheetByName(body.sheet);
    if (!sheet) return { success: false, reason: 'sheet_not_found' };

    var range = sheet.getRange(body.cell);
    var current = String(range.getValue()).trim();
    if (current !== '') {
      return { success: false, reason: 'occupied' };
    }
    range.setValue(body.name);
    invalidateGridCache(body.sheet);
    appendLog(body.tg_id, 'book', body.sheet, body.cell, body.name);
    return { success: true, cell: body.cell, sheet: body.sheet };
  } finally {
    lock.releaseLock();
  }
}

function registerSheet(body) {
  var ss = getSpreadsheet();
  var sheet = ss.getSheetByName(body.sheet);
  if (!sheet) return { success: false, reason: 'sheet_not_found' };

  var metaSheet = ss.getSheetByName('Метаданные');
  if (!metaSheet) {
    metaSheet = ss.insertSheet('Метаданные');
    metaSheet.appendRow(['sheet_name', 'opening_time', 'is_active']);
  }

  var rows = metaSheet.getDataRange().getValues();
  for (var i = 1; i < rows.length; i++) {
    if (String(rows[i][0]) === body.sheet) {
      metaSheet.getRange(i + 1, 2).setValue(body.opening_time);
      metaSheet.getRange(i + 1, 3).setValue(true);
      return { success: true, updated: true };
    }
  }
  metaSheet.appendRow([body.sheet, body.opening_time, true]);
  return { success: true, updated: false };
}

function appendLog(tgId, action, sheetName, cell, details) {
  var ss = getSpreadsheet();
  var logSheet = ss.getSheetByName('Журнал');
  if (!logSheet) {
    logSheet = ss.insertSheet('Журнал');
    logSheet.appendRow(['timestamp', 'telegram_id', 'action', 'sheet', 'cell', 'details']);
  }
  var ts = Utilities.formatDate(new Date(), 'Europe/Moscow', 'yyyy-MM-dd HH:mm:ss');
  logSheet.appendRow([ts, tgId, action, sheetName, cell, details]);
}
