# Phương án đóng blocker T014 — P1–P7 đã được duyệt

Ngày: 2026-11-08. Feature: `specs/001-airflow-automation-tool`.
**P1–P7 đã được chủ dự án duyệt trong phiên làm việc; đang remediation. T014 vẫn BLOCKED.**
Các bảng baseline/triage bên dưới là snapshot đề xuất trước thay đổi; trạng thái thực thi
xem `docs/testing/phase1-report.md`. Không có quyền commit/push hoặc CI remote. Đây là kế hoạch có mục
tiêu theo Constitution1.1.0; không sửa Constitution, Spec, Tasks hoặc reviewer checklist.
Không thay BR-08, tám phase, MVP, schema/API hoặc triển khai Phase2.

## 1. Đầu vào và kết quả xác minh

- Đọc `docs/testing/phase1-report.md`, `phase1-security.json`, `phase1-npm-audit.json`,
  `docker/images.lock`, Plan/Research, manifest/locks, Dockerfiles, workflow và source shell.
- Trivy0.76.1 ghi **800 occurrences HIGH/CRITICAL, 277 mã vulnerability khác nhau** trên
  bảy image. Đây không phải 800 lỗ hổng độc lập hoặc 800 đường khai thác đã chứng minh.
- [Ledger theo package/version/path](t014-triage-packages.csv): 238 nhóm, chứa từng
  advisory, severity, installed/fixed candidate, URL, phạm vi, tác động và hướng xử lý.
  [Ledger từng finding](t014-triage-findings.json) giữ đủ 800 occurrences, target/path,
  image ID và SHA256 raw report. Tất cả còn OPEN; chưa có waiver hay kết luận false positive.
- FixedVersion trong ledger là dữ liệu scanner, **chưa được xác minh độc lập toàn bộ**.
  Mục không có FixedVersion không đồng nghĩa an toàn; không dùng `--ignore-unfixed` để mở gate.
- [Metadata candidate](t014-candidate-metadata.json) được đọc trực tiếp từ official-images
  và registry manifest; có index digest và manifest Linux/amd64 riêng. Không pull layer,
  cài package, build hay thay image đang chạy trong lượt Plan này.
- Constitution IX–XII tiếp tục áp dụng; tài liệu/metadata PASS không thay runtime PASS.

| Image hiện tại | HIGH | CRITICAL | Phạm vi cần xử lý |
| --- | ---: | ---: | --- |
| backend | 74 | 9 | Debian runtime; không có HIGH/CRITICAL Python app trong snapshot này |
| airflow | 188 | 23 | Debian, Python runtime/tooling, Ray JAR/vendor Python, Docker CLI |
| frontend | 61 | 3 | nginx/Alpine runtime; npm audit được đánh giá riêng |
| postgres | 140 | 20 | Debian và Go stdlib nhúng trong gosu |
| mysql | 142 | 2 | Oracle Linux, Python trong mysqlsh, Go stdlib nhúng trong gosu |
| backend-tests | 74 | 9 | Debian của runner kiểm thử |
| e2e-tests | 52 | 3 | Ubuntu và global npm của runner |

Scan hiện tại chưa bao phủ riêng Node build image và mọi intermediate wheel-build stage.
Phải bổ sung coverage này; không suy rằng final image sạch thì build chain sạch.
Native browser CVE coverage cũng không được bảo đảm chỉ bởi Trivy language/OS scan.

## 2. Triage theo đường sử dụng thực

### Frontend production dependencies

`frontend/src/app/router.tsx` dùng createBrowserRouter/RouterProvider Data Mode, sáu route
tĩnh. `App.tsx` có NavLink đích literal; chưa có loader/action/redirect, SSR/RSC,
prerender hoặc ScrollRestoration. Không thấy import Zod trong `frontend/src`.
Router chạy trong browser bundle; Node chỉ dùng build. Chưa kiểm bundle để xác nhận
Zod bị tree-shake hoàn toàn. Không kết luận SPA miễn nhiễm hoặc Zod được miễn sửa.

