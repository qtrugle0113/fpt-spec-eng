# Giao diện làm mới

Đợt thay đổi `002-ui-refresh` giữ nguyên sáu menu và nghiệp vụ; dùng nền xám nhạt, sidebar/panel trắng, màu nhấn teal. Download template và mở Airflow có hình thức button, giữ link và hành vi tải/tab. Không thêm hoặc đổi API.

## Sử dụng

- Dashboard: bộ lọc ở đầu trang, tám thẻ tổng quan trên một hàng khi đủ1280px, Recent runs trước biểu đồ/thông tin bổ sung.
- Table Management: wizard gọn phía trên, lịch sử uploads và creation jobs cạnh nhau trên desktop.
- DAG Builder: định nghĩa và xác nhận deployment cùng cột; lịch sử bên cạnh; File Sources phía dưới. Tất cả bước review, cảnh báo và authority giữ nguyên.
- Connections/DAG Monitoring: bộ lọc theo hàng, dữ liệu gọn, các đích Airflow có button rõ ràng.
- Settings: trường chia hai cột trên desktop, hướng dẫn nằm cùng trường, thông tin ứng dụng ở panel riêng.
- Mobile: mở menu bằng Open menu, form chuyển một cột. Bảng rộng cuộn ngang ngay trong vùng bảng; có thể focus vùng bảng rồi dùng phím mũi tên. Các thông tin vẫn đầy đủ nên màn hình nhỏ còn cần cuộn dọc.

Button chính có nền teal; phụ có viền; destructive vẫn đỏ. Trạng thái có nhãn chữ; focus bàn phím rõ. Backend/Airflow lỗi hoặc dữ liệu stale vẫn được báo đúng, không thay bằng dữ liệu mẫu.

## Chạy và kiểm chứng

Xem [quickstart](../../specs/002-ui-refresh/quickstart.md) và [báo cáo kiểm chứng](../testing/ui-refresh-20261115.md). Preview phục vụ source đã build, độc lập với frontend demo cũ; không có rollout/deploy trong đợt này.

Trong môi trường đã kiểm chứng, Node đúng phiên bản nằm `.tools/node-ui/node.exe`; để dùng các lệnh npm với Node này trong PowerShell tại repo:

```powershell
$env:Path = (Join-Path (Get-Location) '.tools/node-ui') + ';' + $env:Path
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend run test:ui
```

Không cần công cụ đặc biệt này nếu máy đã có Node22.23.4 trong PATH. Dependency theo lock; không có dependency giao diện mới.

## Airflow admin/admin

Feature003 bổ sung yêu cầu bắt buộc admin/admin cho Airflow local/demo và thay thế hạn chế trước đây của feature002. Xem [hướng dẫn tài khoản local](local-airflow-admin.md) để cập nhật demo cũ, khởi tạo mới và restore. Service account/operator và dữ liệu hiện hữu giữ nguyên; bootstrap thường không reset mật khẩu tùy chỉnh.
