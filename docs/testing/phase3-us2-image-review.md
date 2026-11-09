# Review image Backend Connections — 2026-11-09

**Owner đã xác nhận mapping đúng Backend ID dưới đây trong hội thoại ngày 2026-11-09.**

Phản hồi: “Xác nhận mapping Backend theo hồ sơ”. Giữ controls/hạn hiện hữu, không
mở rộng sang image khác; T014_FULL vẫn BLOCKED.

Source Connections đã kiểm 23/23 tests trên PostgreSQL/MySQL thật, gồm HTTP,
credential/revision/dependency, handshake timeout và schema. Foundation regression
47/47 PASS. Frontend TypeScript/build PASS. Đã build ba artifact cho E2E thực tế:

| Artifact | ID đầy đủ | HIGH/CRITICAL | Delta so baseline |
| --- | --- | ---: | --- |
| Backend runtime | `18fa537b59b8405da24bed0295e1234ec84e52d3538197cf25b50b1385a3b7e2` | 42 (40 HIGH, 2 CRITICAL) | 0 thêm / 0 bớt |
| Frontend | `3dc8e51aa5c51190eddd9aa374e6d6d18568a31512a668e0cba6e3e3fe8497da` | 0 | 0 / 0 |
| E2E runner | `960bb3edb6e256a94ec5bf29373e54354d922cc8a4b391d0bd1bed9e074d7415` | 0 | 0 / 0 |

So sánh tuple advisory/package/installed version/severity/fixed version với baseline
trong `t014-r3-security.json`. Backend có cùng danh sách HIGH/CRITICAL; image ID đổi
vì đã đóng gói source Connections mới. Không dùng xác nhận test-runner cũ thay cho
runtime image này, không coi findings khớp là security PASS.

Đề nghị xác nhận mapping ngoại lệ local hiện hữu sang **đúng Backend ID trên** để
khởi chạy fixture E2E production Compose và tiếp tục T045/T046. Giữ controls hiện
hữu, review2026-11-16 và hạn2026-11-23 00:00 UTC+09. Không mở rộng cho image khác
hoặc public deployment; không miễn trừ secrets/auth/data integrity; T014_FULL còn BLOCKED.
Các image trước đã được xác nhận vẫn có hiệu lực, không đề nghị xác nhận lại.

Fixture được chuẩn bị tại `tests/tools/run_connections_e2e.py`: project/network/
volumes riêng, network internal, không publish ports, không dùng dữ liệu/secrets
hiện hữu. Credential test chỉ cấp hai file đích vào container E2E; log công bố
redact hai giá trị này; cleanup đúng project sau khi kiểm thử.

- [Scan mới](phase3-us2-image-security.json).
- [Danh sách findings và delta](phase3-us2-image-delta.json).
- [Quy tắc review](../proposals/t014-conditional-local-gate.md):
  “owner phải ký delta trước mốc tiếp theo”.
