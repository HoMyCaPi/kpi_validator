# KPI Validator Workspace

Ứng dụng nội bộ (Streamlit) giúp nhân viên các bộ phận **PKT, PQA, PNS, MKT** nhập chỉ số
KPI hàng tháng theo đúng phân quyền, dữ liệu được ghi trực tiếp vào Google Sheets.

---

## 1. Cấu trúc project

```
kpi_validator/
├── app.py                          # Giao diện chính (4 View / wizard)
├── config.py                       # Toàn bộ cấu hình: ID Sheet, GID, màu, danh sách KPI
├── sheets_service.py               # Toàn bộ logic đọc/ghi Google Sheets (gspread)
├── utils.py                        # Hàm tiện ích: tính tháng mặc định, đọc file upload
├── requirements.txt                # Thư viện cần cài
├── .streamlit/
│   └── secrets.toml.example        # File mẫu để cấu hình Service Account
└── README.md                       # Tài liệu này
```

**Nguyên tắc chia module:**
- `config.py`: nơi DUY NHẤT chứa ID/GID Google Sheets, bảng màu, danh sách chỉ số KPI.
  Muốn đổi cấu trúc nghiệp vụ (thêm chỉ số, đổi bộ phận, đổi cột) chỉ cần sửa file này.
- `sheets_service.py`: DUY NHẤT chứa code gọi Google Sheets API. `app.py` không bao giờ
  gọi trực tiếp `gspread`, giúp dễ thay đổi cách xác thực / cách đọc-ghi sau này.
- `utils.py`: các hàm thuần logic (tính ngày tháng, parse Excel) không phụ thuộc UI.
- `app.py`: chỉ lo phần giao diện & điều phối luồng 4 bước (wizard), gọi vào 2 module trên.

---

## 2. Cài đặt & chạy local

```bash
# 1. Tạo virtual env (khuyến nghị)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Cài thư viện
pip install -r requirements.txt

# 3. Cấu hình Service Account (xem mục 3 bên dưới)

# 4. Chạy ứng dụng
streamlit run app.py
```

Ứng dụng sẽ mở tại `http://localhost:8501`.

---

## 3. Cấu hình Service Account để kết nối Google Sheets

Ứng dụng dùng **Service Account** (tài khoản dịch vụ của Google Cloud) để đọc/ghi Google
Sheets mà KHÔNG cần người dùng đăng nhập Google mỗi lần. Làm theo đúng các bước sau:

### Bước 1 — Tạo Project trên Google Cloud Console
1. Truy cập https://console.cloud.google.com/
2. Góc trên bên trái, bấm chọn Project → **New Project**.
3. Đặt tên (ví dụ: `kpi-validator-workspace`) → **Create**.

### Bước 2 — Bật (Enable) 2 API cần thiết
Trong Project vừa tạo, vào **APIs & Services → Library**, tìm và bật lần lượt:
- **Google Sheets API**
- **Google Drive API** (cần để `gspread` mở file theo ID)

### Bước 3 — Tạo Service Account
1. Vào **APIs & Services → Credentials**.
2. Bấm **Create Credentials → Service account**.
3. Đặt tên, ví dụ `kpi-validator` → **Create and Continue**.
4. Phần "Grant this service account access to project": có thể bỏ qua (Skip) vì
   quyền truy cập Sheet sẽ được cấp riêng ở Bước 5.
5. Bấm **Done**.

### Bước 4 — Tạo Key (file JSON) cho Service Account
1. Trong danh sách **Credentials**, bấm vào Service Account vừa tạo.
2. Vào tab **Keys → Add Key → Create new key**.
3. Chọn định dạng **JSON** → **Create**.
4. Trình duyệt sẽ tự tải về 1 file `.json` — **giữ bí mật file này**, không commit lên Git.

File JSON có dạng:
```json
{
  "type": "service_account",
  "project_id": "kpi-validator-workspace",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "kpi-validator@kpi-validator-workspace.iam.gserviceaccount.com",
  "client_id": "...",
  ...
}
```
Ghi nhớ giá trị `client_email` — đây chính là "địa chỉ" bạn sẽ dùng để **Share (chia sẻ)**
các Google Sheets nguồn dữ liệu ở bước tiếp theo.

### Bước 5 — Share (chia sẻ) 4 Google Sheets nguồn dữ liệu cho Service Account
Mở lần lượt **4 file Google Sheets** sau, bấm nút **Share (Chia sẻ)** ở góc trên bên phải,
và thêm email của Service Account (`client_email` ở Bước 4) với quyền:

| Sheet | ID | Quyền cần cấp |
|---|---|---|
| Monthly KPI (chứa sheet "Thực tế") | `196DIW3ZxGvJdbqEiCMui5F_mJXNGPSK0zwMM1Ab72j0` | **Editor** (cần ghi dữ liệu) |
| 2026 - PNS Data share - Ngọc | `19G1FRmD5rAqyMMKXFjmalOdpVG64GLfG` | Viewer (chỉ đọc) |
| Danh sách Nhà hàng | `1TPRbbPfzCsCxW55VYHyYVfn47wNhdYdiQ_uqazR0_5I` | Viewer (chỉ đọc) |
| File Template mẫu | `1mjhtClhmlMDINF_dUZEHbGeQ7WrxGm3c6ZjxhM7_Y7c` | Viewer (chỉ đọc, hoặc để "Anyone with link" vì chỉ dùng để tải file mẫu) |

