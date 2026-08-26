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
# CẤU HÌNH TRANG
# ============================================================
st.set_page_config(
    page_title=config.APP_TITLE,
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ============================================================
# TẢI FONT INTER (dùng <link> thay vì chỉ @import cho chắc chắn)
# ============================================================
st.markdown(
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">',
    unsafe_allow_html=True,
)

# ============================================================
# CSS THƯƠNG HIỆU
# ============================================================
CUSTOM_CSS = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* Ép font Inter lên toàn bộ chữ, nhưng LOẠI TRỪ icon nội bộ của Streamlit
       (icon dùng font ligature riêng - vd chữ "upload" render thành hình icon;
       ép font lên icon sẽ làm lộ chữ thật thay vì hình, gây lỗi hiển thị). */
    html, body, .stApp,
    .stApp p, .stApp span:not([data-testid="stIconMaterial"]), .stApp label,
    .stApp div:not([data-testid="stIconMaterial"]), .stApp h1, .stApp h2, .stApp h3,
    .stApp h4, .stApp h5, .stApp h6, .stApp button, .stApp input, .stApp li, .stApp a,
    .stApp table, .stApp td, .stApp th {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    }}

    .stApp {{
        background-color: {config.COLOR_BG};
    }}

    /* ===================== HEADER THƯƠNG HIỆU (logo trên, chữ dưới, căn giữa) ===================== */
    .kpi-header {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 16px;
        background-color: {config.COLOR_PRIMARY};
        padding: 30px 36px;
        border-radius: 14px;
        margin-bottom: 32px;
        box-shadow: 0 2px 10px rgba(4,52,99,0.25);
    }}
    .kpi-header img {{
        height: 70px;
        background: white;
        padding: 14px 20px;
        border-radius: 8px;
    }}
    .kpi-header-text {{
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
        text-align: center;
    }}
    /* ---- DÒNG TIÊU ĐỀ LỚN "KPI VALIDATOR WORKSPACE" - chỉnh size ở ĐÂY ---- */
    .kpi-title {{
        color: {config.COLOR_ACCENT};
        font-size: 32px;
        margin: 0;
        font-weight: 500;
        letter-spacing: 0.5px;
        opacity: 0.9;
        /* Streamlit bản mới tự áp gradient/hiệu ứng "trong suốt" lên h1-h6
           (background-clip:text + -webkit-text-fill-color:transparent), khiến
           chữ hiển thị mờ/tối trên nền đậm thay vì đúng màu đã set ở trên.
           3 dòng dưới đây HUỶ hoàn toàn hiệu ứng đó, ép hiển thị đúng màu thật. */
        background: none !important;
        -webkit-background-clip: initial !important;
        background-clip: initial !important;
        -webkit-text-fill-color: {config.COLOR_ACCENT} !important;
    }}
    /* ---- DÒNG PHỤ NHỎ "Hệ thống thu thập..." - chỉnh size ở ĐÂY (RIÊNG, không liên quan dòng trên) ---- */
    .kpi-subtitle {{
        color: {config.COLOR_ACCENT};
        font-size: 12px;
        font-weight: 500;
        letter-spacing: 0.3px;
        opacity: 0.9;
        background: none !important;
        -webkit-background-clip: initial !important;
        background-clip: initial !important;
        -webkit-text-fill-color: {config.COLOR_ACCENT} !important;
    }}

    /* ===================== STEPPER (THANH TIẾN TRÌNH - vạch pill bo tròn, tách khỏi card) ===================== */
    /* Vạch pill được vẽ là 1 khối RIÊNG, nằm ngay dưới chữ theo dòng chảy tài
       liệu bình thường (không dùng position:absolute) -- đảm bảo luôn thẳng
       hàng giữa các bước, không phụ thuộc vào việc các cột có bị co giãn
       chiều cao khác nhau hay không. */
    .step-static-label {{
        text-align: center;
        padding: 4px 10px 0 10px;
        font-size: 16px;
        font-weight: 700;
        color: #6C757D;
    }}
    .step-static-label.active {{
        color: {config.COLOR_PRIMARY};
    }}
    .step-static-label.upcoming {{
        color: #6C757D;
    }}
    .step-pill {{
        height: 5px;
        border-radius: 999px;
        margin: 10px 14% 0 14%;
        background: #C9D0D8;
    }}
    .step-pill.active {{
        background: {config.COLOR_ACCENT};
    }}
    .step-pill.done {{
        background: {config.COLOR_PRIMARY};
    }}
    .step-pill.upcoming {{
        background: #C9D0D8;
    }}

    /* Nút bấm cho các bước ĐÃ HOÀN THÀNH -- style để trông giống label chữ
       (không phải hộp nút); vạch pill của bước "done" được vẽ RIÊNG ngay sau
       nút (xem render_step_bar), không dùng ::after, cùng lý do nêu trên. */
    div[data-testid="stVerticalBlock"]:has(> div.step-marker-done) {{
        margin-bottom: 4px;
    }}
    div[data-testid="stVerticalBlock"]:has(> div.step-marker-done) div.stButton > button {{
        background: transparent !important;
        border: none !important;
        border-radius: 6px !important;
        color: {config.COLOR_PRIMARY} !important;
        font-weight: 700 !important;
        font-size: 16px !important;
        padding: 4px 10px !important;
        width: 100% !important;
        box-shadow: none !important;
        transform: none !important;
    }}
    div[data-testid="stVerticalBlock"]:has(> div.step-marker-done) div.stButton > button:hover {{
        background: rgba(4,52,99,0.06) !important;
        color: {config.COLOR_PRIMARY} !important;
        box-shadow: none !important;
        transform: none !important;
    }}

    /* Khoảng thở giữa toàn bộ cụm Stepper và Card nội dung bên dưới */
    div[data-testid="stVerticalBlock"]:has(> div.step-bar-wrap-marker) {{
        margin-bottom: 30px;
    }}

    /* Ẩn icon liên kết (anchor link) mà Streamlit tự thêm cạnh mỗi tiêu đề */
    [data-testid="stHeaderActionElements"] {{
        display: none !important;
    }}

    /* ===================== TIÊU ĐỀ MỤC (thay emoji bằng SVG icon nét mảnh) ===================== */
    .section-title {{
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 24px;
        font-weight: 700;
        color: {config.COLOR_BLACK};
        margin: 0 0 0.6rem 0;
    }}
    .section-title svg {{
        flex-shrink: 0;
    }}

    /* ===================== CARD CHỨA NỘI DUNG (container border=True) ===================== */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: {config.COLOR_WHITE} !important;
        border: 1px solid #E7EAEE !important;
        border-top: 4px solid {config.COLOR_ACCENT} !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 16px rgba(0,0,0,0.06) !important;
        margin-bottom: 20px;
    }}
    div[data-testid="stVerticalBlockBorderWrapper"] > div {{
        padding: 8px 6px;
    }}

    /* ===================== VÙNG NHẬP LIỆU - NỀN SÁNG NỔI BẬT ===================== */
    div[data-testid="stVerticalBlock"]:has(> div.input-zone-marker) {{
        background-color: #F4F8FC !important;
        border: 1px solid #E1EAF3 !important;
        border-radius: 12px !important;
        padding: 18px !important;
        margin-top: 10px;
        margin-bottom: 10px;
    }}

    /* ===================== Ô NHẬP LIỆU (INPUT) ===================== */
    .stTextInput input, .stNumberInput input {{
        background-color: {config.COLOR_WHITE} !important;
        border: 1px solid #D9DEE3 !important;
        border-radius: 8px !important;
        color: {config.COLOR_BLACK} !important;
    }}
    .stTextInput input:focus, .stNumberInput input:focus {{
        border-color: {config.COLOR_PRIMARY} !important;
        box-shadow: 0 0 0 2px rgba(4,52,99,0.15) !important;
    }}
    div[data-baseweb="select"] > div {{
        background-color: {config.COLOR_WHITE} !important;
        border: 1px solid #D9DEE3 !important;
        border-radius: 8px !important;
    }}
    div[data-testid="stFileUploaderDropzone"] {{
        background-color: {config.COLOR_WHITE} !important;
        border: 1.5px dashed #C7CFD8 !important;
        border-radius: 10px !important;
    }}

    /* ===================== NÚT HÀNH ĐỘNG CHÍNH ===================== */
    div.stButton > button {{
        background-color: {config.COLOR_PRIMARY};
        color: white;
        border-radius: 8px;
        font-weight: 600;
        border: none;
        padding: 10px 22px;
        transition: all 0.15s ease;
    }}
    div.stButton > button:hover {{
        background-color: #06508f;
        color: {config.COLOR_ACCENT};
        transform: translateY(-1px);
        box-shadow: 0 3px 8px rgba(4,52,99,0.25);
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
# ICON SVG NÉT MẢNH (thay cho emoji 3D, đồng bộ phong cách Flat/Corporate)
# ============================================================
def _icon_svg(path_svg: str, size: int = 24) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{config.COLOR_PRIMARY}" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round">{path_svg}</svg>'
    )


ICON_LOCK = _icon_svg(
    '<rect x="5" y="11" width="14" height="9" rx="2"></rect>'
    '<path d="M8 11V7a4 4 0 0 1 8 0v4"></path>'
)
ICON_STORE = _icon_svg(
    '<path d="M3 9l1.5-5h15L21 9"></path>'
    '<path d="M3 9a2 2 0 0 0 4 0 2 2 0 0 0 4 0 2 2 0 0 0 4 0 2 2 0 0 0 4 0"></path>'
    '<path d="M5 9v10h14V9"></path>'
    '<path d="M9 21v-6h6v6"></path>'
)
ICON_CHART = _icon_svg(
    '<polyline points="3 17 9 11 13 15 21 7"></polyline>'
    '<polyline points="14 7 21 7 21 14"></polyline>'
)
ICON_CHECK = _icon_svg(
    '<circle cx="12" cy="12" r="9"></circle>'
    '<polyline points="8 12 11 15 16 9"></polyline>'
)


def section_title(icon_html: str, text: str):
    """Vẽ tiêu đề mục (thay cho st.subheader) với icon SVG nét mảnh + chữ."""
    st.markdown(
        f'<div class="section-title">{icon_html}<span>{text}</span></div>',
        unsafe_allow_html=True,
    )

# ============================================================
# HEADER (logo trên cùng, 2 dòng tiêu đề bên dưới, căn giữa)
# ============================================================
st.markdown(
    f"""
    <div class="kpi-header">
        <img src="{config.LOGO_URL}" />
        <div class="kpi-header-text">
            <h1 class="kpi-title">{config.APP_TITLE}</h1>
            <span class="kpi-subtitle">Hệ thống thu thập & xác thực chỉ số KPI hàng tháng</span>
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
if "is_bulk" not in st.session_state:
    st.session_state.is_bulk = False
if "bulk_rows" not in st.session_state:
    st.session_state.bulk_rows = []

STEP_LABELS = ["Xác thực NV", "Chọn nhà hàng", "Nhập KPI", "Xác nhận & Gửi"]


def render_step_bar():
    """
    Vẽ stepper kiểu vạch pill bo tròn nối giữa các bước (tách rời khỏi card
    bên dưới bằng margin riêng), kích thước to hơn. Bước ĐÃ HOÀN THÀNH là nút
    bấm thật (st.button) -- bấm để quay lại bước đó. Bước hiện tại / chưa tới
    là nhãn tĩnh, không bấm được.

    Vạch pill được vẽ là 1 <div> RIÊNG ngay sau chữ/nút (dòng chảy tài liệu
    bình thường), KHÔNG dùng ::after định vị tuyệt đối -- tránh lệch hàng
    giữa các bước khi các cột bị co giãn chiều cao không đồng đều.
    """
    with st.container():
        st.markdown('<div class="step-bar-wrap-marker"></div>', unsafe_allow_html=True)
        cols = st.columns(len(STEP_LABELS))
        for idx, col in enumerate(cols, start=1):
            with col:
                status = "active" if idx == st.session_state.step else ("done" if idx < st.session_state.step else "upcoming")
                with st.container():
                    st.markdown(f'<div class="step-marker step-marker-{status}"></div>', unsafe_allow_html=True)
                    if status == "done":
                        if st.button(STEP_LABELS[idx - 1], key=f"step_nav_{idx}", use_container_width=True):
                            st.session_state.step = idx
                            st.rerun()
                    else:
                        st.markdown(
                            f'<div class="step-static-label {status}">{STEP_LABELS[idx - 1]}</div>',
                            unsafe_allow_html=True,
                        )
                    st.markdown(f'<div class="step-pill {status}"></div>', unsafe_allow_html=True)


render_step_bar()
# Spacer cố định (không phụ thuộc CSS :has()) để đảm bảo Stepper luôn tách
# rời hoàn toàn khỏi Card bên dưới, kể cả khi trình duyệt không hỗ trợ :has().
st.markdown('<div style="height: 28px;"></div>', unsafe_allow_html=True)

# ============================================================
# VIEW 1: XÁC THỰC NHÂN VIÊN
# ============================================================
if st.session_state.step == 1:
    with st.container(border=True):
        section_title(ICON_LOCK, "Xác thực Nhân viên")
        st.write("Vui lòng nhập Mã nhân viên để hệ thống tra cứu bộ phận và phân quyền nhập liệu.")

        with st.container():
            st.markdown('<div class="input-zone-marker"></div>', unsafe_allow_html=True)

            ma_nv_input = st.text_input(
                "Mã nhân viên", value=st.session_state.ma_nv, placeholder="Ví dụ: BN.DNG"
            )

            if st.button("Tra cứu", type="primary", use_container_width=True):
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

# ============================================================
# VIEW 2: CHỌN NHÀ HÀNG (hoặc Bulk Import nhiều nhà hàng)
# ============================================================
elif st.session_state.step == 2:
    with st.container(border=True):
        section_title(ICON_STORE, "Chọn Nhà hàng")
        st.markdown(
            f'<span class="info-pill">Mã NV: {st.session_state.ma_nv}</span>'
            f'<span class="info-pill">Bộ phận: {st.session_state.ma_bo_phan}</span>',
            unsafe_allow_html=True,
        )
        st.write("")

        mode = st.radio(
            "Phương thức",
            options=["🔍 Chọn từng nhà hàng", "📥 Bulk Import nhiều nhà hàng cùng lúc"],
            horizontal=True,
        )

        dept = st.session_state.ma_bo_phan
        allowed_fields = [k for k, v in config.KPI_FIELDS.items() if v["dept"] == dept]

        input_zone = st.container()
        input_zone.markdown('<div class="input-zone-marker"></div>', unsafe_allow_html=True)

        # -------------------- NHÁNH 1: CHỌN TỪNG NHÀ HÀNG --------------------
        if mode == "🔍 Chọn từng nhà hàng":
          with input_zone:
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
                    if st.button("⬅ Quay lại", use_container_width=True):
                        st.session_state.step = 1
                        st.rerun()
                with col_next:
                    if st.button("Tiếp tục ➡", type="primary", use_container_width=True):
                        st.session_state.restaurant = selected
                        st.session_state.is_bulk = False
                        st.session_state.step = 3
                        st.rerun()
            else:
                st.warning("Không có dữ liệu nhà hàng hoặc không thể kết nối tới Google Sheets.")
                if st.button("⬅ Quay lại"):
                    st.session_state.step = 1
                    st.rerun()

        # -------------------- NHÁNH 2: BULK IMPORT --------------------
        else:
          with input_zone:
            st.markdown(
                f"[📥 Tải file Template mẫu]({config.TEMPLATE_DOWNLOAD_URL})  \n"
                "Điền **Mã nhà hàng** vào cột A cho từng dòng, và điền giá trị KPI vào các cột "
                "thuộc thẩm quyền bộ phận của bạn (các cột khác có thể để trống). "
                "Sau khi upload, hệ thống sẽ chuyển thẳng sang bước Xác nhận."
            )

            col_thang, col_nam = st.columns(2)
            with col_thang:
                bulk_thang = st.selectbox(
                    "Tháng (áp dụng cho toàn bộ danh sách)",
                    options=config.MONTHS,
                    index=config.MONTHS.index(st.session_state.thang),
                )
            with col_nam:
                bulk_nam = st.number_input(
                    "Năm", min_value=2020, max_value=2100, value=st.session_state.nam, step=1
                )

            uploaded_bulk_file = st.file_uploader(
                "Upload file Excel (.xlsx) hoặc CSV — mỗi dòng là 1 nhà hàng",
                type=["xlsx", "xls", "csv"],
                key="bulk_uploader",
            )

            if uploaded_bulk_file is not None:
                try:
                    parsed_rows = utils.parse_bulk_template_file(uploaded_bulk_file, allowed_fields)
                    with st.spinner("Đang đối chiếu Mã nhà hàng..."):
                        restaurants = load_restaurants()
                    restaurant_lookup = {r["ma"]: r for r in restaurants}

                    enriched_rows = []
                    unknown_codes = []
                    for row in parsed_rows:
                        info = restaurant_lookup.get(row["ma_nha_hang"])
                        if info is None:
                            unknown_codes.append(row["ma_nha_hang"])
                            enriched_rows.append(
                                {
                                    "ma": row["ma_nha_hang"],
                                    "tinh": "(không rõ)",
                                    "dia_chi": "(không rõ)",
                                    "values": row["values"],
                                }
                            )
                        else:
                            enriched_rows.append(
                                {
                                    "ma": info["ma"],
                                    "tinh": info["tinh"],
                                    "dia_chi": info["dia_chi"],
                                    "values": row["values"],
                                }
                            )

                    st.success(f"✅ Đã đọc {len(enriched_rows)} dòng dữ liệu từ file.")
                    if unknown_codes:
                        st.warning(
                            "⚠️ Các Mã nhà hàng sau KHÔNG khớp với Danh sách Nhà hàng hệ thống, "
                            "vui lòng kiểm tra lại chính tả trước khi Submit: "
                            + ", ".join(unknown_codes)
                        )

                    if st.button("Xác nhận danh sách ➡ Đi tới bước 4", type="primary", use_container_width=True):
                        st.session_state.bulk_rows = enriched_rows
                        st.session_state.is_bulk = True
                        st.session_state.thang = bulk_thang
                        st.session_state.nam = int(bulk_nam)
                        st.session_state.step = 4
                        st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

            if st.button("⬅ Quay lại"):
                st.session_state.step = 1
                st.rerun()

# ============================================================
# VIEW 3: NHẬP DỮ LIỆU KPI (chỉ áp dụng cho luồng chọn từng nhà hàng)
# ============================================================
elif st.session_state.step == 3:
    with st.container(border=True):
        section_title(ICON_CHART, "Nhập dữ liệu KPI")
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

        current_values = dict(st.session_state.kpi_values)

        # -------- Vùng nhập liệu: nền sáng nổi bật (đánh dấu qua input-zone-marker) --------
        with st.container():
            st.markdown('<div class="input-zone-marker"></div>', unsafe_allow_html=True)

            input_mode = st.radio(
                "Phương thức nhập dữ liệu",
                options=["Nhập trực tiếp", "Upload file Excel/CSV theo mẫu"],
                horizontal=True,
            )

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
                    "Hệ thống sẽ tự động đọc & điền vào các chỉ số thuộc thẩm quyền bộ phận của bạn "
                    "(dòng dữ liệu đầu tiên trong file sẽ được sử dụng)."
                )
                uploaded_file = st.file_uploader(
                    "Upload file Excel (.xlsx) hoặc CSV", type=["xlsx", "xls", "csv"]
                )
                if uploaded_file is not None:
                    try:
                        extracted, file_ma_nha_hang = utils.parse_template_file(uploaded_file, allowed_fields)

                        # QUAN TRỌNG: set trực tiếp session_state của từng ô nhập TRƯỚC khi
                        # vẽ lại widget, vì Streamlit ưu tiên giá trị đã lưu trong session_state
                        # theo key hơn tham số value= truyền vào -- nếu không làm bước này,
                        # ô sẽ vẫn giữ giá trị cũ (0.00) dù đã đọc được dữ liệu mới từ file.
                        for k, v in extracted.items():
                            st.session_state[f"upload_input_{k}"] = v

                        current_values.update(extracted)
                        st.success("✅ Đã đọc và điền dữ liệu từ file thành công. Vui lòng kiểm tra lại bên dưới.")

                        if file_ma_nha_hang and file_ma_nha_hang != st.session_state.restaurant["ma"]:
                            st.warning(
                                f"⚠️ Mã nhà hàng trong file (**{file_ma_nha_hang}**) không khớp với "
                                f"nhà hàng đã chọn ở bước 2 (**{st.session_state.restaurant['ma']}**). "
                                f"Dữ liệu KPI vẫn được điền vào form, vui lòng kiểm tra lại kỹ trước khi Submit."
                            )
                    except ValueError as exc:
                        st.error(str(exc))

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
            if st.button("⬅ Quay lại", use_container_width=True):
                st.session_state.step = 2
                st.rerun()
        with col_next:
            if st.button("Tiếp tục ➡", type="primary", use_container_width=True):
                st.session_state.thang = thang
                st.session_state.nam = int(nam)
                st.session_state.kpi_values = current_values
                st.session_state.step = 4
                st.rerun()

# ============================================================
# VIEW 4: XÁC NHẬN & SUBMIT
# ============================================================
elif st.session_state.step == 4:
    with st.container(border=True):
        section_title(ICON_CHECK, "Xác nhận & Gửi dữ liệu")

        # -------------------- NHÁNH BULK IMPORT --------------------
        if st.session_state.is_bulk:
            st.markdown("**Thông tin Validator**")
            st.table(
                {
                    "Mã nhân viên": [st.session_state.ma_nv],
                    "Bộ phận": [st.session_state.ma_bo_phan],
                    "Tháng/Năm": [f"{st.session_state.thang:02d}/{st.session_state.nam}"],
                }
            )

            st.markdown(f"**Danh sách {len(st.session_state.bulk_rows)} nhà hàng sẽ được ghi nhận**")
            display_rows = []
            for row in st.session_state.bulk_rows:
                item = {"Mã nhà hàng": row["ma"], "Tỉnh/Thành phố": row["tinh"]}
                for key in config.WRITE_ROW_ORDER:
                    meta = config.KPI_FIELDS[key]
                    if meta["dept"] == st.session_state.ma_bo_phan:
                        val = row["values"].get(key)
                        item[meta["label"]] = utils.format_value_display(val, meta["value_type"]) if val is not None else "-"
                display_rows.append(item)
            st.dataframe(display_rows, use_container_width=True, hide_index=True)

            st.info(
                "Lưu ý: các chỉ số **không** thuộc thẩm quyền bộ phận của bạn sẽ được ghi giá trị **0** "
                "vào sheet Thực tế cho mỗi dòng."
            )

            col_back, col_submit = st.columns([1, 1])
            with col_back:
                if st.button("⬅ Quay lại chỉnh sửa", use_container_width=True):
                    st.session_state.step = 2
                    st.rerun()
            with col_submit:
                if st.button("🚀 Submit tất cả", type="primary", use_container_width=True):
                    try:
                        progress = st.progress(0, text="Đang ghi dữ liệu vào Google Sheets...")
                        total = len(st.session_state.bulk_rows)
                        for i, row in enumerate(st.session_state.bulk_rows, start=1):
                            append_actual_row(
                                ma_cua_hang=row["ma"],
                                thang=st.session_state.thang,
                                nam=st.session_state.nam,
                                values=row["values"],
                                ma_nv=st.session_state.ma_nv,
                            )
                            progress.progress(i / total, text=f"Đang ghi... ({i}/{total})")
                        st.session_state.submitted = True
                        st.session_state.step = 5
                        st.rerun()
                    except Exception as exc:
                        st.error(f"❌ Gửi dữ liệu thất bại: {exc}")

        # -------------------- NHÁNH ĐƠN LẺ (1 NHÀ HÀNG) --------------------
        else:
            st.markdown("**Thông tin Validator**")
            st.table(
                {
                    "Mã nhân viên": [st.session_state.ma_nv],
                    "Bộ phận": [st.session_state.ma_bo_phan],
                }
            )

            st.markdown("**Thông tin nhà hàng được đánh giá**")
            st.table(
                {
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
                if st.button("⬅ Quay lại chỉnh sửa", use_container_width=True):
                    st.session_state.step = 3
                    st.rerun()
            with col_submit:
                if st.button("🚀 Submit / Gửi dữ liệu", type="primary", use_container_width=True):
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

# ============================================================
# VIEW 5 (Kết quả): THÀNH CÔNG
# ============================================================
elif st.session_state.step == 5:
    with st.container(border=True):
        if st.session_state.is_bulk:
            st.success(
                f"🎉 Đã ghi nhận thành công dữ liệu cho **{len(st.session_state.bulk_rows)} nhà hàng** "
                f"vào sheet **Thực tế**!"
            )
            st.write(
                f"Tháng {st.session_state.thang:02d}/{st.session_state.nam} "
                f"— Người nhập: {st.session_state.ma_nv} ({st.session_state.ma_bo_phan})"
            )
        else:
            st.success("🎉 Dữ liệu đã được ghi nhận thành công vào sheet **Thực tế**!")
            st.write(
                f"Nhà hàng **{st.session_state.restaurant['ma']}** — "
                f"Tháng {st.session_state.thang:02d}/{st.session_state.nam} "
                f"— Người nhập: {st.session_state.ma_nv} ({st.session_state.ma_bo_phan})"
            )

        if st.button("➕ Nhập cho nhà hàng / tháng khác", use_container_width=True):
            st.session_state.step = 2
            st.session_state.kpi_values = {}
            st.session_state.is_bulk = False
            st.session_state.bulk_rows = []
            st.session_state.thang, st.session_state.nam = utils.default_month_year()
            st.rerun()

        if st.button("🔄 Bắt đầu lại từ đầu", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

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
