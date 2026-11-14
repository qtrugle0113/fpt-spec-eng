# Rà soát SpecKit trước nghiệm thu ngày 13/11/2026

## Phạm vi và cách thực hiện

Áp dụng hướng dẫn `speckit-analyze` tại
`../../../../.github/skills/speckit-analyze/SKILL.md`, sau đó chuyển sang
`speckit-implement` theo yêu cầu tiếp tục triển khai đã được chủ dự án giao.
Không sinh lại Spec/Plan/Tasks hoặc thay các marker checklist của reviewer.
Không có `.specify/extensions.yml`, nên không có extension hook cần thực thi.

Prerequisites đã chạy thành công bằng PowerShell với execution policy chỉ áp dụng
cho process con, đặt `SPECIFY_FEATURE_DIRECTORY` trỏ đến feature hiện hữu. Lần đầu
thất bại do execution policy của host; lần tiếp theo phát hiện thiếu feature context.
Đã dùng override được chính script hỗ trợ, không tạo feature mới.

Đã đối chiếu Constitution 1.3.0, các phần kiến trúc/phase/gate của Plan, yêu cầu
FR/NFR/SC và ma trận A–AM của Spec, mô hình dữ liệu, contracts runtime/Airflow,
Tasks, Quickstart và checkpoint hiện hành. Các snapshot lịch sử trong Plan/Tasks
không thay thế phần trạng thái mới nhất hoặc artifact của máy hiện tại.

## Kết quả cấu trúc và truy vết

| Chỉ số | Kết quả |
| --- | --- |
| Task | 152, T001–T152, không thiếu hoặc trùng ID |
| Checkbox đã đánh dấu | 148 |
| Task còn mở | T014, T140, T151, T152 |
| FR/NFR/SC trong Spec | 100/10/15 |
| Yêu cầu có tham chiếu trực tiếp hoặc trong dải mã của Tasks | 125/125 |
| Dependency không tồn tại/vòng lặp | 0/0 |
| Checklist requirements/spec-quality | 16/16 và 48/48 |

Coverage trên là coverage **tham chiếu tài liệu**, không chứng minh mọi hành vi
đã được kiểm thử hoặc mọi task đã nghiệm thu. Chi tiết từng task, dependency và
hash checklist tại [task-audit.json](task-audit.json).

Không phát hiện mâu thuẫn Critical/High mới trong phần tài liệu được đối chiếu.
Các acceptance blocker hiện hữu vẫn được giữ đúng: T014_FULL chưa PASS; T140
chưa đủ evidence restart theo phase; T151 chờ T140; T152 chờ dependencies và
full security gate. Không dùng kết luận phân tích cấu trúc để đóng các blocker này.

## T040 và các bước tiếp theo

T040 đã `[x]` tại Tasks. Implementation ở
`backend/src/aat_api/schemas/connections.py`, kiểm chứng ở
`tests/unit/test_connection_schemas.py`, `tests/api/test_connections.py` và
`tests/integration/test_connections.py`; báo cáo lịch sử tại
[phase3-connections-report.md](../../phase3-connections-report.md).
Duplicate code trim/case-insensitive thuộc kiểm chứng API/DB; DNS rebind thuộc
kiểm chứng adapter/policy, không suy từ schema unit tests đơn lẻ.

Tiếp tục bằng `speckit-implement`: build/scan artifacts hiện tại, kiểm điều kiện
local policy trước runtime, sửa lỗi fixture T140 đã được test hồi quy phát hiện,
chạy các selector còn thiếu khi được gate cho phép, rồi đối chiếu lại Analyze
và báo cáo acceptance. Chỉ thay checkbox khi tiêu chí của task thực sự đạt.
