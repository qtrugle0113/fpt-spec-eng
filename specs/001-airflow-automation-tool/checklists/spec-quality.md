# Checklist chất lượng đặc tả: Airflow Automation Tool

**Mục đích**: Đánh giá mức độ đầy đủ, rõ ràng, nhất quán, không mâu thuẫn, có thể kiểm thử và có thể triển khai của yêu cầu; không kiểm tra implementation.
**Ngày tạo**: 2026-11-06
**Tính năng**: [Đặc tả](../spec.md)
**Cơ sở đối chiếu**: [Constitution 1.0.0](../../../.specify/memory/constitution.md), [Specification](../spec.md), [Implementation Plan](../plan.md).
**Độ sâu**: Rà soát toàn diện theo rủi ro, bao phủ 16 nhóm được yêu cầu.
**Người sử dụng và thời điểm**: Reviewer rà soát tài liệu trước phân rã task và triển khai.

**Ghi chú**: Checklist được tạo bằng `/speckit-checklist`; các mục là câu hỏi về nội dung yêu cầu đã viết, không phải thủ tục kiểm thử sản phẩm.
**Quyền đánh giá**: Reviewer sở hữu checklist. Chỉ reviewer mới quyết định đánh dấu `[x]` khi tiêu chí chất lượng yêu cầu đã được đáp ứng.
**Ý nghĩa trạng thái**: `[x]` không có nghĩa implementation hoàn thành. Toàn bộ mục mới giữ `[ ]`; chưa có kết luận đạt/chưa đạt.
**Cách tổ chức**: Nhóm theo 16 miền nghiệp vụ; nhãn trong từng mục chỉ chiều chất lượng: đầy đủ, rõ ràng, nhất quán, khả năng đo lường, bao phủ, khả thi, phụ thuộc hoặc mâu thuẫn.
**Truy vết**: `Spec §FR/BR/NFR/SC/US/AS` chỉ mã trong đặc tả; `Plan §` chỉ heading trong kế hoạch; `Constitution §` chỉ nguyên tắc. `Gap` chỉ câu hỏi về khoảng trống cần reviewer rà soát, không khẳng định tài liệu đang thiếu.

## 1. Phạm vi sản phẩm và câu chuyện người dùng

- [ ] CHK001 Phạm vi MVP có nêu rõ một operator local, sáu màn hình, tám hướng ETL, một source/target mỗi DAG và các phần ngoài phạm vi, nhất quán giữa ba tài liệu không? [Đầy đủ, Nhất quán; Spec §FR-001, §FR-002, §AS-01, §AS-03, §Ngoài phạm vi MVP; Plan §Bối cảnh kỹ thuật; Constitution §II, §XII]
- [ ] CHK002 Mỗi US-01 đến US-11 có mục tiêu, ưu tiên, điều kiện tiên quyết và tiêu chí chấp nhận với kết quả quan sát được, bao gồm luồng chính, luồng thay thế và lỗi liên quan không? [Bao phủ, Chất lượng tiêu chí chấp nhận; Spec §US-01–US-11, §Các trường hợp biên, §Phân bổ phạm vi nghiệm thu theo câu chuyện]
- [ ] CHK003 Phân kỳ trong Plan có đầu ra, phụ thuộc và cổng nghiệm thu truy vết đến yêu cầu, không bỏ chức năng P2 thuộc MVP hoặc trì hoãn validation/bảo mật của chức năng lõi không? [Khả thi, Nhất quán; Plan §Các giai đoạn triển khai và tiêu chí ra giai đoạn; Spec §Kịch bản người dùng và kiểm thử, §AS-09; Constitution §III, §XII]

## 2. Dashboard và metadata Airflow

