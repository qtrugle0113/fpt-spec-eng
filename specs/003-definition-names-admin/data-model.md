# Dữ liệu và trạng thái

Không migration/schema/API mới. Password dictionary SimpleAuthManager thêm khóa admin; khóa service/operator và user khác giữ nguyên. Danh sách role thêm admin:admin, không bật all_admins. Backup giữ bytes file gốc và cấu hình Compose, permission hạn chế. Lệnh reset/restore chỉ dùng local; bootstrap fresh có opt-in, lần sau chỉ kiểm secret/key như hiện tại.

Chuỗi Definition không đổi scope workbook, message_key, mã lỗi, SHA256, định dạng Excel hoặc entity đã lưu.
