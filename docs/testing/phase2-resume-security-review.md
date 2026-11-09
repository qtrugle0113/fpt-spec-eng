# Delta image cho máy mới — 2026-11-09

**Trạng thái: owner đã xác nhận mapping đúng hai ID trong hội thoại ngày 2026-11-09.**

Phản hồi: “Xác nhận mapping hai ID theo hồ sơ”. Giữ controls, hạn và review như
đề nghị dưới đây; không áp dụng cho image khác. T014_FULL vẫn BLOCKED.

Scan Trivy theo digest đã khóa hoàn tất cho hai candidate build từ source hiện tại.
So sánh tuple advisory/package/installed version/severity/fixed version với baseline:

| Candidate | ID mới | HIGH/CRITICAL | Thêm | Bớt |
| --- | --- | --- | --- | --- |
| Backend tests | `6b65b34da83e6f271d2f8f892d08f7fefad31ad06e040f134b7f39d0bc97123e` | 42 | 0 | 0 |
| PostgreSQL | `c93823be91b7c9219c9e97423fdd9ffbe36ce2423fbfa099ecf7355bd69a2dce` | 53 | 0 | 0 |

Danh sách HIGH/CRITICAL giống baseline đã lưu, nhưng image IDs đã đổi. Không coi việc
khớp findings là security PASS hoặc thay cho xác nhận applicability của reviewer.
Scan bao gồm mọi severity; bảng này chỉ tóm tắt HIGH/CRITICAL theo gate hiện hữu.

Đề nghị owner xác nhận mapping findings sang **hai ID mới ở bảng trên** để tiếp tục
phát triển/kiểm thử local cô lập, dữ liệu tổng hợp, loopback. Giữ hạn hiện hữu
2026-11-23 00:00 UTC+09, review 2026-11-16 và các controls hiện hữu; không miễn trừ
secret/auth/data integrity, không nghiệm thu T014_FULL hoặc chấp nhận image khác.

Cơ sở bắt buộc review: [quy tắc rebuild](../proposals/t014-conditional-local-gate.md)
ghi: “owner phải ký delta trước mốc tiếp theo”. Quyền làm đến T152 trong hội thoại
đã mở phạm vi task nhưng nói rõ không phải miễn trừ security findings.

- [Scan mới và toàn bộ HIGH/CRITICAL](phase2-resume-security.json).
- [Delta máy đọc, ID baseline và danh sách findings](phase2-resume-security-delta.json).
- Baseline: `t014-local-runner-security.json` và `t014-r3-security.json`.

Các tests source-copy trên DB dùng một lần là kiểm chứng candidate, chưa phải
deployment được nghiệm thu. Không có service sản phẩm hoặc cổng public mới được mở.
