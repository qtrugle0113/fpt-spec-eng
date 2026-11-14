# Remediation T014 sau khi cho phép commit/push

Trạng thái đầy đủ vẫn **BLOCKED bởi security**, không còn lý do cấm commit/push.
Chủ dự án đã cho phép push nhánh `001-airflow-automation-tool-t014` trong yêu cầu
hiện tại. Các ghi chú cấm commit/push/CI NOT_RUN ở báo cáo cũ là lịch sử.

## Thay đổi và kết quả

- Áp dụng `speckit-analyze` và `speckit-implement`; prerequisites/checklist PASS,
  không có extension hooks; không thay Constitution hoặc reviewer markers.
- Đưa OS package fixes theo lock hiện có lên stage `security-patched`, sau bản vá
  Brotli offline; giữ kiểm tra offline trước lệnh mạng đầu tiên. Trước khi thay
  dnspython, runtime rebuild có chính xác ID cũ `7a55c47c…`, build stage mới
  `f446e0c1…` được scan riêng. CI hồi quy bảo vệ cả hai thứ tự bắt buộc.
- Nâng override dnspython2.9.0→2.9.2, hash wheel từ PyPI; giữ nguyên upstream
  constraints và các override khác. [Quyết định triển khai](../../../decisions/t014-dnspython-remediation-20261114.md)
  ghi đúng phạm vi ủy quyền; không phải waiver hoặc acceptance approval.
- Candidate Airflow mới `a9dc2f031b05d2eea106adae7b9ee180a6735108d27aad2517fd1e490ff6ef28`.
  `pip check`, import SDK/version và chặn WKS service65536 đều PASS tại
  [kiểm chứng](dnspython/verification.json). Routes lượt đầu FAIL trước test vì
  ACL của `backend/dist` tại workspace gốc; lượt r2 dùng worktree sạch, giữ nguyên
  lượt lỗi và dữ liệu, xem [kết quả r2](dnspython/routes-r2-result.json).
  R2 PASS đủ10tests/180.820s (tám hướng ETL và hai scheduled), cleanup0.
  [Tổng hợp cuối](dnspython/verification-final.json) giữ phạm vi PASS kỹ thuật
  riêng với security BLOCKED và giữ nguyên FAIL lượt ACL trong receipt ban đầu.
- Scan cùng database mới: runtime cũ217 HIGH/CRITICAL, candidate216; advisory
  dnspython mới đã hết trên candidate. [Scan candidate](dnspython/security.json),
  [raw](dnspython/raw-airflow.json), [scan runtime trước bản vá](runtime-security-current-db.json).
- Stage OS-patched258 HIGH/CRITICAL; scan cũ299 dùng database cũ nên không dùng
  hiệu số41 làm số lượng finding đã vá. [Scan stage](remediated-stage-security.json).
- Commit `2585bc006ac1cbb4b9ab96cead0bbbff278031b3` và commit dnspython
  `021a21d` đã push; CI Windows/Linux đều PASS. [Receipt CI source](ci-source.json).
  Lượt CI cuối cho commit báo cáo được ghi riêng trong `ci-final.json` sau push.

## Security còn cần xử lý/review

[Hồ sơ hiện hành](current-review-packet.json) có 21targets/1.669occurrences/363nhóm,
229nhóm không có FixedVersion. Hai target thay đổi được scan lại; 19artifacts
immutable không đổi dùng raw reports trước, có SHA và database provenance theo
từng target. Đây không phải một lần scan toàn bộ cùng database. Hồ sơ cũ vẫn giữ.

Mỗi nhóm ghi advisory, package/version/fix, impact từ scanner, image và layer,
đường dẫn package khi scanner cung cấp. Mọi nhóm chưa khép giữ trạng thái pending.
Finding còn bản sửa ở base/build-stage phải đối chiếu vai trò thực tế; bản sửa đã
cài ở runtime không tự đóng finding của base/stage. Không tuyên bố mọi việc
remediation kỹ thuật trên toàn bộ base/stage đã hoàn tất.

Runtime mới chỉ còn một HIGH/CRITICAL có FixedVersion trong scan:
`CVE-2025-47273`, setuptools70.3.0→78.1.1. Đã xác định component70.3.0 nằm trong
`pip/_vendor/bom.cdx.json`; import setuptools không có, nhưng chưa kết luận
not-affected. [Context cụ thể](dnspython/setuptools-context.json) và
[quan sát runtime](dnspython/sbom-inspection.json) dành cho reviewer đánh giá
đường đi PackageIndex, phạm vi vendored code và độ chính xác SBOM.

Security owner/reviewer cần đưa kết luận hợp lệ theo từng context, yêu cầu bản vá
hoặc baseline mới khi cần. Với nhóm không có FixedVersion, cần đánh giá vendor
backport/upstream và khả năng ảnh hưởng; không tự mặc định an toàn. Hồ sơ chưa có
approval mới; không tự chấp nhận rủi ro, gia hạn policy hoặc sửa luật nghiệm thu.

## T152 và demo

T014_FULL chưa PASS nên T014/T152 giữ `[ ]`, 150/152. Phần stabilization sau bản vá
được ghi đúng phạm vi; không lấy CI source thay security gate. Converge chưa hoàn
tất; nghĩa vụ còn thiếu đã nằm trong T014/T152, không tạo task trùng để thay trạng
thái. Ma trận A–AM/BR-08/SC/US theo [acceptance report](../../acceptance-report.md).

Demo vẫn chạy trên images đã được review trước đó, chưa rollout candidate mới.
Không merge main, public deploy, reset volume, sửa dữ liệu hoặc đưa credentials
lên Git. Evidence được giữ nguyên bytes bằng `.gitattributes`; lỗi whitespace
trong terminal captures được giữ như raw evidence, source diff kiểm riêng.
