# Trạng thái T014 sau remediation vòng3 — 2026-11-09

**T014/Phase1 vẫn BLOCKED bởi security. Implementation d57db09 đã commit/push và CI
Windows/Linux PASS; clean checkout static/sample tests PASS. Chưa triển khai Phase2.**

Kết quả mới nhất: [báo cáo vòng3](t014-r3-report.md), [results/IDs](t014-r3-results.json),
[scan20targets](t014-r3-security.json), [149nhóm vendor review](t014-r3-vendor-review.json).
Đã vá dnspython2.9.0 và chuyển Go toolchain sang Alpine3.24; giữ Airflow3.3.2/upstream
constraints. Fresh/restart1310.699s,13unit/5compatibility/7runtime/4E2E, auth/operator UI,
frontend build và npm audit đều PASS. Scan final IDs khớp, HIGH/CRITICAL1327→784;
7final images/runners còn247occurrences, chưa có reviewer waiver. Không tự đóng gate.
Candidate riêng23000/28000/28080; stack A/B và dữ liệu/volumes/secrets hiện có được giữ.

## Snapshot sau A/B, trước remediation vòng3

**A/B đã được chủ dự án duyệt và triển khai. T014/Phase1 vẫn BLOCKED bởi security và CI source mới.**

Kết quả mới nhất tại [báo cáo triển khai A/B](t014-ab-report.md). Airflow giữ upstream
constraints bất biến, chỉ thay hai pin certifi/urllib3 bằng policy riêng. Browser runner
đã chuyển đồng bộ sang Playwright1.65.0/Resolute/Chromium158.0.8127.18.
Fresh/restart/persistence PASS752.059s; test profile13unit/4E2E, compatibility5,
runtime/fault injection7, shell12route/viewport và đăng nhập UI Airflow đều PASS.
Các kết quả scan/triage và phạm vi CI được ghi riêng trong báo cáo A/B; không tự miễn trừ findings.

## Snapshot trước khi được duyệt A/B

Các mục bên dưới giữ bằng chứng của lượt trước; các câu “chờ duyệt A/B” và phạm vi test/scan
ở snapshot không phải trạng thái hiện hành. Không dùng chúng thay kết quả sau triển khai.

**T014: BLOCKED. Gate Phase1: BLOCKED. Chưa triển khai Phase2.**

Áp dụng [speckit-implement](../../.github/skills/speckit-implement/SKILL.md), feature
`specs/001-airflow-automation-tool`, phạm vi T014. HEAD khi bắt đầu là
`b29ae868bcf4a86f0bdb42dfedc4f58ed5dd0b4b`, nhánh `001-airflow-automation-tool-t014`;
các thay đổi lượt này nằm trong working tree, chưa commit/push. Kết quả dưới đây chỉ
nghiệm thu đúng phạm vi đã chạy, không thay toàn bộ compatibility/runtime/security gates.

## Prerequisites và môi trường

- `check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks` resolve đúng feature và
  research/data-model/contracts/quickstart/tasks. Tasks hiện152mục,13mục đã đánh dấu hoàn thành.
- Checklist read-only: requirements16/16, spec-quality48/48, đều PASS. Không đổi marker.
- Không có `.specify/extensions.yml`; không có before/after implementation hooks để chạy.
- Podman machine có sẵn đang tắt và được khởi động lại; không tạo/reset machine hoặc
  sửa các containers/volumes có trước. Client/server hiện6.1.1, Linux/amd64,
  rootful/cgroupv2, khoảng7,6GiB RAM. Đây là môi trường khác baseline5.8.3/5.8.9 cũ.
