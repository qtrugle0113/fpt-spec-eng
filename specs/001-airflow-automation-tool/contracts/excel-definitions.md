# Hợp đồng Excel Definition 1.0

## Artifact và tải về

- Template rỗng: [Table Definition.xlsx](../../../templates/Table%20Definition.xlsx),
  [ETL Definition.xlsx](../../../templates/ETL%20Definition.xlsx).
- Ví dụ nhiều định nghĩa: [Table Definition.sample.xlsx](../../../samples/definitions/Table%20Definition.sample.xlsx),
  [ETL Definition.sample.xlsx](../../../samples/definitions/ETL%20Definition.sample.xlsx).
- Endpoint dự kiến: GET /api/v1/templates/table-definition, GET /api/v1/templates/etl-definition;
  response binary XLSX, Content-Disposition attachment và ETag SHA-256.
- Artifact đã tạo tại Plan; endpoint/parser/backend chưa được triển khai. File mẫu dùng registry
  seed pg_etl/mysql_etl và file UUID11111111-1111-4111-8111-111111111111; không gọi đây là ETL đã chạy.

## Quy tắc workbook

Version là text `1.0` tại Instructions!B1, Instructions!A1=`Template Version`;
Instructions!B2=`Table Definition` hoặc `ETL Definition`. Tên sheet/header đúng case.
Dữ liệu bắt đầu dòng2 ở các sheet dữ liệu; row/column error là Excel index thật bắt đầu1.
Dòng hoàn toàn trống bỏ qua, dòng một phần vẫn validate. Sheet bắt buộc không được thiếu;
Column_Mappings có thể chỉ header. Sheet/header ngoài hợp đồng bị từ chối, không âm thầm bỏ.

Không formula cells, VBA, OLE, external links hoặc executable payload; kiểm ZIP magic,
member path, số entry <=2000, uncompressed <=100MiB, compression ratio<=100, definition upload<=10MiB.
Parser openpyxl read_only=True, data_only=False, keep_links=False; kiểm .xlsx package trước parse,
không dùng data_only=True để formula cached value qua mặt validation. Giới hạn100.000 dòng
metadata tổng workbook, 100 table hoặc100 DAG/lần upload; lỗi vượt giới hạn rõ ràng.

Mỗi field có cell comment Required/Conditional/Optional tiếng Anh. Boolean TRUE/FALSE;
integer là số nguyên, string không được tự diễn giải ngày/locale; date/time text ISO8601.
Blank là chưa chỉ định; literal mặc định là JSON scalar text (`null`, `0`, `true`, `"unknown"`).
Không nhận expression CURRENT_TIMESTAMP hoặc SQL/Python mặc định. Giá trị bắt đầu '=' bị lỗi formula;
không thực thi expression có dấu '+'/'-' vì tất cả nonnumeric fields xử lý literal có type.

DataValidation trong workbook giúp nhập TRUE/FALSE/type/load strategy/positive counts và
cross-sheet names; server phải kiểm lại mọi dòng, không tin dropdown và không giới hạn ở1001.

## Table Definition

Sheets đúng thứ tự Instructions, Tables, Columns. Một lần xác nhận chọn một target connection,
tất cả table phải trùng connection đó. Muốn target khác tải workbook khác; không silently route.

| Sheet | Header | Quy tắc |
| --- | --- | --- |
| Tables | Target Connection Code | Bắt buộc, registry tồn tại, khớp target UI |
| Tables | Target Schema | PostgreSQL optional kế thừa connection schema; MySQL trống hoặc đúng Database Name |
| Tables | Table Name | Bắt buộc identifier hợp lệ, unique normalized physical identity |
| Tables | Table Description | Optional text <=1000ký tự |
| Columns | Target Connection Code, Target Schema, Table Name | Tham chiếu table trong Tables, cùng schema resolution |
| Columns | Column Name | Bắt buộc, unique theo semantics target, không dotted identifier |
| Columns | Column Order | Bắt buộc nguyên1..1000, unique/table; không cần liên tiếp |
| Columns | Data Type | Bắt buộc Integer/Big Integer/Varchar/Text/Decimal/Boolean/Date/Timestamp |
| Columns | Length | Bắt buộc Varchar, 1..65535 và giới hạn byte/row dialect; kiểu khác bỏ trống |
| Columns | Precision, Scale | Decimal: precision1..38, scale0..precision; kiểu khác trống |
| Columns | Nullable, Primary Key | Bắt buộc TRUE/FALSE; primary key không nullable, khóa ghép theo Column Order |
| Columns | Default Value | Optional typed JSON scalar, tương thích kiểu; trống không có explicit default |
| Columns | Column Description | Optional text <=1000ký tự |

