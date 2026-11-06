# Hợp đồng tích hợp Apache Airflow 3.3.2

## Phạm vi và xác thực

Public API base nội bộ `http://airflow-apiserver:8080/api/v2`; browser UI base
`http://localhost:8080`. Backend là client duy nhất phục vụ browser, runtime bind endpoint
cũng xác minh identity qua client này. Không gọi `/ui`, không query Airflow metadata DB.

SimpleAuthManager với service user `aat_service` role admin trong môi trường local tin cậy;
password seed một lần qua private file theo định dạng provider. Backend POST /auth/token,
nhận JWT, giữ memory, refresh trước hết hạn hoặc retry auth một lần sau401; không trả token
về frontend và không lưu vào DAG/log/XCom. Official Airflow token exchange là giao thức auth
service; database credentials ứng dụng tuyệt đối không trả qua API. Rate limit/backoff và
permission errors khác connectivity errors. Airflow UI có thể yêu cầu login riêng bằng local
Airflow user được init, không tạo login trên UI ứng dụng. Không bật all-admin anonymous.

Image pin `apache/airflow:3.3.2-python3.12`, schema nguồn đúng
[OpenAPI 3.3.2](https://raw.githubusercontent.com/apache/airflow/3.3.2/airflow-core/src/airflow/api_fastapi/core_api/openapi/v2-rest-api-generated.yaml).
Implementation lưu bản schema/hash và test contract với image, không dùng schema latest động.

## Endpoint mapping

Tất cả path bên dưới nối sau `/api/v2`; path segment phải percent-encode.

| Nghiệp vụ | Method/path | Quy tắc |
| --- | --- | --- |
| List DAGs | GET /dags | limit/offset, lấy đủ trang; không chỉ100DAG đầu |
| DAG metadata | GET /dags/{dag_id} | ownership tags, paused/active, fileloc theo response |
| DAG details | GET /dags/{dag_id}/details | latest_dag_version object nullable, parse/schedule metadata |
| Pause/unpause | PATCH /dags/{dag_id} | body is_paused boolean, đọc xác nhận lại |
| Versions | GET /dags/{dag_id}/dagVersions | paginated; version UUID dùng identity, number dùng path dưới |
| Version cụ thể | GET /dags/{dag_id}/dagVersions/{version_number} | path nhận integer version_number, không UUID |
| Run history | GET /dags/{dag_id}/dagRuns | pagination, trạng thái/timestamps từ Airflow |
| Run detail | GET /dags/{dag_id}/dagRuns/{dag_run_id} | response dag_versions là array, không có scalar dag_version_id |
| Trigger | POST /dags/{dag_id}/dagRuns | dag_run_id stable, logical_date:null, conf object không secret |
| Task instances | GET /dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances | status, attempt; dag_version object trên TI |
| Task detail | GET /dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances/{task_id} | wrapper task execute_etl, map_index=-1 khi cần |
| Log | GET /dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances/{task_id}/logs/{try_number} | full_content=false, map_index=-1, query token |
| Import errors | GET /importErrors | filename/path matching và timestamp; không gán lỗi DAG khác vào deployment |
| Health | GET /monitor/health | đọc JSON metadatabase/scheduler/dag_processor, không chỉ status200 |

Trigger body chính xác: dag_run_id=`manual__aat_<operation_uuid>`, logical_date=null, conf={};
logical_date là trường bắt buộc dù nullable trong3.3.2. Có thể thêm conf tham chiếu revision
không secret cho run managed, không tự giả conf của scheduled runs. 409 hoặc timeout phải GET
cùng run_id để reconcile, không sinh UUID mới. Không auto retry POST chưa biết kết quả.

Đối với FULL_REFRESH manual, API phải commit ONCE reservation/RunIntent và Operation trong
app DB trước POST trên. RunIntent chưa phải ExecutionBinding; bind chỉ tạo sau TI version
đã xác minh. GET cùng run_id đọc `run_type` từ `DAGRunResponse`, không suy từ prefix/conf.
SCHEDULED chỉ nhận `scheduled`; `manual` cần ONCE đúng intent; `backfill`,
`operator_triggered`, `asset_triggered`, `asset_materialization` không được dùng quyền lịch
trong MVP. Manual FULL_REFRESH tạo trực tiếp trên Airflow UI thiếu ONCE intent bị chặn.
Scheduled run bind tham chiếu quyền SCHEDULED còn hiệu lực và scope/schedule hash đúng.
`is_paused=false` cho lịch FULL_REFRESH cần SCHEDULED, không dùng ONCE để authorize toàn lịch.

Log JSON response có content array và continuation_token nullable; request tiếp theo dùng
query `token`, không `continuation_token`. Giới hạn mỗi page1MiB hiển thị; redact trước trả;
structured logs được normalize thành timestamp/level/message, không HTML raw.

## Deployment và admission

1. Persist operation/idempotency/config SHA và expected revision. Kiểm DAG ID local/Airflow;
   external owner bị từ chối, không nhận ownership chỉ dựa prefix aat_.
2. Đóng admission transaction ứng dụng, pause qua API và xác nhận. Drain tất cả queued/running
   runs, không chỉ task running. Race run vừa tạo phải được kiểm lại; runtime startup kiểm gate
   nên không có ETL mới chạy trong chuyển revision. Có run chưa kết thúc thì deployment fail/busy,
   không tự cancel run để vượt qua; giữ paused khi chưa xác minh an toàn.
3. Atomic write file wrapper trên shared DAG volume cùng filesystem; chỉ fixed template import
   SDK/controlled engine, DAG ID/config literal serialization an toàn. Config không có secret,
   artifact ngoài allowlisted root bị từ chối. File naming dùng internal UUID, không DAG ID raw.
4. Poll 1/2/4giây rồi cap5giây+jitter, tổng120giây. Đối chiếu owner tag, revision hash,
   fileloc, parsed timestamp sau deployment và latest_dag_version.id/number; import errors cùng file.
   Cùng config/hash đã verified có thể no-op, không yêu cầu version number tăng giả.
5. Save version mapping; re-open admission đúng revision. DAG mới vẫn paused. Redeploy DAG
   trước active chỉ phục hồi trạng thái khi revision/API/ủy quyền verified; lỗi giữ paused và
   trả revision cuối đã biết, không tự ghi đè metadata báo success.

LocalDagBundle không giữ code lịch sử. Runtime bind kiểm TI.dag_version.id đối chiếu deployment,
wrapper expected revision và binding; historical clear sau redeploy bị reject `REVISION_MISMATCH`.
Task retry chỉ chạy cùng immutable dataset/config, không lấy code/config mới để chạy run cũ.
Đây là tradeoff có chủ đích thay GitDagBundle; có test old-clear bắt buộc.
Với FULL_REFRESH, clear/retry cùng run có final marker VERIFIED chỉ đối soát, không thay
dữ liệu lần hai. Thu hồi quyền không tương đương Pause hoặc cancel; Pause không thu hồi
quyền tự động và revoke không tự hủy transaction đã có admission. Runtime kiểm quyền tại
ranh giới [replacement admission](runtime.md), không dùng trạng thái Airflow làm commit proof.

## Dashboard và performance API

Không mirror DAG Runs vào app DB. Cache memory tối đa30giây kèm fetched_at/completeness;
refresh thủ công invalidate. Phân trang200items và giới hạn4request đồng thời, retry GET tối đa3,
backoff cho429/503; connect timeout3giây, read timeout10giây. Request vượt tổng30giây báo
incomplete/unavailable, không tổng hợp trang đầu như tổng. Không cam kết lifetime nếu source
retention/API không cung cấp đủ lịch sử; không làm application DB thành bản sao lịch sử.

Inventory hiện tại tách run metrics theo date range. Có thể lấy run qua từng DAG khi API batch
không cung cấp đúng trường; không giả định endpoint thống kê undocumented. Filter theo actual
start hoặc queued/created fallback, không logical_date; tính timezone/range theo BR-11.
State queued/other giữ riêng; schedule history thiếu dùng Unknown. Cache key gồm scope/date/
timezone/ownership; stale khác zero. Deep link dùng `/dags/{encoded_dag_id}` trên UI base, kiểm
bằng Playwright trên version3.3.2 thay suy đoán hostname container.

## Lỗi và phục hồi

401 refresh token một lần;403 hiển thị permission error;404 DAG/run không tồn tại;429 honor
Retry-After; network/5xx là unavailable. Timeout command không chứng minh thất bại side effect.
Backend UI request không retry command mù; durable operation reconcile khi khôi phục API.
Airflow scheduled task đang chạy vẫn có thể tiếp tục khi Dashboard/backend mất kết nối;
chỉ run startup chưa bind phải fail-safe. Không cập nhật run success trong app DB thay Airflow.
