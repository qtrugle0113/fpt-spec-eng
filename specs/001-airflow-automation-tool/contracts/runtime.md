# Hợp đồng ETL runtime và phục hồi

## Package và một execution

`aat-etl-engine==0.1.0` và `aat-metadata==0.1.0` là wheel chung giữa backend và custom
Airflow image, runtime chỉ import cần thiết. Airflow wrapper sử dụng Task SDK và gọi đúng
một task `execute_etl` để giữ connection snapshot/native target lock trong cùng process.
Không chia extract/load thành các task có thể chuyển worker rồi mất session/lock.

Trước execution, gọi private bind endpoint bằng service token từ secret file để backend
nhận tại URL canonical `http://backend:8000/internal/runtime/bind` (ngoài `/api/v1`,
operation OpenAPI đã override server). Không gọi qua frontend proxy; prefix private
và biến thể `/api/v1/internal/runtime` đều bị nginx chặn theo [REST API](rest-api.md).
Backend kiểm `dag_id/run_id/task_id`, TI dag_version.id và revision đã deployed qua Public API.
Backend trả binding/config IDs không credentials. Package metadata đọc encrypted immutable
connection revisions bằng role riêng của app_metadata, giải mã keyfile tại memory.
Một run chỉ có một binding; attempt khác phải khớp config/source/target/dataset identity.
API/backend mất liên lạc trước bind thì retry hữu hạn/fail trước ghi; execution đã binding
không gắn vòng đời HTTP request, vẫn dùng app metadata/target sessions riêng.

## Manifest và encoding v1

Path logic: `/var/lib/aat/staging/<sha256-dag-id>/<sha256-run-id>/<dataset-uuid>/`;
writer attempt UUID có thư mục temp riêng. Chỉ server sinh path, không lấy raw ID làm path.

Manifest JSON có format_version=`aat-jsonl/1`, dataset_id, binding_sha256, source_snapshot_time,
source_schema_hash, target_schema_hash, mapping_hash, ordered columns với logical_type,
precision/scale/timezone semantics, files theo thứ tự chứa sha256/rows/bytes,
extracted_rows/validated_rows và state COMPLETE. Không credentials/connection DSN.

Mỗi file `part-000001.jsonl` gồm một row array/physical line; JSON serializer escape newline,
quote/delimiter, preserve Unicode. Value theo schema: integer JSON integer, bool JSON bool,
NULL JSON null, decimal canonical string chính xác, date ISO date, naive datetime ISO không offset,
aware datetime ISO có offset. Chuỗi literal giữ nguyên kể cả token NULL. Không float cho decimal;
float/binary/JSON/array/interval types không thuộc bảng hỗ trợ MVP thì validation lỗi.

Write `.part` → flush/fsync file → checksum → atomic rename cùng volume; manifest temp chỉ
rename COMPLETE sau tất cả file bền; fsync parent directory trên Linux container. Nếu process
chết trước COMPLETE thì không load. Mỗi đọc verify checksum/schema/binding trước sử dụng;
không dùng manifest app DB thay bằng chứng file tồn tại. Quota tính cả temp và complete.

## Streaming, snapshot và hạn mức mặc định

| Tham số | Mặc định | Hành vi |
| --- | --- | --- |
| extraction_chunk_rows | 1000, tối đa10000 | Source read cap, khác batch commit |
| target_batch_rows | 1000, tối đa10000 | Excel/runtime, có thể nhỏ hơn chunk |
| buffer_bytes | 8MiB | Chia chunk/batch sớm khi chạm byte cap |
| max_row_bytes | 1MiB | Dòng quá lớn fail rõ, không tăng memory tự động |
| etl_memory_budget | 512MiB/process | Stress test đo RSS, hai run tối đa trong scheduler container2GiB |
| source_upload_limit | 256MiB/file | Seed dataset lớn cho stress tạo trong volume, không buộc upload qua UI |
| definition_upload_limit | 10MiB compressed | Uncompressed100MiB/100k metadata rows |
| staging_run_quota | 10GiB | Giới hạn run bao gồm artifacts được bảo vệ |
| staging_global_quota | 20GiB | Reservation accounting app DB + kiểm filesystem thực |
| min_free_disk | 1GiB | Từ chối ghi tiếp trước khi vượt reserve; xử lý ENOSPC dù precheck thành công |
| target_scratch_quota | 10GiB/run, 5triệu dòng/run | Theo rows/byte estimate và size kiểm chứng, chặn trước tác động target |
| lock_wait_timeout | 300giây | Target busy thì fail rõ, không bỏ khóa của run khác |
| DB connect/query timeout | 10giây / 120giây mỗi statement | Full run không có timeout cực ngắn; lâu hơn phải cấu hình có kiểm thử |
| heartbeat/stale | 10giây / 120giây | Stale không chứng minh worker chết/commit rollback |

