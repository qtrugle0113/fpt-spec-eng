# Danh sách task: Airflow Automation Tool

**Trạng thái hiện hành (ưu tiên hơn các snapshot bên dưới):** T138 đã khép
trong phạm vi local được duyệt; tổng hợp 13 selectors tại
`docs/testing/resume-20261111/t138-aggregate.json`. T141 PASS luồng UI đầy đủ
desktop/mobile, xác minh 4 dòng đích mỗi luồng; T142 PASS cả 4 hướng DB qua
Airflow thật với PK ghép/NULL/decimal/temporal. T143 vẫn mở: guard mất file đã
PASS installed image; TXT thất bại do mapped reservation giữ gần10GiB sau lỗi
typed FULL_REFRESH, không phải parser. Đã build sửa cách tính reservation với
quota/PROTECTED giữ nguyên; chờ selectors liên quan trên `portable-346d83ce/`.
T139/T140/T144–T152 chưa hoàn tất. T014_FULL vẫn BLOCKED. Ngoại lệ Kerberos
đã được chủ dự án duyệt đúng 14 advisory/306 contexts, không còn chờ phê duyệt.
Sản phẩm local tại <http://localhost:23000>, Airflow <http://localhost:28080>.

**Sau phê duyệt Kerberos2026-11-11:** chủ dự án duyệt đúng14advisory/306contexts,
policy LOCAL_POLICY_MATCH. Bản installed-image mới READY tại23000/Airflow28080;
không thay demo13000. T138 đang khép regression:214unit/API+4SDK+54integration+
118engine+19runtime+8Airflow routes+stress>1GiB PASS. Connections6/Tables10E2E
PASS; các E2E còn lại đang chạy. Giữ `[ ]` T138 đến khi đủ selectors/cleanup.
Xem [báo cáo hiện hành](../../docs/testing/phase8-regression-report.md).

**Checkpoint portable mới nhất2026-11-11:** build/resolve10artifacts tại máy hiện
tại, scan không cần baseline images cũ; wheel inspection PASS91/45/26modules,
8unit tests preflight/policy PASS. Đã vá libxslt1.1.43-r4, frontend scan0findings.
T138 vẫn mở:14advisory Kerberos/306contexts ngoài policy cần quyết định riêng tại
[đề xuất](../../docs/proposals/portable-local-krb5-20261111.md). Runtime regression
mới chưa chạy; gate thực chặn trước fixture. Không mở T139–T152/T014_FULL.

**Quy trình portable được duyệt2026-11-11:** T138 bổ sung resolve/build image từ
source/locks/config tại mỗi máy và scan đối chiếu policy có provenance; không
yêu cầu baseline images máy trước. IDs vẫn ghi evidence, unknown findings không
tự miễn. Xem [quyết định](../../docs/decisions/portable-local-build-20261111.md).
Các mô tả blocker thiếu exact IDs bên dưới giữ lịch sử trước thay đổi này.

**Tiếp nhận trên máy TrungLQ13, 2026-11-11:** T138 vẫn mở. Evidence mới hơn có
ETL/stress và packaged Monitoring/Phase7 PASS trên máy trước. Máy hiện tại thiếu8
regression image IDs và6 baseline Phase7 IDs; preflight thực ghi BLOCKED. Runner
đã bổ sung `--preflight-only`, chỉ kiểm images cần cho nhóm được chọn và lưu đầy
đủ blocker;3unit tests PASS. Candidate mới chưa được duyệt để chạy runtime.
Chi tiết tại [báo cáo Phase8](../../docs/testing/phase8-regression-report.md).

**Checkpoint tiếp tục 2026-11-11:** Phase7 T121–T137 đã khép trong phạm vi local
được duyệt. Source regression18PASS, API bổ sung9PASS; packaged Monitoring8PASS,
Dashboard/Settings/UX10PASS +2persistence +2outagePASS. T132 all-state lifecycle
35.686s PASS, gồm actual RUNNING và206runs qua nhiều trang. Không dùng source
overlay thay installed-image acceptance. T014_FULL vẫn BLOCKED; bắt đầu T138
Phase8. Xem [checkpoint mới](../../docs/testing/product-resume-20261111.md).

**Checkpoint sản phẩm hiện hành, 2026-11-10:** T096/T097 và T115–T117 đã nghiệm thu
trong phạm vi task: contracts40PASS, wizard/authority/deployment trên image mới
10E2E PASS desktop/mobile và actual Airflow/target verifier PASS. T118–T120 đang
khép wheel/revision/authorization lifecycle. Image delta `add150fe` đã được chủ
dự án duyệt local theo `docs/decisions/phase6-local-image-approval.json`;
T014_FULL vẫn BLOCKED. Xem [checkpoint](../../docs/testing/product-resume-20261110.md).
Các snapshot “hiện hành” bên dưới là lịch sử trước checkpoint này.

**Hiện hành sau tiếp tục, 2026-11-10:** T098–T111 đã khép phạm vi riêng. T104 SDK normal/SIGKILL retry PASS; T105–T109 fixed wrapper, atomic publication, registration và lost-response reconciliation đã kiểm với Airflow thật. T110/T111 grant/list/detail/revoke7PASS trên HTTP/PG thật. Tiếp T112 trigger/RunIntent/ONCE; chưa có UI→deploy→ETL trọn luồng, chưa nghiệm thu MVP. T096/T097 còn mở cho acceptance đầy đủ; T014_FULL BLOCKED. Chi tiết và giới hạn tại phase6 report; các khối phía dưới giữ lịch sử.

**Hiện hành, 2026-11-10:** T070–T095 khép phạm vi engine trực tiếp: tám route thật trên wheel mới, policies/recovery/locks/ledger, stress nguồn>1GiB/270batch với peak RSS106405888bytes. Files UI giữ nghiệm thu T069 trước đó. Bắt đầu Phase6 T096/T097; chưa có UI→Airflow ETL chạy trọn luồng, chưa nghiệm thu MVP. T014_FULL vẫn BLOCKED; không đổi dependency baseline/security exceptions. Xem [engine checkpoint](../../docs/testing/phase5-engine-report.md); các snapshot dưới là lịch sử.

**Hiện hành:** Connections đã khép T045/T046 bằng E2E6/6PASS desktop/mobile trên
artifacts đã scan/review; cleanup0. Bắt đầu T047/T048 Table Management. T014_FULL
vẫn BLOCKED, không dùng kết quả Connections làm nghiệm thu MVP. Các snapshot dưới là lịch sử.

**Hiện hành sau mất mạng 2026-11-09:** T034 đã khép bằng49aggregate/51profile/contract1PASS.
T035–T044 đã kiểm: Connections23PASS, foundation regression47PASS, typed client/buildPASS.
T045/T046 giữ mở chờ E2E và review Backend artifact mới; chưa mở Phase4. Xem
[báo cáo](../../docs/testing/phase3-connections-report.md). Các snapshot dưới là lịch sử.

**Sau xác nhận mapping hai image:** T028–T031/T033 đã đóng sau kiểm parity/seed/key-loss,
owner không superuser, T017 và worker restart thật. T015 9PASS/T018 7PASS trên máy mới.
T034 còn mở: chờ mapping Airflow candidate bổ sung trước live readiness/full aggregate.
Xem [hồ sơ Airflow](../../docs/testing/phase2-resume-airflow-review.md). Các trạng thái
“chờ xác nhận hai image” bên dưới là lịch sử, không cần duyệt lại hai ID đã xác nhận.

**Lượt implement mới 2026-11-09:** phạm vi hội thoại đã mở đến T152, giữ dependency/gates.
T022–T027 và T032 đã kiểm lại trên máy mới theo phạm vi model/schema/middleware của
từng task; cập nhật checkbox tương ứng. Migration/seed/key-loss 5PASS, T017 28PASS,
T033 3PASS; chưa đóng foundation T034 vì Airflow/live aggregate còn thiếu. Hai candidate
đã scan, đang chờ xác nhận delta image trước mốc tiếp theo; xem
[hồ sơ](../../docs/testing/phase2-resume-security-review.md). Các snapshot dưới là lịch sử.

**Tiếp nhận Phase2 ngày 2026-11-09:** source T022–T034 đã có trong HEAD `b389d2e`,
đang hoàn thiện theo [checkpoint](../../docs/testing/phase2-checkpoint.md); các dòng
“chưa triển khai T022” bên dưới là snapshot cũ. Lượt tiếp nhận kiểm 12/12 tests nguồn
PASS; chưa chạy lại integration do thiếu runtime Podman/Docker. Không đóng thêm task.
Xem [báo cáo tiếp nhận](../../docs/testing/phase2-resume-report.md).

**Hiện hành T021:** FileParserRevision và UploadedFile.revision/ETag đã kiểm trên PG thật:
47/47 PASS (16 T021,31 regression T019/T020). T021 hoàn thành phạm vi ORM; binding/recovery
NOT_RUN vì model/service chưa có, không suy thành recovery safety PASS. T0161PASS/6RED,
T01728RED; T029/T034/build/scan/CI mới NOT_RUN. Chưa triển khai T022 trở đi.
T014_FULL BLOCKED/security FAIL, quyền local giữ hạn23/11 00:00 UTC+09/review16/11.
Xem [báo cáo T021](../../docs/testing/t021-report.md). Các khối bên dưới là lịch sử.

**Hiện hành T020/T019:** 5definition ORM có16tests mới +15regression T019 PASS31/31 trênPG thật.
Nhánh code dependency T019 đã PASS bằng TableDefinition thật (ORM/SQL), đủ đóng T019.
T019/T020 hoàn thành ở phạm vi ORM; T021 trở đi chưa triển khai. T0161PASS/6RED, T01728RED.
T029/T034/build/scan/CI mới NOT_RUN; T014_FULL BLOCKED/security FAIL.
Xem [báo cáo T020](../../docs/testing/t020-report.md). Các khối cũ phía dưới là snapshot lịch sử.

**Hiện hành T019:** ba ORM và constraint/immutability/codec/projection/type snapshot có15PG tests PASS.
T019 vẫn `[ ]`/PARTIAL: positive branch chặn code có business dependency thật NOT_RUN,
không tạo schema thay thế hoặc triển khai T020 ngoài scope. T0161PASS/6RED, T01728RED không đổi.
T029/T034/build/scan/CI mới NOT_RUN; T014_FULL BLOCKED/security FAIL.
Xem [báo cáo T019](../../docs/testing/t019-report.md). Các snapshot dưới đây là lịch sử.

**Hiện hành T018:** common schemas/health routing đã triển khai và kiểm source-only:
19/19checks gồm T015,7/7 trên backend dependencies PASS; live ALIVE, ready503 chưa đủ T034.
T016 vẫn1PASS/6RED, T017 giữ RED/NOT_RUN branches. Chưa build/deploy source mới, CI/scan mới NOT_RUN.
T014_FULL BLOCKED/security FAIL; chưa triển khai T019 trở đi.
Xem [báo cáo T018](../../docs/testing/t018-report.md). Snapshot T017/T015/T016 bên dưới là lịch sử.

**Hiện hành — T017 2026-11-09:** hoàn thành viết12state/16repository tests; collect28cases,
28FAIL/RED do thiếu T031, không collection error. Nhánh concurrency/lock/role chưa chạy tới
(NOT_RUN), không nghiệm thu foundation T034. T014_FULL BLOCKED/security FAIL, quyền local
giữ hạn23/11 00:00 UTC+09/review16/11. Chưa triển khai T018 trở đi.
Xem [báo cáo T017](../../docs/testing/t017-report.md). Các snapshot T015/T016/vòng3 dưới đây là lịch sử.

**Hiện hành — M0/T015/T016 2026-11-09:** M0 khép theo xác nhận chủ dự án;
PHASE2_LOCAL_ELIGIBILITY AUTHORIZED đến2026-11-23 00:00 UTC+09, review16/11.
T014_FULL vẫn BLOCKED/security FAIL. T015 harness PASS9/9; T016 đã viết/collect7cases,
1PASS/6FAIL RED đúng foundation chưa triển khai. Chỉ hoàn thành task viết tests,
không nghiệm thu foundation T034. CI source mới/full scan21targets NOT_RUN.
Xem [kết quả hiện hành](../../docs/testing/t015-t016-report.md).
Phần vòng3 dưới đây là lịch sử.

**Trạng thái mới nhất vòng3:** T014 `[ ]`/BLOCKED bởi security784occurrences;
CI Windows/Linux d57db09 và clean checkout PASS. Chỉ tiếp tục T014, chưa mở Phase2.
Xem [báo cáo vòng3](../../docs/testing/t014-r3-report.md); các đoạn tiến độ A/B cũ bên
dưới giữ provenance lịch sử, kết quả vòng3 được ghi cuối file.

**Ngày tạo**: 2026-11-06.
**Đồng bộ có mục tiêu**: 2026-11-08 theo Plan sau Analyze; giữ nguyên 152 task và ID T001–T152.
**Đầu vào**: [Specification và Clarification](spec.md), [Plan](plan.md), [Research](research.md), [Data Model](data-model.md), [Quickstart](quickstart.md), [Constitution](../../.specify/memory/constitution.md), [REST API](contracts/rest-api.md), [OpenAPI](contracts/openapi.yaml), [Airflow](contracts/airflow.md), [Runtime](contracts/runtime.md), [Excel](contracts/excel-definitions.md).
**Trạng thái**: T001–T013 đã kiểm chứng bootstrap; A/B đã được duyệt và triển khai trong T014. Fresh/restart/persistence trên Podman6.1.1/Compose5.6.0 PASS752.059s;13unit/4E2E/5compatibility/7runtime tests PASS. T014 vẫn BLOCKED bởi security findings và CI source mới. CI Windows/Linux tại HEAD b29ae86 đã PASS; working tree lượt mới chưa chạy CI remote. Gate Phase1 chưa đạt; US1/MVP chưa hoàn thành. Chi tiết tại [báo cáo A/B](../../docs/testing/t014-ab-report.md).
**Tổ chức**: Giữ đúng 8 implementation phase của Plan và yêu cầu người dùng; trong phase chia nhóm user story thay vì tạo thêm phase riêng cho từng story. US1–US11 tương ứng US-01–US-11 trong Spec. US1 được hoàn thiện qua infrastructure và kiểm chứng cuối; US3/US7/US8 cùng xây engine nhưng có nhóm task và tiêu chí độc lập.

## Quy ước định dạng và thực thi

