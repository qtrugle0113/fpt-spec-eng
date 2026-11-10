# Checkpoint DAG Builder — 2026-11-10

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