- [ ] CHK004 Tài liệu có phân biệt metadata cấu hình của ứng dụng, metadata điều phối của Airflow và dữ liệu ETL, xác định nguồn có thẩm quyền cho lịch sử/trạng thái và cấm nghiệp vụ đọc bảng nội bộ Airflow không? [Rõ ràng, Nhất quán; Spec §FR-064, §FR-078, §FR-082; Plan §Tóm tắt, §Kiến trúc module và hướng dependency; Constitution §VIII, §Ràng buộc kiến trúc và phạm vi sản phẩm]
- [ ] CHK005 Các KPI, công thức Success Rate, nhóm lịch, phạm vi managed/external, phân trang, timezone và số liệu lifetime/date-filtered có định nghĩa đủ cụ thể để đối chiếu khách quan không? [Rõ ràng, Khả năng đo lường; Spec §FR-071–FR-077, §BR-11, §BR-12, §SC-008]
- [ ] CHK006 Yêu cầu có phân biệt dữ liệu rỗng thật, thiếu, chưa đầy đủ, cũ và không khả dụng khi Airflow mất liên lạc, kể cả metrics external DAG, thay vì quy thành 0 hoặc success không? [Bao phủ ngoại lệ, Nhất quán; Spec §FR-065, §FR-072, §FR-077, §FR-078, §FR-096; Plan §Frontend UI/UX]

## 3. Quản lý connection

- [ ] CHK007 Schema connection, quy tắc unique/trim/case, trường bắt buộc, miền port, vai trò source/target và kết quả kiểm tra kết nối thật có được định nghĩa nhất quán cho PostgreSQL/MySQL không? [Đầy đủ, Rõ ràng; Spec §FR-003–FR-007, §BR-01, §US-02]
- [ ] CHK008 Yêu cầu sửa/xóa connection có làm rõ dependency, revision, thay vị trí DB, thay credential, validation/xác nhận lại và revision bất biến của run đã bắt đầu không? [Bao phủ, Không mâu thuẫn; Spec §FR-008, §FR-009, §BR-21; Plan §Connections, Excel và DDL]
- [ ] CHK009 Tiêu chí chấp nhận có nêu timeout hữu hạn, nhóm lỗi kết nối, giới hạn phân loại lỗi và quy tắc secret mới/bỏ trống/không đọc password cũ, thay vì chỉ yêu cầu “kết nối thành công” không? [Chất lượng tiêu chí chấp nhận, Rõ ràng; Spec §US-02, §FR-007–FR-009, §NFR-009; Constitution §IV, §VI]

## 4. Quản lý file nguồn

- [ ] CHK010 Hợp đồng CSV/TXT có định nghĩa encoding, delimiter, header, quote/escape, NULL, chuỗi rỗng, BOM và tên cột không header, đồng thời bảo đảm preview và ETL dùng cùng cấu hình được xác nhận không? [Đầy đủ, Nhất quán; Spec §FR-011, §FR-015, §FR-017, §FR-092, §AS-06]
- [ ] CHK011 Yêu cầu có phân biệt preview tối đa 100 dòng với validation toàn file, đồng thời mô tả lỗi header trùng/rỗng, encoding, quote, số trường và vị trí physical line/record nhiều dòng không? [Bao phủ biên, Rõ ràng; Spec §FR-014, §FR-092, §US-03]
- [ ] CHK012 Vòng đời file có định nghĩa reference gắn đúng nội dung, upload chưa hoàn tất, persistence, retention/dependency và nguồn thiếu/quá hạn phải fail thay vì trở thành dataset rỗng không? [Đầy đủ, An toàn dữ liệu; Spec §FR-012, §FR-013, §FR-016, §US-03; Constitution §VII, §IX]

## 5. Table Definition và SQL DDL

- [ ] CHK013 Schema workbook Table Definition có quy định version, sheet/header, required/optional, liên kết Tables/Columns, định danh ghép, dòng trống và duplicate/orphan đủ để tác giả không phải tự suy đoán không? [Đầy đủ, Rõ ràng; Spec §FR-018–FR-023, §FR-098, §BR-22; Plan §Connections, Excel và DDL]
- [ ] CHK014 Yêu cầu kiểu dữ liệu, length/precision/scale, nullable/default, khóa ghép và SQL preview có nhất quán theo hai dialect, không chấp nhận chuyển kiểu mất dữ liệu hoặc biểu thức SQL tùy ý không? [Nhất quán, Khả thi; Spec §FR-023–FR-025, §NFR-003; Constitution §V, §VI]
- [ ] CHK015 Yêu cầu có phân biệt validation toàn workbook không side effect với DDL runtime có thể thành công từng table, nêu rõ xác nhận/revalidation, table tồn tại và giới hạn transaction MySQL mà không hứa rollback toàn workbook không? [Không mâu thuẫn, Bao phủ lỗi; Spec §FR-026–FR-028, §BR-02, §BR-03, §BR-06; Plan §Connections, Excel và DDL]

