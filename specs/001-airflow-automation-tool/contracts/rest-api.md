# Hợp đồng REST API ứng dụng

**Phiên bản**: /api/v1. **Nguồn máy đọc được**: [openapi.yaml](openapi.yaml).
Đây là thiết kế; API chưa chạy. Runtime OpenAPI /openapi.json và Swagger /docs phải khớp
contract ở implementation. Mô tả tiếng Việt; message hiển thị trên UI tiếng Anh.

## Quy ước chung

ETL preview item có `id` là revision UUID và `definition_id` là parent UUID để
gọi `/etl-definitions/{id}/replacement-authorizations`. Hai identity tách biệt;
không suy parent từ DAG ID hoặc dùng revision làm alias của parent. Table preview
không cần definition_id. Trường bổ sung không thay workbook1.0.

Local single-operator, không login. Chỉ bind loopback; CORS allow origin http://localhost:3000,
không wildcard credentials; reject Origin lạ cho mutating requests, CSRF/origin protection
cho local browser. Network DB host allowlist mặc định postgres/mysql; operator có thể cấu
hình env thêm host rõ ràng. Không coi host/port user nhập là cơ chế SSRF an toàn cho môi trường
public; ngoài local không thuộc phạm vi. Không cho HTTP URL hoặc path làm database host.

UUID cho resource ID; DAG/Run IDs là string percent-encoded. Pagination limit mặc định50,
max200, offset>=0; trả items/total/next_offset, total=null khi source thiếu bằng chứng.
Time UTC RFC3339 và timezone IANA rõ ở filter/display. Không truyền database password trong
query string/response. Create/rotate password write-only, GET chỉ has_password=true/false.

PATCH cấu hình cần If-Match revision/ETag, stale412; mutating long operations cần
Idempotency-Key UUID và confirmation_token hash-bound. Cùng key khác payload409; cùng payload
trả operation cũ. Token xác nhận là opaque signed token10phút, gắn upload/checksum/revision/
source-target schema/scope, không chứa secret; dependency đổi thì stale-confirmation409.

Response201 cho tạo metadata/upload,202 cho job,204 cho xóa metadata không dependency;
400 request sai,404 không tồn tại,409 dependency/conflict/confirmation stale,412 stale update,
413 quá size,422 validation,503 dependency unavailable,504 timeout biết chắc request thất bại.
Side effect chưa rõ trả operation state NEEDS_RECONCILIATION, không dùng504 để cho phép auto-replay.

## Tác vụ đồng bộ và bất đồng bộ

CRUD/list/details/template/settings/preview sau validation là đồng bộ, timeout hữu hạn.
Upload stream xuống disk, không parse toàn workbook trong HTTP lifecycle. Test Connection
đồng bộ tối đa30giây. Full file/workbook validation, table execution, deploy/reconcile và
trigger command là Operation durable202, worker xử lý bằng transaction ngắn, frontend poll.

Operation trả id/kind/state/progress/result_links/error/created_at/deadline; terminal gồm
SUCCEEDED, PARTIALLY_SUCCEEDED, FAILED, NEEDS_RECONCILIATION. Một operation có nhiều DAG/table
results; không coi queued là success. Poll1giây tăng đến5giây; dừng terminal, có Retry-After.
Không FastAPI BackgroundTasks làm nguồn lưu việc, không chạy ETL trong API worker.

## Danh mục endpoint

