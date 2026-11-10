# Mô hình dữ liệu và vòng đời

**Ngày**: 2026-11-06. **Cơ sở**: [spec.md](spec.md), [research.md](research.md).

## Quy ước chung

Application metadata nằm trong PostgreSQL `app_metadata`, schema `public`; UUID là khóa nội bộ,
`timestamptz` lưu UTC, các số tiền/decimal không lưu float. Bảng có `created_at`, `updated_at`
trừ record bất biến chỉ có created_at. JSONB không chứa secret plaintext. Code người dùng được
trim/normalize theo Spec; table/column name giữ case theo dialect. `revision` tăng đơn điệu,
update dùng optimistic concurrency với ETag; xung đột trả 409/412, không last-write-wins.

Alembic chỉ quản lý application schema; `airflow db migrate` quản lý `airflow_metadata`.
Ứng dụng không đọc Airflow metadata tables. ETL chỉ đọc/ghi bảng application được cấp quyền.
FK dependency dùng RESTRICT; không cascade xóa Definition/connection làm mất recovery.

## Các thực thể cấu hình

| Thực thể/bảng | Thuộc tính chính | Ràng buộc và quan hệ |
| --- | --- | --- |
| Connection / connections | id, code, normalized_code, name, database_type, current_revision_id, description, deleted_at | unique normalized_code; PG/MYSQL; code bất biến khi có dependency |
| ConnectionRevision / connection_revisions | id, connection_id, revision, database_type, host, port, database_name, schema_name, username, secret_id, physical_server_fingerprint, test_status, tested_at | unique connection_id/revision; immutable endpoint/credential, kể cả database_type snapshot để sửa type không đổi run cũ (FR-008); port1–65535; secret FK |
| ConnectionSecret / connection_secrets | id, ciphertext, key_id, created_at, retired_at | Fernet token; không plaintext; chỉ backend/runtime role đọc, không public serializer |
| UploadedFile / uploaded_files | id, original_name, safe_storage_key, sha256, bytes, extension, encoding, delimiter, header_present, quote_char, escape_char, null_token, parser_revision, parser_file_id, revision, validation_status, expires_at | storage_key do server sinh; filename không thành path; immutable content; parser sửa tạo revision; revision cho ETag, parser_file_id nội bộ do DB tính |
| FileParserRevision / file_parser_revisions | id, file_id, revision, encoding, delimiter, header_present, quote_char, escape_char, null_token, config_sha256, created_at | unique file/revision; immutable snapshot và hash; FK file RESTRICT, current-parser composite FK RESTRICT |
| DefinitionUpload / definition_uploads | id, kind, uploaded_file_id, template_version, workbook_sha256, status, validation_report_key | TABLE/ETL; version1.0; validation gắn file/checksum, report không chứa cell secret |
| DefinitionIssue / definition_issues | id, upload_id, code, scope, sheet, row, column, column_name, severity, message_key, safe_context | row/column bắt đầu1; lỗi workbook có location null và scope=workbook; không echo dữ liệu nhạy cảm |
| TableDefinition / table_definitions | id, upload_id, target_connection_revision_id, target_schema, table_name, physical_table_identity, description, definition_hash | unique upload/physical table identity; chỉ tạo mới table |
| TableColumn / table_columns | id, table_definition_id, name, ordinal, logical_type, length, precision, scale, nullable, primary_key_ordinal, default_literal, description | unique name/ordinal/table; key không nullable; default tagged JSON; PK ghép thứ tự ordinal |
| ETLDefinition / etl_definitions | id, dag_id, current_revision_id, owner=aat, lifecycle | dag_id unique local; collision external kiểm thêm Airflow; không cascade xóa lịch sử |
| ETLDefinitionRevision / etl_definition_revisions | id, definition_id, revision, upload_id, config_json, config_sha256, schema_fingerprint_source, schema_fingerprint_target, dependency_fingerprint, status | immutable canonical config; JSON chứa IDs/reference, không secret; unique definition/revision/hash |
| ColumnMapping / column_mappings | id, etl_revision_id, ordinal, source_column, target_column, transformation, default_literal, enabled | một target enabled mỗi revision; source tùy transform; enum whitelist |
| DataReplacementAuthorization / replacement_authorizations | id, dag_id, etl_revision_id, physical_target_id, scope, scope_sha256, schedule_sha256, allow_empty, allow_empty_acknowledged_at, acknowledged_at, state, reserved_intent_id, consumed_at, closed_at, revoked_at, invalidated_at, revision | scope ONCE/SCHEDULED; allow_empty mặc định false, true cần xác nhận riêng; ONCE reservation một lần không giải phóng; đổi phạm vi làm mất hiệu lực; không xóa quyền còn recovery |
| ApplicationSetting / application_settings | key, value_json, value_type, revision, updated_at | whitelist key; không lưu secret; default mới không mutate deployed config |

