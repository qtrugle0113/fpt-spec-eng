# Báo cáo nghiệm thu baseline local có rủi ro đã biết

## Khép lại review T152 — evidence theo từng điều kiện

Trạng thái mới nhất: **technical evidence PASS; chờ CI cho cập nhật T152**.
Ma trận trước đây gán AH vào memory stress là thiếu sót tham chiếu, đã được lưu
nguyên trạng tại [snapshot trước review](resume-20261114/t152-closure/matrix-before-review.json).
Ma trận hiện hành không suy PASS từ checkbox hoặc một receipt tổng hợp.

- [Ma trận v2](resume-20261114/t152-closure/acceptance-matrix-v2.json):39ca A–AM,
  15success criteria,11user stories và BR-08, mỗi ca có expected/actual,
  điều kiện con, test IDs, receipt/log SHA256 và phạm vi artifact thực tế.
- AH:44test storage/snapshot/quota/recovery PASS; I/O failure, checksum, SIGKILL
  và mất staging sau partial commit có selectors riêng. Load policies/schema/mapping41PASS.
- AJ/timezone:63test API/schema PASS, gồm lost response, pending/expired worker,
  stale revision và UTC/IANA/DST. Native typed DB routes4PASS, concurrency2PASS
  trên candidate hiện hành. Dependency recovery6PASS qua Airflow thật.
- Đổi revision và credential3test PASS trong lượt ghép; dashboard lượt đó FAIL
  vì fixture đã có4DAG nhưng test yêu cầu fresh1DAG. Giữ nguyên FAIL và receipt
  [selected assertions](resume-20261114/t152-closure/revision-credentials-selected-results.json)
  chỉ ghi đúng3test đã PASS. Dashboard chạy riêng sau đó1PASS, không nới assertion.
- Registration/workbook/settings18PASS; blank/partial workbook rows15PASS;
  implicit mapping exact-name/type3PASS. Table UI10PASS, language UI có receipt
  riêng; performance HTTP và security surfaces4PASS trên fixture riêng.
- CaseO/AD và startup/restart AM dùng lại đúng artifacts gốc; physical application
  file equivalence, thay đổi distribution và measurements được giữ trong
  [memory equivalence](resume-20261114/t152-closure/memory-equivalence.json) và
  [T140 equivalence](resume-20261114/accepted-handover/t140-equivalence.json).
  Không gán image mới cho execution cũ hoặc nói đã chạy lại các lượt này.
- [Live rollout](resume-20261114/t152-closure/live-demo-rollout.json):8services healthy,
  Airflow đúng image a9dc2f03… được duyệt, loopback, volumes/config giữ nguyên.
  [Read-only target verification](resume-20261114/t152-closure/live-target-verification.json)
  xác nhận hai workflow cũ và giá trị đích nguyên vẹn. App23000/Airflow28080 READY.
- CI bổ sung7negative/positive tests cho evidence validator và kiểm ma trận thật:
  thiếu AH conditions, test ID không nằm trong log PASS, checksum đổi hoặc thiếu
  SC đều bị từ chối. Scope risk acceptance và thời hạn không thay đổi.

## Snapshot bàn giao62003a2 trước khi sửa mapping T152

Các thông tin phía dưới giữ để truy vết; dòng “demo chưa rollout” là lịch sử.

**Trạng thái mới nhất: T152 đang tái kiểm chứng** sau review evidence mapping.
Các kết luận hoàn tất bên dưới là snapshot62003a2; kết luận mới sẽ dựa trên
selector/test-ID và expected/actual của từng ca bắt buộc. T014 vẫn PASS theo
phạm vi rủi ro đã được chủ dự án chấp thuận.

Trạng thái hiện hành: **PASS — nghiệm thu baseline local có rủi ro đã biết;152/152task**.
Constitution2.0.0 được chủ dự án phê duyệt trong hội thoại ngày2026-11-14.
Security disposition: `OWNER_ACCEPTED_KNOWN_RISKS`; scan vẫn có1.669 HIGH/CRITICAL
occurrences/363nhóm trên21targets. Không phải security-clean hoặc production-ready.

