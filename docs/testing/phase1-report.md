# Báo cáo Phase1 sau remediation P1–P7 — 2026-11-08

## Kết quả tiếp tục ngày 2026-11-09 — nguồn trạng thái hiện hành

[Triển khai A/B đã được duyệt](t014-ab-report.md) là kết quả mới nhất: fresh/restart752.059s,
13unit/4E2E/5compatibility/7runtime tests và UI Airflow auth PASS. Upstream constraints giữ
nguyên hash; certifi2026.10.18/urllib3 2.8.0 và Playwright1.65.0/Resolute đã áp dụng.
Security và CI source mới vẫn là gate riêng; không tuyên bố Phase1 hoàn thành.

[Báo cáo T014 hiện hành](t014-current-report.md) ghi các sửa đổi lock/CI, kết quả build,
10unit tests/4proxy tests PASS và scan mới của ba targets. CI Windows/Linux đã PASS tại
HEAD b29ae86; thay đổi working tree lượt mới chưa chạy CI remote. Podman hiện6.1.1,
khác baseline lịch sử. Security và các gate chưa tái kiểm vẫn chặn T014/Phase1.
Các mục bên dưới là lịch sử, không tự kế thừa PASS hoặc NOT_RUN cho source/máy hiện tại.

## Lượt2 đang nghiệm thu — trạng thái hiện hành

Chủ dự án đã cho phép compatible security patches và commit/feature branch/push/CI.
Branch hiện tại `001-airflow-automation-tool-t014`; author được chỉ định là
le quang trung <rikateamovt1@gmail.com>. GitHub device flow đã xác thực thành công.
Npm12.2.2 build/audit Win/Linux PASS; OS Airflow13pins và gosu1.19 rebuild Go1.27.3,
loại mysql-shell/Docker CLI/uv extra/prek tooling đang nghiệm thu trên source cuối.
Official constraints và Playwright1.56.1 baseline vẫn nguyên; trial riêng không là pin áp dụng.
CI Windows/Linux đã PASS tại SHA a3c421ed78def8cfc28c0555e82b37e4cff96e55 (run42491834726).
Clean checkout cùng SHA đã PASS fresh/restart442.108s và UI/auth-login đúng38080;
runtime8tests có6PASS/2FAIL: SSH125 transient và tên project không qua restore allowlist.
Guard giữ nguyên, lượt cuối dùng tên project hợp lệ. Pip26.3 artifact hash đã build/pip-check
và không thay app dependency graph, không thuộc constraints; đang nghiệm thu source cuối.
T014 giữ BLOCKED, CI source mới phải chạy lại; các số liệu P1–P7 bên dưới là lịch sử,
không tự kế thừa PASS cho source lượt2. Tiếp tục gate trước khi có kết luận cuối.

## Kết luận baseline P1–P7 trước lượt2

**T001–T013 PASS trong phạm vi bootstrap; T014 BLOCKED. Gate Phase1: BLOCKED.**
P1–P7 đã được duyệt và áp dụng; chưa commit/push hoặc chạy CI remote. Không triển khai
Phase2, sửa Constitution/checklist reviewer hoặc override constraints. Bootstrap không là
US1/MVP hoàn thành. Các kết quả dưới đây thuộc candidate mới, không kế thừa PASS lịch sử.

| Kiểm chứng | Trạng thái và bằng chứng |
| --- | --- |
| Frontend | PASS npm ci trên fixture sạch, typecheck/Vite build; Router7.18.5/Zod4.6.7; Node22.23.4/npm10.9.4 |
| npm audit | PASS full và production:0 vulnerabilities; Zod/resolvers5.2.2 valid/invalid input PASS |
| T011 wiring | PASS trong6test runtime: init dependency failure, secret domains, actual cgroup limits, UID/RO/loopback/order |
| T012 | PASS DB/scheduler fault injection; HTTP200 không che unhealthy; dependency đã phục hồi |
| T013 | PASS fresh startup một lệnh và down/up không-v trên volumes cũ,597.552s; secret bytes/DB edits/artifacts giữ nguyên |
| Test profile | PASS pytest7/7, Playwright4/4 desktop/mobile, cả hai private paths GET/POST404 |
| UI nginx candidate | PASS12route/viewport, search/mobile menu,0page errors; Chromium141.0.7390.37 |
| DB patch restore | PASS logical backup PG17.6/MySQL8.4.7 từ stack cũ sang namespace mới trên17.11/8.4.13; hashes dữ liệu mẫu khớp, không sửa source DB |
| T014 compatibility | PASS3/3,13.527s; pip check/SDK3.3.2,7base digests/platform, actual browser/client1.56.1 |
| Source/runtime | PASS8file hash đối chiếu cụ thể; scan12image IDs khớp tags cuối,0mismatch |
| T014 security | BLOCKED; scan execution PASS nhưng còn634HIGH/CRITICAL occurrences trên12targets; không waive/ignore-unfixed |
| T014 CI | NOT_RUN/BLOCKED; workflow Windows/Linux chưa chạy trên commit chứa đúng source |
| Root workspace | BLOCKED startup do ACL cache lịch sử; npm ci mới FAIL EPERM file native đang khóa. PASS fixture không thay PASS root hoặc clean Git checkout |

