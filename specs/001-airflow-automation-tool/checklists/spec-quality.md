# Checklist chất lượng đặc tả: Airflow Automation Tool

**Mục đích**: Đánh giá mức độ đầy đủ, rõ ràng, nhất quán, không mâu thuẫn, có thể kiểm thử và có thể triển khai của yêu cầu; không kiểm tra implementation.
**Ngày tạo**: 2026-11-06
**Tính năng**: [Đặc tả](../spec.md)
**Cơ sở đối chiếu**: [Constitution 1.1.0](../../../.specify/memory/constitution.md), [Specification](../spec.md), [Implementation Plan](../plan.md).
**Độ sâu**: Rà soát toàn diện theo rủi ro, bao phủ 16 nhóm được yêu cầu.
**Người sử dụng và thời điểm**: Reviewer rà soát tài liệu trước triển khai; lượt này đối chiếu bản152task đã đồng bộ Plan ngày2026-11-08.
**Reviewer/ngày đánh giá**: Codex theo ủy quyền trực tiếp của chủ dự án, 2026-11-08.
**Phạm vi quyết định**: Đánh giá đủ CHK001–CHK048 bằng nội dung Spec/Plan/Data Model/Contracts/Tasks; không kiểm thử implementation, không thay approval quy tắc Constitution.

**Ghi chú**: Checklist được tạo bằng `/speckit-checklist`; các mục là câu hỏi về nội dung yêu cầu đã viết, không phải thủ tục kiểm thử sản phẩm.
**Quyền đánh giá**: Reviewer sở hữu checklist. Chỉ reviewer mới quyết định đánh dấu `[x]` khi tiêu chí chất lượng yêu cầu đã được đáp ứng.
**Ý nghĩa trạng thái**: `[x]` xác nhận reviewer thấy đủ bằng chứng chất lượng yêu cầu/thiết kế cho đúng câu hỏi; không có nghĩa implementation hoàn thành hoặc kiểm thử sản phẩm PASS. Mục thiếu, mâu thuẫn hoặc chưa rõ phải giữ `[ ]`.
**Cách tổ chức**: Nhóm theo 16 miền nghiệp vụ; nhãn trong từng mục chỉ chiều chất lượng: đầy đủ, rõ ràng, nhất quán, khả năng đo lường, bao phủ, khả thi, phụ thuộc hoặc mâu thuẫn.
**Truy vết**: `Spec §FR/BR/NFR/SC/US/AS` chỉ mã trong đặc tả; `Plan §` chỉ heading trong kế hoạch; `Constitution §` chỉ nguyên tắc. `Gap` chỉ câu hỏi về khoảng trống cần reviewer rà soát, không khẳng định tài liệu đang thiếu.

## 1. Phạm vi sản phẩm và câu chuyện người dùng

- [x] CHK001 Phạm vi MVP có nêu rõ một operator local, sáu màn hình, tám hướng ETL, một source/target mỗi DAG và các phần ngoài phạm vi, nhất quán giữa ba tài liệu không? [Đầy đủ, Nhất quán; Spec §FR-001, §FR-002, §AS-01, §AS-03, §Ngoài phạm vi MVP; Plan §Bối cảnh kỹ thuật; Constitution §II, §XII]

  **Bằng chứng reviewer — Đạt:** [Spec](../spec.md) FR-001/FR-002, AS-01/AS-03 và §Ngoài phạm vi MVP liệt kê đúng tám hướng, sáu trang, một operator local và một source/target; [Plan](../plan.md) §Bối cảnh kỹ thuật giữ cùng phạm vi, không thêm DB/CDC/multi-user ngoài MVP.

- [x] CHK002 Mỗi US-01 đến US-11 có mục tiêu, ưu tiên, điều kiện tiên quyết và tiêu chí chấp nhận với kết quả quan sát được, bao gồm luồng chính, luồng thay thế và lỗi liên quan không? [Bao phủ, Chất lượng tiêu chí chấp nhận; Spec §US-01–US-11, §Các trường hợp biên, §Phân bổ phạm vi nghiệm thu theo câu chuyện]

  **Bằng chứng reviewer — Đạt:** [Spec](../spec.md) §Kịch bản người dùng và kiểm thử có đủ US-01–US-11, mỗi mục nêu vai trò/mong muốn, ưu tiên/lý do, kiểm thử độc lập và các tình huống Cho trước/Khi/Thì. Điều kiện đầu vào nằm trong từng kịch bản; EC-01–EC-24 và §Phân bổ phạm vi nghiệm thu theo câu chuyện bổ sung luồng lỗi/biên, không chỉ happy path.

- [x] CHK003 Phân kỳ trong Plan có đầu ra, phụ thuộc và cổng nghiệm thu truy vết đến yêu cầu, không bỏ chức năng P2 thuộc MVP hoặc trì hoãn validation/bảo mật của chức năng lõi không? [Khả thi, Nhất quán; Plan §Các giai đoạn triển khai và tiêu chí ra giai đoạn; Spec §Kịch bản người dùng và kiểm thử, §AS-09; Constitution §III, §XII]

  **Bằng chứng reviewer — Đạt:** [Plan](../plan.md) §Các giai đoạn triển khai và tiêu chí ra giai đoạn có tám phase, đầu ra/phụ thuộc/gate riêng; §Chiến lược kiểm thử và bằng chứng giữ A–AM. [Tasks](../tasks.md) Phase1–8 giữ US10/US11 P2 trong MVP, validation/security đi cùng core; T004/T011/T013 tạo và kiểm runner trước T046, không chờ T138.


## 2. Dashboard và metadata Airflow

- [x] CHK004 Tài liệu có phân biệt metadata cấu hình của ứng dụng, metadata điều phối của Airflow và dữ liệu ETL, xác định nguồn có thẩm quyền cho lịch sử/trạng thái và cấm nghiệp vụ đọc bảng nội bộ Airflow không? [Rõ ràng, Nhất quán; Spec §FR-064, §FR-078, §FR-082; Plan §Tóm tắt, §Kiến trúc module và hướng dependency; Constitution §VIII, §Ràng buộc kiến trúc và phạm vi sản phẩm]

  **Bằng chứng reviewer — Đạt:** [Plan](../plan.md) §Tóm tắt và §Kiến trúc module và hướng dependency tách app_metadata/airflow_metadata/ETL target. [Data Model](../data-model.md) §Parser revision và API đọc lịch sử chỉ lưu binding/engine metrics/recovery, cấm mirror run/task/log; Airflow Public API là nguồn lịch sử và status, không dùng engine state làm Airflow success.

- [x] CHK005 Các KPI, công thức Success Rate, nhóm lịch, phạm vi managed/external, phân trang, timezone và số liệu lifetime/date-filtered có định nghĩa đủ cụ thể để đối chiếu khách quan không? [Rõ ràng, Khả năng đo lường; Spec §FR-071–FR-077, §BR-11, §BR-12, §SC-008]

  **Bằng chứng reviewer — Đạt:** [Spec](../spec.md) BR-11 quy định success/(success+failed), mẫu số0 là Not available, inventory khác run count, khoảng ngày nửa mở theo timezone và actual-start/queued fallback; BR-12 phân biệt schedule hiện tại/lịch sử. [Airflow](../contracts/airflow.md) §Dashboard và performance API yêu cầu đủ trang, lifetime incomplete nếu thiếu lịch sử; [OpenAPI](../contracts/openapi.yaml) Dashboard/RunMetrics có completeness và lifetime tương ứng.

