# -*- coding: utf-8 -*-
"""
utils.py
--------
Các hàm tiện ích dùng chung:
- Tính Tháng/Năm mặc định (Tháng liền trước thời điểm hiện tại)
- Đọc file Excel/CSV do người dùng upload (Cách 2) và map vào các field KPI
  đúng thẩm quyền bộ phận, dựa theo tên cột (header) trùng với label trong config.KPI_FIELDS
"""

from __future__ import annotations
import datetime
import io
from typing import Optional

import pandas as pd

import config


def default_month_year(today: Optional[datetime.date] = None) -> tuple[int, int]:
    """
    Trả về (tháng, năm) mặc định = tháng liền TRƯỚC thời điểm hiện tại.
    Ví dụ: hôm nay 25/08/2026 -> trả về (7, 2026).
    Nếu hôm nay là tháng 1 -> trả về (12, năm - 1).
    """
    today = today or datetime.date.today()
    if today.month == 1:
        return 12, today.year - 1
    return today.month - 1, today.year


def parse_template_file(uploaded_file, allowed_field_keys: list[str]) -> tuple[dict, Optional[str]]:
    """
    Đọc file Excel (.xlsx) hoặc CSV do người dùng upload theo mẫu Template.
    Chỉ lấy giá trị của các field nằm trong `allowed_field_keys`
    (tức là các chỉ số thuộc thẩm quyền bộ phận của nhân viên đang đăng nhập).

    Cách match: so khớp TÊN CỘT (header) trong file với `label` trong config.KPI_FIELDS.
    Ví dụ header "Doanh thu (PKT)" -> field_key "doanh_thu".

    Trả về: (dict {field_key: float} các chỉ số đọc được,
             Mã nhà hàng tìm thấy ở CỘT ĐẦU TIÊN của file nếu có -- dùng để đối
             chiếu với nhà hàng đã chọn ở View 2 -- hoặc None nếu cột trống).
    Ném ValueError nếu không đọc được file hoặc file không có dữ liệu.
    """
    filename = uploaded_file.name.lower()
    raw_bytes = uploaded_file.read()

    if filename.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(raw_bytes))
    elif filename.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(raw_bytes))
    else:
        raise ValueError("Định dạng file không hỗ trợ. Vui lòng dùng .xlsx, .xls hoặc .csv")

    if df.empty:
        raise ValueError("File không có dữ liệu.")

    # Chỉ lấy dòng dữ liệu đầu tiên (mỗi lần nhập tương ứng 1 nhà hàng / 1 tháng)
    first_row = df.iloc[0]

    # Mã nhà hàng (nếu file có cột đầu tiên chứa mã nhà hàng, theo đúng template)
    ma_nha_hang_in_file: Optional[str] = None
    if len(df.columns) > 0:
        raw_ma = first_row[df.columns[0]]
        if not pd.isna(raw_ma):
            candidate = str(raw_ma).strip()
            if candidate:
                ma_nha_hang_in_file = candidate

    # Xây map: label hiển thị -> field_key
    label_to_key = {meta["label"]: key for key, meta in config.KPI_FIELDS.items()}

    extracted: dict[str, float] = {}
    for col_name in df.columns:
        col_name_clean = str(col_name).strip()
        if col_name_clean in label_to_key:
            field_key = label_to_key[col_name_clean]
            if field_key not in allowed_field_keys:
                continue  # bỏ qua field không thuộc thẩm quyền bộ phận
            raw_val = first_row[col_name]
            if pd.isna(raw_val):
                continue
            try:
                extracted[field_key] = round(float(raw_val), 2)
            except (ValueError, TypeError):
                continue

    if not extracted:
        raise ValueError(
            "Không tìm thấy cột dữ liệu hợp lệ nào khớp với chỉ số KPI thuộc thẩm quyền "
            "bộ phận của bạn trong file đã upload. Vui lòng kiểm tra lại tiêu đề cột."
        )
    return extracted, ma_nha_hang_in_file


def format_value_display(value: float, value_type: str) -> str:
    """Format giá trị hiển thị theo loại: number (VND) hoặc percent (%)."""
    if value is None:
        return "-"
    if value_type == "percent":
        return f"{value:,.2f} %"
    return f"{value:,.2f} VND"


def parse_bulk_template_file(uploaded_file, allowed_field_keys: list[str]) -> list[dict]:
    """
    Đọc file Excel/CSV Bulk Import — MỖI DÒNG là 1 nhà hàng. Cột đầu tiên (A)
    được coi là Mã nhà hàng, các cột còn lại match theo `label` trong
    config.KPI_FIELDS giống parse_template_file, nhưng đọc TẤT CẢ các dòng
    thay vì chỉ dòng đầu tiên.

    Trả về: list các dict {"ma_nha_hang": str, "values": {field_key: float}}.
    Bỏ qua các dòng không có Mã nhà hàng. Ném ValueError nếu không đọc được
    file hoặc không có dòng dữ liệu hợp lệ nào.
    """
    filename = uploaded_file.name.lower()
    raw_bytes = uploaded_file.read()

    if filename.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(raw_bytes))
    elif filename.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(raw_bytes))
    else:
        raise ValueError("Định dạng file không hỗ trợ. Vui lòng dùng .xlsx, .xls hoặc .csv")

    if df.empty:
        raise ValueError("File không có dữ liệu.")

    ma_col = df.columns[0]  # Cột A = Mã nhà hàng theo đúng template mẫu
    label_to_key = {meta["label"]: key for key, meta in config.KPI_FIELDS.items()}

    rows: list[dict] = []
    for _, r in df.iterrows():
        raw_ma = r[ma_col]
        ma_nha_hang = "" if pd.isna(raw_ma) else str(raw_ma).strip()
        if not ma_nha_hang:
            continue  # bỏ qua dòng trống Mã nhà hàng

        values: dict[str, float] = {}
        for col_name in df.columns:
            col_clean = str(col_name).strip()
            if col_clean not in label_to_key:
                continue
            field_key = label_to_key[col_clean]
            if field_key not in allowed_field_keys:
                continue  # bỏ qua chỉ số ngoài thẩm quyền bộ phận
            raw_val = r[col_name]
            if pd.isna(raw_val):
                continue
            try:
                values[field_key] = round(float(raw_val), 2)
            except (ValueError, TypeError):
                continue

        rows.append({"ma_nha_hang": ma_nha_hang, "values": values})

    if not rows:
        raise ValueError(
            "Không đọc được dòng dữ liệu hợp lệ nào. Vui lòng kiểm tra cột A "
            "(Mã nhà hàng) đã được điền đầy đủ chưa."
        )
    return rows
