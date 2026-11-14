# Khởi động và chạy luồng mẫu

**152/152task hoàn tất; T014_FULL/T152 PASS** theo Constitution2.0.0: nghiệm thu
baseline local có rủi ro đã biết, không phải security-clean/production-ready.
Review2026-11-16, hết hạn2026-11-23T00:00:00+09:00.

## Baseline nghiệm thu theo Constitution2.0.0 — 2026-11-14

Chủ dự án đã phê duyệt [quyết định nghiệm thu có rủi ro đã biết](../../docs/decisions/t014-owner-review-20261114.json).
Security scan giữ nguyên findings; disposition là `OWNER_ACCEPTED_KNOWN_RISKS`,
không phải security-clean hoặc production-ready. Phạm vi một operator, loopback,
dữ liệu tổng hợp; review2026-11-16 và hạn2026-11-23T00:00:00+09:00, không gia hạn
tự động. Artifact/finding mới không kế thừa approval. Mọi kiểm thử chức năng,
secrets, an toàn dữ liệu và recovery vẫn bắt buộc trước khi đóng T014/T152.
Các checkpoint BLOCKED trước sửa đổi này là lịch sử, không tự đổi kết quả scan.

## Phạm vi

Hướng dẫn này dành cho một operator local trên Podman/Linux containers. Runtime đã kiểm
trên Podman WSL Linux/amd64 với Compose provider 5.6.0; Docker chưa được nghiệm thu theo
bằng chứng này. Không đưa ứng dụng loopback lên Internet.

Bản demo hiện có: ứng dụng <http://localhost:23000>, Airflow
<http://localhost:28080>, readiness <http://localhost:28000/api/v1/health/ready>.
Không xóa hoặc đổi volumes của demo. Khi cần môi trường sạch, dùng project/checkout riêng.

Lượt tiếp tục14/11/2026 trên máy hiện tại đã có demo READY và full workflow UI,
Airflow, đối soát dữ liệu đích PASS. Project cụ thể đọc từ `.tools/local-demo.json`.
Trạng thái mới nhất, runtime/provider và các gate còn mở tại
[checkpoint14/11](../../docs/testing/product-resume-20261114.md).

T140 đã PASS full fresh startup/restart/persistence/fail-closed trên Podman
client5.8.3/server5.8.9 và Compose5.6.0; T151 sample pack đã hoàn tất.
Gate full security/T152 còn BLOCKED; [bằng chứng](../../docs/testing/continuation-20261114.md).

## Điều kiện đầu vào

- Podman engine/machine đang chạy, Compose provider đúng phiên bản đã công bố.
- Checkout ở thư mục gốc repo, quyền pull/build images và đủ tài nguyên/cổng cho stack.
- Không cần tạo `.env`, chạy migration/seed thủ công, hoặc cài Python/Node trên host.
- Mặc định stack mới dùng frontend `localhost:3000`, backend `localhost:8000` và Airflow
  `localhost:8080`; kiểm tra Compose config nếu đã cấu hình cổng khác.

## Khởi động

Từ PowerShell tại repo:

```powershell
podman compose up --build -d
podman compose ps -a
Invoke-RestMethod http://localhost:8000/api/v1/health/ready
```

Lệnh đầu tiên khởi động stack và initialization tự động. Đợi init hoàn tất, services khỏe
và readiness báo `READY`; container ở trạng thái running hoặc HTTP liveness không chứng minh
Airflow và dependencies đã sẵn sàng. Nếu init lỗi, giữ nguyên volumes và xem logs/service
health trước khi thử lại. Không dùng `down --volumes`, `prune` hoặc reset để né lỗi.

Ứng dụng local không yêu cầu login. Airflow UI/API có xác thực riêng; credentials không
được lấy từ application API hoặc chép vào logs. Database không publish cổng host mặc định.

## Luồng mẫu

1. Mở Connections, kiểm tra các connection mẫu PostgreSQL/MySQL và chạy Test Connection.
   Kết quả phải đến từ database thật; password không được trả lại.
2. Tải Table Definition mẫu trong Table Management. Upload, validate, review DDL rồi xác
   nhận tạo bảng. Bảng đã có không bị tự DROP hoặc ALTER.
3. Trong File Sources, tải customers CSV/TXT mẫu, xem preview và validate toàn file.
   Preview giới hạn số dòng; nó không thay cho full-file validation.
4. Tải ETL Definition mẫu trong DAG Builder. Chọn nguồn/đích, kiểm mapping, load policy và
   lịch; preview rồi deploy. DAG mới ở trạng thái paused cho đến khi operator xác nhận.
5. Trigger manual run hoặc xác nhận lịch riêng. Theo dõi run trong Monitoring/Airflow;
   đối soát row count và giá trị dữ liệu đích, không chỉ dựa vào trạng thái task success.
6. Mở Dashboard để kiểm inventory, run history và completeness. Dữ liệu unavailable, stale
   hoặc incomplete phải được hiển thị rõ, không diễn giải thành số 0.

APPEND có thể tạo duplicate khi tạo run mới. UPSERT cần key duy nhất phù hợp. FULL_REFRESH
chỉ được thực hiện sau xác nhận đúng target/revision/scope; quyền `allow_empty` cần xác nhận
riêng. Revoke không hủy transaction đã admission. Xem [Excel Definition](../../docs/excel-definitions.md),
[triển khai DAG](../../docs/operations/dag-deployment.md) và
[xử lý sự cố](../../docs/operations/troubleshooting.md) trước khi xử lý lỗi hoặc recovery.

## Dữ liệu và recovery

Metadata, uploaded files, generated DAGs, logs, staging và keyring dùng volumes bền. Restart
không được tạo key mới hoặc reset dữ liệu. Khi secret/key mất, giữ volumes và phục hồi bản
đúng; không seed lại để bỏ qua lỗi decrypt. Khi commit chưa rõ, giữ Run ID và staging
`PROTECTED`, rồi reconciliation trước retry. Backup/restore cần giữ metadata, keyring/secrets,
uploads và artifacts liên quan trong một snapshot nhất quán; restore phải kiểm tra ở namespace
cô lập trước khi cho phép ghi.

## Kiểm chứng và giới hạn

Full UI-to-Airflow workflow, database routes, parser, retry và FULL_REFRESH recovery đã có
evidence trên stack local; chi tiết mới nhất tại
[kiểm chứng 2026-11-14](../../docs/testing/continuation-20261114.md). T140 đã PASS
toàn selector: fresh startup, restart extraction/commit/FULL_REFRESH, persistence và
fail-closed, cleanup0. T151 sample pack đã hoàn tất. T146 PostgreSQL/MySQL concurrency
đã PASS; lượt memory mới có22.000hàng/174parts, payload1.441.792.000bytes và peak RSS
102.817.792bytes với budget512MiB.

T014_FULL security gate vẫn `BLOCKED`; local exception không phải security PASS hoặc MVP
acceptance. Dùng các runner/fixtures cô lập trong
[hướng dẫn kiểm thử](../../docs/operations/testing.md); không chạy failure injection trên
demo hoặc dữ liệu người dùng. Không tuyên bố MVP hoàn thành khi mandatory task/gate còn mở.
