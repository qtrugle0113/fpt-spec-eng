# Checkpoint DAG Builder — 2026-11-10

## Hiện hành sau tiếp tục

T104–T112 đã khép phạm vi riêng. T109 có worker/fixed wrapper đăng ký thật và
reconcile mất phản hồi ghi file PASS; owner migration/grants đã kiểm. T110/T111
grant/list/detail/revoke7PASS qua HTTP/PG thật. T112 public trigger→fixed wrapper
→private bind→ETL→target2rows đã PASS thật. T113 activation/state đã PASS;
tiếp T114 deploy API và wizard.
Chưa có UI→deploy→ETL trọn luồng và chưa nghiệm thu MVP. T014_FULL vẫn BLOCKED.

T104 đã kiểm scheduler/Task SDK thật: `t104-resume-prestart/` có2/2 PASS,
normal1attempt và SIGKILL extraction2attempts cùng binding; target đúng2rows,
metrics loaded2, COMMIT_VERIFIED/commit_uncertain=false, generations COMPLETE hoặc
EXPIRED→COMPLETE. Airflow healthy, cleanup9/9 exit0, không published ports hoặc
service hiện hữu bị sửa. Phạm vi UI→deploy→ETL vẫn chưa nghiệm thu.

Nguyên nhân hai lượt `t104-resume-current/` và `t104-resume-origins/` FAIL là
fixture khởi động scheduler trước copy source. Scheduler đã import cả hai package
từ site-packages trong image; task kế thừa module cũ, đổi sys.path không thay được.
Driver nay create→copy→start; assertion nguồn module giữ nguyên và hai ca SDK PASS.
Chẩn đoán chỉ ghi module paths/classes/frame locations, không raw logs/SQL/secrets.

Máy hiện tại không có IDs399adacf/87507379/b659185 của logs trước. Dùng đúng mapping
đã duyệt tại phase2-resume-airflow-review, phase2-resume-security-review và
phase5-us3-image-review: Airflow/runner b5e9745e…, PG c93823be…, workbook libs
b1943b23…. Exact IDs/source hashes/commands selectors trong fixture-results và
source-sha256 tương ứng. Không rebuild hoặc đổi dependency/security exception.
Hai checklist16/16,48/48 PASS; quyền local còn hạn23/11, review16/11; T014_FULL BLOCKED.

Các phần bên dưới giữ lịch sử; không dùng trạng thái T104 mở ở checkpoint cũ
thay trạng thái hiện hành phía trên.

### T105/T106 sau T104

- T105 `t105-resume-final/`:4/4PASS import generated Python bằng SDK3.3.2 thật.
  Một task execute_etl, no XCom, retries/delay hữu hạn, stable canonical bytes,
  UUID/hash validation, extra credentials bị từ chối, literal nguy hiểm không chạy.
  Cron/timezone/Catchup theo config đã validate; Catchup mặc địnhfalse, DAG mới
  luôn paused kể cả config is_paused=false (FR-037). Task wording được làm rõ
  default để không bỏ cấu hình Catchup hợp lệ tại FR-034/BR-04.
- T106 `t105-t106-resume-red/` có4errors storage chưa tồn tại; lượt này còn một
  lỗi test dùng timetable.summary không có trong SDK. Đã kiểm DAG.schedule thật
  và sửa truy vấn assertion, không bỏ kiểm cron.
- T106 `t106-resume/`:4/4PASS trên Linux: UUID filename/hash, fsync→replace→parent
  fsync, lỗi trước rename giữ file cũ và dọn temp, lỗi sau rename giữ file mới
  nguyên vẹn để reconcile, chặn root/destination symlinks. Root mặc định khớp
  Compose backend-worker `/data/generated_dags`; không dùng DAG ID làm path.
- Backend Dockerfile đã copy fixed template; chưa build/scan image source mới.
  Các kết quả này chưa chứng minh generated DAG được đăng ký hoặc chạy; phần đó
  tiếp tục T107–T120. T014_FULL giữ BLOCKED.

### T107 admission/redeploy