Máy đọc: [results](t014-remediation-results.json), [final state](phase1-final-state.json),
[source hashes](phase1-source-hashes.json), [security](phase1-security.json),
[triage từng finding](t014-security-triage.csv), [full npm](phase1-npm-audit.json),
[production npm](t014-npm-audit-production.json), [image locks](../../docker/images.lock).
Có thêm40[build inputs](t014-build-input-hashes.json) đối chiếu raw SHA256 root→fixture.
[Danh mục file chờ review](t014-review-files.json) gồm cả thay đổi có trước lượt này;
patch đối chiếu HEAD tại `.tools/t014-review.patch`, không tự stage bất kỳ file nào.

## Baseline đã áp dụng và giới hạn

- Python3.12.16-slim-bookworm cho backend/pytest/wheel stages; Node22.23.4-bookworm-slim
  cho frontend build, npm10.9.4 được enforce vì image thực bundle10.9.9.
- PostgreSQL17.11-bookworm, MySQL8.4.13, nginx1.30.6-alpine3.24. FROM/DB refs dùng digest
  Linux/amd64 thực; `images.lock` ghi inspect/repo digest, không lẫn với image ID/index.
- Airflow slim3.3.2-python3.12; provider/driver input và lock hashes gồm standard1.19.0,
  psycopg2-binary2.9.13 và asyncpg0.31.0. Official constraints bytes/hash giữ nguyên;
  không đổi core/SDK/Public API contracts/BR-08.
- Playwright image/client1.56.1 và Chromium141.0.7390.37 giữ nguyên.159OS packages khóa
  exact versions; [resolution provenance](t014-os-resolution.txt). Final runner dùng node
  CLI trực tiếp, không global npm; dependencies/build stage vẫn được scan riêng.
- Podman client5.8.3/server5.8.9, Docker Compose provider5.6.0; không đổi machine,
  healthcheck, limits, UID/mount/secret semantics hoặc volumes để chạy được.

## Lệnh kiểm chứng và log

Lệnh host dùng `.venv\Scripts\python.exe` để điều phối Podman; test dependencies chạy
trong image Linux/Python3.12. Env candidate: AAT_COMPOSE_PROJECT=aat-phase1-t014-final-cf8461ea,
AAT_COMPOSE_DIR đọc `.tools/phase1-compose-dir.txt`; port overrides13000/18000/18080;
AAT_AIRFLOW_URL=http://127.0.0.1:18080. Không chạy fault injection trên project dữ liệu thực.

| Lệnh/nhóm lệnh đã chạy | Kết quả/log |
| --- | --- |
| Node22.23.4 chạy npm10.9.4 CLI: npm ci, npm run build, npm audit --json và --omit=dev | PASS; fixture frontend, không tắt preview để mở khóa native module |
| podman build -f … cho backend/frontend/Airflow/pytest/E2E, --target build/wheels/dependencies | PASS; logs chi tiết `.tools/t014-build-*.log`; build targets được tag riêng để scan |
| python -m unittest tests.integration.test_bootstrap_startup -v với AAT_FRESH_START=1 | [PASS log](t014-logs/t014-startup-final.log) |
| python -m unittest tests.integration.test_compose_bootstrap_wiring tests.integration.test_bootstrap_health tests.integration.test_bootstrap_secret_logs tests.integration.test_database_patch_restore -v | [6PASS log](t014-logs/t014-runtime-gates.log) |
| podman compose --profile test run --rm backend-tests/e2e-tests trên fixture cuối | [pytest7PASS](t014-logs/t014-pytest-final.log), [Playwright4PASS](t014-logs/t014-playwright-final.log) |
| podman run runner + AAT_SHELL_BASE_URL=http://frontend:80 + verify-shell.cjs RO | [12PASS log](t014-logs/t014-shell-final.log); không dùng preview cũ làm evidence candidate |
| python -m unittest tests.integration.test_image_compatibility -v | [3PASS log](t014-logs/t014-compatibility-final.log) |
| tests/tools/scan_phase1_images.py |12targets; Airflow đổi sau fix được [scan lại](t014-security-airflow-final.json) rồi merge theo ID; tất cả final tags khớp |
| python -m unittest tests.unit.test_sample_artifacts -v |3PASS host; raw LF/hash/XLSX không đổi; không thay CI Windows/Linux |

## Findings còn lại

| Target | HIGH | CRITICAL |
| --- | ---: | ---: |
| backend |40|2|
| airflow |146|22|
| frontend |0|0|
| postgres |75|4|
| mysql |33|2|
| backend-tests |40|2|
| e2e-tests |2|0|
| node-build-base |44|1|
| frontend-build |72|4|
| backend-wheels |43|2|
| airflow-wheels |43|2|
| e2e-dependencies |52|3|

Bảy final targets còn368occurrences so với800ở snapshot trước;12targets hiện tại là634.
Coverage khác nhau nên không so tổng634với800 để tuyên bố hết rủi ro. Scan là OS/language
vulnerabilities, không chứng minh exploitability hay bao phủ đầy đủ native browser CVEs.
Trivy0.76.1/digest và DB timestamps giữ trong security JSON; không đổi scanner chỉ vì có
notice phiên bản mới. Tất cả HIGH/CRITICAL còn lại OPEN; fixed candidates chưa là pin được duyệt.