T014_FULL=PASS, T152=PASS. [CI quản trị](resume-20261114/accepted-handover/ci-governance.json)
PASS Windows/Linux; CI của commit bàn giao cuối được xác minh sau push.

## Phạm vi, thời hạn và bằng chứng

- Một operator, loopback, dữ liệu tổng hợp. Review2026-11-16, hạn2026-11-23T00:00:00+09:00.
  Không tự gia hạn; thay artifact/finding, thu hồi hoặc đến hạn review thì gate dừng.
- [Decision và hash snapshot](../decisions/t014-owner-review-20261114.json),
  [images](resume-20261114/accepted-handover/images.json),
  [ma trận39ca A–AM](resume-20261114/accepted-handover/acceptance-matrix.json).
- Unit/API231unique đã được kiểm chứng sau sửa fixture:229PASS lượt đầu,
  hai lỗi stale build inputs được khép bằng nhóm8test rerun PASS. Lượt FAIL giữ
  nguyên; không cộng test trùng thành test mới.
  [Resolution](resume-20261114/accepted-handover/unit-api-resolution.json).
- SDK factory4PASS; compatibility5PASS (pip/dependencies/SDK/constraints provenance,
  locked bases và actual browser); approval guard6PASS, CI kiểm raw evidence checkout thật.
- Full workflow6browser checks desktop/mobile PASS và exact target verifier PASS,
  cleanup0 trên candidate Airflow a9dc2f03… đã duyệt; không dùng source overlay.
- T140 full restart/persistence/fail-closed giữ bằng chứng image gốc. Application
  files giống candidate; chỉ dnspython2.9.0→2.9.2 đổi trong runtime distributions,
  đã được DNS bound test, SDK,10Airflow routes và fresh UI workflow kiểm chứng.
  [Equivalence](resume-20261114/accepted-handover/t140-equivalence.json).
- App <http://localhost:23000>, Airflow <http://localhost:28080>. Demo cũ được giữ;
  candidate bàn giao chưa tự thay vào demo. Artifact IDs của từng lượt ghi trong receipt.
- Checkout bàn giao riêng: `.tools/accepted-handover-7273297`. Các thử nghiệm Trixie
  và sửa helpers chưa commit ở workspace gốc được bảo toàn, không nằm trong baseline này.

## Lịch sử trước khi phê duyệt Constitution2.0.0

Các kết luận BLOCKED dưới đây phản ánh trạng thái trước quyết định mới, không
ghi đè trạng thái hiện hành bên trên và không bị xóa khỏi evidence.

# Báo cáo nghiệm thu Airflow Automation Tool

**Trạng thái: BLOCKED — chưa nghiệm thu toàn bộ sản phẩm.**

**Sau quyền commit/push mới:** CI Windows/Linux đã PASS trên commit2585bc0 và
021a21d. Đã vá dnspython2.9.2 trên candidate, đưa OS fixes lên build stage và
scan lại hai target; full security vẫn BLOCKED. Các ghi chú cấm push/CI NOT_RUN
bên dưới là lịch sử. [Remediation hiện hành](resume-20261114/t014-closeout/remediation-report.md).

**Lượt khép T014/T152 tiếp theo:** kiểm source local Windows15/Linux15 PASS trên
snapshot500file; remote CI vẫn NOT_RUN. Đã tổng hợp21rawreports đúng image IDs
thành362nhóm HIGH/CRITICAL,229nhóm không có FixedVersion. Không scan mới hoặc
tự duyệt findings; T014/T152 giữ mở. Xem [hồ sơ khép cổng](resume-20261114/t014-closeout/closeout-report.md).

**Cập nhật14/11/2026:** xem [lượt tiếp tục](continuation-20261114.md).
Đã nâng wheel build, bỏ rsync và kiểm chứng lại; full baseline21targets đã scan
(1.710 HIGH/CRITICAL occurrences), full gate vẫn BLOCKED. Phạm vi10artifacts
local có752occurrences/216nhóm. T140 full selector PASS (cleanup0), T151 đã khép;
hiện150/152tasks, chỉ T014/T152 còn mở.
Các kết quả ngày13/11 bên dưới giữ làm lịch sử, không thay kết luận mới này.

