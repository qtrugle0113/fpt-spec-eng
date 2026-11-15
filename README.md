# Airflow Automation Tool

Airflow Automation Tool giúp khai báo và vận hành luồng chuyển dữ liệu bằng file Excel.
Người dùng có thể tạo bảng đích, cấu hình nguồn và cách ánh xạ dữ liệu, đưa DAG lên
Airflow, chạy theo lịch hoặc thủ công, rồi theo dõi kết quả trên giao diện.

Nguồn dữ liệu hỗ trợ **PostgreSQL, MySQL và file CSV/TXT**; đích là **PostgreSQL hoặc
MySQL**. Công cụ sinh SQL tạo bảng và DAG từ định nghĩa đã kiểm tra, giúp người dùng
không phải tự viết DAG Python cho từng luồng.

## Chức năng chính

| Màn hình | Công việc |
| --- | --- |
| Dashboard | Xem tổng quan DAG, các lần chạy và tỷ lệ thành công. |
| Connections | Quản lý và kiểm tra kết nối database. |
| Table Management | Tải mẫu Table Definition, kiểm tra cấu trúc và tạo bảng đích. |
| DAG Builder | Chuẩn bị file nguồn, kiểm tra ETL Definition, xem lại cấu hình và triển khai DAG. |
| DAG Monitoring | Theo dõi DAG, từng lần chạy, số dòng xử lý và log. |
| Settings | Thiết lập giá trị mặc định cho workspace. |

**Table Definition** là file Excel mô tả bảng và các cột. **ETL Definition** là file
Excel mô tả nguồn, đích, ánh xạ cột, lịch chạy và chính sách ghi dữ liệu. **Template**
là file mẫu tải từ ứng dụng để điền hai loại định nghĩa này.

Giao diện có nút **Download User Guide** ở thanh trên cùng. Hướng dẫn viết bằng
tiếng Việt, có ảnh thao tác, đọc được offline và có thể in hoặc lưu PDF. Bạn cũng
có thể tải [bản HTML trong repository](outputs/user-guide/Airflow-Automation-Tool-Huong-dan-su-dung.html).

## Thành phần hệ thống

| Thành phần | Công nghệ và vai trò |
| --- | --- |
| Frontend | React, TypeScript, Vite; Nginx phục vụ giao diện và chuyển tiếp yêu cầu API. |
| Backend API | Python 3.12, FastAPI; quản lý kết nối, file định nghĩa, kiểm tra dữ liệu và trạng thái xử lý. |
| Backend worker | Xử lý công việc nền như tạo bảng và triển khai DAG. |
| Apache Airflow | Điều phối và thực thi ETL; gồm API server, scheduler và DAG processor. |
| PostgreSQL | Lưu metadata ứng dụng và metadata Airflow trong các database riêng; có database phục vụ ETL mẫu. |
| MySQL | Database phục vụ ETL mẫu và kiểm thử kết nối/luồng dữ liệu. |
| Volumes | Lưu database, file upload, DAG, log, staging và secrets qua các lần khởi động lại. |

Frontend gọi Backend API; backend-worker triển khai DAG qua Airflow API. Airflow
thực thi ETL giữa nguồn và đích, dùng staging trên đĩa. Chi tiết tại
[tài liệu kiến trúc](docs/architecture.md).

## Chuẩn bị môi trường

- Git để lấy mã nguồn.
- Podman với Linux containers trên kiến trúc `amd64`. Baseline đã kiểm chứng dùng
  Podman trên WSL và Compose provider **5.6.0**.
- Compose provider đã cài và được Podman nhận diện. Nếu máy dùng nhiều provider,
  chọn bằng biến môi trường `PODMAN_COMPOSE_PROVIDER` trỏ tới executable cần dùng.
- Có kết nối mạng để tải base images và dependencies trong lần build đầu tiên;
  đủ RAM và dung lượng đĩa cho database, Airflow và staging.

Khi build toàn bộ bằng container, không cần cài Python hoặc Node.js trên host.
Dockerfile và các file lock đã khai báo phiên bản dependencies.

Trên Windows, kiểm tra Podman machine trước khi chạy:

```powershell
podman machine list
```

Nếu chưa có machine, chạy `podman machine init` một lần; nếu machine đang dừng,
chạy `podman machine start`. Sau đó kiểm tra engine và Compose provider:

```powershell
podman info
podman compose version
```

Hướng dẫn môi trường và artifact local chi tiết nằm tại
[local-portable.md](docs/operations/local-portable.md). Các lệnh bên dưới dùng
Podman, là runtime đã được kiểm chứng của dự án.

## Build và khởi động

### 1. Lấy mã nguồn

```powershell
git clone https://github.com/qtrugle0113/fpt-spec-eng.git
cd fpt-spec-eng
git switch main
```

