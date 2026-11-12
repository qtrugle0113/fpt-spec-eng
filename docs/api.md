# Sử dụng API ứng dụng

## Nguồn hợp đồng

API công khai dùng prefix `/api/v1`. Schema thiết kế tại
[OpenAPI](../specs/001-airflow-automation-tool/contracts/openapi.yaml) và quy tắc
chi tiết tại [REST API](../specs/001-airflow-automation-tool/contracts/rest-api.md).
Backend xuất `/openapi.json`; giao diện Swagger `/docs` và ReDoc bị tắt trong
implementation hiện tại. Không coi schema thiết kế là bằng chứng server đã chạy.

Readiness: `GET /api/v1/health/ready`; liveness:
`GET /api/v1/health/live`. Với demo portable, backend dùng cổng28000 và frontend
cổng23000; xác minh bằng `.tools/local-demo.json` và readiness thực tế.

## Thao tác và phản hồi

Các nhóm endpoint phục vụ connections, templates, definition uploads, tables,
files/parser revisions, DAG deployment/control, replacement authorizations,
monitoring, dashboard và settings. Dùng đường dẫn/body chính xác trong OpenAPI;
không suy resource UUID từ DAG ID hoặc dùng definition revision thay parent ID.

- PATCH cấu hình gửi `If-Match` từ ETag đã đọc; stale trả412.
- Lệnh dài gửi `Idempotency-Key` UUID; cùng key/payload trả operation cũ,
  cùng key khác payload bị409. Khi mất response, giữ key để đối soát.
- Confirmation token gắn scope có hạn10phút; token hết hạn không tự giải phóng
  ONCE hoặc cho phép tạo run thay thế.
- 202 chỉ xác nhận tiếp nhận operation. Poll operation đến trạng thái cuối;
  trigger thành công chưa chứng minh ETL thành công hoặc dữ liệu đích đúng.
- List có pagination; đọc đủ `next_offset`, không coi trang đầu là toàn bộ dữ liệu.

Các trạng thái cần phân biệt: SUCCEEDED, PARTIALLY_SUCCEEDED, FAILED và
NEEDS_RECONCILIATION. Khi kết quả side effect chưa rõ, không gửi key mới để né
reconciliation. Lỗi public dùng message tiếng Anh, không trả credentials hoặc
exception từ driver.

## Ranh giới truy cập

Ứng dụng local một operator không có login riêng; Airflow có xác thực riêng.
Mutating requests từ browser phải có origin hợp lệ. Password connection chỉ
ghi, không có endpoint đọc lại plaintext. Không đặt password trong URL/workbook.

`/internal/runtime/bind` là endpoint nội bộ có service token và xác minh identity
Airflow; frontend không được dùng làm API công khai. Backend gọi public API
Airflow `/api/v2`, không query bảng nội bộ để điều khiển DAG/run.

Xem [hướng dẫn workflow](operations/dag-deployment.md) và
[kiểm thử](operations/testing.md) để xác minh hành vi thực tế.