| Method/path sau /api/v1 | Dữ liệu chính | Kết quả |
| --- | --- | --- |
| GET /connections | search/type/status/limit/offset | ConnectionPage không password |
| POST /connections | ConnectionCreate với password write-only | 201 ConnectionPublic |
| GET /connections/{id} | UUID | Chi tiết và dependency refs |
| PATCH /connections/{id} | ConnectionPatch + If-Match | Revision mới/needs_revalidation |
| DELETE /connections/{id} | UUID + If-Match | 204 hoặc409dependency |
| POST /connections/{id}/test | revision hiện tại | TestResult thật <=30giây |
| GET /files | filter/limit/offset | SourceFilePage |
| POST /files | multipart file + parser_json | 201 SourceFile, chưa full validated |
| GET /files/{id} | UUID | Metadata không physical path |
| PATCH /files/{id}/parser | ParserConfig + If-Match | Parser revision mới; active/recovery409 |
| GET /files/{id}/preview | max_rows<=100 | Columns/typed rows/parser/limited |
| POST /files/{id}/validate | expected checksum/parser revision | 202 Operation |
| POST /definition-uploads | multipart kind TABLE/ETL và file | 201 DefinitionUpload |
| GET /definition-uploads | kind/status/date/limit/offset | Lịch sử upload bền, không cần ID từ browser |
| GET /definition-uploads/{id} | UUID | Status/version/checksum |
| POST /definition-uploads/{id}/validate | optional selected target connection cho TABLE | 202 Operation |
| GET /definition-uploads/{id}/issues | limit/offset | Issues có vị trí thật |
| GET /definition-uploads/{id}/table-preview | target resolved | Tables/columns/results + confirmation token |
| GET /definition-uploads/{id}/ddl-preview | validated upload | DDL theo table/dialect, không execute |
| GET /definition-uploads/{id}/etl-preview | validated upload | DAG config/mapping/schedule/load warnings + token |
| POST /table-creation-jobs | upload_id/confirmation_token | 202 Operation/result job link |
| GET /table-creation-jobs | upload/target/state/date/limit/offset | Lịch sử tạo table theo job |
| GET /table-creation-jobs/{id} | UUID | Per-table results/SQL/partial status |
| GET /table-definitions/{id} | UUID | Định nghĩa/columns/PK/results và introspection DB thật hoặc unavailable |
| POST /dag-deployments | upload_id/dag_ids/confirmation_token/support_acknowledged | 202 Operation/per-DAG deployments |
| GET /dag-deployments/{id} | UUID | State/revision/registration/error/reconcile_required |
| POST /dag-deployments/{id}/reconcile | same operation identity | 202 Operation, không tạo revision mới ngầm |
| POST /etl-definitions/{id}/replacement-authorizations | revision/physical target/scope/allow_empty/acknowledgment | 201 Authorization, không execute dữ liệu |
| GET /etl-definitions/{id}/replacement-authorizations | limit/offset | Quyền của DAG với trạng thái và scope |
| GET /replacement-authorizations/{id} | UUID | Reservation/state/revocation/acknowledgment không secret |
| POST /replacement-authorizations/{id}/revoke | If-Match + Idempotency-Key + acknowledgment | 200 Authorization, không cancel/rollback transaction đã admission |
| GET /operations/{id} | UUID | Durable operation trạng thái thật |
| GET /dags | search/ownership/paused/latest_status/pagination | DAGPage từ Airflow |
| GET /dags/{dag_id} | encoded ID | Details + managed definition link nếu có |
| GET /dags/{dag_id}/runs | date/state/limit/offset | RunPage từ Airflow |
| GET /dags/{dag_id}/runs/{run_id} | encoded IDs | Run/tasks/engine metrics nếu managed |
| POST /dags/{dag_id}/trigger | confirmation/authorization nếu cần | 202 Operation, stable Airflow run_id |
| PATCH /dags/{dag_id}/state | is_paused/expected_revision/confirmation | 202 Operation, active phải kiểm quyền/revision |
| GET /dags/{dag_id}/runs/{run_id}/tasks/{task_id}/logs | attempt/token/map_index | Redacted logs/content/next token |
| GET /dashboard | from/to/timezone/scope | Inventory+date metrics/lifetime/completeness/fetched_at |
| GET /settings | Không | SettingsPublic và connectivity status |
| PATCH /settings | allowed fields + If-Match | Validated settings/revision |
| GET /templates/table-definition | Không | XLSX attachment |
| GET /templates/etl-definition | Không | XLSX attachment |
| GET /health/live | Không | Process alive, không secrets |
| GET /health/ready | Không | app DB/schema/worker/Airflow dependencies ready hoặc503 |