[Blocker chi tiết và quyết định tiếp](../proposals/t014-remaining-blockers.md): Airflow OS
patches/constraints/vendor copies; npm build toolchain; embedded Go trong gosu/Docker CLI;
mysqlsh; OS NO_FIX; hai GStreamer HIGH chưa có fix. Frontend audit0 không bao phủ global
npm của build image. Không tự sửa constraints, nâng browser hoặc bỏ findings để mở gate.

## Lỗi đã gặp, phục hồi và trạng thái môi trường

- Startup thử đầu FAIL vì thiếu asyncpg trong slim. Bổ sung đúng constraint0.31.0 và hash;
  giữ [log FAIL](t014-logs/t014-startup.log). Fixture lỗi đã down không-v, volumes được giữ.
  Fresh project cuối độc lập đã PASS, không đổi nhãn lượt FAIL cũ.
- Runner OS lock ban đầu CRLF làm apt đọc sai version. Sửa bytes LF và thêm rule checkout
  `.gitattributes`; retry build PASS, không chuẩn hóa file upload hoặc đổi workbook/dataset.
- Standalone integration có lỗi SSH/HTTP tạm thời khi nhiều build/scan đang chạy. Giữ
  [retry có backend FAIL/proxy4PASS](t014-logs/t014-api-proxy-retry.log), diagnostic app
  HTTP200 và [backend test cuối PASS](t014-logs/t014-backend-final-test.log); không nới timeout.
- Pytest venv Windows/Python3.13:6PASS/1FAIL do thiếu cryptography. Không lấy host venv làm
  Linux runtime; runner Linux7PASS. npm ci root EPERM không xử lý bằng reset ACL/xóa cache.
- Project candidate hiện hành: `aat-phase1-t014-final-cf8461ea`;4init Exited0/8services healthy.
  `.tools/phase1-project.txt` và `.tools/phase1-compose-dir.txt` trỏ candidate. Project cũ
  `aat-phase1-800be543` vẫn8healthy, lưu tên tại `.tools/t014-retained-project.txt`.
- Xem shell candidate http://localhost:13000; backend live http://localhost:18000/api/v1/health/live
  (ready404); Airflow health/API ở18080. UI/auth redirect qua port phụ18080 chưa được nghiệm
  thu trình duyệt; UI cũ8080 vẫn giữ. Shell cũ3000 và preview4173 vẫn HTTP200.

## CI, Git và gate

Git vẫn main, HEAD c00947a14bc6b1e5b85b7d1609ed0a1e06c0d444; source/workflow có nhiều
untracked/modified files từ trước. Chưa stage/commit/push hoặc chạy CI remote. Workflow
đã thêm log commit thực và kiểm artifact không bị test sửa; không coi YAML/local unit là CI PASS.
Cần duyệt scope commit/push riêng, checkout mới đúng SHA rồi chạy Windows/Linux. Không clone
HEAD cũ và coi đã chứa implementation untracked; không reset ACL/cache/volumes.

T014 giữ[ ]; gate Phase1 BLOCKED, chưa chuyển Phase2. Các phần bên dưới là **lịch sử trước
remediation P1–P7**, không dùng làm trạng thái source/baseline hiện tại.

---

## Lịch sử trước remediation P1–P7


### Kết luận trước P1–P7

**T001–T013 PASS trong phạm vi bootstrap; T014 BLOCKED. Gate Phase1: BLOCKED.**
Không chuyển Phase2; bootstrap không đồng nghĩa US1 hoặc MVP hoàn thành. Reviewer và
Constitution không bị sửa trong lượt tiếp tục này. Không thay bất kỳ version pin nào.

| Phần nghiệm thu | Kết quả hiện hành |
| --- | --- |
| T001–T010 | PASS; skeleton/locks/images/init/secrets, bằng chứng chi tiết và lịch sử bên dưới |
| T011 | PASS; secret domains riêng, init/health dependency, kernel limits/UID/GID/RO/loopback và test profile thật; sửa nocopy có fresh/restart proof |
| T012 | PASS; fault injection MySQL/scheduler, HTTP200 không che unhealthy, dependency phục hồi |
| T013 | PASS; fresh/restart249.15s, secrets/DB edits/artifacts giữ nguyên, pytest7PASS/Playwright4PASS, DB/Airflow auth/API/UI thật |
| T014 compatibility | PASS3test;7base digests thật, pip check/SDK/browser; npm typecheck/build PASS |
| T014 security | BLOCKED; npm audit FAIL exit1 với2gói HIGH, image scan có HIGH/CRITICAL cần triage |
| T014 CI | NOT_RUN; workflow đã tạo/parse nhưng chưa chạy remote Windows/Linux |
| Workspace gốc startup | BLOCKED do ACL .pytest_cache; không reset ACL hoặc xóa cache. PASS fixture sạch không thay kết quả này |

Project hiện hành `aat-phase1-800be543` từ `.tools/phase1-project.txt`:4init Exited(0),
8service healthy; URL shell http://localhost:3000, preview giữ nguyên http://localhost:4173,
Airflow http://localhost:8080. Backend chỉ live tại http://localhost:8000/api/v1/health/live;
ready404. Socket host chỉ LISTEN127.0.0.1. Cards shell vẫn tĩnh, chưa nối API nghiệp vụ.