`config_json` chứa source union DB hoặc FILE, target, schedule union Manual/cron, timezone,
start_date/catchup, strategy/conflict_keys, batch/retry, mapping/filter và IDs các dependency.

Chi tiết ORM T020: UploadedFile giữ snapshot parser ban đầu bất biến; parser mới phải dùng
FileParserRevision của T021, không sửa đè snapshot/content cũ. safe_storage_key là token opaque
do server sinh, không ghép original_name vào path. TableDefinition bổ sung physical_table_identity
nội bộ từ fingerprint server đã xác minh, database/schema/table để unique theo upload không bị
vượt qua bằng credential revision mới; chưa xác minh fingerprint thì chưa lưu target definition.
Tên schema/table giữ nguyên theo dialect; canonicalization và xác minh server thật thuộc adapters.
Issue.safe_context chỉ cho metadata count/limit và expected_type/actual_type có whitelist,
không raw cell value/credential. default_literal SQL NULL là không có default; JSON tagged value=null
là explicit null, decimal giữ text lossless. Các chi tiết này không triển khai parser/DDL nghiệp vụ.
Cột enum/config được validate Pydantic trước lưu; SQL identifiers không nhận dotted SQL fragment.

Chi tiết ORM Phase2: ETL config lưu JSONB object canonical theo PostgreSQL JSONB text UTF-8,
SHA256 do DB tính/đối chiếu đầu vào; từ chối credential keys lồng nhau và credential DSN.
Đây là boundary lưu trữ, không thay full ETLConfig validator T071. Unique revision theo
(definition_id, revision) và (definition_id, config_sha256); mapping là một phần snapshot
bất biến, enabled target unique qua partial index, disabled rows vẫn giữ provenance.
FK current revision gồm definition_id để không trỏ revision của Definition khác.

Chi tiết Phase2 quyền/runtime: authorization scope và acknowledgment là snapshot bất biến;
đổi scope phải tạo quyền mới và invalidate quyền cũ. reserved_intent_id khi đã gán không
được xóa/chuyển; FK vòng authorization/intent là RESTRICT deferred. Dataset pointer phải
thuộc đúng binding; file_parser_revision của binding lưu UUID FileParserRevision để FK
giữ cả revision cũ. ReplacementAdmission bổ sung writer_finished làm bằng chứng điều kiện
cho epoch retry; trường này không thay target-ledger proof. Audit safe_summary lưu message key,
không lưu nguyên exception/payload. Worker chỉ xử lý kinds có handler, không replay operation
NEEDS_RECONCILIATION. Các gate target lock/commit proof vẫn thuộc phase engine sau.

Wiring Phase2: app-init dùng owner secret domain riêng `/secrets/app-owner`, chỉ chứa
app_owner; backend/worker không mount owner/admin secret. Domain này bổ sung cho namespace
mới, không tự sửa secret volumes của các project đang chạy. Worker heartbeat nền lưu bảng
worker_heartbeats (UUID/id, owner_process_id ngẫu nhiên mỗi process, heartbeat_at) để backend
kiểm freshness qua DB thay vì đọc `/tmp` của container khác. DAGDeployment bổ sung dag_id
nội bộ do DB suy ra từ ETL revision cho unique active deployment theo DAG, kể cả khác revision.
Dataset COMPLETE không quay lại INCOMPLETE hoặc đổi content/binding pointer.

`physical_server_fingerprint` dùng server/database identity được adapter xác minh. Quyền ghi
cuối cùng do native lock ngay trên target quyết định: PG table OID trong database hiện tại,
MySQL normalized database/table trên cùng mysqld. DNS alias không tạo hai khóa khác nhau.
Không resolve chắc chắn thì chặn an toàn, không dùng Connection Code làm identity vật lý.

## Công việc nền và kết quả thao tác

