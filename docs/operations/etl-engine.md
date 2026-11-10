# Chạy và kiểm chứng ETL engine

## Trạng thái hiện hành

Engine đã có đường chạy standalone trên database thật: PostgreSQL→PostgreSQL,
PostgreSQL→MySQL, MySQL→PostgreSQL, MySQL→MySQL; CSV/TXT→hai loại database.
Đây là kiểm chứng Phase5, chưa phải bằng chứng DAG/UI/Airflow hoàn chỉnh.
Xem [checkpoint engine](../testing/phase5-engine-report.md) và JSON/logs tại
`docs/testing/resume-20261110/`. T014_FULL vẫn BLOCKED.

## Đường chạy và bảo vệ dữ liệu

`aat_etl.engine.execute_database` nhận config typed, immutable connection engines,
schema/physical-identity pins, UUID run/dataset và binding SHA đã được caller xác minh.
`execute_file` nhận thêm `FileReference` của upload/parser revision bất biến, không
nhận filename người dùng làm đường dẫn. Các hàm này là giao diện nội bộ, không phải
public API cấp quyền thay thế dữ liệu.

DB source dùng một read-only snapshot, staging source COMPLETE trên đĩa, đóng source
session, rồi mapping và full target-typed validation trước load. File source phải
đúng checksum/parser và hợp lệ toàn bộ format trước mọi target write. APPEND/UPSERT
file chuyển kiểu theo từng row/batch nên lỗi type muộn có thể giữ batch trước;
UPSERT vẫn kiểm toàn bộ chosen keys/collation bằng scratch trước target write.
FULL_REFRESH luôn hoàn tất mapped staging trước admission.

- APPEND commit từng batch cùng marker. Retry cùng run/dataset bỏ qua marker đúng
  binding/payload; run mới có thể chèn trùng khi target không có unique constraint.
- UPSERT PostgreSQL dùng đúng chosen conflict key; MySQL dùng UPDATE JOIN rồi INSERT
  những chosen keys chưa có. Unique phụ lỗi thì rollback batch; không cập nhật nhầm row.
  Chỉ mapped non-key columns được update, key-only mapping không ghi đè cột khác.
- FULL_REFRESH cần `AdmissionAdapter` nối repository app DB thật, target native lock,
  scope/run/dataset/binding đúng và admission đã commit được đọc lại. DELETE, INSERT,
  kiểm row count và final marker nằm trong một target transaction. Empty replacement
  cần xác nhận allow_empty riêng. Inbound FK/trigger hoặc thiếu quyền kiểm tra bị chặn.

Final marker được kiểm trước extraction khi gọi lại run đã commit. Commit mất phản
hồi phải giữ staging và đối soát dưới native lock mới sau khi chứng minh session cũ
đã kết thúc. Không dùng heartbeat stale làm bằng chứng rollback hoặc giành lại khóa.
Không có original prepared dataset thì partial run không được re-extract source mới.
Lỗi app metric projection sau target commit không cho phép replay dữ liệu đích.

## Đĩa, bộ nhớ và cleanup

Root volume hiện hữu của Compose là `/data/staging`; worker dùng `AAT_STAGING_ROOT`
để override khi có cấu hình đã kiểm. Path con chỉ gồm SHA256 DAG/run và dataset UUID.
Không dùng XCom hoặc tmpfs chứa dataset. Test DB tạm có thể dùng anonymous disk volumes
để kiểm scratch; dataset của test nằm trên filesystem đĩa của runner.

Quota10GiB/run và20GiB/global tính cả ACTIVE/PROTECTED/temp artifacts, giữ1GiB free.
Mapped/raw source cùng tính vào quota run. MySQL scratch dùng charge bảo thủ và
giới hạn5triệu row; PG còn kiểm allocation relation/index thực. Budget RSS512MiB dùng
supervisor Linux, abort sớm với32MiB headroom. Stress lớn có gate riêng T095/T147;
không suy từ test nhỏ thành nghiệm thu stress hoặc LocalExecutor.

GC staging cần terminal + đối soát xong + session writer cũ đã kết thúc + hết retention
(mặc định7ngày). Protected/commit unknown không bị xóa để nhường quota. Source blob
không còn reference chỉ được thu sau30ngày; giữ metadata/checksum/parser history.
Target commit ledger chưa có automatic purge; giữ ít nhất30ngày và giữ lâu hơn khi
còn recovery/dataset reference. Worker maintenance chạy riêng, không làm hết lease
của Operation đã claim hoặc ngừng heartbeat khi target chậm.

## Quyền và vận hành local

Target cần quyền đọc/ghi theo policy và quyền tạo support objects có consent. MySQL
cần CREATE TEMPORARY TABLES cho InnoDB scratch; FULL_REFRESH cần quyền TRIGGER để
không nhầm metadata trigger bị ẩn với việc không có trigger. Bootstrap source chỉ
cấp các quyền đó trong sample database `etl_test.*`, chưa áp dụng vào volume hiện hữu.
Không dùng PROCESS/root ở runtime để đo scratch; quyền root chỉ dùng probe trong
fixture tổng hợp khi kiểm chứng charge so với allocation thực.

Các callback `on_prepared` và `project` để runtime caller lưu tham chiếu/metrics bền.
Caller DAG/bind phải chốt đúng revisions, dataset/binding UUID/SHA và persisted
authority trước execution; không lấy các primitive standalone này thay quyền runtime.
Không tự xóa protected staging, đổi dataset sau partial commit hoặc tạo run ID mới để
né recovery. Bản tích hợp Airflow, giao diện và hướng dẫn startup cuối vẫn còn các
gate sau; hiện chưa có tuyên bố MVP hoàn chỉnh.