Bằng chứng máy đọc: [final-state](phase1-final-state.json), [source/runtime hashes](phase1-source-hashes.json),
[image scan](phase1-security.json), [npm audit](phase1-npm-audit.json),
[base image digests](../../docker/images.lock). Các phần cũ phía dưới là lịch sử, không
được dùng làm trạng thái hiện hành hoặc thay bằng chứng cho source đã thay đổi.

## Lịch sử trước khi nghiệm thu Podman

Chỉ thực hiện T001–T014 theo phụ thuộc, không vào Phase 2. **Phase 1 chưa hoàn thành**:
T001/T003 đã đạt tiêu chí skeleton/shell; T002 và T005 có đầu ra một phần nhưng còn BLOCKED.
Không có Compose, DB/Airflow readiness hoặc execution thật để nghiệm thu US1/MVP.
Reviewer checklists không bị sửa trong lượt implementation này.

| Task | Trạng thái | Đầu ra/bằng chứng và giới hạn |
| --- | --- | --- |
| T001 | PASS | Manifest frontend/3package Python, wheels0.1.0, editable install no-deps, isolated import không FastAPI/Airflow, typed markers, sample raw LF/hash. Kiểm trên Python3.13.15; Linux/Python3.12 còn chưa kiểm. |
| T002 | BLOCKED | 32artifact backend/14artifact ETL có hash, resolve/tải lại offline đạt; constraints Apache có hash. Chưa install/pip check hai môi trường Linux/backend và Airflow3.3.2. |
| T003 | PASS | React/TypeScript/router/Query/form/tokens, sáu route; npm ci/typecheck/build và Chromium desktop/mobile đạt. Shell chưa gọi API. |
| T004 | NOT_RUN | Chưa bắt đầu vì T002 chưa nghiệm thu. |
| T005 | BLOCKED | Đã có frontend Dockerfile/nginx config; thiếu Docker để build/nginx syntax/proxy guards/API proxy verification. |
| T006–T014 | NOT_RUN | Chưa bắt đầu vì các prerequisite T002/T004/T005 và hạ tầng Docker chưa đạt. |

## Môi trường và công cụ

- Windows PowerShell, Python3.13.15, virtual environment `.venv`; chưa có Python3.12 local.
- Docker/Compose không tìm thấy trong PATH; đường dẫn Docker Desktop thông dụng cũng không có.
  Không cài Docker hoặc thay cấu hình hệ thống. Điều kiện đầu vào Linux containers chưa đáp ứng.
- Node22.21.1 portable/npm10.9.4 trong `.tools`, archive chính thức nodejs.org đã so SHA256
  `3c624e9fbe07e3217552ec52a0f84e2bdc2e6ffa7348f3fdfb9fbf8f42e23fcf`.
- Build1.3.0/setuptools80.9.0/wheel0.45.1/pytest8.4.2 được cài trong `.venv` qua PyPI sau khi
  truy cập socket trong sandbox bị chặn. Node/browser/cache/venv đều nằm trong workspace và bị ignore.
- Playwright1.56.1, Chromium141.0.7390.37. Browser checks là shell-only, không DB/Airflow E2E.

## Lệnh và kết quả thực tế

Các lệnh Python bên dưới dùng `.venv\Scripts\python.exe` sau khi tạo venv và cài build tools.

| Kiểm chứng | Lệnh/kết quả |
| --- | --- |
| RED trước implementation | `python -m unittest discover -s tests/unit -v`: FAIL do thiếu packages/manifests/attributes và mẫu CRLF; workbook hash đã đúng. |
| GREEN skeleton/artifact | `python -m unittest discover -s tests/unit -v`: 6test PASS sau implementation. |
| Pytest | `python -m pytest tests/unit -q`: 6PASS. |
| Wheel build | `python -m build --wheel --no-isolation` cho backend, packages/aat_metadata và etl_engine: cả3PASS. |
| Editable install | `python -m pip install --no-deps --no-build-isolation -e packages/aat_metadata -e etl_engine -e backend`: PASS. |
| Isolated import | Python `-I` import aat_metadata/aat_etl/aat_api, version0.1.0 và không có fastapi/airflow trong sys.modules: PASS. |
| Frontend | Trong frontend: `npm ci --no-audit --no-fund`, `npm run typecheck`, `npm run build`: PASS. Build326.72kB JS/7.35kB CSS trước nén. |
| Shell browser | `npm run test:shell`: 12route-viewport checks PASS; navigation search/menu mobile hoạt động, không overflow ngang, 0page errors. |
| Docker/Compose | `docker version`, `docker compose version`: BLOCKED — command không tồn tại. |
| Linux runtime/pip check | NOT_RUN — không dùng venv Python3.13 cài no-deps làm bằng chứng runtime. |
| T005 nginx/image | NOT_RUN — không dùng Vite preview thay nginx hoặc Docker image. |

Build Vite lần đầu trong sandbox bị lỗi quyền đọc thư mục cha của esbuild; chạy lại npm ci/build
với quyền chạy tiến trình phù hợp đã thành công. Lần npm install với `--prefix frontend` ban đầu
báo ENOENT package.json ở root; chạy trực tiếp với working directory frontend đã thành công.
Đây là kết quả thất bại đã khắc phục, không bị tính thành test sản phẩm PASS.

