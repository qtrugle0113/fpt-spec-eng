# Đề xuất hỗ trợ Podman — đã được chủ dự án duyệt

**Ngày soạn/duyệt**: 2026-11-08. **Trạng thái**: Chủ dự án đã duyệt nội dung bằng phản hồi
“ok duyet”; đã áp dụng Constitution1.1.0 và đồng bộ tài liệu. Bản mô tả dưới đây lưu nội
dung sửa đã duyệt và kết quả kiểm tra môi trường ở thời điểm đề xuất, không phải runtime PASS.
Lượt soạn đề xuất trước khi duyệt chỉ kiểm tra môi trường, không sửa quy tắc hoặc chạy stack.
Lượt áp dụng sau duyệt chỉ đồng bộ quản trị/tài liệu; chưa tiếp tục build/run stack.

## Kết quả kiểm tra thực tế

| Nội dung | Kết quả đọc được |
| --- | --- |
| Podman client | 5.8.3, `C:\Program Files\RedHat\Podman\podman.exe` |
| Machine | podman-machine-default, WSL, State=running |
| Podman server | 5.8.9; Linux/amd64, cgroup v2 |
| Quyền runtime | Rootful=true; thông tin này không cho phép container chạy đặc quyền tùy ý |
| Tài nguyên cấu hình machine | 6CPU, metadata Memory2GiB, disk capacity100GiB |
| Bộ nhớ engine thực báo | MemTotal8.280.391.680bytes (~7,71GiB), MemFree7.372.234.752bytes lúc kiểm |
| Compose provider | Docker Compose5.6.0, `docker-compose.exe` trong WinGet; được `podman compose version` chọn và thực thi |
| Tùy chọn provider | `podman compose up --help` có --build/--detach/--wait/--wait-timeout |
| Build/container/stack | NOT_RUN trong lượt này; help/version không chứng minh Compose semantics hoặc workload tương thích |

Thông tin Memory2GiB trong machine metadata khác memory engine thấy trong WSL. Không suy
machine thực bị giới hạn2GiB từ metadata, cũng không coi7,71GiB đủ cho toàn stack/stress.
Plan hiện khuyến nghị host8CPU/12GiBRAM/80GiB disk trống; capacity100GiB không chứng minh
free disk còn80GiB. Chưa đo cgroup limits hoặc disk free của workload.
CLI/server khác phiên bản phải được ghi trong baseline và kiểm thực tế; không tự nâng cấp,
downgrade hoặc đổi machine để làm phiên bản bằng nhau.

Các lệnh đọc đã chạy ngoài sandbox để truy cập cấu hình/socket cá nhân:

```powershell
podman --version
podman machine list --format json
podman machine inspect podman-machine-default --format '{{.State}}'
podman machine inspect podman-machine-default --format '{{.Rootful}}'
podman info --format json
podman compose version
podman compose up --help
```

`podman info` được lọc chỉ lấy OS/arch/cgroups/rootless/memory/server version cho báo cáo.
Lỗi kết nối ở lượt trước là ghi nhận lịch sử; lần này engine đã phản hồi. Không tự động
chuyển T002/T005 từ BLOCKED sang PASS chỉ vì kết nối đã được khôi phục.

