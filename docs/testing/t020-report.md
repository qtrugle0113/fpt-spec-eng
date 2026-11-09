# T020 và khép affected T019 — 2026-11-09

**T020 và T019 hoàn thành trong phạm vi ORM source/constraints đã kiểm; T014_FULL BLOCKED/security FAIL.**
Không triển khai T021 trở đi, parser/upload API hoặc DDL tạo/sửa bảng dữ liệu người dùng.
[Results/hashes/exact IDs](t020-results.json), [scope](../decisions/t020-local-scope.json).
Hạn local giữ2026-11-23 00:00 UTC+09/review16/11; không mở rộng approval findings/images.

## Thay đổi

[definitions.py](../../packages/aat_metadata/models/definitions.py) thêm 5 model production:
UploadedFile, DefinitionUpload, DefinitionIssue, TableDefinition và TableColumn.

- Storage key opaque do PostgreSQL sinh, không ghép original_name vào path; CHECK từ chối
  traversal key. Uploaded content/checksum/storage identity và parser snapshot ban đầu bất biến.
  Parser revision/history mới là T021, chưa triển khai hoặc tuyên bố đã kiểm history đầy đủ.
- Definition kind TABLE/ETL, template1.0, trạng thái upload và composite FK gắn đúng file/checksum;
  chỉ VALIDATED với template được hỗ trợ. FK RESTRICT giữ upload/table/column history.
- Issue workbook có location null; cell có sheet/row/column và index bắt đầu1. safe_context
  chỉ whitelist metadata count/limit/type, từ chối raw cell value/credential. Không dùng model
  thay parser validation hoặc tự chứng minh mọi lỗi nghiệp vụ đã safe.
- TableDefinition unique theo upload/physical table identity, không vượt uniqueness bằng
  credential revision mới. Identity được DB tính từ fingerprint/database/schema/table và trả
  lại ORM; thiếu fingerprint hợp lệ bị chặn. Metadata fixture dùng fingerprint tổng hợp;
  **không phải** bằng chứng server/network/dialect identity đã được adapter xác minh.
- Column unique name/ordinal/PK ordinal, constraints type/length/precision/scale, PK không nullable
  và composite PK có thứ tự tương ứng column ordinal. Tagged JSON giữ decimal text lossless,
  phân biệt không default (SQL NULL) với explicit null, chặn float/tag sai/extra expression key.
- Data Model được làm rõ trước implementation: parser snapshot ban đầu, opaque storage key,
  physical_table_identity nội bộ, safe_context whitelist và tagged-default null semantics.
  Không đổi Spec/OpenAPI, task dependencies hoặc chính sách nghiệm thu.

DDL listeners phục vụ ORM DDL trong fixture. T029 phải đưa đầy đủ constraints/functions/triggers
vào Alembic thật; không dùng create_all để migrate hoặc chữa DB hiện hữu.

## T019 đã có bằng chứng còn thiếu

[test_t019_real_table_dependency_blocks_code_change_in_orm_and_sql](../../tests/integration/test_definition_models.py)
tạo TableDefinition thật có FK tới ConnectionRevision thật. UPDATE code bằng SQL trực tiếp
và ORM đều bị từ chối; connection khác không có business dependency vẫn rename được.
15 regression T019 tiếp tục PASS. Do đó đóng phần PARTIAL trước đây và đánh dấu T019 hoàn thành.
Không suy kết quả này thành PASS concurrency/dependency admission của service T042 hoặc grants
runtime/backend hoàn chỉnh T030/T031; các gate đó vẫn phải kiểm riêng.
[Báo cáo T019 cũ](t019-report.md) là snapshot trước khi có model phụ thuộc.

## Kiểm thử

```powershell
python tests/tools/run_metadata_foundation.py --definitions-orm --phase green
python tests/tools/run_metadata_foundation.py
python tests/tools/run_metadata_foundation.py --authorization
```

Tái sử dụng driver T016, chỉ thêm selector T020. Tất cả tables do production Base.metadata
thật tạo trong PostgreSQL tmpfs/network riêng; không mock DB hoặc fake dependency table.
Không mount volumes/secrets/engine socket, không ports, không đổi services/images hiện hữu.

| Tiêu chí | Kết quả | Bằng chứng |
| --- | --- | --- |
| Prerequisites/checklists/scope/expiry/exact IDs | PASS;16/16 và48/48; không hooks | [scope](../decisions/t020-local-scope.json) |
| RED trước T020 implementation | 16 FAIL thiếu definition models,15 PASS T019 | [RED](t014-round2-logs/local-t020-orm-red.log) |
| T020 + affected T019 | PASS31/31 (16 mới,15 regression) | [GREEN](t014-round2-logs/local-t020-orm-green.log), [fixture](t020-fixture-results.json) |
| T019 code có business dependency thật | PASS ORM và SQL | Cùng GREEN, không dùng bảng thay thế |
| T016 | 1 PASS/6 FAIL RED như trước | [log](t014-round2-logs/local-t016-foundation-red.log) |
| T017 | 28 FAIL RED thiếu repository/state T031 | [log](t014-round2-logs/local-t017-authorization-red.log) |
| T018 | Tái sử dụng PASS, source không đổi | [report](t018-report.md) |
| T021 parser history / T029 migrations / T034 foundation | NOT_RUN | Ngoài scope/chưa đủ implementation |
| New build/scan/CI/clean checkout | NOT_RUN | Không build/deploy/commit; không gán scan cũ cho source mới |

Fixture T017 chỉ đổi storage key thành token32hex và validation_status thành VALID để khớp
schema thật; không sửa assertions/skip tests. Kết quả T017 vẫn RED đúng repository chưa có.
Các nhánh concurrency/role trong T017 chưa chạy tới; không được coi là PASS.

## Giới hạn và bước tiếp theo

Đã có **ORM DDL tests**, chưa có Alembic acceptance, target DDL, full runtime hay MVP.
Typed default mới kiểm representation/tag/type, chưa thay semantic parser/dialect validation
của T051/T053/T054. Physical identity còn phụ thuộc verified/canonicalized metadata của adapter.
Không public API hoặc generic ORM serialization; các boundary DTO/service vẫn thuộc task sau.

Bước tiếp theo **T021**: FileParserRevision, UploadedFile.revision/ETag và immutable parser history,
tests trước trên PostgreSQL thật. Giữ content và parser snapshot ban đầu, không mutate binding cũ.
T021 trở đi chưa được thực hiện trong lượt này. Giữ T014_FULL BLOCKED/security FAIL và hạn/thu hồi
local nguyên vẹn. Services, dữ liệu, volumes và secrets hiện có được giữ nguyên.