Scheduler parallelism2, mem_limit2GiB, DBs mỗi1GiB, host khuyến nghị8CPU/12GiBRAM/80GiB disk.
Một worker RSS512MiB là budget, không tuyên bố runtime container có hard per-process limit riêng với
LocalExecutor; supervisor theo dõi RSS và abort an toàn trước cgroup scheduler OOM, test bắt buộc.
Môi trường nhỏ hơn có thể giảm parallelism1, không giảm quy tắc integrity.

PG psycopg server cursor, transaction read-only REPEATABLE READ. MySQL PyMySQL SSCursor,
InnoDB consistent snapshot cùng transaction REPEATABLE READ. Không commit giữa các chunk
nguồn; mất source session bỏ incomplete dataset. Snapshot là một table, không distributed.
Không dùng COUNT(*) live sau extraction; manifest đếm dòng thực đã đọc sau filter.

CSV/TXT đọc TextIOWrapper/csv streaming có giới hạn record; phải giữ quoted/unquoted token
provenance cho NULL marker. Python csv.reader đơn thuần làm mất thông tin quote: lexer nhỏ
được kiểm thử ghi token.was_quoted trước chuyển value; không suy marker từ string đã parse.
Preview100dòng không thay full validation; file immutable checksum phải trùng validation.
Header BOM đầu được loại, trim theo setting công bố; header trùng/rỗng fail, không tự rename.

Trước khi chuyển cell lớn qua driver, query extraction có size guard do adapter sinh từ
identifiers đã validation: octet length của projected row và overflow flag; cell vượt giới hạn
không được materialize đầy đủ rồi mới kiểm RAM. Cursor fetch nhỏ theo max_row_bytes/byte budget
(ví dụ tối đa8row với8MiB/1MiB), ghép logical chunk1000row bằng streaming ghi file, không fetchmany
1000row lớn rồi mới chia. File parser giới hạn record bytes trong lúc đọc, kể cả multiline quote.
Typed Python object overhead được tính trong RSS stress gate, không chỉ số byte serialized.
## Mapping và kiểm tra kiểu

Implicit map exact-name khi không có enabled mapping; mapping tường minh thì không auto-bổ sung.
Direct Mapping chỉ cùng logical type/range tương thích; integer→bigint/decimal chỉ khi exact;
text→numeric/date/time chỉ Type Conversion tường minh và parser ISO/decimal invariant.
Không coercion numeric-string tự động, không cắt/round/đoán timezone; NULL Handling thay chỉ NULL.
Aware→naive hoặc naive→aware cần mapping rõ; MVP không có field cấu hình gán timezone cho
naive nên từ chối conversion đó, không dùng schedule timezone ngầm. PostgreSQL timestamptz
sang MySQL TIMESTAMP chỉ giữ instant nếu session UTC và precision/range tương thích; introspection
kiểm trước. Target Datetime naive không được nhận aware bằng cách bỏ offset.

Schema fingerprint gồm cột dùng/mapping/type/nullability/key, kiểm trước run và trước load.
DDL drift làm binding invalid; không tự sửa table/map. Decimal scale vượt target chỉ nhận khi
không thay giá trị biểu diễn; nếu cần round thì lỗi. Invalid row fail-fast, log vị trí/code không
nguyên row nhạy cảm; Failed Rows chỉ số biết chắc, không gán toàn phần chưa xử lý.

UPSERT phải kiểm mọi key trong dataset trước ghi: target-typed temporary validation table,
unique chosen key theo target collation/null semantics, ENGINE InnoDB ở MySQL. Scratch DDL
trước target DML transaction, không sử dụng temp-memory-only; stream staging vào scratch theo
chunk, quota riêng; duplicate key/NULL/type fail trước update target. Không Python set toàn tập.

## Thuật toán load theo policy

1. Resolve target/native lock cùng writer session. Key PG(namespace constant, table OID),
   MySQL GET_LOCK(sha256 database/table canonical). Không acquire lock ở pool connection khác.
2. Validate schema/authorization/support object signatures và dataset/checksums. Support DDL
   chỉ tạo mới sau confirmation; DDL target MySQL không trộn vào transaction dữ liệu.