Theo [Podman5.8.3 — compose](https://docs.podman.io/en/v5.8.3/markdown/podman-compose.1.html),
`podman compose` là wrapper cho external provider và thiết lập kết nối Podman socket;
có thể chọn provider bằng `PODMAN_COMPOSE_PROVIDER` hoặc containers.conf.
[Hướng dẫn Compose của Podman Desktop](https://podman-desktop.io/docs/compose/setting-up-compose)
phân biệt Compose provider với Podman engine. Vì vậy không phải chỉ thay tên executable.

## Sửa Constitution đề nghị: 1.0.0 → 1.1.0

Đề nghị tăng **MINOR** vì bổ sung runtime/command được chấp nhận, giữ Docker là lựa chọn
hợp lệ và giữ toàn bộ nghĩa vụ kiểm chứng. Không bỏ Linux containers, one-command startup,
readiness, persistence, least privilege hoặc integration thật. Không thay các nguyên tắc
khác bằng ngoại lệ Podman. Ngày thông qua gốc giữ2026-11-06; ngày sửa đổi chỉ ghi ngày
thực sự áp dụng sau khi chủ dự án duyệt, không ghi bản nháp là đã ban hành.

### Nội dung thay thế nguyên tắc IX

> ### IX. Môi trường Linux containers khởi động bằng một lệnh
>
> - Môi trường PHẢI chạy bằng Linux containers trên Docker Engine/Desktop hoặc Podman.
>   README PHẢI công bố runtime, phiên bản engine/client và Compose provider đã nghiệm thu.
> - Khi engine đã hoạt động và điều kiện đầu vào đã chuẩn bị theo README, toàn bộ stack
>   PHẢI khởi động bằng đúng một lệnh của runtime đã chọn:
>
>   `docker compose up --build -d` hoặc `podman compose up --build -d`.
>
>   Đây là hai lựa chọn thay thế; KHÔNG ĐƯỢC yêu cầu chạy cả hai để khởi động một môi trường.
> - Môi trường PHẢI gồm Frontend, Backend, Airflow, PostgreSQL, MySQL và các service phụ trợ
>   cần thiết. PHẢI tự initialization, migrations, seed, cấu hình persistent volumes và
>   healthchecks theo dependency; nhận cấu hình qua environment variables/secret files.
> - Lần khởi động đầu tiên PHẢI tự hoàn tất phần nội bộ ứng dụng, KHÔNG ĐƯỢC yêu cầu chạy
>   migration, tạo schema hoặc cấu hình service thủ công sau lệnh startup. Cài runtime,
>   Compose provider và khởi động engine/machine là điều kiện đầu vào được công bố,
>   tương tự khởi động Docker daemon, không phải bước setup nghiệp vụ ngầm.
> - Init/migrations/seed PHẢI chạy lại an toàn, không xóa hoặc ghi đè dữ liệu người dùng;
>   sample namespace PHẢI tách dữ liệu thực. Dữ liệu, uploads, DAGs, logs, staging và key
>   cần lưu PHẢI bền qua restart; engine/provider không được làm thay đổi nghĩa vụ recovery.
> - Container running KHÔNG thay service readiness. Healthchecks PHẢI phản ánh khả năng
>   phục vụ; startup dependencies, init Exited(0), restart behavior và resource limits
>   PHẢI được kiểm bằng runtime/provider thật được công bố, không suy từ Compose config.
> - Quyền volume/UID/GID, secret mounts, network isolation và loopback exposure PHẢI được
>   giữ đúng thiết kế. KHÔNG ĐƯỢC dùng privileged, tắt healthcheck/constraint, chmod777,
>   bỏ memory/disk limits hoặc xóa volumes để né khác biệt runtime.
> - Nghiệm thu PHẢI ghi runtime/provider/phiên bản và kết quả thực. PASS trên một tổ hợp
>   KHÔNG chứng minh tổ hợp khác đã được kiểm. Chỉ cần nghiệm thu baseline được công bố
>   cho lần bàn giao; KHÔNG ĐƯỢC quảng bá runtime khác đã tương thích khi chưa có evidence.
>
> **Kiểm chứng:** fresh startup đúng một lệnh trên baseline đã công bố, init/readiness thật,
> workflow mẫu khi đủ chức năng, restart và xác minh persistence/secret/recovery. Không còn
> mandatory test chưa chạy trong phạm vi tuyên bố hoàn thành.

### Các chỗ còn lại trong Constitution phải đồng bộ sau duyệt

- Nguyên tắc XII: thay cụm ưu tiên “Docker environment và database” bằng “môi trường Linux
  containers và database”; giữ nguyên thứ tự core, gates và không trì hoãn security/validation.
- §Ràng buộc kiến trúc và phạm vi sản phẩm: đổi diễn đạt database cùng môi trường Docker
  thành cùng môi trường container; vẫn cấm nghiệp vụ truy cập bảng nội bộ Airflow.
- §Quy trình phát triển và các cổng chất lượng, mục4: kiểm startup trên baseline runtime/
  provider được công bố thay vì mặc định chỉ Docker; giữ nguyên các yêu cầu bằng chứng.
- Báo cáo tác động đồng bộ và version/date cuối file phản ánh đúng bản được chủ dự án duyệt.
  Không sửa nguyên tắc VI/VII/VIII/X để nới secret, integrity, memory hoặc Airflow authority.

## Bản sửa Plan đề nghị

| Vị trí | Nội dung đề nghị |
| --- | --- |
| §Bối cảnh kỹ thuật | Thêm baseline Podman client5.8.3/server5.8.9 trên WSL Linux/amd64; provider Docker Compose5.6.0. Ghi rõ mới phát hiện môi trường, chưa nghiệm thu stack. |
| §Kiểm tra Constitution | Tham chiếu1.1.0 chỉ sau khi được duyệt/ban hành; kết luận design khác evidence runtime. |
| §Thiết kế Docker Compose | Đổi tên thành §Thiết kế Compose và runtime container; giữ `docker-compose.yml`/Dockerfile và named volumes, không cần đổi tên thư mục `docker/`. |
| Provider | Công bố/pin đường dẫn hoặc biến `PODMAN_COMPOSE_PROVIDER` cho lệnh kiểm thử, không âm thầm đổi provider giữa các lượt. Không tự sửa cấu hình user/global trong lượt đề xuất. |
| Registry/images | Dùng tên image đầy đủ registry, ví dụ docker.io/library/postgres và docker.io/apache/airflow; giữ version/digest thật, không dùng latest hoặc đổi registry không kiểm chứng. |
| Init/readiness | Kiểm thực `service_healthy`/`service_completed_successfully`, one-shot failures chặn consumer và JSON/CLI healthchecks, không đổi thành sleep. |
| Volumes/secrets | Kiểm UID/GID/RO mounts trong Linux VM và durability; không chuyển dataset/staging sang Windows bind mount hoặc tmpfs để né quyền. |
| Networking | Browser localhost khác container service DNS; kiểm loopback3000/8000/8080, private-runtime guards và service auth, không mở unauthenticated engine API/TCP. |
| Resources | Inspect actual cgroup memory limits và filesystem quota behavior; không lấy machine metadata hoặc mem_limit trong YAML thay enforcement. Giữ baseline RAM/disk/RSS; chỉ giảm parallelism1 nếu cấu hình và kiểm chứng theo thiết kế hiện có. |
| §Chiến lược kiểm thử | Ghi rõ engine/provider/client/server; fresh/restart/failure tests dùng cùng baseline. Container health/deploy/data gates không giảm. |

Chưa có Compose file nên chưa thể chạy `podman compose config` cho dự án này. Không dùng
một Compose ví dụ nhỏ để tuyên bố stack Airflow/PostgreSQL/MySQL đã tương thích.

## Bản sửa Tasks đề nghị

Giữ8phase và các ID hiện tại nếu đủ, không reset T001/T003 hoặc đánh task khác hoàn thành
từ kết quả kiểm tra môi trường. Bổ sung preflight engine/provider trước tiếp tục T002.

| Task | Thay đổi và điều kiện kiểm chứng |
| --- | --- |
| T002 | Build/install dependency backend/runtime trong Linux/Python3.12 qua Podman; resolve lại markers và pip check thật, lưu hash constraints/lock. Client/server/provider đều được ghi; chưa PASS chỉ vì tải wheel thành công. |
| T004/T006 | Build Dockerfiles bằng Podman, kiểm import/runtime/wheel/airflow version/pip check; không cài dependency khi startup hoặc thay pin để build lọt. |
| T005 | Podman build frontend image; chạy nginx thật kiểm SPA/proxy và cả hai private prefixes404/no upstream; direct canonical bearer kiểm khi có T103, không dùng Vite thay nginx. |
| T007–T010 | Kiểm init/roles/secret files và UID/GID trên baseline rootful hiện tại; container vẫn chỉ nhận quyền cần thiết, không truyền admin key vào ETL runtime. |
| T011 | Cùng `docker-compose.yml`, profile test và topology; provider phải thực hiện đúng dependencies, named volumes, RO mounts, loopback ports và resource limits. |
| T012 | Kiểm HTTP/JSON/database/CLI probes trên container thật; dependency down không che bởi HTTP200, không restart cascade hoặc reset volume. |
| T013/T140 | Chấp nhận đúng `podman compose up --build -d` trên baseline Podman đã công bố; giữ fresh/restart/persistence/error cases. Ghi engine/provider vào evidence, không tính thành Docker-tested. |
| T014 | Pin image registry/digests thật, kiểm client/server/provider compatibility, actual resource enforcement và dependency/image scans; không bịa PASS. |
| T046/T138/T141–T152 | Đổi runner prefix theo baseline, giữ nguyên selectors/fixtures/project-volumes isolation và toàn bộ dữ liệu expected-actual/BR-08/A–AM. |

Sau duyệt, thứ tự tiếp tục Phase1: preflight Podman → T002 → T004/T006 và các nhánh đủ
prerequisite; T005 độc lập sau T003. Không vào Phase2 trước gate T014.

## Tài liệu liên quan cần đồng bộ sau duyệt

- [Spec](../../specs/001-airflow-automation-tool/spec.md): US-01, FR-081, SC-001, AS-02 và
  chỗ yêu cầu startup Docker tường minh phải chấp nhận lệnh Podman tương ứng; không đổi
  BR-08, phạm vi tám ETL routes hoặc tiêu chí toàn vẹn. Đây là đồng bộ runtime, không thêm TTL.
- [Plan](../../specs/001-airflow-automation-tool/plan.md),
  [Tasks](../../specs/001-airflow-automation-tool/tasks.md),
  [Research](../../specs/001-airflow-automation-tool/research.md),
  [Quickstart](../../specs/001-airflow-automation-tool/quickstart.md),
  [README](../../README.md): dùng cùng baseline/lệnh/provider và giới hạn đã kiểm.
- Runtime/Airflow contracts chỉ sửa chỗ phụ thuộc engine hoặc hướng dẫn vận hành, giữ
  metadata/secret/native-lock/ledger/recovery semantics. Không thay API/Excel schema vì đổi engine.
- Reviewer cần rà soát lại CHK003/CHK031–CHK034/CHK040/CHK042/CHK045/CHK048 trên tài liệu
  sau sửa; không tự giữ hoặc bật checkbox để mở gate. `requirements.md` thuộc Specify/Clarify.
- [Báo cáo Phase1](../testing/phase1-report.md) giữ kết quả lịch sử Docker chưa có; ghi thêm
  bằng chứng Podman mới ở lượt implementation, không đổi NOT_RUN lịch sử thành PASS.

## Quyết định áp dụng và giới hạn

Chủ dự án đã duyệt nội dung nguyên tắc IX mới, các thay thế liên quan và version1.1.0 ở
trên. Đã áp dụng Constitution → đồng bộ Spec/Plan/Tasks/docs và đối chiếu reviewer các mục
bị ảnh hưởng. Bước tiếp theo là tiếp tục implementation Phase1 theo dependency và gate.
Không cần cài Docker Desktop nếu
baseline Podman đạt đầy đủ gates. Hiện chỉ xác minh engine/provider phản hồi; compatibility
stack, resource enforcement, build, startup, persistence và recovery vẫn NOT_RUN.

## Kiểm chứng sau áp dụng bản duyệt

- Constitution1.1.0 giữ ngày thông qua2026-11-06, ngày sửa đổi2026-11-08 và đủ12nguyên tắc;
  không có placeholder chưa giải thích. Chỉ IX/XII đổi nội dung nguyên tắc theo bản duyệt;
  I–VIII/X/XI giữ nguyên so với bản quản trị trước sửa đổi.
- Spec BR-08 giữ nguyên nội dung. Tasks giữ152ID liên tiếp, T001/T003 là hai task đã đánh
  hoàn thành; dependency không thiếu ID/cycle, T152 vẫn có151task tổ tiên.
- Đã kiểm211liên kết local trong Constitution/README/proposal và bộ tài liệu feature,
  không broken links; `git diff --check` không lỗi.
- Reviewer giữ48marker hiện có, bổ sung đối chiếu thiết kế các mục bị ảnh hưởng;
  `requirements.md` không đổi. Không có extension hooks cấu hình.
- Lượt áp dụng chỉ sửa tài liệu/quản trị; không chạy build/container/stack hoặc đổi
  trạng thái nghiệm thu runtime. Các kết quả implementation lịch sử vẫn giữ nguyên.
