# Hợp đồng UI và static

- Một link dạng button có accessible name `Download User Guide`, icon tải ẩn với screen reader, trong thanh chung của sáu route.
- URL cùng origin: `${BASE_URL}user-guide/Airflow-Automation-Tool-Huong-dan-su-dung.html`; download filename đúng tên trên.
- GET trả 200, Content-Type HTML, bytes trùng bản gốc; không nhận SPA index.html thay tài liệu.
- Không đổi URL hiện tại, không gửi request ghi dữ liệu, không phụ thuộc backend/Airflow.
- Tab có focus nhìn thấy; Enter tải được. Nút cao tối thiểu 36px, nhìn thấy ban đầu, không tràn ngang ở desktop/mobile/320px.
- File tải mở offline: lang=vi, đủ 16 chapter và 12 ảnh decode được, không cần mạng để hiển thị.
- Docker COPY public trước build; dist giữ nguyên file. Không thêm API hoặc sửa Nginx.
