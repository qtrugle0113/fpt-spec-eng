# Kế hoạch: Làm mới giao diện

**Feature**: `002-ui-refresh` | **Ngày**: 2026-11-15 | **Đặc tả**: [spec.md](spec.md)

## Tổng quan

Giữ workflow thật và sáu menu; chuẩn hóa CSS thành theme trắng/xám nhạt/teal, link dạng button, bảng gọn và bố cục nhiều cột. Dashboard ưu tiên metrics và Recent runs, tám thẻ một hàng khi đủ1280px, bốn cột tablet. Table Management đặt wizard gọn phía trên, hai lịch sử upload/job cạnh nhau bên dưới. DAG Builder có hai cột: định nghĩa kèm deployment và lịch sử. Không che cảnh báo, review hoặc authority. Settings chia nhóm trường và thông tin ứng dụng.

## Bối cảnh kỹ thuật

- TypeScript5.9.3, React19.2.0, React Router7.18.5, Vite7.3.7, Tailwind4.1.18; giữ dependency/lock.
- TanStack Query5.90.10, React Hook Form7.66.0; không đổi query key, mutation, validation hay API.
- Node yêu cầu22.23.4; host24.22.1. Ưu tiên chuẩn bị đúng Node cho build; ghi runtime thực đo.
- Sáu trang web local loopback; viewport1366×768 và390×844.
- Backend demo28000, Airflow28080; preview riêng proxy `/api` đến backend loopback. Không thay stack/volumes/secrets hiện hữu.
- Repo chưa có lint script/config: typecheck, build, Playwright và `git diff --check`; không tuyên bố lint riêng.
- Không đổi storage, API contracts, schema Excel, ETL, staging, retry/rerun hoặc scheduler. PostgreSQL/MySQL/Airflow hiện hữu chỉ qua API cho kiểm chứng UI đọc dữ liệu/tải template.

## Đánh giá constitution trước và sau thiết kế

| Nguyên tắc | Bằng chứng thiết kế | Kết luận |
| --- | --- | --- |
| I — ngôn ngữ | Markdown tiếng Việt, UI tiếng Anh | Đạt |
| II — nhận diện | Giữ tên ứng dụng; ảnh chỉ gợi ý palette/mật độ, không sao chép branding | Đạt |
| III — Spec Kit | Feature riêng, FR/US/task/kiểm thử truy vết | Đạt |
| IV — sản phẩm thật | API thật khi kiểm tra tích hợp; fixture lỗi cô lập ghi riêng | Đạt theo thiết kế, chờ kiểm chứng |
| V — metadata | Không sửa Excel/validation; giữ review workbook/SQL | Đạt |
| VI — dữ liệu/secret | Không ghi dữ liệu/credentials/authority, không che xác nhận | Đạt |
| VII — staging/bộ nhớ | Không đổi ETL/tài nguyên | Không áp dụng với thay đổi UI |
| VIII — Airflow | Giữ URL/public API và trạng thái thật | Đạt |
| IX — runtime/container | Build/preview riêng, không deploy image/volume demo | Đạt trong phạm vi source/preview |
| X — kiểm thử/bảo mật | Typecheck/build, viewport/keyboard/download/URL, không kế thừa approval image cũ | Đạt theo thiết kế, chờ kiểm chứng |
| XI — tài liệu | Quickstart, nghiên cứu, checklist, tasks, báo cáo kiểm chứng | Đạt |
| XII — giai đoạn | Workflow baseline đã có, UI là đợt riêng | Đạt |

Không sửa constitution hoặc phát sinh ngoại lệ. Nghiệm thu UI không đồng nghĩa image mới đã phê duyệt hay production-ready.

## Pha 0 — Nghiên cứu

Đã đọc code và giao agent nghiên cứu chỉ đọc theo skill plan. Xem [research.md](research.md). Không còn ẩn số cần hỏi.

## Pha 1 — Thiết kế và hợp đồng

- `frontend/src/app/styles.css`: token, layout responsive, control/table/feedback dùng chung.
- `frontend/src/components/ActionLink.tsx`: anchor có icon, style button; giữ href/target/rel/download.
- `frontend/src/app/App.tsx`: sidebar/dấu menu; giữ nội dung, route, search.
- `frontend/src/pages/`: grid theo thứ tự đọc, không sửa side effect.
- `frontend/src/features/`: template button, form gọn, chart teal và legend tương ứng.
- `frontend/scripts/verify-ui.cjs`: preview proxy riêng, API thật, sáu route/hai viewport, keyboard, download/popup; lưu ảnh/kết quả.

Hợp đồng tại [contracts/ui.md](contracts/ui.md), mô hình tại [data-model.md](data-model.md), kiểm chứng tại [quickstart.md](quickstart.md).

## Chiến lược kiểm chứng

Kiểm tra API baseline; cài dependency đúng lock, typecheck/build. Script đọc dữ liệu thật, tải template, mở Airflow; không trigger DAG/tạo bảng để chứng minh CSS. Fixture lỗi/empty/loading cô lập ghi riêng. Rà soát ảnh desktop/mobile, sửa lỗi phát hiện. Báo rõ giới hạn nếu thiếu công cụ.

## Độ phức tạp

Không thêm dependency, persistence, microservice hoặc framework. Đánh giá sau thiết kế: không xung đột constitution.
