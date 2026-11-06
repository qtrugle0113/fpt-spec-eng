# Hướng dẫn khởi động và kiểm chứng

**Trạng thái tài liệu**: Hướng dẫn nghiệm thu cho implementation sắp thực hiện.
Ở bước Plan đã có tài liệu, hợp đồng API và workbook .xlsx; chưa có docker-compose.yml,
application source code, endpoint hoặc test suite. Các lệnh chạy ứng dụng bên dưới chỉ dùng
sau khi các phase tương ứng được triển khai, không phải kết quả đã chạy thành công.

## Điều kiện đầu vào

- Docker Engine/Desktop với Linux containers và Composev2>=2.24; host khuyến nghị8CPU,
  12GiBRAM,80GiB disk trống. Có quyền pull/build images và các cổng3000/8000/8080 chưa bị chiếm.
- Clone workspace implementation, đứng ở root. Không cần Python/Node trên host để dùng app.
- Một operator local, app bind127.0.0.1; không dùng cấu hình này làm triển khai Internet.
- .env là optional: default local đủ để boot, không bắt copy .env.example hoặc tự tạo secret.
  Secret key và account service tạo tự động trên volume, không in ra log.

## Một lệnh khởi động

```powershell
docker compose up --build -d
```

Lệnh detached kết thúc trước khi mọi initialization xong. Đợi trạng thái sẵn sàng bằng các
lệnh đọc sau, không phải setup bổ sung:

```powershell
docker compose ps -a
docker compose logs --tail 100 secrets-init db-init app-init airflow-init
Invoke-RestMethod http://localhost:8000/api/v1/health/ready
```

Kỳ vọng: init services Exited(0), services dài hạn healthy, readiness status READY và các
required dependencies HEALTHY. HTTP200 đơn thuần chưa đủ để xác nhận Airflow scheduler/
dag-processor khỏe. DB role/migrations/seed/Airflow account/network phải tự chuẩn bị.
Nếu init fail, xem error chẩn đoán; không reset/xóa volume để biến lỗi thành trạng thái sạch.

| Thành phần | URL trên browser | URL giữa containers |
| --- | --- | --- |
| Ứng dụng | http://localhost:3000 | http://frontend:80 |
| Backend/OpenAPI | http://localhost:8000/docs | http://backend:8000 |
| Airflow UI/API | http://localhost:8080 | http://airflow-apiserver:8080 |
| PostgreSQL | Không publish host mặc định | postgres:5432 |
| MySQL | Không publish host mặc định | mysql:3306 |

Ứng dụng không login. Airflow UI có account local riêng do init tạo; operator xem account
operator qua cơ chế quản trị secret của môi trường, không qua application API hoặc logs.
Backend tự dùng service account/JWT; thao tác ứng dụng không cần operator login Airflow trước.

## Kiểm chứng template thiết kế hiện có

Artifact thực tế ở root templates và samples/definitions, quy tắc ở
[contracts/excel-definitions.md](contracts/excel-definitions.md). Hai template rỗng đều version1.0,
Instructions!A1/B1 và sheet/header đúng hợp đồng; hai sample có nhiều table/DAG.
Mở bằng Excel/LibreOffice để xem instruction, comments và dropdown. Không kích hoạt macro;
workbook không có công thức metadata. Download endpoint chỉ có sau implementation.

Bằng chứng cấu trúc/hash/size nằm ở [template-artifacts.json](contracts/template-artifacts.json);
đó không phải kết quả parser/application hoặc data transfer test.

## Workflow nghiệm thu với dữ liệu mẫu

1. Mở Connections, xác minh pg_etl và mysql_etl trỏ đúng hostname nội bộ và có test thật.
   Source/target khác table dù cùng connection. Không dùng localhost làm DB host trong container.
2. Tải Table Definition hoặc dùng samples/definitions/Table Definition.sample.xlsx.
   Upload/Validate, kiểm preview table/columns/PK/DDL, rồi Confirm Create Tables.
   Sample có customers_target/customers_archive tại pg_etl.public; table đã có trả ALREADY_EXISTS,
   không xóa table cũ để test lại. Dùng tên table riêng cho lượt nghiệm thu mới.
