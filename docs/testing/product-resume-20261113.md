# Tiếp tục triển khai ngày 2026-11-13

## Bản dùng thử đang chạy

Ứng dụng <http://localhost:23000>, Airflow <http://localhost:28080>, readiness
<http://localhost:28000/api/v1/health/ready>. Project
`aat-portable-demo-a7f852ae`; record `.tools/local-demo.json`, không source overlay.
Không xóa volumes hoặc đổi manifest demo khi tiếp tục kiểm thử riêng.

Workflow UI thực tế trên demo desktop/mobile6checks PASS,35.267/31.387s,
4dòng đích exact values mỗi luồng. Xem Monitoring:
`aat_full_desktop_1794495308921`, `aat_full_mobile_1794495345481`.
Ứng dụng không login; Airflow có xác thực riêng, không in password vào evidence.

## Đã kiểm chứng trong lượt tiếp tục

- T143 khép:9SDK cases PASS164.053s, engine file/full-refresh/quota29PASS55.10s,
  cleanup0. Chi tiết [checkpoint12/11](product-resume-20261112.md).
- Cron APPEND/FULL_REFRESH:2PASS46.900s, dữ liệu và manifest thực.
- T144:4cases retry/SIGKILL/commit response loss PASS70.257s; thêm6cases
  source/target session loss và app metrics projection failure PASS113.164s.
  Một intent/một binding, exact target rows; evidence
  `resume-20261113/dependency-recovery-airflow/` và
  `resume-20261112/retry-refresh-airflow/`. Cleanup0. Không gọi session loss là
  bằng chứng đã stop/start toàn bộ DB service.
- T145:12cases admission/commit loss, revoke trước/sau admission và extraction
  kill/terminal PASS203.339s; cleanup0.
- T139 E2E history/parser/authorization PASS trên packaged full-workflow fixture.
  T148 security14PASS, language6/6 và contract drift2/2; T149 response limits và
  Dashboard truth PASS. Evidence tại `resume-20261113/history-parser-e2e/`,
  `security-surfaces/`, `language-e2e/`, `response-limits-measured/` và
  `dashboard-truth-airflow/`.
- T147 packaged Airflow large-data PASS:22.000 hàng, payload1.441.792.000 bytes,
  174 commits/parts, staging allocated1.442.504.704 bytes, peak child RSS103.460.864
  bytes với budget536.870.912. Cùng image IDs đã preflight, 15/15 quota/RSS/protected-GC
  tests PASS, gồm process kill trước OOM và bảo vệ artifact cần reconciliation.
  Evidence tại `resume-20261113/airflow-memory-large-r5/` và
  `resume-20261113/airflow-memory-guards/`.
- T146 concurrency module PASS hai lượt liên tiếp trên packaged runtime/disposable
  fixture: PostgreSQL và MySQL manual+scheduled aliases, 2/2 tests, maximum
  writers=1, bốn hàng exact mỗi target; fixture cleanup 6/6. Evidence:
  `resume-20261113/current-t146-diagnostic-r3/` và
  `resume-20261113/current-t146-confirmation/`. Lượt lỗi cũ không tái hiện;
  diagnostic test-only dùng đúng attempt/pagination, không sửa runtime. Revision,
  old-clear và authorization/credential invalidation được covered bởi T118/T119/T145.
- T151 verification PASS: sample artifact hash/byte/LF checks 3/3; regression unit/API và SDK
  selectors PASS trên exact LOCAL_POLICY_MATCH images. Fresh T140 workflow đã
  tải cả Table/ETL templates, điền và upload workbook, xác minh checksum CSV và
  exact target values; fresh seed kiểm checksum cả CSV/TXT. Evidence:
  `resume-20261113/current-t151-sample-checks/` và
  `resume-20261112/aat-t140-bf3008e2/`. Checkbox T151 vẫn mở đến khi dependency
  T140 hoàn tất.