- [x] CHK006 Yêu cầu có phân biệt dữ liệu rỗng thật, thiếu, chưa đầy đủ, cũ và không khả dụng khi Airflow mất liên lạc, kể cả metrics external DAG, thay vì quy thành 0 hoặc success không? [Bao phủ ngoại lệ, Nhất quán; Spec §FR-065, §FR-072, §FR-077, §FR-078, §FR-096; Plan §Frontend UI/UX]

  **Bằng chứng reviewer — Đạt:** [Spec](../spec.md) FR-065/FR-072/FR-077/FR-078 không ép dữ liệu thiếu thành0; [Plan](../plan.md) §Frontend UI/UX tách empty/loading/error/stale/partial/unknown và external metrics Not available. [Airflow](../contracts/airflow.md) §Dashboard và performance API giữ fetched_at/completeness, lỗi tổng hợp không coi trang đầu là tổng.


## 3. Quản lý connection

- [x] CHK007 Schema connection, quy tắc unique/trim/case, trường bắt buộc, miền port, vai trò source/target và kết quả kiểm tra kết nối thật có được định nghĩa nhất quán cho PostgreSQL/MySQL không? [Đầy đủ, Rõ ràng; Spec §FR-003–FR-007, §BR-01, §US-02]

  **Bằng chứng reviewer — Đạt:** [Spec](../spec.md) FR-003–FR-007 quy định đủ trường, code unique sau trim/case-insensitive, port1–65535 và dùng cùng connection cho source/target. [OpenAPI](../contracts/openapi.yaml) ConnectionCreate/ConnectionPatch/Connection/TestResult định nghĩa enum POSTGRESQL/MYSQL và request/response; [Data Model](../data-model.md) Connection/ConnectionRevision lưu normalized_code, revision và trạng thái test.

- [x] CHK008 Yêu cầu sửa/xóa connection có làm rõ dependency, revision, thay vị trí DB, thay credential, validation/xác nhận lại và revision bất biến của run đã bắt đầu không? [Bao phủ, Không mâu thuẫn; Spec §FR-008, §FR-009, §BR-21; Plan §Connections, Excel và DDL]

  **Bằng chứng reviewer — Đạt:** [Spec](../spec.md) FR-008/FR-009 và BR-21 chặn xóa/đổi code có dependency, chặn đổi vị trí khi run active, yêu cầu revalidation/consent; credential cũ gắn immutable revision của run. [Data Model](../data-model.md) §Parser revision và API đọc lịch sử giữ secret revision khi active/recovery; [Tasks](../tasks.md) T041–T043 có dependency refs và needs_revalidation công khai.

- [x] CHK009 Tiêu chí chấp nhận có nêu timeout hữu hạn, nhóm lỗi kết nối, giới hạn phân loại lỗi và quy tắc secret mới/bỏ trống/không đọc password cũ, thay vì chỉ yêu cầu “kết nối thành công” không? [Chất lượng tiêu chí chấp nhận, Rõ ràng; Spec §US-02, §FR-007–FR-009, §NFR-009; Constitution §IV, §VI]

  **Bằng chứng reviewer — Đạt:** [Spec](../spec.md) US-02 và FR-007/FR-009 yêu cầu lỗi host/port/auth/database/timeout, báo giới hạn phân loại, password trống giữ cũ và GET không đọc secret. NFR-009 đặt30giây; [Plan](../plan.md) §Kiến trúc module và hướng dependency đặt connect10giây/tổng30giây; [REST API](../contracts/rest-api.md) §Quy ước chung/§Tác vụ đồng bộ và bất đồng bộ quy định write-only và timeout.


## 4. Quản lý file nguồn

- [x] CHK010 Hợp đồng CSV/TXT có định nghĩa encoding, delimiter, header, quote/escape, NULL, chuỗi rỗng, BOM và tên cột không header, đồng thời bảo đảm preview và ETL dùng cùng cấu hình được xác nhận không? [Đầy đủ, Nhất quán; Spec §FR-011, §FR-015, §FR-017, §FR-092, §AS-06]

  **Bằng chứng reviewer — Đạt:** [Spec](../spec.md) FR-011/FR-015/FR-017, AS-06 định nghĩa UTF-8/CSV comma/quote/header/NULL marker và tên column_1… khi thiếu header. [Runtime](../contracts/runtime.md) §Streaming, snapshot và hạn mức mặc định giữ was_quoted, bỏ BOM đầu, NULL khác empty/0/false. [Data Model](../data-model.md) §Parser revision và API đọc lịch sử chốt config immutable cho preview/execution.

- [x] CHK011 Yêu cầu có phân biệt preview tối đa 100 dòng với validation toàn file, đồng thời mô tả lỗi header trùng/rỗng, encoding, quote, số trường và vị trí physical line/record nhiều dòng không? [Bao phủ biên, Rõ ràng; Spec §FR-014, §FR-092, §US-03]

  **Bằng chứng reviewer — Đạt:** [Spec](../spec.md) FR-014/FR-092 giới hạn preview100dòng, full validation toàn nội dung, header unique/không rỗng và lỗi format có vị trí. [Runtime](../contracts/runtime.md) §Streaming, snapshot và hạn mức mặc định yêu cầu lexer giữ quote provenance và cap record trong lúc đọc multiline; [Tasks](../tasks.md) T062/T063/T065 kiểm physical line/record, encoding/quote/field count, không lấy preview thay validation.

- [x] CHK012 Vòng đời file có định nghĩa reference gắn đúng nội dung, upload chưa hoàn tất, persistence, retention/dependency và nguồn thiếu/quá hạn phải fail thay vì trở thành dataset rỗng không? [Đầy đủ, An toàn dữ liệu; Spec §FR-012, §FR-013, §FR-016, §US-03; Constitution §VII, §IX]

  **Bằng chứng reviewer — Đạt:** [Spec](../spec.md) FR-012/FR-013/FR-016 yêu cầu content reference bền, upload chỉ publish khi xong, thiếu/quá hạn fail. [Data Model](../data-model.md) UploadedFile/FileParserRevision và §Retention và khôi phục giữ checksum/revision/FK RESTRICT; [Tasks](../tasks.md) T064/T065/T067/T091 quy định atomic publish, cleanup incomplete sau xác minh và không GC nguồn còn dependency.


## 5. Table Definition và SQL DDL

- [x] CHK013 Schema workbook Table Definition có quy định version, sheet/header, required/optional, liên kết Tables/Columns, định danh ghép, dòng trống và duplicate/orphan đủ để tác giả không phải tự suy đoán không? [Đầy đủ, Rõ ràng; Spec §FR-018–FR-023, §FR-098, §BR-22; Plan §Connections, Excel và DDL]

  **Bằng chứng reviewer — Đạt:** [Excel](../contracts/excel-definitions.md) §Quy tắc workbook/§Table Definition đặt version text1.0 ở Instructions!B1, exact sheet/header, từng trường required/conditional/optional và table identity connection/schema/table. Dòng trống toàn bộ bỏ, dòng một phần validate; duplicates/orphan chặn toàn workbook. [Spec](../spec.md) FR-098/BR-22 khẳng định không suy cha bằng thứ tự dòng hoặc last-row-wins.