| Thực thể/bảng | Thuộc tính chính | Ràng buộc và vòng đời |
| --- | --- | --- |
| Operation / operations | id, kind, idempotency_key, request_sha256, state, progress_json, result_ref, deadline_at, lease_owner, lease_until, heartbeat_at, attempt, error_code, error_summary | unique kind/idempotency_key; cùng key khác payload409; SELECT FOR UPDATE SKIP LOCKED nhận việc |
| TableCreationJob / table_creation_jobs | id, operation_id, upload_id, confirmation_hash, target_revision_id, started_at, finished_at | chỉ bắt đầu từ upload VALIDATED, recheck quyền/schema/existence |
| TableCreationResult / table_creation_results | id, job_id, table_definition_id, state, ddl_text, ddl_sha256, started_at, finished_at, error_code, safe_error | unique job/table; kết quả riêng, không hứa transaction toàn workbook |
| DAGDeployment / dag_deployments | id, operation_id, etl_revision_id, previous_deployment_id, state, revision_sha256, generated_file_key, file_sha256, previous_file_sha256, expected_owner_tag, parsed_at, airflow_version_id, airflow_version_number, last_verified_at, previous_paused, reconcile_required | unique deployment identity; một active deploy mỗi dag; version UUID/number lấy API thật |
| AdmissionState / dag_admission | dag_id, generation, desired_paused, gate_state, reason, etl_revision_id, deployment_id | state OPEN/BLOCKED; chặn run mới vào engine khi redeploy/connection change; không scheduler thay thế |
| AuditEvent / audit_events | id, operation_id, subject_type/id, action, revision_before/after, acknowledgment_scope, timestamp, safe_summary | ghi xác nhận/xung đột/recovery; không chứa credentials, payload file/dataset hoặc nguyên dòng lỗi |
| RunIntent / run_intents | id, operation_id, run_uuid, dag_id, airflow_run_id, run_type, etl_revision_id, authorization_id, request_sha256, state, reserved_at, last_reconciled_at | unique operation_id và dag_id/airflow_run_id và run_uuid; manual ID ổn định trước POST Airflow; ONCE không chuyển intent; scheduled intent tạo sau API xác minh run |

Operation: QUEUED → RUNNING → SUCCEEDED / PARTIALLY_SUCCEEDED / FAILED /
NEEDS_RECONCILIATION. Worker mất lease không cho worker mới replay side effect chưa đối soát.
Validation job có thể replay read-only; DDL phải kiểm tra ledger/result/schema; deploy phải
đối chiếu file/API/revision; table đã tồn tại không được tự nhận owned hoặc DROP để thử lại.

Table result: PENDING → CREATING → CREATED / ALREADY_EXISTS / FAILED / UNKNOWN.
ALREADY_EXISTS là lỗi theo mặc định; UNKNOWN sau network interruption phải inspect đúng
signature và ghi kết quả xác minh, không tạo lần hai. Job partial không đổi kết quả CREATED.

Deployment state tương ứng UI: VALIDATION_FAILED → READY_TO_DEPLOY → DEPLOYMENT_PENDING →
DEPLOYED / DEPLOYMENT_FAILED / PARSE_ERROR. `reconcile_required` bổ sung khi API/storage
không biết chắc kết quả; timeout120giây không có nghĩa rollback file hay registry đã xảy ra.
DAGGeneration chưa phải registration. Sau lỗi redeploy giữ admission blocked và DAG paused.

## Metadata phục hồi execution

| Thực thể/bảng | Thuộc tính chính | Vai trò |
| --- | --- | --- |
| ExecutionBinding / execution_bindings | id, dag_id, airflow_run_id, task_id, airflow_dag_version_id, etl_revision_id, source_revision_id, target_revision_id, file_parser_revision, source_file_sha256, authorization_id, dataset_id, runtime_build, binding_hash, state, commit_uncertain, last_reconciled_at | unique dag/run; lần đầu chốt immutable; retry phải trùng binding |
| DatasetManifest / dataset_manifests | id, execution_binding_id, generation, snapshot_started_at, schema_hash, mapping_hash, path_key, manifest_sha256, extracted_rows, validated_rows, total_bytes, state | INCOMPLETE/COMPLETE/CORRUPT/PROTECTED/EXPIRED; complete không mutate |
| StagingArtifact / staging_artifacts | id, dataset_id, attempt_id, path_key, file_sha256, rows, bytes, min/max_record_index, state, expires_at, recovery_protected | unique safe path, file ordinal; complete chỉ sau fsync |
| ExecutionMetric / execution_metrics | binding_id, extracted_rows, validated_rows, loaded_rows, failed_rows_nullable, staging_bytes_current/peak, duration_ms, phase, metric_updated_at | metric engine và projection commit ledger, không copy Airflow history |
| RuntimeLease / runtime_leases | binding_id, owner_process_id, heartbeat_at, target_identity, target_lock_identity, recovery_state | heartbeat chỉ phát hiện nghi ngờ; không thay native target lock |
| ReplacementAdmission / replacement_admissions | id, binding_id, run_intent_id, authorization_id, admission_epoch, authorization_revision, scope_sha256, dataset_sha256, target_identity, owner_process_id, target_session_identity, state, admitted_at, reconciled_at | unique binding_id/admission_epoch; tối đa một admission chưa đối soát mỗi binding; immutable identity; không là bằng chứng target commit |