Kết quả browser dạng máy đọc: [phase1-shell.json](phase1-shell.json).
SHA256 wheels đã build: [phase1-wheel-hashes.json](phase1-wheel-hashes.json); wheel outputs
nằm trong dist bị ignore. Hash đó là của lần build hiện tại, chưa cam kết build bit-for-bit.

## Khóa dependency và giới hạn

Constraints lấy từ kho Apache chính thức:
`https://raw.githubusercontent.com/apache/airflow/constraints-3.3.2/constraints-3.12.txt`;
SHA256 `821effd0f491975682f2774fca3427d7bc2f59ca6de68dcb413ad2c8f890e58c`,
lưu cạnh file ở `airflow/docker/constraints-3.12.sha256`.

Hai lần resolve thực tế dùng pip26.2.1, PyPI, `--only-binary=:all: --python-version 3.12`,
với các platform tags `manylinux_2_34_x86_64`, `manylinux_2_28_x86_64`,
`manylinux2014_x86_64`, `manylinux_2_17_x86_64`:

```powershell
python -m pip download --only-binary=:all: --python-version 3.12 --platform manylinux_2_34_x86_64 --platform manylinux_2_28_x86_64 --platform manylinux2014_x86_64 --platform manylinux_2_17_x86_64 --dest .tools/wheels/backend -r backend/requirements.in
python -m pip download --only-binary=:all: --python-version 3.12 --platform manylinux_2_34_x86_64 --platform manylinux_2_28_x86_64 --platform manylinux2014_x86_64 --platform manylinux_2_17_x86_64 --dest .tools/wheels/runtime -c airflow/docker/constraints-3.12.txt -r etl_engine/requirements.in
```

Lock ghi name/version từ METADATA từng wheel, SHA256 từ raw bytes. Mỗi môi trường đã được
pip tải lại offline với `--no-index --find-links .tools/wheels/<environment> --require-hashes`,
giữ nguyên target tags, `-r <requirements.lock>` và dest `<environment>-verified`: PASS.
Điều này chứng minh artifact resolve/hash, không chứng minh binary import hoặc Linux markers.

Backend là môi trường riêng, giữ Uvicorn0.38.0 theo Plan; constraints Airflow chính thức
pin Uvicorn0.52.4, nên không áp toàn bộ constraints Airflow lên backend riêng. ETL shared
dependencies theo constraints; metadata/engine không phụ thuộc Uvicorn/FastAPI/Airflow.
Windows-based target resolution có thể đánh giá marker theo host, nên cả hai lock còn phải
được kiểm/hoàn thiện trong Linux/Python3.12 trước build/install production. Không hỗ trợ
ARM từ lock hiện tại. Không thay đổi pin thiết kế để vượt qua resolver hoặc compatibility gate.

## Artifact mẫu và bước tiếp theo

Đã thêm `.gitattributes` và materialize LF riêng hai sample sau khi kiểm normalization
khớp manifest lịch sử, không overwrite dữ liệu khác hoặc normalize upload của người dùng.
Raw hash CSV `e5a9d8f77e05faaaf973c9fdc08df3f5f2652963ad9fc309881241291cd954fc`,
TXT `704a390b7bace232b578d55270ffbacbe1d71d6e370be975ed38dcf250d94fcd`.
Bốn workbook giữ nguyên bytes/hash. CI Windows/Linux tại T014 chưa thực hiện.

Tiếp tục sau khi có Docker Linux containers/Compose: kiểm target locks và pip check T002,
rồi T004/T006 và các nhánh đủ prerequisite; build/kiểm nginx T005, hoàn thiện init/secrets/DB/
Compose/health/smoke T007–T014. Chỉ đóng gate Phase1 khi mọi tiêu chí có evidence thật.

## Tiếp tục Phase1 trên Podman — 2026-11-08

Phần này cập nhật trạng thái hiện hành, các kết quả thiếu Docker phía trên là lịch sử.
Không thay đổi Constitution1.1.0, pin hoặc checklist reviewer.

| Kiểm chứng thực tế | Kết quả |
| --- | --- |
| Backend Linux/Python3.12.12: pip install offline --require-hashes từ lock 32 dependency, pip check | PASS |
| Airflow image3.3.2/Python3.12.14: runtime lock14 dependency dưới constraints chính thức, pip check, airflow version | PASS; vẫn3.3.2 |
| podman build -t localhost/aat-frontend:0.1.0 -f frontend/Dockerfile . | PASS |
| pytest tests/integration/test_frontend_proxy.py -v | PASS:4test, nginx thật/upstream fixture cô lập |
| podman build --format docker -t localhost/aat-backend:0.1.0 -f backend/Dockerfile . | PASS: wheels/import dependencies/pip check |
| pytest -p no:cacheprovider tests/integration/test_backend_bootstrap.py -v | PASS:1test; liveness200, ready404, import và pip check trong container |

