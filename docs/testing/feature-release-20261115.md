# Tách nhánh và kiểm chứng trước merge — 2026-11-15

Chủ dự án yêu cầu mỗi chức năng một feature branch, push riêng và merge tất cả vào main. Các nhánh kế tiếp dựa trên nhánh trước để giữ phụ thuộc; mỗi nhánh có một commit riêng cho chức năng tương ứng. Baseline remote main trước thay đổi: `40732e955056a7d9afa5ae664a82dcd10e98730a`.

| Nhánh | Nội dung commit riêng |
| --- | --- |
| `feature/ui-refresh` | Giao diện trắng/teal, bố cục gọn, trạng thái và button download/Airflow |
| `feature/definition-terminology` | Tên ETL Definition/Table Definition trong UI, backend, Excel và test |
| `feature/airflow-admin-login` | admin/admin local, bootstrap và cập nhật/khôi phục có kiểm soát |
| `feature/vietnamese-user-guide` | HTML hướng dẫn tiếng Việt có ảnh và builder |
| `feature/user-guide-download` | Nút tải guide, static packaging và kiểm thử |

Đã đối chiếu toàn bộ staged tree sau khi ghép năm tính năng với snapshot local trước tách: không có khác biệt. Báo cáo này được bổ sung sau bước đối chiếu. Snapshot backup chỉ giữ local, không thuộc các nhánh cần push.

## Kiểm chứng lại khi tách commit

- Build/typecheck tại UI riêng, Definition và tổng hợp cuối: PASS.
- Shell tại UI riêng và tổng hợp: PASS, 18 tổ hợp route/viewport.
- UI tổng hợp với API thật, chỉ đọc: PASS 25/25.
- Unit Definition/admin trên container dependency image, không network/volume demo: PASS 29/29.
- Unit/contract tương ứng CI: PASS 28/28 (`test_sample_artifacts`, `test_image_baseline`, `test_airflow_constraints`, `test_airflow_offline_patch`, source pin/lock, `test_full_handover_policy`, `test_t152_evidence`).
- `tests.tools.full_handover_policy`: giữ kết luận OWNER_ACCEPTED_KNOWN_RISKS trong đúng baseline đã duyệt; không coi tính năng mới là image đã nghiệm thu.
- `tests.tools.t152_evidence --require-tracked`: PASS, 39 ca, 15 success criteria, 53 file bằng chứng tracked.
- Download guide: PASS 13 lượt từ production preview; filename/hash/giữ trang/bàn phím, backend unavailable và mở offline 16 mục/12 ảnh đều đạt.

Lượt chạy trực tiếp unit thuật ngữ trên Python host không thực hiện được vì thiếu openpyxl; đã thay bằng runner container đầy đủ dependency và 29/29 đạt. Không cài thêm dependency vào host để chạy kiểm tra này.

Git chuẩn hóa HTML về LF khi đưa vào repository. Bản guide canonical sau chuẩn hóa là 645820 bytes, SHA256 `4e1a49bad2ff3590e7d6ae875e1cf379c23658572e4717cdc861a3b7a809f67c`; source/public/dist/HTTP/download đều khớp. Hash 645922 bytes trong báo cáo chụp trước đó là bản Windows trước chuẩn hóa; nội dung/ảnh không thay đổi.

Các báo cáo/ảnh lịch sử giữ nguyên nội dung đã chụp. Log first-attempt cũ được giữ nguyên kể cả whitespace terminal, không được dùng làm bằng chứng PASS. Không build/scan/rollout image mới hoặc thay dữ liệu demo trong bước tách nhánh và merge.
