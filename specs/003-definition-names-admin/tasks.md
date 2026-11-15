# Công việc: Definition và admin local

**Nguồn**:[spec.md](spec.md),[plan.md](plan.md). Task chỉ đóng khi có bằng chứng.

## Pha 1 — Chuẩn bị

- [x] T001 Chụp baseline project/volume/dữ liệu, rà spec/plan/checklist và cấu hình auth thực tế; ghi docs/testing/definition-admin-20261115.md. FR-007,008.

## Pha 2 — US1: Thuật ngữ

**Kiểm độc lập**: Chuỗi, Excel Instructions, desktop/mobile, upload/validate trên fixture.

- [x] T002 [US1] Thống nhất chuỗi frontend/src/pages, frontend/src/features và selector tests/e2e, frontend/scripts; giữ identifier. FR-001,003.
- [x] T003 [US1] Đồng bộ message backend/src/aat_api/services và validation, giữ message_key/code; cập nhật template Instructions qua generator hiện có và docs/operations. FR-002,003.
- [x] T004 [US1] Chạy typecheck/build và kiểm UI/template/validation trên source mới, ghi docs/testing/definition-admin-20261115.md. Phụ thuộc T002,T003. SC-001.

## Pha 3 — US2: Admin local

**Kiểm độc lập**: Unit opt-out/custom password và login API/browser thật ở demo/fresh, restart/preservation.

- [x] T005 [US2] Viết tests/unit/test_local_airflow_admin.py trước helper; kiểm opt-in/idempotence/reset/restore/secret hỏng/account khác. FR-004–007.
- [x] T006 [US2] Thêm docker/bootstrap/local_airflow_admin.py, sửa secrets.py và entrypoint/Dockerfile/docker-compose.yml cho fresh local opt-in, không reset init; unit test đạt. Phụ thuộc T005. FR-005–007.
- [x] T007 [US2] Thêm scripts/configure-local-airflow-admin.py xác minh demo/project/loopback/volume, backup, cập nhật persistent secret và Compose env, recreate API --no-build; có restore. Phụ thuộc T001,T006. FR-004,006,007.
- [x] T008 [US2] Kiểm login admin/admin/quyền thật trên demo, service auth, restart và ID/volume trước–sau; tests/e2e/definition_admin.spec.ts hoặc script browser tương ứng. Phụ thuộc T007. SC-002–004.
- [x] T009 [US2] Chạy fresh stack với project/network/volume riêng và source overlay, login/quyền thật, unit/integration idempotence/restore; giữ dữ liệu demo. Phụ thuộc T006. SC-002–004.

## Pha 4 — Hoàn thiện

- [x] T010 Đồng bộ docs/operations/local-airflow-admin.md, docs/excel-definitions.md, README.md, quickstart và báo cáo; analyze/converge, ghi giới hạn, không commit/push/production. Phụ thuộc T004,T008,T009. FR-003,008.

## Thứ tự và song song

T001 → US1(T002→T003→T004) và US2(T005→T006→T007→T008,T009) → T010. Không đánh dấu P vì source/tooling dùng chung. Có thể nghiên cứu fixture song song với đọc chuỗi bằng agent chỉ đọc theo skill plan. Hai mục tiêu đều bắt buộc, không coi US1 đủ để hoàn tất.
