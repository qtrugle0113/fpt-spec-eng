# Checklist chất lượng yêu cầu UI

**Mục đích**: Review tiêu chuẩn, tập trung mật độ hiển thị và thao tác.
**Ngày tạo**: 2026-11-15
**Đặc tả**: [spec.md](../spec.md)
**Quyền review**: Tạo bởi speckit-checklist, người dùng đã ủy quyền AI tự review. Dấu x chỉ chất lượng yêu cầu, không phải hoàn tất implementation.

## Đầy đủ và rõ ràng

- [x] CHK001 Có xác định cả sáu màn hình và ranh giới giữ nguyên menu/nghiệp vụ không? [Đầy đủ, Spec FR-002]
- [x] CHK002 Palette và quy tắc branding được mô tả nhất quán không? [Rõ ràng, Spec FR-001]
- [x] CHK003 Các loại download/Airflow link và hành vi giữ nguyên có được xác định không? [Đầy đủ, Spec FR-003]
- [x] CHK004 Mật độ hiển thị có tiêu chí viewport, cỡ chữ, chiều cao control cụ thể không? [Đo lường, Spec FR-004]

## Bao phủ và nhất quán

- [x] CHK005 Có yêu cầu cho màn hình hẹp, bảng rộng và tên/ID dài không? [Bao phủ, Spec FR-005, Trường hợp biên]
- [x] CHK006 Có quy định keyboard, focus và tương phản không? [Đầy đủ, Spec FR-006]
- [x] CHK007 Có quy định loading/empty/error/stale/busy và cảnh báo an toàn không? [Bao phủ, Spec FR-006, Trường hợp biên]
- [x] CHK008 Phạm vi admin/admin có giới hạn local và phương án không thay tài khoản cũ không? [Nhất quán, Spec FR-008]
- [x] CHK009 Có phân biệt fixture cô lập, API thật và artifact approval không? [Ràng buộc, Spec FR-009, Giả định]
- [x] CHK010 Mỗi tiêu chí thành công có thể kiểm chứng khách quan không? [Đo lường, Spec SC-001–SC-005]

## Ghi chú

speckit-implement chỉ đọc trạng thái; review được thực hiện riêng trước triển khai theo ủy quyền của người dùng.
