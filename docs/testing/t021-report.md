# T021 — ORM lịch sử parser và revision cho ETag

**Hoàn thành T021 trong phạm vi ORM source/constraints đã kiểm trên PostgreSQL thật.**
T014_FULL vẫn BLOCKED, security FAIL_WITH_APPROVED_LOCAL_EXCEPTIONS. Chưa triển khai T022
trở đi hoặc parser/upload API. [Kết quả và hashes](t021-results.json),
[phạm vi local](../decisions/t021-local-scope.json), [môi trường](t021-environment.json).

## Thay đổi và truy vết

- [FileParserRevision](../../packages/aat_metadata/models/file_parsers.py) lưu đầy đủ cấu hình,
  UUID, revision, UTC created_at và config_sha256; unique(file_id, revision), FK file RESTRICT.
  PostgreSQL sinh hash từ cấu hình thực, từ chối hash đầu vào sai; trigger chặn UPDATE mọi
  field của snapshot bằng SQL trực tiếp và ORM, kể cả identity/hash/created_at.
- [UploadedFile](../../packages/aat_metadata/models/definitions.py) thêm revision bắt đầu1,
  tăng tại DB trên mỗi UPDATE. SQLAlchemy dùng version cũ trong UPDATE và nhận version mới
  từ DB, từ chối ORM write dựa trên version cũ. Đây là primitive ETag, chưa phải nghiệm thu
  HTTP If-Match/status412 hoặc repository concurrency T028.
- CSV/TXT có composite FK deferred từ (parser_file_id, parser_revision) tới history cùng file;
  thiếu snapshot tại COMMIT hoặc trỏ nhầm file/revision đều không hợp lệ. parser_file_id do
  DB tính, XLSX không dùng delimited parser. Snapshot1 phải khớp parser ban đầu.
- Đổi parser lưu revision2 rồi đổi con trỏ trong cùng transaction. Tests xác minh ETag tăng,
  content checksum/size và snapshot ban đầu/revision1 không đổi. Không cho con trỏ lùi.
  Con trỏ hiện hành được FK RESTRICT bảo vệ khỏi xóa; history cũ vẫn bất biến khi UPDATE.
- DefinitionIssue.scope đã có từ T020, tái sử dụng regression về workbook/cell location.
  Không áp dụng lại patch hoặc thêm trường trùng.
- Data Model được làm rõ trước implementation: conditional composite FK cho CSV/TXT,
  ETag version và cách hash. Hash dùng SHA256 UTF-8 của PostgreSQL JSONB array text, theo
  [encoding, delimiter, header_present, quote_char, escape_char, null_token]. SQL NULL escape
  khác chuỗi rỗng; token NULL là text nguyên vẹn, không diễn giải thành dữ liệu NULL tại ORM.

Truy vết T021: FR-011–FR-017/FR-020/FR-092. ORM chỉ lưu và bảo vệ metadata; semantic parsing,
preview/full validation, dependency invalidation và active/recovery admission thuộc T063/T067/T042.
Không dùng kết quả ORM để tuyên bố những service đó đã đúng.

## Kiểm thử và bằng chứng

```powershell
python -X utf8 tests/tools/run_metadata_foundation.py --file-parsers-orm --phase red
python -X utf8 tests/tools/run_metadata_foundation.py --file-parsers-orm --phase green
python -X utf8 tests/tools/run_metadata_foundation.py
python -X utf8 tests/tools/run_metadata_foundation.py --authorization
```

Driver tái sử dụng test infrastructure hiện có, chỉ thêm selector T021. PostgreSQL17.11
trên tmpfs256MiB/internal network, runner512MiB; không published ports hoặc mount volumes,
secrets, engine socket hiện hữu. Tất cả bảng do production Base.metadata thật tạo trong
DB cô lập. Không mock DB, tạo bảng thay thế, skip hoặc giảm assertions.

