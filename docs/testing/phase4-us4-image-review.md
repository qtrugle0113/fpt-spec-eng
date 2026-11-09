# Review image Backend quản lý bảng — 2026-11-09

**Trạng thái: owner đã xác nhận mapping đúng Backend ID bên dưới trong hội thoại.**

Phản hồi: “Xác nhận mapping Backend Table theo hồ sơ”. Giữ nguyên controls và hạn
23/11 theo hồ sơ; xác nhận chỉ áp dụng đúng ID này. Tiếp tục E2E T059/T060.
Không sử dụng xác nhận Backend Connections cũ thay cho artifact đã đóng gói code
quản lý bảng mới. Các ID PostgreSQL, Airflow, test-runner đã được owner xác nhận
trước đó vẫn giữ hiệu lực; không đề nghị xác nhận lại các ID đó.

| Artifact | ID đầy đủ | HIGH/CRITICAL | Delta so baseline R3 |
| --- | --- | ---: | --- |
| Backend runtime | `ac5e0ed3fe3e3ebb87176e62de2ec7a93668e6600b1b98d4814d5891c199252c` | 42 (40 HIGH, 2 CRITICAL) | 0 thêm / 0 bớt |
| Frontend cuối, sửa UUID HTTP và cột ID mobile | `a7be4d553fbdc2a7725bd5a2ba4d269b5b19a40486b46b9361e08db2c609c4e5` | 0 | 0 / 0 |

Scan Trivy0.76.1 mới trên archive của đúng ID, không dùng engine socket, không
ignore-unfixed hoặc bỏ severity. Đối chiếu tuple advisory/package/installed
version/severity/fixed version với `t014-r3-security.json`. Findings Backend
không đổi; đây vẫn là security **BLOCKED** ngoài ngoại lệ local, không phải
security PASS. Frontend không cần ngoại lệ HIGH/CRITICAL.

## Bằng chứng triển khai

- Source API/parser/DDL: **18/18 PASS**, PostgreSQL17.11 và MySQL8.4.13 thật,
  `resume-20261109/tables-acceptance-source-green.log` và fixture results.
- Bao gồm 20 workbook lỗi, ZIP/formula, template/sample gốc, typed defaults trên
  hai DB, DATETIME(6), PK ghép, bảng hiện hữu, partial permission failure, schema
  drift, account lock, stale confirmation và giữ lịch sử khi đổi dependency.
- Mất phản hồi sau DDL MySQL thật lưu UNKNOWN; replay cùng key không chạy lại,
  key mới cũng bị chặn khi physical table còn active/uncertain. Hai connection
  alias tranh admission thật chỉ một request được nhận.
- Foundation regression **47/47 PASS** trong
  `resume-20261109/phase4-regression-fixed/phase2-foundation-core-green.log`.
- Frontend TypeScript/build PASS; đã sửa giới hạn proxy để hỗ trợ workbook10MiB
  cộng multipart framing, có browser test upload trên1MiB chờ chạy.
- Read-only đối chiếu45/45 file Backend trong installed wheel khớp source đã kiểm,
  `resume-20261109/tables-packaged-source.json`; không execute image mới để làm
  bước đối chiếu này.
- Production Compose fixture đã qua preflight; `tables-e2e-results.json` ghi
  **PREPARED_NOT_RUN**, không publish port hoặc dùng dữ liệu/secrets hiện hữu.
- Đã có browser tests desktop1440/mobile390, workbook fixtures công khai và tài
  liệu vận hành. Chưa tuyên bố T059/T060 hoàn thành khi E2E chưa chạy.

## Quyết định cần owner

[Quy tắc repo](../proposals/t014-conditional-local-gate.md) yêu cầu:
“owner phải ký delta trước mốc tiếp theo”. Đề nghị xác nhận mapping ngoại lệ local
hiện hữu sang **đúng Backend ID ac5e…9252c ở trên**, giữ nguyên controls, review
2026-11-16 và hạn 2026-11-23 00:00 UTC+09, để chạy E2E T059/T060 rồi tiếp tục các
task đủ dependency. Không mở rộng ngoại lệ sang ID khác, không miễn trừ
secrets/auth/data integrity hoặc nghiệm thu bằng bằng chứng. T014_FULL vẫn BLOCKED.

- [Scan đúng artifact](phase4-us4-image-security.json).
- [Scan Frontend sau sửa UUID trên HTTP](phase4-ui-httpfix-security.json): thay
  Frontend d2fc…fee6 của lượt E2E đầu. Backend đã được owner duyệt giữ nguyên ID;
  Frontend mới vẫn không cần ngoại lệ HIGH/CRITICAL.
- [Scan Frontend cuối sau kiểm ảnh mobile](phase4-ui-mobile-security.json).
  Artifact cuối đã E2E10/10PASS desktop/mobile, cleanup0; T059/T060 đã khép.
- [Findings và delta](phase4-us4-image-delta.json).
- [Checkpoint Phase4](phase4-tables-report.md).
- [Hướng dẫn vận hành](../operations/table-definitions.md).