ExecutionBinding bổ sung `run_intent_id` FK RESTRICT unique và `airflow_run_type`.
`RunIntent.authorization_id` nullable cho APPEND/UPSERT; việc có intent không cấp
quyền replacement. FULL_REFRESH vẫn bắt buộc authorization đúng scope tại bind và
admission; `ReplacementAdmission.authorization_id` luôn NOT NULL.
Role `aat_etl` được UPDATE riêng `RunIntent.last_reconciled_at` để PostgreSQL cho
phép SELECT FOR UPDATE khi admission/close khóa intent. Role không được đổi state,
authorization_id, run_uuid hay revision của intent; không được cấp quyền hoặc xóa evidence.
RunIntent được tạo trước Airflow manual run, không dùng ExecutionBinding chưa có TI version
để giả runtime đã bind. Binding lần đầu chốt config/source/target; dataset chốt khi COMPLETE
trước target ghi, extraction retry có thể bỏ generation INCOMPLETE và tạo generation mới
chỉ khi chưa target commit, không mutate COMPLETE hoặc ghép snapshot. RunIntent và
authorization không bị xóa khi mất phản hồi trigger hoặc worker restart.

## Vòng đời ủy quyền FULL_REFRESH

- Authorization state: GRANTED → RESERVED (ONCE) → CONSUMED hoặc CLOSED. REVOKED/INVALIDATED
  chặn cấp admission mới; quyền đã terminal không được dùng lại. `revoked_at` lưu riêng để
  không mất lịch sử thu hồi khi kết quả cuối sau đối soát là CONSUMED/CLOSED.
- SCHEDULED còn GRANTED qua nhiều run đúng lịch; mỗi run có intent/binding/admission riêng.
  Airflow `run_type=scheduled` và schedule hash/revision/target phải khớp. Manual run cần
  ONCE riêng; các run type khác không tự hưởng quyền lịch.
- Operation/idempotency replay kiểm request hash và trả intent cũ. Với yêu cầu mới,
  transaction khóa authorization row trước, kiểm scope/revocation rồi tạo intent,
  gán `reserved_intent_id` nếu ONCE và commit cùng Operation. FK vòng authorization/intent
  dùng insert intent rồi set reference trong cùng transaction; parent quyền đã tồn tại.
  Hai transaction tranh ONCE chỉ một transaction được commit reservation; không last-write-wins.
- RunIntent state: RESERVED → SUBMITTING → CREATED hoặc NEEDS_RECONCILIATION; REJECTED
  đã xác minh không còn run/retry thì đóng ONCE. Scheduled intent không đi qua POST trigger.
  Timeout tạo run giữ intent; GET cùng run_id trước gửi lại, không cấp run_uuid mới.
- ReplacementAdmission state: ADMITTED → COMMIT_VERIFIED / ROLLBACK_VERIFIED /
  NEEDS_RECONCILIATION. Admission/thu hồi khóa cùng authorization row; lock order
  authorization → intent → binding/admission, không đảo thứ tự giữa các repository.
  Runtime đang giữ native target lock, kiểm ledger và quyền, commit admission ngắn rồi
  bắt đầu target transaction. Không giữ row lock app DB trong suốt target load.
- Thu hồi commit trước admission thì admission bị từ chối. Admission commit trước thu hồi
  cho phép transaction đã được chấp thuận hoàn tất/rollback, không retry DML mới bằng
  admission cũ. Mất phản hồi admission không được ghi target trước khi đọc lại identity.
  Khi recovery chứng minh rollback và writer cũ đã kết thúc, retry cùng run cần admission
  epoch mới và quyền vẫn hợp lệ. Marker final đã khớp thì chỉ đối soát, không ghi lần hai.