| Advisory | Điều kiện upstream | Đánh giá source shell hiện tại |
| --- | --- | --- |
| HIGH GHSA-2w69-qvjg-hvjx | Untrusted redirect trong Data/Framework/RSC | Data Mode có tồn tại; chưa có consumer redirect, chưa quan sát đường khai thác |
| HIGH GHSA-49rj-9fvp-4h2h | Framework cùng prototype pollution trước đó | Thiếu prerequisite trong shell |
| HIGH GHSA-8646-j5j9-6r62 | Unstable RSC redirect | Không có RSC |
| HIGH GHSA-8x6r-g9mw-2r78 | Framework manifest | Không có Framework Mode |
| HIGH GHSA-rxv8-25v2-qmq8 | Framework single-fetch | Không có Framework Mode |
| HIGH GHSA-chx6-hx7r-mcp5 | Framework manifest route expansion | Không có Framework Mode |
| HIGH GHSA-8v8x-cx79-35w7 | SSR ScrollRestoration cùng key không tin cậy | Không có SSR/API này |
| MOD GHSA-h5cw-625j-3rxh | Server actions | Chưa có consumer |
| MOD GHSA-wrjc-x8rr-h8h6 | Link/useNavigate đích attacker kiểm soát | NavLink hiện literal |
| MOD GHSA-337j-9hxr-rhxg | SSR error hydration | Không SSR/hydration |
| MOD GHSA-2j2x-hqr9-3h42, GHSA-jjmj-jmhj-qwj2 | Application open redirect | Chưa có redirect |
| MOD GHSA-f22v-gfqf-p8f3 | Framework prerender redirect HTML | Không prerender |
| HIGH Zod GHSA-mrhx-c7xc-m3w5 | Collection quá lớn làm cạn RAM khi validate | Chưa import/parse trong shell; cần vá trước consumer validation |

Nguồn từng Router advisory: `https://github.com/remix-run/react-router/security/advisories/<GHSA-ID>`.
[Zod advisory](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5).
Đây là đánh giá exposure của source hiện tại, không là waiver cho consumer tương lai.

### OS runtime và công cụ đi kèm