Settings ETag bao phủ toàn bộ bốn defaults: revision public là tổng revision của
bốn ApplicationSetting rows đã seed. GET lấy snapshot nhất quán; PATCH khóa các
row theo key, kiểm revision rồi cập nhật atomic. DB trigger tăng revision từng
row được ghi; response đọc lại sau flush. Stale trả412, readonly/null/boolean ở
integer fields và timezone không hợp lệ trả422. Defaults mới chỉ áp dụng cấu
hình mới; preview revision cũ giữ batch size đã resolve ở lần validation.

Private endpoint `/internal/runtime/bind` dùng runtime service bearer từ secretfile, không
được expose qua frontend proxy; verify identity/version qua Airflow, response chỉ binding/
reference/config. Credential lookup đi trực tiếp application metadata encrypted records theo
role runtime, không có endpoint decrypt hoặc password export.

URL canonical giữa containers là `http://backend:8000/internal/runtime/bind`.
Operation OpenAPI đã có `servers: [{url: http://backend:8000}]`, override base `/api/v1`
của public API; không ghép prefix public vào endpoint private. Backend đăng ký router
runtime ngoài router `/api/v1`; `/api/v1/internal/runtime/bind` không có route alias.
Nginx frontend trả 404 cho cả prefix `/internal/runtime` và `/api/v1/internal/runtime`
(đúng prefix hoặc path con), trước public API proxy và SPA fallback, không redirect.
Runtime gọi backend trực tiếp bằng bearer; việc backend publish loopback8000 cho operator
không bỏ xác thực private endpoint.

Kiểm chứng implementation: qua frontend3000, POST cả hai biến thể `/bind`, có và không
bearer hợp lệ, đều404 và không tới backend; GET cũng không trả SPA fallback. Gọi trực tiếp
backend canonical không bearer/sai bearer bị401/403, bearer hợp lệ vẫn phải qua kiểm tra
identity/version; gọi trực tiếp biến thể `/api/v1/internal/runtime/bind` luôn404.

## Hợp đồng lỗi

ErrorResponse gồm error.code ổn định, message tiếng Anh, request_id UUID,
retryable boolean, operation_id optional và details array. Detail có scope workbook/sheet/cell/
resource, sheet/row/column/column_name nullable, message và code. Không echo credentials,
connection DSN, local file path hoặc nguyên dữ liệu nhạy cảm.

Ví dụ message: `Target table has no matching unique key`, `Deployment could not be verified`,
`Source file is no longer available`. Frontend không tự dịch stack trace DB thành thông báo;
Backend sanitize theo SQLSTATE/driver error class, fallback `Connection failed` nếu không phân loại được.

## Contract dữ liệu chuyên biệt

- Table preview chứa normalized target, ordered columns, PK list, DDL và cảnh báo existence;
  xác nhận không tự ALTER/DROP. Table runtime failure trả result theo table.
- ETL preview có source union/type inferred, target, mapping/type compatibility,
  schedule/timezone/catchup/load/key/retry, support DDL và data replacement acknowledgment.
- Dashboard có inventory, run_metrics, lifetime_metrics, schedule_groups, time_series,
  recent_runs, timezone/from/to, completeness, unavailable_fields, fetched_at/stale.
  Missing totals/null khác0; lifetime thiếu không được ghi chính xác.
- Log response giới hạn1MiB/page, token opaque; không đặt JWT/secret trong token người dùng nhận.
- Runtime API/task commands cần schema strict extra=forbid; SQL identifiers/host/path và filter
  validation phía Backend dù frontend đã dùng Zod. Zod/React Hook Form chỉ hỗ trợ UX.