- [x] CHK014 Yêu cầu kiểu dữ liệu, length/precision/scale, nullable/default, khóa ghép và SQL preview có nhất quán theo hai dialect, không chấp nhận chuyển kiểu mất dữ liệu hoặc biểu thức SQL tùy ý không? [Nhất quán, Khả thi; Spec §FR-023–FR-025, §NFR-003; Constitution §V, §VI]

  **Bằng chứng reviewer — Đạt:** [Excel](../contracts/excel-definitions.md) §Table Definition định nghĩa length1..65535 chịu byte/row dialect, decimal1..38/scale<=precision, PK không nullable theo Column Order, typed JSON defaults và ánh xạ PG/MySQL. [Runtime](../contracts/runtime.md) §Mapping và kiểm tra kiểu cấm round/truncate/coercion mất dữ liệu; [Tasks](../tasks.md) T053–T055 tạo preview đúng dialect, phân biệt explicit null với không default.

- [x] CHK015 Yêu cầu có phân biệt validation toàn workbook không side effect với DDL runtime có thể thành công từng table, nêu rõ xác nhận/revalidation, table tồn tại và giới hạn transaction MySQL mà không hứa rollback toàn workbook không? [Không mâu thuẫn, Bao phủ lỗi; Spec §FR-026–FR-028, §BR-02, §BR-03, §BR-06; Plan §Connections, Excel và DDL]

  **Bằng chứng reviewer — Đạt:** [Spec](../spec.md) FR-026–FR-028, BR-03/BR-06/BR-15 tách validation toàn workbook khỏi DDL từng table, không rollback toàn workbook MySQL hoặc ALTER/DROP table cũ. [Data Model](../data-model.md) §Công việc nền và kết quả thao tác có CREATED/ALREADY_EXISTS/FAILED/UNKNOWN; [Tasks](../tasks.md) T055–T060 recheck sau confirmation, reconcile signature khi mất phản hồi DDL và lưu kết quả từng table.


## 6. ETL Definition và column mapping

- [x] CHK016 ETL Definition có định nghĩa nguồn DB/file loại trừ nhau, reference hợp lệ, target phải tồn tại, nhiều DAG trong workbook và mapping liên kết đúng DAG, không ngầm tạo target hoặc bổ sung nguồn thứ hai không? [Đầy đủ, Nhất quán; Spec §FR-030–FR-033, §FR-042, §FR-098, §AS-03]

  **Bằng chứng reviewer — Đạt:** [Excel](../contracts/excel-definitions.md) §ETL Definition quy định DB/file loại trừ, file UUID hoặc connection/schema/table, target phải tồn tại và một dòng/một DAG. §Column_Mappings liên kết DAG ID cùng workbook; [OpenAPI](../contracts/openapi.yaml) ETLSource/ETLConfig diễn đạt union/whitelist. [Spec](../spec.md) FR-030–FR-033 không cho implicit CREATE target hoặc nguồn thứ hai.

- [x] CHK017 Quy tắc mapping tường minh/implicit có rõ điều kiện enabled, tên cột chính xác, cột dư, target thiếu, nullable/default, mapping trùng và trường hợp mơ hồ phải bị từ chối không? [Rõ ràng, Bao phủ biên; Spec §FR-044–FR-046, §BR-05; Spec §Ma trận nghiệm thu bắt buộc, mục AL]

  **Bằng chứng reviewer — Đạt:** [Spec](../spec.md) FR-044–FR-046/BR-05 chỉ implicit exact-name khi không có mapping enabled, reject target bắt buộc thiếu/default sai và mapping enabled trùng. [Excel](../contracts/excel-definitions.md) §Column_Mappings bắt buộc Enabled cho dòng có dữ liệu, không tự bổ sung cột nếu explicit mapping; cột source bỏ phải preview rõ. [Runtime](../contracts/runtime.md) §Mapping và kiểm tra kiểu giữ quy tắc đó khi thực thi.

- [x] CHK018 Danh mục transformation/filter có phạm vi, quy tắc NULL/giá trị falsy/conversion và tiêu chí bảo toàn Unicode/decimal/temporal, đồng thời yêu cầu lỗi và revalidation khi schema drift thay vì sửa mapping ngầm không? [Khả thi, Khả năng đo lường; Spec §FR-043, §FR-046–FR-048, §FR-091, §SC-015; Plan §Engine, type và load]

  **Bằng chứng reviewer — Đạt:** [Excel](../contracts/excel-definitions.md) §Column_Mappings/§ETL Definition giới hạn bốn transformation, DB-only AND predicate1..20, IN1..1000 và operator whitelist, không raw WHERE. [Runtime](../contracts/runtime.md) §Mapping và kiểm tra kiểu quy định conversion exact/ISO, không tự bỏ/gán timezone, schema fingerprint trước run/load; [Spec](../spec.md) BR-17/SC-015 phân biệt NULL/falsy và yêu cầu lossless hoặc lỗi.


## 7. Sinh và triển khai DAG

- [x] CHK019 Tiêu chí deployment thành công có yêu cầu bằng chứng Airflow parse và đăng ký đúng DAG ID cùng revision, tách khỏi ghi file thành công, DAG cũ tồn tại và execution thành công không? [Rõ ràng, Chất lượng tiêu chí chấp nhận; Spec §FR-035, §FR-038, §SC-009; Constitution §VIII]

  **Bằng chứng reviewer — Đạt:** [Airflow](../contracts/airflow.md) §Deployment và admission bước4–5 đòi owner/hash/fileloc/parse timestamp/latest version khớp trước Deployed; file đã ghi hoặc DAG cũ không đủ. [Spec](../spec.md) FR-035/FR-038/SC-009 và [Tasks](../tasks.md) T097/T108/T118 tách registration khỏi execution/target data, có ca old revision/parse error.

- [x] CHK020 Yêu cầu có phân biệt pending, parse error, timeout/API unavailable và kết quả chưa xác định trong hạn 120 giây, với identity và đối soát trước retry thay vì báo thất bại/thành công không có bằng chứng không? [Bao phủ ngoại lệ, Khả năng đo lường; Spec §FR-039, §FR-041, §FR-096; Plan §DAG và Airflow]

  **Bằng chứng reviewer — Đạt:** [Spec](../spec.md) FR-039/FR-096 giới hạn120giây để xác minh hoặc báo timeout/unknown. [Airflow](../contracts/airflow.md) §Deployment và admission quy định poll1/2/4/cap5+jitter; §Lỗi và phục hồi không blind retry command. [Data Model](../data-model.md) DAGDeployment.reconcile_required và Operation.NEEDS_RECONCILIATION giữ identity qua restart, không coi timeout là rollback.

- [x] CHK021 Quy tắc cron/manual, UTC/IANA/DST, catchup, DAG mới paused, activation riêng, external ownership và redeploy có chốt revision/drain run/xác nhận lại đủ để tránh xung đột lịch và quyền ghi dữ liệu không? [Đầy đủ, Nhất quán; Spec §FR-034, §FR-036, §FR-037, §FR-097, §BR-04, §BR-20; Plan §DAG và Airflow]

  **Bằng chứng reviewer — Đạt:** [Spec](../spec.md) BR-04/BR-20 quy định cron5trường/manual, UTC default/IANA/DST, Catchup false và activation riêng sau paused deploy. [Airflow](../contracts/airflow.md) §Deployment và admission chốt revision, pause/drain queued/running, block startup race, không tự cancel hoặc ghi đè external; LocalDagBundle old-clear revision mismatch bị reject. [Tasks](../tasks.md) T107/T112/T113/T118/T119 bao phủ manual/cron và quyền ONCE/SCHEDULED.