`t107-resume-red/`:3errors trước implementation. `t107-resume-expanded/`:14PASS
gồm6admission trên registry PG thật và8factory/storage regression. Airflow facts
trong6ca này là test double cô lập: gate đóng trước lookup, forged aat tag không
chiếm DAG ngoài, outage giữ blocked, pause/drain, queued run xuất hiện sau check
chặn publication, revision đổi trong I/O bị chặn. Không cancel run.

`t107-real-airflow/`:2SDK ca PASS, có controller prepare/assert_ready chạy qua
Public API thật trên DAG vừa chạy ETL: exact file/tag/last verified version khớp,
pause readback=true, existing run vẫn success, gate BLOCKED. Cleanup9/9 exit0.
T107 khép primitive; chưa có public deploy worker/UI. `t108-resume/`7PASS kiểm
lại6admission sau bổ sung owner/version number/UUID artifact identity và1registration
evidence. Các kiểm bổ sung T107/T108 ngay dưới là trạng thái mới hơn.

### T107/T108 kiểm bổ sung

`t107-new-revision-red/` tái hiện controller từ chối revision mới vì so con trỏ
current với candidate thay vì last verified deployment. Đã sửa expected-current
theo previous deployment; không đổi current trước registration. `t107-t108-final/`
11PASS gồm7admission (có revision mới) và4registration/polling.
`t108-polling/`8PASS gồm polling/deadline và client regression;
`t108-real-airflow/`2PASS chạy verifier owner/hash/file/published timestamp/version
trong fixture SDK thật, rồi ETL normal/retry và controller redeploy thật. Cleanup0.
T107/T108 khép primitive. Không dùng các kết quả này thay deploy worker/UI acceptance.

### T109 worker và migration

- `t109-resume-red/`:2errors trước worker/migration; unique operation_id cũ chặn
  nhiều DAG cùng yêu cầu. Data Model đã làm rõ unique(operation_id,dag_id).
  Migration0005 chỉ đổi constraint này, giữ unique active DAG và mọi grants.
- `t109-recovery/`:3PASS registry/disk thật, gồm durable rename rồi response loss,
  reconcile đọc cùng file/hash và không gọi writer lần hai. Registration evidence
  trong suite này là test double cô lập, không dùng thay Airflow.
- `t109-real-recovery/`:4PASS trên SDK/Airflow thật: ETL normal và SIGKILL retry,
  worker render fixed wrapper→atomic publish→owner/hash/file/parse/version verified,
  cùng ca durable publication mất response rồi reconcile thật không republish.
  Registry DEPLOYED, gate OPEN, DAG paused và0runs; cleanup9/9 exit0.
- `t109-worker-lease/`:4PASS, worker hết lease không dispatch file, các ca recovery
  và nhiều DAG vẫn qua. `t109-final-fences/`:10PASS worker/admission regression.
- `t109-owner-migration/` NOT_RUN vì chọn runner Airflow không có pytest.
  `t109-owner-migration-rerun/`:1PASS trên backend-tests6b65b34d…: concurrent init
  bằng owner không superuser, Alembic head0005, seed và runtime grants. Không chạy
  migration trên volume người dùng. Chưa build/scan image source mới.

### T110/T111 đang làm

`t110-red/` thiếu service; `t110-grant/`3PASS: grant/replay, empty acknowledgment,
SCHEDULED trên Manual bị từ chối, target và idempotency mismatch. T110 còn kiểm
cron/credential invalidation. `t111-red/`HTTP grant404 đúng vì route chưa có.
Preview bổ sung definition_id theo contract để UI dùng parent UUID canonical cho
authorization endpoints; id vẫn là revision UUID, không tạo alias parent/revision.

Kết quả mới hơn: `t110-final/`4PASS gồm cron SCHEDULED hợp lệ và credential
rotation làm authority cũ INVALIDATED. `t110-t111/`7PASS gồm grant/list/detail/revoke
HTTP theo contract, ETag1→2, replay cùng key/If-Match cũ trả identity cũ, key mới
với ETag cũ412, missing404 và thiếu empty acknowledgment422. T110/T111 khép phạm
vi riêng; thời điểm đó trigger/state chưa có. Các kết quả tiếp theo ghi dưới đây.

### T112 public trigger và generated ETL

