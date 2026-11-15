# Đặc tả: Tên Definition thống nhất và tài khoản Airflow local

**Ngày**: 2026-11-15 | **Feature**:003-definition-names-admin | **Trạng thái**: Đã triển khai và kiểm chứng cả hai mục tiêu; [báo cáo](../../docs/testing/definition-admin-20261115.md)
**Nguồn**: Yêu cầu đính kèm; người dùng ủy quyền tự quyết, tạo/cập nhật admin trên demo và fresh stack, restart/recreate service cần thiết. Giữ thay đổi UI chưa commit từ feature002.

## Kịch bản và chấp nhận

### US1 — Một tên cho một tài liệu (P1)

Operator dùng ETL Definition hoặc Table Definition xuyên suốt tải mẫu, upload, validate, review và history.

1. Tất cả nội dung hướng tới người dùng gọi đúng ETL Definition/Table Definition; không dùng workbook thay tên hai tài liệu.
2. Template chỉ file mẫu tải về; label input là ETL Definition file (.xlsx)/Table Definition file (.xlsx).
3. Nhãn, hướng dẫn, thông báo backend, accessibility label, Excel Instructions và test nhất quán; không đổi menu, API, mã lỗi, identifier hoặc schema Excel.

**Kiểm thử độc lập**: Rà chuỗi, tải hai template, xem trang desktop/mobile và thao tác upload/validate trên stack cô lập.

### US2 — Đăng nhập Airflow demo (P1)

Operator đăng nhập admin/admin có quyền quản trị trên demo hiện hữu và stack local mới.

1. Demo hiện hữu đăng nhập giao diện thật, quyền admin thật; service account và user khác giữ nguyên, các dữ liệu/volume/DAG/run không mất.
2. Restart service liên quan vẫn đăng nhập được; bootstrap bình thường không reset password tùy chỉnh.
3. Fresh local/demo cô lập khởi tạo admin/admin; cấu hình này không áp dụng cho môi trường ngoài local/demo loopback.
4. Có backup/restore và hướng dẫn; không in secret cũ, không tắt auth, không sửa trực tiếp metadata DB, không thay service credential.

**Kiểm thử độc lập**: Browser login và xác minh quyền qua API/UI; kiểm service auth, ID dữ liệu/volume trước–sau, restart, fresh bootstrap thật và unit test idempotence/opt-out.

## Yêu cầu

- **FR-001**: Thống nhất mọi chuỗi UI ETL/Table, phân biệt template và file (.xlsx), giữ tiếng Anh.
- **FR-002**: Đồng bộ thông báo backend và Excel Instructions, giữ nguyên identifier, lỗi, schema và dữ liệu đã lưu; nội dung lịch sử bất biến không bị sửa.
- **FR-003**: Đồng bộ tài liệu vận hành tiếng Việt và test liên quan, bảo toàn bố cục hiện tại.
- **FR-004**: Tạo/cập nhật admin/admin với quyền admin trên demo local đang có; có sao lưu và restore, giữ service account/user khác.
- **FR-005**: Fresh local/demo có admin/admin qua chế độ local rõ ràng; chế độ ngoài local không tạo admin password này.
- **FR-006**: Restart giữ cấu hình; init không tự reset mật khẩu tùy chỉnh; chỉ lệnh cập nhật được yêu cầu rõ mới đặt lại admin/admin.
- **FR-007**: Không xóa/reinitialize volume/database/DAG/run/upload/dữ liệu ETL; không credential trong source DAG/API response/log/XCom; không tắt xác thực hoặc cho mọi user quyền admin.
- **FR-008**: Có bằng chứng login/quyền thật, backend service auth, preservation, restart và fresh isolation; không thay bằng mock/config-only; không commit/push/production.

## Thành công

- **SC-001**: Rà chuỗi user-facing không còn workbook thay tên Definition; typecheck/build và kiểm tra liên quan đạt, label không bị cắt.
- **SC-002**: Hai môi trường demo/fresh đều login admin/admin và có quyền quản trị; service auth tiếp tục hoạt động.
- **SC-003**: Restart không đổi kết quả login; unit test chứng minh init giữ custom password và opt-out không tạo weak default.
- **SC-004**: Volume identity và tập ID dữ liệu/DAG/run trước–sau demo không mất; có backup/restore có thể kiểm chứng trên fixture.

## Biên và giả định

- Admin có sẵn: lệnh migration được phép đặt lại password/quyền; bootstrap thường giữ nguyên. User/service khác không đổi.
- Secret mất, JSON lỗi, project không khớp, port không loopback: dừng, không tự tạo lại secret hoặc đoán project.
- Migration lỗi: giữ backup, có hướng khôi phục; kiểm trước khi recreate để tránh bỏ lại cấu hình không nhất quán.
- Giữ nguyên API scope `workbook`, message_key và mã WORKBOOK_* vì là hợp đồng kỹ thuật; chỉ đổi văn bản người dùng.
- Bằng chứng lịch sử, spec001/002 và báo cáo cũ giữ nguyên; tài liệu hiện hành được đồng bộ. Template Version/header/sheet giữ nguyên.

## Làm rõ — 2026-11-15

Không hỏi người dùng theo ủy quyền. Root Compose là cấu hình local loopback; helper library mặc định không tạo admin khi không opt-in. Demo hiện hữu được cập nhật secret file và cấu hình user qua đường chính thức SimpleAuthManager; không dùng SQL metadata. Kiểm thử source trên image dependency hiện có được ghi đúng phạm vi, không kế thừa approval cho image mới.
