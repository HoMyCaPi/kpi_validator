# -*- coding: utf-8 -*-
"""
sheets_service.py
------------------
Module duy nhất chịu trách nhiệm giao tiếp với dữ liệu Google Sheets.

PHIÊN BẢN NÀY dùng Google Apps Script Web App làm backend (thay cho Service
Account + gspread), vì Apps Script chạy dưới danh tính TÀI KHOẢN NỘI BỘ công
ty (Execute as: Me) nên không bị chính sách "chặn chia sẻ ra ngoài tổ chức"
của Google Workspace áp dụng cho Service Account.

app.py KHÔNG gọi trực tiếp `requests` mà chỉ gọi các hàm public bên dưới,
giữ nguyên chữ ký hàm giống bản gspread trước đó -> không cần sửa app.py.

Xem README.md mục "Cấu hình Google Apps Script Backend" để biết cách deploy
Code.gs (trong thư mục apps_script/) và lấy URL Web App.
"""

from __future__ import annotations
import datetime
from typing import Optional

import requests
import streamlit as st

import config


# ============================================================
# 1. LẤY CẤU HÌNH ENDPOINT (URL Web App + API Key)
# ============================================================
def _get_endpoint_config() -> tuple[str, str]:
    """
    Ưu tiên lấy từ st.secrets (khuyến nghị khi deploy Streamlit Cloud):
        st.secrets["apps_script_url"]
        st.secrets["apps_script_api_key"]
    Fallback về config.APPS_SCRIPT_URL / config.APPS_SCRIPT_API_KEY (dùng khi
    chạy local và không muốn tạo secrets.toml).
    """
    url = None
    api_key = None
    try:
        url = st.secrets.get("apps_script_url")
        api_key = st.secrets.get("apps_script_api_key")
    except Exception:
        pass  # st.secrets có thể chưa được cấu hình

    url = url or getattr(config, "APPS_SCRIPT_URL", "")
    api_key = api_key or getattr(config, "APPS_SCRIPT_API_KEY", "")

    if not url or not api_key:
        raise RuntimeError(
            "Chưa cấu hình APPS_SCRIPT_URL / APPS_SCRIPT_API_KEY.\n"
            "Vui lòng cấu hình st.secrets['apps_script_url'] và "
            "st.secrets['apps_script_api_key'] trên Streamlit Cloud, "
            "hoặc điền tạm vào config.py khi chạy local. "
            "Xem hướng dẫn trong README.md."
        )
    return url, api_key


def _call_apps_script(action: str, payload: Optional[dict] = None, timeout: int = 60) -> dict:
    """
    Gọi 1 action tới Apps Script Web App, trả về phần `data` trong response JSON.

    Apps Script đôi khi phản hồi chậm bất thường ở lần gọi đầu tiên sau một
    thời gian không hoạt động ("cold start"). Để giảm lỗi gián đoạn cho người
    dùng, hàm này tự động thử lại 1 lần nếu lần gọi đầu bị timeout.
    """
    url, api_key = _get_endpoint_config()
    body = {"action": action, "api_key": api_key}
    if payload:
        body.update(payload)

    last_exc = None
    for attempt in range(2):  # thử tối đa 2 lần: 1 lần chính + 1 lần retry
        try:
            resp = requests.post(url, json=body, timeout=timeout)
            resp.raise_for_status()
            break
        except requests.Timeout as exc:
            last_exc = exc
            continue  # thử lại lần nữa (nếu còn lượt)
        except requests.RequestException as exc:
            raise RuntimeError(f"Không gọi được Apps Script Web App: {exc}") from exc
    else:
        raise RuntimeError(
            f"Không gọi được Apps Script Web App sau 2 lần thử (timeout={timeout}s): {last_exc}"
        )

    try:
        data = resp.json()
    except ValueError as exc:
        raise RuntimeError(
            "Apps Script trả về dữ liệu không phải JSON hợp lệ. "
            "Kiểm tra lại URL deploy và đảm bảo 'Who has access' = Anyone."
        ) from exc

    if not data.get("ok"):
        raise RuntimeError(f"Apps Script báo lỗi: {data.get('error')}")
    return data.get("data")


# ============================================================
# 2. VIEW 1 - TRA CỨU MÃ BỘ PHẬN THEO MÃ NHÂN VIÊN
# ============================================================
def lookup_department_by_employee(ma_nv: str) -> Optional[str]:
    """
    Tra cứu 'Mã bộ phận' dựa trên 'Mã nhân viên' qua Apps Script (action=lookup_department).
    Trả về Mã bộ phận (str) nếu tìm thấy, None nếu không tìm thấy.
    """
    ma_nv = (ma_nv or "").strip()
    if not ma_nv:
        return None

    result = _call_apps_script("lookup_department", {"ma_nv": ma_nv})
    if result and result.get("found"):
        return result.get("department")
    return None


# ============================================================
# 3. VIEW 2 - DANH SÁCH NHÀ HÀNG
# ============================================================
@st.cache_data(ttl=300, show_spinner=False)
def load_restaurants() -> list[dict]:
    """Đọc danh sách nhà hàng qua Apps Script (action=list_restaurants)."""
    result = _call_apps_script("list_restaurants")
    return result or []


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
    Ghi (append) một dòng vào sheet "Thực tế" qua Apps Script (action=append_actual).
    Thứ tự cột: A Mã cửa hàng | B Tháng | C Năm | D..I 6 chỉ số KPI | J Mã NV | K Thời gian.
    """
    row = [ma_cua_hang, thang, nam]
    for field_key in config.WRITE_ROW_ORDER:
        v = values.get(field_key)
        row.append(v if v not in (None, "") else 0)

    timestamp = datetime.datetime.now().strftime("%H:%M:%S %d/%m/%Y")
    row.append(ma_nv)
    row.append(timestamp)

    _call_apps_script("append_actual", {"row": row})
