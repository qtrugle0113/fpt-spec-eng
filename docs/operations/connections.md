# Vận hành Connections

## Trạng thái kiểm chứng

Backend Connections đã kiểm với PostgreSQL17.11/MySQL8.4.13 thật: 23/23 tests gồm
HTTP, codec, policy và schema. Frontend đã nối API, build/typecheck PASS và E2E6/6PASS
desktop/mobile trên artifacts đã scan/review. Đã kiểm keyboard/focus, hủy/xác nhận
xóa và private proxy. Đây là nghiệm thu Connections, không phải MVP. Chi tiết tại báo cáo Phase3.

## Thao tác trên giao diện

1. Mở **Connections**, chọn **Add connection**. Điền code, name, database type,
   host, port, database name, schema nếu PostgreSQL, username và password.
2. **Save connection** chỉ lưu metadata mã hóa, chưa chứng minh DB kết nối được.
   Chọn bản ghi rồi **Test connection** để kiểm DB thật. Status và thời điểm chỉ
   phản ánh revision đã kiểm; thành công cũ không đảm bảo DB vẫn đang sẵn sàng.
3. Tìm theo code/name/host hoặc lọc database/status. **Refresh details** lấy lại
   ETag và dependencies trước khi sửa một bản ghi đã được thay đổi ở nơi khác.
4. **Edit connection** không trả password cũ về browser. Bỏ trống giữ credential
   cũ; nhập password mới tạo secret/revision mới. Form không đưa password vào
   Query cache, và xóa password khỏi form sau mỗi lần gửi lưu.
5. Xem **Dependencies** trước sửa/xóa. Code và thao tác xóa bị chặn khi còn tham
   chiếu. Thay host/port/database/schema/type bị chặn khi có binding active hoặc
   chưa đối soát. Đổi endpoint/credential làm validation/quyền cho công việc mới
   mất hiệu lực; binding đang chạy giữ revision/secret reference cũ.
6. **Delete connection** yêu cầu xác nhận trên đúng connection. Metadata được ẩn
   khỏi workspace bằng tombstone, lịch sử revision được giữ; code lịch sử vẫn
   chịu unique constraint. Không thao tác xóa bảng hoặc dữ liệu đích.

## Mạng và thời hạn kết nối

Mặc định chỉ `postgres,mysql` được phép. Operator có thể đặt biến môi trường
`AAT_DB_ALLOWED_HOSTS` thành danh sách hostname/IP tin cậy phân cách dấu phẩy trước
khi khởi tạo services; Compose truyền cấu hình này cho backend và worker. Không
dùng URL/path làm host. Loopback, link-local, multicast, địa chỉ không xác định
hoặc reserved bị từ chối; không dùng quyền local làm quyền triển khai public.

Adapter resolve tối đa3giây, kiểm toàn bộ địa chỉ rồi ghim một IP cho kết nối,
không dùng hostname user nhập làm identity. PostgreSQL dùng NullPool, connect10giây
và statement5giây; MySQL connect10giây, read/write5giây. Tests có handshake bị giữ
thật để kiểm timeout dưới30giây, không dùng mock để thay bằng chứng DB thật.

PG dùng `hostaddr` cùng `host` theo [libpq17](https://www.postgresql.org/docs/17/libpq-connect.html).
Fingerprint PG được xác minh từ địa chỉ/port server và database OID trả về bởi server;
native target lock ở engine vẫn là thẩm quyền cuối cùng cho alias/concurrency.
MySQL dùng [server_uuid](https://dev.mysql.com/doc/refman/8.4/en/replication-options.html)
trả về từ server để fingerprint. Không dùng Connection Code làm identity vật lý.

## Xử lý lỗi và lịch sử

- `412`: revision đã đổi; lấy lại details, đối chiếu thay đổi rồi gửi lại. Không
  tự ghi đè bằng ETag mới khi người dùng chưa xem thay đổi.
- `409`: code trùng/dependency/run active; xem dependencies và trạng thái đối soát.
- Test `FAILED`: kiểm code lỗi và thông báo an toàn; không có raw DSN/password.
  MySQL account bị hạn chế có thể nhận permission denied trước khi server tiết lộ
  database tồn tại; không suy trường hợp đó thành database missing.
- Lỗi chưa phân loại được trả `UNKNOWN_DATABASE_ERROR`, không giả định chắc chắn
  là authentication hoặc network. Không tự retry thao tác có side effect chưa rõ.
- Thiếu key: khôi phục đúng key volume/backup gốc. Codec không tự sinh key thay thế.
  Primitive rotation chỉ tạo token mới bằng current key đã được owner cấp sẵn;
  không mutate ciphertext lịch sử hoặc xóa key còn revision/binding tham chiếu.

## Kiểm thử và codegen

Drivers dùng DB/container/network riêng, không migration/reset volumes đang dùng.
Lệnh kiểm API/adapters/schema hiện hành có trong
[báo cáo Phase3](../testing/phase3-connections-report.md). Codegen types từ canonical
OpenAPI bằng `tests/tools/generate_frontend_api.py --image <Airflow-ID-đã-kiểm>`;
không sửa `frontend/src/lib/api.generated.ts` bằng tay.
