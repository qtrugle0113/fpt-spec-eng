# Nghiên cứu giao diện

**Ngày**: 2026-11-15

## Bố cục và công nghệ

- **Quyết định**: Giữ React/Vite, sửa CSS chung, thêm link button dùng lại.
- **Cơ sở**: `.connections-page` chưa có padding đồng nhất. Sidebar tối260px, header74px và panel padding lớn gây dư chiều cao. Metrics min-width180px gây nhiều hàng.
- **Phương án khác**: Framework mới tăng phạm vi/rủi ro; thu nhỏ chữ hoặc giấu cảnh báo không đáp ứng yêu cầu.

## Mật độ và thứ tự đọc

- **Quyết định**: Sidebar216px, header56px, padding panel16px, gap12–16px, chữ bảng13px, control>=36px. Metrics tám cột khi đủ1280px, bốn cột tablet và hai cột mobile. Recent runs đứng trước thông tin bổ sung. Hai lịch sử upload/job của Tables cạnh nhau dưới wizard để giảm vùng trống; deployment đứng cùng cột với ETL wizard để không bị lịch sử dài đẩy xuống. Mobile một cột và giữ toggle.
- **Cơ sở**: Đưa dữ liệu đầu tiên vào768px nhưng vẫn dễ đọc. Không thêm vùng cuộn dọc bảng.
- **Phương án khác**: Cuộn lồng nhau làm khó keyboard và theo dõi dữ liệu.

## Tích hợp và kiểm chứng

- **Quyết định**: Preview loopback riêng phục vụ build, proxy API thật; fixture lỗi/empty/loading tách riêng.
- **Cơ sở**: Vite chưa có proxy; backend28000, frontend demo23000 đang phục vụ build cũ.
- **Phương án khác**: Deploy demo ngoài phạm vi; mock toàn bộ không chứng minh tích hợp.

## Tài khoản Airflow

- **Quyết định**: Giữ bootstrap/tài khoản, ghi hạn chế theo FR-008.
- **Cơ sở**: `docker/bootstrap/secrets.py` tạo `aat_service`/`operator` với password ngẫu nhiên một lần; `initialized.json` khiến lần sau chỉ kiểm tra rồi return. `airflow/docker/airflow.cfg` dùng SimpleAuthManager; entrypoint đọc password file từ secret volume. Đổi demo hiện hữu đòi hỏi thay secret/tài khoản.
- **Phương án khác**: Opt-in admin/admin cho fresh stack không giúp demo hiện hữu và mở rộng auth/bootstrap ngoài trọng tâm UI. Không mặc định password yếu toàn hệ thống.

Agent nghiên cứu chỉ đọc theo skill plan, không đọc giá trị secret hoặc sửa tài khoản.
