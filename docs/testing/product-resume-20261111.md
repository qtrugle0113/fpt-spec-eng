# Checkpoint tiếp tục ngày 2026-11-11

## Trạng thái ưu tiên để tiếp tục

**Sửa quota mới nhất, chưa nghiệm thu runtime:** đã xác định nguyên nhân T143
bằng stack private: QuotaExceeded, không phải TXT parser. Source
`etl_engine/src/aat_etl/readers/file_source.py` giới hạn mapped reservation
FULL_REFRESH theo số dòng × MAX_ROW_BYTES + MAX_MANIFEST_BYTES, cap theo quota
run còn lại. Không thay các quota/controls, không xóa PROTECTED/raw COMPLETE,
không giải phóng ONCE. Build tại `portable-346d83ce/`: backend `cfd6b296...`,
Airflow `8cb33c0d...`, tests `ecfc46d1...`; scan 5 artifact thay đổi đang hoàn tất.
`installed-reservation-package.json`: 3 module hashes PASS trong site-packages.
T143 nay có 9 ca (thêm FULL_REFRESH CSV→PG/TXT→MySQL thành công), còn phải chạy
selector bình thường không instrumentation trên image mới sau khi policy đạt.
Runner hỗ trợ `--etl-path tests/etl/test_file_transfer.py` để chỉ chạy phần liên
quan. Không tính các kết quả cũ thành PASS cho bản sửa quota này.

**Installed API guard đã PASS:** `installed-missing-source-guard/` có 6 browser
checks PASS/1.9 phút trên backend `8204b16f...`, desktop/mobile workflow thật
54.588/52.118 giây, 4 dòng đích đúng mỗi workflow. Preview/trigger missing file
đều409, 0 intent, khôi phục file→preview200; target exact values sau khôi phục
PASS; cleanup0. Không source overlay. Demo23000 vẫn giữ image trước bản sửa.
Chẩn đoán hai ca terminal failure→TXT đạt2PASS/81.691s nhưng không coi là
nghiệm thu. Đang chạy toàn chuỗi instrumented tại `t143-full-sequence-diagnostic/`.

**Bản sửa mất file mới:** backend `8204b16f...`, manifest/scan/receipt tại
`resume-20261111/portable-0d406416/`, policy LOCAL_POLICY_MATCH; 4 artifact mới
đã scan, 6 artifact không đổi tái dùng receipt exact ID trong 24 giờ. Installed
module hash PASS tại `backend-guard-package.json`. Thêm HTTP409 an toàn trong
compile preview, không thay dependency baseline. Demo đang chạy vẫn giữ image
trước bản sửa. Lượt T143 sau sửa ở `t143-guard-rerun/`; đọc kết quả trước khi
rerun. TXT→PG chạy riêng đã PASS tại `t143-txt-diagnostic/`, cleanup 0.
Lượt `t143-guard-rerun/` đã kết thúc: 5 PASS/2 FAIL trong 119.518 giây,
cleanup 10 mã 0. Missing-file guard đã PASS; TXT cả hai DB vẫn FAIL theo chuỗi.
Selector chẩn đoán không thay engine behavior (chỉ ghi tọa độ stack, không ghi
exception text/dữ liệu/secrets) tại `t143-terminal-sequence-diagnostic/` đang
kiểm tra terminal failure→TXT. Không tính instrumentation này là nghiệm thu.

- T138 đã khép: 13 selectors PASS trong `resume-20261111/t138-aggregate.json`.
  E2E gồm Connections 6, Tables 10, Files 12+2 persistence, DAG Builder 12,
  Monitoring 8, Phase7 10+2 persistence+2 outage; cleanup đã đối chiếu.
- T141 đã khép: `t141-explicit-conversions/acceptance.json`, 6 browser checks
  PASS; hai luồng UI thật desktop/mobile 40.233/36.144 giây, mỗi luồng 4 dòng
  đích đúng Unicode/NULL/decimal/timestamp. Lượt lỗi thiếu Type Conversion giữ lại.
- T142 đã khép: `t142-cross-database/`, 4 ca PASS 82.579 giây, installed SDK,
  cả PG→PG/MySQL→MySQL/PG→MySQL/MySQL→PG; khóa ghép và kiểu dữ liệu đúng.