## 8. APPEND, UPSERT và FULL_REFRESH

- [x] CHK022 APPEND có định nghĩa rõ chỉ insert, giữ dữ liệu cũ, nguy cơ duplicate khi rerun mới, unique violation và điều kiện retry chỉ tiếp tục batch chưa commit trên dataset bất biến không? [Rõ ràng, Bao phủ; Spec §FR-050, §FR-051, §BR-07, §SC-005]

  **Bằng chứng reviewer — Đạt:** [Spec](../spec.md) FR-050/FR-051, BR-06/BR-07 định nghĩa APPEND insert-only, rerun mới có thể duplicate, unique error fail thay skip. [Runtime](../contracts/runtime.md) §Thuật toán load theo policy yêu cầu DML+batch marker atomic, hash/order deterministic và chỉ skip marker khớp binding/dataset; commit unknown đối soát trước replay. [Tasks](../tasks.md) T083/T086/T094/T144 có kết quả đối chiếu theo batch.

- [x] CHK023 UPSERT có yêu cầu conflict key khớp trọn khóa thật, xử lý khóa ghép/NULL/duplicate theo target, xung đột unique key khác và không tự ALTER/index/downgrade APPEND, với tiêu chí rerun đo bằng key/giá trị không? [Đầy đủ, Chất lượng tiêu chí chấp nhận; Spec §FR-052, §BR-07, §BR-15, §SC-005]

  **Bằng chứng reviewer — Đạt:** [Spec](../spec.md) FR-052/BR-15/BR-17/BR-18 yêu cầu real chosen PK/unique trọn khóa, non-NULL và duplicate theo semantics target, không ALTER/index/downgrade. [Runtime](../contracts/runtime.md) §Mapping và kiểm tra kiểu dùng scratch disk/target collation trước ghi; §Thuật toán load theo policy nêu PG ON CONFLICT đúng key và MySQL UPDATE JOIN+INSERT, collision unique phụ rollback. SC-005 và T083/T087/T088/T094 đo key/giá trị qua ba lần.

- [x] CHK024 FULL_REFRESH có định nghĩa ủy quyền đúng target/scope/revision/lịch, quyền zero-row riêng, chuẩn bị toàn dataset trước thay thế, một commit công bố atomic và giới hạn isolation/dependency, không TRUNCATE rồi commit batch không? [An toàn dữ liệu, Không mâu thuẫn; Spec §FR-053, §FR-054, §BR-06, §BR-08, §BR-15; Constitution §VI; Plan §Engine, type và load]

  **Bằng chứng reviewer — Đạt:** [Spec](../spec.md) BR-08 chốt target/revision/scope/lịch, ONCE reservation trước trigger, SCHEDULED không manual và allow_empty xác nhận riêng. [Runtime](../contracts/runtime.md) §Reservation và admission FULL_REFRESH serialize revoke/admission, không reuse quyền hoặc replacement đã verified; §Thuật toán load theo policy chuẩn bị mapped dataset trước DELETE/INSERT/final-marker cùng một commit, reject unsafe dependency/trigger, loại READ UNCOMMITTED. [Tasks](../tasks.md) T084/T085/T089/T119/T145 giữ các ranh giới này.


## 9. Toàn vẹn dữ liệu và phục hồi lỗi

- [x] CHK025 Yêu cầu chống mất dữ liệu có chỉ rõ hậu điều kiện khi extraction/validation thất bại, lỗi giữa batch và lỗi công bố FULL_REFRESH, bao gồm giữ/phục hồi target cũ và không suy lỗi nguồn thành empty dataset không? [Đầy đủ, Bao phủ phục hồi; Spec §FR-053–FR-055, §FR-060, §SC-006, §SC-013; Constitution §VI]

  **Bằng chứng reviewer — Đạt:** [Spec](../spec.md) FR-053–FR-055/BR-06/BR-18 nói extraction/full validation fail chưa đổi target, APPEND/UPSERT lỗi chỉ rollback batch hiện tại và báo partial, FULL_REFRESH giữ old target khi transaction lỗi. [Runtime](../contracts/runtime.md) §Thuật toán load theo policy/§Reservation và admission FULL_REFRESH dùng final ledger cho commit proof, không diễn giải source error thành empty. T083/T089/T145 kiểm old/new data và unknown không success.

- [x] CHK026 Retry/rerun có phân biệt logical run mới/cũ, dataset identity, tiến độ commit bền, commit mất phản hồi, worker kill và recovery không tự hoàn tất, với điều kiện dừng/đối soát/can thiệp và giới hạn retry rõ ràng không? [Rõ ràng, Khả thi; Spec §FR-051, §FR-054, §FR-089, §FR-095, §BR-07, §SC-014; Plan §Engine, type và load]

  **Bằng chứng reviewer — Đạt:** [Data Model](../data-model.md) §Vòng đời ủy quyền FULL_REFRESH tách RunIntent/binding/admission/commit state, ONCE không trả GRANTED khi timeout hoặc terminal failure. [Runtime](../contracts/runtime.md) §Reservation và admission FULL_REFRESH/§Cleanup và trạng thái phục hồi giữ immutable dataset, protected evidence và cần old-writer-ended proof; [Tasks](../tasks.md) T090 retry0..10/delay0..3600, dừng non-safe sớm; T091 đối soát120giây hoặc nêu blocked.

- [x] CHK027 Yêu cầu ghi đồng thời có xác định physical target kể cả connection alias, quyền ghi độc quyền, timeout 300 giây, chủ sở hữu chưa rõ và giả định không có writer ngoài, nhất quán cho cả ba strategy không? [Phụ thuộc, Nhất quán; Spec §BR-09, §SC-014; Plan §Engine, type và load; Constitution §VII]

  **Bằng chứng reviewer — Đạt:** [Spec](../spec.md) BR-09 định nghĩa physical identity qua server/database/schema/table, aliases cùng target phải serialize xuyên ba strategy, timeout300giây và không cam kết external writer. [Data Model](../data-model.md) §Các thực thể cấu hình/§Support objects trong target database và [Runtime](../contracts/runtime.md) §Thuật toán load theo policy đặt PG OID/MySQL canonical DB-table native lock cùng writer session, không chiếm bằng heartbeat stale; T079/T146 kiểm alias/owner unknown.


## 10. Dữ liệu lớn và staging trên đĩa

