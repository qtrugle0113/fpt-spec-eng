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
- T146 chưa khép: MySQL concurrency PASS; Postgres có lượt PASS riêng nhưng module
  lặp lại báo scheduled task `AirflowFailException` và chưa thu được guard message.
  Chưa kết luận lỗi sản phẩm hoặc đóng task trước khi có run ổn định/diagnostic.
- T150 docs được đồng bộ; internal links cho README/architecture/API/Excel/
  troubleshooting/Quickstart và diff checks PASS. T139, T144, T145, T147–T150 đã khép.
- Contract drift mới: runtime route inventory và required JSON request fields
  khớp canonical contract, derive từ schema thay vì hardcode operation count.
  Hai checks PASS1.927s trên installed backend image với test source mới,
  không DB/mạng/application overlay; container kiểm đã remove. Evidence
  `resume-20261113/contract-drift/unittest.log`. Chưa là toàn bộ T148 audit.

## Fresh startup T140

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

- T140 fresh selector đã PASS trong564.113s, nhưng còn thiếu restart giữa extraction,
  commit và FULL_REFRESH trên fresh Compose stack.
- T146 PostgreSQL concurrency cần giải thích scheduled run thất bại; MySQL tương ứng PASS.
- T151 chờ T140 và kiểm tra sample pack/download/checksum trên fresh stack.
- T152 final acceptance chưa thể chạy khi các task/gates trên còn mở.
- T014_FULL vẫn BLOCKED. Chỉ local/dữ liệu tổng hợp/loopback; hạn ngoại lệ
  23/11/2026 00:00 UTC+09, review16/11. Không thêm ngoại lệ mới.
- Source/locks/core/SDK giữ nguyên; chỉ runtime Airflow bỏ git/git-man không dùng
  sau khi scan phát hiện3advisory HIGH mới. Policy portable hiện MATCH.

## Bước tiếp theo

Tiếp tục T140 phase-specific restart và chẩn đoán T146 PostgreSQL bằng selector
cô lập; sau đó xác minh T151 sample pack/fresh stack rồi mới chạy T152 Analyze và
acceptance. T014 chỉ đóng theo scan/CI/reviewer evidence; không tạo waiver mới.
Không commit/push hoặc xóa stack/dữ liệu có trước.
