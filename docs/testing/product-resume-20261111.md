# Checkpoint tiếp tục ngày 2026-11-11

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
