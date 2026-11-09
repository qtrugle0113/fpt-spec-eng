# T019 — Connection/Revision/Secret ORM, 2026-11-09

**Snapshot được thay thế:** lượt T020 đã kiểm PASS nhánh dependency thật còn thiếu và đóng
T019; xem [kết quả hiện hành](t020-report.md). Giữ nội dung PARTIAL dưới đây làm lịch sử.

**15 kiểm tra PostgreSQL PASS; T019 còn mở vì nhánh dependency nghiệp vụ chưa được kiểm thật.**
Không triển khai T020 trở đi. T014_FULL BLOCKED/security FAIL; không đổi ngoại lệ/IDs/hạn local.
[Results/hashes](t019-results.json), [scope](../decisions/t019-local-scope.json).
Quyền local đến2026-11-23 00:00 UTC+09, review16/11; checklists16/16,48/48 PASS, không hooks.

## Source đã triển khai

- [Base](../../packages/aat_metadata/models/base.py): registry ORM chung, repr chỉ chứa ID,
  public projection mặc định từ chối; không tự tạo engine/schema hoặc chạy migrations.
- [Ba models thật](../../packages/aat_metadata/models/connections.py): UUID/timestamps aware,
  normalized_code do PostgreSQL tính lower/trim và unique, POSTGRESQL/MYSQL, revision>=1,
  port1–65535, FK RESTRICT; current_revision phải thuộc đúng connection.
- Revision snapshot endpoint/credential bất biến bằng PostgreSQL trigger, kể cả SQL trực tiếp;
  test_status/tested_at vẫn có thể cập nhật. Secret ciphertext/key_id bất biến; retired_at riêng.
- Data Model đã bổ sung `ConnectionRevision.database_type` **trước** implementation trường này:
  FR-008 yêu cầu sửa type không thay revision/run cũ. Snapshot lấy parent khi ORM insert,
  không đổi Connection API/core/constraints/dependency hoặc topology. Kiểm PG→MYSQL giữ type
  của revision cũ và chặn sửa type snapshot đã PASS. T029 phải đưa trường/guards vào migrations.
- `ConnectionSecret.from_plaintext` tái sử dụng [SecretCodec](../../packages/aat_metadata/secrets/codec.py)
  nguyên vẹn, không rotation/key regeneration. Model kiểm cấu trúc Fernet token; DB có check
  chống plaintext thông thường. Xác thực/decrypt token thật vẫn do codec với keyfile tách riêng,
  không coi regex/shape check là xác minh HMAC hoặc chống privileged writer cố ý giả token.
- Connection/Revision có whitelist `public_dict`; Secret không có public projection.
  Không serialize ORM `__dict__`/generic ORM encoder vào API; DTO/public routes vẫn thuộc task sau.
  SQL engine của fixture ẩn parameters để lỗi constraint không in ciphertext/credentials.

DDL listener chỉ đăng ký guards cho schema do model tạo. **T029 không tự có guards chỉ vì
đã import model**: migration phải đưa đúng constraints/functions/triggers vào upgrade path.
Production app không được dùng create_all thay Alembic.

## Bằng chứng

```powershell
python tests/tools/run_metadata_foundation.py --connections-orm --phase green
python tests/tools/run_metadata_foundation.py
python tests/tools/run_metadata_foundation.py --authorization
```

Driver T016 được mở rộng selector riêng; approved PostgreSQL17.11 và backend-tests image IDs,
internal network/tmpfs riêng, không ports/volumes/secrets hiện có. Schema test do **Base.metadata
của production models thật** tạo, không có hand-written/fake tables để làm test xanh.
Không có Alembic/migrations/seed nghiệp vụ được chạy trên DB hiện hữu.

| Kiểm tra | Kết quả | Bằng chứng |
| --- | --- | --- |
| Tests trước implementation | RED14 đúng thiếu models | [log RED](t014-round2-logs/local-t019-orm-red.log) |
| Constraints/FK/immutability/codec/projection/type snapshot | PASS15/15 | [log GREEN](t014-round2-logs/local-t019-orm-green.log), [tests](../../tests/integration/test_connection_models.py) |
| Secret defaults không cấp đọc cho Airflow/PUBLIC | PASS trong fixture | Cùng log; không thay nghiệm thu grants runtime/backend T030/T031 |
| Sửa code khi chưa có business dependency | PASS | Có owned revision nhưng chưa có Definition/DAG/binding phụ thuộc |
| Chặn đổi code khi có business dependency thật | NOT_RUN | Model phụ thuộc chưa có, không tạo bảng giả hoặc triển khai T020 trái scope |
| T016 regression | 1 PASS/6 FAIL RED không đổi | [log](t014-round2-logs/local-t016-foundation-red.log) |
| T017 regression | 28 FAIL RED thiếu T031, không collection error | [log](t014-round2-logs/local-t017-authorization-red.log) |
| T018 | Tái sử dụng PASS source không đổi | [report](t018-report.md) |
| T029 migrations / T034 foundation | NOT_RUN | ORM DDL tests không thay nghiệm thu migrations/readiness |
| New build/scan/CI/clean checkout | NOT_RUN | Không build/deploy/commit hoặc mở rộng approval |

Lượt kiểm đầu có11PASS/3FAIL do raw SQL đi ngoài savepoint Session; đã sửa test wiring
sang Session.execute (vẫn SQL PostgreSQL thật), không giảm assertions. [Log chẩn đoán](t014-round2-logs/local-t019-initial-savepoint.log).

Fixture T017 được đồng bộ DML với schema thật: bỏ normalized_code generated, key_id32hex,
database_type snapshot. Không đổi assertions/skip tests; kết quả vẫn RED vì repository chưa có.

## Phần còn thiếu và bước tiếp theo

Có code-dependency guard dựa trên foreign keys thật vào Connection/Revision, không coi owned
revision là business dependency. Negative/no-dependency branch đã chạy; positive branch và
dependency-admission concurrency/permissions qua service T042 **chưa nghiệm thu**.
Không đánh `[x] T019` khi chưa có bằng chứng positive branch. T019 hiện PARTIAL, không phải FAIL security mới.

Task tiếp theo có thể là **T020**, vì dependency trong Tasks là T016, không phải T019 đã đóng.
Sau khi T020 có model TableDefinition thật với FK target_connection_revision_id, bổ sung test
T019 chặn đổi code có dependency; chỉ đóng T019 nếu bằng chứng đầy đủ. Không đổi dependencies
hoặc nghiệm thu chỉ để vượt gate. Chưa làm T020 trong lượt này.

Giữ mọi service/data/volume/secrets hiện có; chỉ xóa fixture do driver tạo. Không có image mới;
source mới chưa được đóng wheel/deploy. Public API, role grants hoàn chỉnh, rotation, migration,
recovery và foundation còn phải kiểm ở các task tương ứng.