Private guards kiểm16 tổ hợp path/method/bearer và counter upstream không thay đổi;
fixture bearer không thay kiểm authorization endpoint thật ở T103.
Backend chỉ báo stage bootstrap; không Connections, US1 hoặc product readiness.
Image frontend build OCI ban đầu bỏ HEALTHCHECK theo cảnh báo Podman; Compose phải có
healthcheck tường minh và được kiểm thật tại T011/T012. Không coi cảnh báo đó là health PASS.
Pytest proxy có warning cache permission trên host; 4assertion test đều PASS; lần sau dùng
-p no:cacheprovider. Tài nguyên fixture được cleanup riêng; preview4173 không bị dừng.

### Preflight runtime thực tế

- Podman client5.8.3 windows/amd64; server5.8.9 linux/amd64; machine
  podman-machine-default đang Running, WSL, rootful, seccomp bật, cgroupv2.
- Compose provider là Docker Compose v5.6.0 từ WinGet, chọn bằng
  `$env:PODMAN_COMPOSE_PROVIDER=(Get-Command docker-compose.exe).Source` trước lệnh Podman.
- Engine info: 12CPU, RAM8.280.391.680bytes; metadata machine ghi6CPU/2GiB nên không
  lấy metadata đó làm bằng chứng memory limit thực. Không thay cấu hình machine.
- `podman machine ssh 'df -h /var/lib/containers; free -m'`: disk930GiB còn trống,
  available RAM7045MiB tại thời điểm kiểm; không thay yêu cầu mem_limit của service.
- `Invoke-WebRequest http://127.0.0.1:4173`: HTTP200; giữ preview hiện hữu.
- Lệnh preflight template Host.Os lần đầu FAIL vì sai field name; đọc JSON Host.os
  thành công sau đó. Không phải lỗi engine.

### Image/runner và secrets/DB

- T004 PASS: backend bootstrap test1PASS; `podman run --rm localhost/aat-backend-tests:0.1.0`
  chạy6unit test PASS trên Linux/Python3.12.12. Runner E2E `npx playwright test --list` collect
  4test; Chromium141.0.7390.37 launch thật từ image mcr.microsoft.com/playwright:v1.56.1-noble.
- Lần browser probe dùng node -e FAIL do quote qua PowerShell; đổi stdin node - rồi PASS.
  Không đổi client/browser pin1.56.1.
- T006 PASS: custom Airflow build, SDK/metadata/engine imports, pip check, entrypoint version3.3.2.
- T007 test RED thiếu aat_metadata.secrets trước implementation; GREEN1PASS trên Linux
  kiểm key_id/ciphertext/decrypt/idempotence/missing-key fail. Secret CLI named volume
  ban đầu FAIL AttributeError do script secrets.py che stdlib secrets; sửa sang os.urandom
  và fixture sạch đã chạy secrets-init Exited(0), DBs đọc được admin secret files.
- `pytest -p no:cacheprovider tests/integration/test_database_bootstrap.py -q --tb=short`:
  PASS1test44.33s với PostgreSQL17.6/MySQL8.4.7 thật. Init2lần giữ sample edit, runtime PG
  bị chặn Airflow metadata, MySQL InnoDB/utf8mb4/strict và grants giới hạn.
- Một lần fixture trước cần sửa podman cp vì pathlib bỏ trailing /. khiến script sai
  vị trí; không dùng lần chỉnh container trực tiếp làm bằng chứng sạch. Lần44.33s là
  chạy lại độc lập sau sửa test harness, cleanup đúng tài nguyên sở hữu.

### Airflow auth và wiring Compose

`AAT_TEST_AIRFLOW=1 pytest -p no:cacheprovider tests/integration/test_database_bootstrap.py -q --tb=short`:
PASS1test148.50s. Official migration2lần Exited(0), anonymous API401/403, service JWT
authentication/API dags200 và UI200; token/password không in ra. Config CLI trả
LocalExecutor và parallelism2.

`pytest ... test_compose_bootstrap_wiring.py::ComposeDependencyTests`: PASS1test18.60s;
init exit23 chặn consumer trên Podman/provider thật, cleanup đúng project test.

Startup tại workspace gốc FAIL trước build: Compose classic builder không stat được
.pytest_cache có ACL chặn truy cập. Get-Acl và Move-Item riêng cache cũng bị OS từ chối;
không thay ACL hoặc xóa dữ liệu. Thêm ignore vẫn không vượt lỗi stat của client.
Fixture `.tools/phase1-clean` copy đúng bytes source cần build, bỏ cache/build outputs;
đây là chuẩn bị fixture kiểm thử, không phải bước setup sản phẩm. Chạy đúng
`podman compose up --build -d` tại fixture với project đọc từ `.tools/phase1-project.txt`.
Kết quả fixture phải báo riêng, không thay kết quả startup FAIL tại workspace gốc.

### Kết quả Compose fixture đầu và bản probe cuối

- Fixture đầu `podman compose up --build -d`: PASS; init4service Exited(0), DB/Airflow/
  worker/backend/frontend đều healthy. `ComposeStackWiringTests`: PASS1test3.65s, kiểm
  actual cgroup memory1GiB mỗi DB/2GiB scheduler, UID50000, DAG/secret RO, loopback ports
  và FinishedAt/StartedAt của dependency. Backend health chỉ liveness bootstrap.
- Test profile build hai runner PASS; pytest collect7unit test và Playwright collect4test
  qua `compose --profile test run --rm --no-deps ...`: PASS.