- `t112-red/` thiếu service trước implementation. `t112-trigger/`2PASS/1ERROR do
  concurrent FULL_REFRESH previews tranh native lock và TargetBusy chưa được ánh
  xạ. Đã map TARGET_BUSY409/retryable, không bỏ native lock.
- `t112-reservation/`3PASS; `t112-worker/`5PASS; `t112-maintenance/`14PASS gồm6trigger
  với metadata thật và8client/registration regression. RunIntent/ONCE persist
  trước POST, run_id=`manual__aat_<operation UUID>`, hai requests không chuyển
  ONCE, SCHEDULED không cấp quyền manual, revoke trước dispatch đóng ONCE không POST.
  POST mất response→GET cùng ID; outage cả hai giữ uncertainty/reservation và
  maintenance chỉ GET, không POST lại. Airflow facts trong6ca là test double.
- `t112-real-trigger/`5PASS trên Airflow thật. Ca mới gọi public trigger HTTP202,
  worker submit→SDK fixed factory→canonical private bind→restricted aat_etl role
  →DB source/target thật. Target `(1,first),(2,NULL)`, binding COMMIT_VERIFIED,
  intent trỏ đúng trigger operation. Không gọi fixture helper để inject DSN vào
  generated callable: scheduler dùng runtime secret files/keyring/volumes và
  hostname backend/postgres cô lập như wiring sản phẩm. Không thay product code
  hoặc dependency để né fixture.
- Activation trong ca này dùng Public API trực tiếp do fixture gọi sau khi assert
  initial paused=true/runs0; product activation còn T113. Marker paused/runs ở
  log worker là trạng thái ban đầu, không phải trạng thái sau trigger. Không suy
  ca APPEND PG này thành tám routes hoặc UI acceptance. Cleanup9/9 exit0.

### T113 activation/state

`t113-red/` thiếu service; `t113-controls/`15PASS controls/authorizations gồm
ONCE không cho bật lịch FULL_REFRESH, SCHEDULED đúng schedule/revision, If-Match
và replay, negative headers/consent. `t113-response-loss/`1PASS với2command
activate/pause: PATCH mất response nhưng GET khớp; Scheduled authority vẫn GRANTED,
không gửi command cancel run hoặc revoke.

`t113-real-activation/`5PASS: thay fixture unpause trực tiếp bằng PATCH public202
và activation worker có ownership/file/hash/version/readback thật, rồi public
trigger→fixed wrapper→restricted role ETL→target2rows. Các ca SDK retry, worker
publication/reconcile và admission thật vẫn PASS; cleanup0. T113 khép primitive;
cron execution/tám routes/lifecycle/UX còn T118–T120 và phần cuối. Monitoring sẽ
dùng lại primitives, không tạo control implementation khác.

Tiếp tục sau gate engine T095, theo speckit-implement. Phạm vi local/ngoại lệ security
giữ nguyên; T014_FULL BLOCKED. Không commit/push, publish port hoặc dùng volume cũ.

## Khả năng sử dụng thực tế

API đã tải template ETL gốc và lưu upload ETL cùng hash/history. UI wizard, validation
toàn registry, deploy DAG, Airflow execution và monitoring chưa nghiệm thu; người dùng
chưa có luồng UI → Airflow → dữ liệu đích hoàn chỉnh.

## Bằng chứng

- `resume-20261110/t096-builder-contract-red.log`: RED trước implementation,
  11 tests/9 failures; unittest lúc đó collect lại bốn tests do import class ở module
  authorization. Đã đổi sang module import để tránh chạy lặp. Lỗi thể hiện template
  route chưa có, ETL upload bị từ chối, deploy/trigger/state chưa có. Một số safe404
  PASS không chứng minh resource handlers đã triển khai. T096 vẫn mở; còn positive
  deployment/authorization/idempotency/race coverage để hoàn thiện và chạy PASS.
- `t098-etl-artifact-green.log`:2 PASS, template nguyên bytes/ETag và ETL upload→GET
  giữ hash/status. `t098-artifact-bytes.log`:3 PASS trên host, bytes mọi template/sample
  đúng manifest, không sửa artifacts. Không tuyên bố sample ETL đã chạy Airflow.
