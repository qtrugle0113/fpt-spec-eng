# Tiếp tục nghiệm thu ngày 14/11/2026

**150/152 task đã hoàn tất.** T140/T151 đã khép; T014_FULL/T152 còn BLOCKED.

Lượt tiếp tục T014/T152 đã kiểm source Windows15/Linux15 PASS và lập hồ sơ review
đủ21targets/362nhóm HIGH/CRITICAL. Remote CI và full security vẫn chưa PASS;
xem [báo cáo khép cổng](resume-20261114/t014-closeout/closeout-report.md).

## Thay đổi đã kiểm chứng

- Nâng công cụ build `wheel` 0.45.1 → 0.46.2 và `setuptools` 80.9.0 → 84.2.1 trong ba Dockerfiles và ba
  `pyproject.toml`. Không sửa dependency runtime hoặc constraints của Airflow.
- Bỏ `rsync` khỏi runtime Airflow sau khi kiểm tra không có consumer trong repo
  hoặc reverse dependency đã cài. Giữ assertions executable không tồn tại và pip check.
- PostgreSQL fixture readiness dùng TCP để không nhận nhầm server Unix socket
  tạm của entrypoint; lỗi tạo role ghi stderr đã che mật khẩu.
- Verifier T140 bảo toàn CSV quoting, kiểm tra prefix đã commit khi extraction
  recovery đang chạy, và kiểm tra chính xác toàn bộ dữ liệu ở kết quả cuối.
- Đối với commit/refresh, verifier tạm dừng đúng child đã xác minh journal và
  command line khi thấy SQL bị chặn. Sau restart, đích phải không đổi khi lock còn
  giữ; sau đó nhả fixture lock trước retry để không tiêu hết `lock_timeout=3s`.
  Sau recovery vẫn phải có owner mới, cùng binding, staging hợp lệ, task success,
  COMMIT_VERIFIED, hết commit uncertainty và toàn bộ giá trị đích đúng nguồn.
- Lifecycle có thể project phase `COMMIT_VERIFIED` khi đối soát ledger thành công;
  verifier chấp nhận phase đó và `COMPLETE`, cùng các điều kiện an toàn còn lại.
- Scanner nhận immutable image ID cho raw base targets; mutable refs vẫn phải
  được phân giải qua các FROM đã khóa.

## Bằng chứng mới

| Phạm vi | Kết quả |
| --- | --- |
| T140 đầy đủ | [PASS](resume-20261112/aat-t140-045d42c5/result.json), 1749.900s, startup141.031s; extraction/commit/FULL_REFRESH, persistence và fail-closed PASS; cleanup0 |
| T151 | Sample pack verification PASS; prerequisite T140 đã PASS; [verification](resume-20261113/current-t151-sample-checks/regression-results.json) |
| Build/scan 10 artifacts cuối | [LOCAL_POLICY_MATCH](resume-20261111/portable-336939fd/local-policy-review.json); không phải full security PASS |
| Unit/API trên image cuối | 225 PASS; SDK factory 4 PASS; [kết quả](resume-20261114/final-unit-api/regression-results.json) |
| Demo trên image cuối | 6 browser checks desktop/mobile PASS/58.5s và exact target verifier PASS, cleanup0; [kết quả](resume-20261114/final-demo-workflow/result.json) |
| Resource enforcement | Cgroup memory thực khớp cấu hình của cả8services demo; [môi trường và image IDs](resume-20261114/environment.json) |
| Airflow sau bỏ rsync | Tám hướng ETL và hai ca scheduled, 10 PASS/394.424s; [kết quả](resume-20261114/rsync-airflow-routes/regression-results.json) |
| Memory stress | 22.000 dòng, payload 1.441.792.000 bytes, peak RSS 102.817.792 bytes dưới budget 512MiB, 174 disk parts; 1 PASS/147.876s; [kết quả](resume-20261114/memory-r6/regression-results.json) |
| Installed application files | Application files và phiên bản runtime dependencies không đổi khi nâng công cụ build; [đối chiếu cuối](resume-20261114/installed-source-comparison-final.json) |
| Commit diagnostic | PASS, task retry2 và final target đúng; [kết quả](resume-20261114/commit-diagnostic-r3/result.json) |
| Full baseline scan | 21 targets, 1.710 HIGH/CRITICAL occurrences; [scan](resume-20261114/full-baseline-final/candidate-security.json), [review BLOCKED](resume-20261114/full-baseline-final/local-policy-review.json) |
| Local artifact triage | 752 occurrences/216 nhóm, 215 nhóm không ghi FixedVersion; [triage](resume-20261114/security-triage.json) |

Các lượt lỗi được giữ nguyên. Memory r4 lỗi setup trước test; r5 vượt deadline
khi có build/test khác chạy song song; r6 PASS với deadline/assertions không đổi.
T140 `53adb284` FAIL ở commit do fixture giữ lock qua retry. Lượt `2646634e`
FAIL vì `podman cp` timeout10s khi scan lớn chạy song song, cleanup0. FULL_REFRESH
diagnostic đã tới task success/COMMIT_VERIFIED nhưng verifier đọc trạng thái bị
timeout; không chuyển bằng chứng FAIL đó thành PASS.

## Phạm vi của bằng chứng và gates còn thiếu

T140 chạy trên canonical images ghi trong artifact045d42c5, trước lượt nâng setuptools cuối. Sau nâng setuptools, application files và runtime package versions byte-for-byte/giá trị không đổi; build/scan và Unit/API cuối được chạy riêng. Không gán image IDs cuối cho các lượt test trước đó.

T140 đã PASS toàn selector ở namespace `aat-t140-045d42c5`, không dùng các
diagnostic riêng lẻ để đóng task. T151 đã khép dependency và verification.
Startup141.031s được đo sau bước chuẩn bị build/scan admission; không phải thời
gian tải/build từ một image store trống. Toàn selector mất1749.900s.

Demo được giữ chạy ở <http://localhost:23000>, Airflow <http://localhost:28080>,
project `aat-portable-demo-516bea17`. Rollout image cuối giữ nguyên volumes/dữ liệu;
frontend được restart sau khi thay backend để cập nhật địa chỉ upstream.

Các raw reports của full baseline khớp image IDs trong manifest. Findings gồm lặp
qua stages/bases và các context cần review; không kết luận tất cả exploitable,
không tự cấp waiver hoặc not-affected. Finding setuptools70.3.0 của Airflow được
scanner phân tích từ SBOM; import runtime không có setuptools. Điều này là thông
tin cho reviewer, chưa phải kết luận not-affected.

CI của patch hiện tại NOT_RUN: người dùng cấm commit/push. Các CI cũ không chứng
minh patch này đã PASS. Giữ nguyên Constitution, approval, hạn local và marker
checklist reviewer. Không public deploy hoặc dùng dữ liệu quan trọng.

[Rà soát SpecKit cuối](resume-20261114/speckit-final-review.md) và
[kiểm repository](resume-20261114/final-repository-check.json) ghi task inventory,
dependency, checksum reviewer, liên kết nội bộ, hash receipt và readiness thực tế.