- Connection response có dependencies resource refs, needs_revalidation và test invalidation.
- Column preview có length/precision/scale/primary_key_ordinal/default_literal/has_default/
  description; default null hợp lệ khác không có default. Decimal/date/time trả dạng lossless,
  không dùng JSON number float cho decimal. ETL config/mapping/source/target/schedule typed.
- DAG/Dashboard có last_successful_run nullable và trạng thái AVAILABLE/UNAVAILABLE/UNKNOWN;
  run/task có error_summary nullable; logs thiếu có reason; metrics có phase/protected bytes/
  recovery summary, không giả0 khi chưa biết.
  last_successful_run là kết quả lifetime trong phạm vi DAG/ownership đã chọn, không bị
  date filter đổi thành last-success trong kỳ; UI phải ghi nhãn lifetime. Thiếu bằng chứng
  lịch sử không bảo đảm kết luận thì availability UNKNOWN/UNAVAILABLE và không đoán từ
  recent_runs. Metric lọc ngày vẫn có from/to/timezone riêng theo BR-11.

## Workflow parser revision

Upload nhận parser_json ban đầu. Preview có thể nhận parser_json dự kiến qua query để đọc
tối đa100dòng, không persist/validate toàn file. Operator xác nhận bằng PATCH parser với
If-Match ETag; content/reference không đổi, parser revision tăng và full validation cũ mất
hiệu lực. File có active/recovery binding trả409; Definition/DAG phụ thuộc cần revalidate/
xác nhận revision mới trước chạy, không sửa run đã bind. Payload parser phải qua cùng
validation/byte cap như upload/execution; không echo source data vào query log.

## Hợp đồng ủy quyền FULL_REFRESH

MVP không định nghĩa TTL, `expires_at` hoặc state EXPIRED cho authorization. Quyền bị
chặn theo state/revocation/scope và các ranh giới BR-08. Confirmation token10phút là
đối tượng khác: token hết hạn không thu hồi quyền đã cấp hoặc giải phóng ONCE reservation.
Test phân biệt request mới với token hết hạn và replay cùng Idempotency-Key/hash trả
intent cũ; không thêm cơ chế authorization expiration từ tên ca kiểm thử.

AuthorizationRequest có confirmation_token hash-bound revision/physical target/schedule,
acknowledged=true và allow_empty=false mặc định. Khi allow_empty=true cần
allow_empty_acknowledged=true riêng; response công bố acknowledgment và scope hash.
GET list/detail cho phép UI khôi phục trạng thái sau restart thay dựa vào local storage.
Create authorization cũng cần Idempotency-Key: cùng request trả quyền cũ, khác payload409;
không cấp nhiều quyền do double submit cùng xác nhận.

ONCE trigger: transaction khóa authorization row, kiểm quyền/phạm vi rồi tạo Operation
và RunIntent stable, reservation trước POST Airflow. Cùng Idempotency-Key/hash trả
operation/intent cũ kể cả token đã hết hạn; payload khác409. Yêu cầu mới dùng ONCE đã
reservation cho run khác trả409 `AUTHORIZATION_ALREADY_RESERVED`, không tạo run mới.
ONCE consumed/closed/revoked/invalidated không cấp mới; timeout trigger giữ reservation,
worker reconcile GET cùng run_id. Retry không gọi trigger để sinh Run ID mới.

Revoke cần acknowledged=true, If-Match và Idempotency-Key; replay cùng request trả kết quả
đã lưu, khác payload409, stale ETag412. Transaction revoke khóa cùng row quyền với runtime
admission. Response có revoked_at và replacement_in_progress để UI nêu
`Revocation does not cancel a replacement already admitted`; giá trị unknown phải null,
không false giả. Revoke không xóa binding/markers/artifacts; recovery đọc vẫn được phép.
Admission đã commit trước revoke chỉ cho giao dịch đã chấp thuận hoàn tất/rollback,
không retry DML mới. Quyết định target commit lấy ledger, không lấy response revoke/admission.

