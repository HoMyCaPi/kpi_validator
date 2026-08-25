/**
 * ============================================================
 * KPI Validator Workspace - Apps Script Backend (Code.gs)
 * ============================================================
 * Vai trò: lớp trung gian (proxy) giữa Streamlit app và Google Sheets.
 * Script này chạy dưới danh tính TÀI KHOẢN NỘI BỘ của bạn (Execute as: Me),
 * nên không bị chính sách "chặn chia sẻ ra ngoài tổ chức" của Google Workspace
 * áp dụng cho Service Account (vốn bị coi là danh tính "external").
 *
 * CÁCH DEPLOY: xem README.md mục "Cấu hình Google Apps Script Backend".
 *
 * LƯU Ý QUAN TRỌNG:
 * - Tài khoản Google dùng để tạo & deploy script này BẮT BUỘC phải có quyền
 *   truy cập (Viewer/Editor tuỳ sheet) vào cả 4 Google Sheets nguồn, giống như
 *   một nhân viên bình thường mở file bằng tay.
 * - Đổi CONFIG.API_KEY thành 1 chuỗi bí mật do bạn tự đặt trước khi deploy.
 */

// ============================================================
// CẤU HÌNH - SỬA CÁC GIÁ TRỊ NÀY TRƯỚC KHI DEPLOY
// ============================================================
const CONFIG = {
  // Đặt 1 chuỗi ngẫu nhiên dài, giữ bí mật - dùng để xác thực request từ Streamlit
  API_KEY: "THAY_BANG_CHUOI_BI_MAT_CUA_BAN",

  // --- Nguồn 1: Monthly KPI (nơi ghi dữ liệu khi Submit) ---
  SPREADSHEET_KPI_ID: "196DIW3ZxGvJdbqEiCMui5F_mJXNGPSK0zwMM1Ab72j0",
  GID_THUCTE_SHEET: 1945875318,

  // --- Nguồn 2: PNS Data (tra cứu Mã bộ phận theo Mã NV) ---
  // ID này là ID của bản Google Sheets GỐC (đã convert từ .xlsx), không phải file .xlsx cũ.
  SPREADSHEET_PNS_ID: "1SuPBOCnfAWC75b4Uv2J-8e-M2uUcfUa4vljLLOyYvho",
  GID_PNS_DATA: 254853384,
  COL_PNS_MA_NV: 2,       // Cột B
  COL_PNS_MA_BO_PHAN: 6,  // Cột F

  // --- Nguồn Danh sách Nhà hàng ---
  SPREADSHEET_NHAHANG_ID: "1TPRbbPfzCsCxW55VYHyYVfn47wNhdYdiQ_uqazR0_5I",
  GID_NHAHANG: 0,
};

// ============================================================
// ENTRY POINTS (Google Apps Script Web App)
// ============================================================
function doGet(e) {
  return handleRequest(e);
}

function doPost(e) {
  return handleRequest(e);
}

function handleRequest(e) {
  try {
    const params = (e && e.parameter) || {};
    let body = {};
    if (e && e.postData && e.postData.contents) {
      try {
        body = JSON.parse(e.postData.contents);
      } catch (parseErr) {
        // Nếu body không phải JSON hợp lệ, bỏ qua và dùng params
      }
    }
    const input = Object.assign({}, params, body);

    if (input.api_key !== CONFIG.API_KEY) {
      return jsonResponse({ ok: false, error: "Unauthorized: sai API key" });
    }

    const action = input.action;
    let result;

    switch (action) {
      case "lookup_department":
        result = lookupDepartment(input.ma_nv);
        break;
      case "list_restaurants":
        result = listRestaurants();
        break;
      case "append_actual":
        result = appendActual(input.row);
        break;
      default:
        return jsonResponse({ ok: false, error: "Action không hợp lệ: " + action });
    }

    return jsonResponse({ ok: true, data: result });
  } catch (err) {
    return jsonResponse({ ok: false, error: String(err) });
  }
}

function jsonResponse(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

// ============================================================
// TIỆN ÍCH: LẤY WORKSHEET THEO GID (không phụ thuộc tên tab)
// ============================================================
function getSheetByGid(spreadsheetId, gid) {
  const ss = SpreadsheetApp.openById(spreadsheetId);
  const sheets = ss.getSheets();
  for (let i = 0; i < sheets.length; i++) {
    if (sheets[i].getSheetId() === Number(gid)) {
      return sheets[i];
    }
  }
  throw new Error("Không tìm thấy sheet với gid=" + gid + " trong spreadsheet " + spreadsheetId);
}

// ============================================================
// 1. TRA CỨU MÃ BỘ PHẬN THEO MÃ NHÂN VIÊN (View 1)
// ============================================================
function lookupDepartment(maNv) {
  if (!maNv) throw new Error("Thiếu mã nhân viên");
  const sheet = getSheetByGid(CONFIG.SPREADSHEET_PNS_ID, CONFIG.GID_PNS_DATA);
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return { found: false, department: null };

  const colB = sheet.getRange(1, CONFIG.COL_PNS_MA_NV, lastRow, 1).getValues();
  const colF = sheet.getRange(1, CONFIG.COL_PNS_MA_BO_PHAN, lastRow, 1).getValues();

  const target = String(maNv).trim().toUpperCase();
  for (let i = 1; i < colB.length; i++) { // i=0 là dòng tiêu đề, bỏ qua
    const val = String(colB[i][0] || "").trim().toUpperCase();
    if (val === target) {
      const dept = String(colF[i][0] || "").trim().toUpperCase();
      return { found: true, department: dept };
    }
  }
  return { found: false, department: null };
}

// ============================================================
// 2. DANH SÁCH NHÀ HÀNG (View 2)
// ============================================================
function listRestaurants() {
  const sheet = getSheetByGid(CONFIG.SPREADSHEET_NHAHANG_ID, CONFIG.GID_NHAHANG);
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return [];

  const values = sheet.getRange(2, 1, lastRow - 1, 3).getValues(); // Cột A,B,C từ hàng 2
  const result = [];
  for (let i = 0; i < values.length; i++) {
    const ma = String(values[i][0] || "").trim();
    if (!ma) continue;
    result.push({
      ma: ma,
      tinh: String(values[i][1] || "").trim(),
      dia_chi: String(values[i][2] || "").trim(),
    });
  }
  return result;
}

// ============================================================
// 3. GHI DÒNG VÀO SHEET "THỰC TẾ" (View 4 - Submit)
// ============================================================
function appendActual(row) {
  if (!row || !Array.isArray(row)) throw new Error("Thiếu dữ liệu dòng ghi (row)");
  const sheet = getSheetByGid(CONFIG.SPREADSHEET_KPI_ID, CONFIG.GID_THUCTE_SHEET);
  sheet.appendRow(row);
  return { appended: true };
}

// ============================================================
// HÀM TEST NHANH TRONG TRÌNH SOẠN THẢO APPS SCRIPT (không bắt buộc)
// Chọn hàm testLookup / testListRestaurants trong dropdown "Run" để thử,
// xem kết quả trong View > Logs (Ctrl+Enter) mà không cần deploy Web App.
// ============================================================
function testLookup() {
  Logger.log(JSON.stringify(lookupDepartment("TT00009")));
}

function testListRestaurants() {
  Logger.log(JSON.stringify(listRestaurants().slice(0, 3)));
}
