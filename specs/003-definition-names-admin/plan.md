# Kế hoạch triển khai

**Ngày**:2026-11-15 | **Đặc tả**:[spec.md](spec.md)

## Công nghệ và nghiên cứu

Giữ React19/TypeScript5.9/Vite7 và Python3.12 backend/Airflow3.3.2/SimpleAuthManager. Dùng Node22.23.4 sẵn ở .tools; không thêm dependency. Đã nghiên cứu local code, source Airflow cài trong container và tài liệu chính thức SimpleAuthManager. Skill plan đã giao agent nghiên cứu runner cô lập, kết quả tại research.md.

## Thiết kế

1. Đổi chuỗi theo ngữ cảnh, không đổi identifier/scope/mã lỗi. Backend validation giữ message_key ổn định khi đổi thông báo. Template Instructions chỉ đổi câu chữ, không đổi schema.
2. Bootstrap nhận AAT_LOCAL_DEMO_AUTH opt-in, chỉ fresh tạo admin/admin; root Compose local truyền1, helper mặc định0. Entry point thêm admin:admin vào danh sách quyền khi local enabled, kiểm password file đủ, giữ service/operator và không bật all_admins.
3. Helper local admin chuẩn thư viện Python: atomic write password file, backup riêng chmod bảo vệ trong secret volume, chỉ reset admin khi gọi tường minh; restore giữ byte gốc. Không in dictionary/password.
4. Script cập nhật demo dùng record .tools/local-demo.json, xác nhận project/container/ports loopback/volume/image hiện hữu, backup Compose và secret, merge admin role vào env của service Airflow. Dùng image cũ với helper source để cập nhật secret, recreate API service --no-build --no-deps; giữ image/volume, không start scheduler ngoài phạm vi. Cấu hình Compose đã lưu giữ hiệu lực sau recreate. Backup/restore nằm ngoài source tracking.
5. Fresh fixture bằng runner hiện hữu/source overlay; network/project/volume riêng, env local admin và users rõ ràng, không chia sẻ demo volumes. Không build image mới; công bố CURRENT_SOURCE_ON_EXISTING_DEPENDENCY_IMAGES.
6. Để thông báo/template đang tải ở demo khớp source mới, dùng scripts/apply-local-definition-source.py tạo volume source riêng RO, lưu backup Compose và cập nhật backend/backend-worker; chỉ recreate backend đang phục vụ, không tự start worker/scheduler. Giữ image, dữ liệu và chứng minh tập ID không mất. UI preview4179 dùng build hiện tại; frontend demo23000 không rollout.

## Cấu trúc

- frontend/src/pages và features: chuỗi; tests/e2e và frontend/scripts: selector/kiểm UI.
- backend/src/aat_api/validation và services: thông báo; công cụ tạo templates hiện có.
- docker/bootstrap/secrets.py và local_airflow_admin.py: init/migration an toàn; airflow/docker/entrypoint.sh + Dockerfile: opt-in users.
- scripts/configure-local-airflow-admin.py: orchestrate demo, backup/restore, chỉ local.
- tests/unit/test_local_airflow_admin.py và tests/e2e/definition_admin.spec.ts: hồi quy và login thật; runner cô lập.
- docs/operations và docs/testing: hướng dẫn/evidence.

## Cổng constitution trước/sau thiết kế

I đạt: tài liệu Việt/UI Anh. II đạt: giữ branding/layout. III đạt: feature riêng, truy vết. IV đạt theo thiết kế: API/login thật, fixture tách. V đạt: giữ schema/validation. VI đạt: user cho phép đổi admin local, secret store, backup, không đổi service; không SQL phá dữ liệu. VII không áp dụng, không đổi ETL/staging. VIII đạt: public auth/API và SimpleAuth config, không viết metadata DB. IX đạt trong phạm vi container hiện hữu và fixture source overlay, không quảng bá image mới. X kiểm unit/API/browser/restart/preservation/fresh trước đóng task. XI tài liệu đồng bộ. XII hai giai đoạn kiểm độc lập. Không sửa constitution, không deploy production hoặc tạo image để né gate scan.

## Kiểm chứng

Test bootstrap/admin opt-out, existing user/custom password, missing secret, corrupt JSON, atomic backup/restore; test thông báo giữ message_key. Typecheck/build, rà chuỗi, kiểm browser desktop/mobile và download Instructions. Login thật demo/fresh, kiểm quyền admin, sai password bị từ chối, auth vẫn bật, backend service token còn hợp lệ. Restart và so sánh fingerprint tài khoản khác/volume/tập dữ liệu trước–sau. Có kết quả trung thực cho mọi cổng; không đóng task khi thiếu evidence.
