# Đề xuất gate phát triển local có điều kiện cho T014

**DRAFT — CHƯA ĐƯỢC DUYỆT. Ngày 2026-11-09.**

Yêu cầu lượt này chỉ cho phép chuẩn bị đề xuất. T014 vẫn `[ ]`/BLOCKED,
security FAIL, Phase2 chưa được phép bắt đầu. Tài liệu này không tạo waiver,
không thay Constitution/Spec/Plan/Tasks và không nghiệm thu MVP.

## 1. Quyết định đề nghị chủ dự án duyệt

| Mã | Quyết định cụ thể | Điều kiện |
| --- | --- | --- |
| D1 | Thêm quyền bắt đầu phát triển Phase2 local khi bootstrap đã kiểm và ngoại lệ có hạn được duyệt | Duyệt bản sửa quản trị và tài liệu trong patch bên dưới; không đánh T014 đầy đủ hoàn thành |
| D2 | Chấp nhận rủi ro tạm cho **147 nhóm/771 occurrences**, liệt kê từng ID loại C | Duyệt danh sách exact image/package/version, owner, controls và hạn; không bao gồm LEX-003 hoặc LEX-079 |
| D3 | Reviewer kết luận riêng **LEX-079, CVE-2023-45853**, 12 contexts, theo bằng chứng Debian/binary inventory | Chỉ ghi not-affected sau review. Nếu không đủ bằng chứng, giữ BLOCKED hoặc xin quyết định rủi ro mới; không tự nhập vào D2 |
| D4 | Chấp thuận kế hoạch triển khai theo mốc M0–M6 sau khi gate kích hoạt | Giữ dependency và tests của các phase; chưa phải nghiệm thu toàn bộ sản phẩm |

**LEX-003 không nằm trong xin miễn trừ:** phải khép đường dùng Brotli chưa vá trong build
trước khi kích hoạt gate. Duyệt D1/D2/D4 không tự giải quyết D3 hoặc LEX-003.
Chủ dự án có thể duyệt từng ID/nhóm; ID không được duyệt vẫn chặn phạm vi phụ thuộc.

Các artifact review:

- [Patch tài liệu dự kiến, chưa áp dụng](t014-conditional-local-gate-changes.patch).
- [Danh mục 149 nhóm A/B/C](t014-conditional-local-findings.md).
- [JSON đầy đủ 784 contexts, image IDs, tác động, owner, controls, hạn/thu hồi](t014-conditional-local-findings.json).
- [Kiểm tra source/image/môi trường chỉ đọc lượt này](t014-conditional-local-verification.json).
- [Snapshot KEV và phạm vi đối chiếu](t014-conditional-local-kev.json).

## 2. Phạm vi được phép nếu đề xuất được thông qua

Một operator trên cùng máy; chỉ loopback, không LAN/public/tunnel/reverse proxy bên ngoài.
Chỉ PostgreSQL/MySQL trong sandbox được tạo riêng, dữ liệu tổng hợp và workbook mẫu đã
kiểm soát; không dùng credentials/dữ liệu khách hàng, production DB, file hoặc endpoint
không tin cậy. Credentials kỹ thuật của sandbox vẫn là secrets và phải bảo vệ đầy đủ.

Không vô hiệu auth Airflow, private routes, origin protection, UID/mount/resource limits,
scanner hoặc SBOM. Không mounts engine socket, không privileged/chmod777. Giữ dữ liệu,
volumes/secrets và services A/B/R3 hiện hữu; môi trường nghiệp vụ mới dùng namespace/ports
riêng, không chuyển migrations vào volumes cũ. Với tài nguyên hiện có, nếu không đủ dung
lượng/RAM cho namespace mới, phải xử lý điều kiện tài nguyên trước khi khởi động, không
prune/reset hoặc tự dừng stack hiện có để vượt gate.

