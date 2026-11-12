# Quyết định build local trên nhiều môi trường

Chủ dự án phê duyệt trực tiếp ngày2026-11-11: mỗi môi trường được build riêng
từ source, dependency locks và cấu hình; không bắt buộc cùng image ID với máy cũ.
Quyết định này thay yêu cầu khôi phục exact baseline images trong quy trình local
trước đây. Các hồ sơ approval cũ giữ nguyên để truy vết, không được viết lại.

Image IDs/digests tiếp tục định danh artifact thực sự build/scan/test tại mỗi máy.
Scan mới đối chiếu advisory/package/installed version/severity theo từng target
với evidence đã được duyệt và hash trong hồ sơ approval; không cần chạy lại image
baseline cũ. Đây là đối chiếu policy, không tuyên bố delta cùng snapshot scanner.
Không kế thừa security PASS, không suy not-affected cho context thay đổi. Findings
mới hoặc provenance thiếu giữ BLOCKED để review cụ thể; không tự thêm ngoại lệ.

Giữ hạn2026-11-23T00:00:00+09:00, review2026-11-16, một operator/dữ liệu tổng hợp/
loopback, không public, không thay/xóa dữ liệu và volumes có trước. T014_FULL
vẫn BLOCKED. Không miễn secrets/auth/data integrity/BR-08 hoặc test chức năng.

Tác động: Constitution1.3.0, Spec/Plan/Tasks/Quickstart và runner local. Không
thay business schema/API/load policy, không yêu cầu registry hoặc archive.
Kiểm chứng bắt buộc: build provenance, scan artifact mới, policy matching có
nguồn gốc, negative tests cho unknown finding, expiry và hash mismatch; DB/Airflow
và browser thật vẫn cần cho nghiệm thu sản phẩm. T138 chỉ khép khi đủ kiểm thử.
