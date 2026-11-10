# Tiếp tục hướng tới bản chạy thử ngày 2026-11-10

## Checkpoint mới nhất sau phê duyệt image

- **Gate Phase6 đã khép:** T096–T120 đều hoàn thành trong phạm vi local đã duyệt.
  `t120-scopes-packaged-verified`12/12 E2E PASS2.4phút, actual verifier PASS,
  cleanup0; kiểm ONCE manual/CONSUMED, SCHEDULED activation, pause readback bằng
  cả Operation và UI. Lượt trước11PASS/1FAIL ở UI pause30giây giữ nguyên lịch sử.
  Bắt đầu T121–T127 Monitoring; T014_FULL vẫn BLOCKED, không nghiệm thu toàn MVP.

- T118/T119 đã khép: `phase6-packaged-sdk`12PASS251.039giây, import origins xác
  nhận Task SDK dùng installed image wheels, không source overlay;8routes,
  redeploy/old-clear, ONCE/clear-success và SCHEDULED/manual discrimination.
- `t119-fault-packaged`12PASS208.213giây: admission acknowledgment loss, target
  COMMIT loss, revoke trước/sau admission, extraction SIGKILL/retry và terminal
  extraction trên PG/MySQL. Fault marker phải khớp chính binding được kiểm.
  Negative giữ old row99 và đóng ONCE; positive CONSUMED/COMMIT_VERIFIED.
- `t119-backfill`1PASS30.384giây: backfill Airflow thật thất bại, không tạo binding
  bằng quyền SCHEDULED. `openapi-harness-airflow.log`9PASS0.587giây.
- Lượt fault đầu6FAIL do fixture revoke bằng role ETL bị chặn đúng và assertion
  phase recovery nhầm COMPLETE. Fixture nay revoke qua HTTP operator; COMMIT
  response-loss kiểm chính xác phase COMMIT_VERIFIED. Không nới grants hoặc sửa
  engine để né lỗi. Harness đầu thiếu PyYAML trong runner backend; rerun dùng
  dependency image Airflow đã pin, không cài thêm thư viện.
- T120 đang chạy `t120-scopes-packaged`: E2E bổ sung manual FULL_REFRESH→CONSUMED
  và SCHEDULED activation, ONCE không bật lịch, pause không thu hồi quyền.
  Các mục “T118–T120 còn mở” bên dưới là trạng thái trước các kết quả này.

- Chủ dự án đã duyệt đúng delta sáu image `phase6-candidates-add150fe`, giữ controls,
  hạn local và T014_FULL BLOCKED. Quyết định:
  `docs/decisions/phase6-local-image-approval.json`. Không cần xin lại approval đó.
- Build sáu stage PASS; payload Backend81/engine45/metadata26 modules đã đối chiếu
  nguồn. Scan9targets: Backend56HIGH/2CRITICAL, Airflow141HIGH/5CRITICAL,
  Frontend0/0; không context HIGH/CRITICAL mới ở ba runtime so baseline cùng DB scan.
- `phase6-packaged-e2e`: 10/10 PASS58.7giây, actual verifier PASS cho hai run
  browser/3rows/target values; cleanup0. Đây là nghiệm thu trên image mới, không
  source overlay. Bản demo cổng13000 vẫn giữ riêng.
- `phase6-final-contracts`:40PASS158.480giây, gồm workbook/deploy/authorization/
  trigger và readiness migration head.
- `phase6-final-sdk`:13PASS252.145giây trên source cuối:8routes, cron PG APPEND/
  FULL_REFRESH, ONCE PG/MySQL và clear success không replacement lần hai,
  SCHEDULED MySQL từ chối manual. Chưa dùng selector này thay installed-wheel run.
- `t118-revision-serialized`:6PASS62.879giây; redeploy version mới và clear old run
  thất bại, target/binding cũ giữ nguyên. Sửa race tag/last_parse mới nhưng serialized
  task cũ bằng params revision/hash và stable version readback từ public API.