- [x] CHK028 Yêu cầu có lượng hóa RAM, quota disk/upload, byte cap từng dòng/chunk, free-space reserve, parallelism và chunk/batch riêng, với tiêu chí dataset lớn hơn hai lần RAM và ít nhất 20 batch không? [Khả năng đo lường, Khả thi; Spec §FR-088, §FR-094, §NFR-004, §SC-007; Plan §Bối cảnh kỹ thuật, §Chiến lược kiểm thử và bằng chứng]

  **Bằng chứng reviewer — Đạt:** [Runtime](../contracts/runtime.md) §Streaming, snapshot và hạn mức mặc định lượng hóa512MiB/process, parallelism2/scheduler2GiB, upload256MiB/definition10MiB, staging10GiB/run/20GiBglobal/reserve1GiB, row1MiB/buffer8MiB và chunk/batch1.000/max10.000. Driver size-guard trước materialize và RSS supervisor được nêu rõ; [Spec](../spec.md) SC-007 và [Tasks](../tasks.md) T095/T147 yêu cầu dataset>1GiB,>20batch, disk/RSS evidence chứ không test nhỏ.

- [x] CHK029 Hợp đồng DB-to-DB staging có xác định disk thật, snapshot nhất quán, namespace DAG/Run/attempt, manifest/checksum/schema revision và điều kiện complete trước target load, không fallback RAM/tmpfs/XCom dataset không? [Đầy đủ, Nhất quán; Spec §FR-055, §FR-057, §FR-058, §FR-089, §FR-090; Plan §Engine, type và load; Constitution §VII]

  **Bằng chứng reviewer — Đạt:** [Runtime](../contracts/runtime.md) §Manifest và encoding v1 có hashed DAG/run/dataset/attempt paths, typed aat-jsonl/1/schema/hash, fsync/rename và COMPLETE chỉ sau file bền; §Streaming, snapshot và hạn mức mặc định dùng PG/MySQL một REPEATABLE READ snapshot. [Spec](../spec.md) FR-055/FR-057/FR-058/FR-089/FR-090 cấm tmpfs/RAM fallback/XCom dataset; T075/T081/T095 kiểm disk/checksum/không target DML trước preparation xong.

- [x] CHK030 Cleanup policy có quy định thời gian lưu theo trạng thái, lịch/điều kiện dọn, artifact active/retry/recovery/commit chưa rõ cần bảo vệ, đối soát orphan sau restart và phản hồi lỗi disk full/I/O/checksum/quyền truy cập không? [Bao phủ phục hồi, Rõ ràng; Spec §FR-061, §FR-094, §FR-095, §FR-100; Plan §Engine, type và load; Constitution §VII]

  **Bằng chứng reviewer — Đạt:** [Data Model](../data-model.md) §Retention và khôi phục quy định staging7ngày sau terminal/recovery xong, source unreferenced30ngày, ledger ít nhất30ngày sau đối soát; active/protected không GC. [Runtime](../contracts/runtime.md) §Cleanup và trạng thái phục hồi nêu orphan chỉ dọn khi writer chết đã xác minh và startup reconciliation120giây hoặc blocked. [Tasks](../tasks.md) T076/T091/T095 ghi quota/I/O/corrupt/lost volume, logs/report và không xóa evidence để vượt quota.


## 11. Compose và khởi tạo tự động

- [x] CHK031 Tiêu chí one-command startup có nêu đúng lệnh `podman compose up --build -d` (hoặc `docker compose up --build -d` cho baseline Docker), điều kiện đầu vào, đầy đủ services, init/migration/seed tự động và readiness chức năng thật, không đòi bước cấu hình thủ công sau khởi động không? [Chất lượng tiêu chí chấp nhận, Đầy đủ; Spec §US-01, §FR-081, §FR-099, §SC-001; Plan §Thiết kế Compose và runtime container; Constitution §IX]

  **Bằng chứng reviewer — Đạt:** [Spec](../spec.md) US-01/FR-081/FR-099/SC-001 và [Quickstart](../quickstart.md) §Một lệnh khởi động dùng đúng podman compose up --build -d cho baseline Podman đã công bố (Docker baseline dùng docker compose tương ứng), không copy .env/migrate/seed thủ công. [Plan](../plan.md) §Thiết kế Compose và runtime container liệt kê đủ init/DB/backend/frontend/Airflow và dependency; §Các giai đoạn triển khai phân biệt bootstrap Phase1 với app readiness T030/T034 và sample workflow nghiệm thu T140/T152.

- [x] CHK032 Yêu cầu restart có bao phủ initialization idempotent, sample namespace riêng, persistent volumes/secret key, migration lỗi không reset dữ liệu và recovery giữa extraction/batch commit/FULL_REFRESH không? [Bao phủ phục hồi, Nhất quán; Spec §FR-083, §FR-100; Spec §Ma trận nghiệm thu bắt buộc, mục AM; Constitution §IX]

  **Bằng chứng reviewer — Đạt:** [Plan](../plan.md) §Thiết kế Compose và runtime container yêu cầu DB init mỗi startup, natural-key insert-only seed, migration owner lock, secret volumes bền và lỗi thiếu key không regenerate. [Data Model](../data-model.md) §Chỉ mục, validation và migrations/§Retention và khôi phục cấm reset/downgrade, bảo vệ revision/evidence; [Tasks](../tasks.md) T007/T013/T030/T091/T140 kiểm fresh/restart và kill giữa extraction/commit/refresh theo AM.

- [x] CHK033 Plan có xác định phụ thuộc startup, health/liveness/readiness, quyền volume, loopback ports và phân biệt hostname nội bộ với URL browser, phù hợp giả định runtime/OS/cổng của Specification không? [Khả thi, Phụ thuộc; Spec §FR-070, §FR-099, §AS-01, §AS-02; Plan §Thiết kế Compose và runtime container, §Bối cảnh kỹ thuật]

  **Bằng chứng reviewer — Đạt:** [Plan](../plan.md) §Thiết kế Compose và runtime container xác định service_healthy/completed, CLI/JSON functional probes, liveness khác aggregate readiness, UID/GID/RO secret mounts và loopback3000/8000/8080; hostname container khác browser URL. §Bối cảnh kỹ thuật/§Các giai đoạn triển khai cùng [Quickstart](../quickstart.md) §Điều kiện đầu vào/§Một lệnh khởi động nêu Linux containers trên Windows và host resources; T012/T034 không lấy HTTP200 hay running thay readiness.


## 12. Tích hợp Backend/API

- [x] CHK034 Ranh giới UI → Backend → DB/Airflow có xác định authority validation, metadata repository, worker công việc nền và Airflow là nơi duy nhất điều phối/thực thi ETL, không mock hoặc scheduler thay thế không? [Nhất quán, Khả thi; Spec §NFR-008; Plan §Kiến trúc module và hướng dependency, §Backend API và công việc nền; Constitution §IV, §VIII]

  **Bằng chứng reviewer — Đạt:** [Plan](../plan.md) §Kiến trúc module và hướng dependency/§Backend API và công việc nền tách frontend, authoritative backend validation, metadata repository và worker durable. ETL wheel chạy bởi Airflow LocalExecutor, không HTTP/background task hoặc scheduler riêng; [Data Model](../data-model.md) §Quy ước chung tách app/Airflow DB. [Spec](../spec.md) NFR-008 và Constitution IV/VIII cấm mock thay bằng chứng tích hợp.

