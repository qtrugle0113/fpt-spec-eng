# T017 — viết tests state/repository quyền, 2026-11-09

**Task viết tests hoàn thành; chức năng quyền chưa PASS. T014_FULL BLOCKED/security FAIL.**
Chỉ thêm test source, mở rộng selector trong driver T016 và hồ sơ theo dõi.
Không tạo model/repository/migration, không triển khai T018 trở đi.

## Quyền thực hiện và baseline

[Scope lượt này](../decisions/t017-local-test-scope.json) ghi yêu cầu hiện tại của chủ dự án
cho riêng T017. Không sửa/mở rộng findings hoặc image IDs đã duyệt tại
[activation](../decisions/t014-local-activation.json).
Hạn local vẫn **2026-11-23 00:00 UTC+09**, review chậm nhất **2026-11-16**.
Chưa hết hạn tại thời điểm kiểm; runtime source hashes và ba candidate IDs vẫn khớp.
Checklists requirements16/16, spec-quality48/48 PASS; không có extension hooks.
.gitignore/.dockerignore giữ nguyên; không có cấu hình ESLint/Prettier/publishing cần bổ sung ignore.

## Thay đổi

- [State tests](../../tests/unit/test_authorization_states.py): 12 cases cho quyền ONCE,
  SCHEDULED, RESERVED/CONSUMED/CLOSED/REVOKED/INVALIDATED, kiểm chứng commit/terminal,
  RunIntent timeout/reconcile và Admission outcome/không dùng lại.
- [Repository tests](../../tests/integration/test_authorization_repository.py): 16 cases,
  PostgreSQL thật; idempotency cùng payload/khác payload, hai transaction tranh ONCE,
  concurrent replay cùng request, identity ổn định, terminal grant, admission/revoke,
  unknown commit, epoch mới sau rollback/writer kết thúc, SCHEDULED scope/manual/backfill,
  allow_empty và runtime role không cấp quyền/sửa scope/xóa evidence.
- Hai lock-order tests giữ row lock rồi quan sát `pg_blocking_pids` và `FOR UPDATE NOWAIT`:
  authorization trước intent/binding; intent trước binding sau khi đã giữ authorization.
- [Driver dùng lại T016](../../tests/tools/run_metadata_foundation.py) thêm `--authorization`;
  selector/log/results riêng, không tạo runner image/harness DB thứ hai.
  Role thử `aat_etl` được tạo nhưng không cấp giả quyền nghiệp vụ để làm test PASS.

T031 chưa có internal API. Tests mô tả **seam nội bộ dự kiến**, không thay public REST API:
pure transitions trong authorizations/replacement_runs và `AuthorizationRepository(connection)`
dùng caller transaction; business refusal ValueError. Chi tiết tham số ở docstrings/tests.
Implementation T031 có thể dùng adapter tương đương nếu API nội bộ khác, nhưng không giảm
assertions nghiệp vụ, concurrency hoặc permission. Không tự thêm implementation để tests xanh.

Fixture chỉ INSERT/UPDATE dữ liệu tổng hợp vào tables do migrations thật tạo; không
CREATE TABLE/create_all hoặc mock repository/DB. Các fixture records kiểm authorization,
không tuyên bố workbook/config đó đã được nghiệm thu ETL. Wiring migrations và fixture DML
vào schema thật cần được kiểm khi T023–T031 có implementation; hiện chưa chạy tới DML này.

## Lệnh và kết quả

```powershell
python tests/tools/run_metadata_foundation.py --authorization
```

Driver dùng internal network và PostgreSQL tmpfs riêng; không published ports, không mount
volumes/secrets hiện hữu. Chỉ xóa containers/network do chính lượt test tạo; image IDs giữ nguyên.
Runner đọc test/source mới qua copy + PYTHONPATH, không rebuild hoặc cài dependency.

| Tiêu chí | Kết quả | Bằng chứng |
| --- | --- | --- |
| Prerequisites/checklists/scope/hạn/source/images | PASS | [scope/baseline](../decisions/t017-local-test-scope.json) |
| Collect T017 | PASS, 28 cases | [log](t014-round2-logs/local-t017-authorization-red.log) |
| Chức năng T017 | FAIL/RED, 28 tests | Thiếu T031 authorization/replacement repository/state; không collection error |
| Probe PostgreSQL trong 16 integration cases | PASS trước assertion thiếu repository | [fixture](t017-fixture-results.json), [log](t014-round2-logs/local-t017-authorization-red.log) |
| Hai transaction/lock ordering/admission/role DML | NOT_RUN | Test bodies đã viết nhưng bị chặn ở setUp thiếu T031 |
| Regression selector T016 | 1 PASS, 6 FAIL/RED không đổi | [log](t014-round2-logs/local-t016-foundation-red.log) |
| T034 foundation gate | NOT_RUN | Thiếu implementation T018–T034 |
| CI/clean checkout source mới | NOT_RUN | Source chưa commit; không kế thừa CI R3 |
| Build/scan mới | NOT_RUN | Không đổi runtime/dependency/image; tái sử dụng bằng chứng đã duyệt |
| Full T014/security | BLOCKED/FAIL | Conditional authorization không phải full PASS |

[Results máy đọc được và hashes](t017-results.json).

## Việc còn lại

Không còn quyết định security cần hỏi lại trong phạm vi viết tests T017 này.
Chỉ đánh dấu task **viết tests** T017 hoàn thành vì collect/RED đúng phần chưa triển khai,
không ghi permission/concurrency/BR-08 đã nghiệm thu. Các branches NOT_RUN phải chạy thật
trước gate foundation T034. T016 vẫn RED như trước; không sửa tiêu chí hoặc skip tests.

Bước tiếp theo **T018**: tests trước cho common schemas/envelopes/health routing, rồi
implementation đúng Tasks/OpenAPI. Chưa thực hiện T018 hoặc các task khác trong lượt này.
Mọi dependency/image/config/trust-boundary mới phải kiểm affected gates và phạm vi approval;
quyền local không tự mở rộng sang artifacts hoặc môi trường mới.