Nguồn hiện tại: commit `82fdec47568db6d2ea9cb95d822f8c13daf187c0` và bản sửa
fixture T140 chưa commit. Không commit/push, không thay Constitution, security
policy hoặc checklist reviewer.

## Kết quả lượt triển khai ngày 13/11/2026

| Hạng mục | Kết quả và bằng chứng |
| --- | --- |
| SpecKit | Đã áp dụng `speckit-analyze` và `speckit-implement`; prerequisites PASS; không extension hook. [Phân tích](resume-20261113/autonomous-82fdec4/specification-analysis.md). |
| Task inventory | 152 ID, 148 checkbox đã đánh dấu; còn T014/T140/T151/T152, không thiếu/trùng ID hoặc vòng lặp dependency. [Audit](resume-20261113/autonomous-82fdec4/task-audit.json). |
| T040 | Đã hoàn thành trước lượt này. Chạy lại schema/parser 12 PASS; profile PostgreSQL/MySQL thật 22 PASS trong21.82s, cleanup0, gồm API Connections, duplicate trim/case-insensitive, host/DNS policy và hồi quy fixture T140. [Kết quả](resume-20261113/autonomous-82fdec4/t040-regression/regression-profile-results.json). |
| Kiểm source/sample/pins | 23 checks PASS; kiểm fixture mới cùng sample artifacts4PASS. Không cộng các suite có phần chồng nhau thành số test độc lập. [Static](resume-20261113/autonomous-82fdec4/static-checks.txt), [RED](resume-20261113/autonomous-82fdec4/t140-fixture-red.txt), [GREEN](resume-20261113/autonomous-82fdec4/t140-fixture-green.txt). |
| SDK runtime unit | 9/9 PASS trên installed Airflow/ETL image; test source được chép vào fixture riêng, không network/DB. Lượt RED trước đó có2fixture journal thiếu quyền0600; đã sửa fixture và bổ sung ca âm journal0644 bị chặn. [RED](resume-20261113/autonomous-82fdec4/runtime-sdk-unit-r2/sdk-unit-results.json), [GREEN](resume-20261113/autonomous-82fdec4/runtime-sdk-unit-r3/sdk-unit-results.json). |
| ETL | Engine118PASS113.52s, runtime19PASS110.58s, cả hai cleanup0 trên artifacts hiện tại. [Kết quả](resume-20261113/autonomous-82fdec4/etl-regression/regression-results.json). |
| Unit/API cuối | 225PASS396.49s và SDK factory4PASS trên runner cuối có toàn bộ sửa test. [Kết quả](resume-20261113/autonomous-82fdec4/unit-api-final/regression-results.json). |
| Airflow routes | 8/8PASS165.769s trên installed image, source/target PG/MySQL và CSV/TXT. [Kết quả](resume-20261113/autonomous-82fdec4/airflow-regression-r2/airflow-0/airflow-fixture-results.json). |
| Build | Đã resolve/build đủ10artifacts, sau đó reuse9artifacts và build lại runner chứa các sửa test. [Manifest cuối](resume-20261111/portable-66c48b64/candidate-images.json), [source checksums](resume-20261111/portable-66c48b64/source-sha256.json). |
| Local policy | `LOCAL_POLICY_MATCH`, không unknown HIGH/CRITICAL, không thêm ngoại lệ. [Receipt cuối](resume-20261111/portable-66c48b64/local-policy-review.json). |
| Demo | READY tại localhost23000/Airflow28080, project `aat-portable-demo-516bea17`; 6UI checks và actual target verifier PASS. [Kết quả](resume-20261113/autonomous-82fdec4/demo-workflow/result.json). |
| T014_FULL | `BLOCKED`; local policy match không phải security PASS. [Scan cuối](resume-20261111/portable-66c48b64/candidate-security.json), [triage](resume-20261113/autonomous-82fdec4/security-triage.json). |
| T140 | Root workspace FAIL trước runtime: Compose không stat được `.pytest_cache`. Đang nghiệm thu lại trên checkout sạch cùng commit và các file sửa đã đối chiếu checksum. [Root failure](resume-20261112/aat-t140-19197f2e/result.json), [checkout provenance](resume-20261113/autonomous-82fdec4/clean-worktree.json). |
| T151 | Verification lịch sử PASS, checkbox còn chờ prerequisite T140. |
| T152 | Giữ BLOCKED đến khi dependencies, Analyze và T014_FULL đạt đủ tiêu chí. |