- ONCE CONSUMED sau target final marker khớp và đối soát; CLOSED khi run thất bại terminal
  không còn retry/hủy đã xác minh và không có commit chưa rõ. Extraction retry an toàn
  trong cùng run giữ RESERVED. Không trả quyền về GRANTED hoặc đổi reserved_intent_id.
- Commit chưa rõ giữ admission NEEDS_RECONCILIATION và protected artifacts. Thu hồi không
  xóa bằng chứng hoặc chặn đọc ledger/rollback. App projection lỗi không đảo target commit.
- Runtime chỉ được ghi binding/metrics/admission qua repository và quyền cột/role giới hạn;
  không được cấp authorization, thay scope/allow_empty hoặc xóa marker/recovery evidence.

## Parser revision và API đọc lịch sử

UploadedFile bổ sung `revision` cho ETag; bảng FileParserRevision lưu id/file_id/revision,
encoding/delimiter/header/quote/escape/null_token/config_sha256/created_at; unique file/revision,
immutable config. Content sha256 không đổi. Sửa parser bị chặn khi file có run active/recovery;
revision mới làm validation/confirmation/DAG dependency stale, không mutate binding cũ.
Preview có thể dùng parser dự kiến không lưu để operator xác nhận trước PATCH; các parser
revision còn binding/recovery tham chiếu phải giữ. Schema workbook1.0 không thay đổi.

Chi tiết lưu trữ T021: `revision` là version của UploadedFile cho ETag, bắt đầu1 và tăng
ở mỗi UPDATE thực; ORM kiểm version cũ để phát hiện lost update. `parser_revision` trỏ tới
snapshot riêng. Với CSV/TXT, cột nội bộ `parser_file_id` do DB tính bằng id; composite FK
(parser_file_id, parser_revision) RESTRICT tới (file_id, revision), deferred để tạo file và
revision1 trong cùng transaction. Với XLSX, parser_file_id là NULL vì workbook không dùng
delimited parser. Chỉ commit CSV/TXT khi đã có snapshot; snapshot1 khớp parser ban đầu.
Đổi parser lưu snapshot mới rồi đổi con trỏ trong cùng transaction, không sửa snapshot cũ;
con trỏ chỉ tăng. Validation/dependency stale và khóa active/recovery thuộc T067/T042,
không được suy từ ORM thành nghiệm thu các service đó.

Hash parser là SHA256 UTF-8 của PostgreSQL JSONB array text theo thứ tự cố định
[encoding, delimiter, header_present, quote_char, escape_char, null_token]; DB sinh và kiểm
hash đầu vào nếu có. SQL NULL escape khác chuỗi rỗng, NULL token giữ nguyên text kể cả `\\N`.
History không cho UPDATE bất kỳ field; xóa revision hiện hành bị FK RESTRICT. Khi có model
binding/recovery, các FK RESTRICT riêng phải bảo vệ revision cũ; nhánh đó chưa kiểm ở T021.

Các history APIs đọc DefinitionUpload/TableCreationJob/TableCreationResult/TableDefinition,
phân trang/sort created_at+id và filter target/upload/state; không dựa IDs trong browser storage.
Table detail trả cấu trúc định nghĩa, kết quả tạo và trạng thái introspection DB thật; DB down
trả rõ unavailable, không mô tả định nghĩa đã lưu như cấu trúc hiện tại được xác minh.

Chỉ lưu identity/binding, engine metrics và bằng chứng recovery mà Airflow không lưu.
Không tạo bảng sao chép đầy đủ DAG Runs/task attempts/logs để làm Dashboard; lịch sử/trạng thái
Airflow luôn lấy API. `ExecutionBinding.state` là trạng thái engine/commit, không được tự ghi
thành Airflow run success. External DAG không có binding, không gán metrics0 giả.

Connection revisions và secret còn được run binding tham chiếu không được garbage collect;
ngừng sử dụng chỉ khi không còn run active/recovery. Task retry sau đổi password vẫn dùng
revision đã chốt; credential bị thu hồi bên ngoài làm fail an toàn, không tự đổi người dùng/target.

## Support objects trong target database

