# Phase8 — regression và ổn định

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
