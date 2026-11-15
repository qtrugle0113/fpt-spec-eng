# Tài khoản Airflow local/demo

## Sử dụng

Demo hiện hữu: <http://localhost:28080>, username **admin**, password **admin**, quyền **admin**. Tài khoản ứng dụng và service account `aat_service` là các đối tượng khác; không dùng admin để thay credential tích hợp backend.

Chỉ dùng cấu hình này cho local/demo trên loopback. Root `docker-compose.yml` bind các cổng public vào127.0.0.1 và truyền `AAT_LOCAL_DEMO_AUTH=1`. Môi trường khác phải opt-out bằng0 và tự quản lý credential; không đưa cấu hình demo ra production/LAN.

## Khởi tạo mới

Khi chạy Compose mới theo README, secrets-init tạo password store một lần. Nếu local flag=1, store có admin/admin cùng service/operator password ngẫu nhiên. Entry point chỉ bổ sung role admin trong chế độ này; không bật `simple_auth_manager_all_admins` và không tắt auth.

Init lại kiểm manifest/key như trước và giữ file password, bao gồm mật khẩu admin đã được tùy chỉnh. Chỉ lệnh cập nhật tường minh dưới đây mới đặt lại admin/admin. Profile không opt-in không tạo password admin mặc định này. Tài khoản, role và password file theo cơ chế [SimpleAuthManager chính thức](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/auth-manager/simple/index.html), không sửa bảng metadata DB.

## Cập nhật demo đã tồn tại

Tại repo, Podman machine và backend/Airflow demo cần hoạt động:

```powershell
python -X utf8 scripts/configure-local-airflow-admin.py
```

Script đọc `.tools/local-demo.json`, xác minh project, port loopback, auth manager, secret volume/image. Nó chụp ID dữ liệu, sao lưu Compose và password file, giữ user khác, đặt lại riêng admin, bổ sung role vào cấu hình Compose đã lưu rồi recreate đúng Airflow API service với `--no-build --no-deps`. Không start scheduler hoặc xóa volumes; service account/operator giữ nguyên.

Kết quả in đường dẫn receipt trong `.tools/local-admin-migrations/<id>/receipt.json`, không in password cũ. Bản sao secret nằm trong `.local-admin-backups` của secret volume, quyền hạn chế; không copy ra repo hoặc evidence công khai. Receipt và backup Compose nằm `.tools` bị ignore.

## Khôi phục

```powershell
python -X utf8 scripts/configure-local-airflow-admin.py --restore .tools/local-admin-migrations/<id>/receipt.json
```

Chọn receipt đúng lượt cập nhật. Script chỉ nhận backup cùng project/secret volume và đường dẫn trong workspace, khôi phục bytes password gốc và Compose trước lượt cập nhật, rồi recreate API. Sau restore tài khoản admin có thể không tồn tại nếu trước đó chưa có; dùng tài khoản trước lượt cập nhật. Không xóa backup hoặc volume để khôi phục.

Nếu sau receipt còn thay đổi Compose khác, cần đối chiếu bản backup với cấu hình hiện hành trước khi restore toàn bộ; ví dụ overlay source Definition được áp dụng sau migration tài khoản. Backup source overlay ghi riêng trong `demo-source-overlay.json`. Giữ role/secret backup và áp lại overlay phù hợp sau rollback nếu cần.

## Source và template đang dùng ở demo

Đợt003 nạp source backend/asset hiện tại bằng volume code riêng mount read-only `/current`, giữ nguyên dependency image và volume dữ liệu. `AAT_ASSETS_ROOT=/current` phục vụ template mới; `PYTHONPATH` trỏ source hiện tại. Compose backend-worker cũng được lưu cấu hình này cho lần start sau; worker/scheduler demo không được tự start trong đợt này.

UI mới xem tại <http://127.0.0.1:4179>; frontend demo23000 chưa rollout. Image hiện hữu không được tuyên bố đã đóng gói source mới. Muốn build image mới phải theo quy trình artifact/scan của repo. Script `scripts/apply-local-definition-source.py` được dùng một lần cho demo local này; từ chối tự chồng thêm overlay khi đã có `/current`.

## Kiểm chứng và bảo toàn

Xem [báo cáo](../testing/definition-admin-20261115.md): login browser thật ở demo/fresh, JWT role admin, API được bảo vệ, sai password bị từ chối, service account còn hoạt động, restart/init không đổi password, backup/restore trên fixture, ID dữ liệu và volume không mất. Không công bố secret cũ trong báo cáo.
