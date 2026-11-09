# T014 — remediation và nghiệm thu vòng3, 2026-11-09

**T014: BLOCKED. Gate Phase1: BLOCKED. Chưa triển khai Phase2.**

Implementation commit `d57db0949bc310da752de578c3522920041e9ca2` đã push lên nhánh
`001-airflow-automation-tool-t014`. Các cập nhật bằng chứng sau commit này không đổi
implementation. [Kết quả máy đọc và IDs](t014-r3-results.json),
[phương án/giới hạn](../proposals/t014-round3-remediation.md).

## Thay đổi đã thực hiện

- Hoàn tất workflow speckit-implement: prerequisites đúng feature001;
  requirements16/16 và spec-quality48/48 PASS, checklists chỉ đọc. Không có extensions.yml
  trước/sau thực thi. Giữ 152 tasks, chỉ13 task hoàn thành, T014 vẫn `[ ]`.
- Đối chiếu source/môi trường và snapshot A/B; Constitution, checklists, upstream
  constraints và samples/templates không đổi. [Baseline check](t014-r3-baseline-check.json)
  ghi riêng ID airflow-wheels đã thay do build của chính lượt này trước khi capture.
- Cập nhật Plan/Research/phương án trước implementation. Thêm override dnspython2.8.0→2.9.0
  vào policy/lock hiệu lực, wheel đã tải và đối chiếu [SHA256 PyPI](t014-r3-python-artifacts.json).
  Upstream constraints giữ SHA256
  `821effd0f491975682f2774fca3427d7bc2f59ca6de68dcb413ad2c8f890e58c`;
  core3.3.2/SDK1.3.2, certifi/urllib3 của A và browser của B giữ nguyên.
  Test policy có RED trước implementation, sau đó PASS.
- Chuyển Go1.27.3 Bookworm sang Alpine3.24 theo digest Linux/amd64 đã scan; giữ source
  gosu1.19 và CGO_ENABLED=0. [Binary hashes](t014-r3-gosu-binary-provenance.json) chứng minh
  gosu trong build stage và hai final DB images giống nhau từng byte. Cache có thể giữ
  final DB IDs cũ vì binary tái build giống nhau; không suy ID mới từ việc đổi FROM stage.
- Đánh giá Python/Node/Postgres Trixie trước khi chọn baseline. Scan tương ứng49/0,
  58/0,91/2 HIGH/CRITICAL nên không áp dụng rebase hàng loạt.
  [Candidate manifests](t014-r3-candidate-manifests.json), [scan](t014-r3-candidate-security.json).
  Airflow3.4 chỉ được resolve manifest/so schema, chưa nâng core hoặc migration.

## Kết quả kiểm chứng

