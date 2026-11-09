# T014/M0 — hồ sơ cần reviewer xác nhận, 2026-11-09

**Snapshot trước xác nhận:** chủ dự án đã xác nhận ba quyết định bên dưới trong hội thoại
tiếp theo. Trạng thái hiện hành ở [activation](../decisions/t014-local-activation.json)
và [báo cáo T015/T016](t015-t016-report.md). Giữ nguyên nội dung chờ review phía dưới
để truy vết hồ sơ đã được review; không áp dụng BLOCKED local lịch sử cho hiện tại.

**T014_FULL BLOCKED; security FAIL; PHASE2_LOCAL_ELIGIBILITY BLOCKED.**
D1/D2/D4 đã được chủ dự án duyệt. Báo cáo này không tự đóng D3/LEX-079,
LEX-003 hoặc mở rộng approval sang candidate IDs. T015/T016 chưa triển khai.

Nguồn quyết định: [approval](../decisions/t014-local-gate-approval.md),
[ledger đã duyệt](../decisions/t014-local-approved-findings.json).
Review chậm nhất 2026-11-16; hết hạn 2026-11-23 00:00 UTC+09, không tự gia hạn.
Ngày kiểm tra 2026-11-09 vẫn trong hạn; quyền local chưa kích hoạt.
HEAD `b0c947d23f1e9c23e9ce0a57b634f9e7a4c7b4ab` cùng thay đổi chưa commit;
CI/clean checkout cho source mới **NOT_RUN**, không kế thừa PASS của R3.

## Candidate đã kiểm tra

| Image | Exact ID | HIGH / CRITICAL |
| --- | --- | --- |
| localhost/aat-airflow-local-security-base:0.1.0 | `97e3d67d1f0a8468f2d2409683f2d6c54e5cd415a162a3df6cff022c9809ec16` | 146 / 21 |
| localhost/aat-airflow-local-candidate:0.1.0 | `399adacf113fd269d4dd5d587b956a9167bc02ef8f656d3ff9ef94e11039e2fc` | 105 / 5 |
| localhost/aat-backend-tests-local-candidate:0.1.0 | `89f5d1e6dcc4ec2c55188404b2a4433aae7f8e87e5b8b7c84e9c0023694aaea4` | 40 / 2 |

[Scan Airflow](t014-local-candidate-security.json),
[scan runner](t014-local-runner-security.json),
[results/source hashes/runtime](t014-local-gate-results.json).
Alias `localhost/aat-airflow-security-base:0.1.0` trỏ tới cùng ID security stage.
Scan chạy Trivy cố định digest, không ignore-unfixed hoặc che findings.
319 là số lượt HIGH/CRITICAL trong ba candidate, không phải số CVE duy nhất
hoặc kết quả scan toàn bộ baseline. Full scope hiện có 21 targets, chưa scan lại toàn bộ.

## LEX-003: đề nghị xác nhận mitigation đường build

Đã cài `libbrotli1 1.0.9-2+deb12u1` từ Debian security. Chain xác minh:
InRelease có chữ ký Debian → SHA256 Packages → SHA256 deb.
Artifact SHA256 `e27b3d655fa6fadd7a56f706687e94573c0af68b7d6df394a32a381a3a6c6d8b`.
[Provenance và chữ ký](t014-local-brotli-provenance.json) ghi nguồn, keyring,
thời hạn metadata và môi trường xác minh offline.

Installer kiểm hash trước khi gọi dpkg/giải mã; RUN đầu tiên trong Airflow stage
dùng `--network=none`, trước apt/network. Không có fallback tải package trong installer.
Security stage và final đều không còn CVE-2026-111497 theo scan đúng IDs trên.
Core 3.3.2, SDK 1.3.2, upstream constraints và Python dependency graph giữ nguyên.
Raw parent vẫn chứa package có finding: đây là mitigation có kiểm soát trong build,
không phải kết luận parent image đã sạch hoặc tự miễn trừ build-only.

