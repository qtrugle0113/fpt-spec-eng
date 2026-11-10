# Theo dõi và điều khiển DAG

Mở **DAG Monitoring** để lọc DAG ID, ownership, trạng thái pause và trạng thái run
gần nhất. Chọn **View workflow** rồi chọn run để xem task, attempt, metrics ETL
và log. Thời gian trên màn hình Monitoring hiển thị UTC.

`Managed` chỉ được xác định sau khi đối chiếu metadata ứng dụng với DAG Airflow.
Tag `aat` riêng lẻ không cấp quyền điều khiển. DAG `External` chỉ đọc; ứng dụng
không tạo metrics ETL hay liên kết Definition giả cho chúng.

Để trigger hoặc đổi pause, chọn command rồi review revision và tác động trước
xác nhận. `Accepted` hoặc Operation đang pending không có nghĩa ETL đã chạy xong.
Khi timeout hoặc mất phản hồi, kiểm tra Operation và run identity cũ trước thử lại.
Ứng dụng đối soát cùng identity để tránh tạo run trùng.

Theo FR-067 đã duyệt, manual run của DAG paused nằm queued cho tới khi operator
xác nhận unpause riêng. Không tự bật lịch để chạy manual. Pause chỉ ảnh hưởng
scheduling tương lai, không hủy transaction hoặc run đang chạy, không thu hồi
quyền FULL_REFRESH. ONCE chỉ áp dụng run đã gắn; SCHEDULED chỉ áp dụng lịch trong
scope đã xác nhận. Thu hồi quyền không đồng nghĩa hủy transaction đã được admission.

Chọn đúng task, map index và attempt để đọc log. Log được che credentials và phân
trang có giới hạn; UI không nối vô hạn các trang. Khi log không khả dụng, kiểm tra
lý do hiển thị và mở Airflow bằng liên kết được cấu hình. Không đưa secret vào
ảnh chụp, báo cáo hoặc log vận hành.

Airflow unavailable trả lỗi hoặc dữ liệu stale/unknown; danh sách trống không thay
cho lỗi kết nối. Navigation dừng polling browser, không hủy công việc server đã nhận.

Bằng chứng hiện có: `docs/testing/resume-20261110/t121-t125-final/` và
`t127-approved-fr067-e2e/` (8 E2E desktop/mobile PASS). Các lượt này dùng source
overlay trên dependency images đã duyệt, chưa phải nghiệm thu image Phase7 mới.