SCHEDULED chỉ run Airflow `scheduled` đúng scope; manual trigger cần ONCE và activation
FULL_REFRESH cron cần SCHEDULED. Thay revision/target/strategy/lịch/timezone/start date/
catchup/scope invalidates quyền cũ và allow_empty. Không tự gia hạn/chuyển scope.

Các lỗi nghiệp vụ public phân biệt `AUTHORIZATION_REVOKED`, `AUTHORIZATION_SCOPE_MISMATCH`,
`AUTHORIZATION_ALREADY_RESERVED`, `EMPTY_REPLACEMENT_NOT_AUTHORIZED`,
`REPLACEMENT_RECONCILIATION_REQUIRED`; message tiếng Anh, request_id/operation_id khi áp dụng,
không raw SQL/credential.

## Liên kết Airflow từ kết quả deployment

`Deployment.airflow_url` là URL UI công khai cho DAG, lấy origin từ
`AAT_AIRFLOW_PUBLIC_URL` (mặc định `http://localhost:8080`). Compose dùng cùng
`AAT_AIRFLOW_PORT` với cổng UI được công bố. Origin phải là HTTP/HTTPS, không có
userinfo, query hoặc fragment. Frontend hiển thị **Open Airflow** sau khi trạng
thái là DEPLOYED; liên kết không thay bằng chứng run đã thực thi thành công.

## Bằng chứng serialized revision khi redeploy

Wrapper cố định ghi revision UUID và canonical hash vào task params. Registration
đọc task definition từ public Airflow API, đối chiếu hai giá trị và đọc lại latest
version sau đó. Tag và last_parsed_time mới không đủ khi serialized DAG còn ở bản
cũ do giới hạn tần suất ghi của Airflow. Params chỉ là bằng chứng đăng ký; runtime
vẫn dùng expected revision cố định của wrapper và xác minh run/TI/binding, không
lấy quyền từ params/conf có thể do người gọi trigger cung cấp.

## Metadata điều khiển trong Monitoring

DAG managed có thể trả `definition_id`, `revision_id`, `upload_id`, `deployment_id`
để UI lấy review/confirmation từ preview hiện có. Detail trả ETag generation để
PATCH state qua primitive đã có. External trả các liên kết metadata này là null;
tag `aat` đơn lẻ không cấp ownership hoặc quyền điều khiển. Run có `revision_id`
từ binding bất biến khi có; task có `map_index` để đọc đúng log attempt của mapped
task. Không sao chép lịch sử run Airflow vào application DB.

FR-067 đã làm rõ theo quyết định chủ dự án: trigger nhận run queued khi native
DAG paused. Không tự unpause. Operator xác nhận state command riêng; cron
FULL_REFRESH vẫn kiểm SCHEDULED authority. Operation SUCCEEDED không có nghĩa
run đã được thực thi hoặc đã commit dữ liệu.

## Khoảng ngày và khả dụng Dashboard

GET Dashboard dùng ngày lịch `from`/`to` YYYY-MM-DD, gồm trọn ngày cuối theo IANA
timezone; tối đa366ngày cho time series hữu hạn. Lifetime độc lập với bộ lọc ngày.
`scope` là ALL/MANAGED/EXTERNAL; `force_refresh=true` bỏ qua cache của lần đọc đó.
Cache tối đa30giây, giảm theo refresh interval khi cấu hình dưới30giây.
`next_scheduled_runs` giữ timestamp và native pause state do Airflow cung cấp.

History được stream theo trang, không lưu mirror hoặc gom mọi payload vào RAM.
Giới hạn100.000run/lần đọc và deadline30giây; chạm giới hạn/thay total/mất page
phải trả INCOMPLETE với số liệu không khả dụng, không báo tổng thiếu là chính xác.
Schedule lúc run chỉ lấy từ immutable binding/intent revision; thiếu là Unknown,
không suy từ lịch hiện tại. Source outage có cache cũ phải gắn stale/completeness
không khả dụng, không giả snapshot mới thành công.
