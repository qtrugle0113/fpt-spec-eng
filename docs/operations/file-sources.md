# Vận hành nguồn file CSV/TXT

Trong DAG Builder, dùng File Sources để upload CSV/TXT cùng cấu hình parser rõ
ràng: encoding, delimiter, header, quote, escape và NULL representation. Encoding
mặc định UTF-8. File không header dùng `column_1`, `column_2`…; các giá trị vẫn là
chuỗi hoặc NULL, không tự suy đoán số, ngày hay boolean.

NULL chỉ xuất hiện khi token **không được quote** khớp chính xác marker, mặc định
`\N`. Token `"\N"` là chuỗi; chuỗi rỗng, `0`, `false` giữ nguyên. BOM đầu header
được bỏ. Với file không header, UTF-8 giữ U+FEFF đầu dữ liệu; chọn UTF-8-SIG nếu
muốn codec bỏ BOM. Multiline trong quote giữ nội dung và vị trí dòng thật.

## Upload và vòng đời

Giới hạn file là 256 MiB, record tối đa 1 MiB và buffer parser tối đa 8 MiB.
Reverse proxy cho phép thêm phần multipart framing; API vẫn kiểm tra đúng giới
hạn file. Upload stream tính SHA-256, publish atomically và tạo parser revision
bất biến. File trùng tên có reference riêng; tên file không phải định danh.
Không dùng storage key hay đường dẫn nội bộ làm thông tin người dùng.

File mới chưa được sử dụng có hạn 30 ngày. Definition/binding còn tham chiếu ngăn
collection; không xóa nguồn đang dùng để vượt lỗi. Nguồn hết hạn, thiếu hoặc đổi
checksum phải báo lỗi, không được coi là dataset rỗng. Seed hiện hữu giữ storage
layout và chính sách hết hạn đã có.

Nếu phản hồi báo `UPLOAD_PUBLICATION_UNCERTAIN`, kiểm tra danh sách file trước
khi thử lại: database có thể đã commit dù phản hồi bị mất. Hệ thống giữ blob hoàn
chỉnh khi chưa chứng minh được rollback; không tự xóa dữ liệu để xử lý lỗi mạng.

## Preview, xác nhận và chọn nguồn

Preview chỉ đọc tối đa 100 record; không thay thế full validation. Thay parser
trên form rồi Preview để xem cấu hình dự kiến, sau đó xác nhận lưu parser. Chỉ
chọn nguồn sau khi full validation thành công cho đúng file SHA/parser revision.
Form có thay đổi chưa lưu phải chặn Validate và Select để tránh chọn cấu hình cũ.

PATCH parser dùng ETag/If-Match. Lỗi 412 yêu cầu tải lại trạng thái trước khi xác
nhận; lỗi 409 khi binding đang chạy hoặc chưa reconcile yêu cầu xử lý trạng thái
runtime trước. Thay parser tạo revision mới, giữ revision binding cũ, đồng thời
invalidate validation/authorization phụ thuộc; không tự chuyển nguồn đã chọn.

## Kiểm chứng

Source tests dùng PostgreSQL/MySQL thật và filesystem cô lập, có upload ngắt kết
nối HTTP, file vượt 256 MiB, checksum sai, parser stale, mất phản hồi sau commit,
collision partial file, retention và lỗi record ngoài phạm vi preview.

Browser fixture chạy trên production Compose với image ID cố định, không publish
port hoặc mount dữ liệu/secrets hiện hữu. Bộ Files tiếp tục recreate backend và
worker, giữ volume của chính fixture, refresh proxy rồi kiểm tra lại metadata,
preview và full validation. Kết quả chỉ PASS sau cả lượt đầu và lượt persistence;
trước khi chạy phải ghi NOT_RUN. Xem checkpoint Phase5 để biết bằng chứng hiện tại.