Reviewer cần xác nhận đường bootstrap offline, provenance, thứ tự thực thi và giới hạn
raw parent đủ để đóng blocker LEX-003 cho phạm vi local đã đề xuất. Chưa có xác nhận này.
Nguồn vendor: [Debian CVE-2026-111497](https://security-tracker.debian.org/tracker/CVE-2026-111497).

## D3/LEX-079: đề nghị not affected có giới hạn

[Evidence](t014-local-lex079-evidence.json) kiểm đúng 12 contexts baseline và ba candidate.
Binary libz có cùng SHA256
`7e2a72b4c4b38c61e6962de6e3f4a5e9ae692e732c68deead10a7ce2135a7f68`.
Inventory và bảng symbols ELF không có entrypoints MiniZip liên quan.
[Debian CVE-2023-45853](https://security-tracker.debian.org/tracker/CVE-2023-45853)
phân biệt contrib/minizip với zlib được build trong Bookworm.

Đề xuất kỹ thuật: not affected chỉ cho zlib1g/CVE-2023-45853 trong đúng contexts
đã kiểm. Không áp dụng cho minizip, pyminizip, bản nhúng hay CVE khác.
Reviewer cần xác nhận kết luận và scope 12 baseline + 3 candidate; `reviewer_approved=false`.

## Mapping D2 sang candidate chưa được phê duyệt

[Delta chi tiết từng finding/ID](t014-local-findings-delta.json): 319 lượt đối chiếu
được advisory/package/installed version với 94 nhóm cũ; không có unmatched.
316 lượt thuộc nhóm C, ba lượt thuộc LEX-079. D2 vẫn chỉ duyệt đúng 147 nhóm C
và 771 contexts baseline ban đầu. Không tự mở rộng sang ba IDs mới.
Reviewer cần xác nhận mapping 316 lượt C sang đúng ba candidate, giữ nguyên owner,
controls, hạn review, hạn hết hiệu lực và điều kiện thu hồi trong proposal.

## Kết quả kiểm tra

| Tiêu chí | Kết quả | Bằng chứng |
| --- | --- | --- |
| Unit affected trên host | PASS, 12 | [log](t014-round2-logs/local-offline-patch-unit.log) |
| Installer Linux Python 3.12 | PASS, 5 | [log](t014-round2-logs/local-offline-patch-linux.log) |
| Runner candidate, gồm wiring mới | PASS, 18 | [log](t014-round2-logs/local-backend-tests.log) |
| Hash/provenance, offline patch | PASS kỹ thuật; review còn thiếu | [provenance](t014-local-brotli-provenance.json), [build stage](t014-round2-logs/local-security-base-build.log) |
| pip check, core/SDK, graph không đổi | PASS | [compatibility](t014-local-compatibility.json) |
| Init/auth/protected API/readiness | PASS | [startup](t014-round2-logs/local-candidate-startup.log), [auth](t014-round2-logs/local-auth.log), [DB](t014-round2-logs/local-health-databases.log), [Airflow](t014-round2-logs/local-health-airflow.log) |
| Operator login/UI | PASS | [UI](t014-local-airflow-ui.json) |
| Scan affected exact IDs | PASS thực thi; security FAIL | Hai scan liên kết ở trên |
| CI/clean checkout source mới | NOT_RUN | Source chưa commit; CI R3 chỉ là lịch sử |
| Scan đầy đủ 21 targets | NOT_RUN | Chỉ scan ba candidate bị ảnh hưởng |
| Restart/recovery candidate | NOT_RUN | Không đổi persistence/entrypoint; bằng chứng R3 không đổi thành PASS candidate |
| T014_FULL / Phase 1 đầy đủ | FAIL / BLOCKED | Findings và review chưa khép |
| T015/T016 | NOT_RUN / BLOCKED | Chưa kích hoạt quyền local |

Project thử riêng `aat-phase1-t014-local-20261109`, ports 43000/48000/48080 loopback.
Giữ nguyên các stack, dữ liệu, volumes, secrets hiện có. Không dừng dịch vụ sau kiểm tra.

## Quyết định còn thiếu và bước tiếp theo

1. Xác nhận đóng LEX-003 trên đường build có kiểm soát nêu trên, bao gồm giới hạn raw parent.
2. Xác nhận D3/LEX-079 not affected cho đúng 12 contexts baseline và ba candidate đã kiểm.
3. Xác nhận mapping nhóm C sang ba exact IDs mới; không xin duyệt lại D1/D2/D4.

Các xác nhận này bắt buộc theo chính yêu cầu chủ dự án và cơ chế review hiện hành.
Sau khi nhận đủ xác nhận, kiểm lại hạn/baseline/controls và mọi tiêu chí M0 trước khi
kích hoạt quyền local có hạn. Khi M0 hợp lệ, task tiếp theo chỉ T015/T016,
viết tests trước implementation; chưa triển khai task Phase 2 khác.