## Môi trường, lệnh và giới hạn

Máy hiện tại dùng Podman client5.8.3/server5.8.9 Linux/amd64, Compose5.6.0.
Không kế thừa compatibility PASS của baseline Podman6.1.1 từ máy trước.
Trong lượt này Windows Update cài WSL3.0.5.0 và dừng machine giữa scan/review.
Đã khởi động lại machine có sẵn và chạy `--review-only` trên scan đã hoàn tất;
không đổi scan bytes hoặc nới policy để bỏ qua lỗi hạ tầng. System event19 của
WindowsUpdateClient lúc23:47:40 UTC+09 ghi cập nhật thành công.

Lượt tiếp tục bắt đầu13/11 và kéo dài sang14/11/2026 UTC+09. So với source snapshot
`portable-a4ec9c82`, có6file runtime thay đổi nội dung và2file chỉ khác line endings;
do đó đã chạy bổ sung ETL, SDK unit và installed Airflow regression thay vì suy
PASS từ checkpoint cũ. [Đối chiếu source](resume-20261113/autonomous-82fdec4/checkpoint-source-comparison.json).

Các lệnh chính đã thực hiện:

```powershell
$env:SPECIFY_FEATURE_DIRECTORY=(Resolve-Path specs/001-airflow-automation-tool).Path
powershell -ExecutionPolicy Bypass -File .specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireSpec -RequireTasks -IncludeTasks
python -X utf8 tests/tools/prepare_local_images.py
python -X utf8 tests/tools/prepare_local_images.py --reuse-candidate docs/testing/resume-20261111/portable-0fb28a4c/candidate-images.json
python -X utf8 tests/tools/scan_portable_images.py --manifest docs/testing/resume-20261111/portable-7d00f390/candidate-images.json --reuse-scan docs/testing/resume-20261111/portable-0fb28a4c/partial/candidate-security.json --cache-volume aat-phase1-scan-c497c1c9-cache
python -X utf8 tests/tools/scan_portable_images.py --manifest docs/testing/resume-20261111/portable-7d00f390/candidate-images.json --review-only
python -X utf8 tests/tools/run_regression.py --group unit-api --preflight-only --evidence-dir docs/testing/resume-20261113/autonomous-82fdec4/runtime-preflight-r2
```

Lệnh profile có đầy đủ immutable IDs tại
[command.json](resume-20261113/autonomous-82fdec4/t040-regression/command.json).
Preflight PASS chỉ kiểm artifact/policy; không thay kết quả test. Runner kiểm
thử dùng image đóng gói, database và volumes disposable, không publish ports,
không dùng application source overlay. Không thay manifest demo hoặc dữ liệu
có trước. Chỉ cleanup namespace do chính lượt kiểm thử tạo.

## Lỗi fixture T140 đã sửa

`csv.reader`/`csv.writer` làm mất provenance dấu nháy quanh NULL token:
`"\N"` là chuỗi literal nhưng đã bị ghi lại thành `\N`, được parser hiểu là NULL.
Fixture mới giữ nguyên bytes các trường còn lại của logical record, gồm Unicode,
dòng trong chuỗi, doubled quotes và NULL; chỉ thay cột ID bằng khóa riêng cho từng
dòng. Test mới tái hiện lỗi trước sửa và PASS sau sửa; samples/templates gốc giữ
nguyên checksum. Đây là sửa kiểm chứng, chưa phải bằng chứng T140 runtime PASS.

