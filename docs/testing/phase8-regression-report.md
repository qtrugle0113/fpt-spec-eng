# Phase8 — regression và ổn định

## Kết quả hiện hành

T138 hoàn thành trong phạm vi local có ngoại lệ được duyệt; tổng hợp 13 selectors
PASS tại [aggregate](resume-20261111/t138-aggregate.json). Không tương đương
nghiệm thu security toàn bộ: T014_FULL tiếp tục BLOCKED.

T141 PASS: [acceptance](resume-20261111/t141-explicit-conversions/acceptance.json),
6 checks gồm 2 luồng UI đầy đủ desktop/mobile, Airflow thật và đọc lại dữ liệu
đích đúng 4 dòng mỗi luồng. T142 PASS 4 ca/82.579s tại
`resume-20261111/t142-cross-database/`; PK ghép, decimal, NULL và temporal đã
đối chiếu trên cả hai database thật; cleanup 0.

T143 lượt đầu FAIL: 7 ca/115.847s, 4 PASS/3 FAIL tại
`resume-20261111/t143-file-database/`. CSV→PG/MySQL, invalid format và invalid
typed row giữ dữ liệu FULL_REFRESH cũ PASS. TXT headerless→PG/MySQL FAIL trong
SDK; missing file trước trigger trả HTTP500. Không coi đây là PASS, không
đánh dấu T143. Đang chạy selector TXT riêng để xác định nguyên nhân.
T139/T140/T144–T152 còn mở. Các mô tả pending T138 bên dưới giữ lịch sử.

Sửa lỗi dự kiến trong phạm vi T143: khi nội dung file biến mất/không đọc được
trong compile preview, trả lỗi nghiệp vụ `FILE_SOURCE_UNAVAILABLE` HTTP409 và
hướng dẫn upload/validate lại, không lộ storage path. Không tạo trigger intent
hoặc tiêu thụ ONCE authorization khi kiểm tra nguồn chưa đạt. Đây là thực thi
guard hiện hữu, không thay policy parser, type conversion hoặc dependency locks.
Artifact có thay đổi phải build/scan lại trước khi nghiệm thu installed image.

Đã build bản sửa backend `8204b16f...`, scan 4 artifact mới và reuse scan 6
artifact exact ID; receipt `resume-20261111/portable-0d406416/` đạt
LOCAL_POLICY_MATCH, security vẫn FAIL_WITH_APPROVED_LOCAL_EXCEPTIONS.
`backend-guard-package.json` xác nhận SHA source bằng module installed trong
site-packages. TXT→PG chạy riêng PASS 1 ca/42.078s, cleanup 0 tại
`t143-txt-diagnostic/`; chưa kết luận hai lỗi TXT lượt đầu là parser bug.
T143 đầy đủ sau sửa tại `t143-guard-rerun/`: 5 PASS/2 FAIL, 119.518s, cleanup
10 mã 0. Guard missing-file PASS, xác nhận target cũ giữ nguyên, 0 intent và
ONCE vẫn GRANTED. Hai ca TXT vẫn FAIL theo chuỗi; task tiếp tục mở. Chẩn đoán
terminal failure→TXT ở `t143-terminal-sequence-diagnostic/` chỉ ghi tọa độ stack
của exception trong private fixture, không tính là installed-image acceptance.

## Nghiệm thu bản sửa missing-file trên installed image

`resume-20261111/installed-missing-source-guard/`: PASS, backend `8204b16f...`,
không source overlay; 6 browser checks trong 1.9 phút. Hai workflow UI thật
desktop/mobile hoàn tất trong 54.588/52.118 giây, mỗi workflow đối chiếu đúng
4 dòng đích và Airflow success/COMMIT_VERIFIED. Với từng file của fixture:
preview409, trigger409, mã FILE_SOURCE_UNAVAILABLE, không lộ storage path,
không tạo intent; khôi phục cùng bytes/quyền file thì preview200. Đọc lại đích
sau khôi phục vẫn đúng toàn bộ giá trị. Verifier hash được ghi trong result;
`missing_source_exit_code=0`, `actual_execution_exit_code=0`, cleanup0.

Chẩn đoán terminal failure→TXT đạt 2 ca PASS/81.691s, cleanup0; không tái hiện
lỗi chỉ với tiền đề này. Lượt instrumented toàn chuỗi đang chạy ở
`t143-full-sequence-diagnostic/`, chưa được tính PASS hay thay nghiệm thu T143.

