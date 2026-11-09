# Nghiên cứu và quyết định kỹ thuật

Hiện hành2026-11-09: owner đã xác nhận LEX-003, LEX-079 và mapping ba candidate IDs;
quyền local có hạn được kích hoạt theo [hồ sơ](../../docs/decisions/t014-local-activation.json).
T014_FULL BLOCKED/security FAIL; chỉ viết tests T015/T016 lượt này.
Test drivers tái sử dụng đúng images đã duyệt: contract trên Airflow candidate network=none;
foundation trên backend-tests candidate + PostgreSQL baseline, tmpfs/internal network riêng.
Không thêm dependency hoặc rebuild; wiring contract dependencies vào profile runner T034
còn phải làm trước gate đó. Chi tiết [báo cáo](../../docs/testing/t015-t016-report.md).

## A/B đã được duyệt ngày 2026-11-09 — quyết định hiện hành

Chủ dự án duyệt [A/B](../../docs/proposals/t014-round2-approval.md). File upstream
constraints3.3.2/Python3.12 giữ nguyên SHA256; policy riêng tạo bản hiệu lực chỉ đổi
certifi2026.7.22→2026.10.18 và urllib3 2.7.0→2.8.0. Mọi pin khác giữ nguyên.
Override wheels có hashes và provenance PyPI riêng; resolve engine/metadata/providers
với bản hiệu lực rồi kiểm pip check, core/SDK3.3.2 và auth/readiness thật.
Quyết định này thay giới hạn “không override” ở phần lịch sử bên dưới, không cho phép
override package khác hoặc nâng Airflow core.

Playwright client1.65.0 trong frontend và E2E; browser image1.65.0-resolute khóa manifest
Linux/amd64 `fb9978a801599ea0a57079eb642ad75cb52dbe1b162c8bf1fc989a603aa39218`,
Chromium158.0.8127.18; OS lock apt/libapt-pkg7.0=3.2.1ubuntu0.1 theo candidate đã thử.
Không tái dùng Noble package lock trên Resolute. Build stages/final runner phải scan lại
đúng image IDs; UI/private-proxy smoke và browser version phải kiểm thực tế.
A/B không chấp nhận findings còn lại; T014 giữ BLOCKED cho tới khi toàn bộ gate đạt.

**Ngày**: 2026-11-06. **Phạm vi**: Spec đã Clarify, Constitution 1.1.0; các kết quả trước sửa đổi là lịch sử.
Tài liệu ghi quyết định thiết kế, không xác nhận hệ thống đã được build hoặc integration test.

**Remediation T014 ngày 2026-11-08 đã được duyệt P1–P7:**
[Phương án](../../docs/proposals/t014-remediation.md) và metadata/triage đi kèm giữ lại
làm provenance trước thay đổi. Quyết định hiện tại: Router7.18.5/Zod4.6.7, Python3.12.16,
Node22.23.4/npm12.2.2, PG17.11/MySQL8.4.13, nginx1.30.6-alpine3.24; thử Airflow slim3.3.2
với provider lock và file constraints chính thức không đổi. A/B mới tạo constraints hiệu lực
riêng và nâng Playwright client/browser1.65.0 theo quyết định hiện hành ở đầu tài liệu,
runner OS được khóa phiên bản; global npm không cần dùng bị loại khỏi final runner,
build stage vẫn phải scan. Candidate không tự mang trạng thái compatibility/security PASS.
Ngoại lệ A/B ban đầu gồm hai override và cặp browser B; quyền remediation bổ sung và
dnspython2.9.0 được ghi ở mục T014 bổ sung bên dưới. Không tự nâng Airflow core. Báo cáo thực thi
hiện hành ở `docs/testing/phase1-report.md`; các NOT_RUN trong thiết kế ban đầu là lịch sử.

## 1. Nền tảng điều phối và phiên bản

