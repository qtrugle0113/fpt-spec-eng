# Delta Airflow trên máy mới — 2026-11-09

**Owner đã xác nhận mapping cho ID Airflow bên dưới trong hội thoại ngày 2026-11-09.**

Phản hồi: “Xác nhận mapping Airflow theo hồ sơ”. Giữ controls/hạn hiện hữu, không
mở rộng sang image khác. Hai image backend-tests/PostgreSQL trước vẫn được duyệt.

Airflow3.3.2 build thành công từ Dockerfile/locks hiện có; pip check PASS, core3.3.2,
PyYAML6.0.3/jsonschema4.26.0 xác minh thật. T015 contract harness 9/9 PASS network=none.

| Image | ID đầy đủ | HIGH/CRITICAL | Thêm/bớt so baseline |
| --- | --- | ---: | --- |
| Airflow candidate | `b5e9745e9bd836d28b7c085b653a315eaa34832f1cb92491cdf9c8f73cf1d52e` | 110 (105 HIGH, 5 CRITICAL) | 0/0 |

Scan hoàn tất theo digest scanner đã khóa. So sánh advisory/package/installed
version/severity/fixed version với image baseline
`399adacf113fd269d4dd5d587b956a9167bc02ef8f656d3ff9ef94e11039e2fc`:
không thêm hoặc bớt tuple HIGH/CRITICAL. Không coi đây là security PASS.

Đề nghị owner xác nhận mapping ngoại lệ local hiện hữu sang **đúng ID trên** để
khởi chạy Airflow trong fixture cô lập cho T034: PostgreSQL tmpfs riêng, network
internal, không publish ports, dữ liệu tổng hợp, không mount volume/secret hiện hữu.
Giữ controls, review2026-11-16 và hạn2026-11-23 00:00 UTC+09. Không miễn trừ
secrets/auth/data integrity hoặc mở rộng cho image khác; T014_FULL vẫn BLOCKED.

Đây là image bổ sung cần cho readiness; xác nhận hai ID backend-tests/PostgreSQL
trước đó được giữ nguyên và không phải xác nhận lại.

- [Scan và findings](phase2-resume-airflow-security.json).
- [Delta và ID baseline](phase2-resume-airflow-delta.json).
- [Quy tắc review image mới](../proposals/t014-conditional-local-gate.md):
  “owner phải ký delta trước mốc tiếp theo”.