Đây là quyền **phát triển và demo local có điều kiện**. Các yêu cầu chức năng, BR-08,
an toàn dữ liệu/secrets, schema Excel/API và tám hướng ETL vẫn giữ nguyên. Giới hạn local
không chứng minh mọi finding không khai thác được; supply-chain hoặc container compromise
vẫn có thể ảnh hưởng host và artifacts, kể cả khi dataset là dữ liệu thử.

## 3. Baseline đã xác minh và bằng chứng tái sử dụng

HEAD `b0c947d23f1e9c23e9ce0a57b634f9e7a4c7b4ab`, implementation `d57db09`.
Đối chiếu toàn bộ hashes source trong R3 và20image IDs: không mismatch.
Hai project A/B và R3 vẫn có8services healthy/project,4init Exited(0)/project;
6containers có trước giữ nguyên trạng thái exited. Kiểm tra lượt này chỉ đọc.
Provider/runtime nghiệm thu: Podman6.1.1/Compose5.6.0, Linux/amd64/rootful/cgroupv2,
12CPU/~7.60GiB RAM engine. Không quảng bá baseline engine khác hoặc mức tài nguyên cao hơn.

| Tiêu chí | Kết quả hiện có | Cách sử dụng trong đề xuất |
| --- | --- | --- |
| Prerequisites/checklists/hooks | PASS;16/16,48/48; không extensions.yml | Checklists giữ read-only; không phải checkbox implementation |
| Startup/restart/persistence | PASS1310.699s | Tái sử dụng [R3](../testing/t014-r3-report.md), không restart lại trong lượt đề xuất |
| Unit/compatibility/runtime/E2E | PASS13/5/7/4 | Tái sử dụng logs R3 vì source/IDs khớp |
| Auth/operator UI/build/npm audits | PASS; audit0 | Không đồng nghĩa security image PASS |
| CI/clean checkout commit cuối | PASS theo [run42550978237](https://github.com/qtrugle0113/fpt-spec-eng/actions/runs/42550978237) | Matrix bytes/policy/source-lock; full runtime là bằng chứng local, không phải CI runtime |
| Scan20targets | Execution PASS; security FAIL784occurrences | [Exact IDs và findings](../testing/t014-r3-security.json);7final images/runners247occurrences |
| Full scan/tests mới trong lượt này | NOT_RUN | Không thay implementation/image; dùng bằng chứng cũ kèm identity verification |
| Restore fixture DB17.6/8.4.7, core3.4 runtime | NOT_RUN | Không được kế thừa thành PASS; không nâng DB/core trong đề xuất |

Hết hạn snapshot hoặc thay code/image/config/trust boundary thì kiểm delta và chạy affected
gates; không dùng label PASS cũ cho artifact mới. Backend ready404 hiện tại là bootstrap;
Phase2 T034 vẫn phải triển khai và kiểm product foundation readiness thật.

## 4. Triage và blocker bắt buộc

**A — LEX-003, Brotli CVE-2026-111497, một context bắt buộc khép.**
Raw Airflow base ID `2568f68b627296ed2d3c0f4e1a0e2f86dc48b870b5ab9cea688244e320daaedb`
có libbrotli1 `1.0.9-2+b6`; bản vá Bookworm là `1.0.9-2+deb12u1` theo
[Debian tracker](https://security-tracker.debian.org/tracker/CVE-2026-111497).
Snapshot [CISA KEV](https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json)
version2026.11.06 khớp CVE này; không suy không có exploit từ việc các CVE khác không khớp.
Đối chiếu chỉ exact CVE IDs, chưa resolve toàn bộ GHSA aliases.

Runtime R3 được kiểm chỉ đọc và có `1.0.9-2+deb12u1`; OS lock cũng pin bản đó.
Tuy nhiên Dockerfile chạy `apt-get update` trước khi cài bản vá, nên chưa đủ bằng chứng
đóng build exposure. Việc đầu tiên sau quyết định là review có mục tiêu đường dùng base.
Nếu không chứng minh kiểm soát đủ, dùng base đã vá có provenance hoặc vá offline từ
artifact có hash **trước network/decode có thể dùng Brotli**, rồi build/test/scan affected
IDs và reviewer ký kết luận. Không cần nâng core3.4 hoặc đổi distro hàng loạt để làm việc này.
Thực hiện remediation này cần lượt triển khai riêng; chưa sửa Dockerfile trong lượt này.

**B — LEX-079, zlib CVE-2023-45853,12contexts đề xuất not-affected.**
Vendor snapshot ghi contrib/minizip không được build từ source zlib Bookworm. Cần reviewer
đối chiếu từng binary/context; không mở rộng kết luận sang bản nhúng. Chưa có reviewer
approval. Setuptools không được tự chuyển sang nhóm B: inventory pip/SBOM chỉ là bằng
chứng bổ sung, vẫn nằm trong nhóm C và giữ finding nguyên trạng.

**C —147nhóm/771contexts xin chấp nhận rủi ro tạm, chưa được duyệt.**
63nhóm có context trên final runtime/runner,84nhóm chỉ có context base/build. Mỗi nhóm
trong JSON có advisory title/impact, package/version, exact image IDs, vendor references,
controls và lý do. Finding base/build vẫn có rủi ro supply-chain; NO_FIX hoặc không có
consumer trong final không tự tạo not-affected. Toàn bộ raw findings và severity được giữ.

Các điều kiện không được miễn trừ bởi D2: image/source mismatch, secret leak, auth/private
route bypass, ghi dữ liệu ngoài ủy quyền, thiếu data-integrity/recovery tests ở phase đang
nghiệm thu, public/untrusted exposure, và LEX-003 chưa khép. Hiện các kiểm tra bootstrap
tương ứng PASS trong phạm vi R3; chưa có bằng chứng nghiệm thu chức năng Phase2 trở đi.
Có dấu hiệu khai thác mới hoặc đường ảnh hưởng thực tế thì thu hồi quyền local và xử lý
finding liên quan trước khi tiếp tục. Không viện dẫn quy định CISA như nghĩa vụ pháp lý
áp dụng cho dự án; KEV là nguồn ưu tiên review kỹ thuật trong chính sách đề xuất này.

## 5. Owner, hạn và hồ sơ quyết định

Risk owner đề xuất: **chủ dự án TrungLQ13**. Remediation owner: maintainer được giao khi
kích hoạt; nếu chưa giao thì chủ dự án chịu trách nhiệm. Reviewer được chủ dự án chỉ định;
AI chuẩn bị bằng chứng không tự ký not-affected/risk acceptance.

Review chậm nhất **2026-11-16**. Hết hiệu lực tại thời điểm sớm hơn giữa
**2026-11-23 23:59:59 UTC+09** và14ngày sau phê duyệt. Nếu duyệt sau ngày review phải
review baseline trước kích hoạt; không tự lùi hạn. LEX-003 phải khép trước kích hoạt,
không được tận dụng hạn14ngày làm thời gian trì hoãn blocker này.

Mỗi quyết định lưu proposal/exception IDs, người duyệt, timestamp, accepted/rejected,
baseline SHA/image IDs, controls được kiểm, reviewer evidence và hạn. Mẫu hồ sơ sau duyệt
là `docs/decisions/t014-local-gate-approval.md` kèm ledger đã ký; chưa tạo hồ sơ giả ở lượt này.
Mọi entry hiện `DRAFT_NOT_APPROVED`, `approved=false`.

Thu hồi ngay khi vượt scope/đổi artifact chưa review, đổi input trust, thêm operator,
phát hiện secret leak/auth bypass/data loss/exploit path, đến hạn hoặc reviewer rút quyết
định. Không tự gia hạn. Quyền local chỉ cho phép tiếp tục dưới controls, không tự cấp quyền
triển khai rộng hoặc sửa/xóa dữ liệu.

## 6. Quy tắc hiện hành và bản sửa dự kiến

[Patch](t014-conditional-local-gate-changes.patch) là diff có thể review/apply-check,
**chưa áp dụng** vào các file canonical.

| Nguồn hiện hành | Điều đang chặn | Đề xuất sau khi được duyệt |
| --- | --- | --- |
| Constitution X, XII, mục Quy trình/cổng chất lượng và Quản trị | Task chỉ hoàn thành khi đủ kiểm chứng; ngoại lệ bắt buộc phải được chủ dự án duyệt | Thêm quyền phát triển local có hạn, tách khỏi hoàn thành task/nghiệm thu sản phẩm; đề xuất MINOR1.1.0→1.2.0 vì thêm cơ chế có điều kiện, giữ nghĩa vụ hoàn thành đầy đủ |
| Spec NFR-003/NFR-010, FR-081/085, SC-001/003 và phạm vi local | Không có cơ chế gate conditional; không cho bỏ an toàn hoặc giả workflow mẫu đạt | Bổ sung mốc demo local, giữ nguyên mọi FR/NFR/SC, tám hướng ETL và BR-08 |
| Plan mục các phase; các ghi chú T014 BLOCKED | Phase2 phụ thuộc Phase1, chưa có nhánh đủ điều kiện local | Cho bắt đầu Phase2 theo quyền local đã ký/còn hạn; gate chức năng T034/T046/... giữ nguyên |
| Tasks Phase2 và T015/T016 phụ thuộc T014 | “Điều kiện bắt đầu: T014 đạt” | “T014 đạt đầy đủ HOẶC hồ sơ local hợp lệ và tất cả điều kiện kích hoạt đã khép”; T014 giữ `[ ]` khi full security chưa đạt |
| Remediation P1–P7 §6, A/B, R3 | Mọi HIGH/CRITICAL phải sửa hoặc reviewed not-affected, không có risk acceptance | Chỉ quyết định local được duyệt mới bổ sung nhánh C có hạn; giữ các báo cáo cũ như lịch sử, không sửa kết quả scan |
| Research/Quickstart/README | Chưa mô tả điều kiện tiếp tục và phạm vi ngoại lệ | Thêm nhãn/cách kiểm hạn, môi trường test riêng và đường trở lại gate đầy đủ |

Patch còn đề xuất sửa hai sai lệch hướng dẫn đã thấy: T046 dùng `npx` trong runner đã bỏ
global npm/npx; T138 còn ghi Playwright1.56.1 dù baseline hiện1.65.0. Chỉ sửa hướng dẫn
theo runner hiện có sau duyệt; không triển khai Phase8 hoặc đổi version trong lượt này.

Trạng thái dự kiến sau kích hoạt: `bootstrap=PASS`, `security=FAIL_WITH_APPROVED_LOCAL_EXCEPTIONS`,
`T014_FULL=BLOCKED`, `PHASE2_LOCAL_ELIGIBILITY=AUTHORIZED_UNTIL_<deadline>`.
Nếu chưa đủ D1–D3/LEX-003/controls thì `PHASE2_LOCAL_ELIGIBILITY=BLOCKED`.
Không đổi tên thành security PASS, không ghi Phase1 hoàn thành vô điều kiện.

## 7. Đường ngắn nhất đến luồng dùng thật sau duyệt

Theo dependencies hiện tại, một luồng Airflow dùng qua UI tới T120 cần chuỗi T015–T120;
xem trạng thái/lỗi trong app tới T127. Không hứa chỉ một lượt hoặc vài ngày cho hơn100tasks.
Nhận sản phẩm tăng dần: Connections dùng được tại T046; tạo bảng thật tại T060;
engine thật tại T094; Airflow/UI tại T120; Monitoring tại T127.

| Mốc | Task/gate bắt buộc | Kết quả chạy thật và bằng chứng |
| --- | --- | --- |
| M0 — kích hoạt quyền local | D1/D2/D3, khép LEX-003, scope/identity/hạn/controls | Hồ sơ duyệt có chữ ký/timestamp; affected scans/tests nếu có remediation; không có source/image mismatch |
| M1 — foundation | T015/T016 viết test trước; T017–T034 theo dependency | App schema riêng, migrations/seed idempotent, constraints, encrypted-secret boundary, durable Operation và foundation readiness; DB thật, restart/recovery không replay |
| M2 — Connections | T035–T046, sau T034 | UI tạo/test PG và MySQL; failure/timeout, write-only secret, revision/dependency; E2E và báo cáo query/log đã redacted |
| M3 — Excel tạo table | T047–T060, sau T046 | Tải template→upload→validate→preview→confirm→DDL thật; so type/PK/rows hai DB; invalid/existing không ALTER/DROP; partial DDL phản ánh đúng |
| M4 — engine | T061–T095, sau T060 | Một route PG→MySQL có kết quả sớm nhưng chưa đóng phase; trước M5 vẫn phải đủ8routes/3policies, retry/rerun/native locks/BR-08, disk staging, stress/quota và recovery theo T094/T095 |
| M5 — Airflow xuyên suốt | T096–T120, sau T095 | Excel ETL→preview→quyền→deploy→parse/register đúng revision→run/task thật→đối soát target; T118/T119/T120, không manual SQL/Python thay workflow |
| M6 — xem trạng thái/lỗi | T121–T127, sau T120 | Monitoring UI lấy Airflow Public API; run/task/logs thật, safe errors, dependency down không success giả; không cần Dashboard polish để demo |

Task đầu tiên sau M0 là **T015 và T016**; có thể làm song song theo `[P]` vì file riêng,
không làm model/endpoint trước các tests tương ứng. Không tạo harness/runner thứ hai.
UI shell/test profile hiện có được mở rộng theo module; UI và API errors vẫn tiếng Anh.

Hoãn polish/hiệu ứng và Dashboard/Settings/full stabilization sau mốc demo; các task đó
vẫn là việc chưa hoàn thành của MVP. Không bỏ functional/security/data-integrity tests
để chuyển phase, không tự tách một route thành gate Phase5 đạt, không đổi8phases.

## 8. Lệnh kiểm chứng dự kiến cho từng mốc

**Các test files M1–M6 chưa được triển khai: mọi lệnh dưới đây là kế hoạch, NOT_RUN.**
Fixture/env wiring phải hoàn tất theo tasks; không mock hoặc mount engine socket để
chạy tests trong runner. Fault tests engine/provider vẫn chạy host khi cần theo baseline.

Môi trường local mới dự kiến (chưa khởi chạy):

```powershell
$env:PODMAN_COMPOSE_PROVIDER=(Resolve-Path .tools/docker-compose-5.6.0.exe).Path
$env:COMPOSE_PROJECT_NAME='aat-local-preview-20261109'
$env:AAT_COMPOSE_PROJECT=$env:COMPOSE_PROJECT_NAME
$env:AAT_FRONTEND_PORT='33000'
$env:AAT_BACKEND_PORT='38000'
$env:AAT_AIRFLOW_PORT='38080'
$env:AAT_AIRFLOW_URL='http://127.0.0.1:38080'
$env:COMPOSE_PARALLEL_LIMIT='1'
podman compose up --build -d
podman compose --profile test build backend-tests e2e-tests
```

Đúng ports/namespace phải được xác minh rảnh trước khi dùng. Rebuild runner khi test/dependency
đổi; scan lại affected final/build IDs và kiểm ngoại lệ khi image ID thay, không kế thừa
blanket approval của baseline R3 cho image mới. Đổi code nghiệp vụ nhưng dependency không
đổi có thể review mapping finding/package→ID mới; owner phải ký delta trước mốc tiếp theo.

| Mốc | Lệnh selector dự kiến sau implementation |
| --- | --- |
| M0 | `git apply --check docs/proposals/t014-conditional-local-gate-changes.patch`; `podman exec aat-phase1-t014-r3-20261109-airflow-scheduler-1 dpkg-query -W libbrotli1` để đối chiếu inventory. Các lệnh này không thay quyết định/review LEX-003; nếu có candidate mới phải build/scan đúng ID và kiểm đường patch-before-network trước khi reviewer khép |
| M1 | `podman compose --profile test run --rm --no-deps backend-tests python -m pytest tests/api/test_openapi_contract.py tests/integration/test_metadata_foundation.py tests/unit/test_authorization_states.py tests/integration/test_authorization_repository.py tests/integration/test_foundation_ready.py -v` |
| M2 | `podman compose --profile test run --rm --no-deps backend-tests python -m pytest tests/api/test_connections.py tests/integration/test_connections.py tests/unit/test_secret_codec.py -v` rồi E2E `connections.spec.ts` |
| M3 | `podman compose --profile test run --rm --no-deps backend-tests python -m pytest tests/api/test_tables.py tests/unit/test_table_workbook.py tests/integration/test_table_ddl.py -v` rồi E2E `tables.spec.ts` |
| M4 | `podman compose --profile test run --rm --no-deps backend-tests python -m pytest tests/api/test_files.py tests/unit/test_delimited_reader.py tests/integration/test_file_sources.py tests/unit/test_mapping.py tests/etl tests/stress/test_disk_staging.py -v` và E2E `files.spec.ts` |
| M5 | `podman compose --profile test run --rm --no-deps backend-tests python -m pytest tests/airflow/test_api_contract.py tests/airflow/test_registration.py tests/airflow/test_execution.py tests/airflow/test_revision_lifecycle.py tests/airflow/test_authorization_lifecycle.py tests/api/test_dag_builder.py tests/api/test_authorizations.py -v` rồi E2E `dag_builder.spec.ts` |
| M6 | `podman compose --profile test run --rm --no-deps backend-tests python -m pytest tests/api/test_monitoring.py tests/airflow/test_control.py -v` rồi E2E `monitoring.spec.ts` |

E2E dùng cùng runner/browser, thay tên spec cho từng mốc:

```powershell
podman compose --profile test run --rm --no-deps e2e-tests node node_modules/@playwright/test/cli.js test connections.spec.ts
```

Selectors trên là minimum smoke của mốc; toàn bộ tests mà tasks tương ứng yêu cầu vẫn
phải PASS. Mỗi mốc lưu SHA/locks/image IDs/env/commands, input checksums/expected-vs-actual,
rows/keys/NULL/decimal, operation/run/task identities, redacted logs và PASS/FAIL/NOT_RUN.
Test thiếu hoặc selector không collect là NOT_RUN/FAIL, không coi là mốc hoàn thành.

## 9. Trước khi dùng dữ liệu quan trọng hoặc triển khai rộng

Quyền local tự hết phạm vi trước các hoạt động này. Phải có đánh giá threat model/auth/network
và backup/restore/key recovery cho môi trường mới. Public nằm ngoài phạm vi Spec hiện tại,
nên cần đặc tả/thiết kế được duyệt riêng. Phải đóng hoặc phê duyệt lại mọi rủi ro theo
chính sách phù hợp, scan đúng deployment IDs và kiểm toàn bộ gate chức năng/performance/
security/recovery/CI của phạm vi công bố. Hoàn thành các task/gate còn lại tới T152 khi
tuyên bố toàn bộ MVP; không dùng demo một bảng làm bằng chứng8routes hay tất cả US đạt.

## 10. Trình tự áp dụng sau quyết định

Ghi quyết định và reviewer → khép LEX-003/D3 → cập nhật patch theo ngày/người duyệt thực tế
→ đồng bộ canonical docs, chạy Analyze nhất quán → kiểm identity/controls/hạn → kích hoạt
quyền local → T015/T016. Phiên bản1.2.0/ngày sửa trong patch là đề xuất, phải xác nhận theo
ngày phê duyệt thực tế. Trước chuỗi này mọi trạng thái đầy đủ vẫn BLOCKED như báo cáo R3.