3. APPEND: manifest row order và batch payload hash deterministic; trong mỗi transaction,
   verify ledger chưa có marker, insert rows, insert batch marker, COMMIT. Unique error rollback
   batch, giữ các batch trước; không INSERT IGNORE. Retry chỉ skip marker cùng binding/dataset/hash.
4. UPSERT PG: ON CONFLICT đúng real unique key DO UPDATE mapped non-key; key-only mapping
   dùng DO NOTHING chỉ khi đúng chosen conflict, metrics vẫn đếm accepted source rows.
   MySQL: UPDATE JOIN theo chosen key, rồi INSERT rows chosen key chưa tồn tại; independent
   unique collision làm rollback batch, không ON DUPLICATE KEY UPDATE nhầm row/REPLACE.
   DML+marker cùng transaction, retry cùng dataset/key ổn định; không dùng affected_rows làm rows loaded.
5. FULL_REFRESH: hoàn tất/validate mapped dataset và row count trước; acquire target lock,
   chuẩn bị INSERT chunks, xác nhận replacement/allow_empty và dependencies. Trong một transaction
   target: DELETE dữ liệu theo ủy quyền toàn table, batched INSERT không commit giữa batch,
   verify count/values, insert final run marker rồi COMMIT một lần. InnoDB/PG rollback bảo vệ
   old data khi bất kỳ bước nào lỗi; không TRUNCATE, DROP, ALTER, rename target hoặc tắt FK.
   Refuse inbound FK, nontransactional effects/unsafe trigger hoặc không kiểm tra được dependency.
6. Đối soát marker dưới lock khi COMMIT mất tín hiệu: query cùng run/dataset/batch trên session
   mới sau khi old session chắc kết thúc. Marker khớp chứng minh commit; absent chỉ replay nếu
   không còn old writer và snapshot/binding còn nguyên. Không kết luận thì NEEDS_RECONCILIATION.
7. Update app metrics sau commit; app DB projection lỗi không rollback target; reconciliation
   từ ledger sửa metric, không replay dữ liệu. Release native lock trong finally nếu còn session;
   process kill dựa server session cleanup và startup reconciliation, không chỉ finally.

Native lock chỉ phối hợp các managed runs; external writers nằm ngoài cam kết MVP. Reader
READ UNCOMMITTED không thuộc isolation hỗ trợ atomic visibility. Target sequence/auto_increment
có thể có khoảng trống sau rollback; không dùng số liên tiếp làm tiêu chí tính toàn vẹn dữ liệu.

## Reservation và admission FULL_REFRESH

MVP không thêm TTL/EXPIRED cho authorization; revoked/invalidated/terminal states theo
BR-08 quyết định quyền ghi. Confirmation token10phút hết hạn là kiểm tra request khác,
không làm mất binding hoặc giải phóng reservation. Replay cùng key/hash trả intent cũ.

Theo Spec BR-08 và [Data Model](../data-model.md), ONCE reservation gắn RunIntent bền ngay
khi tiếp nhận trigger, trước POST Airflow. Runtime bind xác minh TI version và run type
qua Public API; manual FULL_REFRESH không có ONCE intent đúng run bị từ chối, kể cả run
được tạo trực tiếp từ Airflow UI. SCHEDULED chỉ `run_type=scheduled`, schedule hash và
DAG/revision/target đúng; các loại backfill/operator_triggered/asset không tự được phép.

Thứ tự cho một replacement:
1. Chốt binding/config và chuẩn bị/validate toàn mapped dataset. ONCE extraction retry
   trước target ghi giữ cùng intent; run mới không nhận lại quyền cũ.
2. Giữ native lock cùng target writer session. Kiểm final ledger trước: marker cùng
   run/dataset/binding khớp thì chỉ đối soát thành công, không DELETE/INSERT lần hai.
   Marker không khớp hoặc writer/commit cũ chưa rõ thì bảo vệ artifact và dừng đối soát.
3. Kiểm schema/dependency/allow_empty và scope. Repository trong app DB khóa row quyền,
   rồi intent/binding/admission theo cùng thứ tự với revoke. Tạo admission epoch gắn
   đúng dataset hash/target session/owner, commit transaction ngắn. Không giữ app lock
   trong extraction/load, không giả transaction phân tán app DB/target.