Lượt chẩn đoán toàn chuỗi kết thúc 5 PASS/2 FAIL/160.323s. Stack private chỉ ra
QuotaExceeded tại `QuotaManager.reserve`, không phải parser. FULL_REFRESH typed
failure để lại raw COMPLETE và mapped INCOMPLETE, đúng guard nên không được xóa
mù quáng; mapped reservation xin toàn bộ phần còn lại gần10GiB khiến run sau
xin10GiB vượt global20GiB kể cả dữ liệu thật rất nhỏ. Phương án sửa: dùng chặn
trên số dòng đã biết × giới hạn serialized row + giới hạn manifest cho mapped
reservation, vẫn cap theo quota run còn lại. Không nâng quota, không xóa staging,
không miễn reconciliation hoặc tự giải phóng ONCE. Plan đã ghi thiết kế này.

## Tiến độ sau startup và kiểm thử thực tế

Native PowerShell `scripts/start-local.ps1` đã tạo project mới
`aat-portable-demo-dcae6f3c`: <http://localhost:23000>, Airflow28080, API28000.
Init exit0, tất cả service healthy, readiness200. Không source overlay; không
đụng demo13000/volumes có trước. Browser readonly12checks PASS trên6routes,
desktop1440/mobile390, screenshots tại `resume-20261111/portable-demo-smoke/`.
Hướng dẫn khởi động/resume tại [local portable](../operations/local-portable.md).

`portable-approved-regression`: unit/API214PASS231.51s, SDK4PASS,
integration54PASS55.96s, ETL engine118PASS79.67s. Lượt runtime đầu giữ FAIL:
18PASS/1FAIL118.18s; test heartbeat giả định2.2s nhưng dispatch renew5s.
Test nay polling tối đa10s, dưới readiness20s, kiểm timestamp DB, file, cùng
PID/owner và worker còn sống. Không đổi code worker hoặc nới readiness/lease.
`portable-runtime-rerun`:19PASS232.03s, cleanup0 trên runner mới65a464f1...
đã scan; `portable-ce69c81e/local-policy-review.json` LOCAL_POLICY_MATCH.

`portable-airflow`:8SDK routes PASS315.570s trên installed engine/metadata
wheels, count/NULL/disk manifest thật; cleanup10codes đều0. Các application
image IDs giữ nguyên giữa các nhóm; chỉ runner mới do sửa test được rebuild.
`portable-e2e`: Connections6PASS32.4s/cleanup0, các suite còn lại đang chạy.
`portable-stress` đang chạy dataset270000rows; chưa ghi PASS khi chưa có exit0.

Đã bổ sung cleanup result/exit-code gate cho metadata/Airflow drivers để không
trả PASS khi cleanup thất bại. Guard metadata đang kiểm bằng fixture thật riêng
`portable-harness-cleanup`; không dùng source fixture làm installed app acceptance.
Các log mới được giữ trong Git sau redaction để lưu cả failure/rerun.

## Sau phê duyệt Kerberos của chủ dự án

Chủ dự án trả lời rõ “Duyệt đúng phạm vi local nêu trên” cho đúng đề xuất
14advisory/306contexts. Hồ sơ mới tại
`docs/decisions/portable-local-finding-approvals.json`, gắn SHA256 đề xuất, giữ hạn
23/11/review16/11 và controls. Không sửa approval cũ hoặc tự duyệt findings khác.
Review lại scan `portable-af8d7ed2` trả LOCAL_POLICY_MATCH, không rescan artifact
không đổi. Security vẫn FAIL_WITH_APPROVED_LOCAL_EXCEPTIONS/T014_FULL BLOCKED.

Đang chạy `python -X utf8 tests/tools/run_regression.py --group all --evidence-dir
docs/testing/resume-20261111/portable-approved-regression`. Chỉ kết quả selector
exit0/cleanup thành công được tính PASS. Các mô tả chờ quyết định phía dưới là
lịch sử trước phê duyệt này.

## Hiện hành sau quyết định portable2026-11-11

