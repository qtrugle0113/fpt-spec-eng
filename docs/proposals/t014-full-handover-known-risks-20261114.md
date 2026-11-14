# Đề xuất nghiệm thu có ghi nhận rủi ro đã được chủ dự án review

Trạng thái: **CHỜ PHÊ DUYỆT THAY ĐỔI QUẢN TRỊ**, chưa áp dụng Constitution.

Chủ dự án xác nhận trong hội thoại: “ko cần sửa gì nữa đâu. Tôi đồng ý với tát
cả nội dung”. Quyết định này được ghi nhận theo đúng snapshot hồ sơ đã review;
không đổi severity, không kết luận mọi finding not-affected và không làm scan
trở thành zero findings.

## Thay đổi cụ thể đề nghị phê duyệt

Bổ sung Constitution2.0.0 cho phép nghiệm thu đầy đủ **có rủi ro đã biết**, khi:

1. Toàn bộ kiểm thử chức năng/an toàn dữ liệu bắt buộc, CI đúng commit cuối,
   compatibility, startup/recovery và truy vết nghiệm thu đều đạt.
2. Security scan trên đúng artifacts được lưu nguyên trạng. Findings còn lại
   có quyết định của chủ dự án cho đúng snapshot advisory/package/version/image;
   không dùng phê duyệt này cho artifact/finding mới.
3. Trạng thái scan vẫn ghi findings/BLOCKED theo kết quả công cụ; trạng thái
   security disposition ghi `OWNER_ACCEPTED_KNOWN_RISKS`. T014_FULL chỉ được PASS
   nếu cả technical gates và quyết định quản trị này đã có hiệu lực.
4. Phạm vi bàn giao: một operator, loopback, dữ liệu tổng hợp, không public/LAN,
   không dữ liệu quan trọng. Không mở rộng quyền triển khai hoặc phạm vi sử dụng.
5. Giữ mốc review2026-11-16 và hạn2026-11-23T00:00:00+09:00; không gia hạn tự động.
   Hết hạn hoặc thay đổi artifacts/findings phải đánh giá lại; chức năng/data
   integrity/secrets/recovery không được miễn kiểm thử.
6. Sau khi T014 đạt theo quy tắc này, chạy cổng T152 đầy đủ và ghi rõ “nghiệm thu
   baseline local có rủi ro đã biết”, không gọi là security-clean hoặc production-ready.

Snapshot được đề nghị áp dụng:
`docs/testing/resume-20261114/t014-closeout/current-review-packet.json`, gồm
21targets/1.669occurrences/363nhóm; immutable IDs và raw report hashes theo hồ sơ.
Ghi SHA256 snapshot và nguyên văn quyết định trong decision record đi kèm.

## Tác động đồng bộ sau phê duyệt

- Constitution1.3.0→2.0.0: thêm cơ chế trên, giữ nguyên các nghĩa vụ còn lại.
- Đồng bộ spec/plan/tasks/research/README/quickstart/acceptance report và bộ
  kiểm tra gate để phân biệt scan findings với quyết định nghiệm thu đã chấp nhận.
- Không tự đánh dấu checklist reviewer. Chỉ đóng T014/T152 sau evidence thực tế.

Đây là đề xuất cụ thể để chủ dự án phê duyệt; chưa phải một waiver hoặc quyết
định đã ban hành. Nếu không được duyệt, giữ quy tắc hiện tại và hai task còn mở.