| Tiêu chí | Kết quả | Bằng chứng |
| --- | --- | --- |
| Prerequisites/checklists/expiry/baseline/controls | PASS;16/16 và48/48, không extension hooks | [Scope](../decisions/t021-local-scope.json), [môi trường](t021-environment.json) |
| Tests trước implementation | RED đúng nguyên nhân:14 FAIL thiếu FileParserRevision;31 regression PASS | [RED](t014-round2-logs/local-t021-orm-red.log) |
| T021 ORM và affected T019/T020 | PASS47/47:16 T021,15 T019,16 T020 | [GREEN](t014-round2-logs/local-t021-orm-green.log), [fixture](t021-fixture-results.json) |
| Cấu hình/hash/NULL/Unicode/uniqueness/FK/immutability | PASS | [Tests](../../tests/integration/test_file_parser_models.py), cùng GREEN |
| Commit thật và session mới đọc history/con trỏ/ETag | PASS | test_committed_file_and_parser_history_survive_new_sessions |
| Snapshot mới giữ checksum/content và snapshot cũ | PASS | test_edit_appends_snapshot_and_advances_etag_preserving_content |
| T019/T020 assertions hiện có | PASS31/31, không sửa assertions | Cùng GREEN; gồm dependency thật và DefinitionIssue.scope |
| T016 | 1 PASS/6 FAIL RED như trước | [Log](t014-round2-logs/local-t016-foundation-red.log) |
| T017 | 28 FAIL RED thiếu T031 như trước | [Log](t014-round2-logs/local-t017-authorization-red.log) |
| T018 | Tái sử dụng PASS; source hashes không đổi | [Kết quả T018](t018-results.json) |
| Binding/recovery giữ parser revision cũ, chặn sửa khi active | NOT_RUN; model/service chưa tồn tại | T025/T042/T067, không tạo schema giả |
| T029 migrations/T034 product foundation | NOT_RUN | ORM create_all không thay Alembic/init acceptance |
| Build/scan mới, CI/clean checkout source mới | NOT_RUN | Không build/deploy/commit, không gán scan cũ cho source mới |

RED ghi14 cases ban đầu; sau đó bổ sung2 cases commit/session và Unicode/hash, GREEN cuối47cases.
T016/T017 vẫn thất bại thực; không tính expected RED thành chức năng PASS. Các nhánh concurrency,
lock order và runtime role của T017 chưa chạy tới repository, vẫn NOT_RUN.

## Baseline và giới hạn

HEAD `b0c947d23f1e9c23e9ce0a57b634f9e7a4c7b4ab`, source thay đổi local chưa commit.
Ba candidate IDs được xác minh nguyên vẹn, không mở rộng approval:

- Security stage: `97e3d67d1f0a8468f2d2409683f2d6c54e5cd415a162a3df6cff022c9809ec16`.
- Airflow final: `399adacf113fd269d4dd5d587b956a9167bc02ef8f656d3ff9ef94e11039e2fc`.
- Backend-tests runner: `89f5d1e6dcc4ec2c55188404b2a4433aae7f8e87e5b8b7c84e9c0023694aaea4`.

PostgreSQL fixture: `87507379f5ed1bca39a781c2f03da05f368e9f92b69c670e9a87cdf32cc9cf03`.
Runner chỉ copy source để kiểm; image và services triển khai sẵn chưa chứa T021 mới.
Hash approval mapping và các source kiểm soát T014 không đổi, constraints upstream không đổi.
Quyền local giữ hạn **2026-11-23T00:00:00+09:00**, review **2026-11-16**; chỉ một operator,
dữ liệu tổng hợp/loopback theo controls đã duyệt. Không có gia hạn hoặc phê duyệt mới.

T029 phải đưa constraints/functions/triggers/conditional FK vào migrations thật. Retention/GC
không được xóa history đang được current pointer hoặc binding/recovery tham chiếu; các FK
binding/recovery riêng còn phải triển khai và kiểm khi có model thật. T021 không chứng minh
recovery safety hoặc toàn bộ file lifecycle. Không chạy migration trên volumes hiện hữu.

Bước tiếp theo là T022: ETLDefinition/Revision/Mapping ORM, tests trước trên PostgreSQL cô lập.
Chưa triển khai T022 trong lượt này; foundation và luồng sản phẩm xuyên suốt vẫn chưa nghiệm thu.