- T150 docs được đồng bộ; internal links cho README/architecture/API/Excel/
  troubleshooting/Quickstart và diff checks PASS. Quickstart đã sửa trạng thái T146 cũ.
  T139, T144, T145, T147–T150 đã khép.
- Contract drift mới: runtime route inventory và required JSON request fields
  khớp canonical contract, derive từ schema thay vì hardcode operation count.
  Hai checks PASS1.927s trên installed backend image với test source mới,
  không DB/mạng/application overlay; container kiểm đã remove. Evidence
  `resume-20261113/contract-drift/unittest.log`. Chưa là toàn bộ T148 audit.

## Fresh startup T140

Portable scan follow-up: current local image IDs match all 10 artifacts in
`resume-20261111/portable-a058b7de/candidate-images.json`. Re-evaluating that
exact scan with `scan_portable_images.py --review-only` returned
`LOCAL_POLICY_MATCH`; `security=FAIL_WITH_APPROVED_LOCAL_EXCEPTIONS` and
`T014_FULL=BLOCKED` remain unchanged. The incomplete `a4ec9c82` source snapshot
differs from the workspace only in Plan/Tasks and the T146 diagnostic test;
runtime/build/sample source inputs match. No runtime tests were run in this
continuation.

Selector `tests/integration/test_one_command_startup.py`: PASS564.113s tại
`resume-20261112/aat-t140-bf3008e2/result.json`.

- Không `.env`, project/volumes mới; build preparation trước runtime admission.
- Build Compose tạo IDs khác portable; scan5artifact mới và reuse2exact IDs
  kết thúc LOCAL_POLICY_MATCH. Manifest riêng
  `.tools/aat-t140-bf3008e2-images.json`; không thay manifest demo.
- Đúng `podman compose up --build -d`, READY179.531s, không migration/seed thủ công.
- Workflow UI desktop/mobile6checks PASS,35.707/28.079s,4dòng exact target values.
- Restart giữ connection IDs/template checksum. API Airflow chưa auth trả401.
- Mất secret, key, hoặc keyring volume: init exit1, không reset; restore bản gốc
  rồi readiness và metadata snapshot vẫn đúng. Cleanup0, không giữ stack T140.
- Lượt trước `aat-t140-eb137d9e` FAIL tại gate IDs trước runtime; giữ evidence,
  không tính lượt đó PASS. Result NOT_RUN của startup không đồng nghĩa test PASS.

T140 còn phải đối chiếu đủ restart giữa extraction/commit/refresh trước khi
đóng task; các ca recovery SDK phía trên dùng fixture riêng, không suy thành
đã restart container giữa transaction trên fresh stack.

## Đang làm và còn lại

- T140 fresh selector đã PASS trong564.113s, nhưng còn thiếu restart giữa
  extraction/commit/FULL_REFRESH trên fresh Compose stack.
- T151 đã có verification PASS nhưng checkbox chờ T140 theo dependency.
- T152 final acceptance chưa thể chạy khi các task/gates trên còn mở.
- T014_FULL vẫn BLOCKED. Chỉ local/dữ liệu tổng hợp/loopback; hạn ngoại lệ
  23/11/2026 00:00 UTC+09, review16/11. Không thêm ngoại lệ mới.
- Source/locks/core/SDK giữ nguyên; chỉ runtime Airflow bỏ git/git-man không dùng
  sau khi scan phát hiện3advisory HIGH mới. Policy portable hiện MATCH.

## Bước tiếp theo

Tiếp tục T140 phase-specific restart trên fresh Compose stack, sau đó chạy
`/speckit-analyze`. Chỉ hoàn tất T152 nếu Analyze và mọi mandatory acceptance
gates đều PASS; T014_FULL chỉ đóng theo scan/CI/reviewer evidence, không tạo waiver mới.
Không commit/push hoặc xóa stack/dữ liệu có trước.
