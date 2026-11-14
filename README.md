# Airflow Automation Tool

## Baseline nghiệm thu theo Constitution2.0.0 — 2026-11-14

Chủ dự án đã phê duyệt [quyết định nghiệm thu có rủi ro đã biết](docs/decisions/t014-owner-review-20261114.json).
Security scan giữ nguyên findings; disposition là `OWNER_ACCEPTED_KNOWN_RISKS`,
không phải security-clean hoặc production-ready. Phạm vi một operator, loopback,
dữ liệu tổng hợp; review2026-11-16 và hạn2026-11-23T00:00:00+09:00, không gia hạn
tự động. Artifact/finding mới không kế thừa approval. Mọi kiểm thử chức năng,
secrets, an toàn dữ liệu và recovery vẫn bắt buộc trước khi đóng T014/T152.
Các checkpoint BLOCKED trước sửa đổi này là lịch sử, không tự đổi kết quả scan.

## Trạng thái hiện tại

**Cập nhật14/11/2026:** [báo cáo tiếp tục](docs/testing/continuation-20261114.md)
ghi build hardening, Unit/API225+SDK4, Airflow10case và memory stress đã PASS.
Podman client5.8.3/server5.8.9, Compose5.6.0 là môi trường đo hiện tại.
T140/T151 đã hoàn tất, hiện150/152tasks. T014_FULL/T152 vẫn BLOCKED.

**Cập nhật 2026-11-13.** Bản demo local đang chạy tại <http://localhost:23000>; Airflow tại
<http://localhost:28080>; readiness tại <http://localhost:28000/api/v1/health/ready>.
Ứng dụng local không yêu cầu đăng nhập; chỉ sử dụng trên loopback.

Luồng giao diện Connections → Table Definition → file/ETL Definition → deploy DAG →
Airflow run → Monitoring/Dashboard đã được kiểm trên PostgreSQL/MySQL và dữ liệu đích thật.
Fresh-stack test cũng đã khởi động stack bằng một lệnh và chạy sample workflow. Xem
[checkpoint 13/11](docs/testing/product-resume-20261113.md) để biết image, fixture và
phạm vi chính xác; không xóa hoặc đổi volumes của demo khi chạy regression.

Trong `tasks.md`, 147/152 task đã đánh dấu hoàn thành. T139, T144, T145, T147, T148, T149 và T150
đã khép với regression evidence mới. T140 còn thiếu restart giữa các phase ETL; T146
concurrency PostgreSQL chưa ổn định; T140, T146, T151–T152 còn mở. T014_FULL vẫn BLOCKED
bởi security gate, vì vậy MVP chưa được nghiệm thu.
Ngoại lệ local hiện hành có review due 2026-11-16 và hết hạn 2026-11-23; không được coi
ngoại lệ này là security PASS hoặc tự gia hạn.

## Dùng ứng dụng

- [Khởi động và vận hành local](docs/operations/local-portable.md)
- [Xử lý sự cố](docs/operations/troubleshooting.md)
- [Quản lý connections](docs/operations/connections.md)
- [Tạo bảng và DAG bằng Excel](docs/excel-definitions.md)
- [Triển khai và chạy DAG](docs/operations/dag-deployment.md)
- [Quản lý file nguồn](docs/operations/file-sources.md)
- [Theo dõi và ETL engine](docs/operations/etl-engine.md)
- [Kiến trúc](docs/architecture.md), [API](docs/api.md), [Excel Definition](docs/excel-definitions.md)

Demo hiện tại dùng các cổng 23000/28000/28080. Stack Compose mới dùng cổng mặc định
3000/8000/8080 trừ khi được cấu hình khác. Không chạy Compose mới trên project/volumes
của demo đang dùng.

## Khởi động stack mới

Runtime đã nghiệm thu local là Podman trên WSL Linux/amd64 với Compose provider 5.6.0.
Engine và provider phải sẵn sàng trước; checkout mới cần chuẩn bị provider theo
[hướng dẫn local](docs/operations/local-portable.md). Từ thư mục gốc repo, lệnh khởi động:

```powershell
podman compose up --build -d
```

Đợi healthcheck và readiness; container đang chạy chưa có nghĩa ứng dụng đã sẵn sàng.
Khởi động lại không kèm `--volumes` để giữ metadata, secrets, DAG và file. Không dùng cấu
hình local loopback này để public ra Internet. PASS trên Podman không chứng minh Docker đã
được nghiệm thu.

## An toàn và kiểm chứng

Ứng dụng chỉ dành cho một operator local. Airflow có xác thực riêng; credentials database
không được trả lại qua API hoặc ghi vào DAG/log/XCom. Giữ nguyên keyring/secrets và staging
khi có lỗi; commit chưa rõ phải reconciliation trước khi retry. Quy trình xử lý và khôi phục
được mô tả trong [troubleshooting](docs/operations/troubleshooting.md).

Kết quả regression gần nhất gồm full UI workflow, tám route ETL, retry/commit-loss,
FULL_REFRESH recovery, language/security/contract checks và response limits. T146 còn có
PostgreSQL failure không giải thích được; T147 chưa có Airflow large-data evidence. Trạng
thái từng selector và lệnh chạy nằm trong [checkpoint hiện tại](docs/testing/product-resume-20261113.md)
và [tasks Spec-Kit](specs/001-airflow-automation-tool/tasks.md). Không suy PASS từ code,
image scan cũ hoặc task checkbox chưa có bằng chứng.
