# Sử dụng Excel Definition

Tải template từ Table Management hoặc DAG Builder của bản đang chạy để có
đúng version. Hợp đồng đầy đủ tại
[Excel Definition1.0](../specs/001-airflow-automation-tool/contracts/excel-definitions.md).
Tên sheet/header và hướng dẫn trong workbook dùng tiếng Anh; không đổi tên cột.

## Tạo bảng

Table workbook có Instructions, Tables và Columns. Khai báo connection code
đã tồn tại, schema/table và các columns. Một lần xác nhận chọn một target
connection. Primary key không nullable; Decimal cần precision/scale, Varchar
cần length. Không điền SQL expression tùy ý vào Default Value.

Upload → chọn target → validate → review SQL/phạm vi → xác nhận tạo bảng.
Ứng dụng không tự DROP/ALTER bảng có trước. Nếu báo lỗi, dùng sheet/dòng/cột
trong kết quả validation để sửa; không bỏ qua lỗi bằng cách đổi target tùy tiện.

## Tạo ETL và DAG

ETL workbook có Instructions, ETL_Definitions và Column_Mappings. Mỗi dòng ETL
định nghĩa một DAG với một nguồn và một đích. Nguồn DB dùng connection/schema/table;
nguồn CSV/TXT dùng file ID và parser revision đã validate, không điền đường dẫn
host hoặc connection DB thay file ID.

`Column Mapping Reference` phải trỏ đúng DAG ID. CSV/TXT đọc cell dạng text:
chuyển sang Integer/Decimal/Timestamp cần `Type Conversion` tường minh;
`Direct Mapping` chỉ cho kiểu tương thích. Headerless TXT dùng các tên cột
`column_1`, `column_2`,… theo preview. NULL marker có quote được giữ là chuỗi
literal; marker không quote theo parser mới đại diện NULL.

Validate workbook rồi review mapping, lịch và load policy trước deploy.
APPEND có thể trùng dữ liệu khi chạy run mới; UPSERT cần key phù hợp.
FULL_REFRESH cần xác nhận quyền thay thế riêng; deploy không tự cấp quyền.
Quyền làm rỗng target cũng cần acknowledgment riêng, mặc định tắt.

DAG mới paused; xác nhận enable manual execution hoặc activate schedule riêng.
Theo dõi run thật và đối soát dữ liệu đích. Xem
[luồng DAG](operations/dag-deployment.md), [file sources](operations/file-sources.md)
và [table definitions](operations/table-definitions.md).

Sample pack nằm ở `samples/definitions/` và `samples/data/`; trạng thái nghiệm
thu sample/fresh stack được ghi theo T151, không suy từ việc tải được template.