- T143 đang xử lý: `t143-file-database/`, 7 ca, 4 PASS/3 FAIL; CSV hai hướng,
  invalid format và invalid typed FULL_REFRESH đã PASS. TXT headerless hai
  hướng thất bại trong SDK; mất file trước trigger trả 500 thay lỗi nghiệp vụ.
  Chưa sửa application runtime, không được báo T143 PASS. Selector chẩn đoán
  riêng lưu tại `t143-txt-diagnostic/`; kiểm tra kết quả trước khi chạy lại.
- T139/T140/T144–T152 còn mở; T014_FULL BLOCKED. Ngoại lệ Kerberos đã duyệt,
  hết hạn 23/11/2026 00:00 UTC+09, review 16/11, chỉ local/dữ liệu tổng hợp.
- Demo mới `aat-portable-demo-dcae6f3c` tại 23000/28080/28000; không xóa volumes.
  Khởi động/resume xem [hướng dẫn](../operations/local-portable.md).
  Manifest `.tools/local-images.json`, policy `portable-ce69c81e/local-policy-review.json`.
  Các mục nói T138 chưa khép/chờ Kerberos bên dưới là lịch sử.

## Sau phê duyệt và startup thực tế

Chủ dự án đã duyệt14Kerberos advisories/306contexts đúng đề xuất/hash, giữ
hạn/controls; policy hiện LOCAL_POLICY_MATCH. Bản mới23000/Airflow28080 READY,
installed images, init0/healthy và12browser smoke PASS. Xem
[hướng dẫn local](../operations/local-portable.md). Không thay demo/volumes cũ.

T138 đã có214unit/API,4SDK,54integration,118engine,19runtime,8Airflow routes,
stress1.107GB/270batch/RSS106745856bytes PASS; Connections6/Tables10E2E PASS.
Các E2E còn lại đang chạy; T138 chưa tick, T014_FULL vẫn BLOCKED. Failure đầu
về heartbeat2.2s và fixture Tables phụ thuộc máy trước đã giữ log, sửa và rerun.
Các trạng thái “chờ phê duyệt/chưa có URL” bên dưới là lịch sử.

## Checkpoint portable mới nhất

Chủ dự án duyệt thay ràng buộc cùng image IDs giữa các máy bằng source/locks/
config và scan từng artifact theo Constitution1.3.0. Build10artifacts, package
inspection91API/45engine/26metadata modules PASS;8unit tests PASS. Frontend vá
libxslt1.1.43-r4, scan mới0findings. Manifest local tại `.tools/local-images.json`,
evidence mới `resume-20261111/portable-af8d7ed2/`. Không cần image từ máy nhà.

Blocker hiện tại là findings mới:14advisory Kerberos/306contexts ngoài ngoại lệ
đã duyệt; chưa có quyết định chủ dự án. [Đề xuất cụ thể](../proposals/portable-local-krb5-20261111.md).
T138/T014_FULL vẫn mở/BLOCKED; runtime regression và startup mới NOT_RUN.
Không có container sản phẩm mới đang chạy. Các đoạn thiếu8/6IDs bên dưới là
lịch sử trước sửa quy trình. Tiếp tục từ [báo cáo Phase8](phase8-regression-report.md).

## Tiếp nhận mới trên máy TrungLQ13

T138 đang mở; đã đối chiếu JSON mới hơn và ghi lại các kết quả PASS lịch sử tại
[báo cáo Phase8](phase8-regression-report.md). Podman6.1.1 đã khởi động; máy này
thiếu8 image IDs của regression manifest và6 baseline IDs Phase7. Preflight thật
ghi BLOCKED, không thay bằng tag cũ. Runner bổ sung `--preflight-only` và kiểm
required images theo nhóm;3unit tests PASS. Candidate rebuild phải scan/review
riêng trước chạy runtime; T014_FULL vẫn BLOCKED. Không mở T139–T152 trước T138.

## Phạm vi

Tiếp tục working tree cũ, không commit/push hoặc triển khai công khai. Demo
`aat-dag_builder-e2e-6f3a6830` và volumes có trước giữ nguyên. T014_FULL vẫn
BLOCKED/security FAIL; quyền local hiện hành không tự bao phủ image IDs mới.

## Thay đổi

- Settings GET/PATCH với strong If-Match cho toàn bộ bốn defaults; khóa row theo
  thứ tự ổn định, stale412, validation422, readonly connectivity/version.