- Dòng task: `- [ ] T### [P?] [USn?] Mô tả; Phụ thuộc: ...; Truy vết: ...; Kiểm chứng: ...`.
- Đường dẫn trong task tương đối với workspace root, dùng `\` cho Windows. Đường dẫn trong liên kết tài liệu tương đối với tài liệu này.
- `Phụ thuộc: không` là task không có prerequisite. Mọi prerequisite thực tế phải được ghi bằng ID; dependency là bắc cầu. Gate phase là cổng nghiệm thu, không phải dependency ngầm thay cho danh sách ID.
- `[P]` cho biết có thể chạy cùng task khác đã đủ prerequisite và không sửa chung file. Không có nghĩa được bỏ dependency hoặc chạy ngay từ đầu. Fixture DB/DAG/volume độc lập khi kiểm thử song song.
- Setup/Foundation/Final Integration không có nhãn story; các nhóm nghiệp vụ phase 3–7 bắt buộc có nhãn. Các kiểm thử phải được viết trước phần triển khai liên quan; lần đầu thất bại đúng lý do chưa có chức năng, sau đó chạy lại để nghiệm thu.
- Mỗi task phải có đầu ra bền và kiểm chứng đã nêu. Task viết test trước implementation hoàn thành khi test collect được và thất bại đúng chức năng chưa có; gate story/phase chỉ hoàn thành khi chạy lại các test đó PASS thật. Không đánh dấu hoàn thành dựa trên mock thay integration, container running thay readiness, ghi file thay DAG registration hoặc task success thay đối soát dữ liệu.
- Constitution có thẩm quyền cao nhất. Mâu thuẫn ảnh hưởng an toàn phải sửa đúng tài liệu nguồn bằng Specify/Clarify/Plan trước task liên quan, không tự thay policy để dễ triển khai.
- Tất cả Markdown/giải thích tiếng Việt; UI, lỗi public API, workbook sheet/header/instructions tiếng Anh; tên công nghệ, enum và lệnh giữ nguyên.
- Các task model triển khai toàn bộ trường của entity tại Data Model, không chỉ trường nêu trong mô tả. Ràng buộc được trích nguyên văn trong task, không tự thêm max length/default/nullable chưa được hợp đồng xác định.

## Phase 1 — Hạ tầng

**Mục tiêu/US liên quan**: Nền tảng US1; stack local khởi động được, chưa tuyên bố workflow sản phẩm hoàn chỉnh.
**Điều kiện bắt đầu**: Spec/Plan được chấp thuận; Podman WSL Linux/amd64 và Compose provider đã pin theo Plan (hoặc baseline Docker đã công bố), quyền pull/build và cổng 3000/8000/8080 sẵn sàng.
**Kết quả dự kiến**: Source skeleton có typing/build, image pin/lock, DB/Airflow thật, init idempotent và volumes/secrets; sample EOL ổn định, pytest/Playwright runner và test profile tối thiểu.
**Cách kiểm tra/test**: T013/T014; resolve/build/pip check/npm build; một lệnh startup và restart trên volume test riêng.
**Điều kiện hoàn thành**: T001–T014 có bằng chứng; DB/Airflow readiness thật, không setup ngầm; bootstrap backend chỉ liveness, chưa giả readiness sản phẩm; runner khởi chạy/collect và shell smoke được nhưng chưa nghiệm thu story chưa triển khai.

- [x] T001 Tạo monorepo và manifest package tại `frontend\package.json`, `backend\pyproject.toml`, `packages\aat_metadata\pyproject.toml`, `etl_engine\pyproject.toml`, `tests\conftest.py`; đúng module/import boundary Plan, metadata/engine wheel 0.1.0; viết kiểm tra bytes/hash mẫu tại `tests\unit\test_sample_artifacts.py` trước chính sách EOL rồi tạo `.gitattributes` với `samples/data/*.csv text eol=lf`, `samples/data/*.txt text eol=lf`, `*.xlsx -text`; materialize riêng sample paths hoặc checkout sạch sau bảo toàn thay đổi người dùng; Phụ thuộc: không; Truy vết: FR-084, NFR-010, Constitution IV; Kiểm chứng: cài editable/build skeleton và import không kéo FastAPI/Airflow vào engine; mẫu raw LF/hash khớp manifest lịch sử, XLSX bytes không đổi, không normalize upload người dùng; CI Windows/Linux kiểm lại T014.
- [x] T002 [P] Khóa dependency Python/backend/runtime tại `backend\requirements.lock`, `etl_engine\requirements.lock`, `airflow\docker\constraints-3.12.txt`; preflight Podman client/server/provider đã công bố, Linux/amd64/Python3.12 và registry access; dùng pin Research, hashes và constraints Airflow 3.3.2, không cài lúc startup; Phụ thuộc: T001; Truy vết: NFR-010, Research §2; Kiểm chứng: resolve và pip check hai môi trường, lưu hash constraints.
- [x] T003 [P] Khởi tạo SPA có TypeScript, router, TanStack Query, form và tokens tại `frontend\src\app\App.tsx`, `frontend\src\app\router.tsx`, `frontend\src\app\styles.css`, `frontend\package-lock.json`; sáu route, tên ứng dụng trung tính, UI tiếng Anh; Phụ thuộc: T001; Truy vết: FR-002, NFR-001–NFR-002; Kiểm chứng: npm ci, typecheck/build và shell 1440/390 px.
- [x] T004 Tạo backend/ETL/test Dockerfile tại `backend\Dockerfile`, `docker\tests\Dockerfile`, liveness bootstrap trong `backend\src\aat_api\main.py`; Podman build theo baseline, copy root tests vào test image; tạo runner E2E tại `docker\tests\playwright.Dockerfile`, `tests\e2e\package.json`, `tests\e2e\package-lock.json`, `tests\e2e\playwright.config.ts` với @playwright/test1.65.0 và image mcr.microsoft.com/playwright:v1.65.0-resolute cùng browser, baseURL http://frontend:80; Phụ thuộc: T002; Truy vết: FR-081, FR-085, NFR-010; Kiểm chứng: build/import wheel và liveness, npm ci/version/client-browser compatibility, runner pytest/Playwright khởi chạy không cài Python/Node/browser trên host; không báo schema/worker ready giả, compose wiring/smoke hoàn thiện T011/T013.
- [x] T005 [P] Tạo image web và proxy tại `frontend\Dockerfile`, `docker\nginx\default.conf`; Podman build với fully qualified image refs, giữ Node 22.21.1/nginx 1.28.0; same-origin `/api/v1`; chặn cả prefix `/internal/runtime` và `/api/v1/internal/runtime` cùng path con trước proxy/SPA fallback; Phụ thuộc: T003; Truy vết: FR-081, NFR-003; Kiểm chứng: SPA route fallback/API proxy đúng, GET/POST hai biến thể private có/không bearer hợp lệ đều404, không redirect/SPA fallback và không request upstream; kiểm direct canonical bearer/alias sau khi có runtime route tại T103.
- [x] T006 Tạo custom Airflow image tại `airflow\docker\Dockerfile`, `airflow\docker\entrypoint.sh`; Podman build docker.io/apache/airflow:3.3.2-python3.12, cài wheel và SDK theo constraints, không làm resolver đổi Airflow; Phụ thuộc: T002; Truy vết: FR-081, NFR-008; Kiểm chứng: pip check, airflow version và import SDK/engine.
- [x] T007 [P] Tạo bootstrap key/account tại `docker\bootstrap\secrets.py`, `.env.example` và primitive Fernet encrypt/decrypt tại `packages\aat_metadata\secrets\codec.py` để app-init dùng ngay; default local không cần copy .env, key_id và secretfile persistent theo domain, không regenerate khi dữ liệu mã hóa tồn tại; Phụ thuộc: T004; Truy vết: FR-100, NFR-003; Kiểm chứng: tạo một lần, chạy lại không đổi bytes, ciphertext seed decrypt được, lỗi thiếu key rõ, log không lộ secret.
- [x] T008 [P] Tạo PostgreSQL init/roles/sample tại `docker\postgres\initialize.py`, `docker\postgres\samples.sql`; tách app_metadata/airflow_metadata/etl_test và `_aat_control`, least privilege, natural-key seed; Phụ thuộc: T004; Truy vết: FR-082–FR-084, FR-099; Kiểm chứng: chạy lại không ghi đè, runtime không đọc bảng Airflow, customers_source/target namespace mẫu đúng.
- [x] T009 [P] Tạo MySQL init/roles/sample tại `docker\mysql\initialize.py`, `docker\mysql\samples.sql`; InnoDB/utf8mb4/strict mode, support objects đúng Data Model, credentials từ file; Phụ thuộc: T004; Truy vết: FR-033, FR-083–FR-084, BR-15; Kiểm chứng: grants, engine và seed idempotent giữ dữ liệu đã sửa.
- [x] T010 [P] Tạo Airflow initialization tại `airflow\docker\initialize.sh`, `airflow\docker\airflow.cfg`; official db migrate, SimpleAuth local users/service JWT, LocalExecutor parallelism2, API/scheduler/dag-processor; Phụ thuộc: T006, T007; Truy vết: FR-099, NFR-008; Kiểm chứng: migration lại an toàn, auth thật, không anonymous all-admin.
- [x] T011 Tạo `docker-compose.yml` với secrets-init/db-init/bootstrap app-init/airflow-init, backend-worker skeleton và web; health/completed dependencies, named volumes, RO mounts/UID, loopback ports và mem_limit scheduler2GiB/DB1GiB; thêm profile test gồm backend-tests/e2e-tests từ runner T004, cùng network frontend, test project/volumes và fixture namespace riêng, không chạy mặc định; Phụ thuộc: T004, T005, T007, T008, T009, T010; Truy vết: FR-081–FR-083, FR-085, FR-099–FR-100, NFR-004, NFR-010; Kiểm chứng: podman compose config/build test services với provider đã pin; kiểm thực service_healthy/service_completed_successfully, one-shot failure chặn consumer, actual cgroup limits/UID/GID/RO mounts/loopback; pytest/Playwright collect qua profile không host setup, cleanup chỉ tài nguyên test sở hữu; bootstrap seed không xóa dữ liệu; app-init chưa có app schema phải được ghi rõ và sẽ hoàn thiện T030.
- [x] T012 Tạo health probes tại `docker\bootstrap\health.py`, `airflow\docker\health.sh`; DB query thật, Airflow JSON metadatabase/scheduler/dag_processor và heartbeat CLI, tách live/ready, hostname container/browser; Phụ thuộc: T011; Truy vết: FR-099, NFR-006; Kiểm chứng: dependency down làm probe đúng, HTTP200 không che unhealthy; probes thực trên Podman/provider baseline, không thay bằng sleep hoặc bỏ healthcheck.
- [x] T013 Tạo smoke test `tests\integration\test_bootstrap_startup.py` và `tests\e2e\bootstrap.spec.ts`; dùng project/volumes test riêng, chạy đúng `podman compose up --build -d`, chờ init Exited(0), DB queries, Airflow auth/API/UI; chạy pytest/Playwright shell/proxy smoke qua profile test T011, không yêu cầu endpoint story tương lai; Phụ thuộc: T012, T004, T011; Truy vết: US-01, SC-001, FR-081, FR-085; Kiểm chứng: ghi client/server/provider; fresh/restart trên Podman không setup thủ công, lỗi init có chẩn đoán và không reset volume; runner/browser thực chạy shell1440/390 và proxy guards, smoke không thay bằng chứng Connections hoặc product readiness.
- [ ] T014 Kiểm tra build/dependency/image baseline và ghi vận hành bootstrap tại `tests\integration\test_image_compatibility.py`, `docker\images.lock`, `README.md`; tạo CI checkout Windows/Linux kiểm `.gitattributes`/sample raw LF/hash/XLSX tại `.github\workflows\sample-artifacts.yml`, tái sử dụng test T001; dùng fully qualified refs, resolve digest thật cả Playwright image; ghi client/server/provider compatibility và actual resource enforcement, scan dependency/image bằng công cụ môi trường được chấp thuận, không bịa PASS; Phụ thuộc: T013; Truy vết: FR-084, NFR-010, Constitution X–XI, Research §10; Kiểm chứng: npm build/typecheck, pip check backend/Airflow, client/browser1.65.0, sample hashes checkout→image nhất quán không normalize, CI chưa chạy ghi NOT_RUN/BLOCKED; digest/hash và giới hạn scan ghi rõ.

## Phase 2 — Nền tảng Backend

**Mục tiêu**: Repository/schema/contracts/error/worker dùng chung; hoàn thiện app-init.
**Điều kiện bắt đầu**: T014 đạt đầy đủ HOẶC hồ sơ quyền local được chủ dự án duyệt/còn hạn, LEX-003/D3 đã khép và controls/exception IDs đã kiểm. T014 giữ `[ ]` nếu full security còn FAIL. Contracts/Data Model vẫn canonical. Ngoại lệ dependency T014 chỉ cho T015/T016 trong scope local, không hạ gate chức năng các phase sau; xem `docs/proposals/t014-conditional-local-gate.md`.
**Kết quả dự kiến**: Application metadata riêng, API typed, errors an toàn, worker durable, schema/migration readiness.
**Cách kiểm tra/test**: T015/T016 viết trước triển khai; T034 chạy unit/API/integration thật.
**Điều kiện hoàn thành**: T015–T034 đạt, schema/repository/migrations/seed và Operation recovery đúng, worker phục hồi không replay side effect chưa rõ; chưa nghiệm thu Connections CRUD hoặc Settings API thuộc Phase3/7.

- [x] T015 [P] Viết contract harness tại `tests\api\test_openapi_contract.py`; lấy operation/schema từ `specs\001-airflow-automation-tool\contracts\openapi.yaml` hiện tại, không hardcode40 hoặc47/53; phát hiện missing operation/required fields/extra fields/write-only secret/status/ETag/idempotency drift; Phụ thuộc: T014; Truy vết: FR-085, NFR-010; Kiểm chứng: schema mismatch cố ý bị phát hiện; baseline hiện tại47operations/53schemas chỉ là thông tin, endpoints story được chạy khi story tương ứng hoàn thiện.
- [x] T016 [P] Viết integration nền tảng tại `tests\integration\test_metadata_foundation.py`; isolation app/Airflow DB, FK RESTRICT, migration concurrency, operation lease/restart, safe errors; Phụ thuộc: T014; Truy vết: FR-082, FR-099–FR-100, NFR-003; Kiểm chứng: thiếu foundation làm test fail đúng nguyên nhân, không mock DB.
- [x] T017 [P] Viết test state/repository quyền tại `tests\unit\test_authorization_states.py`, `tests\integration\test_authorization_repository.py`; reservation một ONCE, RunIntent idempotency, lock order authorization→intent→binding/admission, revoked/invalidated/consumed/closed, role cấm cấp/sửa scope runtime; Phụ thuộc: T016; Truy vết: BR-08, FR-053–FR-054, SC-014; Kiểm chứng: collect/red đúng chức năng thiếu; gate foundation chạy PostgreSQL thật, hai transaction tranh quyền chỉ một reservation.
- [x] T018 Tạo Pydantic envelope/base schemas và API routing tại `backend\src\aat_api\schemas\common.py`, `backend\src\aat_api\routes\health.py`; UUID, UTC RFC3339, pagination default50/max200/offset>=0, unknown total nullable; Phụ thuộc: T015; Truy vết: FR-077, NFR-006; Kiểm chứng: validate boundary/errors khớp OpenAPI.
- [x] T019 [P] Tạo Connection/Revision/Secret ORM tại `packages\aat_metadata\models\connections.py`; trích ràng buộc: “unique normalized_code; PG/MYSQL; code bất biến khi có dependency”, “unique connection_id/revision; immutable endpoint/credential; port1–65535; secret FK”, “Fernet token; không plaintext; chỉ backend/runtime role đọc, không public serializer”; Phụ thuộc: T016; Truy vết: FR-003–FR-009; Kiểm chứng: constraint DB, serializer không ciphertext/password.
- [x] T020 [P] Tạo UploadedFile/DefinitionUpload/Issue/TableDefinition/Column ORM tại `packages\aat_metadata\models\definitions.py`; “storage_key do server sinh; filename không thành path; immutable content; parser sửa tạo revision”, “TABLE/ETL; version1.0; validation gắn file/checksum, report không chứa cell secret”, “row/column bắt đầu1; lỗi workbook có location null và scope=workbook”, “unique upload/physical table identity; chỉ tạo mới table”, “unique name/ordinal/table; key không nullable; default tagged JSON; PK ghép thứ tự ordinal”; Phụ thuộc: T016; Truy vết: FR-010–FR-028, FR-098; Kiểm chứng: FK/duplicate/null/default round-trip đúng.
- [x] T021 [P] Tạo FileParserRevision ORM tại `packages\aat_metadata\models\file_parsers.py`, thêm UploadedFile.revision và DefinitionIssue.scope trong `packages\aat_metadata\models\definitions.py`; “unique file/revision, immutable config”, “Content sha256 không đổi”, parser revision còn binding/recovery phải giữ; Phụ thuộc: T020; Truy vết: FR-011–FR-017, FR-020, FR-092; Kiểm chứng: config/hash/encoding/delimiter/header/quote/escape/NULL đầy đủ, FK RESTRICT và ETag revision.
- [x] T022 [P] Tạo ETLDefinition/Revision/Mapping ORM tại `packages\aat_metadata\models\etl.py`; “dag_id unique local; collision external kiểm thêm Airflow; không cascade xóa lịch sử”, “immutable canonical config; JSON chứa IDs/reference, không secret; unique definition/revision/hash”, “một target enabled mỗi revision; source tùy transform; enum whitelist”; Phụ thuộc: T016; Truy vết: FR-030–FR-048; Kiểm chứng: immutable/hash/FK và enabled target uniqueness.
- [x] T023 [P] Tạo Authorization ORM tại `packages\aat_metadata\models\authorizations.py` với toàn fields Data Model: dag/revision/target/scope hashes, acknowledged/allow_empty timestamps, state/reserved_intent_id/consumed/closed/revoked/invalidated/revision; “scope ONCE/SCHEDULED; allow_empty mặc định false, true cần xác nhận riêng; ONCE reservation một lần không giải phóng; đổi phạm vi làm mất hiệu lực; không xóa quyền còn recovery”; Phụ thuộc: T022, T017; Truy vết: BR-08, FR-053–FR-054; Kiểm chứng: GRANTED/RESERVED/CONSUMED/CLOSED/REVOKED/INVALIDATED constraints và scope/ETag snapshot.
- [x] T024 [P] Tạo Operation/TableCreationJob/Result/Deployment/Admission/Audit ORM tại `packages\aat_metadata\models\operations.py`; “unique kind/idempotency_key; cùng key khác payload409; SELECT FOR UPDATE SKIP LOCKED nhận việc”, “chỉ bắt đầu từ upload VALIDATED, recheck quyền/schema/existence”, “unique job/table; kết quả riêng, không hứa transaction toàn workbook”, “unique deployment identity; một active deploy mỗi dag; version UUID/number lấy API thật”, “state OPEN/BLOCKED; chặn run mới vào engine khi redeploy/connection change; không scheduler thay thế”, “ghi xác nhận/xung đột/recovery; không chứa credentials, payload file/dataset hoặc nguyên dòng lỗi”; Phụ thuộc: T016; Truy vết: FR-028, FR-035–FR-041, FR-096–FR-097; Kiểm chứng: state transition/unique/FK và audit redaction.
- [x] T025 [P] Tạo Binding/Manifest/Artifact/Metric/Lease ORM tại `packages\aat_metadata\models\runtime.py`; “unique dag/run; lần đầu chốt immutable; retry phải trùng binding”, “INCOMPLETE/COMPLETE/CORRUPT/PROTECTED/EXPIRED; complete không mutate”, “unique safe path, file ordinal; complete chỉ sau fsync”, “metric engine và projection commit ledger, không copy Airflow history”, “heartbeat chỉ phát hiện nghi ngờ; không thay native target lock”; Phụ thuộc: T016; Truy vết: FR-057–FR-062, FR-089–FR-095; Kiểm chứng: retry binding mismatch và nonnegative counts bị chặn.
- [x] T026 [P] Tạo RunIntent/ReplacementAdmission ORM tại `packages\aat_metadata\models\replacement_runs.py`, gắn ExecutionBinding.run_intent_id/airflow_run_type trong `packages\aat_metadata\models\runtime.py`; “unique operation_id và dag_id/airflow_run_id và run_uuid; manual ID ổn định trước POST Airflow; ONCE không chuyển intent; scheduled intent tạo sau API xác minh run”, “unique binding_id/admission_epoch; tối đa một admission chưa đối soát mỗi binding; immutable identity; không là bằng chứng target commit”; Phụ thuộc: T024, T025, T023; Truy vết: BR-08, FR-053–FR-054, FR-096; Kiểm chứng: circular reservation FK insert/set trong một transaction, binding unique/FK RESTRICT, target session/owner/dataset hashes lưu đủ.
- [x] T027 [P] Tạo Setting ORM tại `packages\aat_metadata\models\settings.py`; “whitelist key; không lưu secret; default mới không mutate deployed config”; tạo validators settings batch1..10000/refresh5..3600/retention1..365/timezone IANA tại `backend\src\aat_api\schemas\settings.py`; Phụ thuộc: T016; Truy vết: FR-079–FR-080, BR-14; Kiểm chứng: reject field lạ, readonly connectivity không PATCH.
- [x] T028 Tạo DB session/repository revisions tại `packages\aat_metadata\repositories\base.py`, `packages\aat_metadata\repositories\revisions.py`; UTC/UUID/JSONB, FK RESTRICT, request session ngắn, ETag optimistic409/412; Phụ thuộc: T018, T019, T020, T022, T024, T025, T027, T021, T023, T026; Truy vết: NFR-007, BR-01–BR-02, BR-10; Kiểm chứng: lost update và delete referenced records fail, runtime mở session riêng.
- [x] T029 Tạo Alembic migrations tại `backend\alembic\env.py`, `backend\alembic\versions\0001_metadata.py`; toàn entity/index Data Model, counts>=0/scale<=precision/nonempty keys, app DB không chứa Airflow history; Phụ thuộc: T028; Truy vết: FR-082, FR-099, NFR-010; Kiểm chứng: upgrade head trên DB mới và hiện hữu, constraint/index phản chiếu ORM.
- [x] T030 Hoàn thiện app-init/seed tại `docker\bootstrap\app_init.py`, `backend\src\aat_api\services\seed.py`, `docker-compose.yml`; migration owner advisory lock, seed pg_etl/mysql_etl và file UUID mẫu/checksum/FileParserRevision1, insert missing không overwrite, tính checksum/bytes trên file LF thực được copy vào volume, so manifest sample T001/T014, không normalize upload; Phụ thuộc: T029, T007; Truy vết: FR-083–FR-084, FR-099–FR-100; Kiểm chứng: hai init cạnh tranh/restart và sample registry đúng Quickstart.
- [x] T031 Tạo repository quyền/intent/admission tại `packages\aat_metadata\repositories\authorizations.py`, `packages\aat_metadata\repositories\replacement_runs.py`, hoàn thiện runtime grants trong `docker\bootstrap\app_init.py`; SELECT FOR UPDATE cùng row quyền cho reserve/revoke/admit, state transitions Data Model, epoch mới sau rollback verified/quyền còn hiệu lực, không transaction phân tán/release vì heartbeat; Phụ thuộc: T017, T029, T028, T030; Truy vết: BR-08, FR-053–FR-054, FR-095–FR-096; Kiểm chứng: chạy T017 PostgreSQL thật; reservation không đổi Run ID, admission/revoke có thứ tự, runtime role không cấp/sửa scope/allow_empty hoặc xóa evidence.
- [x] T032 Tạo error/logging/origin middleware tại `backend\src\aat_api\errors.py`, `backend\src\aat_api\logging.py`, `backend\src\aat_api\middleware.py`; English ErrorResponse/request_id/location/retryable, redact DSN/path/secret, CORS/origin mutation protection; Phụ thuộc: T018; Truy vết: NFR-001, NFR-003, Constitution IV; Kiểm chứng: exception không phân loại có safe message và logging, không broad silent fallback.
- [x] T033 Tạo Operation worker/lease/confirmation tại `backend\src\aat_api\workers\main.py`, `backend\src\aat_api\services\operations.py`, `backend\src\aat_api\services\confirmation.py`, `backend\src\aat_api\routes\operations.py`; signed token10phút hash-bound, SKIP LOCKED, state graph Data Model, không BackgroundTasks/ETL scheduler; Phụ thuộc: T028, T032; Truy vết: BR-02, FR-041, FR-096; Kiểm chứng: cùng key/payload reuse, khác409, stale token409, unknown side effect NEEDS_RECONCILIATION không replay.
- [x] T034 Hoàn thiện foundation readiness và chạy bộ nền tại `backend\src\aat_api\services\health.py`, `tests\integration\test_foundation_ready.py`; app DB/head/worker heartbeat/Airflow readiness, external ETL connectivity riêng; mở rộng fixture metadata và harness profile test T011, chỉ chạy foundation selectors, không yêu cầu Connections CRUD/Settings API; Phụ thuộc: T030, T033, T012, T031; Truy vết: FR-099–FR-100, NFR-006; Kiểm chứng: T015/T016/T017 và health tests PASS thật, dependency lỗi không restart cascade hoặc reset dữ liệu.

## Phase 3 — Connections, US2 (P1)

**Điều kiện bắt đầu**: T034 đạt.
**Kết quả dự kiến**: CRUD/test thật, secret encrypted/revision/dependency an toàn; trang Connections tích hợp API.
**Cách kiểm tra/test**: T035/T036 viết trước, T046 nghiệm thu độc lập trên PG/MySQL.
**Điều kiện hoàn thành**: T035–T046 đạt; timeout<=30giây, không password ở response/log, sửa endpoint không chuyển target run cũ.

- [x] T035 [P] [US2] Viết API contract Connections tại `tests\api\test_connections.py`; create/list/detail/PATCH/DELETE/test, 201/204/409/412, password write-only/blank giữ cũ và pagination/search/filter; Phụ thuộc: T034; Truy vết: FR-003–FR-009; Kiểm chứng: tất cả request/response so OpenAPI, endpoint thiếu fail trước implementation.
- [x] T036 [P] [US2] Viết DB/security tests tại `tests\integration\test_connections.py`, `tests\unit\test_secret_codec.py`; PG/MySQL thật, host/port/auth/db/timeout failures, network allowlist/DNS rebind, encrypted revisions; Phụ thuộc: T034; Truy vết: US-02, NFR-003; Kiểm chứng: errors bounded, không DSN/password trong artifacts.
- [x] T037 [US2] Mở rộng primitive codec T007 với rotation tại `packages\aat_metadata\secrets\codec.py`; Fernet key_id/MultiFernet, tách keyfile/ciphertext, giữ secret revision còn binding active/recovery, tái sử dụng codec seed không tạo đường mã hóa riêng; Phụ thuộc: T036, T019, T007; Truy vết: FR-009, FR-100, Constitution VI; Kiểm chứng: encrypt/decrypt/rotate/restore thiếu key fail readiness, không tự key mới.
- [x] T038 [P] [US2] Tạo PG connection adapter tại `backend\src\aat_api\services\connections\postgres.py`; NullPool connect10giây/tổng30giây, SQLSTATE classification, server fingerprint/schema/quyền; Phụ thuộc: T036, T032; Truy vết: FR-007–FR-008; Kiểm chứng: connect thật và toàn nhóm lỗi PG, release connection.
- [x] T039 [P] [US2] Tạo MySQL adapter tại `backend\src\aat_api\services\connections\mysql.py`; PyMySQL timeout/classification, database/engine/collation/identity, không raw DSN; Phụ thuộc: T036, T032; Truy vết: FR-007–FR-008, BR-15; Kiểm chứng: connect thật và toàn nhóm lỗi MySQL trong30giây.
- [x] T040 [US2] Tạo connection schemas/validation tại `backend\src\aat_api\schemas\connections.py`; code trim case-insensitive unique, required fields FR-004, port1..65535, PG/MySQL enum theo OpenAPI, host allowlist/resolved address trước connect; Phụ thuộc: T035, T018; Truy vết: FR-003–FR-004, NFR-003; Kiểm chứng: boundary/duplicate/URL-path-host/rebind rejects.
- [x] T041 [US2] Tạo CRUD/revision service tại `backend\src\aat_api\services\connections\service.py`; encrypted password, invalidate old test, changed endpoint blocked active run, credential mới cần test; Phụ thuộc: T037, T038, T039, T040, T028; Truy vết: FR-005–FR-009; Kiểm chứng: run giữ revision đã chốt, blank password giữ cũ.
- [x] T042 [US2] Tạo dependency/admission guards tại `backend\src\aat_api\services\connections\dependencies.py`; list Definition/DAG/binding refs, block delete/code change, endpoint/revision đổi làm validation/authorization stale; Phụ thuộc: T041, T022, T024, T025; Truy vết: FR-008, BR-21; Kiểm chứng: dependency fixtures không orphan, không tự resume failed run.
- [x] T043 [US2] Tạo Connections routes/Test Connection tại `backend\src\aat_api\routes\connections.py`; dùng service shared, status/tested_at thật, required dependencies resource refs và needs_revalidation đúng OpenAPI, GET không secret; Phụ thuộc: T042; Truy vết: FR-005–FR-009; Kiểm chứng: T035/T036 chạy qua HTTP và DB thật, UI xem dependency trước sửa/xóa không cần gây lỗi409.
- [x] T044 [US2] Sinh typed OpenAPI client tại `frontend\src\lib\api.generated.ts`, `frontend\src\lib\api.ts`; codegen từ contract, ErrorResponse và polling helpers, không any/secret cache; Phụ thuộc: T043, T003; Truy vết: NFR-010, Constitution IV; Kiểm chứng: typecheck và client nhận status/error chuẩn.
- [x] T045 [US2] Tạo trang/forms Connections tại `frontend\src\features\connections\ConnectionForm.tsx`, `frontend\src\pages\Connections.tsx`; search/filter/details/test timestamp/Add/Edit/Delete/dependency warning, pending/error/readonly password; Phụ thuộc: T044; Truy vết: US-02, FR-005–FR-009, NFR-002; Kiểm chứng: UI English, keyboard, API thật, không optimistic success.
- [x] T046 [US2] Viết/chạy vertical E2E tại `tests\e2e\connections.spec.ts`, hướng dẫn tại `docs\operations\connections.md`; PG/MySQL CRUD/test và error flows từ UI; Phụ thuộc: T045, T013; Truy vết: US-02, SC-011, ma trận Q/Y; Kiểm chứng: chạy `podman compose --profile test run --rm e2e-tests node node_modules/@playwright/test/cli.js test connections.spec.ts` trên runner T004/T011 đã có; T035/T036 và E2E PASS, giới hạn/error recovery tài liệu tiếng Việt.

## Phase 4 — Table Management, US4 (P1)

**Điều kiện bắt đầu**: T046 đạt.
**Kết quả dự kiến**: Template tải được, parser/validation, preview đúng dialect, table thật và per-table history.
**Cách kiểm tra/test**: T047/T048 viết trước; T060 trên hai DB thật.
**Điều kiện hoàn thành**: T047–T060 đạt; invalid workbook không side effect, existing table không ALTER/DROP, partial DDL không success giả.

- [x] T047 [P] [US4] Viết template/upload/preview/create/history/detail contract tests tại `tests\api\test_tables.py`; GET upload history/jobs/table-definition detail, pagination/filter/date, typed length/default/has_default/PK columns, Operation202/signed confirmation/safe issues; Phụ thuộc: T046; Truy vết: FR-018, FR-020, FR-022, FR-028; Kiểm chứng: collect/red trước triển khai; response required fields đúng REST/OpenAPI, browser mới không cần nhớ ID.
- [x] T048 [P] [US4] Viết parser/DDL fixtures tại `tests\unit\test_table_workbook.py`, `tests\integration\test_table_ddl.py`; 20 workbook lỗi, sheet/row/column thật, PK ghép, table tồn tại, partial MySQL/network-after-DDL; Phụ thuộc: T046; Truy vết: SC-004, ma trận A/B/P/AL; Kiểm chứng: invalid không table, runtime per-table đúng trên hai DB.
- [x] T049 [US4] Kiểm tra/tái sử dụng artifact mẫu tại `templates\Table Definition.xlsx`, `samples\definitions\Table Definition.sample.xlsx`, triển khai download tại `backend\src\aat_api\routes\templates.py`; không tạo workbook khác schema1.0; Phụ thuộc: T047; Truy vết: FR-018, FR-084; Kiểm chứng: openpyxl mở download, SHA/ETag, English Instructions/comments/dropdowns, dùng sample ngay với seed.
- [x] T050 [US4] Tạo ZIP-safe workbook parser tại `backend\src\aat_api\validation\workbook.py`; read_only/data_only=False/keep_links=False, reject macro/formula/OLE/external link/path, <=2000entry/100MiB expanded/ratio100/10MiB compressed/100krows; Phụ thuộc: T048, T020, T032; Truy vết: FR-019–FR-021, NFR-003; Kiểm chứng: malformed/bomb/metadata formula rejected trước side effect.
- [x] T051 [US4] Tạo Table validator tại `backend\src\aat_api\validation\tables.py`; version text1.0, exact sheets/headers, max100tables, ordinal1..1000, varchar1..65535 theo byte dialect, decimal precision1..38/scale0..precision, descriptions<=1000, bool/typed literal/ref/duplicates; Phụ thuộc: T050; Truy vết: FR-021–FR-024, FR-098, Excel contract; Kiểm chứng: T048 và locations/null workbook scope, không đoán locale/schema.
- [x] T052 [US4] Lưu upload/table/column/issues tại `backend\src\aat_api\services\definition_uploads.py`; streaming checksum, registry/target selection, toàn workbook validation durable, issues200/trang/total/truncated; Phụ thuộc: T051, T033, T020; Truy vết: FR-020, FR-023, FR-028; Kiểm chứng: state VALIDATED chỉ sau đầy đủ, lỗi có thể sửa/upload lại.
- [x] T053 [P] [US4] Tạo PG DDL adapter tại `backend\src\aat_api\ddl\postgres.py`; SQLAlchemy Core types/quote/default literal, ASCII identifiers max63byte, order/PK ghép, không raw SQL; Phụ thuộc: T051; Truy vết: FR-024–FR-025, NFR-003; Kiểm chứng: compiled preview và table introspection PG khớp.
- [x] T054 [P] [US4] Tạo MySQL DDL adapter tại `backend\src\aat_api\ddl\mysql.py`; identifiers max64ký tự/utf8mb4/strict mode/row limits, Timestamp→DATETIME(6), không cắt type/length; Phụ thuộc: T051; Truy vết: FR-024–FR-025, BR-15; Kiểm chứng: compiled preview/table thật và implicit DDL commit boundary.
- [x] T055 [US4] Tạo typed preview API tại `backend\src\aat_api\routes\definition_uploads.py`, `backend\src\aat_api\services\table_preview.py`; columns ordinal/length/precision/scale/primary_key_ordinal/has_default/TypedLiteral, PK list/target/fingerprints/existence/token đúng DefinitionPreview, preview không execute; Phụ thuộc: T052, T053, T054; Truy vết: FR-022, FR-025–FR-026, BR-02; Kiểm chứng: decimal không float/default null khác không default, đổi target/schema/upload làm token stale409.
- [x] T056 [US4] Tạo DDL worker/job tại `backend\src\aat_api\workers\tables.py`; recheck permissions/existence/revision, result CREATED/ALREADY_EXISTS/FAILED/UNKNOWN, unknown reconcile signature không nhận ownership ngầm; Phụ thuộc: T055, T033, T024; Truy vết: FR-026–FR-028, BR-03; Kiểm chứng: network interruption không create lần hai/DROP bù, table cũ nguyên.
- [x] T057 [US4] Tạo create/history/detail routes tại `backend\src\aat_api\routes\tables.py`; job202/per-table SQL/time/error và PARTIALLY_SUCCEEDED, safe history; Phụ thuộc: T056; Truy vết: FR-028; Kiểm chứng: T047 và job/result persistence qua restart.
- [x] T058 [US4] Tạo lịch sử và table detail query tại `backend\src\aat_api\services\table_history.py`, `backend\src\aat_api\routes\table_history.py`; GET /definition-uploads, /table-creation-jobs, /table-definitions/{id}, created_at+id sort/date/filter/limit-offset; định nghĩa lưu bền khác actual_columns VERIFIED/DRIFTED/UNAVAILABLE/NOT_CREATED; Phụ thuộc: T057, T028, T053, T054; Truy vết: FR-028, FR-026–FR-027; Kiểm chứng: T047 qua DB thật, mở browser mới/restart vẫn list history và DB down không giả introspection.
- [x] T059 [US4] Tạo wizard Table Management tại `frontend\src\features\tables\TableWizard.tsx`, `frontend\src\pages\Tables.tsx`; download/upload/issues/typed length/default/PK preview/confirmation/progress/history/detail từ API phân trang, client codegen không cast any; Phụ thuộc: T057, T044, T049, T058; Truy vết: US-04, FR-028, NFR-002; Kiểm chứng: lỗi English/location, browser mới đọc history, per-table partial không tổng success giả.
- [x] T060 [US4] Viết/chạy E2E và tài liệu tại `tests\e2e\tables.spec.ts`, `docs\operations\table-definitions.md`; download sample→validate→DDL→create thật cả PG/MySQL, existing/invalid giữ nguyên; Phụ thuộc: T059; Truy vết: US-04, SC-004, ma trận A/B/P/AL; Kiểm chứng: T047/T048/E2E PASS và SQL/PK introspection bằng DB thật.

## Phase 5 — ETL Engine, US3/US6/US7/US8 (P1)

**Điều kiện bắt đầu**: T060 đạt; engine chạy trực tiếp trước factory, không phụ thuộc phase6.
**Kết quả dự kiến**: File Sources UI/API, snapshot/typed disk staging, mapping/load/ledger/recovery và metrics thật.
**Cách kiểm tra/test**: T061/T062/T070/T083 viết trước phần liên quan; T094/T095 nghiệm thu từng story.
**Điều kiện hoàn thành**: T061–T095 đạt; tám route engine trực tiếp, data loss/duplicate kiểm soát theo policy, staging disk/RSS/cleanup có bằng chứng.

### US3 — File Sources

- [x] T061 [P] [US3] Viết Files API contract tại `tests\api\test_files.py`; upload/list/detail/preview<=100 với parser_json dự kiến không persist, PATCH /files/{id}/parser If-Match, validate202, active/recovery409/stale412, source checksum immutable/parser revision; Phụ thuộc: T060; Truy vết: FR-010–FR-017, FR-092; Kiểm chứng: collect/red trước implementation, payload/required fields đúng OpenAPI, đổi parser invalidates validation/dependency không mutate binding.
- [x] T062 [P] [US3] Viết parser/retention tests tại `tests\unit\test_delimited_reader.py`, `tests\integration\test_file_sources.py`; CSV/TXT multiline/quoted NULL/BOM/encoding/header/delimiter/empty/oversize/upload interrupt; Phụ thuộc: T060; Truy vết: FR-012–FR-017, FR-092, BR-17; Kiểm chứng: preview/execution cùng token semantics, error line/record thật.
- [x] T063 [US3] Tạo bounded delimited lexer/reader tại `etl_engine\src\aat_etl\readers\delimited.py`; UTF-8 default, preserve was_quoted cho `\N`, max record1MiB kiểm khi đọc, no-header column_1..., fail strict encoding; Phụ thuộc: T062; Truy vết: FR-015, FR-017, FR-092, BR-17; Kiểm chứng: quoted marker là chuỗi, NULL khác empty/0/false, multiline bytes bounded.
- [x] T064 [US3] Tạo file storage/upload service tại `backend\src\aat_api\services\files.py`; server safe key/checksum, upload<=256MiB, atomically publish, incomplete cleanup, persistent/parser revision, không expose path; Phụ thuộc: T061, T063, T020, T032; Truy vết: FR-011–FR-013; Kiểm chứng: restart/ref filename trùng/path traversal/interrupt không publish sai.
- [x] T065 [US3] Tạo file validation worker tại `backend\src\aat_api\workers\files.py`; full format với byte cap, checksum/parser binding, expiry/dependency guard không xóa file còn dùng; Phụ thuộc: T064, T033; Truy vết: FR-014–FR-016; Kiểm chứng: preview không thay full validation, missing source fail không empty.
- [x] T066 [US3] Tạo Files routes tại `backend\src\aat_api\routes\files.py`; upload/list/details/parser/preview/validate theo contract, upload status chưa validated; Phụ thuộc: T065; Truy vết: FR-010–FR-017; Kiểm chứng: T061/T062 qua API thật.
- [x] T067 [US3] Tạo parser revision service/PATCH tại `backend\src\aat_api\services\file_parsers.py`, `backend\src\aat_api\routes\file_parsers.py`; preview candidate cùng bounded reader không lưu, If-Match, block active/recovery, immutable FileParserRevision/checksum, validation/dependency/confirmation stale; Phụ thuộc: T066, T021, T042, T063; Truy vết: FR-015–FR-017, FR-091–FR-092; Kiểm chứng: T061 PASS, ref/content không đổi, revision mới không tự chuyển cấu hình run cũ.
- [x] T068 [US3] Tạo File Sources panel tại `frontend\src\features\files\FileSourcesPanel.tsx`; list/upload/preview candidate→confirm PATCH parser→full validate/select stable ref trong DAG Builder, codegen client; Phụ thuộc: T066, T044, T067; Truy vết: US-03, FR-002, FR-010–FR-017; Kiểm chứng: English parser confirmations/expiry/errors, stale conflict và không RAM toàn file.
- [x] T069 [US3] Viết/chạy file UI E2E và hướng dẫn tại `tests\e2e\files.spec.ts`, `docs\operations\file-sources.md`; reference/parser/checksum/restart/retention, nhiều file cùng tên; Phụ thuộc: T068; Truy vết: US-03, ma trận X/AF; Kiểm chứng: T061/T062/E2E PASS, dependency file không bị GC.

### US6 — DB-to-DB, mapping và staging

- [x] T070 [P] [US6] Viết snapshot/staging/type tests tại `tests\etl\test_snapshot_staging.py`, `tests\unit\test_mapping.py`; concurrent source update, session lost, manifest incomplete/corrupt, Unicode/NULL/decimal/temporal/drift; Phụ thuộc: T060; Truy vết: NFR-005, FR-042–FR-048, FR-055, FR-089–FR-092, SC-013–SC-015; Kiểm chứng: chạy PG/MySQL thật và expected typed round-trip.
- [x] T071 [US6] Tạo typed execution/source/target/mapping contracts tại `etl_engine\src\aat_etl\contracts\config.py`; ETLConfig/ETLSource/ETLTarget/ETLMapping/SourcePredicate/TypedLiteral theo OpenAPI và Excel→enum mapping, schedule/source union/strategy ranges/whitelist/canonical hash; Phụ thuộc: T070, T022; Truy vết: FR-031–FR-033, FR-042–FR-048; Kiểm chứng: source DB+file/UPSERT thiếu key/Constant thiếu literal/file filter bị từ chối, decimal/date/time lossless, không arbitrary Python/SQL.
- [x] T072 [P] [US6] Tạo PG snapshot reader tại `etl_engine\src\aat_etl\readers\postgres.py`; read-only REPEATABLE READ/server cursor, projected row size guard trước materialize, byte-bounded fetch, parameterized filter; Phụ thuộc: T071, T038; Truy vết: FR-055, FR-088, FR-090, BR-16; Kiểm chứng: source update không ghép snapshot và no-key table vẫn đọc đúng.
- [x] T073 [P] [US6] Tạo MySQL snapshot reader tại `etl_engine\src\aat_etl\readers\mysql.py`; InnoDB REPEATABLE READ/SSCursor, một source session, size guard/collation/UTC temporal, reject unsupported engine; Phụ thuộc: T071, T039; Truy vết: FR-033, FR-055, FR-090, BR-15–BR-17; Kiểm chứng: snapshot thật, reconnect bỏ incomplete không ghép dữ liệu.
- [x] T074 [US6] Tạo schema introspection/preflight tại `etl_engine\src\aat_etl\readers\schema.py`; used columns/type/nullable/key fingerprint, source=target physical alias reject, schema drift revalidation trước run/load; Phụ thuộc: T072, T073; Truy vết: FR-033, FR-091, BR-09; Kiểm chứng: key/type/endpoint thay đổi fail, không ALTER hoặc auto-map lại.
- [x] T075 [US6] Tạo staging writer/reader tại `etl_engine\src\aat_etl\staging\manager.py`; aat-jsonl/1 typed arrays, hashed DAG/run/dataset path/temp attempt, fsync/rename/checksum/manifest COMPLETE sau toàn files, immutable reuse; Phụ thuộc: T070, T071, T025; Truy vết: FR-055, FR-057, FR-089–FR-090; Kiểm chứng: disk volume thật, truncated file bị chặn và extract fail target không ghi.
- [x] T076 [US6] Tạo quota/RSS supervision tại `etl_engine\src\aat_etl\staging\quota.py`, `etl_engine\src\aat_etl\resources.py`; chunk1000/max10000/buffer8MiB/row1MiB/RSS512MiB/run10GiB/global20GiB/reserve1GiB, reservation atomic cả protected/temp; Phụ thuộc: T075; Truy vết: FR-088, FR-094, NFR-004; Kiểm chứng: ENOSPC/race/large row fail an toàn trước OOM, không fallback RAM.
- [x] T077 [US6] Tạo mapping/type conversion/filter tại `etl_engine\src\aat_etl\mapping\mapper.py`, `etl_engine\src\aat_etl\mapping\types.py`; exact-name implicit hoặc enabled explicit, Constant/NULL/direct/conversion, AND whitelist, no truncate/round/timezone inference; Phụ thuộc: T071, T074; Truy vết: NFR-005, FR-042–FR-048, BR-05, BR-17; Kiểm chứng: T070, mapped non-key giữ cột unmapped và unsupported value fail vị trí.
- [x] T078 [US6] Tạo full-dataset validation tại `etl_engine\src\aat_etl\mapping\validation.py`; DB staging validate trước load, target-typed disk scratch cho UPSERT chosen key/collation, quota10GiB/5triệu rows, NULL/duplicates fail trước target; Phụ thuộc: T075, T076, T077, T074; Truy vết: FR-052, BR-18, Runtime §Mapping; Kiểm chứng: duplicate xa nhiều chunk/case-insensitive thật, không Python set toàn tập.
- [x] T079 [US6] Tạo target native lock/session tại `etl_engine\src\aat_etl\loaders\session.py`; PG namespace/OID/MySQL GET_LOCK canonical DB/table, same writer session, timeout300giây, reconnect phải reconcile/reacquire; Phụ thuộc: T074; Truy vết: BR-09, SC-014; Kiểm chứng: aliases cùng lock, lock owner unknown không chiếm theo heartbeat.
- [x] T080 [US6] Tạo support DDL/signature/ledger tại `etl_engine\src\aat_etl\loaders\ledger.py`; PG _aat_control.batch_commits/run_commits/support_schema_version, MySQL _aat_batch_commits/_aat_run_commits/_aat_support_schema_version dùng cùng mapping/signature1 với init; PK batch(target_identity,run_uuid,dataset_sha,batch_index), run(target_identity,run_uuid), hashes hex64, support sau consent; Phụ thuộc: T079, T078; Truy vết: FR-051–FR-054, Data Model §Support objects; Kiểm chứng: collision/quyền/tên alias cũ chặn; DB fixture DML+marker cùng transaction, app metrics không commit proof.
- [x] T081 [US6] Tạo preparation pipeline và writer protocol tại `etl_engine\src\aat_etl\engine.py`, `etl_engine\src\aat_etl\contracts\writer.py`; snapshot→COMPLETE disk→map/validate, đóng source session, output dataset/schema/hash cho writer chưa triển khai; Phụ thuộc: T075, T076, T077, T078; Truy vết: FR-055–FR-060, BR-16–BR-18; Kiểm chứng: source/staging/mapping thật và không target DML, chưa nghiệm thu load/recovery; kiểm chứng target transfer chuyển T092/T094 sau policy dispatch.
- [x] T082 [US6] Tạo metrics/ledger projection độc lập writer tại `etl_engine\src\aat_etl\metrics.py`, `packages\aat_metadata\repositories\metrics.py`; extracted/validated/loaded/failed nullable/phase/protected_bytes/recovery_summary/duration, không affected_rows/retry double count; Phụ thuộc: T025, T080; Truy vết: FR-062, FR-093, BR-13, BR-18; Kiểm chứng: fixture ledger thật đã commit→projection, app DB projection fail không gọi writer; flow toàn engine kiểm sau T092.

### US8 — Load strategy và phục hồi

- [x] T083 [P] [US8] Viết policy/failure tests tại `tests\etl\test_load_policies.py`, `tests\etl\test_commit_recovery.py`; APPEND duplicate/unique, UPSERT nhiều keys/collation, FULL_REFRESH old/new visibility/empty/extract fail, commit lost/kill; Phụ thuộc: T060; Truy vết: NFR-005, FR-049–FR-054, ma trận J–M/AC/AG/AH/AI; Kiểm chứng: expected target values/ledger cho hai DB thật.
- [x] T084 [P] [US8] Viết FULL_REFRESH admission tests tại `tests\etl\test_replacement_admission.py`; bind fixture app DB, native target lock, admission response loss/revoke trước-sau điểm chấp thuận, revoked retry không ghi mới, final-marker verified clear không replacement lần hai; Phụ thuộc: T083, T031, T080; Truy vết: BR-08, FR-053–FR-054, SC-014; Kiểm chứng: collect/red trước adapter; chạy hai DB thật khi T085/T089 có, không dùng Airflow status làm commit proof.
- [x] T085 [US8] Tạo admission adapter tại `etl_engine\src\aat_etl\loaders\replacement_admission.py`; dùng repository T031, target lock/ledger trước app authorization row lock, immutable epoch/hash/session/owner, admission commit verified rồi mới target transaction; Phụ thuộc: T084, T031, T079, T080; Truy vết: BR-08, FR-053–FR-054; Kiểm chứng: app DB unavailable trước admit không ghi/fallback cache, lost admission response đọc identity, retry epoch mới chỉ sau rollback/old writer kết thúc/quyền còn hiệu lực.
- [x] T086 [US8] Tạo APPEND writer tại `etl_engine\src\aat_etl\loaders\append.py`; deterministic batch hash/order, insert+marker commit từng batch, unique rollback batch, retry skip marker exact, rerun mới cảnh báo duplicate; Phụ thuộc: T083, T080; Truy vết: FR-050–FR-051, BR-06–BR-07; Kiểm chứng: partial giữ batch trước, không INSERT IGNORE/UPSERT/xóa bù.
- [x] T087 [P] [US8] Tạo UPSERT PG tại `etl_engine\src\aat_etl\loaders\upsert_postgres.py`; ON CONFLICT chosen real key, update mapped non-key, key-only DO NOTHING đúng chosen conflict, DML+marker atomic; Phụ thuộc: T083, T080; Truy vết: FR-052, BR-17; Kiểm chứng: khóa ghép/rerun3lần/value đúng, unique phụ không update nhầm.
- [x] T088 [P] [US8] Tạo UPSERT MySQL tại `etl_engine\src\aat_etl\loaders\upsert_mysql.py`; UPDATE JOIN chosen key rồi INSERT thiếu trong cùng transaction, không REPLACE/ON DUPLICATE KEY UPDATE, rollback unique phụ; Phụ thuộc: T083, T080; Truy vết: FR-052, BR-15, Research §7; Kiểm chứng: nhiều independent keys/collation/NULL/duplicates và số key ổn định.
- [x] T089 [US8] Tạo FULL_REFRESH tại `etl_engine\src\aat_etl\loaders\full_refresh.py`; full mapped staging/allow_empty acknowledgment trước target, native lock→final ledger→T085 admission→DELETE/chunks/verify/final marker một commit, reject inbound FK/unsafe trigger/engine; Phụ thuộc: T083, T080, T077, T085; Truy vết: NFR-005, FR-053–FR-054, BR-08, BR-15; Kiểm chứng: T084 PASS, verified commit chỉ đối soát retry/clear, revoke trước admission chặn/sau admission không hứa rollback, không TRUNCATE/DROP/ALTER/rename/tắt FK.
- [x] T090 [US8] Tạo retry/recovery coordinator tại `etl_engine\src\aat_etl\recovery\coordinator.py`; retries0..10/delay0..3600giây, fail non-safe sớm, immutable binding/dataset, old session+ledger reconcile, NEEDS_RECONCILIATION giữ artifact; Phụ thuộc: T086, T087, T088, T089, T082; Truy vết: NFR-005, FR-051, FR-060, FR-095, BR-07, BR-19; Kiểm chứng: commit lost không blind replay, nguồn mới chỉ extraction trước target ghi.
- [x] T091 [US8] Tạo startup reconciliation/GC tại `backend\src\aat_api\workers\recovery.py`, `etl_engine\src\aat_etl\staging\cleanup.py`; trong120giây từ dependencies ready đối soát hoặc lý do blocked, staging7ngày sau hết recovery/source unreferenced30ngày/ledger>=30ngày, protected không xóa; Phụ thuộc: T090, T033, T065; Truy vết: FR-061, FR-094–FR-095, FR-100, BR-14, BR-19; Kiểm chứng: kill không finally/orphan/GC error có logs/report và không reclaim active owner.
- [x] T092 [US8] Gắn writers/policy dispatch/cancel/resource close vào preparation `etl_engine\src\aat_etl\engine.py`; đối soát intent/binding/final ledger trước preparation khi retry run đã commit, ledger/admission/recovery state và metrics, không đổi dataset sau partial, cancel đúng strategy/ONCE terminal CLOSED hoặc CONSUMED; Phụ thuộc: T090, T091, T081, T082, T085; Truy vết: FR-049–FR-062, BR-08; Kiểm chứng: T083/T084 PASS, standalone load/metrics/failure DB thật, verified commit/revoked chỉ đối soát không replacement mới, no replay khi projection fail.

### US7 — File-to-DB và nghiệm thu engine

- [x] T093 [US7] Gắn file pipeline tại `etl_engine\src\aat_etl\readers\file_source.py`; full format/schema checksum trước run, typed per-row APPEND/UPSERT partial, UPSERT full-key validation, FULL_REFRESH full mapped disk trước publication; Phụ thuộc: T063, T065, T078, T092; Truy vết: FR-056, BR-18, US-07; Kiểm chứng: CSV/TXT→PG/MySQL, source thiếu fail không empty.
- [x] T094 [US7] Viết/chạy tám route engine tại `tests\etl\test_transfer_routes.py`, tài liệu tại `docs\operations\etl-engine.md`; C–H/U, mapping khác tên/NULL/decimal/quoted tokens/khóa ghép/3policies và đối soát target; Phụ thuộc: T093, T082; Truy vết: FR-001, SC-003, SC-005, SC-015; Kiểm chứng: mọi route engine trực tiếp thật, chưa nhận Airflow E2E hoàn thành.
- [x] T095 [US6] Viết/chạy stress/staging evidence tại `tests\stress\test_disk_staging.py`, `tests\etl\test_storage_failures.py`; dataset>1GiB và>20batch/RSS<=512MiB, files/checksums thật và được loader dùng, quota/full/corrupt/lost volume/concurrent aliases; Phụ thuộc: T094, T076, T091, T069; Truy vết: SC-007, SC-013–SC-015, ma trận O/V/AA/AD/AE/AH/AI; Kiểm chứng: RSS/actual disk/row reconciliation/cleanup artifacts, không proxy bằng test nhỏ.

## Phase 6 — DAG Builder và Airflow, US5 (P1)

**Điều kiện bắt đầu**: T095 đạt; engine wheel chạy thật và contract Airflow 3.3.2 có schema pin.
**Kết quả dự kiến**: Workbook→config→atomic deployment→registration đúng revision→task ETL thật, wizard tích hợp.
**Cách kiểm tra/test**: T096/T097 viết trước; T118/T120 chạy Airflow thật.
**Điều kiện hoàn thành**: T096–T120 đạt; không false Deployed, old-clear mismatch bị chặn, scheduled/manual binding giữ đúng scope.
**Lưu ý thứ tự**: Airflow API client xây ở phase này vì deployment phụ thuộc; phase7 tái sử dụng và mở rộng monitoring, không trì hoãn client đến sau consumer.

- [x] T096 [P] [US5] Viết ETL preview/deploy/authorization/early trigger contracts tại `tests\api\test_dag_builder.py`, `tests\api\test_authorizations.py`; create/list/detail/revoke/If-Match/Idempotency-Key, confirmation hash/scope, allow_empty=false mặc định/true cần acknowledgment riêng, reserved_run/state/nullable in-progress và typed ETL preview; Phụ thuộc: T095; Truy vết: FR-029–FR-041, FR-053–FR-054, BR-08; Kiểm chứng: collect/red trước implementation, later PASS47operations contract hiện tại không hardcoded, safe errors và per-DAG202.
- [x] T097 [P] [US5] Viết Airflow contract/registration tests tại `tests\airflow\test_api_contract.py`, `tests\airflow\test_registration.py`; schema3.3.2, owner/hash/fileloc/parse/latest version, parse error/timeout/old revision/external conflict; Phụ thuộc: T095; Truy vết: FR-035–FR-039, SC-009, ma trận W/AJ; Kiểm chứng: APIs thật, scalar DAGRun dag_version_id không được giả định.
- [x] T098 [US5] Kiểm/tải ETL artifact tại `templates\ETL Definition.xlsx`, `samples\definitions\ETL Definition.sample.xlsx`, bổ sung `backend\src\aat_api\routes\templates.py`; version1.0/sheet/English/defaults theo contract; Phụ thuộc: T096, T049; Truy vết: FR-018, FR-084; Kiểm chứng: download hash/ETag và sample refs seed dùng được ngay.
- [x] T099 [US5] Tạo ETL workbook parser/validator tại `backend\src\aat_api\validation\etl_definitions.py`; max100DAG, DAG regex1..200, mappings refs, version/header/duplicates, schedule5fields/IANA/Start Date/Catchup/Paused, retry/batch ranges và structured filter; Phụ thuộc: T096, T050, T071, T077; Truy vết: FR-030–FR-034, FR-042–FR-048, FR-098; Kiểm chứng: AL/AF và workbook invalid không side effect.
- [x] T100 [US5] Tạo canonical DAG config/preview tại `backend\src\aat_api\services\etl_preview.py`; nguồn writable/readable/schema/key/introspection/fingerprint, missing target hướng Table Management, scope/allow_empty/support DDL/diff warnings; Phụ thuộc: T099, T074, T080, T042; Truy vết: FR-029, FR-033, FR-049, BR-02; Kiểm chứng: source=target alias/unsafe FULL_REFRESH blocked, confirmation hash đúng.
- [x] T101 [US5] Tạo Airflow client auth/base tại `backend\src\aat_api\airflow_client\client.py`; JWT SimpleAuth memory/401 refresh1lần, connect3/read10giây, GET retry<=3/Retry-After, percent-encoded IDs, schema/hash3.3.2; Phụ thuộc: T097, T010, T032; Truy vết: NFR-008, FR-096; Kiểm chứng: token không frontend/log,403 khác unavailable, không retry POST mù.
- [x] T102 [US5] Tạo client deployment/control primitives tại `backend\src\aat_api\airflow_client\deployment.py`; DAG/details/dagVersions number/TI/importErrors/health/pause verify và runs pagination; Phụ thuộc: T101; Truy vết: FR-036–FR-039, FR-097; Kiểm chứng: latest_dag_version UUID/number, file matching và HTTP200 unhealthy đúng schema.
- [x] T103 [US5] Tạo runtime binding endpoint/repository tại `backend\src\aat_api\routes\runtime.py`, `packages\aat_metadata\repositories\bindings.py`; canonical `http://backend:8000/internal/runtime/bind`, router ngoài `/api/v1`, operation server override hiện hữu; bearer/TI.dag_version.id/wrapper/gate/API run_type, scheduled đúng SCHEDULED/manual đúng ONCE intent, không quyền thì first bind reject; existing binding sau consumed/revoked vẫn cho đối soát nhưng không admission ghi mới; Phụ thuộc: T102, T025, T100, T031; Truy vết: FR-008, FR-040, FR-057, FR-097, BR-08; Kiểm chứng: run_intent_id/run_uuid required, config/source/target first bind/dataset COMPLETE trước ghi, old-clear revision mismatch/token sai blocked, không credentials; direct canonical thiếu/sai bearer401/403, alias `/api/v1/internal/runtime/bind`404, frontend hai prefix đều404 kể cả bearer hợp lệ và không upstream/SPA fallback.
- [x] T104 [US5] Tạo runtime secret lookup/task adapter tại `etl_engine\src\aat_etl\runtime.py`; bind trực tiếp canonical `http://backend:8000/internal/runtime/bind` không qua frontend hoặc prefix `/api/v1`; direct encrypted app metadata role/keyfile, bind rồi engine session riêng/repository admission T085, không API password hoặc restart Airflow khi connection mới; Phụ thuộc: T103, T037, T092, T093, T085; Truy vết: NFR-003, NFR-008, BR-08; Kiểm chứng: trước bind dependency down fail-safe; đã binding không giữ HTTP request nhưng app DB down trước admission không fallback quyền cache.
  - Checkpoint2026-11-10: adapter/recovery18tests PASS; supervised child PG/MySQL1test PASS; safety4tests PASS; lifecycle7tests PASS. Scheduler/SDK thật2/2PASS tại t104-resume-prestart: normal1attempt, SIGKILL extraction2attempts cùng binding, target2rows và cleanup0; xem phase6 report.
- [x] T105 [US5] Tạo fixed factory/wrapper tại `backend\src\aat_api\deployments\factory.py`, `airflow\dags\aat_wrapper_template.py`; SDK một execute_etl task, JSON canonical config/IDs/hash/owner, max_active_runs1/Catchup theo config đã validate (mặc địnhfalse)/DAG mới paused, không code/secret từ cell; Phụ thuộc: T100, T104; Truy vết: FR-029–FR-037, Constitution V/VIII; Kiểm chứng: import generated Python thật trong image và source không credentials.
- [x] T106 [US5] Tạo atomic file writer tại `backend\src\aat_api\deployments\storage.py`; internal UUID filename/allowlisted root/temp fsync/os.replace/same volume/parent fsync/hash; Phụ thuộc: T105; Truy vết: FR-038–FR-041, NFR-007; Kiểm chứng: interrupt trước/sau rename không file nửa chừng hoặc outside root.
- [x] T107 [US5] Tạo admission/redeploy controller tại `backend\src\aat_api\deployments\admission.py`; compare revision, block concurrent edit, pause confirm, drain queued/running, race startup gate, reject external ownership và run active; Phụ thuộc: T102, T103, T106, T024; Truy vết: FR-036, FR-097, BR-10, BR-20; Kiểm chứng: không tự cancel để deploy, failed giữ paused/last verified.
- [x] T108 [US5] Tạo registration verifier tại `backend\src\aat_api\deployments\registration.py`; poll1/2/4/cap5+jitter<=120giây, owner/hash/fileloc/parse timestamp/version đúng, importErrors đúng file; Phụ thuộc: T107; Truy vết: FR-035, FR-038–FR-039, SC-009; Kiểm chứng: file success/DAG cũ/cache không Deployed, same hash verified no-op hợp lệ.
- [x] T109 [US5] Tạo deploy/reconcile worker tại `backend\src\aat_api\workers\deployments.py`; durable identity/support consent/per-DAG state, timeout NEEDS_RECONCILIATION và giữ blocked, reconcile cùng revision trước retry; Phụ thuộc: T108, T033; Truy vết: FR-035–FR-041, FR-096–FR-097; Kiểm chứng: API timeout after write không revision dư, partial workbook status thật.
- [x] T110 [US5] Tạo authorization create service tại `backend\src\aat_api\services\replacement_authorizations.py`; confirmation/idempotency/hash-bound DAG/revision/physical target/strategy/schedule/timezone/start_date/catchup, ONCE/SCHEDULED, allow_empty=false/true cần separate acknowledgment; Phụ thuộc: T100, T103, T089, T031, T096; Truy vết: FR-053–FR-054, BR-08; Kiểm chứng: token/source scope stale/extra fields reject, same request trả quyền cũ, thay scope invalidate quyền cũ, không consent từ cell Excel.
- [x] T111 [US5] Tạo authorization list/detail/revoke routes tại `backend\src\aat_api\routes\replacement_authorizations.py`; POST/GET /etl-definitions/{id}/replacement-authorizations, GET quyền/{id}, POST revoke/If-Match/Idempotency-Key/acknowledged, required state/hash/revision/nullable replacement_in_progress; Phụ thuộc: T110, T031; Truy vết: BR-08, FR-053–FR-054; Kiểm chứng: T096 authorization contracts PASS, stale412/different payload409, revoke serialize cùng row admission không cancel/DELETE recovery evidence.
- [x] T112 [US5] Tạo trigger primitive/worker/route dùng chung tại `backend\src\aat_api\services\dag_control.py`, `backend\src\aat_api\workers\dag_control.py`, `backend\src\aat_api\routes\dag_control.py`; commit ONCE reservation+RunIntent+Operation trước POST Airflow/stable manual__aat_operation_uuid, same key/hash trả intent cũ kể cả token hết hạn; Phụ thuộc: T031, T103, T101, T110, T033, T111, T109; Truy vết: BR-08, FR-067, FR-096; Kiểm chứng: hai requests một ONCE/same request reuse/response loss giữ reservation+GET ID cũ, manual thiếu ONCE chặn; phase6 gọi route thật, phase7 reuse.
- [x] T113 [US5] Tạo activation/state primitive trước nghiệm thu cron tại `backend\src\aat_api\services\dag_activation.py`, `backend\src\aat_api\workers\dag_activation.py`, gắn PATCH /dags/{dag_id}/state trong `backend\src\aat_api\routes\dag_control.py`; confirmation/revision/Operation/If-Match, activate FULL_REFRESH cần SCHEDULED scope đúng, pause/readback không cancel/thu hồi quyền; Phụ thuộc: T112, T111, T102, T107; Truy vết: FR-034, FR-037, FR-068, BR-08, BR-20; Kiểm chứng: API activation thật trước cron T118, lost response reconcile same identity, ONCE không authorize lịch; phase7 reuse/hoàn thiện controls.
- [x] T114 [US5] Tạo DAG Builder/deployment routes tại `backend\src\aat_api\routes\dag_builder.py`; ETL validate/preview/deploy/status/reconcile và links sang authorization routes T111, Definition/revision/history gắn managed; Phụ thuộc: T109, T110, T052, T112, T111, T113; Truy vết: FR-029–FR-041, FR-040; Kiểm chứng: T096/T097 qua API và source workbook persistence.
- [x] T115 [US5] Tạo Definition/mapping/schedule wizard tại `frontend\src\features\dags\DagDefinitionWizard.tsx`; File Sources reuse, inferred source, key/mapping/filter warnings và English issues; Phụ thuộc: T114, T068, T044; Truy vết: US-05, FR-029–FR-034, FR-042–FR-048; Kiểm chứng: codegen/typecheck, preview với API thật, không arbitrary transformation.
- [x] T116 [US5] Tạo AuthorizationPanel tại `frontend\src\features\dags\AuthorizationPanel.tsx`; typed list/detail/create/revoke, ONCE reservation Run ID/state, SCHEDULED chỉ run lịch, separate allow_empty consent, stale ETag/in-progress unknown và English warning revoke không cancel admitted replacement; Phụ thuộc: T111, T112, T044; Truy vết: BR-08, FR-053–FR-054, NFR-002; Kiểm chứng: API thật, browser mới reload quyền không local-only state, không dùng ONCE activate lịch hoặc tự bật allow_empty.
- [x] T117 [US5] Tạo confirmation/deployment UI tại `frontend\src\features\dags\DeploymentPanel.tsx`, `frontend\src\pages\DagBuilder.tsx`; support consent và AuthorizationPanel T116, scope/revision/allow_empty riêng, polling bounded/unknown/reconcile/new paused/Open Airflow; Phụ thuộc: T115, T116; Truy vết: FR-035–FR-041, FR-053–FR-054, NFR-002; Kiểm chứng: English pending/parse/timeout không success giả, activation FULL_REFRESH cần SCHEDULED.
- [x] T118 [US5] Viết/chạy Airflow ETL integration tại `tests\airflow\test_execution.py`, `tests\airflow\test_revision_lifecycle.py`; rebuild image wheel hiện tại, manual+cron/scheduled/TI binding/old-clear/redeploy/API lost và tám route thật; Phụ thuộc: T117, T104; Truy vết: SC-003, SC-009, SC-014, ma trận N/W/AJ/AK; Kiểm chứng: parse/version+run/task trạng thái thật và target values, không chỉ registration.
- [x] T119 [US5] Viết/chạy Airflow authorization lifecycle integration tại `tests\airflow\test_authorization_lifecycle.py`; early trigger T112→reservation→bind→native lock→admission→target ledger, scheduled/manual/backfill discrimination, double submit/revoke barriers/admission response loss/target commit loss/clear success/extraction retry/terminal close; Phụ thuộc: T118, T112, T111, T085; Truy vết: BR-08, FR-053–FR-054, SC-006, SC-014; Kiểm chứng: PG/MySQL/Airflow thật, chỉ một run/commit, ONCE không chuyển run, SCHEDULED không manual, protected evidence giữ sau revoke.
- [x] T120 [US5] Viết/chạy wizard E2E và docs tại `tests\e2e\dag_builder.spec.ts`, `docs\operations\dag-deployment.md`; template download→validate→consent/quyền→register→Airflow link, source invalid/external ID/stale confirm, ONCE trigger/SCHEDULED activation khác nhau; Phụ thuộc: T118, T119, T098; Truy vết: US-05, SC-002, BR-08, ma trận W/AL; Kiểm chứng: <=10phút thao tác fixture chuẩn, T096/T097/T119/E2E PASS.

## Phase 7 — Monitoring, Dashboard và Settings

**Điều kiện bắt đầu**: T120 đạt; client/deployment/runtime không xây lại từ đầu.
**Kết quả dự kiến**: US9 monitoring/control, US10 Dashboard thật, US11 Settings và UX đầy đủ.
**Cách kiểm tra/test**: T121/T128/T133 viết trước; T127/T132/T137 nghiệm thu độc lập.
**Điều kiện hoàn thành**: T121–T137 đạt; không copy Airflow history, external read-only, KPI đúng/incomplete rõ, settings không mutate run deployed.

### US9 — Theo dõi và điều khiển DAG (P1)

- [x] T121 [P] [US9] Viết monitoring/control/log contract tests tại `tests\api\test_monitoring.py`, `tests\airflow\test_control.py`; DAG/run/TI/log paging/token/map_index, trigger logical_date:null/stable runID, pause confirm/external read-only; Phụ thuộc: T120; Truy vết: FR-063–FR-070, FR-096; Kiểm chứng: 409/timeout reconcile cùng ID, no secret logs.
- [x] T122 [US9] Mở rộng client monitoring tại `backend\src\aat_api\airflow_client\monitoring.py`; list/details/runs/TI/logs với token query/try_number, page cap1MiB/redact/structured normalize, all pagination; Phụ thuộc: T121, T101; Truy vết: FR-063–FR-065, FR-069, FR-077; Kiểm chứng: schema3.3.2 thật, missing logs có lý do không HTML raw.
- [x] T123 [US9] Tạo monitoring service/routes tại `backend\src\aat_api\services\monitoring.py`, `backend\src\aat_api\routes\monitoring.py`; API run_type/task/error_summary/log unavailable_reason, managed metrics phase/protected_bytes/recovery_summary/revision, external Not available, DAG last_successful_run nullable/availability và deep links; Phụ thuộc: T122, T082; Truy vết: FR-063–FR-065, FR-069–FR-070, FR-075; Kiểm chứng: required typed fields/null khác0, không app DB mirror history.
- [x] T124 [US9] Hoàn thiện monitoring controls bằng primitives T112/T113 tại `backend\src\aat_api\services\dag_control.py`, `backend\src\aat_api\workers\dag_control.py`; reuse reservation/idempotency/trigger/activation, filter ownership/pause readback không cancel/thu hồi, durable reconcile; Phụ thuộc: T121, T107, T110, T033, T112, T111, T113; Truy vết: FR-066–FR-068, FR-096, BR-08, BR-20; Kiểm chứng: API lost/409 cùng identity, không tạo trigger/state implementation thứ hai, command accepted khác executed.
- [x] T125 [US9] Gắn control routes tại `backend\src\aat_api\routes\dag_control.py`; Operation202/If-Match/idempotency/revision guards, external mutation reject; Phụ thuộc: T124, T123; Truy vết: FR-066–FR-068, AS-07; Kiểm chứng: T121 qua HTTP thật và readback Airflow state.
- [x] T126 [US9] Tạo Monitoring UI tại `frontend\src\features\monitoring\RunDetails.tsx`, `frontend\src\pages\Monitoring.tsx`; ownership/list/filter/tasks/attempt logs/trigger/pause/Open Airflow, pending/unknown/partial; Phụ thuộc: T125, T044; Truy vết: US-09, FR-063–FR-070; Kiểm chứng: English API integration, redacted paged logs, external không có controls.
- [x] T127 [US9] Viết/chạy monitoring E2E tại `tests\e2e\monitoring.spec.ts`, docs tại `docs\operations\monitoring.md`; deep link Airflow3.3.2 thật, trigger/pause/run logs/timeouts/down states; Phụ thuộc: T126; Truy vết: US-09, ma trận T/W/AJ/AK; Kiểm chứng: T121 và E2E PASS, pause không đổi run đang chạy thành canceled.

### US10 — Dashboard đáng tin cậy (P2, thuộc MVP)

- [x] T128 [P] [US10] Viết KPI/date/pagination contracts tại `tests\unit\test_dashboard_metrics.py`, `tests\api\test_dashboard.py`; inventory khác run, success denominator0/null, queued/other, lifetime/date/DST/schedule history unknown; Phụ thuộc: T120; Truy vết: FR-071–FR-078, BR-11–BR-12, SC-008; Kiểm chứng: expected 100% fixture, thiếu page không tổng chính xác giả.
- [x] T129 [US10] Tạo Dashboard aggregator tại `backend\src\aat_api\services\dashboard.py`; Airflow all pages/max4request, cache30giây key scope/date/timezone/ownership, GET retry<=3/tổng30giây, incomplete/unavailable/stale; Phụ thuộc: T128, T122; Truy vết: FR-071–FR-078, NFR-009; Kiểm chứng: date start/queued fallback không logical_date, manual invalidate, không DB mirror.
- [x] T130 [US10] Tạo schedule/statistics và Dashboard route tại `backend\src\aat_api\services\schedule_statistics.py`, `backend\src\aat_api\routes\dashboard.py`; preset groups/current-vs-historical/recent series/next-run và required last_successful_run/availability lifetime theo scope không đổi bởi date filter; Phụ thuộc: T129; Truy vết: FR-073–FR-075, BR-11–BR-12; Kiểm chứng: history thiếu UNKNOWN/UNAVAILABLE không đoán từ recent_runs/current schedule, UI lifetime nhãn riêng.
- [x] T131 [US10] Tạo Dashboard UI tại `frontend\src\features\dashboard\Metrics.tsx`, `frontend\src\pages\Dashboard.tsx`;8KPI/SVG charts/recent/date/timezone/manual/auto refresh/last update, empty0 khác unavailable/stale; Phụ thuộc: T130, T044; Truy vết: US-10, FR-071–FR-078; Kiểm chứng: typed API thật, English labels và responsive không mock số liệu.
- [x] T132 [US10] Viết/chạy Dashboard integration/E2E tại `tests\airflow\test_dashboard_truth.py`, `tests\e2e\dashboard.spec.ts`; fixture đủ state/managed/external/multipage/API down, expected KPI/lifetime/timezone; Phụ thuộc: T131, T127; Truy vết: SC-008, ma trận S/Z; Kiểm chứng: 100% aggregate đối chiếu Airflow thật, không cache success khi unavailable.

### US11 — Settings và UX nhất quán (P2, thuộc MVP)

- [x] T133 [P] [US11] Viết Settings contract tests tại `tests\api\test_settings.py`; ranges batch1..10000/refresh5..3600/retention1..365, IANA, If-Match, readonly connectivity/version, persistence; Phụ thuộc: T120; Truy vết: FR-079–FR-080, BR-14; Kiểm chứng: default mới không đổi config/run hiện hữu.
- [x] T134 [US11] Tạo Settings service/routes tại `backend\src\aat_api\services\settings.py`, `backend\src\aat_api\routes\settings.py`; defaults batch1000/refresh30/timezoneUTC/staging7, connectivity readonly, không public retry/chunk setting ngoài contract; Phụ thuộc: T133, T027, T028, T102; Truy vết: FR-079–FR-080, FR-088, BR-14; Kiểm chứng: GET/PATCH errors/ranges đúng, worker GC không xóa protected theo setting mới.
- [x] T135 [US11] Tạo Settings UI tại `frontend\src\pages\Settings.tsx`; units/ranges/readonly connectivity/application info, English field feedback, apply refresh kỳ tiếp theo; Phụ thuộc: T134, T044, T131; Truy vết: US-11, FR-079–FR-080; Kiểm chứng: form API/typecheck/persistence, không optimistic revision.
- [x] T136 [US11] Đồng bộ UX shell/components tại `frontend\src\components\Feedback.tsx`, `frontend\src\components\ConfirmationDialog.tsx`, `frontend\src\app\App.tsx`; keyboard/focus/label/step feedback/390px tables/neutral branding và map English dependency errors; Phụ thuộc: T135, T126, T117, T059, T045; Truy vết: NFR-001–NFR-002; Kiểm chứng: six-page audit1440/390, không English Markdown hoặc Vietnamese UI ngoài thuật ngữ hợp lệ.
- [x] T137 [US11] Viết/chạy Settings/UX E2E tại `tests\e2e\settings.spec.ts`, `tests\e2e\accessibility.spec.ts`, docs tại `docs\operations\settings.md`; readonly/range/restart/scope và keyboard/main-action visibility; Phụ thuộc: T136; Truy vết: US-11, NFR-001–NFR-002, ma trận X/Z; Kiểm chứng: T133/E2E PASS, defaults không đổi deployed config.

## Phase 8 — Tích hợp cuối và bàn giao

**Điều kiện bắt đầu**: T132 và T137 đạt; các gate phase trước đã nghiệm thu.
**Kết quả dự kiến**: MVP toàn bộ US1–US11, A–AM có bằng chứng tái lập, samples/docs sử dụng được.
**Cách kiểm tra/test**: T138–T149 trên stack thật; T150/T151 tài liệu; T152 cổng cuối.
**Điều kiện hoàn thành**: Không mandatory test NOT_RUN/BLOCKED/FAILED; no Critical/High chưa giải quyết; không tuyên bố MVP hoàn thành chỉ với US1 hoặc core slice.

- [x] T138 Mở rộng Compose test profile/Playwright runtime đã tạo T004/T011 tại `docker-compose.yml`, `docker\tests\playwright.Dockerfile`, `tests\e2e\playwright.config.ts`; giữ backend-tests root tests và e2e-tests browser/client1.65.0, bổ sung full regression/fixture namespaces/cleanup không user data; không là producer đầu tiên của runner cho E2E Phase3–7; Phụ thuộc: T132, T137, T004, T011, T013; Truy vết: FR-085, NFR-010; Kiểm chứng: đúng lệnh Quickstart unit/API/integration/ETL/Airflow/E2E/stress chạy trong container.
- [ ] T139 [P] Tạo/chạy regression UI/API mới tại `tests\e2e\history_parser_authorization.spec.ts`; browser mới history/table detail, parser candidate/PATCH/stale/active-recovery guards, ONCE reserve/retry/rerun cần quyền mới, scheduled allow_empty consent/list/revoke warning và typed fields/dashboard lifetime; Phụ thuộc: T138, T058, T067, T116, T119; Truy vết: FR-015–FR-017, FR-028, FR-053–FR-054, FR-075, BR-08; Kiểm chứng: stack thật/browser1440/390, no secret hoặc success giả, readonly/unknown/stale feedback English.
- [ ] T140 [P] Tạo/chạy fresh one-command/restart verification tại `tests\integration\test_one_command_startup.py`; default không .env, Airflow API/UI auth, migrations/seed secrets idempotent, restart extraction/commit/refresh, lost secret/volume/init failure không reset; Phụ thuộc: T138; Truy vết: US-01, FR-081–FR-083, FR-099–FR-100, SC-001, ma trận AM; Kiểm chứng: đúng `podman compose up --build -d`, ghi engine/provider đã nghiệm thu (không suy Docker-tested từ Podman), services READY thật và workflow sample sau init không setup thêm.
- [x] T141 [P] Tạo/chạy full UI vertical workflow tại `tests\e2e\full_workflow.spec.ts`; Connections→download sample→table create→file/ETL upload→preview→deploy/parse→run→monitor/dashboard/Open Airflow; Phụ thuộc: T138; Truy vết: US-02–US-11, SC-002, SC-009; Kiểm chứng: UI/API/DB/Airflow thật, table/DAG/data values và <=10phút thao tác fixture.
- [x] T142 [P] Tạo/chạy cross-DB Airflow regression tại `tests\airflow\test_cross_database.py`; PG→PG/MySQL→MySQL/PG→MySQL/MySQL→PG, source!=target, mappings/PK ghép/NULL/decimal/temporal; Phụ thuộc: T138; Truy vết: FR-001, SC-003, SC-015, ma trận C–F/I/AE; Kiểm chứng: 4routes target count/value/key và staging evidence thật.
- [ ] T143 [P] Tạo/chạy file-to-DB Airflow regression tại `tests\airflow\test_file_database.py`; CSV/TXT→PG/MySQL, parser checksum/quoted NULL/headerless/multiline, format/type errors và missing file; Phụ thuộc: T138; Truy vết: US-03, US-07, FR-001, ma trận G/H/U/AF; Kiểm chứng: 4routes data thật, FULL_REFRESH invalid source không empty target.
- [ ] T144 [P] Tạo/chạy Airflow retry/commit-loss regression tại `tests\airflow\test_retry_recovery.py`; source/target down, kill không finally, app metric fail, stable retry binding/checkpoint, rerun mới/cảnh báo APPEND; Phụ thuộc: T138; Truy vết: FR-051, FR-060, SC-014, ma trận K/R/AH/AJ; Kiểm chứng: no blind duplicate replay, commit uncertain giữ PROTECTED và đối soát120giây hoặc lý do blocked.
- [ ] T145 [P] Tạo/chạy FULL_REFRESH regression tại `tests\airflow\test_full_refresh_recovery.py`; pre-extract/mapped validation/mid-insert/COMMIT lost/zero-row/authorization revoked/invalidated trước admission và recovery sau revoke/dependency reject, reader old/new ở isolation hỗ trợ; Phụ thuộc: T138; Truy vết: NFR-005, FR-053–FR-054, SC-006, SC-013, ma trận L/M/AC; Kiểm chứng: old data giữ/phục hồi, một replacement commit, unknown không success hoặc replay; không tạo TTL/EXPIRED cho authorization; confirmation token10phút hết hạn chặn request mới nhưng replay cùng Idempotency-Key/hash trả intent cũ, không giải phóng ONCE.
- [ ] T146 [P] Tạo/chạy concurrency/revision regression tại `tests\airflow\test_concurrent_runs.py`; hai managed DAG/connection aliases cùng target, manual+scheduled, redeploy drain/old-clear/credential change,300giây lock wait; Phụ thuộc: T138; Truy vết: BR-09, BR-20–BR-21, SC-014, ma trận AI/AJ/AK; Kiểm chứng: một writer, run không mất/gộp, no target/revision đổi giữa run.
- [ ] T147 [P] Tạo/chạy Airflow large-data regression tại `tests\stress\test_airflow_memory.py`; dataset>1GiB/>20batches, RSS512MiB/process/parallelism2/scheduler2GiB, quota/reserve/scratch/disk staging loader/checksum/retention GC; Phụ thuộc: T138; Truy vết: SC-007, NFR-004, ma trận O/V/AD/AH; Kiểm chứng: RSS/bytes/manifest/row metrics thực, kill trước OOM an toàn và protected không GC.
- [ ] T148 [P] Tạo/chạy security/language/contract audit tại `tests\integration\test_security_surfaces.py`, `tests\e2e\language.spec.ts`, `tests\api\test_contract_drift.py`; password DB/DAG/API/log/XCom scans, injection/macro/path/origin/service token/runtime scope grants, Markdown tiếng Việt/UI+Excel tiếng Anh; Phụ thuộc: T138; Truy vết: SC-004, SC-011, NFR-001, NFR-003, ma trận P/Y/Z/AL; Kiểm chứng: không secret leak/input nguy hiểm không side effect, runtime operations/required schemas so contract hiện tại không hardcode số lượng.
- [ ] T149 [P] Tạo/chạy performance/status regression tại `tests\integration\test_response_limits.py`; p95 list/detail/preview100<=3giây, connection<=30giây/deploy<=120giây, Dashboard all-page truth/incomplete/stale/lifetime, resources/fixture công bố; Phụ thuộc: T138; Truy vết: SC-008, SC-010, NFR-009, ma trận S/Q/W; Kiểm chứng: không dùng cached/mock số liệu thay proof hoặc timeout để giả fail đã rollback.
- [ ] T150 [P] Hoàn thiện README/architecture/API/Excel/operations docs tại `README.md`, `docs\architecture.md`, `docs\api.md`, `docs\excel-definitions.md`, `docs\operations\troubleshooting.md`; Vietnamese, startup/no hidden setup/load/keys backup-restore/recovery/cleanup/limits/revision tradeoff, không mô tả chưa test như hoàn thành; Phụ thuộc: T138; Truy vết: FR-086–FR-087, Constitution XI; Kiểm chứng: link checker và người khác theo workflow/error instructions tái hiện được.
- [ ] T151 Hoàn thiện sample pack và đồng bộ thiết kế tại `samples\definitions\Table Definition.sample.xlsx`, `samples\definitions\ETL Definition.sample.xlsx`, `samples\data\customers.csv`, `samples\data\customers.txt`, `specs\001-airflow-automation-tool\quickstart.md`; giữ sample refs/version/English instructions, phản ánh app seed và download artifacts, cập nhật đúng tài liệu nguồn nếu implementation có thay đổi được chấp thuận; Phụ thuộc: T140, T141, T142, T143, T150; Truy vết: FR-018, FR-084, FR-087; Kiểm chứng: downloaded Excel dùng ngay trên fresh stack, references/checksums valid và không bước setup ngầm.
- [ ] T152 Chạy stabilization/cổng bàn giao và ghi báo cáo tại `docs\testing\acceptance-report.md`; tổng hợp A–AM/BR-08/SC-001–SC-015/US1–US11, engine/client/server/Compose-provider/build/commit nếu có/locks/digest/env/commands/resources/input-checksum/expected-actual/artifacts/PASS-FAIL-NOT_RUN-BLOCKED, sửa lỗi liên quan/rerun selectors; Phụ thuộc: T140, T141, T142, T143, T144, T145, T146, T147, T148, T149, T151, T139, T119; Truy vết: SC-012, FR-085, BR-08, Constitution X; Kiểm chứng: đủ evidence không mandatory bị bỏ qua, Analyze không Critical/High unresolved, checklist reviewer không tự đánh dấu.

## Dependency và thứ tự thực hiện

### Đồ thị phase

```text
Phase1 infrastructure → Phase2 foundation → Phase3 connections → Phase4 table
Phase4 → Phase5 engine/file/policies → Phase6 DAG integration
Phase6 → Phase7 monitoring/dashboard/settings → Phase8 regression/bàn giao
```

Đây là thứ tự gate dự kiến, không hàm ý mọi task trong phase sau đều phụ thuộc mọi task trước. Prerequisite chính xác nằm tại từng dòng. Cho phép chuẩn bị test/nhánh độc lập sau prerequisite; không nghiệm thu phase khi gate trước chưa đạt.

### Đồ thị user story

```text
US1 bootstrap → foundation → US2 → US4
US4 → US3 File Sources
US4 → US6 DB engine + US8 policies
US3 + US6 + US8 → US7 File-to-DB
US6 + US7 + US8 → US5 DAG thật → US9 monitoring/control
US5/client → US10 Dashboard
foundation/settings model + US5/client → US11 Settings
US1–US11 → final acceptance
```

- US1 bootstrap hoàn thành tại T014; tiêu chí môi trường đầy đủ và workflow mẫu của US1 được chốt tại T140/T152.
- US6 pipeline ban đầu có thể thử độc lập source/staging/mapping; vertical load hoàn chỉnh cần US8 policy dispatch T092.
- US8 tests/policy có thể chạy trực tiếp trên fixture DB, không cần chờ DAG UI.
- US7 cần file parser/validation, engine và policies, không coi fixture file nhỏ là bằng chứng stress.
- US9 cần client/deployment/binding đã xây phase6. US10/US11 có nhánh test độc lập, nhưng E2E cuối dùng Airflow thật.
- P2 không phải ngoài MVP. Không được bỏ Dashboard/Settings khi tuyên bố hoàn thành toàn sản phẩm.
- Runner đi theo T004 → T011 → T013 → T014 trước foundation và T046; không thêm cạnh ngược
  từ E2E sớm về T138. T095 hội tụ cả engine lẫn File Sources E2E T069; T120 cần template
  download T098. T152 vì vậy có dependency bắc cầu tới toàn bộ 151 task trước.

### Ví dụ song song theo story

| Story | Các task độc lập có thể chạy cùng nhau sau prerequisite | Điểm hội tụ |
| --- | --- | --- |
| US1 | T007/T008/T009 sau T004; T005 nhánh frontend | T011 rồi startup T013 |
| US2 | T035/T036; T038/T039 sau T036 | T041 rồi API/UI |
| US3 | T061/T062 | T064; storage/parser/validation trước UI |
| US4 | T047/T048; T053/T054 sau T051 | T055 preview |
| US5 | T096/T097 | T100 config và T101 client hội tụ tại binding/factory |
| US6 | T072/T073 sau T071 | T074 rồi staging/load |
| US7 | T143 cùng T142 ở phase8, isolated fixture | T152 nghiệm thu 8routes |
| US8 | T087/T088 sau T080/T083 | T090 recovery |
| US9 | T121 cùng T128/T133, khác files | T125/control và monitoring UI |
| US10 | T128 cùng T121/T133 | T129 aggregator cần client T122 |
| US11 | T133 cùng T121/T128 | T134 rồi Settings UI |

Không chạy hai task sửa `docker-compose.yml`, generated API client hoặc sample workbook cùng lúc. Task `[P]` chỉ nhận công việc khi prerequisite đã hoàn thành; các DB tests cần namespace/project riêng.

## Bao phủ yêu cầu và bằng chứng

Các nhóm dưới đây là chỉ mục bổ sung, không thay traceability và acceptance tại từng task. BR/NFR/EC liên quan được thực hiện trong task cùng miền, không ngầm bỏ vì không có mã FR mới.

| Yêu cầu Spec | Task implementation chính | Task kiểm chứng |
| --- | --- | --- |
| FR-001 | T072–T073, T086–T089, T093, T104 | T094, T118, T142–T143 |
| FR-002 | T003, T045, T059, T068, T117, T126, T131, T135 | T137, T141 |
| FR-003–FR-009 | T019, T037–T043 | T035–T036, T046 |
| FR-010–FR-017 | T020, T021, T063–T068, T067 | T061–T062, T069, T143, T139 |
| FR-018–FR-028 | T020, T049–T059, T058 | T047–T048, T060, T141, T151, T139 |
| FR-029–FR-041 | T022–T024, T098–T117 | T096–T097, T118–T120 |
| FR-042–FR-048 | T071, T074, T077–T078, T099–T100 | T070, T094, T142–T143 |
| FR-049–FR-054 | T078–T080, T086–T092, T110, T023–T031, T085, T112–T116, T113 | T017, T084, T083, T094, T144–T146, T119–T139 |
| FR-055–FR-062 | T072–T076, T081–T082, T090–T093 | T070, T095, T144, T147 |
| FR-063–FR-070 | T122–T126 | T121, T127, T141 |
| FR-071–FR-078 | T129–T131 | T128, T132, T149 |
| FR-079–FR-080 | T027, T134–T136 | T133, T137 |
| FR-081–FR-084 | T004–T012, T029–T030, T049, T098, T151 | T013–T014, T140–T143 |
| FR-085–FR-087 | T004, T011, T138, T150–T152 | T013, T140–T149, T152 |
| FR-088–FR-090 | T072–T073, T075–T076 | T070, T095, T147 |
| FR-091–FR-093 | T063, T074, T077–T078, T082 | T062, T070, T094, T142–T143 |
| FR-094–FR-095 | T076, T090–T091 | T095, T144, T147 |
| FR-096–FR-098 | T051, T099, T101, T107–T109, T124 | T048, T097, T118, T144, T146 |
| FR-099–FR-100 | T007–T012, T029–T034, T091 | T013, T016, T140 |
| NFR-001–NFR-003 | T003, T032, T037, T040, T050, T077, T136, T150 | T046, T060, T137, T148 |
| NFR-004–NFR-007 | T075–T076, T080, T082, T090–T091 | T095, T140, T144–T147 |
| NFR-005 — Toàn vẹn | T077, T089–T090 | T070, T083, T145 |
| NFR-008–NFR-010 | T002–T006, T028, T101–T109, T122, T129 | T014–T016, T118, T149, T152 |
| SC-001–SC-004 | Hạ tầng/seed/templates/parser/engine/wizard | T140–T143, T048, T120, T148 |
| SC-005–SC-007 | Policies/recovery/staging | T083, T094–T095, T144–T147 |
| SC-008–SC-012 | Dashboard/Airflow/performance/security/báo cáo | T118, T132, T148–T149, T152 |
| SC-013–SC-015 | Snapshot/commit recovery/lossless types | T070, T095, T142–T147 |
| BR-08 — 5 quyết định Clarify | T023, T026, T031, T085, T089–T092, T103–T104, T110–T117 | T017, T084, T118–T120, T139, T144–T146 |

### Ma trận nghiệm thu A–AM

| Ca bắt buộc | Bằng chứng task |
| --- | --- |
| A/B/P/AL — Table/Excel/versions/duplicate/implicit | T048, T060, T099, T120, T148 |
| C–H/U/I/AE — 8routes/mapping/typed values | T094, T118, T142–T143 |
| J/K — UPSERT rerun và APPEND | T083, T094, T144 |
| L/M/AC — FULL_REFRESH success/failure/extraction/transaction | T083, T118, T145 |
| N/T/W/AJ/AK — Lịch/link/registration/API/revision | T097, T118–T121, T127, T144, T146 |
| O/V/AA/AD/AH/AI — Snapshot/memory/disk/concurrency/kill | T070, T095, T144, T146–T147 |
| Q/Y/AB/AF — Connection/security/key/drift/parser | T036, T062, T070, T083, T148 |
| R/AG — Dependency down và row reconciliation | T082–T083, T094, T144–T145 |
| S/Z/X — Dashboard/UI/language/retention/settings | T069, T132, T137, T148–T149 |
| AM — Startup/restart/secret/volume | T013, T034, T140 |

## Chiến lược triển khai và kiểm chứng độc lập

1. Bootstrap US1 là increment đầu tiên, không phải MVP đầy đủ. Dựng shell/health/services và resolve dependency trước.
2. Sau foundation, bàn giao Connections rồi Table Management với UI/API/DB thật. Tạo test trước implementation; không chờ phase8 mới phát hiện contract mismatch.
3. US3 nghiệm thu upload/preview/validate/restart không cần DAG. US6 nghiệm thu snapshot/staging/types; US8 nghiệm thu policies bằng engine trực tiếp; US7 thêm bốn file routes.
4. Core vertical slice có giá trị tiếp theo: US2 + US4 + US6/US8 + US5, chạy một DB-to-DB DAG thật. Đây chỉ là mốc demo, không được bỏ 8routes/P2.
5. Sau US5 mới nghiệm thu registration/manual/cron/runtime/revision. US9 kiểm control/logs độc lập bằng DAG fixture; US10 kiểm KPI với Airflow fixture đủ trạng thái; US11 kiểm persisted settings/scope/keyboard.
6. Cuối cùng chạy regression A–AM và Quickstart, bổ sung tài liệu/bằng chứng thật. Lỗi task liên quan phải sửa root cause và rerun selector; thay đổi nghiệp vụ phải cập nhật đúng Spec/Clarify/Plan trước.

### Lệnh runner dự kiến sau implementation

```powershell
podman compose up --build -d
podman compose --profile test run --rm backend-tests pytest tests/unit tests/api
podman compose --profile test run --rm backend-tests pytest tests/integration tests/etl
podman compose --profile test run --rm backend-tests pytest tests/airflow
podman compose --profile test run --rm e2e-tests npx playwright test
podman compose --profile test run --rm backend-tests pytest tests/stress -m large_data
```

Khi làm task riêng, chọn file/selector nhỏ nhất bao phủ thay đổi; các thư mục trong lệnh container tuân layout Linux của test image. Lệnh trên là kế hoạch tương lai, chưa phải kết quả đã chạy.
Runner/profile tối thiểu có từ Phase1 tại T004/T011 và được nghiệm thu bootstrap T013;
Phase2 chỉ mở rộng fixture/harness nền. Chọn selector phù hợp chức năng đã triển khai,
không yêu cầu future endpoint PASS, không dùng skip để nghiệm thu story. Manifest/lock
E2E riêng ở `tests\e2e`, cài bằng npm ci trong image, client/browser1.56.1 đồng bộ.

## Thống kê task hiện hành và lịch sử sau Clarify

- Tổng cộng **152 task**: **34** setup/foundation, **103** gắn user story và **15** final integration; **53** task có `[P]`.
- Số task theo phase 1–8: **14 / 20 / 12 / 14 / 35 / 25 / 17 / 15**.
- Số task theo story: US2=12, US3=9, US4=14, US5=25, US6=14, US7=2, US8=10,
  US9=7, US10=5, US11=5. US1 là scope bootstrap/first boot/restart tại setup và final gates,
  không gán nhãn story trái convention của các phase dùng chung.
- Contract47operations/53schemas là baseline thiết kế hiện tại; tests/codegen đọc contract
  hiện tại và so cấu trúc, không đóng đinh số lượng để cản contract update.
- Preparation T081 chưa có target writer: chỉ xác minh snapshot/staging/mapping/protocol.
  Metrics T082 dùng fixture ledger độc lập; writers T086–T089, recovery T090 và dispatch
  T092 mới nghiệm thu load thật. Không tạo cycle bằng cách để preparation cần dispatch.
- Trigger T112 và activation T113 có worker/routes ở phase6 trước cron/manual tests T118;
  phase7 T124/T125 tái sử dụng, không dời tích hợp cần thiết tới sau consumer.
- Lượt sau Clarify đã bổ sung explicit lifecycle/schema/repository/race tests, history/table detail, parser
  revision, authorization UI/revoke và regression BR-08. Không thay đổi Spec/Plan/Contracts,
  binary samples, source code hoặc reviewer checklist trong lượt Tasks này.

### Ánh xạ ID lịch sử của finding F2

Các ID trong báo cáo Analyze/Plan của lượt 137 task là tham chiếu lịch sử, không phải
prerequisite của lượt hiện tại. Dùng bảng này khi đối chiếu finding cũ:

| ID lượt trước | ID hiện tại | Đầu ra |
| --- | --- | --- |
| T074 | T081 | Preparation và writer protocol, không target load |
| T075 | T082 | Metrics/projection độc lập writer |
| T081 | T090 | Retry/recovery sau policy writers |
| T083 | T092 | Dispatch và kiểm chứng toàn pipeline sau writers |
| T137 | T152 | Cổng bàn giao cuối |

## Ghi chú quản trị

- Không tự đánh dấu checklist reviewer [spec-quality.md](checklists/spec-quality.md). `[x]` của reviewer đánh giá chất lượng requirement, không chứng minh runtime hoàn thành.
- Task chỉ hoàn thành khi đầu ra và kiểm chứng tương ứng đã đạt; failure evidence phải được giữ an toàn, không xóa artifact recovery để “làm sạch”.
- Việc đánh lại ID và bổ sung models/API/tests sau Clarify là lịch sử của bản152task.
  Lượt đồng bộ2026-11-08 giữ nguyên toàn bộ ID,8phase và checkbox chưa đánh dấu; chỉ cập
  nhật task descriptions/dependencies theo Plan, không thêm source code.

## Đồng bộ có mục tiêu theo Plan ngày 2026-11-08

- Private runtime: T005 chặn cả root/public-prefix variants; T103/T104 giữ canonical root,
  server override đã tồn tại. Không lặp kết luận Analyze sai rằng OpenAPI thiếu override.
- Runner: T004 tạo Dockerfile/config/manifest/lock, T011 tạo test profile, T013 kiểm smoke,
  T014 kiểm reproducibility/CI; T046 dùng ngay runner hiện có, T138 chỉ mở rộng regression.
- Foundation T034 không nghiệm thu Connections CRUD hoặc Settings API; các API đó vẫn
  nằm Phase3/7. Backend Phase1 chỉ liveness; product readiness hoàn thiện T034.
- T095 phụ thuộc T069 để nghiệm thu File Sources trước Phase6; T120 phụ thuộc T098 để
  ETL template download sẵn sàng. Không đánh lại ID hoặc thêm dependency tới task tương lai.
- T145 dùng revoked/invalidated và đối soát sau revoke, không có authorization TTL/EXPIRED;
  confirmation token hết hạn khác replay cùng key/hash giữ intent/reservation. BR-08 giữ nguyên.
- NFR-005 được dẫn trực tiếp tại T070/T077/T083/T089/T090/T145. T001/T014/T030 quy định
  sample EOL/hash từ checkout→image→volume; `.gitattributes`/CI là đầu ra implementation
  tương lai, không có sample bytes hoặc policy file nào được sửa trong lượt Tasks này.
- Không thay đổi Spec, Plan, Research, Data Model, contracts, Quickstart, Constitution,
  reviewer checklist hoặc ghi nhận kiểm chứng lịch sử của Plan trong lượt này.
- Bước tiếp theo: `/speckit-analyze` trên bản152task đã cập nhật, reviewer đánh giá checklist,
  rồi triển khai Phase1 T001–T014 theo gate; bootstrap không phải MVP đầy đủ.

### Kiểm chứng cấu trúc Tasks trong lượt đồng bộ

- Script Python chỉ đọc xác nhận152ID liên tiếp/duy nhất, đủ checkbox chưa đánh dấu,
  đường dẫn/nhãn story, dependency/truy vết/kiểm chứng ở mỗi dòng;8phase và53nhãn `[P]`.
- Không ID phụ thuộc bị thiếu, không cạnh tới task phía sau hoặc chính nó, không cycle;
  T152 có151task tổ tiên. T095 nhận T069, T120 nhận T098, T046 nhận runner T004/T011/T013
  mà không phụ thuộc T138. Các liên kết Markdown local tồn tại.
- Mã tham chiếu trực tiếp hoặc khoảng mã trong các dòng task bao phủ100FR/10NFR/15SC,
  tổng125/125; đây là kiểm truy vết, không xác nhận đủ mọi hành vi hoặc test đã PASS.
- `git diff --check` không lỗi. Không có extension hooks cấu hình. Chưa chạy build,
  pytest/Playwright, CI EOL hoặc kiểm thử sản phẩm; không đánh dấu task/checklist hoàn thành.

## Tiến độ Phase1 ngày 2026-11-08

- T001 hoàn thành trong phạm vi skeleton: manifests, wheels0.1.0/editable installs,
  import boundaries và sample raw LF/hash đã kiểm trên Windows/Python3.13.15.
  T003 hoàn thành shell sáu route, npm ci/typecheck/build và Chromium1440/390.
- T002 có constraints chính thức và lock có hash cho Linux x86_64/CPython3.12, đã resolve
  và tải lại offline require-hashes; chưa install/pip check backend/custom Airflow thật
  vì không có Docker/Compose. Giữ checkbox chưa đánh dấu, trạng thái BLOCKED.
- T005 đã soạn frontend Dockerfile/nginx guards; build image/nginx runtime/proxy tests
  BLOCKED vì thiếu Docker. Không lấy Vite preview thay bằng chứng nginx.
- T004/T006–T014 chưa thực thi do prerequisite chưa nghiệm thu; không chuyển Phase2.
  Runner Playwright dùng riêng để kiểm shell T003 không thay runner/profile container T004/T011.
- Báo cáo lệnh, phiên bản, kết quả và giới hạn: [Báo cáo Phase1](../../docs/testing/phase1-report.md).
  Checklist reviewer giữ nguyên; Phase1/US1/MVP chưa hoàn thành.

## Đồng bộ Podman theo Constitution1.1.0 đã duyệt

Giữ152ID,8phase, phụ thuộc và checkbox T001/T003 hiện có. Baseline Plan dùng Podman;
runner examples hiện dùng `podman compose`, không là bằng chứng đã chạy. Bản ghi thiếu
Docker trong tiến độ trước sửa đổi là lịch sử; Podman hiện phản hồi nhưng T002/T005 còn
chưa nghiệm thu runtime, không tự đổi thành PASS. T004/T006–T014 vẫn tuân dependency.
T007–T010 phải kiểm roles/secret/UID/GID/persistence trên baseline Podman, giữ least privilege;
T046/T138/T141–T152 giữ selectors/fixtures/project-volumes isolation và A–AM/BR-08.
Sau đồng bộ phải Analyze và rà soát reviewer trước tiếp tục Phase1; không vào Phase2.

## Cập nhật thực thi Podman 2026-11-08 — trạng thái hiện hành

- T002 PASS: backend Linux/Python3.12.12 cài 32 dependency từ lock/hash, pip check sạch;
  image chính thức Airflow3.3.2/Python3.12.14 kiểm lock runtime/constraints và pip check sạch,
  airflow version vẫn3.3.2. Không đổi pin; SHA256 constraints giữ nguyên.
- T005 PASS: image frontend build thật; 4test nginx PASS, bao gồm GET/POST private prefixes
  có/không bearer, không request upstream; public proxy giữ path và SPA deep link đúng.
  Bearer dùng fixture cô lập; kiểm authorization trực tiếp trên endpoint thật vẫn thuộc T103.
- Các ghi nhận thiếu Docker trước đây là lịch sử, không còn là blocker T002/T005.
- T004/T006 và gate Phase1 chưa kết luận; xem báo cáo thực thi hiện hành.

- T004 PASS: backend wheel/liveness test1PASS, pytest runner6PASS, Playwright collect4test
  và Chromium141.0.7390.37 chạy thật trong image1.56.1.
- T006 PASS: custom image build/pip check/SDK+engine import và entrypoint airflow version3.3.2.
- T007 primitive/init test RED thiếu module trước implementation; GREEN1PASS trên Linux
  container overlay source, chưa thay bằng chứng Compose/volume permissions T011.

- T007 PASS: primitive/init GREEN trên Linux, named-volume secrets-init Exited(0),
  credential file được DB thật sử dụng thành công; random dùng os.urandom để tránh tên
  secrets.py che module chuẩn khi chạy trực tiếp. Không in secret.
- T008/T009 DB fixture sạch PASS44.33giây: init2lần, giữ sample edit, PG runtime không
  connect Airflow DB, MySQL grants/InnoDB/utf8mb4/strict. Đang bổ sung kiểm signature
  collision và tích hợp Airflow; chưa đóng gate Phase1.

- T008/T009 PASS trên DB fixture thật: roles/grants/sample init idempotent, giữ sửa đổi,
  InnoDB/utf8mb4/strict; support signature1 được kiểm sau init, collision test bổ sung.
- T010 PASS: fixture bật AAT_TEST_AIRFLOW=1 chạy148.50giây; official migration2lần Exited(0),
  API anonymous bị chặn, JWT service auth/API/UI thật PASS, LocalExecutor/parallelism2.
- T011 đang nghiệm thu Compose. Workspace có .pytest_cache ACL không đọc/di chuyển được
  làm Compose build context FAIL trước build, kể cả đã ignore. Không reset ACL. Dùng
  fixture source sạch byte-for-byte để tiếp tục kiểm stack; không báo workspace startup PASS.

## Nghiệm thu tiếp tục 2026-11-08 — cập nhật hiện hành

- T011/T012 PASS trên bản nocopy cuối:4test wiring/fault injection PASS34.72s; secret
  domains riêng, init exit23 chặn consumer, cgroup limits/UID/RO/loopback và probes thật.
- T013 PASS: project fresh aat-phase1-800be543, startup chuẩn và restart giữ volumes
  PASS249.15s; secret hashes, DB edits và artifacts giữ nguyên. Test profile chạy7unit
  PASS, DB init/grants/signature collision PASS, Airflow auth/API/UI PASS và4Playwright
  desktop/mobile PASS4.2s; secret values không có trong service logs.
- T014: compatibility3test PASS13.06s;7digest thật đã ghi docker/images.lock. Npm
  typecheck/build PASS, audit exit1 với2HIGH (react-router,zod). Không đổi pin. Image
  vulnerability scan đang chạy; workflow Windows/Linux đã tạo, CI remote NOT_RUN.
- Workspace gốc vẫn chưa có bằng chứng startup mới: lỗi ACL cache đã ghi riêng; không
  reset ACL hoặc dùng PASS fixture để thay kết quả workspace. Reviewer không thay đổi.

### Kết luận cuối lượt tiếp tục

T001–T013 PASS trong phạm vi bootstrap; T014 giữ [ ] và BLOCKED. Security scan7image
đã chạy với IDs khớp hiện tại, có HIGH/CRITICAL cần triage; npm audit2gói HIGH, không
đổi pin. CI Windows/Linux NOT_RUN dù workflow đã tạo/parse. Workspace gốc còn ACL cache
blocker; không lấy PASS fixture sạch thay startup tại workspace. Gate Phase1 BLOCKED,
không vào Phase2, không coi bootstrap là US1/MVP. Bằng chứng/kế hoạch đóng blocker tại
[phase1-report.md](../../docs/testing/phase1-report.md), máy đọc final-state/security JSON
cùng thư mục. Reviewer checklist/Constitution giữ nguyên trong lượt này.


### Trạng thái hiện hành sau remediation P1–P7 đã duyệt — 2026-11-08

Các kết luận trước mục này là lịch sử. P1–P7 đã áp dụng: Router7.18.5/Zod4.6.7,
Python3.12.16/Node22.23.4/npm10.9.4, PG17.11/MySQL8.4.13/nginx1.30.6-alpine3.24,
Airflow slim3.3.2 với standard/psycopg2/asyncpg theo official constraints không đổi,
Playwright client/browser1.56.1 giữ nguyên và runner OS lock. FROM/DB refs enforce digest.

T011/T012/T013 nghiệm thu lại PASS trên candidate fixture:6runtime tests, fresh/restart
597.552s, pytest7PASS/Playwright4PASS qua test profile; shell12checks và DB backup/restore
cũ→candidate namespace PASS. Compatibility3PASS13.527s,8source/runtime hashes và12scan
IDs khớp. Npm full/production audit0vulnerabilities. Lượt đầu thiếu asyncpg/CRLF lock và
SSH/HTTP failures giữ đúng FAIL lịch sử; không nới test/gate.

T014 vẫn[ ]/BLOCKED: security12targets còn634HIGH/CRITICAL occurrences (7final targets368),
CI remote Windows/Linux NOT_RUN; root ACL startup vẫn BLOCKED, fixture không thay clean
Git checkout. Không override constraints, commit/push, Phase2 hoặc sửa reviewer/Constitution.
Current project đọc `.tools/phase1-project.txt`, source fixture `.tools/phase1-compose-dir.txt`;
old stack/volumes và preview4173 giữ nguyên. Báo cáo/lệnh/evidence hiện hành tại
[phase1-report.md](../../docs/testing/phase1-report.md), quyết định tiếp tại
[t014-remaining-blockers.md](../../docs/proposals/t014-remaining-blockers.md).


### Lượt2 hardening — đang nghiệm thu trên feature branch

Author được chỉ định: le quang trung <rikateamovt1@gmail.com>. Commit a3c421e đã push lên
001-airflow-automation-tool-t014; CI Windows/Linux PASS đúng SHA, clean checkout raw
sample3PASS/fresh-restart442.108s/UI Airflow public login PASS. Giữ T014[ ]/BLOCKED:
source mới đang kiểm lại, security còn findings, chưa có approval override constraints/browser.
Npm12.2.2 Win/Linux build/audit và scan thử PASS; Go1.27.3 rebuild gosu1.19, loại tool
không dùng và OS Airflow lock có kiểm hardening thực. Pip26.3 vá vendor copies, app graph
không đổi. Tất cả trial và số liệu chờ cập nhật cuối xem phase1-report, không mở Phase2.

### Tiếp tục T014 trên workspace hiện tại — 2026-11-09

Áp dụng speckit-implement: prerequisites/checklist PASS, không có extension hooks. Đã sửa
record/validation image lock để đối chiếu FROM immutable và image ID, đồng bộ ba index/platform
digests với registry evidence (8image IDs không đổi), thêm hồi quy và selector CI. Runner mới
10unit PASS, frontend build/typecheck/npm audit0 và4nginx/proxy tests PASS. Scan mới3targets:
backend-tests40HIGH/2CRITICAL, frontend0/0, frontend-build34/1; không miễn trừ finding.
CI tại HEAD b29ae86 PASS Windows/Linux, thay đổi working tree lượt này CI remote NOT_RUN.
Podman hiện6.1.1 khác baseline lịch sử; full runtime/compatibility/scan baseline chưa tái kiểm.
T014 giữ[ ]/BLOCKED; A/B trong phương án lượt2 vẫn chờ duyệt. Chi tiết/lệnh/logs tại
[báo cáo T014 hiện hành](../../docs/testing/t014-current-report.md).

### Kết quả sau triển khai A/B đã duyệt — 2026-11-09

A/B đã áp dụng; upstream constraints giữ nguyên SHA256. Fresh/restart/persistence752.059s,
13unit/4E2E/5image compatibility/7runtime tests,12shell route/viewport và UI Airflow login PASS.
Scan đủ20targets với IDs cuối khớp: tổng1327HIGH/CRITICAL occurrences, riêng7final images248.
341nhóm vendor review vẫn chưa có reviewer approval; không miễn trừ hoặc hạ severity.
CI source mới và clean checkout immutable SHA chưa chạy vì working tree chưa commit.
T014 giữ[ ]/BLOCKED, không mở Phase2. Lệnh, logs, image IDs/hashes và bước tiếp theo tại
[báo cáo A/B](../../docs/testing/t014-ab-report.md).
# Trạng thái tiếp tục T014 — remediation vòng3, 2026-11-09

T014 giữ `[ ]`, chưa mở Phase2. Commit triển khai d57db09 đã push, CI Windows/Linux
và clean checkout static PASS. Bổ sung dnspython2.9.0 và Go1.27.3-Alpine3.24;
fresh/restart1310.699s,13unit/5compatibility/7runtime/4E2E, auth/UI/build/audit PASS.
Scan20targets đúng IDs cuối:784HIGH/CRITICAL occurrences (7final images/runners247),
149review groups chưa được reviewer duyệt đầy đủ. Gate security FAIL, Phase1 BLOCKED.
[Báo cáo hiện hành](../../docs/testing/t014-r3-report.md),
[results](../../docs/testing/t014-r3-results.json). Không sửa tiêu chí nghiệm thu/checklists.
