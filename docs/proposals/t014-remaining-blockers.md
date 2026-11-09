# Blocker còn lại sau P1–P7

**Phạm vi lịch sử:** bảng dưới đây ghi trạng thái ngay sau P1–P7, trước lượt2 và trước
CI đã PASS. Trạng thái hiện hành xem [báo cáo T014 ngày 2026-11-09](../testing/t014-current-report.md);
quyết định A/B đã được duyệt và triển khai, xem [báo cáo A/B](../testing/t014-ab-report.md)
và [phương án lượt2](t014-round2-approval.md). Không dùng bảng lịch sử làm gate hiện hành.

P1–P7 đã áp dụng và kiểm chứng bootstrap; T014 vẫn BLOCKED. Không thay phiên bản ngoài
phương án đã duyệt, override constraints, tự miễn trừ finding hoặc chạy CI remote.
Nguồn hiện hành: `docs/testing/phase1-security.json`, `t014-security-triage.csv` và
`t014-remediation-results.json`. Snapshot đề xuất trước sửa nằm ở `docs/proposals/t014-*`.

| Nhóm cần quyết định tiếp | Bằng chứng cụ thể | Hướng xử lý trước khi đóng |
| --- | --- | --- |
| Airflow OS/runtime tooling | Image slim còn146HIGH/22CRITICAL; OpenSSL3.0.20 → candidate3.0.22-1~deb12u2; apt2.6.1 →2.6.2, PCRE2 deb12u1 →u2; có cả NO_FIX | Chốt OS patch lock/snapshot riêng cho custom Airflow và loại công cụ không dùng có dependency proof. Không giả định slim hoặc repull tag là đủ |
| Python bị constraints khóa | Official constraints certifi2026.7.22, urllib3 2.7.0; scanner nêu2026.10.18/2.8.0. Một số bản cũ còn nằm trong vendor/tool trees | Cần duyệt phương án override có provenance/resolver/regression riêng, hoặc nâng Airflow với contracts/SDK review. Không tự sửa constraints upstream; pip upgrade top-level không vá vendor copy |
| Build/npm | Node base44HIGH/1CRITICAL; frontend build72/4; npm10.9.4 giữ theo duyệt. Backend/Airflow wheels mỗi43/2 | Nghiên cứu và trình exact npm/toolchain candidate được scan và build thử; không audit-fix-force hoặc giấu build-stage findings. OS NO_FIX cần triage từng advisory |
| PostgreSQL/MySQL | PG17.11 còn75/4, MySQL8.4.13 còn33/2; có stdlib nhúng trong gosu1.24.6, thư viện trong mysqlsh | Cần vendor image/binary đã vá hoặc custom rebuild có provenance; chứng minh đường dùng từng CVE. Không cài Go mới để giả sửa embedded binary; không sửa lock Python backend để vá mysqlsh |
| Browser runner | Sau OS patch và loại global npm còn2HIGH/0CRITICAL ở GStreamer1.24.2, scanner NO_FIX | Giữ OPEN; đánh giá media/browser prerequisites hoặc trình cặp client/image/browser mới. Không tự loại media libraries làm browser lỗi hoặc nâng một phía; native browser coverage cần review riêng |
| Backend/pytest OS | Mỗi image40HIGH/2CRITICAL, toàn bộ còn lại không có FixedVersion trong snapshot | Vendor/advisory/reachability review từng finding; không mặc định exploitable hoặc not-affected, không tự waive |
| CI Windows/Linux | Workflow có matrix và commit evidence, remote NOT_RUN; source/workflow còn uncommitted/untracked | Chủ dự án duyệt scope commit/branch/push và chạy CI remote sau review diff. CI phải trỏ đúng SHA; local PASS không thay remote PASS |
| Clean Git checkout | Fixture raw-byte checks PASS, nhưng root ACL cache chưa được xử lý; HEAD chưa chứa implementation | Sau khi được phép commit, checkout mới đúng SHA trong thư mục mới, kiểm hashes/status và startup. Không reset ACL/cache/volumes; clone HEAD cũ không chứa source untracked |

Các fixed versions trên là candidates trong scanner, không phải pin mới được duyệt hoặc
compatibility PASS. Không cần sửa Constitution để giữ gate hiện hành; bất kỳ chấp nhận
rủi ro nào là quyết định riêng và phải kiểm tính phù hợp Constitution trước.

Phạm vi xin quyền publish phải liệt kê cả thay đổi có trước lượt remediation; protected
Constitution/reviewer vẫn giữ nguyên bytes trong lượt này. Không dùng một lệnh `git add .`
để gộp mọi thay đổi. File manifest và patch review được chuẩn bị riêng; chưa stage/commit.
