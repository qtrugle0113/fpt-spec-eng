# Chạy regression trong fixture riêng

Stack sản phẩm khởi động bằng một lệnh theo README, không cần Python/Node trên
host. Các driver phát triển bên dưới dùng Python3.12 chuẩn trên host để điều
khiển Podman; dependencies ứng dụng, pytest, browser và dữ liệu kiểm thử đều chạy
trong Linux containers. Không mount engine socket vào container.

Đặt Podman6.1.1 vào PATH và dùng Compose provider5.6.0 đã công bố. Trên workspace
hiện tại có thể dùng `.tools/podman-6.1.1/podman-6.1.1/usr/bin` và
`.tools/docker-compose-5.6.0.exe`. Không tự cài hoặc đổi dependency baseline khi
thiếu công cụ; kiểm điều kiện đầu vào và artifact thực tế trước.

## Các nhóm kiểm tra

Manifest `tests/fixtures/regression-images.json` là evidence lịch sử trên máy cũ.
Mặc định driver dùng `.tools/local-images.json` sinh trên máy hiện tại, không yêu
cầu mang image IDs giữa các máy. Chuẩn bị một lần sau checkout/source change:

```powershell
python -X utf8 tests/tools/run_regression.py --prepare-images --group unit-api
```

Lệnh build từ source/locks/Compose bằng tags riêng, ghi snapshot và scan từng
artifact rồi đối chiếu policy. Unknown findings giữ BLOCKED. Khi có candidate
cũ cùng source có thể dùng `prepare_local_images.py --reuse-candidate <manifest>`
để tránh rebuild phần không đổi, sau đó `scan_portable_images.py --manifest
<manifest-mới>`. Không cần baseline image của máy trước. `.tools` là cấu hình
local được ignore, không chứa approval dùng chung hoặc secret được commit.

Driver kiểm receipt scan/policy, expiry và IDs của artifact local, tạo project
mới và lưu commands/results theo selector:

```powershell
$env:PYTHONIOENCODING='utf-8'
python tests/tools/run_regression.py --group unit-api
python tests/tools/run_regression.py --group integration
python tests/tools/run_regression.py --group etl
python tests/tools/run_regression.py --group airflow
python tests/tools/run_regression.py --group e2e
python tests/tools/run_regression.py --group stress
```

`--group all` chạy tuần tự các nhóm, dừng tại failure và giữ evidence. Mỗi group
có thư mục riêng; có thể chỉ định `--evidence-dir` để tiếp nhận dễ hơn. Không dùng
nhãn PASS của một selector để thay cho selector chưa chạy.

Nhóm unit/API, integration và ETL dùng Compose test profile với PostgreSQL/MySQL,
credentials và network `regression_internal` riêng. Runner không nhận các secret
domains hoặc network của stack ứng dụng. Init test database tự tạo roles,
migrations và seed synthetic; environment `AAT_FOUNDATION_DISPOSABLE=1` bắt buộc.
Nhóm integration mặc định gồm foundation/repository/operation/API và adapters/
table/file thật; startup/owner migration và Airflow có lifecycle riêng, không
trộn vào một database đã được migrate rồi suy là fresh-init PASS.

Generated-DAG unit tests cần pendulum/Airflow SDK thật. Coordinator gán riêng
`test_dag_factory.py` cho image Airflow đã duyệt và chỉ PASS nhóm unit/API khi
cả hai runner đều PASS; không cài Airflow vào backend runtime, không mock SDK
để thay bằng chứng parse. Source factory được kiểm trên installed SDK; nghiệm
thu workflow vẫn dùng image ứng dụng đóng gói và Airflow thật.

Nhóm Airflow mặc định chạy tám route qua Task SDK installed wheels và public API.
Có thể chọn module riêng, mỗi module nhận fixture Airflow mới:

```powershell
python tests/tools/run_regression.py --group airflow --airflow-module tests.airflow.test_dashboard_truth
python tests/tools/run_regression.py --group e2e --e2e-suite phase7
```

E2E chạy image đóng gói, không source overlay mặc định. Desktop1440px/mobile390px
dùng cùng Playwright client/browser1.65.0. Nhóm stress dùng database named volumes
mới và staging trên đĩa; supervisor giới hạn child512MiB, runner1GiB để chứa cả
supervisor và child. Kết quả engine stress không thay nghiệm thu Airflow stress.

## Lệnh Compose trực tiếp

Khi đã build/review test image đúng source, có thể dùng profile trực tiếp:

```powershell
podman compose --profile test run --rm backend-tests pytest -p no:cacheprovider tests/unit tests/api --ignore tests/unit/test_dag_factory.py -v
podman compose --profile test run --rm backend-tests pytest -p no:cacheprovider tests/etl -v
```

Lệnh này chỉ phụ thuộc database regression, không khởi động frontend/production
database. Khi làm việc cạnh demo có trước, ưu tiên driver để có project namespace
mới thay vì dùng Compose project mặc định. Không trỏ test DSN vào database của
demo hoặc dữ liệu người dùng.

Lệnh Compose unit/API trực tiếp ở trên chưa gồm SDK cases; dùng driver
`--group unit-api` để chạy và tổng hợp đầy đủ cả SDK cases, không xem selector
đã loại SDK là nghiệm thu toàn nhóm.

## Evidence và cleanup

Mỗi lượt lưu exact IDs, nguồn/config, command, stdout đã redacted, exit code và
cleanup code. Driver chỉ xóa tài nguyên thuộc project vừa tạo; không dùng prune,
không xóa volumes có trước. Source-only và installed-image acceptance có nhãn
khác nhau. Image ID mới cần scan/review theo controls local hiện hành; quyền
local không phải security PASS hoặc nghiệm thu toàn MVP.

Runner/test source mới cần được đưa vào image mới trước nghiệm thu package;
không sửa manifest thành mutable tag hoặc mượn PASS từ source khác. T014_FULL vẫn
BLOCKED; report tổng phải giữ đầy đủ FAIL/NOT_RUN/BLOCKED và failure artifacts.
