# Tiếp tục Connections sau mất mạng — 2026-11-09

**Đã khép story Connections:** owner đã xác nhận Backend mapping; E2E6/6PASS
desktop/mobile trên production artifacts thật. Đã xem screenshot1440/390px, không
tràn ngang toàn trang. Đã sửa Compose app-init sang `python -m docker.bootstrap.app_init`
và selector combobox trong test; các lượt FAIL giữ riêng để truy vết. T045/T046 đã
đóng; bắt đầu Phase4 theo dependency. Các đoạn chờ review/E2E bên dưới là snapshot cũ.

## Đầu ra hiện tại

Đã nhận lại kết quả các process trước gián đoạn, không chạy trùng build đã hoàn tất.
Không có container sản phẩm được để chạy hoặc mở cổng sau lượt kiểm thử.

- Foundation: live readiness2PASS, full aggregate49PASS, Compose profile51PASS và
  response contract1PASS; T034 đã đóng. Hai lỗi profile đã sửa: kiểm worker trong
  wheel và credential fixture không được regenerate khi start dependencies.
- T035/T036 viết và chạy RED trước phần triển khai (routes thiếu/adapters và rotation
  chưa có), không phải collection error. Sau triển khai, tổng hợp Connections23/23
  PASS trên PostgreSQL/MySQL thật: 11HTTP,7adapter/policy,2rotation,3schema.
- Source mới chạy lại foundation core47/47PASS. Các suite có phần chồng nhau,
  không cộng thành tổng số test độc lập.
- T037–T043: rotation, adapters, schemas, revision CRUD/dependencies, safe routes đã
  kiểm. Có kiểm binding giữ credential reference cũ, chặn đổi location khi active,
  invalidation authorization/admission và ciphertext tại DB.
- T044: TypeScript types sinh từ canonical OpenAPI, không `any`; client có ETag,
  safe error, polling và timeout. Typecheck/build thực trong Node22.23.4 PASS.
- Trang Connections/form đã nối API, không cache password; build frontend PASS.
  T045/T046 giữ chưa đóng vì chưa chạy E2E desktop/mobile trên artifact mới.

## Artifact và gate

Đã build Backend runtime, frontend và E2E runner. Frontend/E2E runner có0HIGH/CRITICAL.
Backend có42HIGH/CRITICAL giống baseline, 0thêm/0bớt; đang chờ owner mapping đúng
ID mới theo [hồ sơ](phase3-us2-image-review.md). Ba ID đã được xác nhận ở lượt trước
vẫn có hiệu lực; không tự mở rộng sang Backend runtime mới. MySQL mới có0HIGH/CRITICAL.
T014_FULL vẫn BLOCKED; không nghiệm thu public deployment hoặc MVP.

Fixture E2E `tests/tools/run_connections_e2e.py` đã qua `--prepare-only`: dùng production
Compose đã resolve với image IDs thật, project/network/volumes riêng, internal network,
không publish ports. Sau khi Backend mapping được duyệt, driver khởi stack thật,
chỉ chuyển hai credential database sang runner, chạy Connections và shell/private-proxy
tests trên desktop/mobile, redact log và cleanup đúng project.

## Lệnh tiếp tục

```powershell
python -X utf8 tests/tools/run_connections_e2e.py --backend-image 18fa537b59b8405da24bed0295e1234ec84e52d3538197cf25b50b1385a3b7e2 --frontend-image 3dc8e51aa5c51190eddd9aa374e6d6d18568a31512a668e0cba6e3e3fe8497da --e2e-image 960bb3edb6e256a94ec5bf29373e54354d922cc8a4b391d0bd1bed9e074d7415 --airflow-image b5e9745e9bd836d28b7c085b653a315eaa34832f1cb92491cdf9c8f73cf1d52e --postgres-image c93823be91b7c9219c9e97423fdd9ffbe36ce2423fbfa099ecf7355bd69a2dce --mysql-image 76ef5ef385ae6bea4acbf835f439350abb6903eab6a3ccba5082d3d56a4be2bf --evidence-dir docs/testing/resume-20261109
```

Chỉ đóng T045/T046 sau kiểm E2E/visual và xử lý mọi lỗi thật. Phase4 theo dependency
T046; không dùng kết quả build thay cho nghiệm thu story.

Bằng chứng: `resume-20261109/phase3-connections-green.log`, fixture results,
`phase3-us2-image-security.json`, `phase3-us2-image-delta.json` và
[hướng dẫn Connections](../operations/connections.md).