Lượt sạch đầu `aat-t140-bf2939bb` đạt READY và6UI checks desktop/mobile, rồi
recovery extraction đã chuyển sang attempt2 và ghi28000dòng đúng batch. Verifier
thất bại vì đòi full80000dòng ngay tại observation trung gian; giữ nguyên
[kết quả FAIL](resume-20261112/aat-t140-bf2939bb/result.json).
Đã sửa observation để chấp nhận **prefix đúng giá trị và đúng ranh giới batch**;
guard cuối vẫn bắt buộc đủ80000dòng, task success, COMMIT_VERIFIED và đúng toàn bộ
giá trị/checksum. COMMIT/FULL_REFRESH khi đang giữ row lock vẫn phải giữ đích cũ.
Hai unit tests bổ sung kiểm cả prefix hợp lệ, prefix sai/incomplete batch và đích
thay đổi trái phép. Lượt chạy lại dùng đúng canonical IDs đã được scan/review,
không miễn scan hoặc lấy lỗi verifier làm bằng chứng acceptance PASS.

## Security và quyết định cần thiết trước full acceptance

Scan local cuối đủ10artifacts có752 HIGH/CRITICAL occurrences (gồm lặp qua build/runtime
targets), gộp216nhóm advisory/package/version/severity. Chỉ còn1nhóm ghi FixedVersion
(setuptools70.3.0 được phân tích từ SBOM); 215nhóm không có FixedVersion. Đây là số findings
của scanner, không phải kết luận tất cả đều exploitable; receipt có cả đối chiếu
policy và bằng chứng binary cho context not-affected đã duyệt.

Các finding local khớp policy đã duyệt, nhưng hồ sơ này không cấp full
security acceptance. [Scan cuối21targets](resume-20261114/full-baseline-final/candidate-security.json)
có1710occurrences và review BLOCKED; raw reports khớp đúng IDs đã được lưu cùng report.
Muốn đóng T014 cần remediation hoặc review not-affected có
bằng chứng và thẩm quyền, đủ scope scan/base/build/final, cùng CI/checkout theo
tiêu chí task. Không tự gia hạn hoặc chuyển local exception thành full PASS.
Reviewer/chủ dự án cần xem
[security-triage.json](resume-20261114/security-triage.json)
và receipt/scan liên kết, xác định từng context đã khép được hay còn chặn. CI của
bản sửa chưa commit trong lượt này là NOT_RUN, không được suy từ CI lịch sử.

## Truy vết nghiệm thu

Checkpoint chức năng lịch sử hiện hành:
[13/11](product-resume-20261113.md), [12/11](product-resume-20261112.md),
[Phase8](phase8-regression-report.md), [Phase5](phase5-engine-report.md),
[Phase6](phase6-dag-builder-report.md).
Evidence lịch sử thuộc artifact/môi trường được ghi trong từng report, không tự
trở thành kiểm chứng trên image IDs của lượt này. Bảng dưới là chỉ mục truy vết;
checkbox task và kết quả trong report gốc vẫn quyết định mức nghiệm thu. Riêng
T152 và full security còn mở; chưa có kết luận PASS tổng thể cho A–AM.