> ⚠️ Nếu bỏ qua bước Share này, ứng dụng sẽ báo lỗi `PermissionError` / `SpreadsheetNotFound`
> dù ID Sheet đã đúng, vì Service Account chưa có quyền truy cập.

### Bước 6 — Nạp credentials vào ứng dụng

**Cách A — Chạy local (khuyến nghị khi phát triển):**
1. Đổi tên file JSON tải về thành `service_account.json`.
2. Copy file này vào **cùng thư mục với `app.py`**.
3. `sheets_service.py` sẽ tự động đọc file này nếu không tìm thấy `st.secrets`.
4. **Tuyệt đối không** đưa file này lên Git/GitHub công khai (thêm vào `.gitignore`).

**Cách B — Deploy lên Streamlit Community Cloud (khuyến nghị khi dùng thật cho team):**
1. Mở file JSON Service Account, copy toàn bộ nội dung.
2. Trong project, tạo file `.streamlit/secrets.toml` (copy từ file mẫu
   `.streamlit/secrets.toml.example` đi kèm), rồi điền đúng các giá trị tương ứng từ JSON
   vào các trường: `project_id`, `private_key_id`, `private_key`, `client_email`, `client_id`,
   `client_x509_cert_url`.
   - Lưu ý: giữ nguyên các ký tự `\n` bên trong `private_key` (không xuống dòng thật).
3. Khi deploy trên https://streamlit.io/cloud, vào **App settings → Secrets**, dán toàn bộ
   nội dung `secrets.toml` vào đó (Streamlit Cloud sẽ tự inject vào `st.secrets`).
4. `.streamlit/secrets.toml` (bản thật) **không được commit lên Git** — chỉ giữ file
   `.example` trong repo.

---

## 4. Ghi chú nghiệp vụ quan trọng

- **Tra cứu bộ phận (View 1):** dò cột B (Mã NV) trong sheet PNS (gid=254853384), lấy giá trị
  tương ứng ở cột F (Mã bộ phận). Nếu không tìm thấy → báo lỗi, không cho qua View 2.
- **Phân quyền nhập KPI (View 3):** mỗi bộ phận chỉ thấy & nhập được đúng chỉ số của mình
  (định nghĩa trong `config.KPI_FIELDS`, field `dept`). Các chỉ số khác sẽ **không hiển thị**
  form nhập, và khi ghi vào sheet "Thực tế" sẽ được set = **0** (chờ bộ phận sở hữu cập nhật
  ở lượt nhập riêng của họ).
- **Upload file mẫu (Cách 2):** hệ thống match theo **đúng tên tiêu đề cột** trong file Excel
  (ví dụ "Doanh thu (PKT)") với `label` khai báo trong `config.KPI_FIELDS`. Nếu đổi tên cột
  trong Template gốc, phải cập nhật `label` tương ứng trong `config.py`.
- **Thứ tự cột khi ghi vào sheet "Thực tế":**
  `A: Mã cửa hàng | B: Tháng | C: Năm | D: Doanh thu | E: Điểm QA Audit | F: COGS | `
  `G: COL | H: Compliant rate | I: EBITDA | J: Mã nhân viên | K: Thời gian ghi nhận`
- Mỗi lần Submit sẽ **append thêm 1 dòng mới** (không ghi đè), nên lịch sử nhập liệu của tất
  cả các bộ phận cho cùng 1 nhà hàng/tháng sẽ nằm trên nhiều dòng khác nhau trong sheet
  "Thực tế" — việc tổng hợp/consolidate theo nhà hàng + tháng nên xử lý ở lớp báo cáo
  (ví dụ Google Sheets QUERY/Pivot, hoặc BI) chứ không phải ở bước ghi dữ liệu này.

---

## 5. Xử lý sự cố thường gặp

| Lỗi | Nguyên nhân | Cách khắc phục |
|---|---|---|
| `RuntimeError: Không tìm thấy thông tin xác thực...` | Chưa cấu hình `secrets.toml` hoặc `service_account.json` | Xem lại Bước 6 |
| `gspread.exceptions.SpreadsheetNotFound` | Service Account chưa được share quyền vào Sheet | Xem lại Bước 5 |
| `APIError: PERMISSION_DENIED` khi Submit | Service Account chỉ có quyền Viewer trên sheet Monthly KPI | Đổi thành quyền **Editor** |
| Không tìm thấy Mã nhân viên dù chắc chắn đúng | Sai gid/sheet, hoặc dữ liệu có khoảng trắng thừa | Kiểm tra lại gid=254853384 và dữ liệu cột B |
| Upload file không đọc được KPI nào | Tên tiêu đề cột trong file không khớp `label` trong `config.py` | Sửa lại tiêu đề cột hoặc cập nhật `config.KPI_FIELDS` |

---

## 6. Bảo mật

- File `service_account.json` / `secrets.toml` (bản thật) chứa private key — **không** commit
  lên Git, không chia sẻ qua chat công khai.
- Chỉ nên cấp quyền **Editor** cho đúng 1 sheet cần ghi (Monthly KPI), các sheet còn lại chỉ
  cần **Viewer**.
- Có thể tạo riêng 1 Service Account chỉ dùng cho ứng dụng này, để dễ thu hồi quyền truy cập
  nếu cần mà không ảnh hưởng các ứng dụng khác.
