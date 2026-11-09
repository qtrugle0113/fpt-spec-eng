# Kết quả tiếp tục triển khai — 2026-11-09

**Cập nhật sau phản hồi owner:** hai ID backend-tests/PostgreSQL đã được xác nhận theo
hồ sơ, giữ controls/hạn. T028–T031/T033 đã đóng thêm: kiểm owner non-superuser 1PASS,
hai initializer cạnh tranh/grants thật, cùng các kiểm chứng bên dưới. T015 9PASS và
T018 7PASS. Airflow build/scan hoàn tất nhưng cần mapping riêng cho ID mới trước khi
khởi chạy fixture: [hồ sơ bổ sung](../phase2-resume-airflow-review.md). T034 còn mở.
Các đoạn “chờ hai ID” bên dưới là snapshot của lượt trước phản hồi owner.

## Phạm vi và kết quả

Theo yêu cầu mới trong hội thoại, phạm vi mở đến T152 khi dependency và gate đạt;
không mở rộng ngoại lệ security. Runtime mới CLI6.1.1/server6.1.4/Compose5.6.0,
WSL2/rootful/cgroupv2. Không dùng ID giả hoặc gán lại ID baseline cho image mới.

Đã build backend-tests và PostgreSQL từ Dockerfile/pin hiện có. Driver kiểm thử
nhận image/network/health URL rõ ràng, ghi ID thực qua inspect, hỗ trợ thư mục
bằng chứng riêng để không ghi đè lịch sử. Selector `--foundation-core` chỉ kiểm
DB/API, không bao gồm readiness Airflow và không thay gate T034.

Đã sửa test migration parity phụ thuộc thứ tự chạy: mỗi test tự chạy initializer
thật trước khi inspect. Bổ sung so column type/nullable/PK/unique/check/FK/index/trigger
với ORM, kiểm seed giữ cấu hình operator/identity mẫu, kiểm thiếu khóa gốc khiến
init fail mà không regenerate hoặc sửa metadata. Không sửa logic nghiệp vụ ứng dụng.

| Bộ kiểm tra | PASS |
| --- | ---: |
| T022 và regression definitions | 23 |
| Model T023–T026 | 16 |
| Settings T027 | 2 |
| Repository/migration/seed/key loss | 5 |
| API boundary và bootstrap key | 6 |
| Operation/confirmation/lease | 3 |
| T017 authorization/repository | 28 |
| Tổng hợp foundation DB/API | 47 |
| Unit trong test image | 37 |

Các suite có phần chồng nhau, không cộng thành tổng số test độc lập. Đã cập nhật
T022–T027 và T032 hoàn thành theo phạm vi riêng của task. Các task foundation còn lại
giữ chưa đóng cho tới khi đủ gate; chưa triển khai Connections/phase nghiệp vụ sau.
Containers và internal networks fixture đã cleanup; cache scan được giữ để tái kiểm.

## Gate còn chờ

Hai candidate có 42 và 53 HIGH/CRITICAL; tuple findings giống baseline, 0 thêm/0 bớt.
Không có security PASS. Quy tắc hiện hữu yêu cầu owner ký delta image trước mốc tiếp
theo, trong khi quyền mới không miễn trừ findings. Đã gửi yêu cầu xác nhận mapping
đúng hai ID, giữ controls/hạn hiện hữu, tại
[hồ sơ review](../phase2-resume-security-review.md).

Chưa chạy Airflow/readiness trên machine mới. Sau review, cần khôi phục image và
fixture Airflow thật, build/scan/review các ID phát sinh tương ứng, chạy T015/T018,
readiness và aggregate foundation đầy đủ; kiểm owner-role/packaging/profile trước
đóng T028–T034. Không dùng lượt core PASS để mở Phase3 hoặc nghiệm thu MVP.

## Lệnh tiếp tục kiểm DB/API

```powershell
python -X utf8 tests/tools/run_metadata_foundation.py --foundation-core --postgres-image localhost/aat-postgres-resume-candidate:17.11 --runner-image localhost/aat-backend-tests-resume-candidate:0.1.0 --evidence-dir docs/testing/resume-20261109
```

[Kết quả và source hashes](results.json); logs và fixture results cùng thư mục.
Không commit/push, không mở cổng public, không migration lên database/volume hiện hữu.
Không có `.specify/extensions.yml`; không có before/after hook cần dispatch.
