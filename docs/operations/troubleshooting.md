# Xử lý sự cố local

## Không mở được ứng dụng

Kiểm tra `podman machine list`, khởi động machine có sẵn nếu đang dừng; không
init/reset machine để chữa lỗi kết nối. Chọn đúng Compose config/project trong
`.tools/local-demo.json`, kiểm `podman compose ... ps -a` và readiness backend.
Init phải exit0, service phải healthy; container running chưa đủ chứng minh sẵn sàng.

Nếu chưa có manifest/demo record, làm theo [local portable](local-portable.md).
Không tự dùng config/DSN của project kiểm thử làm demo. Cổng mặc định portable
là23000/28000/28080; không dừng stack khác chỉ để chiếm cổng.

## Validation hoặc deploy bị chặn

- Connection fail: kiểm hostname trong network Compose, database/user và quyền;
  không dùng localhost để trỏ sang container khác.
- Mapping text sang số/ngày: dùng `Type Conversion` trong workbook; xem
  [Excel](../excel-definitions.md).
- Stale412 hoặc stale confirmation409: đọc lại revision, review thay đổi và
  xác nhận scope mới. Không retry mù bằng token cũ.
- TARGET_BUSY: đợi writer/run hiện tại; không xóa lock hoặc hủy run để né gate.
- Parse/registration lỗi: xem deployment result và Airflow import error đúng DAG;
  file đã ghi không đồng nghĩa deploy thành công.
- Run queued khi DAG paused: xác nhận unpause riêng trong UI; không submit thêm run.

## ETL lỗi, quota hoặc commit chưa rõ

Giữ Run ID, operation ID, timestamps và revision. Xem Monitoring và log đã
redact; không gửi password/DSN vào báo cáo. NEEDS_RECONCILIATION cần đối soát
ledger và binding; không xóa staging/PROTECTED hoặc chạy lại bằng identity mới.

Quota không được chữa bằng tăng giới hạn hoặc xóa dữ liệu phục hồi. Xác minh
reservation và writer đã dừng theo [ETL engine](etl-engine.md). Lỗi nguồn/parser
không phải dataset rỗng hợp lệ và không được làm rỗng FULL_REFRESH target.

## Mất key/secret và sao lưu

Không xóa volume key/secret hoặc chạy seed reset để chữa lỗi decrypt/auth.
Giữ nguyên volumes, dừng writer và xác định snapshot/backup phù hợp trước phục hồi.
Backup phải bao gồm database ứng dụng, target data cần phục hồi, keyring/secrets,
uploads, generated DAGs và staging liên quan cùng checkpoint nhất quán. Giữ
backup ngoài log/public repository, giới hạn quyền truy cập.

Restore vào namespace cô lập trước; xác minh key đọc được credentials, revisions,
checksum/manifest, ledger và readiness trước khi cho ghi dữ liệu. Đây là quy
trình vận hành cần nghiệm thu backup/restore riêng, chưa phải tuyên bố đã test
restore hoàn chỉnh. Không trộn key/metadata/staging từ các thời điểm tùy ý.

Dừng demo bằng đúng project với `down` không kèm `--volumes`; không dùng prune.
Regression tạo fixture riêng theo [hướng dẫn kiểm thử](testing.md).
