# Tiếp tục Phase7 — Monitoring, Dashboard và Settings

Trạng thái tiếp tục ngày2026-11-11 tại [checkpoint](product-resume-20261111.md).
Các đoạn “đang chạy” bên dưới là lịch sử phiên trước; không suy từ đó rằng
Phase6 chưa khép hoặc Monitoring chưa có kết quả.

## Gate đầu vào

T096–T120 đã khép trong phạm vi local đã duyệt. Image delta Phase6 được chủ dự
án duyệt tại `docs/decisions/phase6-local-image-approval.json`; T014_FULL vẫn
BLOCKED, không có blanket approval cho image tương lai hoặc bản bàn giao.
Giữ bản demo cổng13000 và mọi volumes hiện có, không commit/push.

## Monitoring — đang kiểm chứng

- T121 RED: bốn query invalid trả404 vì chưa có route. Evidence `t121-red`.
- T121–T123 lượt đầu9PASS50.610giây trên public Airflow thật: inventory, managed/
  external, run/task, metrics, log attempt. Năm ca DAG Builder được collect do
  import class test; đã sửa import để các lượt sau không collect lặp.
- Safe log contracts3PASS2.053giây: outage không trả inventory rỗng, filters
  invalid và log redaction dùng credential mã hóa thật/giới hạn toàn JSON1MiB.
  Mock chỉ dùng payload lỗi/redaction; positive Airflow/logs có fixture thật riêng.
- Frontend Monitoring build/typecheck PASS, Node22.23.4/npm12.2.2 offline,
  artifact `.tools/aat-frontend-source-ea53ddee`.
- Đang chạy `t121-t125-final` cho primitives qua HTTP/ETag/idempotency và
  `t127-monitoring-e2e` cho desktop/mobile. Chưa có kết quả thì không báo PASS.

## Thiết kế triển khai

Monitoring dùng Public API Airflow, cùng HTTP/JWT client đã pin; toàn bộ logical
read có deadline30giây, pagination kiểm total và concurrency tối đa4. Application
DB chỉ cung cấp ownership/immutable binding/ETL metrics; không mirror run history.
External không có metadata/metrics giả hoặc controls. Lỗi nguồn trả503 thay0.

Task logs lấy đúng attempt/map_index/token, redaction trước hiển thị; known
credentials thay bằng một regex pass để không thay lặp marker. Giới hạn metadata
redaction256KiB và page JSON1MiB, kể cả JSON escaping/envelope; vượt khả năng
redaction thì fail closed. UI không append vô hạn các log pages.

UI review revision/scope trước commands và gọi lại primitives T112/T113, không tạo
scheduler hoặc control implementation thứ hai. ONCE/SCHEDULED và acknowledgment
tách riêng; navigation hủy polling phía client, không hủy công việc server đã nhận.

## Việc tiếp theo

Khép T121–T127 sau live/E2E, cập nhật bản demo bằng source overlay hiện tại.
Tiếp T128–T137 theo dependency; Phase8 chỉ mở sau T132/T137. Giữ source checkpoint
và báo cáo lỗi thực tế, không tự đánh dấu reviewer checklist.