- Bổ sung secret volume riêng postgres_secrets/mysql_secrets để mỗi DB chỉ đọc admin
  secret của chính nó; admin bootstrap tổng hợp chỉ cấp one-shot db-init, không runtime.
  Loại app_owner khỏi backend_secrets. Không đổi quyền/grants nghiệp vụ hoặc secret pin.
- Dọn riêng project fixture đầu aat-phase1-4f454dc8 và volumes test sở hữu. Chuẩn bị lại
  fixture bằng tests/tools/prepare_phase1_fixture.py;94file đối chiếu raw SHA256 nguồn/đích
  bằng nhau, không normalize bytes. Bản cuối dùng health.py/health.sh và domain secret riêng
  đang kiểm fresh startup; không dùng bằng chứng bản trước để tự đóng gate bản mới.

## Tiếp tục nghiệm thu bản cuối ngày 2026-11-08

- Preflight: Podman client5.8.3/server5.8.9, Compose5.6.0; phiên startup cũ kết thúc exit0.
  Tiếp nhận project aat-phase1-7e2b3818;4init Exited(0),8service healthy, preview4173 HTTP200.
- Checklist giữ nguyên: requirements16/16, spec-quality48/48; không là test runtime.
- Wiring + fault injection:4PASS33.11s. Scheduler dừng làm JSON unhealthy dù HTTP200,
  MySQL dừng làm query probe fail, liveness vẫn đúng; dependency phục hồi sau test.
- Persistence lần đầu FAIL đúng lỗi quyền: uploads/staging root:root1755, worker không ghi
  được. Không nới UID/quyền hoặc reset volumes. Thêm volume.nocopy=true cho shared DAG/
  uploads/staging/logs để init sở hữu quyền; startup lại giữ data hiện hữu, stat cả3data
  dirs750:50000:50000. Đang nghiệm thu lại fresh và restart; chưa coi sửa config là PASS.

- Sau nocopy, startup lại project cũ không xóa volumes; data dirs750:50000:50000.
  Dừng project cũ aat-phase1-7e2b3818 bằng compose down KHÔNG -v, giữ volumes để đối chiếu.
  Project fresh mới aat-phase1-800be543 đang chạy test AAT_FRESH_START=1: lệnh startup
  chuẩn, sửa sample DB và ghi markers đã thành công, đang down/up giữ volumes.
- Runner image source hiện tại:7unit test PASS0.11s (Linux/Python3.12.12), gồm secret
  idempotence/mất key và raw sample/workbook hashes.

### Kết quả nghiệm thu runtime sau sửa nocopy

| Kiểm chứng | Kết quả |
| --- | --- |
| AAT_FRESH_START=1 pytest test_bootstrap_startup.py -v | PASS1test249.15s; fresh và restart cùng volumes, secrets/data/artifacts giữ nguyên |
| pytest test_compose_bootstrap_wiring.py test_bootstrap_health.py -q | PASS4test34.72s trên project fresh cuối; cả dependency được phục hồi |
| compose --profile test run --rm --no-deps backend-tests | PASS7unit test0.10s |
| profile backend-tests python docker/bootstrap/check_databases.py | PASS; PG/MySQL thật, init2lần/grants/strict/sample edit và signature collision bị chặn |
| profile backend-tests python docker/bootstrap/check_airflow.py | PASS auth/API/UI thật, không anonymous |
| profile e2e-tests | PASS4test4.2s;6routes1440/390, private runtime guards |
| pytest test_bootstrap_secret_logs.py | PASS; đối chiếu secret values trong backend/Airflow domains với log các service, không in values |
| test_image_compatibility.py | RED thiếu images.lock, sau ghi digest thật GREEN3PASS13.06s; linux/amd64, pip check/SDK/browser |
| npm run typecheck; npm run build | PASS; JS326.72kB/CSS7.35kB |
| npm audit --json | FAIL exit1;2HIGH ở react-router và zod; raw report .tools/security/npm-audit.json |

T001–T013 hoàn thành trong phạm vi bootstrap. T014 chưa hoàn thành: image scan/triage và
CI Windows/Linux chưa đủ bằng chứng. Không tự sửa pin hoặc chấp nhận vulnerability để mở gate.
Project cũ aat-phase1-7e2b3818 đã down không -v, volumes giữ nguyên; project hiện hành
aat-phase1-800be543. Không chuyển Phase2, không sửa reviewer checklist.

### T014 — compatibility, CI và security

- Ghi docker/images.lock bằng tests/tools/record_image_baseline.py từ7image đã pull thật,
  không bịa digest hoặc đổi version. Compatibility3test PASS13.06s: platformlinux/amd64,
  backend/Airflow pip check/SDK imports, Playwright1.56.1 với browser141.0.7390.37.
- CI workflow sample-artifacts.yml đã tạo với Windows/Linux, Python3.12 và contents:read.
  Parse YAML/matrix/permissions PASS; remote CI NOT_RUN, không được dùng parse thay runtime.
  Sample artifact tests trên Windows:3PASS; Linux container đã kiểm cùng raw hashes trong7unit.
- npm typecheck/build PASS; npm audit exit1,2gói HIGH: react-router7.9.6 và zod4.1.12.
  Audit nêu fix candidates7.18.5 và4.6.7; đây là dữ liệu audit, chưa là baseline được duyệt
  hoặc bằng chứng tương thích. Giữ pin theo yêu cầu; chi tiết phase1-npm-audit.json.
