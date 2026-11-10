# Tạo, triển khai và chạy DAG từ workbook

## Bản chạy thử hiện có

Ứng dụng tại <http://localhost:13000/dag-builder>, API tại
<http://localhost:18000/api/v1/health/ready>, Airflow tại <http://localhost:18080>.
Đây là bản local chạy source hiện tại trên dependency images có sẵn, không thay
nghiệm thu image mới hoặc gate T014_FULL. Monitoring/Dashboard/Settings còn thuộc
Phase7, chưa được công bố hoàn thành.

Project `aat-dag_builder-e2e-6f3a6830` có volumes riêng. Khởi động lại:

```powershell
$env:PODMAN_COMPOSE_PROVIDER=(Resolve-Path .tools/docker-compose-5.6.0.exe).Path
podman compose -f .tools/compose-aat-dag_builder-e2e-6f3a6830.json -p aat-dag_builder-e2e-6f3a6830 up -d --no-build frontend airflow-scheduler airflow-dag-processor
```

Dừng bằng `podman compose -f .tools/compose-aat-dag_builder-e2e-6f3a6830.json -p aat-dag_builder-e2e-6f3a6830 down`.
Không thêm `--volumes`; dữ liệu, uploads, keys và recovery evidence phải được giữ.

## Luồng thao tác

1. Trong Connections, test connection nguồn và đích. Bản local có `pg_etl` và
   `mysql_etl`; không đưa mật khẩu vào workbook.
2. Chọn **Download ETL Definition template**. Điền Excel theo schema1.0;
   DAG ID duy nhất, nguồn/đích thực, mapping và load policy được kiểm soát.
3. **Upload ETL workbook** → **Validate ETL workbook**. Nếu lỗi, đọc mã lỗi và
   sheet/dòng/cột. `TARGET_BUSY` nghĩa là target có writer; đợi rồi validate lại.
   `ETL_REVISION_EXISTS` yêu cầu mở upload gốc trong **ETL workbook history**.
4. Kiểm nguồn, đích, mapping, khóa, schedule/timezone/catchup và load policy.
   Chọn **Review schedules and load policies** rồi xác nhận từng phạm vi.
5. Khi cần support objects, đọc SQL và xác nhận riêng trước **Confirm and deploy
   workflows**. Ghi file chưa phải thành công; chỉ DEPLOYED sau bằng chứng parse,
   owner, revision và version. PARSE_ERROR/timeout/unknown không phải DEPLOYED.
6. DAG mới paused. Xác nhận **Enable manual execution** hoặc **Activate schedule**.
   **Pause future scheduling** không hủy run đã bắt đầu.
7. Xác nhận **Run workflow now**. Operation SUCCEEDED chỉ xác nhận lệnh trigger;
   dùng **Open Airflow** để xem trạng thái run/task thực tế và kết quả ETL.

FR-067 đã được làm rõ: manual trigger không tự unpause. Nếu DAG còn paused,
run giữ queued cho tới khi operator xác nhận unpause riêng. Không cần submit run
mới; giữ reservation/identity cũ. Cron FULL_REFRESH vẫn cần SCHEDULED authority
để bật lịch; ONCE không thay quyền đó.

Các workbook test nằm trong `.tools/dag-e2e-fixtures/`, cùng `index.json` ghi DAG ID.
Mở lại upload đã validate từ history thay vì upload lại cùng cấu hình. Sample pack
chuẩn của repository vẫn cần nghiệm thu riêng; tải template thành công không chứng
minh toàn bộ sample workflow đã chạy.

## Quyền FULL_REFRESH

Deploy không tự cấp quyền thay thế dữ liệu. Chọn ONCE cho một manual run;
SCHEDULED chỉ cho schedule đã chốt, không dùng thay ONCE. Bật **Allow a valid
empty dataset to empty the target** cần acknowledgment riêng, mặc định tắt.
Nguồn lỗi không được coi là dataset rỗng hợp lệ.

Quyền lưu trên server và xem lại được từ trình duyệt mới. ONCE reserve trước khi
gửi lệnh Airflow, retry giữ đúng run; sau CONSUMED, run mới cần quyền mới.
Revocation chặn admission mới, không hủy transaction đã admission và không xóa
bằng chứng phục hồi. Thay revision/scope/target yêu cầu review và quyền mới.

## Timeout và phục hồi

Giữ request identity khi mất response; không double submit bằng key mới để né
pending/unknown. Dùng **Refresh saved operation**, **Refresh deployment results**
và **Reconcile this deployment** khi server cho phép. Nếu vẫn unknown, không tự
ghi lại file hoặc xóa staging/ledger. Không sửa constraints hoặc xóa volumes để
làm hết lỗi.

## Bằng chứng

[Checkpoint tiếp tục](../testing/product-resume-20261110.md) ghi selector và kết
quả thực tế. Playwright kiểm desktop1440/mobile390, invalid workbook, validation
retry, cấp/list/detail/revoke quyền qua trình duyệt mới, deploy/activation/trigger.
Host verifier đối chiếu public Airflow success, binding/metrics và giá trị target;
không dùng trạng thái Operation thay kết quả ETL.
