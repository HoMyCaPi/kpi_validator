# -*- coding: utf-8 -*-
"""
sheets_service.py
------------------
Module duy nhất chịu trách nhiệm giao tiếp với Google Sheets API.
Toàn bộ phần còn lại của ứng dụng (app.py) KHÔNG gọi trực tiếp gspread/google-auth
mà chỉ gọi các hàm public bên dưới -> dễ bảo trì, dễ test, dễ thay Provider sau này.

Xác thực: dùng Service Account (xem hướng dẫn chi tiết trong README.md).
Thư viện: gspread + google-auth.
"""

from __future__ import annotations
import datetime
from functools import lru_cache
from typing import Optional

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

import config

# Scope tối thiểu cần thiết: đọc & ghi Sheets + đọc metadata Drive (mở file theo ID)
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


# ============================================================
# 1. KHỞI TẠO CLIENT (Service Account)
# ============================================================
@st.cache_resource(show_spinner=False)
def get_client() -> gspread.Client:
    """
    Tạo gspread client dùng Service Account.

    Ứng dụng hỗ trợ 2 cách nạp credentials, ưu tiên theo thứ tự:
    1) st.secrets["gcp_service_account"]  (khuyến nghị khi deploy Streamlit Cloud)
    2) File JSON local: service_account.json (đặt cùng thư mục app.py, dùng khi chạy local)

    Xem README.md mục "Cấu hình Service Account" để biết cách tạo & lấy các giá trị này.
    """
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
            return gspread.authorize(creds)
    except Exception:
        # st.secrets có thể chưa được cấu hình -> fallback xuống file local
        pass

    try:
        creds = Credentials.from_service_account_file(
            "service_account.json", scopes=SCOPES
        )
        return gspread.authorize(creds)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Không tìm thấy thông tin xác thực Service Account.\n"
            "Vui lòng cấu hình st.secrets['gcp_service_account'] hoặc tạo file "
            "'service_account.json' cạnh app.py. Xem hướng dẫn trong README.md."
        ) from exc


def _open_worksheet_by_gid(spreadsheet_id: str, gid: int):
    """Mở đúng worksheet theo GID (không phụ thuộc tên tab, vì tên có thể đổi)."""
    client = get_client()
    sh = client.open_by_key(spreadsheet_id)
    return sh.get_worksheet_by_id(gid)


# ============================================================
# 2. VIEW 1 - TRA CỨU MÃ BỘ PHẬN THEO MÃ NHÂN VIÊN
# ============================================================
def lookup_department_by_employee(ma_nv: str) -> Optional[str]:
    """
    Tra cứu 'Mã bộ phận' (Cột F) dựa trên 'Mã nhân viên' (Cột B)
    trong Nguồn 2 (2026 - PNS Data share - Ngọc, gid=254853384).

    Trả về:
        - Mã bộ phận (str, đã upper + strip) nếu tìm thấy
        - None nếu không tìm thấy mã nhân viên
    """
    ma_nv = (ma_nv or "").strip()
    if not ma_nv:
        return None

    ws = _open_worksheet_by_gid(config.SPREADSHEET_PNS_ID, config.GID_PNS_DATA)
    col_b_values = ws.col_values(_col_letter_to_index(config.COL_PNS_MA_NV))
    col_f_values = ws.col_values(_col_letter_to_index(config.COL_PNS_MA_BO_PHAN))

    for idx, val in enumerate(col_b_values):
        if idx == 0:
            continue  # bỏ qua dòng tiêu đề
        if val.strip().upper() == ma_nv.upper():
            if idx < len(col_f_values):
                return col_f_values[idx].strip().upper()
            return None
    return None


# ============================================================
# 3. VIEW 2 - DANH SÁCH NHÀ HÀNG
# ============================================================
@st.cache_data(ttl=300, show_spinner=False)
def load_restaurants() -> list[dict]:
    """
    Đọc danh sách nhà hàng từ Nguồn Danh sách Nhà hàng (gid=0), bắt đầu từ hàng 2.
    Trả về list các dict: {"ma": ..., "tinh": ..., "dia_chi": ...}
    """
    ws = _open_worksheet_by_gid(config.SPREADSHEET_NHAHANG_ID, config.GID_NHAHANG)
    records = ws.get_all_values()  # list[list[str]], bao gồm cả hàng tiêu đề (row 1)

    result = []
    for row in records[1:]:  # bỏ qua hàng 1 (tiêu đề)
        if not row or not row[0].strip():
            continue
        ma = row[0].strip() if len(row) > 0 else ""
        tinh = row[1].strip() if len(row) > 1 else ""
        dia_chi = row[2].strip() if len(row) > 2 else ""
        result.append({"ma": ma, "tinh": tinh, "dia_chi": dia_chi})
    return result


# ============================================================
# 4. VIEW 4 - GHI DỮ LIỆU VÀO SHEET "THỰC TẾ"
# ============================================================
def append_actual_row(
    ma_cua_hang: str,
    thang: int,
    nam: int,
    values: dict,
    ma_nv: str,
) -> None:
    """
    Ghi (append) một dòng dữ liệu vào sheet "Thực tế" (Nguồn 1, gid=1945875318).

    Thứ tự cột:
      A: Mã cửa hàng | B: Tháng | C: Năm
      D: Doanh thu (PKT) | E: Điểm QA Audit (PQA) | F: COGS (PKT)
      G: COL (PNS) | H: Compliant rate (MKT) | I: EBITDA (PKT)
      J: Mã nhân viên | K: Thời gian ghi nhận

    `values` là dict {field_key: float|None} theo config.WRITE_ROW_ORDER.
    Trường None hoặc không thuộc thẩm quyền bộ phận -> ghi 0.
    """
    ws = _open_worksheet_by_gid(config.SPREADSHEET_KPI_ID, config.GID_THUCTE_SHEET)

    row = [ma_cua_hang, thang, nam]
    for field_key in config.WRITE_ROW_ORDER:
        v = values.get(field_key)
        row.append(v if v not in (None, "") else 0)

    timestamp = datetime.datetime.now().strftime("%H:%M:%S %d/%m/%Y")
    row.append(ma_nv)
    row.append(timestamp)

    ws.append_row(row, value_input_option="USER_ENTERED")


# ============================================================
# TIỆN ÍCH NỘI BỘ
# ============================================================
def _col_letter_to_index(letter: str) -> int:
    """Chuyển 'A' -> 1, 'B' -> 2, ... 'F' -> 6 (dùng cho ws.col_values)."""
    letter = letter.strip().upper()
    idx = 0
    for ch in letter:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx
