# Đề xuất làm rõ FR-067 cho Airflow3.3.2

## Bằng chứng thực tế

FR-067 hiện yêu cầu: “paused managed DAG được manual trigger sau xác nhận mà không
cần unpause lịch”. Baseline Airflow3.3.2 nhận POST manual run nhưng scheduler không
thực thi khi DagModel vẫn paused. Đã đối chiếu mã cài trong image được duyệt:
`DagRun.get_queued_dag_runs_to_set_running` và
`DagRun.get_running_dag_runs_to_examine` đều yêu cầu `DagModel.is_paused == false()`.
Đây là đọc source chính thức trong image; không query/sửa Airflow metadata DB.

Fixture `t127-monitoring-e2e` quan sát qua public API:

| DAG | Native pause | Manual run | State |
| --- | --- | --- | --- |
| aat_browser_append_desktop_8f109056 | true | manual__aat_f7d73356-da4f-4ed9-b18d-90ced87ae381 | queued |
| aat_browser_append_mobile_0d2cf5f5 | true | manual__aat_d05c6ada-2834-43b8-bca4-347be8dba8e5 | queued |

Operation trigger SUCCEEDED chỉ là nhận lệnh, không phải ETL success. UI hiện đọc
đúng queued, không gán row metrics bằng0 hoặc báo success giả.

## Phương án đề nghị

Giữ nguyên Airflow3.3.2, dependency/security baseline và mọi guard dữ liệu. Sửa
phần FR-067 về paused thành:

> Manual trigger tạo đúng một run có identity bền. Khi DAG paused, run có thể
> queued và chỉ thực thi sau thao tác unpause được xác nhận riêng. Ứng dụng không
> tự unpause hoặc kích hoạt lịch khi nhận manual trigger. UI phải nêu rõ điều này.

Manual-only DAG không có recurring schedule, nhưng native pause vẫn chặn execution.
Với cron FULL_REFRESH, unpause/activate vẫn cần SCHEDULED authority đúng scope;
ONCE chỉ giữ reservation cho manual run, không được dùng để bật lịch. Replay cùng
request giữ run cũ. Không tự giải phóng hoặc chuyển reservation khi run queued.

Nếu duyệt, đồng bộ Spec/Plan/Tasks/contracts/docs và E2E: tạo manual khi paused,
xác minh queued/native paused vẫn true, operator review/xác nhận unpause riêng,
rồi kiểm actual Airflow success/target/metrics. Pause không hủy run đang chạy.

## Phương án giữ nguyên yêu cầu

Giữ FR-067 thì chức năng execution-manual-khi-paused bị BLOCKED trên baseline
hiện tại. Không tạm unpause ngầm, không thao tác Airflow metadata DB, không dựng
scheduler ngoài Airflow hoặc đổi version khi chưa có quyết định riêng.
Tiếp tục các task độc lập; không dùng E2E queued để nghiệm thu execution success.

## Trạng thái

ĐÃ ĐƯỢC CHỦ DỰ ÁN DUYỆT ngày2026-11-10: “Duyệt queued rồi unpause rõ ràng”.
Quyết định được ghi tại `docs/decisions/fr067-paused-manual-approval.json`.
Không đổi dependency/security baseline hoặc BR-08.