## 6. ETL Definition và column mapping

- [ ] CHK016 ETL Definition có định nghĩa nguồn DB/file loại trừ nhau, reference hợp lệ, target phải tồn tại, nhiều DAG trong workbook và mapping liên kết đúng DAG, không ngầm tạo target hoặc bổ sung nguồn thứ hai không? [Đầy đủ, Nhất quán; Spec §FR-030–FR-033, §FR-042, §FR-098, §AS-03]
- [ ] CHK017 Quy tắc mapping tường minh/implicit có rõ điều kiện enabled, tên cột chính xác, cột dư, target thiếu, nullable/default, mapping trùng và trường hợp mơ hồ phải bị từ chối không? [Rõ ràng, Bao phủ biên; Spec §FR-044–FR-046, §BR-05; Spec §Ma trận nghiệm thu bắt buộc, mục AL]
- [ ] CHK018 Danh mục transformation/filter có phạm vi, quy tắc NULL/giá trị falsy/conversion và tiêu chí bảo toàn Unicode/decimal/temporal, đồng thời yêu cầu lỗi và revalidation khi schema drift thay vì sửa mapping ngầm không? [Khả thi, Khả năng đo lường; Spec §FR-043, §FR-046–FR-048, §FR-091, §SC-015; Plan §Engine, type và load]

## 7. Sinh và triển khai DAG

- [ ] CHK019 Tiêu chí deployment thành công có yêu cầu bằng chứng Airflow parse và đăng ký đúng DAG ID cùng revision, tách khỏi ghi file thành công, DAG cũ tồn tại và execution thành công không? [Rõ ràng, Chất lượng tiêu chí chấp nhận; Spec §FR-035, §FR-038, §SC-009; Constitution §VIII]
- [ ] CHK020 Yêu cầu có phân biệt pending, parse error, timeout/API unavailable và kết quả chưa xác định trong hạn 120 giây, với identity và đối soát trước retry thay vì báo thất bại/thành công không có bằng chứng không? [Bao phủ ngoại lệ, Khả năng đo lường; Spec §FR-039, §FR-041, §FR-096; Plan §DAG và Airflow]
- [ ] CHK021 Quy tắc cron/manual, UTC/IANA/DST, catchup, DAG mới paused, activation riêng, external ownership và redeploy có chốt revision/drain run/xác nhận lại đủ để tránh xung đột lịch và quyền ghi dữ liệu không? [Đầy đủ, Nhất quán; Spec §FR-034, §FR-036, §FR-037, §FR-097, §BR-04, §BR-20; Plan §DAG và Airflow]

## 8. APPEND, UPSERT và FULL_REFRESH

- [ ] CHK022 APPEND có định nghĩa rõ chỉ insert, giữ dữ liệu cũ, nguy cơ duplicate khi rerun mới, unique violation và điều kiện retry chỉ tiếp tục batch chưa commit trên dataset bất biến không? [Rõ ràng, Bao phủ; Spec §FR-050, §FR-051, §BR-07, §SC-005]
- [ ] CHK023 UPSERT có yêu cầu conflict key khớp trọn khóa thật, xử lý khóa ghép/NULL/duplicate theo target, xung đột unique key khác và không tự ALTER/index/downgrade APPEND, với tiêu chí rerun đo bằng key/giá trị không? [Đầy đủ, Chất lượng tiêu chí chấp nhận; Spec §FR-052, §BR-07, §BR-15, §SC-005]
- [ ] CHK024 FULL_REFRESH có định nghĩa ủy quyền đúng target/scope/revision/lịch, quyền zero-row riêng, chuẩn bị toàn dataset trước thay thế, một commit công bố atomic và giới hạn isolation/dependency, không TRUNCATE rồi commit batch không? [An toàn dữ liệu, Không mâu thuẫn; Spec §FR-053, §FR-054, §BR-06, §BR-08, §BR-15; Constitution §VI; Plan §Engine, type và load]

## 9. Toàn vẹn dữ liệu và phục hồi lỗi

