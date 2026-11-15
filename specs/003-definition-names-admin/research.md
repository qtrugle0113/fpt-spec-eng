# Nghiên cứu và quyết định

## Thuật ngữ

Frontend dùng workbook ở label, toast, history và Settings; backend dùng trong thông báo validation. Giữ tên kỹ thuật workbook_sha256/WORKBOOK_* và message_key để tương thích bản ghi cũ. Chỉ đổi văn bản hiển thị và tài liệu hiện hành, không rewrite lịch sử.

## Auth và persistent state

Airflow đang chạy3.3.2, SimpleAuthManager.get_users đọc config core/simple_auth_manager_users; password file qua core/simple_auth_manager_passwords_file. Entry point chép persistent secret RO sang /tmp riêng rồi dùng file đó. Bootstrap tạo aat_service/operator một lần. Tài liệu chính thức cho phép quản user bằng config và cập nhật password file: [SimpleAuthManager](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/auth-manager/simple/index.html). Source cài đúng phiên bản trong container được kiểm cùng tài liệu; không dùng lệnh FAB users cho manager này.

Quyết định: init fresh opt-in, cập nhật existing bằng helper tường minh có backup; env user roles được lưu vào Compose record, recreate giữ volume/image. Không xóa dữ liệu hoặc đổi service. Không tự reset custom admin ở init.

## Fixture và artifact

Agent nghiên cứu chỉ đọc xác nhận tests/tools/run_connections_e2e.py tạo project/volume/network riêng, source snapshot RO /current; secrets-init chạy bootstrap source mới. Config/entrypoint cũ trong image không tự đổi bằng PYTHONPATH, nên fixture phải mount entrypoint/helper hoặc truyền user roles tương đương rõ ràng. Không coi source overlay là packaged image acceptance. Giữ fixture volumes, tránh thao tác cleanup vào demo.
