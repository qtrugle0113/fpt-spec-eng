# Quản lý bảng từ workbook

Mở **Table Management**, tải **Table Definition template** và giữ nguyên schema 1.0:
ba sheet `Instructions`, `Tables`, `Columns`, đúng thứ tự và header. Version trong
`Instructions!B1` phải là chuỗi `1.0`. Có thể dùng ngay
`samples/definitions/Table Definition.sample.xlsx` với connection `pg_etl` đã seed.

Upload workbook `.xlsx` tối đa 10 MiB, chọn connection đã Test Connection thành
công rồi bấm **Validate workbook**. Upload được lưu bằng khóa ngẫu nhiên, không
dùng tên file làm đường dẫn. Worker kiểm tra toàn workbook trước khi công bố các
table definition. Workbook lỗi không tạo bảng đích; **View validation issues** cho
biết sheet, row, column và thông báo English an toàn, tối đa 200 issue mỗi trang.
Sửa file rồi upload lại để giữ được lịch sử bản cũ.

Kiểm tra **Review tables**, độ dài/precision/scale, nullable, thứ tự PK ghép và
default trước khi xác nhận. `No default` khác default JSON `null`; số decimal và
ngày/giờ dùng JSON string để giữ chính xác. Không nhập biểu thức SQL vào default.
DDL dùng identifier được kiểm tra và SQLAlchemy literal, không chạy SQL do người
dùng cung cấp. Preview chỉ đọc metadata đích. Confirmation có hạn 10 phút và gắn
với checksum, definition, revision/identity đích cùng tình trạng tồn tại của bảng.
Đổi dependency phải preview/validate lại, không dùng confirmation cũ.

**Confirm and create tables** tạo operation bền vững và job theo từng bảng.
`CREATED` nghĩa là đã nhận được xác nhận hoàn thành DDL; `ALREADY_EXISTS` giữ
nguyên bảng hiện hữu, không ALTER/DROP hoặc sửa dữ liệu. `FAILED` hiển thị lỗi an
toàn. Một job có thể `PARTIALLY_SUCCEEDED`: xem từng bảng và SQL/time đã lưu,
không xem job này là thành công toàn bộ.

MySQL có implicit DDL commit. Nếu mất phản hồi sau khi gửi DDL, kết quả là
`UNKNOWN`, operation là `NEEDS_RECONCILIATION`. Không retry bằng key mới, không
xóa bảng để chạy lại và không nhận ownership chỉ vì schema đang khớp. Replay cùng
Idempotency-Key trả lại operation cũ. Worker mất lease không được thực hiện lại
DDL; dispatch đang dở được cách ly để đối chiếu. Việc xác minh live schema chỉ mô
tả schema hiện tại, không chứng minh ai đã tạo bảng hoặc thay thế bằng chứng commit.

**Workbook uploads** và **Table creation jobs** đọc từ DB, có phân trang và bộ lọc
ngày UTC/status/state. Mở browser mới vẫn xem được lịch sử, không cần nhớ ID từ
phiên trước. Trong **View table details**, **Stored definition** tách biệt với
**Live database verification**: `VERIFIED`, `DRIFTED`, `UNAVAILABLE` hoặc
`NOT_CREATED`. Nếu DB không truy cập được, định nghĩa/lịch sử vẫn được trả về,
`actual_columns` là null, không lấy metadata lưu sẵn giả làm introspection.

Nếu browser mất kết nối trong lúc submit/poll, kiểm tra operation/job hiện tại
trước khi gửi yêu cầu mới. Đóng browser không hủy operation đã được nhận.

## Kiểm thử local cô lập

`tests/tools/run_metadata_foundation.py` nhận image ID cụ thể, tạo PostgreSQL/MySQL
tmpfs trong network riêng, không publish port hay gắn volume/secrets hiện hữu.
Các module Table là `tests.api.test_tables`, `tests.integration.test_table_ddl`,
`tests.unit.test_table_workbook`. Evidence ở `docs/testing/resume-20261109/` gồm
fixture results và log; các lượt lỗi được giữ riêng.

Chuẩn bị workbook công khai cho browser bằng
`python tests/tools/prepare_table_fixtures.py --image <reviewed-backend-tests-id>`.
Fixture PostgreSQL giữ nguyên sample của repo; fixture MySQL chỉ đổi connection,
schema và prefix tên bảng để tránh trùng bảng mẫu seed có cấu trúc khác.

Chạy `tests/tools/run_connections_e2e.py --suite tables` với các tham số image và
`--evidence-dir` đã review. Driver dùng production Compose, xóa port mappings,
tạo network/volume theo project ngẫu nhiên và chỉ cleanup đúng tài nguyên vừa
tạo. Không dùng `down --volumes` trên project làm việc của người vận hành. Image
mới có HIGH/CRITICAL phải được owner review đúng ID theo gate của repo trước mốc
E2E; việc build xong hoặc dependency không đổi không tự cấp ngoại lệ mới.
