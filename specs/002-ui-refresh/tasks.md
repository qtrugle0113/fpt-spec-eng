# Công việc: Làm mới giao diện

**Nguồn**: [spec.md](spec.md), [plan.md](plan.md), [contracts/ui.md](contracts/ui.md)
**Kiểm chứng**: Có yêu cầu kiểm thử UI thực tế; mỗi task chỉ đóng khi đầu ra được kiểm chứng. Không commit/push/deploy.

## Pha 1 — Chuẩn bị

- [x] T001 Rà soát spec/plan/checklist và chuẩn bị dependency đúng lock tại frontend/package-lock.json; ghi môi trường vào docs/testing/ui-refresh-20261115.md. Đạt khi xác định runtime, API baseline và cài dependency thành công. FR-009.

## Pha 2 — Nền tảng

- [x] T002 Tạo kiểm chứng viewport, keyboard, download và URL tại frontend/scripts/verify-ui.cjs, đăng ký frontend/package.json; chạy trước sửa UI để xác định lỗi baseline. Phụ thuộc T001; đạt khi test bắt được yêu cầu layout/button chưa đáp ứng. FR-003–006.

## Pha 3 — US1: Giao diện sáng và gọn

**Mục tiêu**: Sáu trang đọc được dữ liệu/control đầu tiên trong viewport và không tràn ngang.
**Kiểm thử độc lập**: Sáu route, hai viewport, ảnh thật và keyboard.

- [x] T003 [US1] Chuẩn hóa token/sidebar/panel/control/table/form/feedback responsive tại frontend/src/app/styles.css và frontend/src/app/App.tsx. Phụ thuộc T002; đạt khi sáu route giữ menu, focus và không overflow. FR-001,002,004–007.
- [x] T004 [US1] Sắp xếp Dashboard metrics/recent runs trước dữ liệu phụ tại frontend/src/pages/Dashboard.tsx và frontend/src/features/dashboard/Metrics.tsx; đồng bộ legend teal. Phụ thuộc T003; đạt khi có metrics và đầu bảng trước768px. FR-001,004,006.
- [x] T005 [US1] Dùng grid cho wizard/history/settings tại frontend/src/pages/Tables.tsx, frontend/src/pages/DagBuilder.tsx, frontend/src/pages/Settings.tsx; gom form upload và bộ lọc, giữ review/authority. Phụ thuộc T003; đạt khi desktop gọn và mobile thứ tự đọc đúng. FR-002,004–007.

## Pha 4 — US2: Download và Airflow rõ ràng

**Mục tiêu**: Mọi link mục tiêu có hình thức button, vẫn anchor semantics.
**Kiểm thử độc lập**: Tải hai template thật, popup Airflow đúng URL và keyboard focus.

- [x] T006 [US2] Thêm frontend/src/components/ActionLink.tsx và áp dụng tại TableWizard.tsx, DagDefinitionWizard.tsx, DeploymentPanel.tsx, Dashboard.tsx, Monitoring.tsx; giữ href/target/rel/download và nhãn. Phụ thuộc T003; đạt khi toàn bộ link mục tiêu là button và hai file tải hợp lệ. FR-003,006,007.

## Pha 5 — US3: Tài khoản demo có điều kiện

**Mục tiêu**: Kết luận khả thi và không sửa tài khoản hiện hữu.
**Kiểm thử độc lập**: Rà bootstrap và cấu hình, đối chiếu điều kiện FR-008.

- [x] T007 [US3] Ghi kết luận không đổi tài khoản tại specs/002-ui-refresh/research.md và docs/operations/ui-refresh.md, tham chiếu docker/bootstrap/secrets.py và airflow/docker/airflow.cfg. Phụ thuộc T001; đạt khi nêu rõ lý do, không có diff auth/secrets/production. FR-008.

## Pha 6 — Hoàn thiện và kiểm chứng

- [x] T008 Chạy typecheck/build/kiểm chứng frontend/scripts/verify-ui.cjs; kiểm tra ảnh desktop/mobile, lỗi/empty/loading cô lập và hồi quy đọc API tại docs/testing/ui-refresh-20261115.md. Phụ thuộc T003–T007; đạt khi các kiểm tra bắt buộc pass, giới hạn được ghi trung thực. SC-001–SC-005, FR-009.
- [x] T009 Đồng bộ docs/operations/ui-refresh.md, specs/002-ui-refresh/quickstart.md và báo cáo, kiểm diff rồi thực hiện speckit-converge. Phụ thuộc T008; đạt khi không còn chênh lệch buildable trong spec/plan/tasks. FR-009.

## Phụ thuộc và chiến lược

T001 → T002 → T003 → T004/T005 → T006 → T007 → T008 → T009. US1 là MVP, kiểm chứng riêng trước hoàn thiện US2; US3 không cản trở UI. Không có task [P] do CSS/pages dùng chung; có thể đọc cấu hình tài khoản song song với nghiên cứu palette nhưng không sửa cùng file đồng thời. Bàn giao source/preview, không deploy.

## Bằng chứng hoàn tất

Xem [báo cáo kiểm chứng](../../docs/testing/ui-refresh-20261115.md): T001 dùng Node22.23.4 và lock hiện tại; T002 bắt3 lỗi baseline; T003–T006 có ảnh/25 kiểm tra UI; T007 ghi quyết định giữ auth; T008 typecheck/build/18 shell/4 E2E đạt; T009 đồng bộ tài liệu và kiểm converge không còn gap. Không rollout hoặc đổi dữ liệu demo.