- `t099-etl-parser-red.log`:7 errors vì module chưa có, trước implementation.
- `t099-etl-and-table-parser-green.log`:11 PASS gồm7 ETL parser tests và4 Table parser
  regression. Parser ETL dùng lại bounded ZIP/OpenXML, version/sheet/header guards;
  kiểm max100 DAG, duplicates/cross-sheet, source union, lịch/IANA/DST, policy/ranges,
  mapping/default scalar và structured filter. Registry/type/key compilation còn T100.

## Tiếp tục validation/preview

- `t100-preview-wiring-green.log`:10 PASS gồm API validation→worker→persisted typed
  preview và8 parser tests, sample ETL seed references đã PASS. Workbook sai không
  công bố definition và có issue row2.
- `t100-preview-safety-green.log`:6 PASS, schema drift làm confirmation unavailable;
  source/target cùng physical table và UPSERT key không unique bị chặn; inbound FK
  chặn FULL_REFRESH trên PG/MySQL; một dependency sai chặn toàn bộ workbook.
- `t100-file-and-publication-green.log`:16 tests,4 subcase failures ở file preview.
  Đã xác định compile dùng DB-only preflight với FileSchema và synthetic text không
  phù hợp Type Conversion; lượt `t100-file-preview-fix` đã PASS hai hướng PG, còn
  hai hướng MySQL fail quyền.
- `t100-file-preview-diagnostic` chỉ ra grant scope MySQL escape underscore
  (`etl\_test`), không phải thiếu quyền thật. Helper dùng chung nhận exact scopes,
  không suy arbitrary wildcard/role expressions thành quyền. Không cấp thêm grant
  hoặc đổi ngoại lệ security. `t100-escaped-mysql-grants-green.log`:10 PASS gồm đủ
  bốn hướng file preview, duplicate revision không kẹt VALIDATING, safety suite,
  privilege scope negative controls và bootstrap MySQL thật/idempotent.

Source hiện có ETL_VALIDATE worker, whole-workbook publication trong savepoint,
revision/mapping immutable, kiểm dependency/checksum và route etl-preview. Những
thay đổi đó chưa được build vào app image hoặc nghiệm thu trên browser. T100 còn
kiểm permissions/column/default/diff và confirmation races trước khi khép task.

T097 đã chạy fixture Airflow thật healthy, không published ports. Lượt đầu schema
path sai404; đã đối chiếu source image và dùng `/openapi.json`. Schema công bố
info.version=`2` là API version, khác phiên bản package Airflow3.3.2; test đang sửa
để kiểm riêng hai giá trị, không hạ pin. Schema/hash thật giữ trong
`t097-schema-red/`. Client/registration chưa có nên RED đúng, chưa nghiệm thu T097.

## Checkpoint API, Airflow client và bind

- T098: sample references tồn tại trong registry đã seed thật, ca PASS riêng trong
  `t103-runtime-bind-red.log`; các failures cùng lượt thuộc binder chưa triển khai.
  Download/hash và artifact bytes có bằng chứng phía trên; không đổi workbook.
- `t100-read-write-privileges-green.log`:2 PASS, tài khoản PG readonly không thể làm
  target; tài khoản không có SELECT nguồn bị chặn. Preview bình thường vẫn PASS.
- `t100-column-and-writer-green.log`:3 PASS, metadata length/default literal/PK đúng
  trên PG/MySQL, bốn hướng file preview và regression MySQL replacement/consumed retry.
- `t100-confirmation-race-green.log`:1 PASS, đổi current connection revision sau live
  compile làm preview409, không phát confirmation.
- `t100-scope-and-consent-green.log`:3 PASS, FULL_REFRESH an toàn vẫn yêu cầu quyền và
  acknowledgment làm rỗng riêng; token chốt100revision nằm trong giới hạn16384bytes và
  sửa revision cuối làm token cũ bị từ chối; import errors match full path.
- Column có server default expression không thể biểu diễn thành TypedLiteral được
  nêu rõ bằng warning, không đánh giá expression hoặc giả thành default NULL. PK vẫn
  hiện riêng. Preview recheck current dependencies sau I/O và chốt cả parent revision.
- T101 RED4errors trước implementation; `t101-client-bounds`4 PASS;
  `t101-real-api/t097-airflow-contract.log`7 PASS gồm API/auth thật và transport faults.
  Schema/hash khớp image3.3.2, API version2; không dùng schema latest hoặc hạ pin.
