# T015/T016 sau kích hoạt local — 2026-11-09

**M0 khép; quyền local có hạn đang AUTHORIZED. T014_FULL BLOCKED, security FAIL.**
Chỉ viết tests T015/T016 và test drivers; chưa triển khai model, migration, API hoặc worker Phase 2.
Đây không phải nghiệm thu foundation T034 hoặc sản phẩm chạy nghiệp vụ xuyên suốt.
[Kết quả máy đọc được, source hashes và exact IDs](t015-t016-results.json).

## Quyết định và phạm vi

Chủ dự án xác nhận riêng LEX-003, D3/LEX-079 và mapping 316 lượt C sang ba exact IDs
trong hội thoại hiện tại. [Activation record](../decisions/t014-local-activation.json)
lưu thời điểm ghi nhận thực tế, người duyệt, từng context và hash delta đã review.
Không giả timestamp gửi message; không ghi AI là reviewer. D1/D2/D4 không thay đổi.

- LEX-003 CLOSED_FOR_CONDITIONAL_LOCAL_BUILD_PATH; raw parent vẫn có finding.
- LEX-079 not affected chỉ 12 zlib1g contexts baseline + 3 candidate contexts đã duyệt.
- 147 nhóm C baseline giữ nguyên; mapping bổ sung đúng 316 lượt C trên ba IDs, không blanket waiver.
- Review chậm nhất **2026-11-16**; hết quyền **2026-11-23 00:00 UTC+09**.
- Một operator, synthetic/local/loopback; giữ nguyên owner, controls và điều kiện thu hồi.
- Phạm vi implementation lượt này chỉ T015/T016. Task khác cần lượt tiếp theo.

[Xác minh trước kích hoạt](t014-local-activation-verification.json): source SHA256 khớp,
ba candidate IDs khớp, 8 dịch vụ healthy + 4 init thành công; không privileged/socket mount,
ports chỉ 127.0.0.1. Checklists 16/16 và 48/48 PASS, không extension hooks.
[Bằng chứng bootstrap/scan tái sử dụng](t014-local-gate-results.json) vẫn có hiệu lực
cho image IDs không đổi. Không scan/build lại vì chỉ thêm test source và hồ sơ quyết định.

## T015 — hoàn thành task viết contract harness

[Harness](../../tests/api/test_openapi_contract.py) đọc operations và schemas từ OpenAPI
canonical, không hardcode số lượng. Các story dùng selection riêng; không bắt mọi endpoint
tương lai phải có ngay. JSON Schema 2020-12 kiểm local refs, required/extra fields, format;
writeOnly bị chặn ở response. Status thành công sai không lọt qua default error response.
Header If-Match, UUID Idempotency-Key và response ETag có negative controls.
Assertion không in giá trị payload nhạy cảm.

**PASS 9/9 self-tests**, gồm mutation cố ý thiếu operation/schema/fields/status/header/secret
và positive controls. Đây là PASS của công cụ kiểm contract, không phải PASS các API nghiệp vụ.
[Log](t014-round2-logs/local-t015-contract-harness.log).

Lệnh tái hiện dùng image Airflow candidate đã duyệt, network=none, không mount dữ liệu,
không cài thêm dependency hoặc rebuild image:

```powershell
python tests/tools/run_openapi_contract.py
```

PyYAML 6.0.3 và jsonschema 4.26.0 có sẵn trong image này. Backend runner hiện chưa có
hai thư viện này hoặc contract YAML; wiring selector canonical T034 vào runner cần hoàn tất
trước gate T034, không suy lệnh profile test cũ đã chạy được T015.

## T016 — hoàn thành task viết tests, kiểm thử chức năng còn RED

[Integration tests](../../tests/integration/test_metadata_foundation.py) collect 7 cases,
kết nối PostgreSQL thật, không mock DB hoặc skip thiếu foundation.
[Driver](../../tests/tools/run_metadata_foundation.py) dùng namespace/network internal riêng,
PostgreSQL tmpfs 256 MiB, không published ports, không mount volumes/secrets hiện hữu;
chỉ xóa containers/network do chính driver tạo. Source mới được copy vào runner đã duyệt,
PYTHONPATH trỏ đúng source thử; không thay image tag/ID hoặc wheel của stack đang chạy.

```powershell
python tests/tools/run_metadata_foundation.py
```

Lệnh trả exit code pytest thực tế; hiện **exit 1: 1 PASS, 6 FAIL (RED dự kiến)**.
[Log](t014-round2-logs/local-t016-foundation-red.log), [fixture IDs/results](t016-fixture-results.json).

| Case | Kết quả hiện tại | Phần còn thiếu |
| --- | --- | --- |
| App/Airflow DB isolation | PASS trong disposable role fixture | Không phải nghiệm thu app-init nghiệp vụ |
| Dependency FK RESTRICT | FAIL/RED | Chưa có tables/migrations T019–T029 |
| Operation idempotency unique | FAIL/RED | Chưa có operations |
| Claim SKIP LOCKED, durable state sau reconnect | FAIL/RED | Chưa có operations |
| Hai initializer cạnh tranh, seed không đổi | FAIL/RED | Chưa có T030 app_init.py |
| Safe error envelope qua app thật | FAIL/RED | Bootstrap trả framework detail; T018/T032 chưa có |
| Worker kill/restart không claim unknown side effect | FAIL/RED | Chưa có durable worker T033 |

Nhánh restart đã viết thao tác process kill/start và kiểm heartbeat PID + durable state/attempt,
nhưng **chưa chạy tới nhánh này** vì worker chưa tồn tại. Không coi reconnect test là bằng chứng
worker recovery đầy đủ. Test DSN/worker command/heartbeat được inject trong fixture cô lập;
wiring app-init và worker vào disposable DB cần hoàn tất cùng T030/T033 trước nghiệm thu.
Không thực hiện migrations lên DB/volumes hiện có ở lượt này.

## Gate và bước tiếp theo

| Tiêu chí | Kết quả |
| --- | --- |
| M0 identity/approval/controls/expiry | PASS cho phạm vi conditional local |
| T015 harness | PASS 9/9 |
| T016 authoring/collection/red đúng phần thiếu | Đã hoàn thành task viết tests; chức năng 1 PASS/6 FAIL |
| Foundation T034 | NOT_RUN; chưa đủ implementation |
| CI/clean checkout source mới | NOT_RUN |
| Full scan 21 targets, candidate restart/recovery mới | NOT_RUN; không gán PASS từ R3 |
| T014_FULL/security | BLOCKED/FAIL |

Chỉ đánh dấu T015/T016 là task **viết tests** hoàn thành; không ghi foundation PASS.
Task tiếp theo là T017 viết tests quyền/state/repository, rồi các dependency T018–T034
theo Tasks; chưa triển khai các task đó trong lượt này. Bất kỳ image/dependency/config/trust
boundary mới phải kiểm affected gates và mapping ngoại lệ trước khi tiếp tục nghiệm thu.
