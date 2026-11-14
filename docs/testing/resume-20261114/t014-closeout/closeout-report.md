# Tiếp tục xử lý T014 và T152

Trạng thái: **BLOCKED**, 150/152 task. Lượt này bổ sung kiểm chứng source đa nền
tảng và hồ sơ security đầy đủ; chưa đáp ứng điều kiện đóng T014 hoặc T152.

## SpecKit và kiểm chứng source

Đã đọc Analyze/Implement/Checklist/Converge trong `.github/skills/`. Prerequisites
PASS qua PowerShell với ExecutionPolicy Bypass theo từng process; không thay
execution policy hệ thống. Không có extension hooks. Checklist reviewer giữ nguyên.
Analyze xác định hai nghĩa vụ còn mở: security full baseline và CI đúng source.
Các nghĩa vụ đã được T014/T152 bao phủ; Converge chưa hoàn tất, không tạo task trùng.
Không có thay đổi application runtime trong lượt này để yêu cầu chạy lại toàn bộ
test tích hợp đã PASS. Ma trận A–AM/BR-08/SC/US và giới hạn image của từng lượt
vẫn theo [báo cáo nghiệm thu](../../acceptance-report.md).

Kiểm tra local các selector của `.github/workflows/sample-artifacts.yml`:

| Môi trường | Kết quả | Evidence |
| --- | --- | --- |
| Windows, Python 3.13 trên máy hiện tại | 15 PASS | [Windows](windows.txt) |
| Linux container, Python 3.12.16, image ID immutable trong command | 15 PASS | [Linux](linux.txt) |

Cùng snapshot 500 file tracked hiện tại, giữ nguyên raw bytes, gồm các thay đổi
chưa commit. [Manifest](source-checks.json) ghi SHA256 từng file, HEAD và commands.
Kiểm source/sample không đổi sau chạy. [Script tái hiện](run_source_checks.py).
Không gọi đây là remote CI PASS: không phải GitHub checkout, Windows không dùng
Python3.12 của workflow; phần Git checkout Windows/Linux vẫn NOT_RUN. Script
snapshot không chứng minh untracked application files hoặc full product acceptance.

## Hồ sơ security

[Hồ sơ 21 targets](security-review-packet.json) đối chiếu từng raw report với
immutable image ID, ghi checksum report và package/layer contexts. Đây là tổng hợp
scan đã có, không phải scan mới, không tạo approval và không đổi severity.
[Script tổng hợp](build_security_packet.py) có assertion số occurrences và image ID.

- 1.710 HIGH/CRITICAL occurrences, 362 nhóm theo advisory/package/version/fix/severity.
- 133 nhóm có FixedVersion; 229 nhóm không có FixedVersion trong scan.
- Các số này thuộc toàn bộ 21 targets; không thay thế số local10artifacts
  752 occurrences/216 nhóm/215 nhóm không có FixedVersion của báo cáo trước.
- Nhiều bản sửa OS đã nằm trong `airflow/docker/os-packages.lock` ở runtime stage.
  Findings tại upstream base hoặc stage trước runtime không được coi đã sửa nhờ
  runtime PASS. Đổi baseline/stage cần build/scan và kiểm chứng riêng.
- Setuptools70.3.0 từ SBOM Airflow vẫn cần review context. Không suy ra not-affected
  từ việc import runtime không thấy module; không xóa metadata để giảm scan count.

## Điều kiện còn thiếu để đóng hai task

1. Security owner/reviewer cần xử lý theo từng context trong hồ sơ: bản vá hoặc
   baseline mới đã build/scan/kiểm chứng, hoặc quyết định hợp lệ theo governance
   hiện hành. AI không tự tạo exception, waiver hay approval. Không có FixedVersion
   không có nghĩa finding an toàn hoặc không thể có vendor backport.
2. Cần CI Windows/Linux kiểm đúng source cuối cùng. Hiện người dùng cấm commit/push;
   CI lịch sử không bao phủ working tree. Có thể dùng cơ chế CI nhận snapshot nếu
   môi trường cung cấp và repo chấp nhận; local test không tự thay yêu cầu CI này.
3. Sau remediation làm thay đổi source/images, phải quét và chạy các selector bị
   ảnh hưởng trên đúng artifacts cuối, cập nhật acceptance matrix và Analyze.
   Chỉ đóng T152 khi T014_FULL=PASS và mọi mandatory gate đều đạt.

[Kiểm tra cuối](final-checks.json) ghi readiness, task count, diff và hash reviewer.
Demo giữ chạy, không sửa dữ liệu/volumes, không commit/push/public deploy. Không
tuyên bố full acceptance và không tự đánh dấu T014/T152.