Chủ dự án trực tiếp duyệt quy trình build source/locks/config trên mỗi máy;
Constitution1.3.0, Spec/Plan/Tasks/Quickstart đã đồng bộ trước implementation.
[Quyết định](../decisions/portable-local-build-20261111.md) giữ nguyên các approval
cũ, hạn và controls; không yêu cầu registry/archive hoặc cùng IDs giữa các máy.

`prepare_local_images.py` resolve Dockerfiles từ Compose, đóng băng context sạch,
build tags riêng, đối chiếu inputs trước reuse, ghi source hashes/revision/dirty
state/engine/provider/commands/IDs. Sửa hai đường dẫn Dockerfile không tồn tại
của regression PostgreSQL/MySQL sang gosu stages có thật. `.tools/local-images.json`
là manifest mỗi máy; manifest trong tests/fixtures giữ evidence lịch sử.

`scan_portable_images.py` scan artifact hiện tại, đối chiếu từng target/advisory/
package/installed-version/severity với policy có provenance. Scan cũ chỉ được
tái sử dụng cho đúng cùng artifact ID trong24giờ, xác minh receipt hash; không
chuyển security PASS sang artifact mới. Binary zlib phải khớp bằng chứng
not-affected cùng target/package/version. Unknown findings giữ BLOCKED.

Hash báo cáo lịch sử ban đầu không khớp raw LF. Đã xác định chính xác CRLF gốc
khớp hash trong approval; verifier chỉ thử raw/LF/CRLF, không reserialize JSON
hoặc bỏ qua khác biệt nội dung. Negative unit test chứng minh đổi giá trị vẫn
bị từ chối. Không coi báo cáo bị sửa nội dung là approval hợp lệ.

Các lượt mới:

| Evidence | Kết quả |
| --- | --- |
| portable-721c39e2 | FAIL trước build do provider kế thừa là podman-compose không hỗ trợ config JSON; đã chọn provider5.6.0 đúng baseline. |
| portable-5527612b |10artifact build/reuse PASS; fresh scan10artifact PASS về execution; policy BLOCKED do contexts mới. |
| portable-5788217d |9artifact reuse, runner mới build PASS; chỉ scan runner ID mới, reuse9scan rows cùng IDs theo receipt; policy BLOCKED. |
| portable-af8d7ed2 |10artifact đã resolve; frontend và runner mới build PASS, frontend-build cache giữ ID; scan2artifact mới và reuse8cùngIDs. Frontend0findings sau vá libxslt1.1.43-r3→r4. |
| portable-af8d7ed2/packaged-source.json |PASS91API/45engine/26metadata modules, không start runtime candidate. |
| portable-policy-gate |Preflight thực BLOCKED tại local-policy review trước tạo fixture; không còn lỗi thiếu image IDs. |
| unittest tests.unit.test_portable_policy tests.unit.test_regression_preflight |8PASS0.111s trên Python3.13.15 host; kiểm logic policy/preflight, không thay DB/Airflow acceptance. |

Scan mới phát hiện14advisory Kerberos trên9packages1.20.1-2+deb12u5,
306occurrences ở6target, ngoài phạm vi các ngoại lệ hiện hành. Scanner không
ghi FixedVersion cho các contexts này; không suy vendor not-affected hoặc chấp
nhận rủi ro ngầm. [JSON đề xuất](../proposals/portable-local-krb5-20261111.json)
và [phạm vi quyết định](../proposals/portable-local-krb5-20261111.md) đã chuẩn bị;
câu hỏi chủ dự án còn chờ trả lời. Không tạo approval mới khi chưa được duyệt.

T138 vẫn `[ ]`, T139–T152 chưa mở. Integration/ETL/Airflow/E2E/stress trên bộ
artifact mới và one-command startup: NOT_RUN vì policy gate. Không có URL sản
phẩm mới đang chạy; không sửa/xóa dữ liệu/volumes có trước, không commit/push.
T014_FULL vẫn BLOCKED. Không còn driver/build/test chạy nền khi kết thúc lượt.

Để tiếp tục sau quyết định: ghi nhận đúng đề xuất/hash/phạm vi nếu chủ dự án
duyệt; dùng `scan_portable_images.py --manifest
docs/testing/resume-20261111/portable-af8d7ed2/candidate-images.json --review-only`
để đối chiếu scan hiện có, rồi `run_regression.py --group unit-api` và các nhóm
còn thiếu. Không scan lại chỉ vì đổi policy nếu artifact/scan không đổi.

