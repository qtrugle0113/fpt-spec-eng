# Quyết định chủ dự án về phát triển local T014 — 2026-11-09

## Quyết định bổ sung và kích hoạt hiện hành

Chủ dự án đã xác nhận rõ trong hội thoại tiếp theo:
1. Đóng LEX-003 cho phạm vi local theo mitigation build offline; raw parent vẫn còn finding.
2. Phê duyệt LEX-079 not affected cho đúng 12 contexts baseline và 3 candidate contexts.
3. Phê duyệt mapping 316 lượt C sang đúng 3 candidate IDs, giữ nguyên controls/owner/hạn/thu hồi.

[Hồ sơ kích hoạt có timestamp ghi nhận và từng context](t014-local-activation.json),
[xác minh source/IDs/controls](../testing/t014-local-activation-verification.json).
Reviewer là chủ dự án TrungLQ13 qua xác nhận trực tiếp, không phải AI tự ký.
Không có timestamp gửi message từ transport; dùng thời điểm ghi nhận thực tế trong JSON.
D1/D2/D4 không thay đổi; LEX-079 không chuyển thành risk acceptance, LEX-003 không
trở thành kết luận raw parent sạch. D2 vẫn đúng 147 nhóm, không blanket waiver.

**M0 đã khép hợp lệ; PHASE2_LOCAL_ELIGIBILITY AUTHORIZED đến
2026-11-23 00:00 UTC+09**, review chậm nhất 2026-11-16, thu hồi theo proposal.
Scope implementation lượt này chỉ T015/T016 viết tests; không cho task Phase 2 khác.
T014_FULL vẫn BLOCKED; security FAIL_WITH_APPROVED_LOCAL_EXCEPTIONS.
CI/clean checkout source mới và full scan 21 targets vẫn NOT_RUN.

Các đoạn REVIEW_REQUIRED/BLOCKED phía dưới là hồ sơ lịch sử trước xác nhận bổ sung,
không phải trạng thái quyết định hiện hành.

Cập nhật bằng chứng: [hồ sơ review](../testing/t014-local-gate-review.md),
[results/exact IDs](../testing/t014-local-gate-results.json),
[mapping chưa phê duyệt](../testing/t014-local-findings-delta.json).
LEX-003 mitigation checks PASS; D3/LEX-079 có kết luận kỹ thuật đề xuất.
Cả hai vẫn REVIEW_REQUIRED; candidate mapping NOT_APPROVED. Không thay đổi quyết định
D1/D2/D4, thời hạn, baseline hoặc kích hoạt PHASE2_LOCAL_ELIGIBILITY.

**D1/D2/D4 ĐÃ DUYỆT. M0/PHASE2_LOCAL_ELIGIBILITY VẪN BLOCKED.**

Nguồn thẩm quyền: chủ dự án phê duyệt rõ trong hội thoại lượt này:
“D1: cơ chế phát triển local có điều kiện”, “D2: chấp nhận rủi ro tạm cho đúng147nhóm
loại C trong ledger”, “D4: kế hoạch triển khai theo các mốc M0–M6”.
Không suy việc đã review thành not-affected cho D3/LEX-079 hoặc đóng LEX-003.
Đây là ghi nhận quyết định trong hội thoại, không giả chữ ký số hoặc chữ ký của reviewer.

## Phạm vi quyết định

| Mục | Trạng thái | Phạm vi |
| --- | --- | --- |
| D1 | APPROVED | Cơ chế local có hạn, tách khỏi nghiệm thu đầy đủ; đồng bộ Constitution1.2.0 và tài liệu theo đề xuất đã review |
| D2 | APPROVED | Đúng147nhóm C/771contexts tại baseline proposal; không bao gồm LEX-003/LEX-079 |
| D3/LEX-079 | REVIEW_REQUIRED | Chuẩn bị bằng chứng kỹ thuật; chủ dự án/reviewer phải xác nhận riêng, không AI tự ký |
| D4 | APPROVED | Mốc M0–M6 theo dependencies hiện có, chưa tự mở Phase2 |
| LEX-003 | REVIEW_REQUIRED | Được phép remediation có mục tiêu, build/test/scan candidate; chưa được miễn trừ hoặc ký đóng |
| T014_FULL/security | BLOCKED/FAIL | Không coi conditional authorization là security PASS |
| PHASE2_LOCAL_ELIGIBILITY | BLOCKED | Chưa đủ D3/LEX-003 và mapping candidate/controls để kích hoạt |

Baseline được duyệt: HEAD `b0c947d23f1e9c23e9ce0a57b634f9e7a4c7b4ab`,
implementation d57db09 và exact IDs trong [proposal ledger](../proposals/t014-conditional-local-findings.json).
Đối chiếu đầu lượt: source hashes và20image IDs không mismatch; checklists16/16,48/48 PASS,
không extension hooks. Reviewer checklists giữ nguyên.

[Ledger ghi nhận D2](t014-local-approved-findings.json) giữ toàn bộ contexts và IDs;
`approved=true` của147nhóm dựa trên quyết định chủ dự án, không phải AI tự miễn trừ.
Hai nhóm còn lại vẫn approved=false. Proposal gốc giữ như snapshot trước phê duyệt.

## Thời gian, owner và điều kiện

Ngày phê duyệt trong hội thoại: **2026-11-09**. Timestamp vận chuyển message không được
API cung cấp; `approval_recorded_at` trong JSON là thời điểm ghi nhận thực tế, không giả
là thời điểm gửi message. Kiểm tra đầu lượt lúc13:58:08 UTC+09 xác nhận chưa vượt hạn.

Review chậm nhất **2026-11-16**. Dùng hạn ghi nhận bảo thủ **2026-11-23 00:00 UTC+09**,
không quá14ngày kể từ phê duyệt ngày09/11 và không vượt hạn cố định của proposal.
Không tự gia hạn. Đây là hạn D2 tối đa; quyền local chưa được kích hoạt nên chưa có quyền
thực hiện Phase2 trong thời gian chờ review.

Risk owner: chủ dự án TrungLQ13. Remediation owner: maintainer được giao, mặc định chủ dự án
nếu chưa giao. Reviewer: chủ dự án hoặc người được chỉ định; AI chỉ chuẩn bị bằng chứng.
Scope local/một operator/dữ liệu tổng hợp/loopback và mọi controls/thu hồi trong proposal
giữ nguyên. Không chuyển risk acceptance sang image mới nếu chưa review mapping/delta.

## Chuyển đổi đã được phép và phần còn chờ

Đồng bộ có chọn lọc các hunk của [patch đã review](../proposals/t014-conditional-local-gate-changes.patch)
về quyền local có điều kiện, gate dependency và hướng dẫn runner. Không đổi checkbox
T014/T015/T016, không tạo implementation Phase2. Các hunk không tự tuyên bố gate ACTIVE.

LEX-003: thiết kế candidate dùng Debian security package có chain chữ ký InRelease →
Packages SHA256 → artifact SHA256; cài offline trong RUN network=none trước apt/network
trong Airflow stage, giữ core/constraints. Bằng chứng kết quả và reviewer cần được ghi
ở báo cáo lượt này sau kiểm thử, không tự cập nhật quyết định đóng khi mới thiết kế.

LEX-079: so binary package/libz inventory và symbols đúng12contexts; đề xuất not-affected
chỉ cho zlib1g/CVE cụ thể, không áp cho minizip/pyminizip/bản nhúng hoặc CVE khác.
Sau khi technical evidence sẵn sàng, cần người có thẩm quyền ký kết luận riêng.
