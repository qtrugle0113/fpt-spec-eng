# T014 — remediation tiếp theo và giới hạn nâng core

Ngày 2026-11-09. Chủ dự án cho phép cập nhật dependency/base image/toolchain trong
T014 và commit/push/CI; nâng Airflow core hoặc đổi kiến trúc cần duyệt riêng.
Không thay tiêu chí nghiệm thu, constraints upstream hoặc reviewer checklists.

## Thay đổi trong phạm vi được phép

Nâng dnspython 2.8.0 → 2.9.0 bằng constraints hiệu lực và hash wheel riêng,
giữ Airflow core 3.3.2/SDK 1.3.2. Python >=3.11 được hỗ trợ; image dùng 3.12.
[Advisory của maintainer](https://github.com/rthalley/dnspython/security/advisories/GHSA-45c3-73f7-pv4m)
xác nhận phiên bản vá 2.9.0 cho CVE-2026-114605. Không bật các optional extras mới.
Kiểm unit bảo vệ policy, resolver/pip check, SDK import, auth/readiness và scan image
candidate riêng; không thay containers đang chạy để thử bản vá.

Finding setuptools 70.3.0 trong scan Airflow có `AnalyzedBy: sbom`, không là distribution
đang được import ở top-level. Không xóa SBOM hoặc cài setuptools mới để che finding;
cần xác định dependency chứa SBOM và xử lý artifact đó theo vendor.

## Đề xuất cần duyệt: nâng Airflow core sang dòng 3.4

Đề nghị cho phép đánh giá nâng Airflow 3.3.2 → 3.4.0, chưa áp dụng vào baseline.
[Changelog chính thức](https://airflow.apache.org/docs/docker-stack/changelog.html)
ghi image 3.4.0 chuyển Bookworm → Debian 13 Trixie, Python từ Docker Hardened Image.
[Debian tracker](https://security-tracker.debian.org/tracker/CVE-2025-7458)
ghi SQLite trên Trixie có bản vá, khác Bookworm đang dùng.
Đây là hướng loại nguyên nhân OS, không là bằng chứng image mới đạt security gate.

Phạm vi sau khi duyệt: resolve manifest Linux/amd64 và upstream constraints 3.4.0 mới
ở file riêng; giữ nguyên file upstream 3.3.2 để truy vết; kiểm provider/core/SDK/public
API/auth/UI/LocalExecutor/DB migrations và rollback trên bản sao dữ liệu cô lập.
Không thử migration trên volumes hiện hữu. Cập nhật contracts nếu API khác trước khi
implementation; scan đầy đủ base/build/final và chỉ nghiệm thu trên IDs cuối.
Nếu còn findings chưa xử lý, giữ BLOCKED. Chưa tuyên bố 3.4.0 tương thích hoặc sạch CVE.

Các base Python/Node/Go/Postgres có thể đánh giá Trixie độc lập dưới quyền đã cấp;
không trộn repository Trixie vào image Bookworm để nâng từng thư viện ABI.
Raw base findings vẫn thuộc phạm vi scan; không bỏ vì final đã được vá.

## Kết quả đánh giá base trước implementation

[Scan candidate theo IDs](../testing/t014-r3-candidate-security.json): Python Trixie
49 HIGH/0 CRITICAL, Node Trixie 58/0, Postgres Trixie 91/2; không chọn rebase ba image
này chỉ để giảm một vài CVE vì vẫn còn nhiều findings chưa giải quyết.
Go1.27.3 Alpine3.24 có 0 HIGH/0 CRITICAL (1 MEDIUM), chọn thay build toolchain Bookworm
vẫn giữ Go version/source gosu/CGO_ENABLED=0. Resolve manifest và hashes tại
[candidate manifests](../testing/t014-r3-candidate-manifests.json).
Gosu là binary static; kiểm build/version/UID và DB hardening trên candidate mới,
scan cả base lẫn gosu-build/final DB IDs. Không thay DB server versions hoặc volumes.