Các mục bên dưới giữ lịch sử trước thay đổi portable.

## Gate đầu vào

Phase7 T121–T137 đã khép trong phạm vi local đã duyệt; xem
[checkpoint](product-resume-20261111.md). T014_FULL vẫn BLOCKED/security FAIL,
không phải nghiệm thu toàn MVP. Không commit/push, không sửa demo cổng13000 hoặc
volumes có trước. Chủ dự án ủy quyền áp dụng phương án đề xuất trong lượt tiếp tục;
hồ sơ tại `docs/decisions/continuation-autonomy-20261111.json`.

## T138 — runner và profile riêng

- Compose test profile có network nội bộ và PostgreSQL/MySQL/credentials riêng.
  Backend test runner không nhận production secret domains hoặc network ứng dụng.
  Init test DB, migration và seed diễn ra trong container có disposable guard.
- `run_regression.py` điều phối unit/API, integration, ETL, Airflow, E2E và stress
  bằng các driver fixture hiện có. Mỗi selector lưu IDs/commands/exit code/cleanup.
  Không mount Podman socket hoặc chạy test trên DSN của demo.
- `t138-isolation`:1PASS0.027s, kiểm ranh giới network/secret/ports của profile.
- `t138-unit-api-collect`:208PASS/1FAIL190.60s trên source fixture; failure là
  capture HTTP machine-local bị thiếu. Test đã chuyển sang responses HTTP thật.
- `t138-compose-profile`:201PASS/8FAIL190.66s; image thiếu DAG template, test
  hardcode `/tmp/specs`, capture HTTP thiếu. Đã bổ sung assets, đường dẫn tương
  đối root và live contract responses; giữ nguyên logs FAIL.
- `t138-compose-verified`:206PASS/3FAIL216.93s. Ba ca import generated DAG cần
  pendulum/SDK và phải chạy trong image Airflow, không đưa Airflow vào backend
  runtime để chữa môi trường test. `t138-sdk-unit`:4PASS1.490s trên SDK thật;
  coordinator chỉ PASS nhóm unit khi cả backend cases và SDK cases đều PASS.
- `t138-integration`:54PASS36.62s, foundation/repositories/operations/API,
  Connections, Table DDL và File Sources trên database thật; không overlay.
- `t138-compose-etl`:133PASS/11FAIL185.42s, đã phát hiện vấn đề recovery phía dưới.
  Không tính lượt này là PASS và không khép T138 chỉ từ những nhóm đã đạt.

Test-only candidate đầu `e9d07121...` và candidate `0afe72f2...` scan cùng baseline
runner:56HIGH/2CRITICAL, không HIGH/CRITICAL context mới. Quyết định theo ủy quyền
được ghi bằng exact IDs, không mở rộng hạn/controls và không đánh security PASS.

## Recovery: một candidate lỗi không được làm dừng maintenance

Regression rộng phát hiện binding thiếu dataset có thể bị một kết quả inspection
không nhất quán đưa tới metrics insert với extracted_rows/validated_rows null;
PostgreSQL chặn NOT NULL và vòng recovery dừng trước các binding tiếp theo.
Thiếu replacement admission cũng từng ném ValueError làm dừng toàn lượt.

Test tái hiện `recovery-poison-red`:ERROR/NotNullViolation đúng lý do trước sửa.
Backend nay kiểm manifest hash và count evidence trước projection, giữ
NEEDS_RECONCILIATION với lý do DATASET_EVIDENCE_UNVERIFIED hoặc
ADMISSION_EVIDENCE_UNVERIFIED; không xóa dữ liệu, không giải phóng ONCE hoặc quota,
không tự ghi số0 thay số chưa rõ. Các test mới kiểm metrics/binding không bị đổi
và FULL_REFRESH thiếu admission giữ row99 của target.

Module runtime lifecycle có comment “reuse fixture only” nhưng thực tế kế thừa
cả adapter test suite, gán inherited methods thành None và còn import class trực
tiếp để pytest collect lặp. Đã chuyển sang composition các fixture methods và bỏ
vòng gán None; adapter cases vẫn chạy đúng một lần ở module gốc. Không bỏ assertion
hoặc biến mandatory test thành skipped.

