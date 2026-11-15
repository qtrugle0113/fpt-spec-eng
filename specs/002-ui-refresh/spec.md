# Đặc tả: Làm mới giao diện Airflow Automation Tool

**Feature**: `002-ui-refresh` (không tạo hoặc chuyển branch)
**Ngày tạo**: 2026-11-15
**Trạng thái**: Đã triển khai và kiểm chứng source/UI; xem [báo cáo](../../docs/testing/ui-refresh-20261115.md)
**Đầu vào**: Yêu cầu refactor UI và bốn ảnh tham khảo trong hội thoại; người dùng ủy quyền tự quyết và tự review toàn bộ bước trong phạm vi workspace.

## Kịch bản người dùng và kiểm thử

### US1 — Nhìn rõ dữ liệu và thao tác (Ưu tiên P1)

Operator muốn nhận biết ngay bộ lọc, dữ liệu và hành động quan trọng trên cả sáu màn hình, với giao diện sáng và đồng nhất.

**Lý do**: Giảm cuộn do khoảng cách/bố cục dư thừa, giúp dùng ứng dụng hàng ngày.
**Kiểm thử độc lập**: Mở Dashboard, Connections, Table Management, DAG Builder, DAG Monitoring và Settings ở 1366×768; kiểm tra dữ liệu thật và bố cục.

**Tiêu chí chấp nhận**:
1. Khi có dữ liệu, tiêu đề, bộ lọc/thao tác đầu tiên và ít nhất hàng dữ liệu hoặc thẻ tổng quan đầu tiên nằm trong 768px chiều cao. Với Settings, trường cấu hình đầu tiên thay cho hàng dữ liệu.
2. Dashboard hiển thị tám thẻ tổng quan gọn, Recent runs trước các thông tin bổ sung; các khối độc lập tận dụng nhiều cột khi đủ chiều ngang.
3. Menu vẫn gồm Dashboard, Connections, Table Management, DAG Builder, DAG Monitoring, Settings theo đúng thứ tự và route hiện tại.
4. Trên màn hình hẹp 390×844, menu đóng/mở được, thao tác không bị cắt và chỉ vùng bảng được cuộn ngang khi cần.

### US2 — Nhận diện download và mở Airflow (Ưu tiên P1)

Operator muốn tìm được các thao tác tải template và mở Airflow bằng button có nhãn rõ ràng.

**Lý do**: Link chữ hiện tại dễ bị bỏ sót.
**Kiểm thử độc lập**: Tải cả hai template và mở các đích Airflow đang có từ Dashboard, DAG Builder và DAG Monitoring.

**Tiêu chí chấp nhận**:
1. Mọi link tải template và mở Airflow có nền/viền, padding như button và icon phụ trợ, vẫn giữ nhãn tiếng Anh, URL, download và hành vi mở tab hiện tại.
2. Nhận biết được focus khi dùng bàn phím; button chính/phụ, disabled, busy và lỗi nhất quán.
3. Run ID/DAG ID dài vẫn đọc được và không đẩy tràn toàn trang.

### US3 — Đăng nhập demo thuận tiện nếu khả thi (Ưu tiên P3)

Operator muốn dùng admin/admin với Airflow local/demo nếu có thể làm mà không ảnh hưởng tài khoản và dữ liệu hiện hữu.

**Kiểm thử độc lập**: Rà soát bootstrap, phạm vi local và hướng dẫn. Nếu thay đổi thì phải kiểm chứng fresh bootstrap và tính bất biến tài khoản cũ; nếu không đủ điều kiện thì ghi nhận hạn chế và giữ nguyên.

**Tiêu chí chấp nhận**: Không đổi production hoặc ghi đè tài khoản cũ; không thay tài khoản ứng dụng. Đây là yêu cầu có điều kiện, không cản trở US1/US2.

### Trường hợp biên

- Không có dữ liệu, backend/Airflow không khả dụng, dữ liệu stale hoặc thiếu: giữ thông báo đúng thực tế và Retry/Refresh hiện có; không thay bằng dữ liệu mẫu.
- ID, tên file, SQL hoặc log rất dài: xuống dòng hoặc cuộn trong vùng thích hợp; không cắt nội dung bắt buộc.
- Form đang xử lý, review hết hạn hoặc cần authority: giữ nguyên điều kiện disabled, xác nhận và cảnh báo; không thu gọn hoặc che cảnh báo an toàn.
- Bảng nhiều hàng giữ phân trang hiện có; vùng cuộn ngang có thể focus bằng bàn phím. Không bổ sung các vùng cuộn dọc lồng nhau cho bảng thường.