- [x] CHK035 Hợp đồng API được Plan tham chiếu có quy định request/response, validation/error location, status tác vụ dài, timeout và trạng thái kết quả chưa rõ, truy vết được sang nghiệp vụ mà không chỉ liệt kê endpoint không? [Đầy đủ, Rõ ràng; Plan §Backend API và công việc nền; Spec §FR-020, §FR-035, §FR-060, §FR-096, §NFR-006]

  **Bằng chứng reviewer — Đạt:** [REST API](../contracts/rest-api.md) §Quy ước chung/§Tác vụ đồng bộ và bất đồng bộ/§Hợp đồng lỗi quy định payload, HTTP status, request_id/location, 202+Operation/poll, timeout và unknown side effect. [OpenAPI](../contracts/openapi.yaml) Issue/ErrorResponse/Operation cùng request/response schemas cung cấp contract máy đọc. T015/T096/T148 phải kiểm drift/required fields/write-only/status, không chỉ kiểm số endpoint.

- [x] CHK036 Quy tắc idempotency, stale edit/confirmation, revision dependency, operation recovery và đồng bộ contract có được tài liệu hóa đủ để tránh gửi lặp, lost update hoặc phản hồi success trước side effect được xác minh không? [Bao phủ, Không mâu thuẫn; Spec §BR-02, §FR-041, §FR-067, §FR-096, §FR-097; Plan §Backend API và công việc nền]

  **Bằng chứng reviewer — Đạt:** [REST API](../contracts/rest-api.md) §Quy ước chung/§Hợp đồng ủy quyền FULL_REFRESH quy định If-Match/ETag412, key/hash409 và token10phút hash-bound; replay intent cũ kể cả token hết hạn không tạo quyền/run mới. [Data Model](../data-model.md) §Công việc nền và kết quả thao tác giữ lease/unknown không replay; [Airflow](../contracts/airflow.md) §Deployment và admission/§Lỗi và phục hồi yêu cầu readback/reconcile identity. T031/T033/T112/T119 kiểm reservation/idempotency/races.


## 13. Trải nghiệm Frontend và ngôn ngữ UI

- [x] CHK037 Yêu cầu cho sáu màn hình có mô tả workflow, preview/xác nhận phạm vi dữ liệu, tiến độ và trạng thái empty/loading/error/stale/partial/unknown, giúp phân biệt tiếp nhận tác vụ với kết quả nghiệp vụ không? [Đầy đủ, Nhất quán; Spec §FR-002, §FR-022, §FR-029, §FR-067, §FR-072, §NFR-002; Plan §Frontend UI/UX]

  **Bằng chứng reviewer — Đạt:** [Plan](../plan.md) §Frontend UI/UX liệt kê đủ sáu trang, route, wizard/table/detail/progress và empty/loading/error/stale/partial/unknown; không optimistic success cho DB/Airflow side effects. [Spec](../spec.md) FR-022/FR-029/FR-067 tách preview/confirmation/accepted khỏi execute, BR-08 yêu cầu UI giải thích allow_empty và giới hạn revoke; T045/T059/T117/T126/T131/T135 gắn API thật.

- [x] CHK038 Các từ “responsive”, “trực quan” và “nhất quán” có được cụ thể hóa bằng tiêu chí 1440/390 px, hành động chính không bị che, vùng cuộn bảng, label/lỗi trường và khả năng dùng bàn phím không? [Rõ ràng, Khả năng đo lường; Spec §NFR-002, §SC-002; Plan §Frontend UI/UX; Constitution §II]

  **Bằng chứng reviewer — Đạt:** [Spec](../spec.md) NFR-002 đặt1440/390px, primary action không bị che, table scroll vùng chứa, form label/lỗi gắn trường và keyboard. [Plan](../plan.md) §Frontend UI/UX cụ thể sidebar thu gọn, focus và wizard; [Tasks](../tasks.md) T013/T136/T137/T139 kiểm browser sizes, accessibility và action visibility. SC-002 giới hạn10phút thao tác fixture tạo table/deploy đầu tiên.

- [x] CHK039 Yêu cầu ngôn ngữ có bao phủ toàn bộ nội dung UI bằng tiếng Anh, kể cả validation/notification/tooltip/empty state và ánh xạ lỗi phụ thuộc, trong khi tên ứng dụng/branding phù hợp Constitution không? [Đầy đủ, Nhất quán; Spec §FR-086, §NFR-001; Constitution §I, §II; Plan §Frontend UI/UX]

  **Bằng chứng reviewer — Đạt:** [Constitution](../../../.specify/memory/constitution.md) I/II bắt buộc UI messages/validation/notification/empty state tiếng Anh, tên Airflow Automation Tool và không third-party branding. [Plan](../plan.md) §Frontend UI/UX dùng đúng tên dạng chữ/icon trung tính và English dependency errors; [Spec](../spec.md) NFR-001/FR-086 và T032/T136/T148 yêu cầu ánh xạ lỗi/redact/language audit. Cụm trung tính ở T003 phải được đọc theo tên bắt buộc này, không cho tự đổi tên.


## 14. Bảo mật

- [x] CHK040 Yêu cầu bảo vệ credential có xác định mã hóa và khóa tách biệt/bền, quyền truy cập, password write-only và các bề mặt cấm DB plaintext/DAG/API/log/XCom, với tiêu chí nghiệm thu không rò secret không? [Đầy đủ, Chất lượng tiêu chí chấp nhận; Spec §FR-009, §FR-100, §NFR-003, §SC-011; Constitution §VI; Plan §Thiết kế Compose và runtime container]

  **Bằng chứng reviewer — Đạt:** [Constitution](../../../.specify/memory/constitution.md) VI, [Spec](../spec.md) FR-009/FR-100/NFR-003/SC-011 cấm plaintext DB và credentials DAG/API/log/XCom. [Plan](../plan.md) §Thiết kế Compose và runtime container chia domain secret volumes/RO mounts, không admin key ở runtime; [Research](../research.md) §4. Secrets và metadata runtime dùng Fernet/key_id và runtime lookup encrypted revision. T007/T037/T148 yêu cầu missing-key fail, rotation/recovery và scan bề mặt rò rỉ, không dùng encrypted DB một mình làm bằng chứng an toàn.

- [x] CHK041 Yêu cầu đầu vào không tin cậy có bao phủ SQL identifiers/values, Python/formula/macro/external link, upload path và giới hạn workbook/network, đồng thời nêu kết quả từ chối trước side effect và không để lỗi công khai lộ dữ liệu nhạy cảm không? [Bao phủ ngoại lệ, Khả thi; Spec §FR-013, §FR-019, §FR-020, §NFR-003; Plan §Connections, Excel và DDL, §Backend API và công việc nền; Constitution §V, §VI]

  **Bằng chứng reviewer — Đạt:** [Excel](../contracts/excel-definitions.md) §Quy tắc workbook/§Table Definition giới hạn ZIP/size/entries, cấm formula/VBA/OLE/external links/raw expressions và quote identifier theo dialect. [REST API](../contracts/rest-api.md) §Quy ước chung giới hạn DB host allowlist/origin, không HTTP URL/path; [Runtime](../contracts/runtime.md) §Streaming, snapshot và hạn mức mặc định/§Mapping và kiểm tra kiểu dùng query parameterization, byte guards và fail-safe. T036/T050/T064/T148 có injection/traversal/rebind/secret leak cases trước side effect.