- Chọn Trivy0.76.1 từ release chính thức và pin registry digest lúc chạy; scanner chỉ nhận
  archive image RO, report/cache volume riêng, không engine socket hoặc secret volumes.
  Nguồn cách chạy: [official release](https://github.com/aquasecurity/trivy/releases/tag/v0.76.1),
  [official images](https://trivy.dev/docs/latest/getting-started/installation/),
  [archive input](https://trivy.dev/docs/latest/target/container_image/#tar-files).
- Scan là OS/language vulnerabilities, mọi severity, không ignore-unfixed; không thay
  pentest, analysis exploitability hoặc kiểm bảo mật sản phẩm Phase8. Trivy cảnh báo
  third-party SBOM/severity nguồn vendor khác trên một số target; cần triage findings.
- Secret log test mở rộng cả bootstrap admin/app-owner domains PASS28.16s; secret values
  chỉ dùng trong tiến trình đối chiếu, không in hoặc lưu vào báo cáo.
- Socket host đo bằng Get-NetTCPConnection:3000/8000/8080/4173 chỉ LISTEN127.0.0.1.
- README đã đồng bộ bootstrap, startup/restart, secret domains, nocopy, probes, test profile
  và giới hạn runtime. Preview4173 được giữ; UI cards còn tĩnh, không thay health probe.

### Kết quả image scan cuối và giới hạn

Trivy0.76.1 đã scan7image bằng digest scanner thật. Backend test runner được rebuild
để chứa root tests mới; đã scan bổ sung đúng image851baad832fb thay kết quả61fb2b062a49.
Đối chiếu toàn bộ7image IDs trong báo cáo với tags hiện tại PASS. Runtime/source và
root tests trong runner đối chiếu8SHA256 PASS; không dùng kết quả source cũ.

| Image | HIGH | CRITICAL | Đánh giá |
| --- | ---: | ---: | --- |
| backend | 74 | 9 | BLOCKED — cần triage |
| airflow | 188 | 23 | BLOCKED — cần triage |
| frontend | 61 | 3 | BLOCKED — cần triage |
| postgres | 140 | 20 | BLOCKED — cần triage |
| mysql | 142 | 2 | BLOCKED — cần triage |
| backend-tests | 74 | 9 | BLOCKED — cần triage |
| e2e-tests | 52 | 3 | BLOCKED — cần triage |

Đây là số finding occurrences theo scanner, không phải số CVE duy nhất hoặc xác nhận
khả năng khai thác. Scan execution thành công không là security PASS. Cần triage theo
package, version, vendor advisory và đường dùng thực; không tự ignore hoặc hạ severity.
DB vulnerability version2 UpdatedAt2026-11-08T06:39:21Z; Java DB version1 UpdatedAt
2026-11-08T00:58:16Z. Digest/version/DB metadata và HIGH/CRITICAL details/PrimaryURL
ở phase1-security.json; raw reports .tools/security/<image>.json. Archive/report volumes
riêng của scanner đã cleanup; DB cache giữ để tái kiểm, tên ở .tools/security/scan-resources.json.
Scanner không nhận engine socket hoặc secret volumes.

Ví dụ findings cần đối chiếu: backend libgnutls30 3.7.9-2+deb12u6 có
CVE-2026-33845/CVE-2026-42010, scanner nêu fixed3.7.9-2+deb12u7; frontend brotli-libs
1.1.0-r2 có CVE-2026-111497, fixed1.1.1-r0. Không tự cài OS patch hoặc đổi base digest.
Đây là dữ liệu scanner, chưa phải khuyến nghị baseline thay thế đã nghiệm thu.

### Blocker và cách đóng gate

1. **Security/pin decision:** triage image và npm findings; duyệt hướng xử lý/baseline
   pin/digest nếu cần. Npm đưa candidates react-router7.18.5/zod4.6.7, chưa được duyệt
   hoặc kiểm tương thích. Sau thay đổi được duyệt phải resolve lock, audit/scan và chạy
   lại các gate bị ảnh hưởng; giữ BR-08/readiness/secrets/resources. Lượt này bị ràng buộc
   không đổi pin nên chưa thể tự xử lý các findings bằng nâng version.
2. **CI NOT_RUN:** workflow sample-artifacts.yml cần chạy trên commit chứa thay đổi
   bằng Windows/Linux runners và lưu kết quả. Chưa commit/push/publish source hoặc
   trigger CI remote trong lượt này; không dùng YAML parse/local unit PASS thay CI PASS.
3. **Workspace ACL:** checkout sạch có quyền đọc hoặc xử lý ACL cache dưới quyền phù
   hợp ngoài bootstrap. Không reset ACL/volumes để né lỗi; giữ kết quả fixture riêng.

Final-state kiểm4init Exited(0),8service healthy, HTTP shell3000/preview4173/Airflow8080
200, live200/ready404 và hai private frontend paths404; reviewer hashes không đổi.
Không có Phase2 implementation hoặc thay đổi DAG Builder. Gate Phase1 vẫn BLOCKED,
T014 giữ [ ]; tài liệu/compatibility validation không được coi là product runtime PASS.
