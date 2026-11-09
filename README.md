# Airflow Automation Tool

T001–T013 đã kiểm chứng trong phạm vi bootstrap. **Phase 1 chưa được nghiệm thu**: T014
còn security findings và các gate tái kiểm. CI Windows/Linux tại HEAD `b29ae86` đã PASS;
thay đổi T014 trong working tree lượt này chưa chạy CI remote. Phase 2 mới viết tests
T015/T016 theo quyền local có hạn; chưa triển khai nghiệp vụ US-01 hoặc MVP.
Xem [kết quả T015/T016 và quyền local](docs/testing/t015-t016-report.md).
UI hiện là shell sáu màn hình; chưa có Connections CRUD, DAG Builder,
ETL hoặc Dashboard metrics hoạt động. Bằng chứng ở [báo cáo Phase 1](docs/testing/phase1-report.md).
Các service cards trên shell còn là trạng thái tĩnh chưa nối API, không phải kết quả health probe.

Kết quả tiếp tục ngày 2026-11-09: [báo cáo T014 hiện hành](docs/testing/t014-current-report.md).
Môi trường máy này là Podman6.1.1/Compose5.6.0: A/B đã triển khai, fresh/restart/persistence,
13unit/4E2E/5compatibility/7runtime tests và UI Airflow auth PASS. Chi tiết tại
[báo cáo A/B](docs/testing/t014-ab-report.md). Candidate test ở13000/18000/18080;
các địa chỉ/stack khác trong phần lịch sử không chứng minh dịch vụ hiện đang chạy.

## Baseline và điều kiện đầu vào

- Lượt A/B đã kiểm bootstrap trên Podman client/server6.1.1, WSL Linux/amd64,
  rootful/cgroupv2 và Docker Compose5.6.0. Tổ hợp5.8.3/5.8.9 thuộc bằng chứng lịch sử;
  không suy PASS giữa hai môi trường. Không cần Docker Desktop; Docker baseline chưa kiểm riêng.
- Engine/machine đã chạy, quyền pull/build và cổng loopback3000/8000/8080 còn trống.
  Khuyến nghị theo Plan:8CPU,12GiBRAM,80GiB disk trống. Engine kiểm thực tế báo12CPU,
  khoảng7,7GiBRAM; metadata machine khác engine nên không dùng để suy ra resource limit.
- Không cần Python/Node/browser trên host để chạy stack hoặc test profile. Không cần copy
  `.env.example`; secret local được sinh một lần trên named volumes, không in giá trị.
- Tám base/build/browser image digests thật ở [images.lock](docker/images.lock). Lock Python
  chỉ hỗ trợ Linux x86_64/CPython3.12; backend và Airflow là hai môi trường riêng.

Chọn đúng provider trong phiên PowerShell; kiểm version trước khi startup:

```powershell
$env:PODMAN_COMPOSE_PROVIDER=(Get-Command docker-compose.exe).Source
podman version
podman compose version
```

Trên máy của lượt A/B, provider portable đã xác minh nằm ở
`.tools/docker-compose-5.6.0.exe`; dùng `(Resolve-Path .tools/docker-compose-5.6.0.exe).Path`
cho `PODMAN_COMPOSE_PROVIDER`. File này là công cụ local không nằm trong Git; checkout mới
cần chuẩn bị Compose5.6.0 theo điều kiện đầu vào. Để tiếp tục project test hiện có, dùng
đúng project/ports trong [báo cáo A/B](docs/testing/t014-ab-report.md), tránh tạo stack trùng.

## Một lệnh startup

Từ checkout sạch có quyền đọc build context:

```powershell
podman compose up --build -d
```

Init tự tạo secrets, DB/roles/sample data, chuẩn bị storage và chạy official Airflow
migration. `app-init` Phase1 chỉ chuẩn bị storage; app schema/migrations/seed đầy đủ thuộc
T030. Backend chỉ có `/api/v1/health/live`; `/api/v1/health/ready` chưa triển khai và trả404.
Worker hiện chỉ có heartbeat bootstrap, chưa xử lý Operation.

| Địa chỉ | Phạm vi hiện tại |
| --- | --- |
| http://localhost:3000 | Frontend shell qua nginx; public proxy `/api/v1` |
| http://localhost:8000/api/v1/health/live | Liveness với stage bootstrap |
| http://localhost:8080 | Airflow UI, SimpleAuth local user `operator` |
| http://localhost:4173 | Preview shell hiện hữu của phiên phát triển, được giữ nguyên |

