# Chạy local trên nhiều máy

Mỗi máy build từ source, locks và Compose; không cần image IDs hoặc volumes của
máy khác. Quyền local và ngoại lệ vẫn có hạn, scan từng artifact mới và lưu
provenance. Quy trình này không phải nghiệm thu bảo mật đầy đủ.

## Bản đang chạy trên máy công ty

**Cập nhật2026-11-12:** bản đang READY trên máy hiện tại là
`aat-portable-demo-a7f852ae`, cùng các cổng23000/28000/28080. Manifest local trỏ
`portable-81a0866e`, policy LOCAL_POLICY_MATCH. T1439/9 và workflow UI6checks
PASS trên installed images; xem [checkpoint](../testing/product-resume-20261112.md).
Các thông tin project cũ ngày11/11 dưới đây là lịch sử; lấy config/project thực
từ `.tools/local-demo.json`, không hardcode namespace của máy khác.

Ứng dụng: <http://localhost:23000>, Airflow: <http://localhost:28080>, readiness:
<http://localhost:28000/api/v1/health/ready>. Project mới
`aat-portable-demo-dcae6f3c`, installed wheels, không source overlay, không dùng
volumes demo13000. Startup đã kiểm tất cả service healthy và init exit0; browser
thật đã mở6trang trên1440/390px,12checks PASS, không horizontal overflow.
Điều này không thay kiểm thử ETL trọn luồng; regression đang chạy riêng.

Để thao tác: bắt đầu ở Connections với các connection mẫu được seed tự động;
test nguồn/đích, tải workbook từ Table Management/DAG Builder và làm theo
[luồng workbook](dag-deployment.md#luồng-thao-tác). Giữ xác nhận load policy và
quyền FULL_REFRESH riêng. Các địa chỉ13000 trong tài liệu cũ là demo máy trước.

## Chuẩn bị artifact khi đổi máy hoặc sửa source

Điều kiện đầu vào: Podman Linux/amd64 đã chạy và Compose provider5.6.0 theo
baseline. Regression driver phát triển dùng Python host; dependencies ứng dụng,
pytest, browser và DB vẫn chạy trong containers. Không cần Node host.

```powershell
python -X utf8 tests/tools/run_regression.py --prepare-images --group unit-api
```

Manifest và config mỗi máy ở `.tools`, được Git ignore. Source revision/hash,
locks, engine/provider, build commands, scan và IDs được ghi trong evidence.
Nếu đã có candidate khớp source, dùng `prepare_local_images.py --reuse-candidate
<manifest>` rồi scan manifest mới; không rebuild các inputs không đổi.
Unknown findings vẫn cần remediation hoặc quyết định đúng phạm vi; không tự
miễn vì mục tiêu có bản chạy nhanh.

## Khởi động artifact đã được kiểm tra

Một lệnh PowerShell, không cần Python/Node trên host ở bước khởi động:

```powershell
.\scripts\start-local.ps1
```

Lệnh xác minh receipt/hash/expiry/images, tạo namespace mới, chỉ bind loopback
23000/28000/28080, tự chạy init/migrations/seed và chờ readiness. Nếu cổng đã dùng
hoặc có `.tools/local-demo.json`, lệnh không tạo đè demo mới. Đây là khởi động
artifact đã chuẩn bị; fresh build từ checkout vẫn theo lệnh canonical
`podman compose up --build -d` trong README, cần kiểm riêng tại T140.

Khởi động lại bản hiện tại, giữ nguyên volumes:

```powershell
$env:PODMAN_COMPOSE_PROVIDER=(Resolve-Path .tools/docker-compose-5.6.0.exe).Path
$demo=Get-Content -Raw .tools/local-demo.json | ConvertFrom-Json
podman compose -f $demo.compose_config -p $demo.project up -d --no-build
```

Dừng bằng cùng config/project với `down`, không thêm `--volumes`. Không dùng
prune hoặc xóa key để xử lý lỗi. Password Airflow được giữ trong secret volume;
không in vào log, workbook hoặc tài liệu.

## Luồng đã kiểm chứng và giới hạn hiện tại

T141 đã chạy UI→Connections→download Excel→tạo bảng→upload CSV→validate→deploy
→mở Airflow→enable manual→trigger→Monitoring/Dashboard trên desktop/mobile,
đối chiếu dữ liệu đích thật. Evidence tại
`docs/testing/resume-20261111/t141-explicit-conversions/acceptance.json`.

Khi mapping CSV/TXT sang cột Integer/Decimal/Timestamp, khai báo `Type Conversion`
trong sheet `Column_Mappings`; `Direct Mapping` dùng cho kiểu tương thích, không
tự đổi text thành số/ngày. `Column Mapping Reference` phải trỏ đúng DAG ID.
Tải template từ UI để giữ đúng version và English instructions hiện hành.

T138/T141/T142 đã PASS trong phạm vi local. T143 vẫn mở do lỗi phát hiện khi
chạy cả chuỗi TXT và missing-file; xem checkpoint trước khi coi một nhóm test
đã hoàn tất. T014_FULL/security chưa được nghiệm thu đầy đủ dù sản phẩm chạy.