## Yêu cầu

### Yêu cầu giao diện

- **FR-001**: Cả sáu trang dùng nền xám nhạt, sidebar/panel trắng, màu nhấn teal, viền mảnh, bo góc nhẹ và cùng quy tắc typography/spacing; không dùng branding bên thứ ba.
- **FR-002**: Giữ nguyên menu, route, ngôn ngữ tiếng Anh trên UI, luồng nghiệp vụ, API, validation, review và xác nhận hiện có.
- **FR-003**: Mọi thao tác download và chuyển sang Airflow phải có hình thức button và nhãn chỉ rõ mục đích, bảo toàn đích và hành vi.
- **FR-004**: Tối ưu viewport 1366×768 theo US1; gom toolbar và form nhiều cột khi phù hợp; ưu tiên dữ liệu chính trước thông tin bổ sung. Chữ dữ liệu chính trong bảng/form tối thiểu 13px, control cao tối thiểu 36px; nhãn/thông tin phụ có thể dùng 12px.
- **FR-005**: Ở 390×844 không có cuộn ngang toàn trang; bảng được cuộn ngang trong vùng riêng, menu có thể mở/đóng, form chuyển một cột.
- **FR-006**: Control có hover/focus rõ; trạng thái thành công/lỗi/đang chạy có nhãn chữ, không chỉ màu; giữ loading, empty, stale, lỗi, disabled và retry hiện có. Chữ thường đạt tương phản tối thiểu 4.5:1, thành phần focus đạt 3:1 với nền.
- **FR-007**: Không thay model dữ liệu, API, scheduler, ETL hoặc cơ chế cấp quyền; không thêm dependency lớn chỉ phục vụ giao diện.
- **FR-008**: Rà soát khả năng admin/admin chỉ local/demo; chỉ thay nếu không ghi đè tài khoản/dữ liệu và có kiểm chứng. Nếu không phù hợp, ghi rõ hạn chế và giữ nguyên.
- **FR-009**: Ghi lại quyết định, checklist, task, kết quả kiểm chứng trung thực; không kế thừa nghiệm thu/security approval của image cũ cho artifact mới và không triển khai lên demo đang chạy.

## Tiêu chí thành công

- **SC-001**: Sáu trên sáu màn hình có tiêu đề và control/dữ liệu đầu tiên trong viewport 1366×768 theo US1.
- **SC-002**: Không có tràn ngang toàn trang ở cả 1366×768 và 390×844, bao gồm dữ liệu tên/ID dài.
- **SC-003**: Cả hai template tải được; tất cả đường dẫn Airflow giữ URL, tab behavior và được nhận diện bằng button có nhãn.
- **SC-004**: Sáu menu và các luồng hiện có vượt kiểm tra hồi quy phù hợp; lỗi, empty, loading, keyboard và busy được kiểm chứng theo phạm vi thay đổi.
- **SC-005**: Có ảnh kiểm tra trực quan, lệnh kiểm chứng/kết quả và kết luận tài khoản demo; mọi giới hạn được công bố rõ.

## Giả định và phụ thuộc

- Dùng workflow/code hiện có làm nguồn bố cục; ảnh chỉ gợi ý màu sắc, mật độ và bề mặt. Không sao chép hệ thống trong ảnh; phù hợp nguyên tắc II.
- Chỉ sửa workspace, không commit/push/deploy, không can thiệp volume và không ghi dữ liệu nghiệp vụ để phục vụ kiểm thử giao diện.
- Dữ liệu thật phụ thuộc stack local hiện có. Fixture chỉ được dùng cho kiểm thử cô lập và phải phân biệt với bằng chứng tích hợp.
- Không bổ sung link hướng dẫn mới nếu sản phẩm hiện không có đích tải tương ứng.

## Làm rõ

### Phiên ngày 2026-11-15

- Người dùng ủy quyền tự quyết: giữ UI tiếng Anh theo constitution, tài liệu tiếng Việt; không có câu hỏi gửi người dùng.
- Dữ liệu phụ vẫn hiển thị; sắp xếp lại, dùng grid và spacing gọn thay vì giấu cảnh báo/review trong accordion.
- Phạm vi nghiệm thu là thay đổi giao diện và hồi quy liên quan, không tuyên bố nghiệm thu lại toàn bộ baseline hoặc production.