- Debian: các nhóm apt/libapt, GnuTLS, OpenSSL, Kerberos, PCRE2, libcap, Perl có
  fixed candidates; util-linux, gzip, ACL, SQLite, zlib, ncurses/systemd và một số
  libxml2/openssh/rsync còn advisory không có fix trong snapshot. Ledger giữ riêng từng CVE.
  GnuTLS CVE-2026-33845 được [Debian tracker](https://security-tracker.debian.org/tracker/CVE-2026-33845)
  xác nhận Bookworm fixed `3.7.9-2+deb12u7`; baseline backend đang u6. Advisory cần
  đường DTLS handshake; chưa chứng minh app thực sự gọi đường đó. Có bản vá thì ưu tiên vá.
  OpenSSL cần tối thiểu release vendor đáp ứng tất cả advisory, scanner nêu đến
  `3.0.22-1~deb12u2`; không so upstream semver để bỏ qua backport Debian.
- nginx/Alpine: brotli `1.1.0-r2 → 1.1.1-r0` (CRITICAL theo scanner), OpenSSL
  `3.3.5-r0 → 3.3.7-r2`, c-ares/curl/expat/libpng/libxml2/musl/nghttp2/PCRE2/tiff/zlib
  có candidate riêng trong ledger. Chưa xác minh vendor từng dòng; image mới phải scan lại.
  nginx còn có advisory upstream ngoài kết quả OS scan. Không dừng ở 1.28.3 chỉ vì vá
  một CVE; [security advisories](https://nginx.org/en/security_advisories.html) ghi nhiều
  bản vá ở stable1.30.6. Module/config prerequisite phải được đối chiếu, không mặc định
  HTTP/3/TLS/alias/rewrite đều đang bật.
- Oracle Linux trong MySQL: OpenSSL scanner nêu đến `1:3.5.8-2.0.1.el9_8`, curl đến
  `7.76.1-40.el9_8.8`; dùng Oracle advisory/release, không đem Debian version áp sang.
- Airflow Ray: Jackson core/databind2.18.8, Guava32.0.1-jre và httpcore5 5.0.2 nằm
  trong `ray/jars/ray_dist.jar`; vendor aiohttp còn nằm dưới Ray. LocalExecutor không
  dùng Ray. Slim/allowlist có thể loại dependency không dùng; phải chứng minh package và
  consumer thật sự không còn. `pip upgrade aiohttp` không vá bản vendor trong Ray JAR/tree.
- Airflow `/usr/bin/docker` nhúng Go1.26.8; không có DockerOperator/socket trong baseline.
  DB `/usr/local/bin/gosu` nhúng Go1.24.6, chạy lúc entrypoint drop UID; chưa chứng minh
  CVE network/parser của stdlib được gọi. Cài Go mới vào image không rebuild hai binary này.
- MySQL Python findings nằm dưới `/usr/lib/mysqlsh/lib/python3.13`, gồm certifi,
  cryptography, pyOpenSSL, urllib3. Không phải lock backend và không phải mysqld Python.
  Kiểm consumer admin/init trước khi loại mysqlsh hoặc chọn image vendor đã vá.
- Runner npm findings nằm dưới `/usr/lib/node_modules/npm`, có tar6/7, pacote,
  minimatch, brace-expansion, glob, sigstore, picomatch, ip-address. npm ci/npx có thể
  xử lý metadata/archive không tin cậy; test-only không có nghĩa không rủi ro.
  Frontend package-lock override không sửa npm bundled trong image.

### Airflow Python candidate cần resolver/constraints review

Đây là **candidate từ scanner**, chưa được duyệt pin và chưa chứng minh tương thích.
Ưu tiên bỏ dependency/tool/provider không dùng qua slim/allowlist, sau đó chỉ sửa phần còn lại.

| Package hiện tại | Candidate scanner để đánh giá |
| --- | --- |
| Authlib1.8.0 / GitPython3.1.62 | 1.9.1 / 3.2.1 |
| aiohttp3.14.3 / certifi2026.6.17,2026.7.22 | 3.14.4 / 2026.10.18 |
| dnspython2.8.0 / filelock3.32.6 | 2.9.0 / 4.2.1 (major change) |
| litellm1.85.7 / msgpack1.1.2,1.2.2 | 1.95.0 / 1.2.3 |
| oauthlib3.3.1 / pyasn1 0.6.4 | 4.0.1 (major change) / 0.6.5 |
| setuptools70.3.0 / tornado6.5.8 / urllib3 2.7.0 | 78.1.1 / 6.5.9 / 2.8.0 |
| uv0.12.10,0.12.15 / virtualenv21.7.9 | 0.13.4 / 21.14.9 |

Không sửa thẳng file constraints Apache rồi giữ nguyên tên/hash như bản upstream.
Nếu dependency cần dùng bị khóa dưới floor vá: dừng nhánh đó, trình diff override có
provenance/test hoặc đề xuất Airflow upgrade riêng. Không tự nhảy Airflow3.4.0.

## 3. Bảng baseline xin duyệt

Mục P1–P5 là candidate để thực hiện/kiểm chứng, không cam kết sẽ đóng mọi CVE.
Các pin không liệt kê giữ nguyên. Chưa có build/pip check/Playwright trên candidate.

| ID | Baseline hiện tại | Đề xuất tối thiểu | Bằng chứng và điều kiện |
| --- | --- | --- | --- |
| P1 | react-router7.9.6; zod4.1.12 | **7.18.5; 4.6.7** | Registry/release tồn tại; floor toàn advisory hiện tại7.18.0/4.6.6. Router Node>=20, React/DOM>=18 đáp ứng baseline; chưa có compatibility PASS |
| P2 | Python3.12.12-slim-bookworm | **3.12.16-slim-bookworm** cho backend, runner, wheel stages | Cùng Python3.12/Bookworm; tag+amd64 manifest thật; giữ app Python pins trước khi scan chứng minh cần đổi |
| P3 | PostgreSQL17.6-bookworm; MySQL8.4.7 | **17.11-bookworm; 8.4.13** | Cùng PG major17/MySQL8.4 LTS, tag+amd64 thật; test upgrade trên bản sao dữ liệu, không reset volumes hoặc giả định rollback binary an toàn |
| P4 | nginx1.28.0-alpine | **1.30.6-alpine3.24** | Stable branch có bản vá upstream; tag+amd64 thật. Đổi nhánh vì1.28.x không đủ coverage advisories hiện tại; kiểm nginx config/proxy/UID/mount/health lại |
| P5 | Node22.21.1-bookworm-slim, host22.21.1/npm10.9.4 | **Node22.23.4-bookworm-slim**, đồng bộ host/engines/docs khi áp dụng; npm10.9.4 tạm giữ | Cùng Node22; manifest thật. npm10.9.4 chưa có bằng chứng sạch, phải scan riêng build toolchain; nếu cần đổi npm, trình exact candidate+scan trước áp dụng |
| P6 | apache/airflow3.3.2-python3.12 full image | **slim-3.3.2-python3.12**, thêm đúng provider cần dùng theo constraints3.3.2/Python3.12 | Tag+amd64 thật; giữ core/SDK/API3.3.2. Xác định allowlist từ config/import/entrypoint, lock provider trước build; không giả định slim tự hết lỗi OS/Python |
| P7 | Playwright client1.56.1 + image1.56.1-noble, Chromium141.0.7390.37 | **Giữ nguyên cả cặp và browser**, dựng child runner có OS security updates được khóa; sau npm ci dùng node CLI và loại global npm khỏi final runner nếu không còn consumer | Không đổi client/browser một phía. Khóa OS snapshot/package versions và child image digest. Build stage chứa npm vẫn phải scan; browser risk review riêng. Nếu không đáp ứng thì trình cặp client/image mới, không tự nâng |

P6/P7 là phương án thử có điều kiện, **chưa phải baseline sạch đã chốt**. Duyệt P6 không
ủy quyền ghi đè constraints hoặc tự loại package runtime bắt buộc. Duyệt P7 không ủy quyền
bỏ browser, scan, sandbox hoặc test để giảm findings. Nếu cần distro/major/constraint
khác bảng, quay lại xin duyệt đề xuất cụ thể; hoàn tất các nhánh độc lập trước.

Nguồn P1: [Router registry](https://registry.npmjs.org/react-router/7.18.5),
[Router release](https://github.com/remix-run/react-router/releases/tag/react-router@7.18.5),
[Zod registry](https://registry.npmjs.org/zod/4.6.7),
[Zod release](https://github.com/colinhacks/zod/releases/tag/v4.6.7).
Nguồn P2–P5: official-images URLs và source revision trong metadata candidate;
[Python3.12.16](https://www.python.org/downloads/release/python-31216/),
[PG17.11 migration notes](https://www.postgresql.org/docs/release/17.11/),
[MySQL8.4.13](https://dev.mysql.com/doc/relnotes/mysql/8.4/en/news-8-4-13.html).
Nguồn P6: [Airflow image build/constraints](https://airflow.apache.org/docs/docker-stack/build.html).
Nguồn P7: [Playwright Docker và version matching](https://playwright.dev/docs/docker).

### Digest candidate chỉ để review

Không chép index digest lẫn manifest digest vào `images.lock`. Khi áp dụng, pull đúng
platform và đối chiếu inspect/repo digest thật, ghi cả platform/source và child image ID.
Các SHA dưới đây là **manifest Linux/amd64**, chưa là production lock được duyệt.

| Candidate | Manifest SHA256 |
| --- | --- |
| python3.12.16-slim-bookworm | `0f086103b026048cc50cb5da25ec435c023c5241a83fc44daea593377abc61c4` |
| postgres17.11-bookworm | `73bedc9eaa0121b92b9b26bb52e5141b3f6f37479c7ef913c0160455763ca80a` |
| mysql8.4.13 | `72c368d898861f3b3a07af0e6d690400f44f048799ed46822783d9224cc2c86d` |
| nginx1.30.6-alpine3.24 | `bb8f722b4be005fcd7827816a136ab779fd40185d85b5171be915cc7fc0575c7` |
| node22.23.4-bookworm-slim | `aaa4b5baf1ecff3b283486bb1f90405cdda225a3e6f79660d2c559fa510a7292` |
| airflow slim3.3.2-python3.12 | `8177d08e713886fe1cfc4d5e2683a72725756cd8086e57af8fe163ee76e2b82f` |

Full Airflow tag hiện trả amd64 digest trùng lock hiện tại `0a74ea83…`; repull cùng tag
không có bằng chứng sẽ sửa findings. Không chọn tag floating `latest`, `17`, `8.4`, `stable`.

## 4. Thay đổi phải thực hiện sau duyệt

1. Chốt các hàng được duyệt và baseline npm/OS/provider còn cần nghiên cứu. Không chạy
   `npm audit fix --force`. Áp dụng P1 riêng trước; npm ci/full-tree audit và production
   audit, dependency tree, typecheck/build; kiểm resolvers5.2.2 với Zod4, sáu route,
   deep-link/navigation/mobile/search. Chưa có schema consumer thì ghi giới hạn đó.
2. P2–P5: sửa đúng Dockerfile FROM, Compose DB refs và engines/toolchain tương ứng;
   giữ backend-worker cùng image, không cài patch trong startup. Khóa package OS dùng
   snapshot/repository provenance tại build; không dùng unbounded upgrade rồi gọi tái lập.
3. P6: kiểm provider thật sự cần (PostgreSQL metadata, LocalExecutor, SimpleAuth/SDK,
   DAG processing), resolve allowlist dưới constraints và khóa hash. Chạy pip check,
   import/CLI/DB migration/auth/API/health/scheduler smoke thật. Không thêm Ray/Docker
   provider chỉ để làm resolver xanh; không xóa package theo tên mà thiếu import review.
4. P7: giữ client1.56.1 trong cả frontend/test manifest+locks và image/browser tương ứng;
   kiểm actual browser launch/version. Test profile phải có đủ hai runner trước consumer;
   không chia sẻ fixture namespace/DB/artifact giữa lượt test hoặc CI.
5. Sau mỗi nhóm: build image thật bằng Podman baseline đã duyệt; scan final và build
   stages, npm toolchain riêng. Giữ raw JSON/SBOM, DB timestamp, scanner digest, image IDs
   và source hashes. So từng CVE cũ/mới; không chỉ so tổng số giảm. Finding mới phải triage.
6. Reaccept T011–T013 trên Compose cuối trong project test riêng rồi mới T014. Giữ preview
   4173 và stack hiện tại; không dựng project trùng/đè port hoặc chuyển volume hiện tại
   sang binary DB mới trước backup/restore test. Không reset volumes.
7. Chỉ sau đủ evidence mới cập nhật task trạng thái; phần thiếu ghi FAIL/NOT_RUN/BLOCKED.

### Danh sách file/lock/evidence cần đồng bộ

- `frontend/package.json`, `frontend/package-lock.json`; `tests/e2e/package*.json` chỉ
  khi toolchain/test dependency thay đổi được duyệt. Không override global npm qua frontend lock.
- `frontend/Dockerfile`, `backend/Dockerfile`, `airflow/docker/Dockerfile`,
  `docker/tests/Dockerfile`, `docker/tests/playwright.Dockerfile`, `docker-compose.yml`.
- `backend/requirements.in`, `requirements.lock`, `etl_engine/requirements.in`,
  `requirements.lock` chỉ khi graph thay đổi; giữ hashes. Provider allowlist/lock mới nếu P6.
  `airflow/docker/constraints-3.12.txt/.sha256` giữ nguyên upstream3.3.2 trừ quyết định riêng.
- `docker/images.lock` cùng `tests/tools/record_image_baseline.py`,
  `tests/tools/scan_phase1_images.py`: refs đúng candidate được duyệt; bổ sung build-stage
  scan không làm mất bảy final-image targets. Khóa digest phải thực sự được dùng khi build,
  không chỉ ghi digest rồi tiếp tục build từ tag có thể dịch chuyển.
- `tests/integration/test_image_compatibility.py` và kiểm version/source liên quan;
  giữ kiểm actual SDK/browser, không chỉ sửa expected string để PASS.
- Plan/Research, `contracts/dependency-verification.json` (metadata kỹ thuật), Quickstart,
  README; Tasks giữ8phase/152IDs, chỉ sửa pin/acceptance liên quan sau duyệt.
  Không đổi contracts nghiệp vụ/Data Model, sample workbook/dataset hoặc reviewer checkbox.
- Báo cáo security/npm-audit/final-state/source hashes/images compatibility và phase1-report
  cập nhật theo source/image cuối; giữ snapshot cũ trong lịch sử, tránh ghi đè mất provenance.

## 5. CI đúng source và checkout sạch

Git thực tế: `main`, HEAD `c00947a14bc6b1e5b85b7d1609ed0a1e06c0d444`.
Remote origin: `https://github.com/qtrugle0113/fpt-spec-eng.git`.
Có nhiều modified/untracked files; workflow, frontend/backend/Compose hiện chưa được track
trong HEAD. `gh` không tìm thấy trên PATH; chưa kiểm quyền tài khoản/Actions qua mạng.
Không commit/push/trigger workflow trong lượt này.

`.github/workflows/sample-artifacts.yml` có matrix ubuntu-latest/windows-latest, checkout@v4,
setup-python@v5 Python3.12, chạy `python -m unittest tests.unit.test_sample_artifacts -v`;
permissions contents:read. Đây chỉ là CI bytes mẫu, không phải CI toàn bootstrap.
Remote CI vẫn NOT_RUN. Workflow untracked chưa thể chạy trên đúng source hiện tại.

Sau duyệt remediation, chuẩn bị diff và danh mục file cụ thể (không `git add .`), kiểm secrets
và file sinh, giữ các thay đổi người dùng đã có. Trình riêng quyền tạo branch/commit/push
với phạm vi source/docs/workflow đã review. Baseline đã duyệt không tự cấp quyền publish.
Khi được phép: commit trên nhánh feature, ghi immutable SHA; tạo checkout mới vào đường dẫn
chưa tồn tại, ví dụ `.tools/t014-checkout-<shortSHA>` sau khi xác minh nằm trong workspace.
Clone/checkout đúng commit, không chỉ clone HEAD cũ rồi coi đã chứa source untracked.

Không reset ACL, không truy cập/xóa `.pytest_cache` bị chặn, không git clean/reset hoặc
copy cache/secret/venv vào checkout. Kiểm Git status sạch, `.gitattributes`, raw SHA256 mẫu,
XLSX và source manifest. Fixture copy hiện tại chỉ là fixture, không tự biến thành checkout
Git; pre-commit có thể kiểm fixture độc lập nhưng phải báo khác kết quả clean checkout.

CI push/PR trên nhánh chứa SHA đó chạy cả hai OS; nếu workflow_dispatch thì chọn đúng
branch và đối chiếu `head_sha` của run. Thêm evidence in/lưu `git rev-parse HEAD`, raw hashes,
Python/OS, run URL/job IDs và logs/artifacts (không chứa secrets). Chỉ khi cả hai jobs
success và artifact đúng SHA mới đánh CI bytes PASS. Nếu sửa source sau run phải chạy lại.
Branch/Actions policy, quyền token hoặc runner unavailable là blocker thật, không thay bằng
local container PASS. Bổ sung full-runtime CI nếu muốn là phạm vi riêng, không cần cho
matrix bytes T014 hiện tại; Podman runtime nghiệm thu local vẫn phải chạy thật.

## 6. Tiêu chí nghiệm thu lại T014 và quyết định còn thiếu

- T011: init dependencies, secret domains PG/MySQL, UID/GID/RO/nocopy, loopback,
  actual cgroup resource limits, hai runner test profile đều được kiểm trên Compose cuối.
- T012: DB/scheduler down tạo unhealthy dù HTTP200; restore dependency và xác nhận healthy.
- T013: fresh startup một lệnh + restart persistent volumes; secret bytes và dữ liệu đã
  sửa không mất; pytest/Playwright thật. Không dùng mẫu bootstrap làm US1/MVP PASS.
- T014: npm ci/typecheck/build, pip check backend/Airflow, SDK/version/browser thật,
  digest/platform/source khớp, sample bytes checkout→image, CI Windows/Linux đúng SHA.
- Security: scan đủ final/build/toolchain, DB scanner còn phù hợp; mỗi HIGH/CRITICAL được
  sửa/loại component có chứng cứ hoặc có đánh giá not-affected từng advisory được review.
  Không tự thêm waiver/risk acceptance hoặc nới gate. Mục chưa rõ/NO_FIX còn BLOCKED;
  nếu muốn chấp nhận rủi ro còn lại phải có quyết định riêng và kiểm Constitution trước.
- Workspace gốc vẫn có ACL blocker lịch sử; nghiệm thu startup ở clean checkout được công
  bố rõ, không đổi nhãn lịch sử workspace gốc thành PASS. Giữ stack/volumes/preview cũ.

**Cần chủ dự án duyệt:** P1–P7 (có thể duyệt từng hàng); quyết định riêng nếu constraint,
npm/browser hoặc NO_FIX còn chặn sau thử nghiệm. Quyền commit/push/chạy CI remote phải
được cấp riêng sau khi diff cuối sẵn sàng review. Chưa có security compatibility PASS cho
bất kỳ candidate nào; T014 và gate Phase1 tiếp tục BLOCKED.

## Phạm vi quyết định local sau này

Kết quả scan/approval và full gate lịch sử phía trên giữ nguyên. Chỉ quyết định riêng
của chủ dự án theo t014-conditional-local-gate.md, đã khép blocker và còn hạn, mới cho phép
phát triển local có điều kiện. Không thay security thành PASS hoặc nghiệm thu T014 đầy đủ.
147 nhóm xin risk acceptance không tự là not-affected; LEX-003/D3 xử lý riêng.