| Tiêu chí | Kết quả | Bằng chứng/phạm vi |
| --- | --- | --- |
| Policy/hash/sample/source-lock local | PASS | [10 tests](t014-round2-logs/r3-static.log) |
| Clean checkout d57db09 | PASS | Detached worktree,10 tests và git status sạch; [log](t014-round2-logs/r3-clean-static.log) |
| CI Windows/Linux đúng source triển khai | PASS | [Run42548651297](https://github.com/qtrugle0113/fpt-spec-eng/actions/runs/42548651297), [jobs/SHA](t014-r3-ci.json); sample bytes và policy/source-lock, không phải CI full runtime |
| Fresh startup + restart/persistence | PASS | [1 test,1310.699s](t014-round2-logs/r3-startup.log); startup một lệnh, down không-v, secret bytes/DB edits/artifact markers giữ nguyên |
| Unit profile trên image cuối | PASS | [13/13](t014-round2-logs/r3-unit.log), Python3.12/Linux |
| Image compatibility | PASS | [5/5](t014-round2-logs/r3-compatibility-final.log);8bases/platform/pins, pip check, core/SDK/override provenance, real Chromium |
| DB binary/UID/server hardening | PASS | [2/2](t014-round2-logs/r3-database-hardening.log), binary hash so build stage |
| Runtime/fault/readiness/secret logs | PASS | [7/7,214.125s](t014-round2-logs/r3-runtime.log), chỉ namespace mới |
| Playwright desktop/mobile/private nginx paths | PASS | [4/4](t014-round2-logs/r3-e2e.log) |
| Airflow service auth/API/UI | PASS | [Anonymous bị chặn, token exchange/protected DAG API](t014-round2-logs/r3-auth.log); không log credentials |
| Airflow operator browser login | PASS | [Chromium158/protected DAG API200](t014-r3-airflow-ui.json) |
| Frontend typecheck/build | PASS | [Build thực trong container](t014-round2-logs/r3-frontend-build.log) |
| Npm full/production audit | PASS | 0 findings [full](t014-r3-npm-audit-full.json), [production](t014-r3-npm-audit-production.json) |
| HTTP/loopback exposure | PASS | [Probes](t014-r3-http-probes.json), [Windows listeners](t014-r3-listeners.json); ready404 đúng bootstrap scope |
| Scanner execution và final IDs | PASS | 20targets, [full scan](t014-round2-logs/r3-scan.log) + [DB rescan](t014-round2-logs/r3-rescan.log); final ID mismatches=0 trong results |
| Security acceptance | FAIL | 784 HIGH/CRITICAL occurrences chưa được xử lý/review đầy đủ;0 reviewer waivers |
| Restore fixture DB17.6/8.4.7 lịch sử | NOT_RUN | Máy này không có fixture cũ; server versions không đổi trong vòng3, không kế thừa test lịch sử thành PASS mới |
| Airflow3.4 runtime/migration/compatibility | NOT_RUN | Ngoài quyền nâng core hiện tại; chỉ có [static API comparison](t014-r3-airflow-api-candidate.json) |

Fresh/restart chạy từ workspace có implementation khớp commit d57db09; clean checkout
được kiểm riêng bằng static/sample tests. Không mô tả startup workspace thành startup
từ detached checkout. Bootstrap PASS không nghiệm thu ETL nghiệp vụ hoặc Phase2.

## Security còn lại

[Final scan20targets](t014-r3-security.json) giữ provenance
[lượt đầu](t014-r3-security-first-pass.json) và [rescan hai DB IDs sau restart](t014-r3-rescan.json).
Tổng1327→784 occurrences trong cùng20targets;7final images/runners248→247.
Đây là số lần finding theo package/image, không phải số CVE duy nhất hoặc số exploit.
Go base và gosu-build mới đều0HIGH/0CRITICAL; Airflow105HIGH/5CRITICAL.
Backend40/2, Postgres50/3, backend-tests40/2; final frontend/MySQL/E2E0/0.
Raw Python/Airflow/Node/Playwright/Postgres/MySQL bases và các build stages còn findings,
không loại vì chỉ dùng khi build. Không ignore-unfixed, không sửa SBOM, không hạ severity.

[Vendor review mới](t014-r3-vendor-review.json) có149groups:81Debian,30Go,1Ubuntu,
37language groups cần review;148OPEN và1PROPOSED_NOT_AFFECTED_REVIEW_REQUIRED.
Không nhóm nào được reviewer duyệt. Snapshot vendor giữ URLs/hashes/thời điểm;
[Go advisories](t014-r3-go-advisories.json). Resolved theo vendor vẫn cần so installed
version; NO_FIX không được coi PASS.

Finding setuptools70.3.0 nằm trong SBOM của pip, vendor.txt có setuptools và pkg_resources
vẫn được phân phối; không có directory vendored setuptools. [Inventory](t014-r3-pip-sbom-review.json)
là bằng chứng cho reviewer đánh giá phạm vi PackageIndex, chưa là waiver/not-affected.
Các OS findings như SQLite Bookworm và đề xuất zlib trước đó vẫn mở.

## Môi trường, bảo toàn và bước tiếp theo

Podman client/server6.1.1, Compose provider5.6.0, Linux/amd64/rootful/cgroupv2,
12CPU/~7.60GiB engine RAM. Project mới `aat-phase1-t014-r3-20261109`, ports23000/28000/28080.
Stack A/B13000/18000/18080 và sáu containers có trước được giữ; không xóa volumes/secrets,
không reset machine/prune. Cuối kiểm thử bốn init Exited(0), tám services healthy trên
candidate; results ghi riêng trạng thái cả hai project.
Windows physical disk free được ghi tại [host disk](t014-r3-host-disk.json); guest disk
còn khoảng899GiB lúc scan, không đồng nghĩa host đạt khuyến nghị80GiB free.
Không quảng bá baseline lịch sử5.8.3/5.8.9 hoặc mức RAM12GiB đã được kiểm trong lượt này.

Blocker đóng T014 hiện là security: tiếp tục bản vá/backport được hỗ trợ hoặc review
not-affected bằng bằng chứng cụ thể. Nâng core3.4 cần duyệt riêng theo yêu cầu chủ dự án;
[phương án](../proposals/t014-round3-remediation.md) ghi schema thay đổi và phạm vi kiểm
trên bản sao dữ liệu, không cam kết nâng core đơn lẻ sẽ PASS. Không tự chấp nhận rủi ro.
Sau remediation/review tiếp theo phải kiểm affected gates, exact IDs và CI đúng source mới.
