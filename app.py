# -*- coding: utf-8 -*-
"""
app.py
------
KPI Validator Workspace - Ứng dụng thu thập & xác thực chỉ số KPI hàng tháng
theo phân quyền bộ phận, ghi trực tiếp vào Google Sheets "Thực tế".

Chạy ứng dụng:
    streamlit run app.py

Xem README.md để biết cách cấu hình Google Apps Script Backend trước khi chạy.
"""

import datetime

import streamlit as st

import config
import utils
from sheets_service import (
    append_actual_row,
    load_restaurants,
    lookup_department_by_employee,
)

# ============================================================
# CẤU HÌNH TRANG & CSS THƯƠNG HIỆU
# ============================================================
st.set_page_config(
    page_title=config.APP_TITLE,
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed",
)

CUSTOM_CSS = f"""
<style>
    .stApp {{
        background-color: {config.COLOR_BG};
    }}
    /* Header thương hiệu */
    .kpi-header {{
        display: flex;
        align-items: center;
        gap: 16px;
        background-color: {config.COLOR_PRIMARY};
        padding: 18px 28px;
        border-radius: 12px;
        margin-bottom: 28px;
        box-shadow: 0 2px 10px rgba(4,52,99,0.25);
    }}
    .kpi-header img {{
        height: 42px;
        background: white;
        padding: 4px 8px;
        border-radius: 6px;
    }}
    .kpi-header h1 {{
        color: {config.COLOR_WHITE};
        font-size: 22px;
        margin: 0;
        font-weight: 700;
    }}
    .kpi-header span {{
        color: {config.COLOR_ACCENT};
        font-size: 13px;
        font-weight: 600;
    }}
    /* Card chứa nội dung từng bước */
    .kpi-card {{
        background-color: {config.COLOR_WHITE};
        border-radius: 14px;
        padding: 28px 32px;
        box-shadow: 0 1px 6px rgba(0,0,0,0.08);
        border-top: 4px solid {config.COLOR_ACCENT};
        margin-bottom: 20px;
    }}
    /* Step indicator */
    .step-bar {{
        display: flex;
        justify-content: space-between;
        margin-bottom: 22px;
    }}
    .step-item {{
        flex: 1;
        text-align: center;
        padding: 8px 4px;
        font-size: 12px;
        font-weight: 700;
        color: #9AA5B1;
        border-bottom: 4px solid #E1E5EA;
    }}
    .step-item.active {{
        color: {config.COLOR_PRIMARY};
        border-bottom: 4px solid {config.COLOR_ACCENT};
    }}
    .step-item.done {{
        color: {config.COLOR_PRIMARY};
        border-bottom: 4px solid {config.COLOR_PRIMARY};
    }}
    div.stButton > button {{
        background-color: {config.COLOR_PRIMARY};
        color: white;
        border-radius: 8px;
        font-weight: 600;
        border: none;
        padding: 10px 22px;
    }}
    div.stButton > button:hover {{
        background-color: #06508f;
        color: {config.COLOR_ACCENT};
    }}
    .info-pill {{
        display: inline-block;
        background: #EAF1FA;
        color: {config.COLOR_PRIMARY};
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
        margin-right: 8px;
    }}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================
st.markdown(
    f"""
    <div class="kpi-header">
        <img src="{config.LOGO_URL}" />
        <div>
            <h1>{config.APP_TITLE}</h1>
            <span>Hệ thống thu thập & xác thực chỉ số KPI hàng tháng</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# KHỞI TẠO SESSION STATE
# ============================================================
if "step" not in st.session_state:
    st.session_state.step = 1
if "ma_nv" not in st.session_state:
    st.session_state.ma_nv = ""
if "ma_bo_phan" not in st.session_state:
    st.session_state.ma_bo_phan = None
if "restaurant" not in st.session_state:
    st.session_state.restaurant = None
if "thang" not in st.session_state:
    st.session_state.thang, st.session_state.nam = utils.default_month_year()
if "kpi_values" not in st.session_state:
    st.session_state.kpi_values = {}
if "submitted" not in st.session_state:
    st.session_state.submitted = False

STEP_LABELS = ["1. Xác thực NV", "2. Chọn nhà hàng", "3. Nhập KPI", "4. Xác nhận & Gửi"]


def render_step_bar():
    cols_html = ""
    for i, label in enumerate(STEP_LABELS, start=1):
        css_class = "active" if i == st.session_state.step else ("done" if i < st.session_state.step else "")
        cols_html += f'<div class="step-item {css_class}">{label}</div>'
    st.markdown(f'<div class="step-bar">{cols_html}</div>', unsafe_allow_html=True)


render_step_bar()

