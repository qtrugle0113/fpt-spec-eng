# Triển khai bản vá dnspython trong phạm vi T014

Nguồn ủy quyền: yêu cầu hiện tại của chủ dự án “Sửa các security findings có thể
sửa, rebuild và scan lại đúng images cuối”. Đây là lựa chọn kỹ thuật triển khai
bản vá, không phải phê duyệt security finding hoặc waiver.

Scan mới phát hiện CVE-2026-128089 trên dnspython2.9.0. Nâng override lên2.9.2,
giữ nguyên bytes/SHA upstream constraints và các override khác. Hash wheel lấy
từ PyPI JSON, tải và kiểm SHA256 trước kiểm chứng. Cập nhật integration assertion
để yêu cầu đúng phiên bản mới; chạy pip check, SDK, regression liên quan và scan.

Nguồn chính thức: [advisory của tác giả](https://github.com/rthalley/dnspython/security/advisories/GHSA-vvf4-9x63-8xvv),
[PyPI2.9.2](https://pypi.org/pypi/dnspython/2.9.2/json).
Ảnh hưởng advisory: parse WKS từ zone-file do bên ngoài kiểm soát có thể dùng quá
nhiều CPU/RAM. Không tự kết luận ứng dụng không bị ảnh hưởng.

Demo tiếp tục dùng image đã review cho đến khi candidate mới đủ điều kiện rollout.
T014/T152 vẫn mở đến khi mọi gate đầy đủ đạt; không đổi local approval hiện có.