- [ ] CHK025 Yêu cầu chống mất dữ liệu có chỉ rõ hậu điều kiện khi extraction/validation thất bại, lỗi giữa batch và lỗi công bố FULL_REFRESH, bao gồm giữ/phục hồi target cũ và không suy lỗi nguồn thành empty dataset không? [Đầy đủ, Bao phủ phục hồi; Spec §FR-053–FR-055, §FR-060, §SC-006, §SC-013; Constitution §VI]
- [ ] CHK026 Retry/rerun có phân biệt logical run mới/cũ, dataset identity, tiến độ commit bền, commit mất phản hồi, worker kill và recovery không tự hoàn tất, với điều kiện dừng/đối soát/can thiệp và giới hạn retry rõ ràng không? [Rõ ràng, Khả thi; Spec §FR-051, §FR-054, §FR-089, §FR-095, §BR-07, §SC-014; Plan §Engine, type và load]
- [ ] CHK027 Yêu cầu ghi đồng thời có xác định physical target kể cả connection alias, quyền ghi độc quyền, timeout 300 giây, chủ sở hữu chưa rõ và giả định không có writer ngoài, nhất quán cho cả ba strategy không? [Phụ thuộc, Nhất quán; Spec §BR-09, §SC-014; Plan §Engine, type và load; Constitution §VII]

## 10. Dữ liệu lớn và staging trên đĩa

- [ ] CHK028 Yêu cầu có lượng hóa RAM, quota disk/upload, byte cap từng dòng/chunk, free-space reserve, parallelism và chunk/batch riêng, với tiêu chí dataset lớn hơn hai lần RAM và ít nhất 20 batch không? [Khả năng đo lường, Khả thi; Spec §FR-088, §FR-094, §NFR-004, §SC-007; Plan §Bối cảnh kỹ thuật, §Chiến lược kiểm thử và bằng chứng]
- [ ] CHK029 Hợp đồng DB-to-DB staging có xác định disk thật, snapshot nhất quán, namespace DAG/Run/attempt, manifest/checksum/schema revision và điều kiện complete trước target load, không fallback RAM/tmpfs/XCom dataset không? [Đầy đủ, Nhất quán; Spec §FR-055, §FR-057, §FR-058, §FR-089, §FR-090; Plan §Engine, type và load; Constitution §VII]
- [ ] CHK030 Cleanup policy có quy định thời gian lưu theo trạng thái, lịch/điều kiện dọn, artifact active/retry/recovery/commit chưa rõ cần bảo vệ, đối soát orphan sau restart và phản hồi lỗi disk full/I/O/checksum/quyền truy cập không? [Bao phủ phục hồi, Rõ ràng; Spec §FR-061, §FR-094, §FR-095, §FR-100; Plan §Engine, type và load; Constitution §VII]

## 11. Docker Compose và khởi tạo tự động

- [ ] CHK031 Tiêu chí one-command startup có nêu đúng lệnh `docker compose up --build -d`, điều kiện đầu vào, đầy đủ services, init/migration/seed tự động và readiness chức năng thật, không đòi bước cấu hình thủ công sau khởi động không? [Chất lượng tiêu chí chấp nhận, Đầy đủ; Spec §US-01, §FR-081, §FR-099, §SC-001; Plan §Thiết kế Docker Compose; Constitution §IX]
- [ ] CHK032 Yêu cầu restart có bao phủ initialization idempotent, sample namespace riêng, persistent volumes/secret key, migration lỗi không reset dữ liệu và recovery giữa extraction/batch commit/FULL_REFRESH không? [Bao phủ phục hồi, Nhất quán; Spec §FR-083, §FR-100; Spec §Ma trận nghiệm thu bắt buộc, mục AM; Constitution §IX]
- [ ] CHK033 Plan có xác định phụ thuộc startup, health/liveness/readiness, quyền volume, loopback ports và phân biệt hostname nội bộ với URL browser, phù hợp giả định Docker/OS/cổng của Specification không? [Khả thi, Phụ thuộc; Spec §FR-070, §FR-099, §AS-01, §AS-02; Plan §Thiết kế Docker Compose, §Bối cảnh kỹ thuật]

## 12. Tích hợp Backend/API