3. Kiểm dataset mẫu customers_source ở PostgreSQL/MySQL và target MySQL customers_target
   được seed trong namespace mẫu. File mẫu samples/data/customers.csv và customers.txt
   được app-init đăng ký UUID11111111-1111-4111-8111-111111111111 cho CSV;
   TXT có UUID22222222-2222-4222-8222-222222222222. Giữ parser và checksum gắn nội dung.
4. Upload ETL Definition.sample.xlsx. Kiểm hai DAG/column mapping khác tên,
   source/target/key/strategy và request support objects trong preview. Confirm Generate/Deploy.
5. Theo dõi Deployment Pending đến Deployed hoặc lỗi thật. Xác minh đúng revision qua Airflow;
   DAG mới Paused. Open in Airflow phải mở đúng DAG ID trên localhost8080.
6. Trigger manual DAG managed; theo dõi queued/running/success/failed từ Airflow và engine
   row metrics. Đối soát target values/NULL/decimal, không chỉ nhìn task success.
7. Chạy lại UPSERT cùng dữ liệu3lần: số key không tăng; APPEND lần hai phải cảnh báo và
   thêm đúng dữ liệu. FULL_REFRESH cần xác nhận target/revision/scope/allow_empty riêng.
8. Tạo cron DAG mỗi phút, Start Date/timezone rõ, Catchup FALSE; activate sau confirmation,
   chờ scheduled run thật xuất hiện history. Manual trigger không đổi periodic schedule.
9. Dashboard chọn khoảng ngày/timezone, kiểm DAG count khác run count, queued/other riêng,
   success rate denominator chỉ success+failed, missing/stale có nhãn. Không chấp nhận mock số liệu.

10. Với FULL_REFRESH manual, preview đúng target/revision rồi tạo quyền ONCE với
    allow_empty=false; trigger phải reservation trước Airflow POST. Gửi lặp cùng request
    chỉ một RunIntent/Run ID; run khác dùng quyền đó bị409. Extraction retry cùng run
    giữ quyền, run terminal thất bại/hủy đóng quyền và rerun cần ONCE mới.
11. Với cron FULL_REFRESH, xác nhận SCHEDULED đúng scope/lịch trước activate. Manual
    trigger cùng DAG vẫn cần ONCE; kiểm run_type từ Airflow API, không dùng prefix.
    allow_empty=true cần acknowledgment riêng về mọi run theo lịch có thể làm rỗng target;
    lỗi nguồn không được xem là zero rows. Thay scope/lịch/revision cần xác nhận mới.
12. Thu hồi quyền từ UI/API, kiểm revoked_at/state và thông báo không cancel transaction
    đã admission. Dùng barrier test để revoke trước admission (không target ghi) và sau
    admission (giao dịch đã chấp thuận hoàn tất/rollback). Commit-response-loss giữ
    quyền/artifact chờ đối soát; retry/clear run đã commit không replacement lần hai.
13. Mở browser mới và truy xuất Upload/Creation History qua API phân trang; không cần IDs
    trong local storage. Table detail phân biệt định nghĩa với introspection DB đã verified.
    Sửa parser bằng preview cấu hình dự kiến rồi PATCH/If-Match: content ID giữ nguyên,
    parser revision tăng, validation/dependency stale; active/recovery source bị409.

Hợp đồng endpoint/response/acknowledgment ở [REST API](contracts/rest-api.md) và
[OpenAPI](contracts/openapi.yaml); lifecycle/commit boundaries ở [Runtime](contracts/runtime.md).
Các bước mới chỉ thực hiện khi task tương ứng đã implementation, không là test đã PASS.

## Các lệnh kiểm thử sau implementation

Compose test profile dự kiến có backend-tests (backend test image với root tests/ và pytest),
e2e-tests (Playwright1.56.1 image với browser cùng version). Chúng không cần cho startup mặc định.

```powershell
docker compose --profile test run --rm backend-tests pytest tests/unit tests/api
docker compose --profile test run --rm backend-tests pytest tests/integration tests/etl
docker compose --profile test run --rm backend-tests pytest tests/airflow
docker compose --profile test run --rm e2e-tests npx playwright test
```

Stress test riêng chạy trên dataset>1GiB và >20batch với worker budget512MiB; không dùng test
unit nhỏ làm bằng chứng bounded memory. Lưu maximum RSS, staging disk bytes/checksum, source
snapshot/target counts và full output. Container test log không được ghi secret.

```powershell
docker compose --profile test run --rm backend-tests pytest tests/stress -m large_data
```

