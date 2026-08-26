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
import uuid
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


def _call_apps_script(action: str, payload: Optional[dict] = None, timeout: int = 60, max_attempts: int = 3) -> dict:
    """
    Gọi 1 action tới Apps Script Web App, trả về phần `data` trong response JSON.

    Apps Script đôi khi phản hồi chậm hoặc lỗi tạm thời (cold-start, hoặc lỗi
    redirect nội bộ trả về 404/5xx) ở lần gọi đầu. Để giảm lỗi gián đoạn cho
    người dùng, hàm này tự động thử lại tối đa `max_attempts` lần cho MỌI lỗi
    liên quan tới request (timeout, lỗi kết nối, lỗi HTTP), không chỉ timeout.
    """
    url, api_key = _get_endpoint_config()
    body = {"action": action, "api_key": api_key}
    if payload:
        body.update(payload)

    last_exc = None
    for attempt in range(max_attempts):
        try:
            resp = requests.post(url, json=body, timeout=timeout)
            resp.raise_for_status()
            break
        except requests.RequestException as exc:
            last_exc = exc
            continue
    else:
        raise RuntimeError(
            f"Không gọi được Apps Script Web App sau {max_attempts} lần thử: {last_exc}"
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
@st.cache_data(ttl=300, show_spinner=False)
def _load_employee_directory() -> dict:
    """
    Tải TOÀN BỘ danh sách Mã NV -> Mã bộ phận 1 lần (action=list_employees),
    cache 5 phút và DÙNG CHUNG cho mọi người dùng trong thời gian cache còn hiệu
    lực. Nhờ vậy, chỉ lần tra cứu ĐẦU TIÊN sau khi cache hết hạn mới phải chờ
    Apps Script phản hồi (có thể chậm do cold-start); các lần tra cứu tiếp theo
    -- kể cả của người dùng khác -- được tra cứu cục bộ, gần như tức thời.
    """
    result = _call_apps_script("list_employees")
    directory = {}
    for item in (result or []):
        ma = str(item.get("ma_nv", "")).strip().upper()
        if ma:
            directory[ma] = str(item.get("department", "")).strip().upper()
    return directory


def lookup_department_by_employee(ma_nv: str) -> Optional[str]:
    """
    Tra cứu 'Mã bộ phận' dựa trên 'Mã nhân viên', dùng danh sách đã cache.
    Trả về Mã bộ phận (str) nếu tìm thấy, None nếu không tìm thấy.
    """
    ma_nv = (ma_nv or "").strip().upper()
    if not ma_nv:
        return None
    directory = _load_employee_directory()
    return directory.get(ma_nv)


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

    Lưu ý về các trường dạng % (Điểm QA Audit, COL, Compliant rate):
    Người dùng nhập trực tiếp theo thói quen tự nhiên (vd nhập 70 nghĩa là 70%,
    nhập 70.5 nghĩa là 70.5%). Nhưng cột tương ứng trên Google Sheet có định dạng
    Phần trăm (%), nên giá trị LƯU TRỮ thực tế phải là số thập phân (70 -> 0.70,
    70.5 -> 0.705) thì Sheet mới hiển thị đúng "70.00%" / "70.50%". Vì vậy chỉ
    chia 100 ở bước ghi xuống Sheet này, KHÔNG đổi cách người dùng nhập liệu hay
    cách hiển thị trong giao diện.

    CHỐNG TRÙNG (idempotency): mỗi lần gọi được gắn kèm 1 `request_id` ngẫu
    nhiên duy nhất. `_call_apps_script` giữ NGUYÊN request_id này xuyên suốt
    các lần retry của CÙNG một lệnh gọi (vì `body` chỉ tạo 1 lần rồi tái sử
    dụng cho mọi lần thử). Phía Apps Script (Code.gs) dùng CacheService để
    nhận diện: nếu request_id đã được xử lý (đã ghi) ở lần thử trước đó, lần
    gọi lại sẽ tự động BỎ QUA thay vì ghi thêm 1 dòng nữa. Nhờ vậy, việc TỰ
    ĐỘNG RETRY khi gặp lỗi tạm thời (vd lỗi redirect nội bộ của Google) là AN
    TOÀN, không tạo dữ liệu trùng lặp.
    """
    row = [ma_cua_hang, thang, nam]
    for field_key in config.WRITE_ROW_ORDER:
        v = values.get(field_key)
        if v in (None, ""):
            row.append(0)
            continue
        meta = config.KPI_FIELDS[field_key]
        if meta["value_type"] == "percent":
            v = round(float(v) / 100, 4)
        row.append(v)

    timestamp = datetime.datetime.now().strftime("%H:%M:%S %d/%m/%Y")
    row.append(ma_nv)
    row.append(timestamp)

    request_id = str(uuid.uuid4())
    _call_apps_script("append_actual", {"row": row, "request_id": request_id}, max_attempts=3)
