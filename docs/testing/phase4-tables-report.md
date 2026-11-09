# Checkpoint quản lý bảng — 2026-11-09

**Hiện hành: T047–T060 đã hoàn thành; tiếp T061/T062 Phase5 File Sources.**
Source18/18PASS, foundation regression47/47PASS, E2E cuối10/10PASS desktop1440 và
mobile390, cleanup0; ảnh đã xem ở cả độ phân giải gốc. Backend giữ đúng ID owner
đã xác nhận. Frontend cuối `a7be4d553fbdc2a7725bd5a2ba4d269b5b19a40486b46b9361e08db2c609c4e5`
build/typecheckPASS, scan0HIGH/CRITICAL theo `phase4-ui-mobile-security.json`.
Evidence cuối: `resume-20261109/tables-e2e.log`, `tables-e2e-results.json`,
`tables-visual-review.json`. Các trạng thái chờ/NOT_RUN dưới đây là lịch sử.

Connections đã hoàn thành đến T046. Phase 4 đã có parser ZIP/OpenXML an toàn,
validator Table schema1.0, download artifact gốc, upload streaming/checksum,
validation durable, typed preview/confirmation, DDL PostgreSQL/MySQL và worker
per-table, job history cùng introspection tách riêng stored definition.

## Bằng chứng hiện có

- RED trước triển khai: `resume-20261109/t047-red.log`, `t048-red.log`;
  route thiếu trả 404, parser/DDL thiếu báo assertion đúng chức năng chưa có.
- `tables-core-expanded-green.log`: 16/16 PASS trên PostgreSQL17.11/MySQL8.4.13
  thật; bao gồm 20 workbook sai, ZIP/formula, template/sample gốc, PK ghép,
  lossless defaults, existing-table preservation, stale token, history/filter,
  MySQL partial permission failure và mất phản hồi sau DDL thật.
- Job UNKNOWN lưu bền và replay cùng key không gọi DDL lần hai; account đích bị
  khóa chỉ làm live verification UNAVAILABLE, không làm mất stored definition.
- Frontend TypeScript/build PASS trong `.tools/frontend-us4-build.log`.
- Hồi quy foundation: 47/47 PASS trong
  `resume-20261109/phase4-regression-fixed/phase2-foundation-core-green.log`.
- Bộ nghiệm thu source cuối **18/18 PASS** trong
  `resume-20261109/tables-acceptance-source-green.log`, gồm DRIFTED/UNAVAILABLE,
  alias admission tranh quyền, key mới không được vượt UNKNOWN, giữ lịch sử khi
  dependency đổi và lossless defaults trên cả hai DB.
- Đối chiếu read-only **45/45 file** Backend trong installed wheel khớp source
  đã kiểm; `resume-20261109/tables-packaged-source.json`. Chỉ create/copy artifact,
  không chạy Backend image mới trước owner mapping.
- T047–T058 đã cập nhật checkbox theo các bằng chứng này; T059/T060 vẫn mở.

Các lượt FAIL trước đó được giữ riêng: lỗi test runner thiếu dependency, extension
storage key, tham số SQL finish operation thiếu kiểu, implicit auto-increment và
format GRANT trong fixture. Không sửa kỳ vọng để bỏ qua lỗi sản phẩm.

## Mốc tiếp theo

T059/T060 còn mở cho đến khi production artifacts mới được scan/review đúng ID,
E2E desktop1440/mobile390 PASS và kiểm tra ảnh thực tế. Đã có `tables.spec.ts`,
giao diện wizard/history/detail, driver `--suite tables` và fixture workbook mẫu.
E2E mới hiện **NOT_RUN**; không kế thừa kết quả Connections hay scan image cũ.
Scan mới ghi vào `phase4-us4-image-security.json`; chỉ xác nhận mapping khi có ID,
delta và bằng chứng cụ thể. T014_FULL vẫn **BLOCKED** theo quyết định hiện hành.

Scan cuối: Backend `ac5e0ed3fe3e3ebb87176e62de2ec7a93668e6600b1b98d4814d5891c199252c`
có42HIGH/CRITICAL, không thêm/bớt so baseline; Frontend
`d2fcfc0e9894fa898d507da155f35a1f7024524e12c0caa0f8db141d531efee6` có0HIGH/CRITICAL.
Owner đã xác nhận “Xác nhận mapping Backend Table theo hồ sơ” cho đúng Backend
theo `phase4-us4-image-review.md`. Đã ghi quyết định vào review/delta và bắt đầu
fixture E2E mới; chỉ cập nhật PASS/FAIL theo kết quả chạy thật.

Sau khi owner xác nhận, ghi nhận quyết định vào review/delta rồi chạy:

```powershell
python -X utf8 tests/tools/prepare_table_fixtures.py --image 6b65b34da83e6f271d2f8f892d08f7fefad31ad06e040f134b7f39d0bc97123e
python -X utf8 tests/tools/run_connections_e2e.py --suite tables --backend-image ac5e0ed3fe3e3ebb87176e62de2ec7a93668e6600b1b98d4814d5891c199252c --frontend-image d2fcfc0e9894fa898d507da155f35a1f7024524e12c0caa0f8db141d531efee6 --e2e-image 960bb3edb6e256a94ec5bf29373e54354d922cc8a4b391d0bd1bed9e074d7415 --airflow-image b5e9745e9bd836d28b7c085b653a315eaa34832f1cb92491cdf9c8f73cf1d52e --postgres-image c93823be91b7c9219c9e97423fdd9ffbe36ce2423fbfa099ecf7355bd69a2dce --mysql-image 76ef5ef385ae6bea4acbf835f439350abb6903eab6a3ccba5082d3d56a4be2bf --evidence-dir docs/testing/resume-20261109
```

Lệnh E2E sẽ tạo fixture mới có network/volumes riêng, không port public. Xem log,
results, ảnh ở `.tools/tables-e2e-artifacts/` rồi sửa lỗi trong phạm vi và kiểm lại;
không đóng T059/T060 trước khi đủ bằng chứng. Sau đó tiếp tục T061 theo dependency.

Không commit/push, không deploy Internet, không xóa dữ liệu/volume hiện hữu.
Nếu gián đoạn, đọc checkpoint này, git diff và fixture-results mới nhất trước khi
chạy lại; chỉ tiếp tục task chưa đủ bằng chứng. Không reset công việc đã có.

## E2E sau xác nhận owner

Lượt đầu:6PASS/4FAIL, đã giữ log/results `tables-e2e-http-uuid-failure.*`, cleanup0.
Lỗi thật phía browser: `crypto.randomUUID` không có trên HTTP origin nội bộ. Đã
thêm fallback UUIDv4 bằng `crypto.getRandomValues`, không dùng Math.random hoặc
mock browser API để vượt lỗi. Frontend mới
`8e80e7e089b0c256a8f8ffd4736f53a18012035061367155436e7f67d91837f3` đã build/typecheck
PASS và scan0HIGH/CRITICAL trong `phase4-ui-httpfix-security.json`; Backend vẫn
đúng ID owner đã xác nhận, không cần hỏi lại mapping. Đang chạy lại E2E trên
fixture mới; chưa đóng T059/T060 cho đến khi có PASS và ảnh đã kiểm.
