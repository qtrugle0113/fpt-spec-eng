# Review image File Sources — 2026-11-10

**Trạng thái: owner đã xác nhận mapping đúng Backend ID dưới đây trong hội thoại.**

Phản hồi: “Xác nhận mapping Backend Files theo hồ sơ”. Giữ controls và hạn
23/11 hiện hữu; tiếp tục browser acceptance đúng artifact, không mở rộng ngoại lệ.

| Artifact | ID đầy đủ | HIGH/CRITICAL | Delta so baseline R3 |
| --- | --- | ---: | --- |
| Backend runtime | `b1943b235931110c0fa61e5c8e66111e565efd08fdfe6ffe0e1210b29843b352` | 42 (40 HIGH, 2 CRITICAL) | 0 thêm / 0 bớt |
| Frontend | `03bd4469931a7e3f0f6681f0158c808864b1acd6e44bcfed9464d87c74754cc8` | 0 | 0 / 0 |

Scan Trivy0.76.1 mới trên archive đúng ID, toàn severity, không ignore-unfixed,
không engine socket. Đối chiếu advisory/package/installed version/fixed version/
severity với baseline R3. Backend vẫn security BLOCKED ngoài ngoại lệ local;
không coi findings không đổi là security PASS. Frontend có 1 MEDIUM.

## Bằng chứng trước mốc browser

- Source regression **116/116 PASS**, gồm foundation, Connections, Tables và
  Files trên PostgreSQL17.11/MySQL8.4.13 thật. Log và fixture IDs tại
  `resume-20261109/phase5-bom-regression-green.log` và fixture-results tương ứng.
- Test RED rồi GREEN cho UTF-8 không header giữ BOM đầu giá trị, tránh biến chuỗi
  thành NULL; UTF-8-SIG vẫn bỏ BOM theo codec được chọn rõ ràng.
- Streaming upload 256 MiB, ngắt HTTP thật, giữ blob khi mất COMMIT ACK, collision
  partial không xóa file khác, parser stale/binding guards và full validation
  ngoài 100 record preview đã kiểm. Upload Definition mất ACK cũng có regression.
- Installed wheel **55/55 file API và engine khớp source**. Chỉ create/copy, chưa
  execute Backend mới: `resume-20261109/files-packaged-source.json`.
- Frontend TypeScript/build PASS; browser specs desktop/mobile và persistence
  sau recreate backend/worker đã chuẩn bị. Production Compose preflight PASS tại
  `resume-20261109/files-preflight/files-e2e-results.json`.
- Browser acceptance **NOT_RUN**; T068/T069 chưa đánh dấu hoàn thành. Không kế
  thừa nghiệm thu image Table cũ cho image này.

## Quyết định cần owner

[Quy tắc repo](../proposals/t014-conditional-local-gate.md) yêu cầu “owner phải ký
delta trước mốc tiếp theo”. Đề nghị mapping ngoại lệ local hiện hữu sang đúng
Backend ID `b1943b235931110c0fa61e5c8e66111e565efd08fdfe6ffe0e1210b29843b352`
để chạy E2E Files và regression runtime, giữ controls hiện hữu, review 16/11 và
hạn 23/11/2026 00:00 UTC+09. Các ID đã duyệt trước vẫn giữ hiệu lực. Không miễn
trừ secret/auth/data integrity hoặc tiêu chí nghiệm thu; T014_FULL vẫn BLOCKED.

- [Scan](phase5-us3-image-security.json).
- [Delta đúng artifact](phase5-us3-image-delta.json).
- [Checkpoint](phase5-file-sources-report.md).
- [Vận hành](../operations/file-sources.md).