**Quyết định**: Apache Airflow `3.3.2`, image `apache/airflow:slim-3.3.2-python3.12`,
Python 3.12; LocalExecutor, parallelism 2, mỗi DAG một task `execute_etl`, max_active_runs 1.
ETL package và metadata package đóng wheel `0.1.0`, cài trong cùng custom image Airflow.

**Lý do**: Phù hợp local một máy; không cần broker/Celery worker. Task là process con của
scheduler, vì vậy scheduler phải mount uploads/staging/secrets, không chỉ API server.
Dùng `airflow.sdk` ở wrapper; ETL engine không phụ thuộc SDK hoặc ORM Airflow.

**Phương án đã cân nhắc**: CeleryExecutor cần Redis/worker không có nhu cầu; SequentialExecutor
không được giả định là executor của Airflow 3; KubernetesExecutor vượt phạm vi.

**Nguồn**: [Release 3.3.2](https://airflow.apache.org/docs/apache-airflow/3.3.2/release_notes.html),
[điều kiện cài đặt](https://airflow.apache.org/docs/apache-airflow/3.3.2/installation/prerequisites.html),
[executor](https://airflow.apache.org/docs/apache-airflow/3.3.2/core-concepts/executor/index.html).

## 2. Khóa dependency và kiểm tra tương thích

**Quyết định**: Backend và ETL dùng chung các pin đã được Airflow constraints Python 3.12
liệt kê: FastAPI 0.136.3, Pydantic 2.13.5, SQLAlchemy 2.0.52, Alembic 1.20.0,
psycopg/binary 3.3.5, PyMySQL 1.1.3, cryptography 50.0.1, httpx 0.28.1,
openpyxl 3.1.5, python-multipart 0.0.32; frontend/image/test pins ở mục ma trận phiên bản.
Không cài toàn bộ providers/extras trong constraints. Pin Airflow trong cả lệnh cài wheel
bổ sung để resolver không nâng/hạ phiên bản ngầm.

**Lý do**: Chọn giao dependency của môi trường Airflow thay vì ghi đè constraints bằng bản
backend mới hơn. Backend có môi trường riêng; package metadata/engine chỉ kéo dependency
cần thiết, không kéo FastAPI vào logic xử lý dữ liệu.

**Phương án đã cân nhắc**: Dùng latest hoặc cài pip lúc container startup không tái lập được.
Implementation tạo npm lockfile và Python lock có hashes, vendor constraints theo commit/hash;
resolve/build/pip check là gate đầu tiên, chưa phải bằng chứng đã chạy ở bước Plan.

**Nguồn**: [Constraints chính thức 3.3.2/Python 3.12](https://raw.githubusercontent.com/apache/airflow/constraints-3.3.2/constraints-3.12.txt).

## 3. API và xác nhận đúng revision

**Quyết định**: Backend dùng Public API `/api/v2`, JWT từ SimpleAuthManager với service user
local; không gọi `/ui` API hay ORM metadata. Contract chi tiết ở contracts/airflow.md.
LocalDagBundle trên shared DAG volume; mỗi file generated có owner tag, revision SHA-256,
đường dẫn ổn định và một wrapper import engine. Config serialization JSON canonical,
không nội suy cell Excel thành Python executable.

Deploy pause và đóng admission, drain queued/running, write temp + fsync + os.replace trên
cùng volume, rồi poll có backoff tối đa 120 giây. Đối chiếu tags/hash/fileloc/parse time và
`latest_dag_version`; lưu version UUID/number. API timeout là kết quả chưa xác định.
Task startup đối chiếu `TaskInstanceResponse.dag_version.id` với revision; không đọc
`dag_version_id` từ DAGRunResponse vì trường scalar đó không có trong schema 3.3.2.

**Lý do**: LocalDagBundle không versioned. Old task clear sau redeploy phải bị từ chối nếu
version không khớp; operator tạo run mới thay vì chạy nhầm mã. Config run đã binding không đổi.
DAG parse mới không bảo đảm run cũ dùng mã cũ, nên không dựa vào DagVersion một mình.

**Phương án đã cân nhắc**: GitDagBundle giữ phiên bản thực tốt hơn nhưng thêm provider/git
lifecycle; chưa cần cho MVP khi đã drain và reject old clear. Sleep cố định và coi ghi file
là deployed đều bị loại bỏ.

**Nguồn**: [Dag bundles](https://airflow.apache.org/docs/apache-airflow/3.3.2/administration-and-deployment/dag-bundles.html),
[OpenAPI đúng tag](https://raw.githubusercontent.com/apache/airflow/3.3.2/airflow-core/src/airflow/api_fastapi/core_api/openapi/v2-rest-api-generated.yaml),
[SimpleAuthManager](https://airflow.apache.org/docs/apache-airflow/3.3.2/core-concepts/auth-manager/simple/index.html).

## 4. Secrets và metadata runtime

**Quyết định**: Fernet mã hóa password theo immutable ConnectionRevision trong app_metadata;
key có key_id, tạo một lần bằng secrets-init, lưu volume private, quyền tối thiểu; không ở DB,
image, DAG hoặc .env committed. Backend và scheduler/runtime nhận mount chỉ đọc cần thiết.
Keyring MultiFernet hỗ trợ rotation có kiểm soát, không tự tạo key mới khi ciphertext đã tồn tại.

Runtime đọc ciphertext bằng role riêng từ app_metadata rồi giải mã trong memory; không trả
password qua API kể cả private API. API runtime chỉ trả config/reference/binding không secret.
Không sao chép connection vào Airflow DB hoặc cần restart Airflow khi thêm connection.
Public response không có password field; request create/rotate secret là write-only.

**Lý do**: Tuân Constitution cấm credentials trong API response/DAG/log/XCom. Tách
application metadata với Airflow internal metadata; role runtime chỉ đọc revision và ghi
binding/metrics/admission qua các thao tác giới hạn của repository, không có quyền migration,
cấp quyền mới, sửa phạm vi ủy quyền hoặc thay cấu hình operator.

**Phương án đã cân nhắc**: Private API trả plaintext secret vẫn vi phạm Constitution;
Airflow Connection ORM/direct metadata table bị loại. Vault thêm vận hành chưa cần local MVP.

**Nguồn**: [Fernet và key rotation](https://cryptography.io/en/latest/fernet/).

## 5. Snapshot và định dạng staging

**Quyết định**: PostgreSQL source read-only REPEATABLE READ transaction và server-side cursor;
MySQL source InnoDB REPEATABLE READ consistent snapshot với unbuffered SSCursor. Không
OFFSET qua nhiều transaction; giữ một source transaction đến khi extraction xong.
Staging là JSON Lines UTF-8 với row array, typed schema manifest, không nén ở MVP.
Decimal biểu diễn chuỗi chính xác, date/time ISO, NULL là JSON null, binary không hỗ trợ.
Mỗi chunk là file riêng, có checksum/rows/bytes và manifest complete chỉ sau fsync.

**Lý do**: Tránh dependency Arrow và float coercion; JSON escaping giữ quote/newline/Unicode.
Chi phí dung lượng cao hơn được kiểm soát quota. Mỗi cell giải mã theo schema, không đoán kiểu.
Byte cap lẫn row cap giữ memory bounded; staging path là hash DAG ID/hash Run ID/attempt UUID,
không nối trực tiếp định danh chứa slash. DB extraction hoàn tất trước ghi target.

**Phương án đã cân nhắc**: CSV không schema mơ hồ NULL/decimal/datetime; Parquet cần thêm
native dependency và kiểm tra logical type, chưa cần. In-memory buffer toàn tập bị cấm.

**Nguồn**: [PostgreSQL snapshot](https://www.postgresql.org/docs/current/transaction-iso.html),
[MySQL consistent read](https://dev.mysql.com/doc/refman/8.4/en/innodb-consistent-read.html),
[SQLAlchemy streaming](https://docs.sqlalchemy.org/en/20/core/connections.html#using-server-side-cursors-a-k-a-stream-results).

## 6. Commit, concurrency và recovery

**Quyết định**: Cùng session target vừa giữ native lock vừa DML: PostgreSQL session advisory
lock trên namespace/table OID trong database; MySQL GET_LOCK theo normalized database/table.
Lock đợi tối đa 300 giây, giữ qua các batch; mất session không được ghi bằng session thay thế
trước reacquire/reconcile. Server-native scope xử lý connection alias trỏ cùng physical table.

Target có support objects do operator xác nhận trong deployment preview: PostgreSQL schema
`_aat_control`; MySQL bảng prefix `_aat_` trong target database, chỉ tạo mới, không sửa table
người dùng. Commit ledger theo run/dataset/batch cùng target transaction với DML; không dùng
checkpoint app_metadata riêng để kết luận cross-database commit. Thiếu quyền tạo support
objects phải báo trước; sample environment tự chuẩn bị. Collision object signature phải fail.

APPEND/UPSERT commit mỗi batch cùng ledger, retry query ledger dưới target lock, verify checksum;
không chứng minh commit thì NEEDS_RECONCILIATION, không replay. FULL_REFRESH chuẩn bị toàn bộ
mapped rows vào disk staging, một transaction DELETE được ủy quyền + batched INSERT + final
ledger + verification; commit đúng một lần, không TRUNCATE/DROP/ALTER target. External readers
ở READ COMMITTED hoặc mạnh hơn thấy old/new; READ UNCOMMITTED không được hỗ trợ integrity.

**Lý do**: Cần marker cùng transaction với dữ liệu để giải quyết mất phản hồi COMMIT.
Session native lock bị ràng buộc với chính writer nên heartbeat app lease không tự tạo split-brain.
Không có distributed transaction với app_metadata; metrics/binding ở đó là projection vận hành.

**Phương án đã cân nhắc**: Chỉ app DB lease hoặc checkpoint file có cửa sổ commit không rõ;
TRUNCATE rồi load batch mất atomicity MySQL; rename swap vi phạm không ALTER table cũ.

**Nguồn**: [PostgreSQL advisory locks](https://www.postgresql.org/docs/current/explicit-locking.html),
[MySQL GET_LOCK](https://dev.mysql.com/doc/refman/8.4/en/locking-functions.html),
[MySQL implicit commit](https://dev.mysql.com/doc/refman/8.4/en/implicit-commit.html).

## 7. UPSERT đúng conflict key

**Quyết định**: PostgreSQL dùng ON CONFLICT theo constraint/column set đã validation.
MySQL dùng UPDATE JOIN theo chosen key rồi INSERT các chosen key chưa có trong cùng batch
transaction; mọi duplicate khác gây rollback, không INSERT IGNORE/REPLACE.
Native ON DUPLICATE KEY UPDATE không dùng cho target nhiều independent unique keys vì
không chỉ định được conflict target như PostgreSQL. Prepared target-typed temporary validation
table có unique key/collation đúng target để bắt duplicate toàn dataset trên đĩa trước load;
DDL scratch thực hiện trước target DML transaction, không thay cấu trúc table người dùng.

**Lý do**: Không update nhầm row khi unique phụ trùng row khác chosen key. UPSERT chỉ update
mapped non-key fields; không dùng affected_rows làm Loaded Rows. External writers ngoài ứng dụng
không nằm trong cam kết phối hợp; database constraint vẫn là hàng rào cuối.

**Phương án đã cân nhắc**: Dùng MySQL native upsert mù, Python set chứa mọi key hoặc SQLite
collation khác target đều có rủi ro correctness/bộ nhớ.

**Nguồn**: [PostgreSQL INSERT/ON CONFLICT](https://www.postgresql.org/docs/17/sql-insert.html),
[MySQL duplicate key](https://dev.mysql.com/doc/refman/8.4/en/insert-on-duplicate.html).

## 8. Công việc nền và Compose

**Quyết định**: Một backend-worker từ cùng backend image nhận durable Operation trong
app_metadata với FOR UPDATE SKIP LOCKED, lease/heartbeat. Worker xử lý validation, DDL,
deploy/reconcile/cleanup; không lập lịch hoặc thực thi ETL thay Airflow. Không Redis/Celery.
Compose thêm secrets-init/app-init/airflow-init one-shot, depends_on healthy/completed;
readiness kiểm tra truy vấn thật và schema version, không chỉ HTTP 200.

**Phương án đã cân nhắc**: FastAPI BackgroundTasks mất việc khi restart; thực thi ETL trong
HTTP request sai ranh giới. Chỉ initdb.d không đủ migration khi volume đã tồn tại.

**Nguồn**: [Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/),
[Airflow health](https://airflow.apache.org/docs/apache-airflow/3.3.2/administration-and-deployment/logging-monitoring/check-health.html).

## 9. Workbook thực tế ở bước thiết kế

**Quyết định**: Tạo hai template .xlsx và hai sample workbook bằng openpyxl 3.1.5 như artifact
thiết kế, không tạo module ứng dụng. Schema/version và mọi instruction tiếng Anh; endpoint tải
là hợp đồng sẽ triển khai, chưa nhận là API đã chạy. Excel validations hỗ trợ nhập liệu nhưng
server validator vẫn là nơi quyết định. Không có câu hỏi nghiệp vụ chặn thiết kế.

**Nguồn**: [openpyxl optimized modes](https://openpyxl.readthedocs.io/en/stable/optimized.html).

## 10. Ma trận phiên bản đã chọn

| Nhóm | Pin |
| --- | --- |
| React / React DOM | 19.2.0 / 19.2.0 |
| TypeScript / Vite / plugin-react | 5.9.3 / 7.3.7 / 5.1.1 |
| Tailwind / @tailwindcss/vite | 4.1.18 / 4.1.18 |
| shadcn CLI | 3.5.0; component source được commit, không coi CLI là runtime library |
| React Router | react-router 7.18.5, declarative mode |
| TanStack Query | @tanstack/react-query 5.90.10 |
| Form / resolver / Zod | react-hook-form 7.66.0 / @hookform/resolvers 5.2.2 / zod 4.6.7 |
| Frontend build image | node:22.23.4-bookworm-slim |
| Static web image | nginx:1.30.6-alpine3.24 |
| Backend image | python:3.12.16-slim-bookworm |
| PostgreSQL / MySQL image | postgres:17.11-bookworm / mysql:8.4.13 |
| FastAPI / Pydantic | 0.136.3 / 2.13.5 |
| SQLAlchemy / Alembic | 2.0.52 / 1.20.0 |
| psycopg[binary] / PyMySQL | 3.3.5 / 1.1.3 |
| openpyxl / defusedxml | 3.1.5 / 0.7.1 |
| cryptography / httpx / python-multipart | 50.0.1 / 0.28.1 / 0.0.32 |
| Uvicorn / pytest | 0.38.0 / 8.4.2 |
| Playwright | @playwright/test 1.65.0, browser install cùng version; container mcr.microsoft.com/playwright:v1.65.0-resolute nếu dùng CI |
| Airflow runtime | apache/airflow:slim-3.3.2-python3.12, constraints3.3.2/Python3.12 |

Metadata npm/PyPI và23 package/image requests đã kiểm tra tồn tại thành công, nguồn và
kết quả từng mục ở [dependency-verification.json](contracts/dependency-verification.json).
Backend shared pins lấy từ constraints chính thức; không khẳng định metadata existence bằng
build compatibility. Vite/plugin yêu cầu Node20.19+ hoặc22.12+; Node22.23.4 đáp ứng.
Resolver/Zod4, React19, Tailwind4 và Vite7 được chọn cùng generation; verify peerDependencies,
npm ci/build/typecheck và pip check trên cả backend/Airflow là gate Phase1, chưa chạy ở Plan.

Pin là baseline tái lập, không khẳng định là patch mới nhất hoặc đã security scan. Phase1
scan image/dependency và cập nhật patch nếu cần bằng decision log/lockfile; không dùng latest.
OCI digest được resolve và ghi vào lock của implementation từ tag exact, không bịa digest.
Playwright browser/image phải đúng1.65.0 theo B đã duyệt, không ghép browser latest với client cũ.

**Nguồn bổ sung**: [Vite7/Node requirements](https://v7.vite.dev/guide/migration),
[metadata React](https://registry.npmjs.org/react/19.2.0),
[metadata Vite](https://registry.npmjs.org/vite/7.3.7),
[metadata form resolver](https://registry.npmjs.org/@hookform%2Fresolvers/5.2.2).

## 11. Vòng đời quyền FULL_REFRESH sau Clarify

**Quyết định**: Áp dụng 5 câu trả lời tại Spec BR-08. ONCE được giữ độc quyền bằng
RunIntent trước khi gọi Airflow tạo run; Operation và RunIntent có định danh bền.
Reservation và thu hồi khóa cùng row authorization bằng PostgreSQL `SELECT FOR UPDATE`.
Run đã binding lấy native target lock, đối soát ledger rồi chốt ReplacementAdmission
trong transaction app DB ngắn trước target DML. Thu hồi và admission cùng khóa row quyền,
vì vậy có thứ tự commit rõ ràng. Không giữ app transaction suốt extraction/load.

**Lý do**: Row lock serialize quyết định cấp/thu hồi trong app DB, nhưng không làm app DB
và target DB commit atomic. Admission là điểm chấp thuận, không phải bằng chứng target
đã bắt đầu/commit. Mất phản hồi admission phải đọc lại cùng identity trước DML;
target commit chỉ được chứng minh bằng ledger trong target transaction.
Admission đã chốt trước thu hồi chỉ cho phép transaction đã chấp thuận hoàn tất/rollback;
không cho retry ghi mới sau thu hồi hoặc tái sử dụng ONCE cho Run ID mới.

**Phương án đã cân nhắc**: Giữ quyền đến trước DELETE cho nhiều run cạnh tranh trái Q1;
trả quyền về chưa dùng sau extraction failure trái Q2; giải phóng theo heartbeat hoặc
coi app projection là commit proof đều bị loại. Không thêm transaction phân tán/2PC.

**Phân loại run**: Public API Airflow 3.3.2 có `DAGRunResponse.run_type` bắt buộc,
tham chiếu `DagRunType`: backfill, scheduled, manual, operator_triggered,
asset_triggered, asset_materialization. Chỉ `scheduled` đúng lịch/revision đã xác nhận
dùng SCHEDULED; `manual` cần ONCE đã reservation qua ứng dụng. Các loại còn lại không
được nhận quyền SCHEDULED trong MVP. Không suy run type từ prefix hoặc `conf`.

**Nguồn đã đối chiếu**:
- [PostgreSQL 17 — Row-Level Locks](https://www.postgresql.org/docs/17/explicit-locking.html#LOCKING-ROWS):
  row lock chặn updater/locker khác và nhả ở transaction end/rollback savepoint.
- [PostgreSQL 17 — SELECT locking clause](https://www.postgresql.org/docs/17/sql-select.html#SQL-FOR-UPDATE-SHARE).
- [OpenAPI Airflow đúng tag 3.3.2](https://raw.githubusercontent.com/apache/airflow/3.3.2/airflow-core/src/airflow/api_fastapi/core_api/openapi/v2-rest-api-generated.yaml):
  `DAGRunResponse.run_type` và enum `DagRunType`.

**Quyết định đồng bộ contract**: Bổ sung history APIs, parser revision API và các response
typed thiếu trong Analyze; không thay requirement gốc hoặc stack. Tên target ledger vật lý
được chuẩn hóa tại Data Model. Số operation/schema phải lấy từ contract hiện tại, không
đóng đinh baseline 40 khi thiết kế đã mở rộng. Workbook1.0 và sample bytes không thay đổi.

## 12. Rà soát có mục tiêu sau Analyze bản152task (2026-11-08)

### Private runtime và namespace

**Quyết định:** Giữ `http://backend:8000/internal/runtime/bind` là URL canonical;
operation OpenAPI đã override server về `http://backend:8000`. Router private nằm ngoài
`/api/v1`; frontend trả404 cho cả `/internal/runtime` và `/api/v1/internal/runtime` cùng
path con trước proxy/fallback. Kiểm qua frontend kể cả khi có bearer hợp lệ; gọi trực tiếp
canonical vẫn kiểm bearer và identity/version. Không tạo public alias.

**Lý do:** Kiểm lại artifact thấy override đã tồn tại; nhận định Analyze thiếu override
được rút lại. Phần cần làm rõ là yêu cầu proxy và kiểm chứng hai biến thể, không phải đổi
URL hiện hữu. **Phương án loại:** di chuyển private endpoint vào public router hoặc chỉ
kiểm một prefix, khiến alias/fallback có thể không được kiểm thử.

### Runner sớm và gate foundation

**Quyết định:** Phase1 tạo runner pytest/Playwright và Compose test profile tối thiểu;
Phase2 mở rộng fixtures/harness nền; Phase3 nghiệm thu Connections E2E trên runner đã có.
Playwright client/browser/image cùng1.65.0 theo B đã duyệt, fixtures project/volumes/namespaces độc lập.
Phase8 chỉ mở rộng regression. Gate Phase2 chỉ schema/repositories/migrations/seed/
Operation recovery/readiness; Connections CRUD và Settings API nghiệm thu tại Phase3/7.

**Lý do:** T138 hiện nằm sau các gate E2E bắt buộc, gate Phase2 còn nhắc API chưa triển khai.
**Phương án loại:** đợi Phase8 hoặc lặng lẽ cài runner local ngoài task, vì không tái lập
được prerequisite. Chỉ đổi vị trí hạ tầng kiểm thử, không thay ưu tiên core hoặc8phase.

### Bytes mẫu và phạm vi authorization

**Quyết định:** Thiết kế `.gitattributes` pin LF cho `samples/data/*.csv` và `*.txt`,
giữ XLSX binary; xác minh SHA256 raw giữa checkout Windows/Linux và seed. Không normalize
upload. Lượt này không đổi sample bytes. Authorization giữ state BR-08, không thêm TTL/
EXPIRED; sửa tên test `authorization expired` thành revoked/invalidated và tách test token
xác nhận10phút hết hạn khỏi idempotency replay.

**Lý do:** Git index LF/working tree CRLF giải thích chính xác hai sample hashes lệch;
normalize trong bộ nhớ để chẩn đoán khớp manifest lịch sử, không chứng minh raw bytes khớp.
BR-08/model/API không định nghĩa authorization expiration. **Phương án loại:** cập nhật
manifest theo EOL mỗi máy hoặc suy TTL quyền từ token xác nhận, vì làm mất tính tái lập
hoặc đổi nghiệp vụ. Không có unknown nghiệp vụ mới cần nghiên cứu/Clarify trong phạm vi này.

## Remediation dependency T014 bổ sung — 2026-11-09

dnspython2.9.0 vá CVE-2026-114605 theo
[maintainer advisory](https://github.com/rthalley/dnspython/security/advisories/GHSA-45c3-73f7-pv4m).
Chọn override có hash riêng, không sửa constraints upstream hoặc nâng Airflow core.
Không cài setuptools top-level để giả vá bản ghi `AnalyzedBy: sbom` của artifact khác.
Phương án core/OS và bằng chứng cần kiểm tại
[round3 remediation](../../docs/proposals/t014-round3-remediation.md).

## Kết luận nghiên cứu

Các quyết định blocking đã được chốt. Không còn placeholder hoặc câu hỏi nghiệp vụ;
version resolution/build, API integration, data integrity và stress tests là gate thực thi
của implementation, không là bằng chứng đã có. Các thiết kế tiếp theo dùng đúng ma trận này.

Đối chiếu bổ sung peerDependencies từ registry ở [peer-dependencies.json](contracts/peer-dependencies.json):
react-dom19.2 yêu cầu React^19.2; plugin-react5.1.1 và Tailwind Vite4.1.18 đều nhận Vite7;
resolver5.2.2 nhận RHF^7.55, RHF7.66/TanStack5.90/Router7.9 nhận React19;
Node22.23.4 vượt minimum22.12 của Vite/plugin. Đây là kiểm metadata peer ranges,
không thay npm resolver/full build/transitive lock hoặc test compatibility trên containers.

## 13. Podman theo bản sửa đã duyệt ngày 2026-11-08

**Quyết định:** Cho phép Docker hoặc Podman theo Constitution1.1.0; baseline dự án hiện
chọn Podman client5.8.3/server5.8.9 trên WSL Linux/amd64/cgroupv2/rootful và provider Docker
Compose5.6.0. Giữ Compose/Dockerfile hiện có, named volumes/health/init/resources/secret
semantics. Lệnh startup baseline là `podman compose up --build -d`; pin provider và ghi đủ
phiên bản trong evidence. Fully qualified registry refs/digests tránh short-name ambiguity.

**Lý do:** Engine/provider đã phản hồi trên máy hiện tại, không cần cài Docker Desktop;
quy tắc Docker-only trước đây cần sửa quản trị trước khi nghiệm thu Podman. Chủ dự án đã
phê duyệt [bản sửa](../../docs/proposals/podman-support.md); thêm lựa chọn nên tăng MINOR,
không nới safety hoặc đổi BR-08. Memory metadata WSL khác memory engine quan sát được,
cần kiểm actual cgroup/free disk thay vì suy từ config.

**Phương án loại:** alias Docker rồi coi đã test Docker; đổi provider/rootful machine toàn
cục không ghi nhận; bỏ service_healthy/limits/volume permissions để stack chạy. Build,
install/pip check Linux, nginx và toàn stack vẫn NOT_RUN, client/server khác phiên bản
phải kiểm compatibility thực tế chứ không tự đổi version.

**Nguồn:** [Podman5.8.3 compose](https://docs.podman.io/en/v5.8.3/markdown/podman-compose.1.html)
quy định external provider/selection; [Podman Desktop Compose](https://podman-desktop.io/docs/compose/setting-up-compose)
hướng dẫn xác minh provider. Không dùng tài liệu hoặc lệnh help thay integration tests.

## Quyết định ngoại lệ local có hạn

LEX-003 dùng backport Bookworm cùng version trong OS lock, không nâng distro/core.
Đã resolve artifact và chain Debian InRelease→Packages→deb SHA256; cài offline trước
network trong Airflow stage. Quyết định D1/D2/D4 tại `docs/decisions/t014-local-gate-approval.md`;
reviewer chưa ký LEX-003/D3, nên chưa mở Phase2.

Cơ chế chỉ có hiệu lực khi chủ dự án ký quyết định theo đề xuất conditional local.
Risk acceptance khác reviewed not-affected; NO_FIX/build-only không tự miễn trừ.
Giữ raw scan/severity/SBOM, T014_FULL BLOCKED khi chưa đủ full acceptance.
Không nâng core hoặc rebase hàng loạt chỉ để kích hoạt local. Theo dõi owner/hạn/thu hồi
và khép full security trước khi mở rộng triển khai.