- [ ] CHK034 Ranh giới UI → Backend → DB/Airflow có xác định authority validation, metadata repository, worker công việc nền và Airflow là nơi duy nhất điều phối/thực thi ETL, không mock hoặc scheduler thay thế không? [Nhất quán, Khả thi; Spec §NFR-008; Plan §Kiến trúc module và hướng dependency, §Backend API và công việc nền; Constitution §IV, §VIII]
- [ ] CHK035 Hợp đồng API được Plan tham chiếu có quy định request/response, validation/error location, status tác vụ dài, timeout và trạng thái kết quả chưa rõ, truy vết được sang nghiệp vụ mà không chỉ liệt kê endpoint không? [Đầy đủ, Rõ ràng; Plan §Backend API và công việc nền; Spec §FR-020, §FR-035, §FR-060, §FR-096, §NFR-006]
- [ ] CHK036 Quy tắc idempotency, stale edit/confirmation, revision dependency, operation recovery và đồng bộ contract có được tài liệu hóa đủ để tránh gửi lặp, lost update hoặc phản hồi success trước side effect được xác minh không? [Bao phủ, Không mâu thuẫn; Spec §BR-02, §FR-041, §FR-067, §FR-096, §FR-097; Plan §Backend API và công việc nền]

## 13. Trải nghiệm Frontend và ngôn ngữ UI

- [ ] CHK037 Yêu cầu cho sáu màn hình có mô tả workflow, preview/xác nhận phạm vi dữ liệu, tiến độ và trạng thái empty/loading/error/stale/partial/unknown, giúp phân biệt tiếp nhận tác vụ với kết quả nghiệp vụ không? [Đầy đủ, Nhất quán; Spec §FR-002, §FR-022, §FR-029, §FR-067, §FR-072, §NFR-002; Plan §Frontend UI/UX]
- [ ] CHK038 Các từ “responsive”, “trực quan” và “nhất quán” có được cụ thể hóa bằng tiêu chí 1440/390 px, hành động chính không bị che, vùng cuộn bảng, label/lỗi trường và khả năng dùng bàn phím không? [Rõ ràng, Khả năng đo lường; Spec §NFR-002, §SC-002; Plan §Frontend UI/UX; Constitution §II]
- [ ] CHK039 Yêu cầu ngôn ngữ có bao phủ toàn bộ nội dung UI bằng tiếng Anh, kể cả validation/notification/tooltip/empty state và ánh xạ lỗi phụ thuộc, trong khi tên ứng dụng/branding phù hợp Constitution không? [Đầy đủ, Nhất quán; Spec §FR-086, §NFR-001; Constitution §I, §II; Plan §Frontend UI/UX]

## 14. Bảo mật

- [ ] CHK040 Yêu cầu bảo vệ credential có xác định mã hóa và khóa tách biệt/bền, quyền truy cập, password write-only và các bề mặt cấm DB plaintext/DAG/API/log/XCom, với tiêu chí nghiệm thu không rò secret không? [Đầy đủ, Chất lượng tiêu chí chấp nhận; Spec §FR-009, §FR-100, §NFR-003, §SC-011; Constitution §VI; Plan §Thiết kế Docker Compose]
- [ ] CHK041 Yêu cầu đầu vào không tin cậy có bao phủ SQL identifiers/values, Python/formula/macro/external link, upload path và giới hạn workbook/network, đồng thời nêu kết quả từ chối trước side effect và không để lỗi công khai lộ dữ liệu nhạy cảm không? [Bao phủ ngoại lệ, Khả thi; Spec §FR-013, §FR-019, §FR-020, §NFR-003; Plan §Connections, Excel và DDL, §Backend API và công việc nền; Constitution §V, §VI]
- [ ] CHK042 Phạm vi “local không login” có được phân biệt với xác thực service/runtime, kiểm soát origin/mutation, quyền DB/volume và giới hạn chưa hỗ trợ Internet, không bị diễn giải thành bỏ toàn bộ bảo mật không? [Giả định, Không mâu thuẫn; Spec §AS-01; Plan §Thiết kế Docker Compose, §Backend API và công việc nền; Constitution §IV, §VI]

## 15. Kiểm thử và tiêu chí chấp nhận

