# KPI Validator Workspace

Ứng dụng nội bộ (Streamlit) giúp nhân viên các bộ phận **PKT, PQA, PNS, MKT** nhập chỉ số
KPI hàng tháng theo đúng phân quyền, dữ liệu được ghi trực tiếp vào Google Sheets.

---

## 1. Cấu trúc project

```
kpi_validator/
├── app.py                          # Giao diện chính (4 View / wizard)
├── config.py                       # Toàn bộ cấu hình: ID Sheet, GID, màu, danh sách KPI
├── sheets_service.py               # Gọi Apps Script Web App để đọc/ghi Google Sheets
├── utils.py                        # Hàm tiện ích: tính tháng mặc định, đọc file upload
├── requirements.txt                # Thư viện cần cài
├── apps_script/
│   └── Code.gs                     # Backend Google Apps Script (deploy riêng trên script.google.com)
├── .streamlit/
│   └── secrets.toml.example        # File mẫu để cấu hình apps_script_url / api_key
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

## 3. Cấu hình Google Apps Script Backend (thay cho Service Account)

Ứng dụng dùng **Google Apps Script Web App** làm lớp trung gian (proxy) đọc/ghi
Google Sheets, thay vì Service Account. Lý do: Apps Script chạy dưới danh tính
**tài khoản Google nội bộ công ty của bạn** (Execute as: "Me"), nên không bị
chính sách "chặn chia sẻ ra ngoài tổ chức" (external sharing) của Google
Workspace áp dụng — vốn là nguyên nhân Service Account (`...iam.gserviceaccount.com`)
bị từ chối quyền dù đã share file công khai.

Code Apps Script nằm ở `apps_script/Code.gs`.

### Bước 1 — Tạo Apps Script Project
1. Truy cập https://script.google.com/home (đăng nhập bằng **tài khoản công ty**
   đang có quyền truy cập cả 4 Google Sheets nguồn — ví dụ tài khoản bạn dùng để
   mở các sheet đó hằng ngày).
2. **New project** (Dự án mới).
3. Đặt tên project, ví dụ `KPI Validator Backend` (bấm vào chữ "Untitled project" ở góc trên trái).

### Bước 2 — Dán code & cấu hình API Key
1. Xoá toàn bộ nội dung mặc định trong file `Code.gs` bên trái.
2. Copy toàn bộ nội dung file `apps_script/Code.gs` (trong project này) và dán vào.
3. Sửa dòng:
   ```javascript
   API_KEY: "THAY_BANG_CHUOI_BI_MAT_CUA_BAN",
   ```
   thành 1 chuỗi ngẫu nhiên, dài, khó đoán — ví dụ tự gõ 1 chuỗi 32 ký tự bất kỳ.
   Đây là "mật khẩu" giữa Streamlit app và Apps Script, **giữ bí mật**, không public.
4. Kiểm tra lại các ID/GID trong `CONFIG` đã đúng với 4 nguồn dữ liệu của bạn
   (đặc biệt `SPREADSHEET_PNS_ID` — phải là ID của bản Google Sheets GỐC, không
   phải file `.xlsx` thô nếu trước đó bạn đã convert).
5. Lưu lại: **Ctrl+S** (hoặc Cmd+S).

### Bước 3 — Test nhanh (tuỳ chọn, khuyến nghị)
1. Trong thanh công cụ phía trên, ở dropdown chọn hàm chạy thử, chọn `testLookup`.
2. Bấm **Run** (▶). Lần đầu chạy, Google sẽ yêu cầu **cấp quyền (Authorize access)**:
   - Chọn đúng tài khoản Google đang dùng.
   - Nếu hiện cảnh báo "Google chưa xác minh ứng dụng này" → bấm **Advanced/Nâng cao**
     → **Go to KPI Validator Backend (unsafe)** → **Allow/Cho phép**. Đây là cảnh báo
     bình thường với Apps Script tự viết, không phải lỗi.
3. Vào **View → Logs** (hoặc Ctrl+Enter) để xem kết quả tra cứu — nếu ra đúng
   bộ phận của mã nhân viên test, nghĩa là script đã có quyền đọc Sheet thành công.

### Bước 4 — Deploy thành Web App
1. Góc trên phải, bấm **Deploy → New deployment**.
2. Bấm biểu tượng bánh răng cạnh "Select type" → chọn **Web app**.
3. Điền:
   - **Description**: `KPI Validator v1`
   - **Execute as**: **Me (email của bạn)**
   - **Who has access**: **Anyone**
4. Bấm **Deploy**.
5. Nếu được hỏi cấp quyền lần nữa, làm tương tự Bước 3.
6. Sau khi deploy xong, copy **Web app URL** — có dạng:
   ```
   https://script.google.com/macros/s/XXXXXXXXXXXXXXXXXXXX/exec
   ```
   Đây chính là `apps_script_url` sẽ dùng ở Bước 5.

> ⚠️ Mỗi khi bạn **sửa code** trong `Code.gs` sau này, phải vào **Deploy → Manage
> deployments → (chọn deployment) → Edit (biểu tượng bút chì) → Version: New version
> → Deploy** thì thay đổi mới có hiệu lực trên URL cũ. Tạo "New deployment" hoàn
> toàn mới sẽ sinh ra URL khác, phải cập nhật lại Secrets.

### Bước 5 — Nạp URL + API Key vào Streamlit

**Cách A — Streamlit Community Cloud:**
1. Vào app trên Streamlit Cloud → **Manage app → Settings → Secrets**.
2. **Xoá** khối `[gcp_service_account]` cũ (nếu còn) — không cần nữa.
3. Dán:
   ```toml
   apps_script_url = "https://script.google.com/macros/s/XXXXXXXXXXXXXXXXXXXX/exec"
   apps_script_api_key = "chuoi-bi-mat-ban-dat-o-Buoc-2"
   ```
4. **Save** → app tự khởi động lại.

**Cách B — Chạy local:**
1. Copy `.streamlit/secrets.toml.example` thành `.streamlit/secrets.toml`.
2. Điền đúng 2 giá trị trên vào đó.
3. `.streamlit/secrets.toml` (bản thật) **không được commit lên Git**.

### Bước 6 — Kiểm tra hoạt động
Mở app, nhập 1 Mã nhân viên có thật → nếu tra được bộ phận và chuyển sang View 2
là toàn bộ chuỗi kết nối đã thông suốt.

---

## 3b. (Tham khảo) Cách cũ dùng Service Account — khi nào nên dùng lại

Cách Service Account (đã mô tả trong các phiên bản trước của tài liệu này) vẫn
là cách chuẩn, phổ biến và không phụ thuộc vào 1 tài khoản cá nhân cụ thể nào.
Nhược điểm duy nhất gặp phải là một số Google Workspace bật chính sách chặn
chia sẻ file ra ngoài tổ chức, khiến Service Account (được xem là "external
identity") bị từ chối quyền dù đã share công khai. Nếu công ty bạn:
- Có Admin sẵn sàng bật `Sharing outside of organization` hoặc cấu hình
  `Domain-wide delegation`, hoặc
- Không gặp vấn đề chặn nói trên,

thì quay lại dùng Service Account vẫn là lựa chọn ổn định hơn về lâu dài, vì
không phụ thuộc vào 1 tài khoản cá nhân cụ thể phải tồn tại/đăng nhập được.
Trường hợp dùng Apps Script như tài liệu này: nếu tài khoản đã tạo & deploy
script bị khoá/đổi mật khẩu/rời công ty, cần người khác deploy lại.

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
| `RuntimeError: Chưa cấu hình APPS_SCRIPT_URL...` | Chưa dán `apps_script_url` / `apps_script_api_key` vào Secrets | Xem lại Bước 5 |
| `Apps Script báo lỗi: Unauthorized: sai API key` | `apps_script_api_key` trong Secrets không khớp `CONFIG.API_KEY` trong `Code.gs` | Kiểm tra lại 2 giá trị này khớp nhau tuyệt đối |
| `Apps Script trả về dữ liệu không phải JSON hợp lệ` | URL sai, hoặc "Who has access" chưa để "Anyone" | Deploy lại đúng theo Bước 4 |
| `Apps Script báo lỗi: Không tìm thấy sheet với gid=...` | Sai GID trong `Code.gs`, hoặc tài khoản deploy không có quyền xem sheet đó | Kiểm tra lại GID + quyền truy cập của tài khoản đã deploy script |
| Không tìm thấy Mã nhân viên dù chắc chắn đúng | Sai ID/GID trong `Code.gs`, hoặc dữ liệu có khoảng trắng thừa | Dùng `testLookup()` trong Apps Script Editor để debug trực tiếp (xem Bước 3) |
| Sửa `Code.gs` xong nhưng không thấy đổi | Quên tạo **New version** khi deploy lại | Deploy → Manage deployments → Edit → Version: New version → Deploy |
| Upload file không đọc được KPI nào | Tên tiêu đề cột trong file không khớp `label` trong `config.py` | Sửa lại tiêu đề cột hoặc cập nhật `config.KPI_FIELDS` |

---

## 6. Bảo mật

- `apps_script_api_key` đóng vai trò như 1 mật khẩu API — **không** commit lên Git, không
  chia sẻ qua chat công khai. Nếu nghi ngờ bị lộ, đổi `API_KEY` trong `Code.gs`, deploy lại
  (New version), rồi cập nhật lại Secrets trên Streamlit Cloud.
- Vì Web App để "Who has access: Anyone", **bất kỳ ai có URL + đúng API Key đều gọi được** —
  API Key chính là lớp bảo vệ duy nhất, nên cần đủ dài/ngẫu nhiên và giữ kín.
- Tài khoản Google dùng để deploy Apps Script nên là tài khoản có quyền hạn phù hợp
  (không nhất thiết là tài khoản cá nhân của 1 người cụ thể — có thể tạo 1 tài khoản
  dịch vụ nội bộ dùng chung cho việc này nếu công ty có).
