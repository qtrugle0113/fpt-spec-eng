# Cấu hình mặc định workspace

Mở **Settings**, chỉnh giá trị rồi chọn **Save settings**. API lưu bền trong
application PostgreSQL và yêu cầu If-Match của toàn bộ bản cấu hình. Nếu có phiên
khác sửa trước, UI yêu cầu **Reload settings** rồi review lại; không ghi đè bằng
revision cũ và không optimistic update.

| Trường | Giới hạn và phạm vi |
| --- | --- |
| Default Batch Size | 1–10.000 dòng; mặc định ban đầu1.000. Chỉ dùng khi validation workbook mới có Batch Size trống; giá trị workbook tường minh được ưu tiên. |
| Dashboard Refresh Interval | 5–3.600 giây; mặc định30. Có hiệu lực ở chu kỳ refresh tiếp theo, khi bật Auto Refresh. |
| Default Timezone | IANA timezone, mặc định UTC. Dashboard dùng khi không nhập timezone filter. Workbook vẫn yêu cầu Timezone tường minh. |
| Staging Retention | 1–365 ngày; mặc định7. Không xóa artifact được bảo vệ cho recovery. |

Revision/config đã validate hoặc deploy giữ nguyên giá trị, không bị Settings
thay đổi hồi tố. Preview đọc lại workbook để kiểm tra dependency nhưng giữ batch
size đã resolve trong revision bất biến. Muốn thay cấu hình workflow, upload và
validate revision mới theo quy trình DAG Builder.

Airflow Connectivity Status và Application Information chỉ đọc. Không public
retry/chunk settings ngoài hợp đồng. Lỗi kết nối không tự đổi defaults hoặc reset
database. Reload sau lỗi lưu để đối chiếu trạng thái thực trước thử lại.