- Một rerun mobile timeout do test tìm upload mới chỉ trên trang history đầu tiên;
  test nay thực hiện pagination, rerun1PASS6.9giây và actual verifier PASS.
  Giữ logs FAIL tại `product-demo-browser-final`/`product-demo-mobile-authority-rerun`.
- T096/T097/T115–T117 đã đánh dấu hoàn thành. T118–T120 còn mở tới khi installed
  wheels và fault lifecycle hoàn tất. Đang chạy `phase6-packaged-sdk` và
  `t119-fault-sdk`; chưa có kết quả thì không báo PASS. Phase7 chưa mở.

Các mục phía dưới ghi trạng thái ở đầu lượt tiếp tục, không thay checkpoint trên.

## Phạm vi và checkpoint

Chủ dự án yêu cầu tiếp tục toàn bộ công việc khả thi, ưu tiên luồng sử dụng xuyên suốt;
không commit/push, không triển khai công khai, giữ dữ liệu và gate hiện hành.
Prerequisite Spec Kit resolve đúng feature `001-airflow-automation-tool`; hai checklist
hiện có không còn checkbox mở. Không tự thay checkbox reviewer.

## Kết quả đã kiểm chứng

- Frontend hiện tại build/typecheck PASS bằng toolchain offline có sẵn
  Node22.23.4/npm12.2.2, không đổi dependency. Evidence:
  `resume-20261110/product-resume-frontend/`.
- Tám route qua scheduler/Task SDK thật PASS, 8 tests trong125.936giây:
  PG→PG, PG→MySQL, MySQL→PG, MySQL→MySQL, CSV/TXT→PG/MySQL.
  Kiểm dữ liệu đích `(1, first), (2, NULL)`, binding COMMIT_VERIFIED,
  staging COMPLETE, metrics extracted/validated/loaded=2 và failed=0.
  Evidence: `resume-20261110/t118-eight-routes-metrics/`.
- Nguyên nhân bốn failure trước: test đọc validated_rows từ raw file manifest
  thay vì execution_metrics. File APPEND/UPSERT chủ đích pin extraction-only
  manifest với validated_rows=0, bất biến sau COMPLETE. Test mới kiểm cả số0
  bất biến trong manifest và số2 đã validate/commit trong metrics; không sửa
  manifest/hash hoặc nới điều kiện thành công của sản phẩm. Hành vi này còn
  được kiểm trong `test_file_final_commit_can_reconcile_after_staging_is_lost`.

## Đang thực hiện

- `t118-scheduled`: APPEND và FULL_REFRESH chạy theo cron trên Airflow thật.
- `product-demo`: Compose project mới, mã nguồn hiện tại mount read-only trên
  dependency images có sẵn; frontend dùng artifact vừa build offline. Không
  thay image/tag hoặc volumes của stack khác. Cổng loopback13000/18000/18080.
- Bổ sung Playwright `dag_builder.spec.ts` cho desktop/mobile, tải template,
  upload/validate/review/deploy/trigger và invalid workbook. Chưa có kết quả
  thì không coi T115–T120 hoàn thành.

## Giới hạn nghiệm thu

T014_FULL vẫn BLOCKED. Source overlay không thay nghiệm thu wheel/image mới;
candidate Phase6 trong `phase6-candidates-230ab426/` vẫn chờ exact-image review.
T118 còn yêu cầu revision lifecycle; T119 còn ma trận authorization lifecycle;
T120 còn nghiệm thu đầy đủ wizard/authorization/E2E/docs. Phase7/8 chưa mở khi
gate T120 chưa khép. Không dùng bằng chứng route thành công để tự bỏ dependency.

Runner `run_connections_e2e.py` hỗ trợ `--source-overlay`, `--frontend-artifact`,
`--keep-running` và suite `dag_builder`. File Compose và project cụ thể được ghi
trong `product-demo/dag_builder-e2e-results.json` khi lượt chạy kết thúc.
Khi giữ demo, dừng bằng `podman compose -f <compose_config> -p <project> down`
với provider `.tools/docker-compose-5.6.0.exe`; không thêm `--volumes`.
