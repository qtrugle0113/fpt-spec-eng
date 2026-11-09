# Hướng dẫn khởi động và kiểm chứng

**Trạng thái hiện hành**: Đã có source/Compose/test bootstrap Phase1; P1–P7 đã được duyệt
và kiểm chứng lại. T014 vẫn BLOCKED bởi security findings và các gate tái kiểm; CI tại
implementation commit d57db09 đã PASS Windows/Linux. Chưa vào
Phase2. Các kịch bản nghiệp vụ dưới đây là tiêu chí cho phase tương ứng, chưa là sản phẩm PASS.
Kết quả mới nhất: [remediation vòng3](../../docs/testing/t014-r3-report.md), gồm
dnspython2.9.0, Go Alpine và project test riêng ports23000/28000/28080.
Xem [báo cáo hiện hành](../../docs/testing/phase1-report.md). Candidate shell đang ở
http://localhost:13000 trong môi trường nghiệm thu cũ; địa chỉ này không chứng minh dịch vụ
đang chạy trên máy hiện tại. Xem [kết quả tiếp tục ngày 2026-11-09](../../docs/testing/t014-current-report.md)
cho môi trường Podman6.1.1 và phạm vi đã kiểm thực tế.

A/B đã duyệt và triển khai: Playwright1.65.0/Resolute và hai override Airflow theo policy
riêng, upstream constraints giữ nguyên hash. Fresh/restart đã PASS trên Podman6.1.1 với
provider5.6.0 trong project test `aat-phase1-t014-ab-20261109`, ports13000/18000/18080.
Xem [báo cáo A/B](../../docs/testing/t014-ab-report.md) trước khi tiếp tục fixture này;
không suy bootstrap PASS thành gate security/CI hoặc workflow nghiệp vụ hoàn thành.

## Điều kiện đầu vào

- Podman WSL Linux containers, client5.8.3/server5.8.9 và Docker Compose provider5.6.0
  theo baseline đã công bố; engine/machine đã hoạt động. Host khuyến nghị8CPU,
  12GiBRAM,80GiB disk trống. Có quyền pull/build images và các cổng3000/8000/8080 chưa bị chiếm.
- Clone workspace implementation, đứng ở root. Không cần Python/Node trên host để dùng app.
- Một operator local, app bind127.0.0.1; không dùng cấu hình này làm triển khai Internet.
- .env là optional: default local đủ để boot, không bắt copy .env.example hoặc tự tạo secret.
  Secret key và account service tạo tự động trên volume, không in ra log.

## Runtime và Compose provider

Baseline hiện chọn Podman theo Constitution1.1.0 đã duyệt. `podman compose version` phải
chọn đúng provider đã công bố; có thể pin executable bằng `PODMAN_COMPOSE_PROVIDER` cho
phiên chạy. Ghi client/server/provider, OS/arch/rootful và actual resources trước build.
Docker baseline khác vẫn có thể dùng `docker compose` tương ứng nếu được công bố/nghiệm thu;
không coi PASS trên Podman là Docker-tested. Cài runtime/provider và engine startup là
điều kiện đầu vào, không thay tự động app init. Không reset machine/volumes để chạy lại.

## Một lệnh khởi động

```powershell
podman compose up --build -d
```

Lệnh detached kết thúc trước khi mọi initialization xong. Đợi trạng thái sẵn sàng bằng các
lệnh đọc sau, không phải setup bổ sung:

