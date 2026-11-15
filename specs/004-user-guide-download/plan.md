# Kế hoạch: Tải User Guide

**Ngày**: 2026-11-15 · **Đặc tả**: [spec.md](spec.md)

## Tổng quan

Dùng ActionLink có download trong workspace-bar dùng chung. Phục vụ HTML từ public để tải không phụ thuộc API; builder cập nhật cả artifact bàn giao và bản public. So sánh bytes/hash để phát hiện tài liệu cũ hoặc SPA fallback.

## Bối cảnh kỹ thuật

- TypeScript, React 19.2.0, Vite 7.3.7, Node 22.23.4, ActionLink hiện có; không thêm dependency.
- Lưu trữ: HTML khoảng 646KB, ảnh data URI; không có schema, migration hoặc API mới.
- Nền tảng: desktop/mobile, frontend Dockerfile → Vite dist → Nginx hiện có.
- Kiểm thử: TypeScript/build, Playwright HTTP/download thật trên production preview, mở file offline; không mock endpoint download.
- Mục tiêu: tải một lần bấm từ sáu route, không đưa guide vào JS bundle, không ghi dữ liệu.

## Kiểm tra Constitution trước và sau thiết kế

| Nguyên tắc | Kết luận | Cơ sở |
| --- | --- | --- |
| I | Đạt | Label UI tiếng Anh, tài liệu bằng tiếng Việt; User Guide tiếng Việt theo yêu cầu trực tiếp. |
| II | Đạt | Tái sử dụng ActionLink, teal/white; không đổi menu/branding. |
| III | Đạt | Spec → plan → tasks → analyze → implement → kiểm chứng, truy vết FR và SC. |
| IV | Đạt | File thật, không mock chức năng tải, không thêm service. |
| V–IX | Không áp dụng | Không thay Excel, ETL, credential, staging, workflow hoặc service runtime. |
| X | Đạt về kế hoạch | Typecheck, tích hợp static HTTP/hash, E2E tải/offline; evidence thực tế ghi riêng. |
| XI–XII | Đạt | README, quickstart, báo cáo; một increment kiểm thử độc lập. |

Không vi phạm hoặc ngoại lệ mới. Sau thiết kế giữ nguyên kết luận; không suy nghiệm thu sản phẩm tổng thể từ tính năng này.

## Cấu trúc triển khai

- `frontend/src/app/App.tsx`: ActionLink Download User Guide tại workspace-bar, nhóm cùng status, URL theo BASE_URL.
- `frontend/src/app/styles.css`: wrap bar/actions và padding; nút tối thiểu 36px, focus hiện có, không tràn ở 320px.
- `frontend/public/user-guide/Airflow-Automation-Tool-Huong-dan-su-dung.html`: bản phát hành được version cùng source.
- `docs/user-guide/build_guide.py`: ghi cùng nội dung vào outputs và public; frontend build không cần ảnh tạm/Python.
- `frontend/Dockerfile`: COPY public trước build; không lấy docs vốn bị .dockerignore loại.
- `frontend/scripts/verify-user-guide.cjs`: kiểm tra static/download trên dist, sáu route, mobile/bàn phím, giữ trang, backend lỗi và offline.
- `README.md`, `docs/testing/user-guide-download-20261115.md`: hướng dẫn và evidence.

## Giai đoạn, phụ thuộc và kiểm chứng

1. Nghiên cứu repo, chốt thiết kế tại research/data-model/contracts/quickstart.
2. Tasks và phân tích tính nhất quán trước khi sửa code.
3. Đóng gói guide, nút, CSS và Docker; không đổi nội dung guide hoặc nghiệp vụ.
4. Build → HTTP/hash → E2E → báo cáo SC-001–004. Không rollout container đang dùng.

## Lỗi và tương thích

Chỉ GET static; browser xử lý download, không transaction nghiệp vụ. QA phải thất bại nếu file thiếu hoặc bytes khác, kể cả HTTP200 SPA fallback. Không yêu cầu backend/Airflow online. Kiểm tra cấu trúc Dockerfile, không quảng bá image mới đã nghiệm thu khi chưa chạy build/scan image.
