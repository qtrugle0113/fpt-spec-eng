# Hợp đồng giao diện

## Điều hướng

Giữ `/`, `/connections`, `/tables`, `/dag-builder`, `/monitoring`, `/settings`, nhãn/thứ tự menu, search và toggle mobile. Active có nền teal và chữ đậm; giữ aria-current từ router.

## Link thao tác

Giữ anchor semantics, href, target, rel, download và nhãn truy cập. Icon trang trí có aria-hidden. Không tạo link trống cho URL thiếu; giữ tham chiếu và thông báo Not available. Template giữ `/api/v1/templates/table-definition` và `/api/v1/templates/etl-definition`.

## Bố cục và control

Chữ bảng>=13px, control>=36px; focus ring rõ trên trắng/teal. Bảng overflow-x, tabIndex=0, không giới hạn chiều cao bảng thường. Primary teal đậm/chữ trắng, secondary viền teal, destructive đỏ. Hover không đổi kích thước.

## Dữ liệu và hành vi

Không đổi request/response, query key, polling, URL parameters, tải file, permission, validation, busy/disabled, dialog hoặc confirmation. Cảnh báo cần review luôn hiện trực tiếp. Metrics null giữ Not available; legend chart khớp màu và có exact counts.