```powershell
podman compose ps -a
podman compose logs --tail 100 secrets-init db-init app-init airflow-init
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

**EOL và checksum dataset mẫu (rà soát2026-11-08):** Git index của `samples/data/customers.csv`
và `customers.txt` dùng LF, checkout Windows hiện tại dùng CRLF; raw checksum vì vậy khác
manifest lịch sử LF tại [design-validation.json](contracts/design-validation.json). Chưa sửa
hai file trong lượt thiết kế này. Bước implementation phải thêm quy tắc `.gitattributes`
`samples/data/*.csv text eol=lf`, `samples/data/*.txt text eol=lf`, `*.xlsx -text`, rồi
kiểm raw bytes/hash trên checkout sạch Windows/Linux và bytes trong image/volume seed.
Không chữa hash mismatch bằng normalize file người dùng. Upload giữ bytes gốc; checksum
và byte count luôn tính trên nội dung thực được lưu.

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

Runner/profile/config tối thiểu phải có từ Phase1, mở rộng fixtures/contracts ở Phase2,
trước Connections E2E của Phase3. Dùng `@playwright/test==1.56.1` với image
`mcr.microsoft.com/playwright:v1.56.1-noble`, baseURL nội bộ `http://frontend:80`;
kiểm client/browser version và lock/digest khi build. Phase8 mở rộng regression trên runner
đã có. Chỉ chạy selector của chức năng đã triển khai; runner smoke/collect không thay
bằng chứng story E2E PASS. Các lệnh bên dưới vẫn là hướng dẫn tương lai.

```powershell
podman compose --profile test run --rm backend-tests pytest tests/unit tests/api
podman compose --profile test run --rm backend-tests pytest tests/integration tests/etl
podman compose --profile test run --rm backend-tests pytest tests/airflow
podman compose --profile test run --rm e2e-tests npx playwright test
```

Ví dụ gate Phase3 sau implementation: chạy
`podman compose --profile test run --rm e2e-tests npx playwright test connections.spec.ts`
và bộ API/integration Connections tương ứng. Không đợi T138 tạo runner mới để chạy gate này;
task IDs có thể đổi ở lượt Tasks tiếp theo, thứ tự producer trước consumer phải được giữ.

Stress test riêng chạy trên dataset>1GiB và >20batch với worker budget512MiB; không dùng test
unit nhỏ làm bằng chứng bounded memory. Lưu maximum RSS, staging disk bytes/checksum, source
snapshot/target counts và full output. Container test log không được ghi secret.

```powershell
podman compose --profile test run --rm backend-tests pytest tests/stress -m large_data
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
| Authorization revoked/invalidated | Chặn admission mới; vẫn đối soát ledger/recovery, không thêm TTL hoặc state EXPIRED |
| Confirmation token hết hạn | Request mới bị từ chối theo contract; replay cùng key/hash trả intent cũ, không giải phóng ONCE |
| Private bind qua frontend | POST có/không bearer hợp lệ tới `/internal/runtime/bind` và `/api/v1/internal/runtime/bind` đều404; không upstream, redirect hoặc SPA fallback |
| Private bind trực tiếp backend | Canonical root thiếu/sai bearer bị401/403; bearer hợp lệ kiểm identity/version; alias dưới `/api/v1` luôn404 |
| Nguồn update giữa chunk | Dataset cùng snapshot, không ghép hai ảnh nguồn |
| NULL/Unicode/decimal/CSV escaping | Round-trip exact hoặc lỗi conversion rõ, không thay dữ liệu im lặng |

Failure injection nằm trong test suite, không hướng dẫn cắt mạng/xóa file của dữ liệu người dùng.
Dùng volume/namespace test biệt lập để mô phỏng disk full và process kill.

## Restart, trạng thái và phục hồi

```powershell
podman compose restart
podman compose ps -a
podman compose logs --tail 100 backend-worker airflow-scheduler airflow-dag-processor
```

Kỳ vọng metadata/files/DAG/log/secret key còn, seed không ghi đè, init/migrations idempotent;
trong120giây từ dependencies ready recovery đối soát hoặc hiển thị lý do bị chặn.
Không regenerate encryption key để chữa ciphertext decrypt fail. Backup app DB phải kèm
keyring/private volume được quản lý an toàn; restore thiếu key cần can thiệp rõ ràng.

Dừng services giữ volumes:

```powershell
podman compose down
```

Không dùng down -v trong luồng vận hành mặc định. Khi có NEEDS_RECONCILIATION, giữ staging/
commit markers, xem operation/run/batch identity và target ledger qua công cụ quản trị được
cấp quyền; không tự chạy lại APPEND hoặc xóa marker để ép success.

## Mẫu báo cáo nghiệm thu

Ghi ngày, build/commit, dependency locks/image digests, resources, testcase A–AM, lệnh,
input/checksum/source snapshot, expected/actual values/rows, state/log/metrics và kết luận.
NOT_RUN/BLOCKED/FAILED khác PASS; không chạy test thì không báo PASS.
Tài liệu này và các artifact Plan chưa chứng minh MVP đã hoạt động. Chỉ bắt đầu triển khai
sau khi đồng bộ bản152task với cập nhật Plan2026-11-08, Analyze lại và xử lý cổng reviewer.

## Quyền phát triển local có điều kiện

Hiện hành2026-11-09: M0 khép theo chủ dự án; quyền local đến2026-11-23 00:00 UTC+09,
review16/11, scope lượt này chỉ viết tests T015/T016. [Activation](../../docs/decisions/t014-local-activation.json)
và [lệnh/kết quả tests](../../docs/testing/t015-t016-report.md). T014_FULL vẫn BLOCKED,
security FAIL; chưa nghiệm thu foundation hoặc chức năng sản phẩm.

Chỉ dùng khi có quyết định chủ dự án còn hạn và các điều kiện kích hoạt đã khép,
theo docs/proposals/t014-conditional-local-gate.md. Đề xuất DRAFT không phải approval.
Nhãn: bootstrap PASS; security FAIL_WITH_APPROVED_LOCAL_EXCEPTIONS; T014_FULL BLOCKED;
PHASE2_LOCAL_ELIGIBILITY chỉ AUTHORIZED khi owner/reviewer/baseline/controls/hạn đầy đủ.
Migrations nghiệp vụ dùng namespace/volumes mới, giữ stack A/B/R3. Không dữ liệu thật,
public/tunnel. Chưa nghiệm thu toàn bộ MVP; hết hạn/vượt scope thì dừng phần phụ thuộc,
review lại, không tự gia hạn hoặc bỏ scanner.