- Provider tự chọn ban đầu là podman-compose1.6.0. Để kiểm Compose config, dùng bản
  Docker Compose5.6.0 portable tại `.tools/docker-compose-5.6.0.exe`, lấy từ
  [release chính thức](https://github.com/docker/compose/releases/tag/v5.6.0), SHA256
  `8aeaa0055e660e12cf07cd70680dc8333957fe6718528b91ec3da084eab62483` đã đối chiếu release metadata.
  Không cài/thay provider mặc định. `podman compose config --quiet` PASS với provider được pin.
- Host Python3.13/Node24 không được dùng thay runtime ứng dụng. Build/test ứng dụng dùng
  Python3.12.16/Node22.23.4 trong images được khóa.

## Thay đổi thực hiện

1. `record_image_baseline.py` lấy nguồn từ FROM trong sáu Dockerfiles thật, từ chối pin
   thiếu/mâu thuẫn; inspect đúng digest immutable, không chọn RepoDigests đầu tiên của tag.
2. `validate_lock` phát hiện digest lệch FROM, thiếu/trùng entry hoặc platform sai.
   Compatibility test đối chiếu thêm image ID. Ba hồi quy unit kiểm valid/internal stages,
   sai digest/thiếu/trùng entry, unpinned/conflicting FROM; CI Windows/Linux thêm selector này
   và kiểm source-lock bằng standard library, không cần Podman trên runner CI.
3. Node/nginx/PostgreSQL trong `images.lock` đổi cách ghi từ digest index sang digest manifest
   đã được Dockerfile dùng sẵn. [Registry evidence](t014-registry-verification.json) xác minh
   SHA256 manifest/config của cả8bases và Linux/amd64; cả8image IDs giữ nguyên. Không đổi
   Dockerfile FROM, package pin, official Airflow constraints hoặc cặp Playwright/browser.
4. Đồng bộ trạng thái tài liệu, bổ sung CI đúng HEAD và bằng chứng kiểm thử/scan mới;
   giữ nguyên các snapshot lịch sử và raw findings. T014 vẫn `[ ]`.

Hồi quy source-lock đã thất bại trước sửa lock với lỗi digest Node khác FROM; sau sửa PASS.
Hai file validator/unit mới trong test runner có SHA256 khớp source working tree.

## Kiểm chứng thực tế

| Kiểm chứng | Kết quả và phạm vi |
| --- | --- |
| Registry8bases | PASS manifest/config SHA256, Linux/amd64, image IDs không đổi; không thay runtime test |
| Backend test image | Build/pip check PASS; pytest10/10 PASS, gồm secrets idempotence/fail-closed, boundaries, sample bytes và3hồi quy lock |
| Frontend build | PASS npm ci, TypeScript và Vite build; Node22.23.4/npm12.2.2 trong image |
| Npm full audit | PASS0vulnerabilities, [JSON](t014-current-npm-audit.json); không bao phủ OS/global tooling |
| Nginx/proxy fixture | PASS4/4: config, deep link, public proxy và private prefixes GET/POST có/không bearer; private requests không tới upstream fixture |
| Selector CI lock mới chạy local | PASS4/4; không thay remote Windows/Linux |
| CI commit HEAD | PASS cả Windows/Linux, [run42495227273](https://github.com/qtrugle0113/fpt-spec-eng/actions/runs/42495227273), head_sha đúng b29ae86; [evidence](t014-ci-runs.json) |
| CI working tree có thay đổi lượt này | NOT_RUN; chưa có commit/SHA chứa source và workflow mới |
| Full bootstrap/DB/Airflow/Playwright | NOT_RUN trên máy hiện tại; chưa nghiệm thu tổ hợp Podman6.1.1/Compose5.6.0 hoặc kế thừa kết quả máy cũ |
| Full image compatibility và scan toàn baseline | NOT_RUN trong lượt này; registry8bases và scan3targets không thay các gate còn lại |

Source hiện tại đã build được ngay từ workspace gốc; không gặp lại lỗi ACL cache lịch sử
trong hai build này. Điều đó không thay fresh/restart/persistence trên full stack.
Nginx proxy test dùng upstream fixture cô lập, không được xem là backend sản phẩm PASS.

## Scan và triage còn mở

Trivy0.76.1 theo digest đã duyệt, DB metadata và image IDs ghi trong các JSON; scan mọi
severity, không ignore-unfixed. Scanner chỉ nhận archive/cache/report volumes, không engine
socket hoặc secret volumes. Ba image mới được scan riêng, không dùng report tag cũ.

| Target đã scan mới | HIGH | CRITICAL | Kết luận |
| --- | ---: | ---: | --- |
| backend-tests-current |40|2|BLOCKED;42findings chưa có FixedVersion trong snapshot |
| frontend-current |0|0|Không có HIGH/CRITICAL trong snapshot; còn1MEDIUM |
| frontend-build-current |34|1|BLOCKED; npm audit0không thay scan build stage |

Nguồn: [backend test runner](t014-current-security.json), [frontend final/build](t014-current-web-security.json).
Không suy tổng77occurrences của3targets này thành số còn lại của toàn baseline.

[Review hai CRITICAL của test runner](t014-current-critical-review.json) ghi:

- CVE-2023-45853 ở zlib1g: [Debian tracker](https://security-tracker.debian.org/tracker/CVE-2023-45853)
  ghi phần contrib/minizip không được build trong Bookworm source version này. Inventory
  image không có minizip/libminizip1; danh mục zlib1g chỉ có libz và tài liệu. Đề xuất
  `PROPOSED_NOT_AFFECTED_REVIEW_REQUIRED` cho đúng finding/package/image; không tự miễn trừ
  hoặc áp cho bản nhúng và các target khác. Finding vẫn giữ trong scan.
- CVE-2025-7458 ở libsqlite3-0: [Debian tracker](https://security-tracker.debian.org/tracker/CVE-2025-7458)
  vẫn ghi Bookworm vulnerable/no-dsa. Giữ OPEN/BLOCKED; không tự hạ severity hoặc gỡ library.

## Lệnh tái lập và bằng chứng

Chạy từ root. Các tags `t014-b29ae86` là image thử tạo trong lượt này, không chứng minh
source khớp commit b29ae86 sau khi working tree đã sửa; hashes cụ thể ở JSON kết quả.

```powershell
$env:PODMAN_COMPOSE_PROVIDER=(Resolve-Path .tools/docker-compose-5.6.0.exe).Path
podman compose config --quiet
python -m unittest tests.unit.test_image_baseline tests.integration.test_image_compatibility.ImageCompatibilityTests.test_source_pins_match_image_lock -v
podman build -t localhost/aat-backend-tests:t014-b29ae86 -f docker/tests/Dockerfile .
podman run --rm --pull=never localhost/aat-backend-tests:t014-b29ae86
podman build --format docker -t localhost/aat-frontend:t014-b29ae86 -f frontend/Dockerfile .
podman build --format docker --target build -t localhost/aat-frontend-build:t014-b29ae86 -f frontend/Dockerfile .
podman run --rm --entrypoint npm localhost/aat-frontend-build:t014-b29ae86 audit --json
```

Proxy tests dùng tag `localhost/aat-frontend:0.1.0`, được gắn từ image frontend mới khi
chưa có tag AAT này trên máy; sau đó chạy `python -m unittest tests.integration.test_frontend_proxy -v`.
Fixture containers/network đã được test cleanup; không đụng containers/volumes có trước.
Scan dùng `tests/tools/scan_phase1_images.py` với TARGETS trỏ đúng các tags trên và SCANNER
trỏ digest trong report; wrapper lần chạy lưu `.tools/scan_t014_current*.py`.

Logs đã lưu: [pytest](t014-round2-logs/current-unit.log),
[proxy](t014-round2-logs/current-proxy.log), [selector CI](t014-round2-logs/current-lock-ci.log),
[frontend build](t014-round2-logs/current-frontend-build.log),
[backend scan](t014-round2-logs/current-backend-scan.log),
[frontend scan](t014-round2-logs/current-web-scan.log).
Kết quả máy đọc: [t014-current-results.json](t014-current-results.json).

### Lỗi và giới hạn đã xử lý

- Thử `podman manifest inspect` trên single-platform OCI digest bị tool từ chối; dùng
  registry manifest/config và đối chiếu SHA256 để xác minh nguồn, không coi lỗi tool là pin mất.
- Lần `podman run` đầu khởi chạy khi build runner còn chạy, trả125 vì chưa có local image;
  sau build dùng `--pull=never`,10tests PASS. Không gọi lượt125 là lỗi ứng dụng.
- Podman CLI build frontend mặc định OCI bỏ HEALTHCHECK và có warning; không nghiệm thu
  image đó. Build lại với `--format docker`, inspect thấy HEALTHCHECK, scan/proxy dùng đúng
  image mới. Compose config PASS không chứng minh canonical startup đã giữ probe trên runtime mới.
- PowerShell bọc stderr của unittest/build thành NativeCommandError trong một số logs;
  kết luận dựa exit code tiến trình và kết quả test, không dựa tên wrapper error.

## Điều kiện để tiếp tục đóng gate

1. Các quyết định [A/B trong phương án lượt2](../proposals/t014-round2-approval.md) vẫn
   chờ duyệt: override certifi/urllib3 với provenance riêng và nâng đồng bộ client/browser.
   Không triển khai hai thay đổi này chỉ từ yêu cầu tiếp tục hardening đã duyệt.
2. Review riêng từng finding còn lại, gồm OS NO_FIX và build-stage findings. Duyệt A/B
   không tự giải quyết chúng hoặc mở gate. Đề xuất not-affected phải được reviewer đánh giá;
   không tự waive/risk-accept hoặc sửa Constitution/reviewer checkbox.
3. Tái nghiệm thu full baseline trên tổ hợp runtime/provider được công bố, fresh/restart,
   secrets/persistence/readiness và browser thật; scan đủ final/build/toolchain theo IDs cuối.
4. Khi source cuối sẵn sàng và được phép publish, commit/push đúng phạm vi đã review và
   chạy lại Windows/Linux CI trên SHA chứa thay đổi mới. Không dùng CI HEAD cũ thay CI source mới.

T014 giữ chưa hoàn thành; các task Phase2 giữ nguyên.