# ============================================================
# VIEW 1: XÁC THỰC NHÂN VIÊN
# ============================================================
if st.session_state.step == 1:
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.subheader("🔐 Xác thực Nhân viên")
    st.write("Vui lòng nhập Mã nhân viên để hệ thống tra cứu bộ phận và phân quyền nhập liệu.")

    ma_nv_input = st.text_input(
        "Mã nhân viên", value=st.session_state.ma_nv, placeholder="Ví dụ: BN.DNG"
    )

    if st.button("Load / Tiếp tục", type="primary"):
        if not ma_nv_input.strip():
            st.error("Vui lòng nhập Mã nhân viên.")
        else:
            with st.spinner("Đang tra cứu thông tin nhân viên..."):
                try:
                    dept = lookup_department_by_employee(ma_nv_input.strip())
                except Exception as exc:
                    st.error("Lỗi kết nối Google Sheets — chi tiết kỹ thuật bên dưới:")
                    st.exception(exc)
                    dept = None

            if dept is None:
                st.error(
                    "❌ Không tìm thấy Mã nhân viên trong hệ thống. "
                    "Vui lòng kiểm tra lại hoặc liên hệ bộ phận Nhân sự."
                )
            elif dept not in config.VALID_DEPARTMENTS:
                st.error(
                    f"❌ Mã bộ phận '{dept}' tra cứu được không nằm trong danh sách hợp lệ "
                    f"({', '.join(config.VALID_DEPARTMENTS)}). Vui lòng liên hệ IT."
                )
            else:
                st.session_state.ma_nv = ma_nv_input.strip()
                st.session_state.ma_bo_phan = dept
                st.session_state.step = 2
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# VIEW 2: CHỌN NHÀ HÀNG
# ============================================================
elif st.session_state.step == 2:
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.subheader("🏬 Chọn Nhà hàng")
    st.markdown(
        f'<span class="info-pill">Mã NV: {st.session_state.ma_nv}</span>'
        f'<span class="info-pill">Bộ phận: {st.session_state.ma_bo_phan}</span>',
        unsafe_allow_html=True,
    )
    st.write("")

    with st.spinner("Đang tải danh sách nhà hàng..."):
        try:
            restaurants = load_restaurants()
        except Exception as exc:
            st.error(f"Lỗi tải danh sách nhà hàng: {exc}")
            restaurants = []

    if restaurants:
        options = [r["ma"] for r in restaurants]
        default_idx = 0
        if st.session_state.restaurant:
            try:
                default_idx = options.index(st.session_state.restaurant["ma"])
            except ValueError:
                default_idx = 0

        selected_ma = st.selectbox(
            "Tìm / chọn Mã nhà hàng",
            options=options,
            index=default_idx,
            help="Gõ để tìm kiếm nhanh theo mã nhà hàng",
        )
        selected = next((r for r in restaurants if r["ma"] == selected_ma), None)

        if selected:
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("Tỉnh / Thành phố", value=selected["tinh"], disabled=True)
            with col2:
                st.text_input("Địa chỉ chi tiết", value=selected["dia_chi"], disabled=True)

        col_back, col_next = st.columns([1, 1])
        with col_back:
            if st.button("⬅ Quay lại"):
                st.session_state.step = 1
                st.rerun()
        with col_next:
            if st.button("Tiếp tục ➡", type="primary"):
                st.session_state.restaurant = selected
                st.session_state.step = 3
                st.rerun()
    else:
        st.warning("Không có dữ liệu nhà hàng hoặc không thể kết nối tới Google Sheets.")
        if st.button("⬅ Quay lại"):
            st.session_state.step = 1
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# VIEW 3: NHẬP DỮ LIỆU KPI
# ============================================================
elif st.session_state.step == 3:
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.subheader("📈 Nhập dữ liệu KPI")
    st.markdown(
        f'<span class="info-pill">Mã NV: {st.session_state.ma_nv}</span>'
        f'<span class="info-pill">Bộ phận: {st.session_state.ma_bo_phan}</span>'
        f'<span class="info-pill">Nhà hàng: {st.session_state.restaurant["ma"]}</span>',
        unsafe_allow_html=True,
    )
    st.write("")

    col_thang, col_nam = st.columns(2)
    with col_thang:
        thang = st.selectbox(
            "Tháng", options=config.MONTHS, index=config.MONTHS.index(st.session_state.thang)
        )
    with col_nam:
        nam = st.number_input(
            "Năm", min_value=2020, max_value=2100, value=st.session_state.nam, step=1
        )

    dept = st.session_state.ma_bo_phan
    allowed_fields = [k for k, v in config.KPI_FIELDS.items() if v["dept"] == dept]

    st.markdown("##### Các chỉ số KPI thuộc thẩm quyền bộ phận **%s**" % dept)

    input_mode = st.radio(
        "Phương thức nhập dữ liệu",
        options=["Nhập trực tiếp", "Upload file Excel/CSV theo mẫu"],
        horizontal=True,
    )

    current_values = dict(st.session_state.kpi_values)

    if input_mode == "Nhập trực tiếp":
        for key in allowed_fields:
            meta = config.KPI_FIELDS[key]
            label = f'{meta["label"]}  ({meta["unit"]})'
            default_val = current_values.get(key, 0.0)
            val = st.number_input(
                label, value=float(default_val), step=0.01, format="%.2f", key=f"input_{key}"
            )
            current_values[key] = round(val, 2)

    else:
        st.markdown(
            f"[📥 Tải file Template mẫu]({config.TEMPLATE_DOWNLOAD_URL})  \n"
            "Điền dữ liệu vào file, sau đó upload lại bên dưới. "
            "Hệ thống sẽ tự động đọc & điền vào các chỉ số thuộc thẩm quyền bộ phận của bạn."
        )
        uploaded_file = st.file_uploader(
            "Upload file Excel (.xlsx) hoặc CSV", type=["xlsx", "xls", "csv"]
        )
        if uploaded_file is not None:
            try:
                extracted = utils.parse_template_file(uploaded_file, allowed_fields)
                current_values.update(extracted)
                st.success("✅ Đã đọc và điền dữ liệu từ file thành công. Vui lòng kiểm tra lại bên dưới.")
            except ValueError as exc:
                st.error(str(exc))

        # Hiển thị các field (cho phép chỉnh sửa sau khi đọc từ file)
        for key in allowed_fields:
            meta = config.KPI_FIELDS[key]
            label = f'{meta["label"]}  ({meta["unit"]})'
            default_val = current_values.get(key, 0.0)
            val = st.number_input(
                label, value=float(default_val), step=0.01, format="%.2f", key=f"upload_input_{key}"
            )
            current_values[key] = round(val, 2)

    col_back, col_next = st.columns([1, 1])
    with col_back:
        if st.button("⬅ Quay lại"):
            st.session_state.step = 2
            st.rerun()
    with col_next:
        if st.button("Tiếp tục ➡", type="primary"):
            st.session_state.thang = thang
            st.session_state.nam = int(nam)
            st.session_state.kpi_values = current_values
            st.session_state.step = 4
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# VIEW 4: XÁC NHẬN & SUBMIT
# ============================================================
elif st.session_state.step == 4:
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.subheader("✅ Xác nhận & Gửi dữ liệu")

    st.markdown("**Thông tin chung**")
    st.table(
        {
            "Mã nhân viên": [st.session_state.ma_nv],
            "Bộ phận": [st.session_state.ma_bo_phan],
            "Mã nhà hàng": [st.session_state.restaurant["ma"]],
            "Tỉnh/Thành phố": [st.session_state.restaurant["tinh"]],
            "Tháng/Năm": [f"{st.session_state.thang:02d}/{st.session_state.nam}"],
        }
    )

    st.markdown("**Chỉ số KPI sẽ được ghi nhận**")
    display_rows = []
    for key in config.WRITE_ROW_ORDER:
        meta = config.KPI_FIELDS[key]
        val = st.session_state.kpi_values.get(key)
        owned = meta["dept"] == st.session_state.ma_bo_phan
        display_rows.append(
            {
                "Chỉ số": meta["label"],
                "Bộ phận sở hữu": meta["dept"],
                "Giá trị": utils.format_value_display(val, meta["value_type"]) if owned else "— (ngoài thẩm quyền, ghi 0)",
            }
        )
    st.table(display_rows)

    st.info(
        "Lưu ý: các chỉ số **không** thuộc thẩm quyền bộ phận của bạn sẽ được ghi giá trị **0** "
        "vào sheet Thực tế, và sẽ do bộ phận tương ứng cập nhật ở lượt nhập của họ."
    )

    col_back, col_submit = st.columns([1, 1])
    with col_back:
        if st.button("⬅ Quay lại chỉnh sửa"):
            st.session_state.step = 3
            st.rerun()
    with col_submit:
        if st.button("🚀 Submit / Gửi dữ liệu", type="primary"):
            try:
                with st.spinner("Đang ghi dữ liệu vào Google Sheets..."):
                    append_actual_row(
                        ma_cua_hang=st.session_state.restaurant["ma"],
                        thang=st.session_state.thang,
                        nam=st.session_state.nam,
                        values=st.session_state.kpi_values,
                        ma_nv=st.session_state.ma_nv,
                    )
                st.session_state.submitted = True
                st.session_state.step = 5
                st.rerun()
            except Exception as exc:
                st.error(f"❌ Gửi dữ liệu thất bại: {exc}")

    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# VIEW 5 (Kết quả): THÀNH CÔNG
# ============================================================
elif st.session_state.step == 5:
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.success("🎉 Dữ liệu đã được ghi nhận thành công vào sheet **Thực tế**!")
    st.write(
        f"Nhà hàng **{st.session_state.restaurant['ma']}** — "
        f"Tháng {st.session_state.thang:02d}/{st.session_state.nam} "
        f"— Người nhập: {st.session_state.ma_nv} ({st.session_state.ma_bo_phan})"
    )

    if st.button("➕ Nhập cho nhà hàng / tháng khác"):
        st.session_state.step = 2
        st.session_state.kpi_values = {}
        st.session_state.thang, st.session_state.nam = utils.default_month_year()
        st.rerun()

    if st.button("🔄 Bắt đầu lại từ đầu"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# FOOTER
# ============================================================
st.markdown(
    f"""
    <div style="text-align:center; color:#9AA5B1; font-size:12px; margin-top:30px;">
        © {datetime.date.today().year} Talad Thai Group — KPI Validator Workspace
    </div>
    """,
    unsafe_allow_html=True,
)
