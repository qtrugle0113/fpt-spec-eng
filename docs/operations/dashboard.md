# Đọc Dashboard

Dashboard lấy inventory và run history từ Public API Airflow, không query bảng
metadata nội bộ Airflow. Tám KPI phân biệt DAG với execution. `Active DAGs` là
workflow hiện hoạt động và unpaused; `Paused DAGs` không đồng nghĩa run đã hủy.

Date filter dùng ngày lịch bao gồm cả hai đầu trong IANA timezone đã chọn, tối đa
366 ngày. Timestamp dùng start time, fallback queue/created time, không dùng
logical date để giả thời điểm execution. Để trống timezone dùng Default Timezone
trong Settings. Inventory hiện tại và Lifetime history không bị date filter đổi.

Success Rate = successful / (successful + failed); không có denominator thì hiển
thị `Not available`. Queued/running/other vẫn được tính trong Total DAG Runs.
Schedule groups phân biệt lịch hiện tại của DAG với lịch bất biến của từng run;
run thiếu lịch sử revision được phân loại Unknown, không đoán theo lịch hiện tại.

Chọn **Refresh dashboard** để bỏ qua cache server. **Auto Refresh** dùng interval
trong Settings; dữ liệu cache server tối đa30giây. Kết quả có thời điểm cập nhật,
completeness và danh sách trường không khả dụng. `Stale data` giữ thời điểm cũ;
outage không tạo bộ số0 hoặc snapshot thành công mới. API tổng hợp đủ pagination,
phát hiện trang thiếu hoặc total thay đổi và trả trạng thái không đầy đủ.

Recent runs có liên kết **View run details** tới đúng DAG/run trong Monitoring.
Last successful run xét toàn bộ lịch sử trong ownership scope, độc lập date filter.
Next scheduled runs chỉ hiển thị forecast Airflow cung cấp; paused không tự unpause.