Đây là metadata kỹ thuật, không nằm trong Airflow DB và không đổi cấu trúc table người dùng.
Deployment preview nêu rõ support DDL và quyền cần thiết; tạo sau xác nhận, sample init tự tạo.
Tên vật lý được chuẩn hóa theo bảng dưới; không dùng `_aat_manifests` làm alias của
run commit. Tên collision không đúng signature/version phải chặn. Table target vẫn không DROP/ALTER.

| Tên logic | PostgreSQL | MySQL trong database target |
| --- | --- | --- |
| batch_commits | _aat_control.batch_commits | _aat_batch_commits |
| run_commits | _aat_control.run_commits | _aat_run_commits |
| support_schema_version | _aat_control.support_schema_version | _aat_support_schema_version |

Init và runtime dùng cùng mapping/signature version1; không tự nhận object tên cũ là tương
thích hoặc migrate user table. Sample init tạo đúng technical objects sau bootstrap consent.

| Bảng | Khóa và trường | Transaction |
| --- | --- | --- |
| batch_commits | PK(target_identity, run_uuid, dataset_sha, batch_index), binding_sha, row_count, payload_sha, strategy, committed_at | Insert marker và target DML cùng một transaction/session |
| run_commits | PK(target_identity, run_uuid), dataset_sha, binding_sha, total_loaded_rows, replacement_authorization_sha, completed_at | FULL_REFRESH final marker cùng commit toàn replacement; APPEND/UPSERT marker hoàn tất sau đủ batch |
| support_schema_version | singleton version/signature | Chỉ tạo mới hoặc migrate metadata riêng có kiểm soát, không sửa user table |

PG types UUID/bigint/text/timestamptz; MySQL CHAR(36)/BIGINT/VARCHAR bounded/DATETIME(6),
InnoDB và utf8mb4. Checksums hex64. UUID run nội bộ mapping stable tới Airflow Run ID dài;
không dùng run_id raw làm tên SQL. Marker xung đột payload không được coi batch đã xử lý.

Đối soát dưới native target lock: marker tồn tại với checksum đúng → đã commit, bỏ qua batch;
không có marker sau khi transaction cũ chắc chắn kết thúc → chưa commit; không kết luận chắc
chắn → NEEDS_RECONCILIATION, giữ artifact. Projection app DB được cập nhật sau target commit,
không phải nguồn chứng minh commit. Không có transaction phân tán giữa hai database.

## Chỉ mục, validation và migrations

- Unique normalized_code; unique dag_id; unique definition/revision; unique operation key;
  indexes operations(state, lease_until), deployments(dag, created_at), issues(upload, sheet,row),
  bindings(dag,run), artifacts(dataset,state,expires_at), dependency FK và audit timestamp.
- Constraint JSON/key fields nonempty, counts không âm; scale <= precision; secret ciphertext
  không xuất qua serializer. Optimistic revision bắt buộc ở PATCH/update/redeploy.
- Migration app_metadata theo Alembic, app-init giữ advisory migration lock và chạy upgrade head
  trước seed. Migrations idempotent theo Alembic revision, không chạy cạnh tranh từng API replica.
- Không startup downgrade hoặc tự reset volume khi migration lỗi. Seed dựa natural keys ổn định,
  không UPDATE dữ liệu người dùng khi restart. Airflow migration là init service độc lập.

## Retention và khôi phục

Authorization/RunIntent/ReplacementAdmission giữ khi còn binding/ledger/recovery tham chiếu;
không cascade xóa hoặc purge quyền đang chờ đối soát, kể cả REVOKED/INVALIDATED.
Staging7ngày sau terminal/recovery xong; source không tham chiếu30ngày; log/operation audit30ngày
mặc định, Definition/revision/deployment được giữ khi còn DAG/binding liên quan. Target ledger
chỉ dọn sau run terminal đã đối soát và dataset hết retention, ít nhất30ngày; không xóa marker
của batch commit chưa rõ. GC có báo cáo, quota tính cả artifact được bảo vệ; không xóa để vượt quota.

Các thay đổi trạng thái và số liệu phải đi qua transaction ứng dụng nhỏ; không giữ SQLAlchemy
Session request trong suốt ETL. Runtime/worker tự mở session ngắn. Shared package metadata không
import FastAPI hoặc Airflow. Khóa encryption lưu volume riêng phải backup cùng app DB;
restore thiếu đúng key làm readiness fail có chẩn đoán, không tạo key mới thay thế.