4. Chỉ admission commit đã xác minh mới cho bắt đầu target transaction DELETE/INSERT/
   verify/final marker. Thu hồi đã commit trước admission chặn bước này. Thu hồi sau
   admission không hứa cancel/rollback giao dịch đã chấp thuận; giao dịch đó có thể
   hoàn tất/rollback. Mất phản hồi admission phải đọc lại cùng epoch/identity trước DML.
5. Sau target COMMIT, dùng final marker chứng minh COMMIT_VERIFIED; ONCE → CONSUMED.
   App projection lỗi chỉ reconcile từ ledger. Commit mất tín hiệu → NEEDS_RECONCILIATION,
   giữ quyền/binding/artifacts; thu hồi không cấm đối soát/rollback hoặc xóa evidence.
6. Nếu rollback và writer cũ kết thúc được xác minh, retry cùng run cần admission epoch
   mới và quyền chưa thu hồi/invalidated. Không dùng admission cũ cho transaction mới.
   Terminal failure hết retry/hủy đã xác minh đóng ONCE dù target chưa đổi; không giải
   phóng về GRANTED. Một run định kỳ hoàn tất không tiêu thụ quyền SCHEDULED toàn lịch.

allow_empty=false mặc định; true cần acknowledgment riêng có scope hash. ONCE chỉ run đã
reservation, SCHEDULED chỉ các run theo lịch trong scope còn hiệu lực. Mất nguồn/lỗi
parser/extraction/validation không là empty hợp lệ. UI phải tách xác nhận quyền thay thế,
quyền làm rỗng và thông báo giới hạn thu hồi đối với transaction đã được chấp thuận.
Run định kỳ khi quyền lịch đã thu hồi/invalidated phải fail trước target ghi; không tự
chuyển sang ONCE/APPEND hoặc bỏ qua xác nhận. Cùng target còn commit chưa rõ phải tiếp tục
tuân recovery/native lock BR-09, kể cả khi operator vừa cấp quyền mới cho run khác.

Runtime có thể dùng repository app DB sau binding mà không giữ HTTP request; app DB
không khả dụng trước admission thì dừng an toàn, không fallback quyền cache. Heartbeat
stale không đủ kết luận transaction cũ đã kết thúc. Task retry sau commit VERIFIED chỉ
đối soát; không coi task clear là quyền replacement mới.

## Cleanup và trạng thái phục hồi

Extraction incomplete không reuse, dọn sau xác minh writer chết. Dataset complete giữ7ngày sau
terminal và hết nhu cầu retry/recovery. File source đang tham chiếu không tự xóa. Target scratch
session temporary được DB thu hồi khi session mất; artifacts phục hồi không bị quota cleaner xóa.
Commit marker tối thiểu30ngày và chỉ dọn sau run đã đối soát/dataset hết retention.

Sau restart đối soát trong120giây từ dependencies ready hoặc nêu lý do bị chặn;
Airflow/target không phản hồi thì giữ PROTECTED và không giành lại khóa bằng heartbeat timeout.
Staging/full disk/corrupt manifest không fallback RAM hoặc re-extract sau partial target commit.
Operator thấy phase, known row counts, protected bytes, failure/recovery summary;
không thấy dataset qua XCom hoặc secret ở log/API.

## Các gate kiểm thử

Spec A–AM là nguồn nghiệm thu. Đặc biệt inject lỗi trước/sau target COMMIT, kill process không
finally, MySQL nhiều unique keys, duplicate theo case-insensitive collation, full refresh rollback,
schema drift, API timeout và same-target aliases. Không chỉ mock driver. Dataset stress >1GiB
và >20batch với worker budget512MiB; ghi RSS/actual disk/checksum/count, không báo PASS trước chạy.

BR-08 bổ sung gate: race hai ONCE requests, retry extraction/run terminal/rerun mới,
trigger timeout giữ RunIntent, revoke trước/sau admission, admission commit-response-loss,
target commit-response-loss, clear run success không replacement lần hai, SCHEDULED không
cho manual/backfill và allow_empty đúng scope. Lưu identity/status/evidence không credentials.


## Baseline container theo Constitution1.1.0

Baseline hiện chọn Podman Linux/amd64 và Compose provider theo Plan; Docker baseline khác
phải công bố/kiểm riêng. Chỉ thay công cụ build/start/test, không đổi snapshot/native lock/
ledger/admission/role/secret/quotas hoặc recovery. Resource limits, volume persistence và
UID/GID/RO mounts cần được kiểm bằng runtime/provider thật; engine rootful không cho phép
privileged hoặc bỏ kiểm quyền. Engine/provider đã phản hồi không chứng minh ETL đã chạy.