- T102 RED3errors trước implementation; `t102-real-api`11 PASS;
  `t102-parsed-dags`8 PASS trên205DAG SDK paused thật: đủ pagination, details/version
  UUID+number, lookup bằng number, run inventory, pause PATCH→GET và health component.
  Đây là fixture API, không phải deploy workbook ETL.
- T103 RED6tests với1failure/4errors, sample seed test PASS; binder policy lượt đầu
  còn lỗi ambiguous ORM join ở route valid bearer, đã sửa explicit FK join.
  `t103-canonical-bind`5 PASS: root401/403, alias404, missing revision404 đúng handler,
  idempotent APPEND, gate/version rejection, manual ONCE và scheduled/backfill rules,
  existing binding sau revoke vẫn đọc đối soát. API facts trong policy tests là input
  cô lập; không dùng chúng thay Airflow thật.
- `t103-live-bind/t103-real-ti-bind-green.log`:1 PASS, SDK task running thật, backend
  xác minh run/TI/version/owner/hash qua Public API, bind đúng revision và reuse ID,
  request version giả409, response không credentials. Task fixture chỉ sleep, target
  pins là metadata synthetic, không tuyên bố ETL đã load. ResourceWarning socket được
  xử lý bằng đóng shared client tại FastAPI lifespan; chờ kiểm shutdown mới.

T098/T099/T100/T101/T102 đủ evidence trong phạm vi riêng.

## Checkpoint bind và adapter runtime

- `t103-binding-races`7 ca PASS, còn1 lỗi fixture parser snapshot ban đầu. Fixture
  được sửa để giữ nguyên original UploadedFile snapshot và chỉ đổi current parser
  pointer. Lượt `t103-parser-snapshot` vẫn FAIL do fixture thử sửa delimiter bất biến;
  `t103-parser-pointer`1 PASS sau sửa đúng. Không sửa/hạ guard để test qua.
- Có bằng chứng concurrent first bind chỉ một binding/intent, revoke trước bind chặn
  FULL_REFRESH, source file pin parser UUID/SHA và binding cũ giữ nguyên snapshot.
- `t103-live-shutdown/t103-real-ti-bind-green.log`1 PASS trên task SDK running thật,
  bao gồm assert đóng shared client tại lifespan; không còn ResourceWarning socket.
  T103 khép phần protocol/repository/private route. Nginx deny-prefix giữ nguyên
  evidence T005; direct canonical401/403 và public alias404 đã kiểm sau khi route có.
- T104 test-first `t104-runtime-adapter-red`2tests/3errors do chưa có module.
  `t104-direct-runtime`9 PASS gồm hai target thật dưới metadata role `aat_etl`,
  callback xác minh COMPLETE/native session đã commit trước INSERT, same-binding
  final-marker reconciliation không replay, private bind503 và7 Connection/DNS
  regression cases. Backend/runtime dùng chung exact allowlist/DNS pinning.
- `t104-restricted-admission` FAIL cả hai target vì role thật không được khóa
  run_intents. Migration0004 và apply_grants chỉ cấp UPDATE(last_reconciled_at),
  đủ SELECT FOR UPDATE; intent state/authorization/run_uuid/revision vẫn không có
  quyền UPDATE. Không thay security waiver hoặc chạy migration trên volume cũ.
  `t104-runtime-intent-lock`2 PASS: FULL_REFRESH PG/MySQL thay đúng fixture target và
  ONCE CONSUMED; negative role tests vẫn chặn grant/scope/state/delete.

T104 đang hoàn thiện file recovery, uncertainty fencing, SDK supervisor và retry
lifecycle. Chưa nối generated DAG → adapter hoặc UI wizard. Các task T096/T097
vẫn mở cho deployment/authorization/registration acceptance. Không dùng kết quả này
thay image/Airflow ETL/UI E2E; T014_FULL vẫn BLOCKED.

## Checkpoint recovery và supervisor của adapter

- `t104-file-recovery` ban đầu có1 PASS/1 FAIL: recovery map quá prefix đã commit
  và gặp conversion lỗi ở tail chưa ghi. `t104-prefix-proof`1 PASS sau khi chỉ map
  prefix có marker, vẫn verify checksum và dataset/binding/strategy của marker.