Nếu đã có repository, vào thư mục dự án và cập nhật `main` bằng
`git pull --ff-only` sau khi đã lưu các thay đổi local.

### 2. Cấu hình local

Compose có sẵn giá trị mặc định nên không bắt buộc tạo `.env`. Nếu muốn đổi tên
project hoặc cổng, tạo `.env` từ mẫu khi chưa có file này:

```powershell
Copy-Item .env.example .env
```

| Biến | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `COMPOSE_PROJECT_NAME` | `aat` | Namespace của stack và volumes. Giữ nguyên khi khởi động lại cùng dữ liệu. |
| `AAT_FRONTEND_PORT` | `3000` | Cổng giao diện web trên host. |
| `AAT_BACKEND_PORT` | `8000` | Cổng Backend API trên host. |
| `AAT_AIRFLOW_PORT` | `8080` | Cổng Airflow trên host. |
| `AAT_LOCAL_DEMO_AUTH` | `1` | Tạo tài khoản Airflow `admin/admin` khi khởi tạo local/demo mới. |

Secrets của database và tài khoản tích hợp được bootstrap vào volumes, không cần
điền mật khẩu database vào `.env`. Chỉ dùng `admin/admin` cho local/demo trên máy cá nhân.

### 3. Build và chạy toàn bộ stack

Chạy từ thư mục chứa `docker-compose.yml`:

```powershell
podman compose up --build -d
```

Lệnh này build images, chạy các bước khởi tạo secrets/database/migrations và đưa
các service lên theo thứ tự phụ thuộc. Lần đầu có thể mất thời gian để tải và build.

Nếu muốn tách bước build để xem lỗi dễ hơn:

```powershell
podman compose build
podman compose up -d
```

Các service `secrets-init`, `db-init`, `app-init`, `airflow-init` là bước khởi tạo;
chạy xong và thoát với mã `0` là bình thường.

### 4. Kiểm tra trước khi sử dụng

```powershell
podman compose ps -a
Invoke-RestMethod http://localhost:8000/api/v1/health/ready
```

Chờ các service chạy lâu dài báo healthy và readiness trả HTTP `200`. Container
đang chạy chưa có nghĩa toàn bộ hệ thống sẵn sàng. Nếu đã đổi cổng backend,
thay `8000` trong lệnh bằng cổng tương ứng.

## Truy cập các service

### Qua trình duyệt hoặc HTTP

Các địa chỉ sau áp dụng cho cấu hình Compose mặc định. Cột demo dành cho stack
local đã được chuẩn bị riêng trên máy phát triển, không phải cổng mặc định khi clone mới.

| Service | Stack mặc định | Demo đã cấu hình | Đăng nhập / ghi chú |
| --- | --- | --- | --- |
| Giao diện ứng dụng | <http://localhost:3000> | <http://localhost:23000> | Không có bước đăng nhập riêng trong bản local. |
| Airflow | <http://localhost:8080> | <http://localhost:28080> | Username **admin**, password **admin** cho local/demo. |
| Backend API | <http://localhost:8000/api/v1> | <http://localhost:28000/api/v1> | Đây là tiền tố endpoint, không phải trang chủ API. Xem [tài liệu API](docs/api.md). |
| Liveness | <http://localhost:8000/api/v1/health/live> | <http://localhost:28000/api/v1/health/live> | Kiểm tra tiến trình backend còn hoạt động. |
| Readiness | <http://localhost:8000/api/v1/health/ready> | <http://localhost:28000/api/v1/health/ready> | Kiểm tra hệ thống sẵn sàng phục vụ; phụ thuộc chưa sẵn sàng có thể trả `503`. |

Backend hiện tắt trang Swagger `/docs` và ReDoc; dùng [docs/api.md](docs/api.md)
để tra cứu API. Nếu `.env` đổi cổng, dùng cổng đã cấu hình thay cho các địa chỉ trên.

Fresh local tạo `admin/admin` khi `AAT_LOCAL_DEMO_AUTH=1`. Khởi tạo lại không reset
mật khẩu đã tùy chỉnh. Với volumes cũ, xem [cách cập nhật/khôi phục tài khoản](docs/operations/local-airflow-admin.md).
Tài khoản này dùng để vào Airflow, khác tài khoản database trong Connections.