- Blank Batch Size lấy setting lúc validation và pin vào revision. Preview giữ
  giá trị đã pin; không áp default mới hồi tố. Workbook tường minh được ưu tiên.
- Dashboard UI dùng typed API thật:8KPI, schedule groups, SVG/time series, recent
  runs, next-run forecast, lifetime, date/timezone/scope, manual/auto refresh.
- Settings UI hiển thị phạm vi/range/unit, xử lý stale bằng reload/review;
  shared Feedback/ConfirmationDialog và focus main khi navigation.
- Tài liệu vận hành Monitoring, Dashboard, Settings; codegen đồng bộ OpenAPI.

## Bằng chứng đã có

Đường dẫn dưới `docs/testing/resume-20261111/`:

| Evidence | Kết quả và giới hạn |
| --- | --- |
| phase7-settings-regression |18tests PASS7.787s; Settings, workbook, Dashboard unit/API trên PG thật; outage fixture không có Airflow được ghi UNAVAILABLE. |
| phase7-api-verified |8tests PASS9.726s; thêm protected retention, thiếu trang và stale cache. |
| phase7-final-build |typecheck/Vite PASS với Node22.23.4/npm12.2.2 offline, không đổi dependency. |
| phase7-final-e2e |10E2E PASS7.2s desktop/mobile; sáu trang, keyboard, layout, Dashboard, Settings stale/range. |
| phase7-final-e2e/settings-persistence.log |2E2E PASS1.7s sau recreate backend/worker và refresh nginx; cleanup0. |
| connections-dialog-regression |6E2E PASS21.7s; CRUD PG/MySQL thật và dialog cancel/Escape/focus. |
| t132-dashboard-truth |1test PASS28.120s sau actual SDK execution, đối chiếu inventory/date/lifetime/zero denominator. |
| phase7-candidates-f8b388ed |6stage build PASS; inspect wheel bytes PASS91API/45engine/26metadata modules. Candidate runtime chưa chạy. |

Các kiểm thử trên là **source overlay trên dependency images đã duyệt**, ngoại
trừ build/inspect candidate chỉ tạo và đọc artifact. Không thay bằng chứng nghiệm
thu installed image mới. Source hashes, image IDs và lệnh selectors nằm trong
JSON/logs từng thư mục. Runner fixture không publish ports và không dùng volumes
có trước; cleanup chỉ tài nguyên thuộc project mới.

## Failure giữ nguyên để truy vết

- `t133-t134`:2PASS/1ERROR; preview áp default1000 khi validation đã pin2000.
  Đã sửa preview pin default theo revision, regression18PASS phía trên.
- `phase7-api-final`:protected fixture tìm kết quả GC bằng next() nhưng query
  loại protected binding ngay từ đầu; sửa assertion chấp nhận không được chọn,
  vẫn bắt buộc artifact tồn tại. `phase7-api-verified` PASS.
- `t132-dashboard-pages`:external pagination205runs PASS nhưng test thứ hai
  giả định chỉ có1managed DAG trong Airflow dùng chung hai test, thực tế2.
  Đã gộp assertions vào cùng lifecycle; lượt xác minh mới lưu riêng, không đổi
  aggregator để né lỗi fixture.
- `dashboard-settings-build`:build/typecheck PASS; host runner in ký tự ✓ lỗi
  cp1252 sau khi đã ghi kết quả/artifact. Lượt final dùng PYTHONIOENCODING=utf-8.

## Đang hoàn thiện

Kiểm concurrency Settings, pagination205runs trên Airflow thật, outage E2E bằng
dừng riêng API fixture, scan exact image IDs cùng baseline Phase6 đã duyệt.
Kết quả chưa có không tính PASS; xem phần cập nhật cuối báo cáo trước khi tiếp tục.

## Lệnh tiếp nhận

Đặt `.tools/podman-6.1.1/podman-6.1.1/usr/bin` vào PATH của process và
`PYTHONIOENCODING=utf-8`. Dùng `python tests/tools/run_metadata_foundation.py`
với `--unittest-module tests.api.test_settings`/`tests.api.test_dashboard`,
`run_airflow_foundation.py --runtime-execution-tests --runtime-execution-module
tests.airflow.test_dashboard_truth`, và `run_connections_e2e.py --suite phase7
--source-overlay --frontend-artifact .tools/aat-frontend-source-c95e3a05`.
Image references và full selector của từng lượt có trong fixture-results JSON.

