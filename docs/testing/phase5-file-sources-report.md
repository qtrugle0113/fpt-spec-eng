# Checkpoint File Sources — 2026-11-09

Phase4 đã khép T047–T060 bằng source18PASS, regression47PASS, production E2E10PASS
desktop/mobile trên Backend owner đã duyệt và Frontend cuối scan0HIGH/CRITICAL;
ảnh đã kiểm, cleanup0. Không hỏi lại các image ID đã duyệt.

## Tiến độ hiện hành

**2026-11-10:** sửa BOM đầu dữ liệu UTF-8 không header, có RED→GREEN riêng.
Hồi quy mới nhất **116/116 PASS** trên PostgreSQL/MySQL thật tại
`resume-20261109/phase5-bom-regression-green.log`; thay số115 của snapshot dưới.
Backend Files `b1943b235931110c0fa61e5c8e66111e565efd08fdfe6ffe0e1210b29843b352`
đã được owner xác nhận mapping ngoại lệ local theo
[review](phase5-us3-image-review.md). Scan42HIGH/CRITICAL, delta0/0; Frontend0.
Installed API/engine55/55file khớp source. E2E Files đang chạy; T068/T069 còn mở
đến khi có browser và persistence evidence. T070 bắt đầu viết tests trước code,
chưa đánh dấu hoàn thành hoặc coi RED là nghiệm thu engine.

**Mốc Files đã đạt:** T068/T069 khép bằng browser **12/12 PASS** và persistence
**2/2 PASS** sau force-recreate backend/worker, giữ volume fixture. Proxy refresh
và cleanup đều exit0; không publish port, không đụng services/dữ liệu hiện hữu.
IDs, source hashes và từng exit code trong
`resume-20261109/files-acceptance/files-e2e-results.json`; logs browser/persistence
cùng thư mục. Ảnh desktop1440/mobile390 đã kiểm tại `.tools/files-e2e-artifacts`;
không global overflow, bảng có horizontal scroll riêng. Không gán nghiệm thu này
cho code engine T071 mới được viết sau khi đóng gói Files.

T070:19tests RED đúng missing implementation, không collect error; log
`resume-20261109/t070-engine-red.log`. T071 typed contracts **7/7 PASS**, gồm
canonical hash, source union/strategy/filter/literal strict, cron/timezone/DST và
round-trip qua JSON Schema OpenAPI chính thức, tại `t071-schema-contract-green.log`.
T070 còn mở đến kiểm đủ engine; T071 có đầu ra source nhưng chưa dùng để tuyên bố
execution engine hoàn thành. Đang chạy regression Tables/Connections trên đúng
runtime Files đã duyệt vì có thay đổi middleware/upload dùng chung.

**Runtime regression đã đạt:** Tables10/10PASS và Connections6/6PASS trên Backend
Files đúng ID owner đã duyệt, cùng Frontend Files; cleanup0 ở cả hai fixture.
Bằng chứng tại `resume-20261109/files-runtime-tables-regression` và
`resume-20261109/files-runtime-connections-regression`. Tiếp
[checkpoint engine](phase5-engine-report.md) cho T070 trở đi.

**Cập nhật mới nhất:** T061–T067 đã khép bằng **23/23 PASS** trong
`resume-20261109/files-ingress-core-green.log` và fixture results. Bao gồm actual
upload256MiB boundary, interrupted cleanup, retained referenced files, full tail/
checksum/missing validation, parser candidate/PATCH/active/recovery/stale/immutable
binding, queued validation không ghi VALID cho parser mới, lỗi đúng line/record
và request ID, declared/chunked ingress cap trước multipart spooling.

File Sources panel đã có trong DAG Builder, typed client từ canonical OpenAPI,
preview candidate→confirm PATCH→full validate→select stable ID/parser/SHA.
Frontend build/typecheck đầu PASS; đang hoàn thiện kiểm tra browser và chuẩn bị
T069. T068/T069 còn mở, không kế thừa E2E của Table. Các bullet dưới giữ lịch sử.

**Hồi quy mới nhất:** `phase5-preimage-regression-green.log` **115/115 PASS** trên
PostgreSQL/MySQL thật, gồm foundation, Connections, Tables và Files. Đã sửa hai lỗi
cleanup được chứng minh RED→GREEN trong `upload-preservation-*.log`: không xóa
partial của request khác khi collision; workbook có metadata COMMIT thật vẫn giữ
blob khi mất ACK. T052/T064 đã kiểm lại và đóng. Files cũng có HTTP TCP disconnect
thật và lost-COMMIT-ACK với PostgreSQL thật; `files-network-core-green.log`25PASS.

Đang chuẩn bị E2E Files; driver `--suite files` chạy browser rồi force-recreate
backend/worker và refresh nginx, tiếp tục `files-persistence.spec.ts` để full
validate lại byte file từ volume. Browser tests giữ manifest reference/parser/SHA
thật, không thay kiểm chứng persistence bằng browser reload.

Lưu ý cho T085/T104 sau này: model RunIntent hiện bắt buộc authorization_id,
trong khi APPEND/UPSERT không được yêu cầu hoặc tự tạo consent FULL_REFRESH.
Phải đối chiếu Spec/Runtime trước khi triển khai intent cho các policy đó; không
giả grant để vượt FK. Fixture guard hiện dùng FULL_REFRESH với authorization
metadata riêng hợp lệ, không thực thi target DML và không là nghiệm thu engine.

- T061/T062: đã viết Files API contract, parser và storage fixtures. Lượt RED
  đầu collect18 methods, lỗi đúng thiếu Files routes/storage/reader; không có lỗi
  collect. `resume-20261109/t061-t062-red.log` giữ bằng chứng.
- T063: bounded lexer/reader đã có, `t063-green.log` **8/8 PASS**. Giữ provenance
  quoted/unquoted NULL, strict text codec, BOM, multiline, header/no-header,
  line/record thật, record<=1MiB và buffer<=8MiB; preview<=100 không thay full
  validation. Reader không import API hoặc Airflow.
- Đã bổ sung retention fixture: file quá hạn nhưng được Definition/binding tham
  chiếu không được collection. Đang chạy RED Files/storage mới trước T064.
- Tiếp theo: T064 streaming storage/checksum/atomic publication; T065 full-format
  worker; T066/T067 API/parser snapshots và dependency/active/recovery guards;
  sau đó UI/E2E và các task engine đủ dependency theo plan.

Driver source test đã copy thêm `etl_engine` và đưa `/tmp/etl_engine/src` vào
PYTHONPATH để kiểm đúng code mới, không vô tình import wheel engine cũ. Dùng image
đã duyệt: Airflow b5e…d52e có test-only YAML/jsonschema, workbook libraries từ
Backend18fa…b7e2 khi import toàn API; Backend-tests6b65…123e cho reader thuần.
Không pip install dependency khác hoặc tạo ID giả.

Files tests yêu cầu metadata PostgreSQL thật và volume/disk fixture riêng. Upload
limit phải kiểm đúng256MiB, không hạ limit trong test. Upload gián đoạn/quá limit
không được publish metadata hoặc giữ partial bytes. Parser PATCH phải giữ content,
reference, checksum và lịch sử FileParserRevision; active/recovery trả409, ETag cũ
trả412. Definition đã bind giữ parser revision cũ, future revision phải revalidate.

T014_FULL vẫn BLOCKED. Chưa tuyên bố US3/File Sources hoặc MVP hoàn thành. Không
commit/push, không deploy Internet hoặc xóa dữ liệu/volume hiện hữu.