Kiểu đồng bộ tối thiểu: Integer→PG INTEGER/MYSQL INT, Big Integer→BIGINT,
Varchar(n)→VARCHAR(n), Text→TEXT, Decimal(p,s)→NUMERIC/DECIMAL,
Boolean→BOOLEAN/BOOLEAN với application strict bool, Date→DATE,
Timestamp→TIMESTAMP WITHOUT TIME ZONE/DATETIME(6). Timestamp là naive;
conversion offset chỉ khi mapping tường minh, không tự bỏ timezone.
MySQL utf8mb4 strict SQL mode, cột decimal không đi qua float; DDL generator từ chối tham số
không phù hợp dialect, không tự cắt length để câu lệnh chạy. PG quote identifiers bằng adapter;
MySQL quote theo dialect. Portable identifier mặc định ASCII `[A-Za-z_][A-Za-z0-9_]*`,
max63byte PG/max64ký tự MySQL; nguồn table ngoài mẫu introspection giữ quoted identifier đã kiểm tra,
không cho spreadsheet đưa SQL token. Tên reserved chỉ khi adapter quote an toàn; không nối raw SQL.

## ETL Definition

Sheets Instructions, ETL_Definitions, Column_Mappings. Mỗi dòng một DAG, một source/target.
Một workbook nhiều DAG có thể dùng nhiều connections; validation toàn workbook trước deploy.

| Header trong ETL_Definitions | Quy tắc |
| --- | --- |
| DAG ID | Bắt buộc, regex `[A-Za-z0-9_.-]{1,200}`, unique workbook/application/Airflow |
| DAG Description | Optional text<=1000 |
| Source Type | Optional DB/CSV/TXT assertion; suy ra reference và phải khớp |
| Source Connection Code | Bắt buộc nguồn DB, phải trống với file |
| Source Schema | DB schema theo dialect, trống với file |
| Source Table | Bắt buộc DB, trống với file |
| Source File Reference | Bắt buộc UUID file khi CSV/TXT, trống với DB |
| Target Connection Code | Bắt buộc registry có target writable |
| Target Schema | Schema theo dialect, optional kế thừa đúng connection |
| Target Table | Bắt buộc table tồn tại; không tự CREATE ở DAG flow |
| Schedule | Bắt buộc Manual hoặc cron5trường, không arbitrary schedule code |
| Start Date | Cron bắt buộc text ISO8601; Manual optional; offset/timezone phải nhất quán |
| Timezone | Bắt buộc IANA, ví dụ UTC, Asia/Ho_Chi_Minh |
| Catchup | Bắt buộc TRUE/FALSE, mặc định FALSE trong ví dụ |
| Load Strategy | Bắt buộc APPEND/UPSERT/FULL_REFRESH |
| Conflict Key | UPSERT bắt buộc comma-separated target columns khớp real PK/unique; strategy khác trống |
| Batch Size | Optional1..10000; ô trống dùng Default Batch Size hiện hành lúc validation (ban đầu1000), pin vào revision; giá trị tường minh được ưu tiên và tiếp tục chịu byte cap |
| Retry Count | Optional0..10, mặc định0 |
| Retry Delay | Optional0..3600giây, mặc định60 |
| Enabled/Paused | Bắt buộc Paused/Enabled; DAG mới luôn paused dù Excel yêu cầu Enabled |
| Optional Source Filtering | Optional JSON predicate DB-only; không SQL fragment |
| Column Mapping Reference | Optional DAG ID trùng chính dòng đó; mapping group thuộc cùng workbook |