- [x] CHK042 Phạm vi “local không login” có được phân biệt với xác thực service/runtime, kiểm soát origin/mutation, quyền DB/volume và giới hạn chưa hỗ trợ Internet, không bị diễn giải thành bỏ toàn bộ bảo mật không? [Giả định, Không mâu thuẫn; Spec §AS-01; Plan §Thiết kế Compose và runtime container, §Backend API và công việc nền; Constitution §IV, §VI]

  **Bằng chứng reviewer — Đạt:** [Spec](../spec.md) AS-01 giới hạn operator tin cậy/loopback, không suy bỏ service auth. [REST API](../contracts/rest-api.md) §Quy ước chung quy định origin/CORS/mutation protection, §Danh mục endpoint chốt private root ngoài public router và chặn cả hai proxy prefixes. [OpenAPI](../contracts/openapi.yaml) private bind có server override/RuntimeBearer; [Plan](../plan.md) §Thiết kế Compose và runtime container chia role/volume và [Airflow](../contracts/airflow.md) §Phạm vi và xác thực cấm anonymous all-admin.


## 15. Kiểm thử và tiêu chí chấp nhận

- [x] CHK043 Ma trận nghiệm thu có bao phủ đủ PostgreSQL → PostgreSQL, MySQL → MySQL, PostgreSQL → MySQL, MySQL → PostgreSQL, CSV/TXT → cả hai DB, với expected count/giá trị/key/NULL và ít nhất một execution Airflow thật cho mỗi hướng không? [Đầy đủ, Chất lượng tiêu chí chấp nhận; Spec §FR-001, §SC-003, §SC-009; Spec §Ma trận nghiệm thu bắt buộc, mục C–H, U; Plan §Chiến lược kiểm thử và bằng chứng]

  **Bằng chứng reviewer — Đạt:** [Spec](../spec.md) FR-001/SC-003/SC-009 và ma trận C–H/U/I/AE đòi đủ tám routes, target count/value/key/NULL và Airflow execution thật cho mỗi hướng. [Plan](../plan.md) §Chiến lược kiểm thử và bằng chứng phân biệt engine trực tiếp/Airflow; [Tasks](../tasks.md) T094 kiểm tám route trực tiếp, T118/T142/T143 kiểm DAG/run/task và target thật, không dùng registration thay transfer.

- [x] CHK044 Tiêu chí “dữ liệu thực sự được chuyển” có yêu cầu đối soát dataset sau filter/mapping với target theo từng strategy, phân biệt source rows với affected rows và thành công DAG với thành công dữ liệu không? [Khả năng đo lường, Rõ ràng; Spec §FR-062, §FR-093, §BR-18, §SC-003; Spec §Ma trận nghiệm thu bắt buộc, mục AG]

  **Bằng chứng reviewer — Đạt:** [Spec](../spec.md) FR-093/BR-13/BR-18 quy định đối soát dataset đã filter: APPEND target tăng tương ứng, UPSERT theo key/giá trị, FULL_REFRESH target mới; loaded là source rows committed, không affected_rows hoặc live source COUNT sau snapshot. [Data Model](../data-model.md) §Support objects trong target database đặt DML+marker cùng commit, projection app DB không commit proof; T082/T094/T144/T145 có expected/actual và không double-count retry.

- [x] CHK045 Yêu cầu bằng chứng có bao phủ unit/integration/E2E thật, lỗi/retry/rerun/recovery/stress/startup, mã truy vết A–AM, fixture/môi trường/lệnh/expected-actual và trạng thái NOT_RUN/BLOCKED, không coi mock hoặc đánh giá thiết kế “Đạt” là runtime PASS không? [Đầy đủ, Không mâu thuẫn; Spec §FR-085, §SC-012; Plan §Kiểm tra Constitution, §Chiến lược kiểm thử và bằng chứng; Constitution §X]

  **Bằng chứng reviewer — Đạt:** [Plan](../plan.md) §Chiến lược kiểm thử và bằng chứng bao phủ unit/API/DB/ETL/Airflow/E2E/stress/startup/failure, environment/resources/commands/input hashes/expected-actual và PASS/FAIL/NOT_RUN/BLOCKED. [Tasks](../tasks.md) T004/T011/T013 đặt runner trước consumer, T095/T140–T149 và T152 chốt A–AM/BR-08/SC-001–SC-015. [Quickstart](../quickstart.md) §Các lệnh kiểm thử sau implementation/§Mẫu báo cáo nghiệm thu không coi smoke/mock/design Đạt là runtime PASS.


## 16. Quy tắc tài liệu Markdown tiếng Việt

- [x] CHK046 Quy định Markdown tiếng Việt có bao phủ heading, user story, acceptance criteria, checklist, kiến trúc/vận hành/báo cáo, đồng thời phân biệt ngoại lệ thuật ngữ/code/path/chuỗi UI và Excel trích dẫn bằng tiếng Anh không? [Rõ ràng, Nhất quán; Spec §FR-086, §NFR-001; Constitution §I]

  **Bằng chứng reviewer — Đạt:** [Constitution](../../../.specify/memory/constitution.md) I liệt kê Markdown/prompt/report/heading/user story/acceptance/docs tiếng Việt và ngoại lệ tên công nghệ/API/code/path/enum/chuỗi UI-Excel trích dẫn. [Spec](../spec.md) NFR-001/FR-086 giữ cùng quy tắc; [Tasks](../tasks.md) §Quy ước định dạng và thực thi cùng T136/T148/T150 phân biệt Markdown tiếng Việt với UI/Excel tiếng Anh.

- [x] CHK047 Yêu cầu bàn giao tài liệu có bao phủ README, API, schema Excel, startup, cấu hình, load/staging/recovery/troubleshooting và cơ chế cập nhật đồng bộ khi nghiệp vụ/API/schema thay đổi không? [Đầy đủ, Khả thi; Spec §FR-086, §FR-087; Constitution §XI; Plan §Các giai đoạn triển khai và tiêu chí ra giai đoạn]

  **Bằng chứng reviewer — Đạt:** [Constitution](../../../.specify/memory/constitution.md) XI và [Spec](../spec.md) FR-086/FR-087 đòi README/architecture/API/Excel/troubleshooting, startup/connections/load/staging/deploy/monitor/recovery/secrets/limits và cập nhật đồng thời thay đổi nghiệp vụ/API/schema. [Tasks](../tasks.md) T014 có README bootstrap; docs đi cùng từng story; T150/T151 bàn giao docs/sample đồng bộ, không trì hoãn hướng dẫn core đến cuối.

- [x] CHK048 Quy tắc quản trị tài liệu có phân biệt chất lượng yêu cầu, trạng thái task, bằng chứng runtime và reviewer approval, đồng thời nêu cách ghi nhận/giải quyết mâu thuẫn ba tài liệu trước triển khai mà không âm thầm tạo ngoại lệ Constitution không? [Không mâu thuẫn, Truy vết; Constitution §III, §Quy trình phát triển và các cổng chất lượng, §Quản trị và sửa đổi; Plan §Kiểm tra Constitution]

  **Bằng chứng reviewer — Đạt:** [Constitution](../../../.specify/memory/constitution.md) III/X/§Quy trình phát triển và các cổng chất lượng/§Quản trị và sửa đổi đặt nguồn thẩm quyền, dừng phần xung đột và sửa đúng tài liệu, không âm thầm nới nguyên tắc. [Plan](../plan.md) §Kiểm tra Constitution/§Kết quả rà soát có mục tiêu ngày 2026-11-08 và bàn giao Tasks và [Tasks](../tasks.md) §Ghi chú quản trị tách design Đạt, runtime evidence, task completion và reviewer approval; không cho implement tự đổi checkbox. Lượt reviewer này có ủy quyền trực tiếp của chủ dự án, chỉ đánh giá yêu cầu/thiết kế.


