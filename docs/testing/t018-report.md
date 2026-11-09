# T018 — common schemas và health routing, 2026-11-09

**T018 hoàn thành ở phạm vi source và affected checks. T014_FULL BLOCKED/security FAIL.**
Không triển khai T019 trở đi; không build/deploy image mới hoặc thay dịch vụ hiện có.
[Results/hashes/exact image IDs](t018-results.json), [scope lượt này](../decisions/t018-local-scope.json).
Quyền local giữ hạn2026-11-23 00:00 UTC+09/review16/11; không mở rộng findings/image approval.

## Thay đổi

- [common.py](../../backend/src/aat_api/schemas/common.py): extra fields forbidden;
  UUID; datetime nhận RFC3339 có timezone, chuẩn hóa UTC và serialize Z, không nhận epoch/naive;
  PageQuery default50/max200/offset>=0; Page total/next_offset bắt buộc có mặt nhưng nullable,
  không dùng0 giả cho tổng chưa biết; Issue/ErrorBody/ErrorResponse/Health theo contract.
- [health.py](../../backend/src/aat_api/routes/health.py) và [main.py](../../backend/src/aat_api/main.py):
  `/api/v1/health/live` trả200 `{"status":"ALIVE"}`, operation IDs đúng canonical OpenAPI.
  `/api/v1/health/ready` trả503 ErrorResponse `FOUNDATION_NOT_READY` và UUID request_id mới.
  Chưa có DB/head/worker/Airflow readiness service T034; không fake READY/dependency checks.
- [Bootstrap probe](../../docker/bootstrap/health.py) đổi expectation liveness sang ALIVE,
  giữ probe DB/Airflow/worker nguyên vẹn. Image regression test cũng kỳ vọng ALIVE/ready503
  khi build image từ source này; không chấp nhận đồng thời payload legacy để vượt test.
- Thêm schema boundary tests, real ASGI contract tests dùng T015 harness và Uvicorn HTTP/probe test.
  Không triển khai global exception/logging/origin middleware T032; unknown route vẫn là framework404
  và test safe-error nền tảng vẫn RED như trước.

Canonical OpenAPI/Data Model/Spec và upstream constraints không sửa. PageQuery dùng minimum1
của component Limit trong canonical; không thay các story-specific query definitions.

## Tests trước implementation và affected checks

```powershell
python tests/tools/run_t018_checks.py --phase green
python tests/tools/run_t018_checks.py --phase green --backend
python tests/tools/run_metadata_foundation.py
```

[Driver](../../tests/tools/run_t018_checks.py) dùng approved images, network=none, source copy
và PYTHONPATH; cwd `/tmp` để test source mới không bị tests cũ trong image che khuất.
Không tải package, không mount dữ liệu/secrets/engine socket. Dependency FastAPI0.136.3,
Pydantic2.13.5/httpx0.28.1 khớp ở hai images; contract image có sẵn PyYAML/jsonschema của T015.

| Tiêu chí | Kết quả | Bằng chứng |
| --- | --- | --- |
| Prerequisites/checklists/hooks/scope/expiry/IDs | PASS;16/16,48/48, không hooks | [scope](../decisions/t018-local-scope.json) |
| RED trước implementation | 9 FAIL T018, 9 PASS T015 | [log RED](t014-round2-logs/local-t018-red.log) |
| Schema/API/HTTP/probe + T015 | PASS19/19 | [log GREEN](t014-round2-logs/local-t018-green.log) |
| Backend image dependencies, source schema/HTTP/probe | PASS7/7 | [log backend](t014-round2-logs/local-t018-green-backend.log) |
| Regression T016 | 1 PASS/6 FAIL RED như trước | [log](t014-round2-logs/local-t016-foundation-red.log) |
| T017 | RED28 theo evidence cũ; không chạy lại | [report](t017-report.md); source/repository không đổi |
| T034 product foundation readiness | NOT_RUN | Chưa đủ implementation |
| Backend wheel/image build và image bootstrap test mới | NOT_RUN | Chưa build; source-copy checks không thay build acceptance |
| Scan/CI/clean checkout mới | NOT_RUN | Không có commit/image mới để nghiệm thu |

Backend test-driver lần đầu bị module tests cũ trong cwd image che source mới;
đã sửa cwd `/tmp` và chạy lại thành công. [Log chẩn đoán ban đầu](t014-round2-logs/local-t018-backend-driver-initial.log).
Đây là lỗi test wiring đã khép, không bỏ tests hoặc sửa expectation để báo PASS.

## Phạm vi nghiệm thu và việc còn lại

PASS trên source được copy vào container của exact IDs đã duyệt, **không phải** image mới
đã đóng gói hoặc triển khai. Services đang chạy vẫn dùng code/image baseline cũ; payload live
của chúng chưa đổi. Không gắn source T018 cho scan/CI lịch sử. Khi build image mới phải kiểm
wheel inclusion, startup/probe và affected scans/mapping trước khi nhận baseline mới.

T016 vẫn thiếu tables/migrations T019–T029, init T030, middleware T032 và worker T033.
T017 state/repository/concurrency/role vẫn chờ T023–T031; các nhánh NOT_RUN chưa được nghiệm thu.
Không có quyết định security mới cần hỏi cho source-only checks này. T014/security không PASS.

Task tiếp theo **T019**: Connection/Revision/Secret ORM theo Data Model, tests trước cho
constraints và serializer/secrets. Không triển khai T019 trong lượt này; giữ gate T034 và
không chạy migrations trên volumes hiện hữu.