Password Airflow operator nằm trong secret volume `airflow_secrets`, file
`/secrets/airflow/operator_password` trong container apiserver. Chỉ đọc tại terminal local
khi cần đăng nhập; không đưa giá trị vào báo cáo/log/source. Service account riêng dùng JWT.
Không bật anonymous all-admin.

## Persistence, readiness và quyền

DB không publish host port; các port web chỉ bind127.0.0.1. Scheduler có memory limit2GiB,
mỗi DB1GiB và đã kiểm cgroup thật. Runtime UID50000; bootstrap root chỉ thiết lập storage/
secrets. Secret admin từng DB ở domain riêng; admin tổng hợp chỉ mount one-shot db-init,
không cấp cho backend/Airflow runtime. Backend không nhận app_owner password.

DAG writer là backend-worker; scheduler/dag-processor/apiserver mount DAG read-only.
Shared DAG/uploads/staging/logs dùng `volume.nocopy=true` để giữ UID/GID do init thiết lập,
không để copy-up thay quyền của volume rỗng. Không chmod777, không privileged.

DB health thực hiện SELECT1. Airflow API probe kiểm JSON metadatabase/scheduler/dag_processor;
HTTP200 không đồng nghĩa healthy. Scheduler/dag-processor kiểm heartbeat CLI. Backend health
ở Phase1 chỉ là liveness, không tuyên bố readiness sản phẩm.

Khởi động lại có kiểm thứ tự init, giữ toàn bộ volumes:

```powershell
podman compose down
podman compose up --build -d
```

Không thêm `-v` khi cần giữ dữ liệu. Mất key/secret đã khởi tạo phải phục hồi đúng volume
ban đầu; bootstrap không tự thay key để bỏ qua lỗi. Init lỗi dừng consumer và giữ dữ liệu.

## Kiểm thử Phase 1

Trên project test riêng, không dùng project chứa dữ liệu thật cho fault injection:

```powershell
podman compose --profile test build backend-tests e2e-tests
podman compose --profile test run --rm --no-deps backend-tests
podman compose --profile test run --rm --no-deps e2e-tests
```

Runner chứa root tests và Playwright client1.65.0/browser Chromium158.0.8127.18 từ image
v1.65.0-resolute theo B đã duyệt. Test profile không chạy mặc định; E2E dùng http://frontend:80 trong network.
Fixture hiện hành đọc từ `.tools/phase1-project.txt`; đặt COMPOSE_PROJECT_NAME đúng project
khi tiếp tục fixture, không tạo stack trùng cổng. Các kiểm thử host điều phối Podman:

```powershell
$env:PODMAN_BIN=(Get-Command podman.exe).Source
$env:AAT_COMPOSE_PROJECT=(Get-Content .tools/phase1-project.txt).Trim()
$env:AAT_COMPOSE_DIR=(Get-Content .tools/phase1-compose-dir.txt).Trim()
$env:AAT_AIRFLOW_URL='http://127.0.0.1:18080'
$env:AAT_AIRFLOW_PORT='18080'
$env:AAT_BACKEND_PORT='18000'
$env:AAT_FRONTEND_PORT='13000'
python -m pytest -p no:cacheprovider tests/integration/test_compose_bootstrap_wiring.py tests/integration/test_bootstrap_health.py
```

`test_bootstrap_startup.py` kiểm fresh khi AAT_FRESH_START=1 trên project mới chưa tồn tại,
rồi down/up không -v để so sánh secret hashes, DB edits và file markers. Fault injection chỉ
chấp nhận project test `aat-phase1-*`, khôi phục dependency trong finally.

CI [sample-artifacts.yml](.github/workflows/sample-artifacts.yml) kiểm checkout Windows/Linux
bằng raw LF/SHA256/XLSX bytes, không normalize upload. Workflow đã tạo nhưng chưa chạy CI
remote; unit PASS tại Windows/Linux container không thay CI PASS.

## Lỗi môi trường và security còn lại