Frontend container có thể vẫn dùng image cũ sau khi source thay đổi; cần build
và cập nhật đúng stack để thấy UI mới. Demo có manifest riêng tại
`.tools/local-demo.json`; cách khởi động lại đúng project/config được mô tả trong
[hướng dẫn local](docs/operations/local-portable.md#khởi-động-artifact-đã-được-kiểm-tra).

### Service nội bộ

| Service | Địa chỉ trong mạng container | Cách sử dụng |
| --- | --- | --- |
| PostgreSQL | `postgres:5432` | Khai báo host này trong Connections khi dùng database của stack. |
| MySQL | `mysql:3306` | Khai báo host này trong Connections khi dùng database của stack. |
| Backend worker | Không có web UI | Theo dõi bằng `podman compose logs -f backend-worker`. |
| Airflow scheduler | Không có web UI riêng | Theo dõi trong Airflow hoặc bằng `podman compose logs -f airflow-scheduler`. |
| Airflow DAG processor | Không có web UI riêng | Xem log bằng `podman compose logs -f airflow-dag-processor`. |

PostgreSQL và MySQL không publish cổng ra host trong Compose mặc định. Khi khai
báo Connections, dùng thông tin database do người quản trị cung cấp; không mặc
định dùng `localhost` hoặc `admin/admin` làm thông tin kết nối database.

## Luồng sử dụng cơ bản

1. Vào **Connections**, thêm hoặc chọn kết nối nguồn/đích và bấm **Test connection**.
2. Nếu chưa có bảng đích, vào **Table Management**, tải mẫu Table Definition,
   điền Excel, kiểm tra và xem SQL trước khi xác nhận tạo bảng.
3. Nếu nguồn là CSV/TXT, vào **File Sources** trong DAG Builder để upload,
   xem trước và kiểm tra toàn bộ file; lấy Reference để điền vào ETL Definition.
4. Điền ETL Definition, upload và validate trong **DAG Builder**; xem lại nguồn,
   đích, mapping, lịch chạy và chính sách ghi trước khi xác nhận triển khai.
5. DAG mới được tạo ở trạng thái Paused. Xác nhận mở chạy thủ công hoặc bật lịch
   theo nhu cầu, rồi theo dõi từng lần chạy trong **DAG Monitoring** và Airflow.

Tải **User Guide** trên UI để xem đầy đủ từng bước và ảnh minh họa. `APPEND` có
thể thêm trùng dữ liệu khi chạy lại; `UPSERT` cần khóa khớp phù hợp; `FULL_REFRESH`
cần xác nhận riêng cho phạm vi thay thế dữ liệu.

## Vận hành cơ bản

Chạy các lệnh tại cùng thư mục, dùng cùng project và cấu hình đã khởi tạo:

```powershell
# Xem trạng thái và log
podman compose ps -a
podman compose logs -f backend backend-worker airflow-scheduler

# Dừng rồi chạy lại, giữ nguyên volumes
podman compose stop
podman compose up -d

# Build và cập nhật sau khi đổi source
podman compose up --build -d
```

Giữ nguyên volumes chứa database, secrets, keyring, uploads và staging. Không dùng
`down --volumes` hoặc prune volumes để xử lý lỗi khởi động. Các bước khôi phục và
đối soát dữ liệu được mô tả trong [troubleshooting](docs/operations/troubleshooting.md).

## Cấu trúc repository và tài liệu

| Thư mục | Nội dung |
| --- | --- |
| `frontend/` | Giao diện và bản User Guide đóng gói cùng frontend. |
| `backend/` | API, migrations và backend-worker. |
| `airflow/`, `etl_engine/` | Cấu hình Airflow, DAG template và engine chuyển dữ liệu. |
| `packages/` | Các package dùng chung. |
| `docker/`, `scripts/` | Bootstrap, container và công cụ vận hành. |
| `templates/`, `samples/` | Mẫu Excel Definition và dữ liệu mẫu. |
| `tests/` | Unit, integration, E2E và công cụ kiểm chứng. |
| `specs/` | Đặc tả, kế hoạch và tasks theo Spec Kit. |
| `docs/` | Kiến trúc, vận hành và báo cáo kiểm thử. |

Tài liệu thường dùng:

- [Hướng dẫn người dùng có ảnh](outputs/user-guide/Airflow-Automation-Tool-Huong-dan-su-dung.html)
- [Schema Excel Definition](docs/excel-definitions.md)
- [Quản lý kết nối](docs/operations/connections.md) và [file nguồn](docs/operations/file-sources.md)
- [Triển khai/chạy DAG](docs/operations/dag-deployment.md) và [ETL engine](docs/operations/etl-engine.md)
- [Kết quả kiểm chứng các tính năng mới](docs/testing/feature-release-20261115.md)

## Phạm vi sử dụng

Cấu hình bàn giao dành cho một operator local, cổng chỉ bind loopback và dữ liệu
demo/tổng hợp. Baseline có [quyết định chấp nhận rủi ro đã biết](docs/decisions/t014-owner-review-20261114.json),
review ngày **2026-11-16**, hết hạn **2026-11-23T00:00:00+09:00**. Image/artifact
mới cần được kiểm tra riêng; kết quả trên Podman không tự chứng minh đã nghiệm
thu Docker hoặc sẵn sàng production. Hồ sơ chi tiết tại
[đề xuất bàn giao baseline](docs/proposals/t014-full-handover-known-risks-20261114.md).