| Ca | Phạm vi | Task/evidence liên quan |
| --- | --- | --- |
| A–B | Table Excel → PostgreSQL/MySQL | T060/T141, phase4 và full workflow trong Phase8 |
| C–F | Bốn hướng DB → DB | T142, `resume-20261111/t142-cross-database/` |
| G–H, U | Bốn hướng CSV/TXT → DB | T143, `resume-20261112/t143-airflow/` |
| I | Mapping cột khác tên | T094/T142, phase5 engine và cross-database |
| J–K | UPSERT lặp và APPEND | T094/T144, phase5 engine và retry recovery |
| L–M | FULL_REFRESH success/failure | T094/T145, `resume-20261112/retry-refresh-airflow/` |
| N | Cron/timezone/history | T119/T146, `resume-20261112/scheduled-airflow/` |
| O | Dataset vượt RAM, staging trên đĩa | T147, `resume-20261113/airflow-memory-large-r5/` và `airflow-memory-guards/` |
| P | Workbook lỗi và vị trí lỗi | T060/T120, table và DAG Builder reports |
| Q | Connection fail/timeout, bảo vệ secret | T036/T040/T046; profile Connections 22 PASS lượt hiện tại |
| R | Source/target failure, partial/retry | T144, `resume-20261113/dependency-recovery-airflow/`; report phân biệt session loss với service stop/start |
| S | Dashboard thật/completeness | T132/T149, `resume-20261113/dashboard-truth-airflow/` |
| T | Open in Airflow | T141, Phase8 full UI workflow |
| V | Disk full/interrupt/concurrency | T095/T144/T146/T147, engine/recovery/concurrency evidence |
| W | Parse/timeout/revision/external conflict | T118–T120, Phase6 DAG Builder report |
| X | Retention/restart/settings/dependency | T069/T137/T140; T140 full selector PASS/cleanup0 |
| Y | Injection/macro/path/secret | T148, `resume-20261113/security-surfaces/` |
| Z | Ngôn ngữ/khả dụng/unavailable states | T137/T148/T149, `resume-20261113/language-e2e/` và response-limits evidence |
| AA | Snapshot khi source thay đổi | T095/T142, engine snapshot và database routes |
| AB | UPSERT thiếu hoặc mất key | T094/T142, schema preflight và cross-database |
| AC | FULL_REFRESH extraction fail/DDL boundary | T094/T145, engine và replacement boundaries |
| AD | Chunk/batch/byte cap | T095/T147, engine/stress và Airflow memory evidence |
| AE | Unicode/NULL/decimal/temporal | T142/T143; fixture T140 mới có hồi quy literal NULL |
| AF | Header/delimiter/quote/schema drift | T069/T139/T143, parser history và file routes |
| AG | Row reconciliation theo strategy | T142/T143/T145, exact target verification |
| AH | I/O/checksum/kill không cleanup | T095/T144/T147, storage/recovery/protected artifacts |
| AI | Hai alias cùng physical target | T146, `resume-20261113/current-t146-confirmation/` |
| AJ | API timeout/pending/stale revision | T118/T119/T145, lifecycle và admission boundaries |
| AK | Manual/scheduled/revision/credentials | T119/T145/T146, concurrency và revision lifecycle |
| AL | Workbook version/duplicate/orphan/implicit map | T060/T120, table/DAG workbook acceptance |
| AM | Fresh boot, phase restart, secret/volume loss | T140 full selector PASS tại `resume-20261112/aat-t140-045d42c5/` |

| Tiêu chí | Task và phạm vi đối chiếu |
| --- | --- |
| SC-001 | T140; fresh startup, READY, persistence và phase restart |
| SC-002 | T141; thao tác UI từ sample đến table/deployment |
| SC-003 | T142/T143; tám hướng ETL và exact target values |
| SC-004 | T060/T120; workbook lỗi, vị trí và không side effect |
| SC-005 | T094/T144; UPSERT/APPEND và retry identity |
| SC-006 | T145; FULL_REFRESH và quyền replacement |
| SC-007 | T095/T147; dữ liệu lớn, RAM, disk staging |
| SC-008 | T132/T149; Dashboard/status/completeness |
| SC-009 | T118–T120/T141–T143; registration/revision và executions thật |
| SC-010 | T149; response measurements và timeout |
| SC-011 | T046/T148; secret surfaces và input nguy hiểm |
| SC-012 | T152; tất cả mandatory cases/gates — đang BLOCKED |
| SC-013 | T095/T142/T145; consistent snapshot và extraction failure |
| SC-014 | T119/T144–T146; uncertainty/ownership/concurrency |
| SC-015 | T142/T143; type/NULL round-trip và conversion errors |

| Story/quy tắc | Task và nguồn evidence |
| --- | --- |
| US-01 | T013/T140; startup và durability, T140 PASS |
| US-02 | T035–T046; Connections report và profile mới trong lượt này |
| US-03 | T061–T069/T139/T143; file source/parser/history |
| US-04 | T047–T060/T141/T151; Table Management; sample pack và prerequisite T140 đã PASS |
| US-05 | T096–T120/T141; Excel ETL → deploy/register/activate |
| US-06 | T070–T095/T142; DB routes, staging/mapping |
| US-07 | T061–T095/T143; file routes |
| US-08 | T083–T094/T144–T146; load policies/recovery |
| US-09 | T121–T127/T139/T141; Monitoring và Airflow navigation |
| US-10 | T128–T132/T149; Dashboard |
| US-11 | T133–T137/T148; Settings/UX/language |
| BR-08 | T110/T119/T139/T145; ONCE/SCHEDULED, allow_empty, admission/revoke và commit reconciliation |
