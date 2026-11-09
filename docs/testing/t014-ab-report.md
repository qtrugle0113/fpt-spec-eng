# Kết quả triển khai A/B trong T014 — 2026-11-09

**A/B đã được duyệt và triển khai. T014: BLOCKED. Gate Phase1: BLOCKED. Chưa triển khai Phase2.**

Chủ dự án duyệt [phương án A/B](../proposals/t014-round2-approval.md) trong hội thoại
ngày2026-11-09 (Asia/Yakutsk). Áp dụng [speckit-implement](../../.github/skills/speckit-implement/SKILL.md),
feature001, chỉ T014. HEAD lúc bắt đầu là `b29ae868bcf4a86f0bdb42dfedc4f58ed5dd0b4b`;
source lượt này vẫn ở working tree, chưa commit/push. Snapshot trước A/B được giữ tại
[báo cáo trước](t014-current-report.md#snapshot-trước-khi-được-duyệt-ab).

## Workflow và môi trường

- Prerequisites resolve đúng feature; requirements16/16 và spec-quality48/48 PASS,
  reviewer checklists chỉ đọc. Không có `extensions.yml`; không có hooks trước/sau implement.
- Plan/Research và phạm vi task đã cập nhật trước implementation. Giữ nguyên Constitution,
  Spec/BR-08, Data Model, API routes và bytes của samples/templates.
- Runtime thực tế: Podman client/server6.1.1, Linux/amd64, rootful/cgroupv2,
  12CPU và 7.60GiB RAM theo engine; Docker Compose5.6.0 portable đã kiểm SHA256.
  Đây là tổ hợp mới được kiểm bootstrap, không tự kế thừa kết quả5.8.3/5.8.9 lịch sử.
- Project test riêng `aat-phase1-t014-ab-20261109`, source là workspace gốc; không dùng fixture
  copy thay checkout. Bốn init Exited(0), tám services healthy sau kiểm thử.
  Cổng Windows13000/18000/18080 thực tế chỉ LISTEN127.0.0.1.
- Sáu containers có trước không bị thay/xóa; không sửa volumes, secrets hoặc dữ liệu của chúng.
  Dữ liệu mà startup/persistence test sửa thuộc namespace test mới.

## A — constraints hiệu lực và provenance

Upstream `airflow/docker/constraints-3.12.txt` giữ nguyên SHA256
`821effd0f491975682f2774fca3427d7bc2f59ca6de68dcb413ad2c8f890e58c`.
`constraints-policy.json` chỉ cho phép certifi2026.7.22→2026.10.18 và urllib3 2.7.0→2.8.0.
`build_constraints.py` từ chối upstream khác hash, thiếu/sai pin hoặc override ngoài danh sách;
build tạo `/opt/aat/constraints-effective-3.12.txt` và `constraints-provenance.json` riêng.

Override wheels trong `overrides.lock` đã tải và đối chiếu SHA256 với metadata PyPI,
[artifact provenance](t014-ab-artifacts.json). Providers/ETL được install dưới bản hiệu lực,
không ghép hai constraints xung đột. Pip check/import core và SDK đều PASS.
Trong container thật: Airflow/core3.3.2, Task SDK1.3.2, certifi2026.10.18, urllib3 2.8.0,
pip26.3; [package graph/provenance](t014-ab-airflow-packages.json).
TDD có3tests RED vì implementation chưa tồn tại, sau triển khai đều PASS.

## B — đồng bộ client/browser/OS

Frontend và E2E cùng khóa @playwright/test/playwright/playwright-core1.65.0.
[Npm delta](t014-ab-npm-lock-delta.json) chỉ nâng ba packages đó và bỏ optional fsevents
không còn được phiên bản mới yêu cầu. Build vẫn dùng Node22.23.4/npm12.2.2.

Browser base là `mcr.microsoft.com/playwright:v1.65.0-resolute` theo manifest Linux/amd64
`fb9978a801599ea0a57079eb642ad75cb52dbe1b162c8bf1fc989a603aa39218`;
[inspect/lock](t014-ab-browser-base.json). Runtime image này bundle Node26.13.0;
không dùng Node của host thay browser runtime. Chromium thực tế158.0.8127.18 đã chạy.
OS lock Resolute khóa apt/libapt-pkg7.0=3.2.1ubuntu0.1, không tái dùng Noble lock.
Global npm không có consumer trong final runner được loại; build dependencies vẫn được scan.

## Kiểm chứng

| Hạng mục | Kết quả thực tế |
| --- | --- |
| Fresh startup + restart không-v | PASS752.059s; secret bytes, sửa đổi DB mẫu và artifacts giữ nguyên |
| Test profile backend-tests | PASS13/13 trên Python3.12.16/Linux; gồm3tests bảo vệ override policy |
| Test profile Playwright | PASS4/4 desktop/mobile, shell và private nginx prefixes |
| Image compatibility | PASS5/5:8base digests/platform/IDs, pip check, core/SDK, override provenance và browser thực |
| Runtime/fault injection | PASS7/7: init fail chặn consumer, mounts/UID/limits/order, query/heartbeat down, phục hồi và secret logs |
| Airflow service auth/API/UI | PASS anonymous bị chặn, token exchange và protected DAG list thành công; không in token/password |
| Airflow operator UI | PASS public login và protected DAG API200 trên Chromium158; [kết quả](t014-ab-airflow-ui.json) |
| Shell bổ sung | PASS12route/viewport1440/390, navigation search/mobile menu,0page errors |
| Frontend build/typecheck | PASS npm ci, TypeScript/Vite; [build stages](t014-ab-build-stages.json) |
| Npm full/production audit | PASS0vulnerabilities; [full](t014-ab-npm-audit-full.json), [production](t014-ab-npm-audit-production.json) |
| Health HTTP | Shell/live/Airflow200, backend ready404 đúng phạm vi bootstrap; [probes](t014-ab-http-probes.json) |
| CI bytes mẫu Windows/Linux tại HEAD b29ae86 | PASS [run42495227273](https://github.com/qtrugle0113/fpt-spec-eng/actions/runs/42495227273), chỉ cho SHA này |
| CI source mới/working tree | NOT_RUN; chưa có commit chứa toàn bộ thay đổi mới |
| Clean Git checkout theo SHA chứa A/B | NOT_RUN; fresh startup từ working tree không thay checkout immutable |
| Restore từ DB17.6/8.4.7 cũ | NOT_RUN lại trong lượt A/B; machine này không có fixture cũ, giữ bằng chứng lịch sử riêng |

Bootstrap PASS không nghiệm thu Connections CRUD, DAG Builder hoặc ETL; backend ready404
không được mô tả thành product readiness. Không chạy Phase2 hoặc sửa checkbox T014 thành hoàn thành.

## Security — scan đúng IDs cuối

Trivy0.76.1 dùng digest cố định, scan tất cả severity, không ignore-unfixed. Script resolve
cả8base refs từ FROM immutable và preflight đủ targets trước khi tạo volumes. Export theo
image ID đã inspect; raw report ImageID được đối chiếu lại. Scanner chỉ nhận archive/cache/
report volumes, không engine socket hoặc secret volumes.

Quét20targets:8bases,5build/toolchain stages,7final images. Sau sửa công cụ scan, test runner
được rebuild/test/scan lại để chứa source mới nhất; báo cáo tổng hợp giữ provenance từng lượt.
[Kết quả tổng hợp](t014-ab-security.json), [lượt20targets](t014-ab-security-first-pass.json),
[runner scan cuối](t014-ab-backend-tests-rescan.json). Đối chiếu tags/containers cuối với
scan IDs không có mismatch. Không thay PASS của execution bằng security PASS.

| Target | HIGH | CRITICAL |
| --- | ---: | ---: |
| python-build-base |40|2|
| airflow-build-base |146|22|
| nginx-build-base |0|0|
| playwright-build-base |8|0|
| go-build-base |267|4|
| node-build-base |44|1|
| frontend-build |34|1|
| backend-wheels |43|2|
| airflow-wheels |43|2|
| e2e-dependencies |34|1|
| backend |40|2|
| airflow |106|5|
| frontend |0|0|
| postgres |50|3|
| postgres-build-base |75|4|
| mysql-build-base |33|2|
| gosu-build |267|4|
| mysql |0|0|
| backend-tests |40|2|
| e2e-tests |0|0|

Tổng 1327HIGH/CRITICAL occurrences trong20targets; riêng7final images là
248occurrences. Đây là số lần finding theo package/image, không phải số CVE duy nhất
hoặc xác nhận exploitability. Phạm vi rộng hơn các snapshot3/12/15targets cũ nên không so
trực tiếp tổng để kết luận tăng/giảm rủi ro. Final frontend/MySQL/E2E không có HIGH/CRITICAL
trong snapshot, không có nghĩa scanner bao phủ mọi native browser/runtime risk.

## Triage vendor và giới hạn

[Vendor review](t014-ab-vendor-review.json) chia thành 341nhóm theo ecosystem,
source package/version và advisory, giữ từng target/package/severity. Có273nhóm Debian,
30nhóm Go,1nhóm Ubuntu và37nhóm language packages cần review thêm;0nhóm được reviewer duyệt.
Snapshot vendor có thời điểm/hash/URL; [Go advisories](t014-ab-go-advisories.json) lưu ranges
chính thức. Không tự hạ severity hoặc chấp nhận rủi ro.

- Debian Bookworm:255nhóm vendor còn open;18nhóm được vendor đánh resolved cần đối chiếu
  fixed version với package thực tế, không tự suy installed image đã vá.
- [CVE-2023-45853](https://security-tracker.debian.org/tracker/CVE-2023-45853): vendor ghi
  contrib/minizip không được build từ src:zlib ở Bookworm. Chỉ đề xuất not-affected cho
  nhóm binary tương ứng, vẫn `PROPOSED_NOT_AFFECTED_REVIEW_REQUIRED`; không miễn trừ bản nhúng.
- [CVE-2025-7458](https://security-tracker.debian.org/tracker/CVE-2025-7458): SQLite Bookworm
  vẫn vulnerable/no-dsa; giữ OPEN/BLOCKED.
- [CVE-2026-109518](https://ubuntu.com/security/CVE-2026-109518): Ubuntu xác nhận fix Resolute
  3.2.1ubuntu0.1. B đã vá final runner; raw browser base3.2.0 còn findings, vẫn giữ để review build path.
- Các đề xuất52build-base occurrences trong review C cũ chưa được duyệt bởi quyết định A/B.
  Phạm vi Go/compiler/base OS được scan riêng; không loại findings vì chỉ dùng lúc build.
- Scanner có146occurrences ghi FixedVersion; đây là candidates cho vòng remediation tiếp,
  không phải pin mới đã duyệt hoặc compatibility PASS. Các NO_FIX vẫn cần review riêng.

## Tái lập trên project hiện có

```powershell
$env:PODMAN_COMPOSE_PROVIDER=(Resolve-Path .tools/docker-compose-5.6.0.exe).Path
$env:COMPOSE_PROJECT_NAME='aat-phase1-t014-ab-20261109'
$env:AAT_FRONTEND_PORT='13000'
$env:AAT_BACKEND_PORT='18000'
$env:AAT_AIRFLOW_PORT='18080'
podman compose ps -a
podman compose --profile test run --rm --no-deps backend-tests
podman compose --profile test run --rm --no-deps e2e-tests
```

Candidate đang giữ tại http://localhost:13000, liveness18000 và Airflow18080.
Không thêm `down -v`, không reset volumes hoặc tạo stack trùng cổng. Init/worker hiện vẫn
là bootstrap, không là schema/Operation của Phase2. Secret vẫn ở private volumes.

Scan có thể tái lập bằng `AAT_SCAN_REPORT` riêng và `python tests/tools/scan_phase1_images.py`
sau khi build đủ targets theo `t014-ab-build-stages.json`. Dùng UTF-8 cho host Python;
deps/tests ứng dụng chạy trong images. Logs đã lưu tại `t014-round2-logs/ab-*.log`:
[startup](t014-round2-logs/ab-startup.log), [unit](t014-round2-logs/ab-unit.log),
[E2E](t014-round2-logs/ab-e2e.log), [compatibility](t014-round2-logs/ab-compatibility.log),
[runtime](t014-round2-logs/ab-runtime.log), [scan](t014-round2-logs/ab-scan.log).
[Kết quả máy đọc](t014-ab-results.json) ghi hashes, image IDs và trạng thái cuối.

## Lỗi đã xử lý và phần còn lại

- TDD RED ban đầu là3tests chưa có implementation, sau đó PASS. Host encoding cp1252 làm
  một lần probe không gửi được script; retry UTF-8 có kiểm marker thành công, không coi lần lỗi là PASS.
- Hai lần scan đầu FAIL do local store không có mutable tag scanner/base dù có digest.
  Đã khóa scanner và derive base refs từ FROM, thêm full preflight và ID assertions;
  lượt cuối20targets và runner rescan đều PASS execution. Chỉ cleanup volumes thuộc lượt lỗi.
- PowerShell có thể bọc stderr unittest thành NativeCommandError; kết luận theo exit code
  và kết quả tests. Không có regression ứng dụng còn FAIL trong các selector đã chạy.

Để đóng T014 cần xử lý/review findings còn lại, nghiệm thu mọi thay đổi tiếp theo rồi CI
đúng source cuối. Các miễn trừ cần reviewer duyệt bằng chứng riêng; A/B không cấp quyền đó.
Chưa commit/push source hoặc chạy CI remote cho working tree. T014 giữ `[ ]`, Phase1 BLOCKED.