- `t104-recovery-fence-red` tái hiện late recovery project sau khi owner đổi.
  Worker nay khóa authorization → intent → binding → lease, so owner/native session
  đã inspect; owner đổi trả OWNER_FENCE_CHANGED, không clear uncertainty của writer mới.
- `t104-recovery-owner`18 PASS trong49.278s trên PG/MySQL: adapter role thật,
  file partial/final recovery, commit-response loss, finite retry và cleanup/retention.
  Prefix chứng minh cập nhật loaded/validated đúng phần biết chắc; failed_rows vẫn NULL.
- `t104-child-red`1 ERROR do module chưa có; `t104-child`1 PASS gồm process con
  thật trên PG/MySQL và gọi lại binding không ghi trùng. `t104-child-safety`4 PASS
  gồm metadata admission outage, same-target uncertainty, error classification và
  parent-death SIGKILL. Chưa phải generated DAG hoặc UI E2E.

## Checkpoint T104 lifecycle — tiếp tục phiên mới

- `t104-lifecycle-red`:3 ca,1 FAIL/2 ERROR; prefix lỗi vẫn RUNNING/uncertain và
  chưa có lifecycle module. `t104-lifecycle`:4 PASS/1 FAIL; ca source kill chưa tới
  điểm injection vì fixture owner-change trước đó giữ reservation gần10GiB.
  Chỉnh cleanup riêng fixture sau assert refusal; không giảm quota sản phẩm.
- `t104-lifecycle-isolated`:7 PASS trong14.627s. Child SIGKILL giữa extraction được
  reap, owner fence đúng, chưa có target writer → retire generation INCOMPLETE,
  release đúng reservation có journal và retry cùng ONCE intent thành công.
  Terminal extraction failure đóng ONCE thành CLOSED; không trả quyền về GRANTED.
- Owner thay đổi chặn cleanup. Manifest COMPLETE trên đĩa nhưng metadata chưa
  publish được giữ lại và chặn re-extract. File lỗi sau committed prefix project
  FAILED/loaded2/failed_rows=NULL, giữ dataset COMPLETE để đối soát.
- Journal riêng chỉ có PID/owner/binding/allocation IDs, fsync trước reservation
  commit hoặc ghi staging. Không dùng stale heartbeat làm bằng chứng child chết.
  SDK quản lý finite retries; engine runtime override0 tránh nhân số lần retry.

Đang kiểm adapter trong scheduler/Task SDK thật bằng fixture cô lập mới, private
HTTP bind và target DB thật. T104 chưa khép trước kết quả. UI vẫn chưa có wizard
deploy/monitoring trọn luồng. Không đổi image baseline/waiver; T014_FULL BLOCKED.

Các lượt SDK đầu chưa PASS:

- `t104-real-sdk`: runner vô tình collect thêm lớp preview được import trực tiếp,
  khiến các ca MySQL ngoài selector fail vì fixture chỉ có PG. Hai ca SDK mới cũng
  fail: file chưa được quét trong120giây hoặc task import runtime lỗi. Đã sửa import
  TestCase/selector, không hạ assertions. Lượt này14tests/7failures, không nghiệm thu.
- Cấu hình thực tế `dag_processor.refresh_interval` là300giây, không đáp ứng gate
  registration120giây khi thêm file sau startup. Compose local và fixture nay dùng5giây;
  không đổi dependency/security baseline hoặc service đang chạy của người dùng.
- `t104-sdk-focused`:2 FAIL do callback runner không tìm được module runtime hiện tại.
  Thêm ưu tiên source path và assert import origin trong fixture SDK, tránh dùng nhầm
  wheel cũ từ reviewed image. Logs chỉ lưu exception classes/frame locations, không
  raw exception/SQL/locals/credentials. Shared logs/private/staging/DAG volumes đều mới,
  fixture-owned; cleanup lượt focused trả0 cho mọi tài nguyên.
- `t105-factory-red`:3 ERROR vì factory chưa có; chỉ chuẩn bị test-first, chưa triển khai
  trước khi dependency T104 được kiểm chứng.