## Ghi chú sử dụng

- Đây là checklist chất lượng yêu cầu, không thay thế test case, test plan hoặc kiểm thử implementation.
- Reviewer ghi bằng chứng tham chiếu, điểm mơ hồ, mâu thuẫn hoặc phần cần bổ sung ngay dưới CHK tương ứng. Mục chưa rõ hoặc chưa được reviewer đánh giá vẫn giữ `[ ]`.
- Với mục không áp dụng, ghi lý do và phạm vi; không dùng “không áp dụng” để bỏ yêu cầu bắt buộc thuộc MVP.
- Các yêu cầu an toàn dữ liệu, retry/rerun, FULL_REFRESH recovery, cleanup, đăng ký DAG, đối soát dữ liệu và one-command startup là trọng tâm rủi ro, không được thay bằng nhận xét chung “hoạt động đúng”.
- `/speckit-implement` đọc trạng thái checklist như cổng chất lượng nhưng không được sửa dấu checkbox.
- [requirements.md](requirements.md) là checklist chất lượng đặc tả tích hợp sẵn do `/speckit-specify` và `/speckit-clarify` quản lý; không áp dụng vòng đời đó cho checklist reviewer này.
- Lịch sử: chưa có `tasks.md` tại thời điểm tạo checklist; lượt reviewer2026-11-08 đã đối chiếu bản152task hiện hành, không coi task dự kiến là kết quả thực thi.
- Checklist ban đầu có48mục chưa đánh giá; kết quả reviewer hiện hành và giới hạn được ghi dưới đây.

## Kết quả reviewer ngày 2026-11-08

- Đã đánh giá48/48mục: **48đạt, 0chưa đạt, 0chưa đánh giá, 0không áp dụng**. Mỗi mục có
  bằng chứng về quy tắc, hành vi hoặc điều kiện nghiệm thu cụ thể; không đánh dấu chỉ vì
  tài liệu tồn tại, task nhắc requirement hoặc Analyze không còn HIGH/CRITICAL.
- Không còn blocker chất lượng yêu cầu/thiết kế trong48tiêu chí để bắt đầu Phase1
  **T001–T014**, khi điều kiện Linux containers/runtime-provider đã công bố/cổng/quyền pull-build
  của Plan/Tasks được kiểm thực tế. Môi trường và dependency compatibility chưa được xác minh.
- Phase1 là bootstrap: backend liveness, DB/Airflow readiness thật và runner smoke. Product
  readiness hoàn thiện T030/T034; workflow mẫu/US1 đầy đủ nghiệm thu T140/T152. Không tuyên bố
  MVP hoặc bất kỳ story nào hoàn thành từ kết quả checklist này.
- Các quy tắc private root/public alias, ONCE reservation/admission/revoke, allow_empty,
  final-marker recovery và protected artifacts đã rõ trong thiết kế; chứng minh runtime
  đúng là công việc test implementation tương ứng, hiện **NOT_RUN**.
- CSV/TXT mẫu trong checkout Windows hiện còn CRLF, khác raw hash lịch sử LF. Thiết kế
  đã chốt `.gitattributes`/raw-byte checks tại T001/T014/T030, không normalize upload.
  Đây là đầu ra implementation phải thực hiện/kiểm chứng, không ghi sample hash hiện tại đạt.
- Ghi chú ngoài phạm vi chỉnh sửa: [requirements.md](requirements.md) vẫn thống kê
  87FR/14BR/12SC/A–Z trong khi Spec hiện có100FR/22BR/15SC/A–AM. Chủ sở hữu Specify/Clarify
  cần cập nhật ghi chú và đánh giá phạm vi bổ sung;16checkbox cũ không được diễn giải thành
  bằng chứng đã rà soát lại các thay đổi. Không sửa file đó hoặc suy ra runtime PASS.
- Hướng tiếp theo: triển khai có giới hạn Phase1 T001–T014, tuân dependency/test/kiểm chứng;
  chỉ đánh task hoàn thành khi đầu ra và tiêu chí thực đạt. Không bỏ mandatory test hoặc
  thay mock/HTTP200/container running cho integration/readiness/data reconciliation.

## Rà soát thiết kế sau sửa đổi Podman đã duyệt — 2026-11-08

Chủ dự án đã duyệt bản sửa Constitution1.1.0; đối chiếu lại các tiêu chí bị ảnh hưởng trên
Spec/Plan/Tasks/Quickstart hiện hành. Giữ nguyên48marker reviewer và quyền sở hữu checklist,
không đánh task hoặc tuyên bố compatibility/runtime PASS từ kết quả này.

| Mục | Bằng chứng bổ sung và kết luận chất lượng thiết kế |
| --- | --- |
| CHK003 | [Plan](../plan.md) §Baseline Podman đã duyệt và [Tasks](../tasks.md) §Đồng bộ Podman giữ8phase/dependency/runner sớm, không nới gate hoặc bỏ P2. Đạt. |
| CHK031–CHK033 | [Constitution](../../../.specify/memory/constitution.md) IX, [Spec](../spec.md) US-01/FR-081/AS-02 và [Quickstart](../quickstart.md) §Runtime và Compose provider thống nhất canonical Podman, Docker alternative phải công bố/nghiệm thu riêng. T011–T014/T140 giữ one-command/init/readiness/persistence và actual limits; engine setup là đầu vào, không app setup ngầm. Đạt. |
| CHK034 | [Plan](../plan.md) §Baseline Podman đã duyệt giữ cùng topology/wheel/Airflow authority, không đổi engine thành scheduler hoặc mock. Đạt. |
| CHK040/CHK042 | [Plan](../plan.md) §Thiết kế Compose và runtime container/§Baseline Podman đã duyệt giữ secret domains, RO mounts, UID/GID/least privilege, loopback/private guards; engine rootful không cho privileged hoặc mở API TCP không xác thực. Đạt. |
| CHK045 | [Tasks](../tasks.md) T002/T005/T011–T014/T140/T152 đòi Linux install/pip check, actual provider semantics/resource enforcement và evidence client/server/provider; không lấy version/help thay tests hoặc suy Docker-tested từ Podman. Đạt. |
| CHK048 | [Constitution](../../../.specify/memory/constitution.md) §Quản trị và sửa đổi và [bản duyệt](../../../docs/proposals/podman-support.md) ghi version1.1.0, giữ ngày thông qua, có ủy quyền trước áp dụng. Không tạo ngoại lệ ngầm hoặc đổi BR-08. Đạt. |

Kết luận vẫn48/48đạt về chất lượng yêu cầu/thiết kế. Có thể tiếp tục Phase1 từ T002 và
nhánh T005 theo dependency sau preflight runtime; engine/provider đã phản hồi nhưng stack
compatibility, build, readiness, persistence và recovery vẫn chưa nghiệm thu. Các nhận định
thiếu Docker ở lượt implementation cũ là lịch sử; không reset task hoặc sửa báo cáo cũ.
`requirements.md` vẫn thuộc Specify/Clarify, phần thống kê lịch sử chưa được sửa trong lượt này.