Lượt `recovery-isolation-green` và `recovery-admission-green` đang kiểm lại nhóm
bị ảnh hưởng. Chỉ kết quả cuối có exit code0 mới là PASS. Backend image tiếp theo
phải chứa fix này và được scan/review trước nghiệm thu package.

Lượt `recovery-isolation-green` ban đầu lỗi collection vì còn vòng tham chiếu
class cũ cuối module sau khi đổi import; đã bỏ vòng không còn cần đó, rerun lưu
`recovery-isolation-rerun`. `recovery-admission-green`:1PASS3.349s, old target99
giữ nguyên và binding/metrics không bị một claim thiếu admission sửa thành success.

## Tiếp nhận trên máy TrungLQ13 ngày 2026-11-11

Spec Kit prerequisite PASS; checklist requirements16/16 và spec-quality48/48 đã
checked, không sửa checklist. Không có `.specify/extensions.yml` hoặc AGENTS.md
trong repository. Working tree đầu lượt sạch.

Các JSON mới hơn phần mô tả phía trên đã có kết quả cuối trên máy trước:
`t138-current-etl` PASS cả etl-engine/etl-runtime, `t138-stress` PASS,
`t138-unit-api-final` PASS cả unit-api/unit-sdk, `t138-current-package-e2e`
PASS Monitoring và Phase7. `recovery-sdk-faults/airflow-fixture-results.json`
PASS trên installed image wheels và cleanup codes đều0. Đây là evidence lịch sử,
không phải các test vừa chạy lại trên máy hiện tại; không suy thành full regression PASS.

Podman machine có trước đã khởi động thành công, client/server6.1.1,
Linux/amd64; `podman ps` không có container đang chạy tại thời điểm tiếp nhận.
Không sửa/xóa stack hoặc volumes có trước. Local store không có8IDs trong
`tests/fixtures/regression-images.json`, cũng không có6 baseline IDs Phase7
dùng cho cùng-snapshot scan. Không thay baseline bằng các tag local cũ.

Runner `run_regression.py` bổ sung `--preflight-only`, kiểm đủ required IDs của
nhóm được chọn và ghi `BLOCKED` trước khi khởi động fixture khi thiếu image.
Integration không còn phụ thuộc browser/Airflow images không dùng; unit-api vẫn
bắt buộc SDK image. `PREFLIGHT_PASS` tách khỏi test `PASS`, không tính là nghiệm thu.

Kiểm chứng mới:

- `python -X utf8 -m unittest tests.unit.test_regression_preflight -v`:
  3PASS0.101s; subprocess inspect được cô lập bằng mock, chỉ kiểm logic điều phối.
- `python -X utf8 tests/tools/run_regression.py --group all --preflight-only
  --evidence-dir docs/testing/resume-20261111/t138-machine-preflight`:
  BLOCKED,8IDs thiếu; không chạy test hoặc fixture.
- Kiểm inspect baseline thật:6/6IDs thiếu. JSON riêng tại
  `resume-20261111/t138-machine-preflight/baseline-images.json`.

T138 giữ `[ ]`; T139–T152 chưa mở. Để tiếp tục packaged acceptance cần khôi phục
exact image archives từ máy đã tạo evidence hoặc chuẩn bị baseline có nguồn gốc
và review cụ thể theo controls hiện hành. Không tự coi image rebuild là ID cũ.

Candidate mới `phase8-candidates-7bf5343e` đã build đủ6stage; source hashes và
exact IDs nằm trong thư mục evidence cùng tên. Lệnh
`python -X utf8 tests/tools/build_phase6_candidates.py --phase phase8` exit0.
`verify_phase6_packages.py --manifest <candidate-images.json>` exit0,
packaged bytes PASS91API/45engine/26metadata modules. Chỉ tạo container để copy
artifact rồi remove, không start candidate runtime. Frontend typecheck/Vite
build chạy trong stage build, không suy thành browser E2E PASS.

`scan_phase6_candidates.py --manifest <candidate-images.json>` exit1 tại
preflight inspect baseline backend `97af4b9a...`, underlying Podman exit125.
Không có `candidate-security.json`, không tạo scanner volumes hoặc chạy scan;
security ghi NOT_RUN/BLOCKED, không áp delegated approval cho các IDs mới.
Không có build/test chạy nền còn dang dở khi kết thúc lượt này.