Fixtures độc lập, tên table/DAG duy nhất theo lượt test và cleanup chỉ namespace test đã tạo;
không DROP/DELETE/TRUNCATE dữ liệu người dùng để reset suite. Test failures phải giữ đủ evidence.

## Các tình huống lỗi phải kiểm

| Tình huống | Cách kiểm chứng và kỳ vọng |
| --- | --- |
| Workbook thiếu sheet/header, duplicate/orphan | Lỗi đúng vị trí thật, không side effect; test A/B/P/AL |
| UPSERT target thiếu key/key bị xóa sau deploy | Validation/runtime preflight chặn, không tự ALTER/index |
| Source mất giữa extraction | Fail/RETRY snapshot mới trước load; FULL_REFRESH giữ target cũ |
| Target mất sau một batch commit | Giữ partial, marker giúp retry không duplicate; commit không rõ phải reconcile |
| Hai DAG cùng target qua hai codes | Một writer giữ native lock, run sau chờ/timeout300giây |
| Worker kill không finally | Sau restart reconcile owner/ledger trước retry/GC; không giành khóa chỉ vì stale |
| Staging full/I/O/corrupt | Fail an toàn, quota reserve có hiệu lực; không fallback RAM/xóa protected artifacts |
| FULL_REFRESH lỗi giữa transaction | Old data còn/rollback, không TRUNCATE trước hoặc commit từng batch |
| API timeout sau trigger/deploy | Đối soát cùng identity trước retry, không tạo run/revision dư |
| Old task clear sau redeploy | Revision mismatch bị reject, không chạy code mới cho run cũ |
| ONCE hai trigger khác nhau/gửi lặp | Chỉ một reservation; cùng request/Run ID reuse; run khác bị chặn |
| Revoke trước/sau admission và response loss | Chặn admission mới hoặc chỉ kết thúc giao dịch đã chấp thuận; giữ identity/đối soát |
| Retry/clear sau FULL_REFRESH commit verified | Chỉ đối soát final ledger, không replacement lần hai |
| SCHEDULED dùng manual/backfill hoặc scope đổi | Bị chặn trước target ghi; manual cần ONCE riêng |
| Empty dataset hợp lệ/chưa xác nhận allow_empty | Chặn replacement nếu chưa acknowledgment riêng; lỗi source không là empty |
| Nguồn update giữa chunk | Dataset cùng snapshot, không ghép hai ảnh nguồn |
| NULL/Unicode/decimal/CSV escaping | Round-trip exact hoặc lỗi conversion rõ, không thay dữ liệu im lặng |

Failure injection nằm trong test suite, không hướng dẫn cắt mạng/xóa file của dữ liệu người dùng.
Dùng volume/namespace test biệt lập để mô phỏng disk full và process kill.

## Restart, trạng thái và phục hồi

```powershell
docker compose restart
docker compose ps -a
docker compose logs --tail 100 backend-worker airflow-scheduler airflow-dag-processor
```

Kỳ vọng metadata/files/DAG/log/secret key còn, seed không ghi đè, init/migrations idempotent;
trong120giây từ dependencies ready recovery đối soát hoặc hiển thị lý do bị chặn.
Không regenerate encryption key để chữa ciphertext decrypt fail. Backup app DB phải kèm
keyring/private volume được quản lý an toàn; restore thiếu key cần can thiệp rõ ràng.

Dừng services giữ volumes:

```powershell
docker compose down
```

Không dùng down -v trong luồng vận hành mặc định. Khi có NEEDS_RECONCILIATION, giữ staging/
commit markers, xem operation/run/batch identity và target ledger qua công cụ quản trị được
cấp quyền; không tự chạy lại APPEND hoặc xóa marker để ép success.

## Mẫu báo cáo nghiệm thu

Ghi ngày, build/commit, dependency locks/image digests, resources, testcase A–AM, lệnh,
input/checksum/source snapshot, expected/actual values/rows, state/log/metrics và kết luận.
NOT_RUN/BLOCKED/FAILED khác PASS; không chạy test thì không báo PASS.
Tài liệu này và các artifact Plan chưa chứng minh MVP đã hoạt động. Chỉ bắt đầu triển khai
sau khi tạo tasks có mục tiêu/đầu ra/tiêu chí kiểm chứng từ kế hoạch này.