Source filter object gồm `and` array1..20 phần tử có column/operator/value. Operator
=, !=, <, <=, >, >=, IN, IS NULL, IS NOT NULL; NULL operators không có value,
IN array1..1000 literal cùng type; field lạ bị từ chối. Không OR/join/subquery/function,
không dùng JSON string như raw WHERE. Batch/setting ranges là giới hạn baseline có thể
được nâng bằng thay đổi hợp đồng có kiểm thử, không nới tự động lúc lỗi.

## Column_Mappings

| Header | Quy tắc |
| --- | --- |
| DAG ID | Required; phải tồn tại ETL_Definitions, không reference workbook khác |
| Source Column | Required Direct Mapping/NULL Handling/Type Conversion; Constant Value bỏ trống |
| Target Column | Required, có thật, unique enabled mapping/DAG |
| Optional Transformation Type | Direct Mapping mặc định, Constant Value, NULL Handling, Type Conversion |
| Optional Default Value | JSON scalar dùng Constant Value/NULL Handling; Type Conversion cần kiểu đích từ target schema |
| Enabled | Required TRUE/FALSE với dòng có dữ liệu |

Type Conversion chỉ theo type target introspection và bảng conversion cho phép trong runtime.md;
không expression riêng. Mapping disabled bị bỏ; không có enabled mapping thì implicit exact-name
mapping type tương thích. Khi có mapping enabled, không tự bổ sung cột; unmatched source chỉ
được bỏ nếu preview rõ. Target bắt buộc không mapping/default gây lỗi. Không yêu cầu file mapping riêng.

## Validation và thông báo

Thứ tự: cấu trúc ZIP/workbook/version → schema/required → duplicates → cross-sheet →
registry dependencies → source/target schema/type/key → mapping/filter/schedule → SQL/config preview.
Tập issues được sắp sheet/row/column, trả giới hạn200issue/trang, có total và cờ truncated.

Ví dụ dữ liệu hiển thị: code=`EXCEL_REFERENCE_NOT_FOUND`, sheet=`Column_Mappings`, row=4,
column=1, column_name=`DAG ID`, message=`DAG ID does not exist in ETL_Definitions`.
Lỗi cấp workbook có scope=workbook và sheet/row/column=null. API message tiếng Anh,
phần giải thích thiết kế tiếng Việt. Không echo nguyên cell password hoặc source row vào log.

Duplicate definition là lỗi toàn workbook, không last-row-wins. Preview có config hash và
connection/schema fingerprints; thay workbook/dependency làm confirmation cũ hết hiệu lực.
SQL runtime từng table báo partial results; validation workbook không cho side effect từng phần.

## Ánh xạ preview và ủy quyền ngoài workbook

Schema Excel1.0 và bytes template/sample không đổi trong lượt Plan sau Clarify. Backend
compile cell metadata thành `ETLConfig` typed trong [OpenAPI](openapi.yaml): source union,
target, schedule/timezone/start_date/catchup, load_strategy/conflict_keys, batch_size,
retry_count/retry_delay, mappings/filter. Transformation English được ánh xạ sang enum
DIRECT/CONSTANT/NULL_HANDLING/TYPE_CONVERSION, literals/predicate operands thành TypedLiteral
giữ decimal/date/time lossless; không thay tên sheet/header hoặc nhận expression tùy ý.
Type Conversion vẫn dùng type target đã introspection, không tự gán timezone.

Không thêm authorization hoặc allow_empty vào cell rồi coi đó là consent. FULL_REFRESH
ONCE/SCHEDULED và allow_empty được xác nhận riêng qua UI/API với scope/revision/hash.
ETL preview phải nêu support DDL, quyền thay thế và quyền làm rỗng; Enabled trong workbook
không bỏ qua paused/activation/admission guards. Column preview có length/default/PK
đúng schema target, lỗi workbook vẫn dùng vị trí Excel thật theo hợp đồng hiện tại.