Không mở Phase8 khi T132/T137 còn chưa đủ gate. Không tự duyệt image hoặc
checklist reviewer. Exact-image approval hiện tại tại
`docs/decisions/phase6-local-image-approval.json` có hạn2026-11-23T00:00+09:00,
review2026-11-16, chỉ áp dụng IDs đã ghi.

## Cập nhật sau phê duyệt Phase7

- Chủ dự án duyệt đúng delta4IDs tại `docs/decisions/phase7-local-image-approval.json`.
  Hai Airflow IDs không đổi giữ approval trước. Chủ dự án sau đó ủy quyền tự xử lý
  câu hỏi theo phương án đề xuất trong phạm vi công việc; không mở public, đổi
  hạn/controls hoặc miễn trừ T014_FULL.
- Candidate cuối `phase7-candidates-57ede3cf`:12targets scan cùng snapshot,
  không context HIGH/CRITICAL mới trên cả6stage so baseline cùng stage.
  Backend56HIGH/2CRITICAL, wheels59/2, frontend-build34/1, Frontend0/0.
  Payload inspection PASS91API/45engine/26metadata modules.
- Build offline ban đầu có CSS khác vì Tailwind quét thêm scripts/old context.
  Runner nay dùng thư mục sạch với đúng COPY inputs Dockerfile. Build mới
  `phase7-matched-context-build` PASS; `.tools/aat-frontend-source-cea342e5`
  khớp byte JS/CSS/HTML candidate, chỉ thêm50x.html từ nginx base.
- `phase7-matched-e2e`:10E2E +2persistence +2outage PASS, cleanup0.
  `phase7-visual-e2e` giữ FAIL:10mainPASS nhưng proxy recreate exit125;
  chưa có bằng chứng nguyên nhân chắc chắn. Rerun matched không gặp lại lỗi.
- `phase7-api-concurrency`:9PASS16.435s, gồm race hai PATCH khác field/cùng
  ETag (chỉ1request200,1request412), protected retention và explicit batch.
- `t132-dashboard-verified`:1lifecycle PASS32.235s, actual SDK run và205external
  runs qua nhiều trang (2success/2failed/201queued, rate50%). External fixture
  được tạo/đổi state qua Public API, không giả chúng đã thực thi ETL.

## Nghiệm thu image Phase7 và gate đã khép

- `phase7-packaged-e2e`:10main E2E PASS8.9s +2persistence PASS1.9s
  +2outage PASS2.2s, recreate0, cleanup0. Backend `97af4b9a...`, frontend
  `36700204...`, không source overlay. Installed origins xác minh API/engine/
  metadata từsite-packages, không mount /current.
- `monitoring-packaged-e2e`:8E2E PASS57.3s desktop/mobile; actual ETL rows/logs,
  queued paused→explicit unpause và external readonly; cleanup0.
- `t132-all-states`:1lifecycle PASS35.686s trên Airflow installed wheels;
  success/failed/queued qua205runs và thêm một task thật RUNNING. Pause readback
  giữ run RUNNING, không cancel. Dashboard đối chiếu đúng206runs, scope/date/
  lifetime và UNKNOWN historical schedule.
- T121–T137 đã khép đúng phạm vi task; T132/T137 đủ gate để bắt đầu T138.
  T014_FULL vẫn BLOCKED. Phase8 đang mở rộng regression profile riêng, chưa
  nghiệm thu toàn MVP.

## Tiếp tục Phase8

Chi tiết tại [báo cáo regression](phase8-regression-report.md). T138 còn mở trong
khi kiểm runner mới và fix recovery phát hiện từ regression rộng; chưa mở các
task T139–T152 cần dependency T138. Integration54PASS; SDK-unit4PASS và kiểm
network/secret isolation1PASS. Nhóm recovery bị ảnh hưởng đã rerun23PASS73.972s;
negative admission1PASS3.349s giữ target99 và uncertainty.

Backend recovery source mới chặn projection thiếu dataset/admission và giữ
NEEDS_RECONCILIATION, không nới safety gate. Đang build `phase8-candidates-88e9926e`
và `regression-candidate-1ec57e78` để scan/review trước chạy package; source ETL
toàn nhóm và real SDK fault lifecycle đang chạy, chưa ghi PASS khi chưa có kết quả.
Source test factory chạy trên installed Airflow SDK riêng, không đưa SDK vào
backend runtime hoặc dùng mock thay registration.
