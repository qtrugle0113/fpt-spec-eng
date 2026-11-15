# Công việc: Tải User Guide

## Giai đoạn 1 — Chuẩn bị

- [x] T001 Rà soát Constitution, template, frontend/static và guide hiện có; ghi `specs/004-user-guide-download/spec.md`, checklist và `research.md`. Phụ thuộc: không. Đạt khi không còn điểm cần làm rõ.

## Giai đoạn 2 — Thiết kế nền tảng

- [x] T002 Hoàn thiện `specs/004-user-guide-download/plan.md`, `data-model.md`, `contracts/user-guide.md`, `quickstart.md`, tasks và rà soát analyze. Phụ thuộc T001. Đạt khi FR-001–006 đều có task và không có mâu thuẫn Constitution.

## Giai đoạn 3 — US1 (P1): Tải từ mọi màn hình

**Kiểm thử độc lập**: từ sáu route tải file thật, giữ trang, mở offline.

- [x] T003 [US1] Đóng gói guide gốc vào `frontend/public/user-guide/Airflow-Automation-Tool-Huong-dan-su-dung.html`; cập nhật `docs/user-guide/build_guide.py` ghi cả hai nơi và `frontend/Dockerfile` COPY public. Phụ thuộc T002; FR-002/003/005. Đạt khi source/public/dist trùng bytes, build frontend không cần ảnh nguồn.
- [x] T004 [US1] Thêm ActionLink dùng BASE_URL trong `frontend/src/app/App.tsx`, responsive actions trong `frontend/src/app/styles.css`. Phụ thuộc T003; FR-001/002/004/006. Đạt khi nút chung thấy trên sáu route, không thêm menu, tải giữ trang.
- [x] T005 [US1] Thêm và chạy `frontend/scripts/verify-user-guide.cjs`, script `test:user-guide` trong `frontend/package.json`. Phụ thuộc T004; FR-001–006, SC-001–004. Đạt khi build/typecheck, HTTP/hash, sáu route desktop/mobile, Enter, offline và backend lỗi đều PASS; evidence ở `.tools/user-guide-download/`.

## Giai đoạn 4 — Bàn giao

- [x] T006 Cập nhật `README.md`, ghi `docs/testing/user-guide-download-20261115.md`, đối chiếu tasks/spec/plan và diff. Phụ thuộc T005. Đạt khi báo cáo lệnh/kết quả/giới hạn đúng thực tế, không tuyên bố container rollout chưa chạy.

## Phụ thuộc và chiến lược

T001 → T002 → T003 → T004 → T005 → T006. Một story, thực hiện tuần tự; không cần phân việc song song sau nghiên cứu. MVP là đúng bản guide có thể tải; không thêm tính năng ngoài phạm vi. Chỉ đánh dấu task triển khai sau khi kiểm chứng tương ứng.
