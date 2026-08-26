# -*- coding: utf-8 -*-
"""
config.py
---------
Nơi tập trung TOÀN BỘ cấu hình của ứng dụng KPI Validator Workspace:
- ID / GID của các Google Sheets nguồn dữ liệu
- Bảng màu thương hiệu (branding)
- Danh sách các trường KPI, gắn với bộ phận sở hữu (department ownership)
- Thứ tự cột khi ghi dữ liệu vào sheet "Thực tế"

Sửa các giá trị trong file này nếu ID/GID của Google Sheet thay đổi trong tương lai,
KHÔNG cần sửa logic ở các file khác.
"""

# ============================================================
# 1. THÔNG TIN CÁC GOOGLE SHEETS NGUỒN DỮ LIỆU
# ============================================================

# --- Nguồn 1: Monthly KPI (Sheet KPI + Sheet Thực tế) ---
SPREADSHEET_KPI_ID = "196DIW3ZxGvJdbqEiCMui5F_mJXNGPSK0zwMM1Ab72j0"
GID_KPI_SHEET = 0                 # Sheet "KPI" (định nghĩa cấu trúc chỉ tiêu)
GID_THUCTE_SHEET = 1945875318     # Sheet "Thực tế" -> nơi APPEND dữ liệu khi Submit

# --- Nguồn 2: 2026 - PNS Data share - Ngọc (tra cứu Mã bộ phận theo Mã NV) ---
# LƯU Ý: file gốc trước đây là .xlsx thô trên Drive (API không thao tác được),
# đã convert sang Google Sheets gốc qua "Tệp > Lưu dưới dạng Google Trang tính" -> ID mới.
SPREADSHEET_PNS_ID = "1SuPBOCnfAWC75b4Uv2J-8e-M2uUcfUa4vljLLOyYvho"
GID_PNS_DATA = 254853384
# Cột B = Mã nhân viên, Cột F = Mã bộ phận (theo yêu cầu nghiệp vụ)
COL_PNS_MA_NV = "B"
COL_PNS_MA_BO_PHAN = "F"

# --- Nguồn Danh sách Nhà hàng ---
SPREADSHEET_NHAHANG_ID = "1TPRbbPfzCsCxW55VYHyYVfn47wNhdYdiQ_uqazR0_5I"
GID_NHAHANG = 0
# Cột A = Mã nhà hàng, Cột B = Tỉnh/Thành phố, Cột C = Địa chỉ chi tiết
COL_NH_MA = "A"
COL_NH_TINH = "B"
COL_NH_DIACHI = "C"

# --- File Template mẫu (dùng để người dùng tải về & upload lại khi nhập theo cách 2) ---
TEMPLATE_SPREADSHEET_ID = "1mjhtClhmlMDINF_dUZEHbGeQ7WrxGm3c6ZjxhM7_Y7c"
TEMPLATE_DOWNLOAD_URL = (
    f"https://docs.google.com/spreadsheets/d/{TEMPLATE_SPREADSHEET_ID}/export?format=xlsx"
)

# ============================================================
# 2. BẢNG MÀU THƯƠNG HIỆU (BRANDING)
# ============================================================
COLOR_PRIMARY = "#043463"   # Xanh đậm chủ đạo (theo logo)
COLOR_ACCENT = "#FFD700"    # Vàng nhấn (accent / touch-up)
COLOR_BG = "#F5F6F8"        # Xám nhẹ - nền
COLOR_WHITE = "#FFFFFF"
COLOR_BLACK = "#1A1A1A"
COLOR_SUCCESS = "#1E8E3E"
COLOR_ERROR = "#D93025"

LOGO_URL = "https://taladthaigroup.com/wp-content/uploads/2025/05/logo_talad.png"
APP_TITLE = "KPI VALIDATOR WORKSPACE"

# ============================================================
# 3. DANH SÁCH CÁC CHỈ SỐ KPI - GẮN VỚI BỘ PHẬN SỞ HỮU
# ============================================================
# key: mã nội bộ dùng trong toàn bộ code
# label: tên hiển thị trên UI (và cũng là tiêu đề cột trong file Template Excel
#        -> dùng để auto-match khi người dùng upload file)
# dept: mã bộ phận sở hữu / có thẩm quyền nhập chỉ số này
# value_type: "number" (số VND, 2 số thập phân) hoặc "percent" (%, 2 số thập phân)
KPI_FIELDS = {
    "doanh_thu": {
        "label": "Doanh thu (PKT)",
        "dept": "PKT",
        "value_type": "number",
        "unit": "VND",
        "target_col": "D",  # cột ghi vào sheet "Thực tế"
    },
    "qa_audit": {
        "label": "Điểm QA Audit (PQA)",
        "dept": "PQA",
        "value_type": "percent",
        "unit": "%",
        "target_col": "E",
    },
    "cogs": {
        "label": "COGS (PKT)",
        "dept": "PKT",
        "value_type": "number",
        "unit": "VND",
        "target_col": "F",
    },
    "col_pns": {
        "label": "COL (PNS)",
        "dept": "PNS",
        "value_type": "percent",
        "unit": "%",
        "target_col": "G",
    },
    "compliant_rate": {
        "label": "Compliant rate (MKT)",
        "dept": "MKT",
        "value_type": "percent",
        "unit": "%",
        "target_col": "H",
    },
    "ebitda": {
        "label": "EBITDA (PKT)",
        "dept": "PKT",
        "value_type": "number",
        "unit": "VND",
        "target_col": "I",
    },
}

# Thứ tự ĐẦY ĐỦ các cột khi ghi 1 dòng vào sheet "Thực tế":
# A: Mã cửa hàng | B: Tháng | C: Năm | D..I: 6 chỉ số KPI (theo KPI_FIELDS)
# J: Mã nhân viên | K: Thời gian ghi nhận
WRITE_ROW_ORDER = [
    "doanh_thu",     # D
    "qa_audit",      # E
    "cogs",          # F
    "col_pns",       # G
    "compliant_rate",# H
    "ebitda",        # I
]

# Danh sách các bộ phận hợp lệ (dùng để validate Mã bộ phận tra cứu được)
VALID_DEPARTMENTS = ["PKT", "PQA", "PNS", "MKT"]

# Tháng hiển thị dạng dropdown
MONTHS = list(range(1, 13))

# ============================================================
# 4. CẤU HÌNH GOOGLE APPS SCRIPT BACKEND
# ============================================================
# Thay cho Service Account + gspread. App gọi tới 1 Web App Apps Script
# (chạy dưới danh tính tài khoản nội bộ công ty) để đọc/ghi Google Sheets.
#
# KHUYẾN NGHỊ: KHÔNG điền giá trị thật vào 2 dòng dưới đây / KHÔNG commit lên
# GitHub. Thay vào đó cấu hình qua Streamlit Secrets:
#   st.secrets["apps_script_url"]
#   st.secrets["apps_script_api_key"]
# 2 dòng dưới chỉ dùng làm fallback khi chạy local nhanh, không khuyến khích
# giữ giá trị thật ở đây nếu repo là public.
APPS_SCRIPT_URL = ""       # dạng: https://script.google.com/macros/s/XXXXXXXX/exec
APPS_SCRIPT_API_KEY = ""   # phải khớp đúng CONFIG.API_KEY trong apps_script/Code.gs