Workspace gốc có `.pytest_cache` bị ACL chặn đọc/stat, khiến Compose classic builder FAIL
trước build dù đã ignore. Không reset ACL hoặc xóa cache đó. Fixture `.tools/phase1-clean`
được tạo bằng `tests/tools/prepare_phase1_fixture.py`, đối chiếu raw SHA256 với source;
PASS tại fixture không thay kết quả startup workspace gốc. Có thể xem stack fixture đang
chạy ở3000; preview4173 không bị dừng. Để build bình thường cần checkout sạch có quyền đọc
hoặc xử lý ACL ngoài bootstrap dưới quyền quản trị phù hợp.

P1–P7 đã được duyệt và áp dụng. `npm audit` full/production trên lock Router7.18.5/Zod4.6.7
đều báo0 vulnerabilities; [kết quả hiện hành](docs/testing/phase1-npm-audit.json). Image scan dùng
Trivy0.76.1 từ registry chính thức, pin digest lúc chạy, đọc archive riêng; không cấp socket
engine hoặc secret volumes cho scanner. Script `tests/tools/scan_phase1_images.py` ghi
coverage/DB version/image IDs/findings, không coi exit0 của scanner là không có vulnerability.
Scan12targets gồm7final và5build/toolchain: frontend final0HIGH/CRITICAL, các target khác
còn findings. Chi tiết ở [phase1-security.json](docs/testing/phase1-security.json) và
[triage hiện hành](docs/testing/t014-security-triage.csv). Candidate shell ở
http://localhost:13000, backend live18000 và Airflow18080; stack cũ/preview4173 được giữ.
Gate Phase1 BLOCKED; không dùng compatibility PASS thay security PASS.

Thiết kế canonical: [Plan](specs/001-airflow-automation-tool/plan.md),
[Tasks](specs/001-airflow-automation-tool/tasks.md),
[Quickstart sản phẩm dự kiến](specs/001-airflow-automation-tool/quickstart.md).

## Hardening tương thích T014 lượt2

Npm12.2.2 đã build/typecheck/audit trên Node22.23.4 Windows/Linux. Airflow3.3.2 giữ
constraints/core/SDK, thêm exact OS patch lock và bỏ Docker CLI/uv extra/prek lint env
không có consumer trong LocalExecutor MVP. PostgreSQL17.11/MySQL8.4.13 dùng child images
được build tại docker/gosu/Dockerfile: gosu1.19 cùng source commit/hash, Go1.27.3; MySQL
không cài mysql-shell không có dependent/consumer. Public Airflow base URL nhận đúng
AAT_AIRFLOW_PORT khi dùng project test port khác; default8080 không đổi.
Chủ dự án đã duyệt A/B ngày2026-11-09: Playwright1.65.0/Resolute và hai override
certifi2026.10.18/urllib3 2.8.0 bằng constraints hiệu lực riêng; upstream giữ nguyên hash.
T014 còn BLOCKED; trạng thái kiểm chứng/CI mới xem báo cáo Phase1, không dùng PASS cũ.

Remediation tiếp theo ngày2026-11-09 bổ sung dnspython2.9.0 vào policy/hash riêng và
chuyển toolchain gosu Go1.27.3 sang Alpine3.24 theo digest đã scan; giữ DB/core versions.
CI Windows/Linux của implementation commit d57db09 đã PASS. T014 chưa đóng vì security;
xem [báo cáo vòng3](docs/testing/t014-r3-report.md) để biết đúng IDs/phạm vi kiểm thử.

## Quyền phát triển local có điều kiện

Chỉ dùng khi có quyết định chủ dự án còn hạn và các điều kiện kích hoạt đã khép,
theo docs/proposals/t014-conditional-local-gate.md. Đề xuất DRAFT không phải approval.
Nhãn: bootstrap PASS; security FAIL_WITH_APPROVED_LOCAL_EXCEPTIONS; T014_FULL BLOCKED;
PHASE2_LOCAL_ELIGIBILITY chỉ AUTHORIZED khi owner/reviewer/baseline/controls/hạn đầy đủ.
Migrations nghiệp vụ dùng namespace/volumes mới, giữ stack A/B/R3. Không dữ liệu thật,
public/tunnel. Chưa nghiệm thu toàn bộ MVP; hết hạn/vượt scope thì dừng phần phụ thuộc,
review lại, không tự gia hạn hoặc bỏ scanner.