- [ ] CHK043 Ma trận nghiệm thu có bao phủ đủ PostgreSQL → PostgreSQL, MySQL → MySQL, PostgreSQL → MySQL, MySQL → PostgreSQL, CSV/TXT → cả hai DB, với expected count/giá trị/key/NULL và ít nhất một execution Airflow thật cho mỗi hướng không? [Đầy đủ, Chất lượng tiêu chí chấp nhận; Spec §FR-001, §SC-003, §SC-009; Spec §Ma trận nghiệm thu bắt buộc, mục C–H, U; Plan §Chiến lược kiểm thử và bằng chứng]
- [ ] CHK044 Tiêu chí “dữ liệu thực sự được chuyển” có yêu cầu đối soát dataset sau filter/mapping với target theo từng strategy, phân biệt source rows với affected rows và thành công DAG với thành công dữ liệu không? [Khả năng đo lường, Rõ ràng; Spec §FR-062, §FR-093, §BR-18, §SC-003; Spec §Ma trận nghiệm thu bắt buộc, mục AG]
- [ ] CHK045 Yêu cầu bằng chứng có bao phủ unit/integration/E2E thật, lỗi/retry/rerun/recovery/stress/startup, mã truy vết A–AM, fixture/môi trường/lệnh/expected-actual và trạng thái NOT_RUN/BLOCKED, không coi mock hoặc đánh giá thiết kế “Đạt” là runtime PASS không? [Đầy đủ, Không mâu thuẫn; Spec §FR-085, §SC-012; Plan §Kiểm tra Constitution, §Chiến lược kiểm thử và bằng chứng; Constitution §X]

## 16. Quy tắc tài liệu Markdown tiếng Việt

- [ ] CHK046 Quy định Markdown tiếng Việt có bao phủ heading, user story, acceptance criteria, checklist, kiến trúc/vận hành/báo cáo, đồng thời phân biệt ngoại lệ thuật ngữ/code/path/chuỗi UI và Excel trích dẫn bằng tiếng Anh không? [Rõ ràng, Nhất quán; Spec §FR-086, §NFR-001; Constitution §I]
- [ ] CHK047 Yêu cầu bàn giao tài liệu có bao phủ README, API, schema Excel, startup, cấu hình, load/staging/recovery/troubleshooting và cơ chế cập nhật đồng bộ khi nghiệp vụ/API/schema thay đổi không? [Đầy đủ, Khả thi; Spec §FR-086, §FR-087; Constitution §XI; Plan §Các giai đoạn triển khai và tiêu chí ra giai đoạn]
- [ ] CHK048 Quy tắc quản trị tài liệu có phân biệt chất lượng yêu cầu, trạng thái task, bằng chứng runtime và reviewer approval, đồng thời nêu cách ghi nhận/giải quyết mâu thuẫn ba tài liệu trước triển khai mà không âm thầm tạo ngoại lệ Constitution không? [Không mâu thuẫn, Truy vết; Constitution §III, §Quy trình phát triển và các cổng chất lượng, §Quản trị và sửa đổi; Plan §Kiểm tra Constitution]

## Ghi chú sử dụng

- Đây là checklist chất lượng yêu cầu, không thay thế test case, test plan hoặc kiểm thử implementation.
- Reviewer ghi bằng chứng tham chiếu, điểm mơ hồ, mâu thuẫn hoặc phần cần bổ sung ngay dưới CHK tương ứng. Mục chưa rõ hoặc chưa được reviewer đánh giá vẫn giữ `[ ]`.
- Với mục không áp dụng, ghi lý do và phạm vi; không dùng “không áp dụng” để bỏ yêu cầu bắt buộc thuộc MVP.
- Các yêu cầu an toàn dữ liệu, retry/rerun, FULL_REFRESH recovery, cleanup, đăng ký DAG, đối soát dữ liệu và one-command startup là trọng tâm rủi ro, không được thay bằng nhận xét chung “hoạt động đúng”.
- `/speckit-implement` đọc trạng thái checklist như cổng chất lượng nhưng không được sửa dấu checkbox.
- [requirements.md](requirements.md) là checklist chất lượng đặc tả tích hợp sẵn do `/speckit-specify` và `/speckit-clarify` quản lý; không áp dụng vòng đời đó cho checklist reviewer này.
- Chưa có `tasks.md` tại thời điểm tạo; checklist không suy diễn task hoặc tuyên bố triển khai hoàn thành.
- Checklist này tạo mới 48 mục CHK001–CHK048, chưa đánh giá kết quả của bất kỳ mục nào.
