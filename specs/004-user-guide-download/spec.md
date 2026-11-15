# Đặc tả: Tải User Guide từ giao diện

**Ngày tạo**: 2026-11-15 · **Trạng thái**: Sẵn sàng triển khai
**Thư mục tính năng**: `specs/004-user-guide-download`
**Đầu vào**: “muốn bổ sung button tải user guide trên UI; dùng speckit bổ sung cho tôi”.

## Tình huống người dùng và nghiệm thu

### US1 — Tải hướng dẫn ngay trên ứng dụng (P1)

Người vận hành muốn tải hướng dẫn tiếng Việt từ bất kỳ màn hình nào, không phải tìm file trong repo.

**Lý do ưu tiên**: tài liệu đã có; cần đưa tới đúng nơi người dùng làm việc.
**Kiểm thử độc lập**: mở sáu màn hình, bấm Download User Guide, mở file đã tải khi tắt mạng.

1. Khi đang ở một trong sáu màn hình, người dùng nhìn thấy nút **Download User Guide** trên thanh trên cùng mà không phải mở menu hoặc cuộn trang.
2. Khi bấm nút, trình duyệt tải file `Airflow-Automation-Tool-Huong-dan-su-dung.html`; màn hình hiện tại, bộ lọc và dữ liệu đang nhập được giữ nguyên.
3. Khi mở file đã tải không có mạng, nội dung tiếng Việt, 12 ảnh minh họa và mục lục vẫn sử dụng được.
4. Khi dùng màn hình hẹp hoặc bàn phím, nút vẫn nhìn thấy, có focus rõ và kích hoạt được bằng Enter.

### Trường hợp biên

- Backend/Airflow không hoạt động: vẫn tải được tài liệu nếu giao diện còn truy cập được.
- Tải lại nhiều lần: nhận cùng tài liệu; không tạo/sửa dữ liệu ứng dụng.
- Màn hình rộng 320px: thanh trên cùng xuống dòng nếu cần, không gây cuộn ngang toàn trang.
- Bản phát hành thiếu tài liệu hoặc khác bản hướng dẫn gốc: kiểm tra đóng gói phải thất bại trước bàn giao.

## Yêu cầu

### Yêu cầu chức năng

- **FR-001**: Cả sáu màn hình hiện tại đều có nút Download User Guide, theo cùng kiểu nút tải file đang dùng.
- **FR-002**: Nút tải bản HTML tiếng Việt hiện có, giữ nguyên tên file dễ nhận biết và không chuyển trang ứng dụng.
- **FR-003**: File nhận được bao gồm toàn bộ ảnh, đọc được offline và trùng nội dung bản hướng dẫn gốc.
- **FR-004**: Có thể tải bằng chuột, cảm ứng hoặc bàn phím, trên desktop và màn hình hẹp; không tràn ngang toàn trang do nút mới.
- **FR-005**: Tài liệu đi cùng bản giao diện đã đóng gói, có thể tải khi backend/Airflow không sẵn sàng.
- **FR-006**: Giữ nguyên sáu menu, chức năng và dữ liệu hiện có; thao tác tải chỉ đọc tài liệu.

### Đối tượng chính

**User Guide**: một tài liệu HTML tiếng Việt có sẵn 16 mục, 12 ảnh nhúng; tên file giữ nguyên bản đã bàn giao. Không có thực thể nghiệp vụ hoặc lịch sử tải mới.

## Tiêu chí thành công

- **SC-001**: Tải được bằng một lần bấm từ cả 6/6 màn hình.
- **SC-002**: File tải về có nội dung khớp bản gốc, mở đủ 16 mục và 12 ảnh khi offline.
- **SC-003**: Nút xuất hiện trong vùng nhìn ban đầu ở desktop 1366px và mobile 390px; kiểm tra thêm biên 320px; điều khiển được bằng bàn phím.
- **SC-004**: Tải thành công khi backend không sẵn sàng; không phát sinh yêu cầu ghi dữ liệu.

## Giả định và phạm vi

- Dùng bản HTML đã tạo theo yêu cầu trước, không tạo thêm PPT hoặc thay nội dung hướng dẫn trong tính năng này.
- Label trên UI bằng tiếng Anh theo Constitution; nội dung hướng dẫn vẫn bằng tiếng Việt theo yêu cầu người dùng.
- Vị trí mặc định là thanh Workspace, tách khỏi danh sách menu.
- Không thêm API, xác thực, thống kê lượt tải hoặc dependency.
- Không có điểm mơ hồ cần hỏi lại; không thay đổi Constitution.
