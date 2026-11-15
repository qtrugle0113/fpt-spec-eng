# Spec Kit — Question & Answer về các điểm cần làm rõ

Ngày tổng hợp: 2026-11-15.

Tài liệu phục vụ assignment: liệt kê các điểm cần xác định khi phát triển dự án, gồm câu hỏi có bản ghi Q/A và các lựa chọn đã được giải quyết bằng mặc định hoặc quyết định thiết kế khi người dùng giao quyền cho AI. Answer chứa luôn phương án đã chọn.

**Cách đọc và thống kê:** Có 70 mục: 5 mục có bản ghi Q/A trong spec (Q21–Q25), 65 mục được biên soạn lại thành câu hỏi từ quyết định, giả định và phạm vi đã lưu. Đây là danh sách tổng hợp tài liệu, không phải bản chép hội thoại hoặc bằng chứng đã hỏi người dùng 70 câu. Các mục tái dựng không chứng minh yêu cầu ban đầu thiếu thông tin ở mọi điểm, cũng không khẳng định mọi quyết định đều do AI tự nghĩ ra. Nhãn nguồn cho phép đối chiếu. Không gộp các mục này thành chỉ số “số câu hỏi thực tế đã hỏi qua /speckit-clarify”.

Phạm vi gồm feature 001–004. Answer phản ánh tài liệu nguồn theo từng feature; không tự xác nhận code đã triển khai hoặc kiểm thử thành công. Không bao gồm toàn bộ lịch sử phê duyệt remediation/security và không thay thế các approval riêng đó.

## A. Các mặc định được ghi nhận khi người dùng ủy quyền — feature 001

Nguồn: [spec 001 — Các nội dung đã làm rõ](../specs/001-airflow-automation-tool/spec.md#các-nội-dung-đã-làm-rõ). Q01–Q20 tách từ bảng nhóm quyết định 1–20; câu hỏi được tái dựng, Answer tóm tắt kết luận đã lưu.

### Q01
**Question:** Công cụ phục vụ một người dùng local hay nhiều người? Có cần đăng nhập ứng dụng không?

**Answer:** Chọn một operator local tin cậy, không yêu cầu login hoặc phân quyền nhiều người. Phạm vi mặc định là loopback; credential của DB và Airflow vẫn cần thiết. Tham chiếu AS-01.

### Q02
**Question:** Có cần tạo riêng connection cho source và target không?

**Answer:** Một connection có thể dùng cho cả source và target. Tham chiếu FR-003.

### Q03
**Question:** Một Table Definition có được mô tả nhiều table không?

**Answer:** Có, một file có thể chứa nhiều table. Tham chiếu FR-021–FR-023.

### Q04
**Question:** Một ETL Definition có được khai báo nhiều DAG không?

**Answer:** Có, một file có thể mô tả nhiều DAG. Tham chiếu FR-030.

### Q05
**Question:** Mapping cột được khai báo ở đâu trong ETL Definition?

**Answer:** Mapping được khai báo cùng sheet theo schema đã chọn. Tham chiếu FR-042.

### Q06
**Question:** Nếu không có mapping enabled, hệ thống xử lý cột thế nào?

**Answer:** Dùng implicit mapping theo tên chính xác và kiểu dữ liệu tương thích. Tham chiếu FR-044.

### Q07
**Question:** DAG mới tạo có được tự chạy ngay không?

**Answer:** DAG mới mặc định paused. Tham chiếu FR-034.

### Q08
**Question:** Hỗ trợ những cách kích hoạt DAG nào?

**Answer:** Hỗ trợ cron và chạy thủ công theo các điều kiện nghiệp vụ tương ứng. Tham chiếu FR-037, BR-04 và BR-20.

### Q09
**Question:** Có tự chạy bù các kỳ lịch quá khứ không?

**Answer:** Không; mặc định Catchup false. Tham chiếu BR-04 và BR-20.

### Q10
**Question:** Khi table đã tồn tại, có tự xóa hoặc sửa cấu trúc để khớp Definition không?

**Answer:** Không tự DROP hoặc ALTER table hiện hữu. Tham chiếu FR-027.

### Q11
**Question:** APPEND có bảo đảm loại bỏ dữ liệu trùng khi chạy lại không?

**Answer:** Không. APPEND có thể tạo dữ liệu trùng; không mặc định coi đây là cơ chế deduplication. Tham chiếu FR-050–FR-054 và BR-15.

### Q12
**Question:** UPSERT có thể chạy nếu target chưa có khóa phù hợp không?

**Answer:** Không. Phải có key thật phù hợp; thiếu key thì chặn, không tự ALTER target để thêm khóa. Tham chiếu FR-050–FR-054 và BR-15.

### Q13
**Question:** FULL_REFRESH phải xử lý thế nào để tránh mất dữ liệu hoặc phục hồi sai?

**Answer:** Hoàn tất extraction và validation trước khi thay target; replacement phải atomic và có recovery. Extraction thất bại không được động target; không TRUNCATE rồi commit từng batch. Tham chiếu FR-053–FR-054 và BR-15.

### Q14
**Question:** TXT được hiểu là dữ liệu theo định dạng nào?

**Answer:** TXT dạng delimited; delimiter phải được xác nhận trong parser. Tham chiếu FR-001 và AS-06.

### Q15
**Question:** Người dùng có được nhập code tùy ý trong Definition không?

**Answer:** Không cho chạy code tùy ý từ Definition. Tham chiếu FR-019.

### Q16
**Question:** DB-to-DB có giữ toàn bộ dữ liệu trong RAM không?

**Answer:** Không; dùng disk staging và xử lý theo chunk/batch để giới hạn bộ nhớ. Tham chiếu FR-055–FR-058.

### Q17
**Question:** Làm sao tránh các lần chạy dùng lẫn artifact staging?

**Answer:** Mỗi run có Run ID và đường dẫn staging riêng; thiết kế kỹ thuật tiếp tục tách theo attempt. Tham chiếu FR-055–FR-058 và research mục 5.

### Q18
**Question:** Có được ghi đè DAG khi redeploy mà không kiểm tra hoặc xác nhận không?

**Answer:** Không; redeploy phải có kiểm tra và xác nhận. Tham chiếu FR-036 và FR-097.

### Q19
**Question:** UI và tài liệu dùng ngôn ngữ nào?

**Answer:** UI tiếng Anh, tài liệu Markdown tiếng Việt. Tham chiếu NFR-001.

### Q20
**Question:** Có cần chờ screenshot, wireframe hoặc Excel mẫu từ người dùng mới thiết kế được không?

**Answer:** Không cần; thiết kế mới theo workflow trong phạm vi yêu cầu. Tham chiếu AS-09.

## B. Năm câu hỏi có bản ghi Q/A — feature 001

Nguồn: [spec 001](../specs/001-airflow-automation-tool/spec.md#các-nội-dung-đã-làm-rõ), năm dòng `Q: … → A: …`. Nội dung dưới đây giữ nguyên câu hỏi và câu trả lời trong bản ghi.

### Q21
**Question:** Quyền FULL_REFRESH ONCE nên được gắn cố định với một lần chạy cụ thể từ thời điểm nào?

**Answer:** Gắn độc quyền với Run ID ngay khi tiếp nhận yêu cầu chạy, trước khi tạo/khởi động run; gửi lặp cùng yêu cầu và retry dùng lại binding đó.

### Q22
**Question:** Sau khi quyền ONCE đã gắn với Run ID, nếu run thất bại hoặc bị hủy trước khi thay dữ liệu, quyền đó có được chuyển sang run mới không?

**Answer:** Không chuyển quyền; retry cùng run khi còn được phép, run mới/rerun cần ONCE mới; thành công tiêu thụ quyền, kết thúc thất bại/hủy đóng quyền, commit chưa rõ giữ chờ đối soát.

### Q23
**Question:** Quyền FULL_REFRESH SCHEDULED có cho phép chạy thủ công ngoài lịch đã xác nhận không?

**Answer:** Không; chỉ run Airflow tạo theo lịch đã xác nhận dùng SCHEDULED, manual trigger/rerun mới cần ONCE; retry cùng run định kỳ được phép khi an toàn và quyền còn hiệu lực.

### Q24
**Question:** Khi operator xác nhận allow_empty cho quyền SCHEDULED, quyền làm rỗng target có được áp dụng cho mọi run theo lịch trong cùng phạm vi không?

**Answer:** Có, chỉ sau xác nhận riêng rõ hậu quả; ONCE chỉ run đã gắn, SCHEDULED chỉ các run theo lịch trong cùng phạm vi; mặc định không cho phép, thay scope/thu hồi làm mất hiệu lực, lỗi nguồn không là dataset rỗng hợp lệ.

### Q25
**Question:** Nếu operator thu hồi quyền FULL_REFRESH khi run đã giữ quyền nhưng chưa xác định xong kết quả thay dữ liệu, hệ thống nên xử lý thế nào?

**Answer:** Thu hồi chặn run mới/retry ghi mới; nếu được ghi nhận trước điểm chấp thuận bắt đầu transaction replacement thì không thay dữ liệu; transaction đã được chấp thuận có thể hoàn tất/rollback an toàn; commit chưa rõ chỉ đối soát, không replay bằng quyền đã thu hồi; UI nêu thu hồi không đồng nghĩa hủy giao dịch đã bắt đầu.

## C. Các giả định và điểm thiết kế bổ sung — feature 001

Nguồn của Q26–Q35: [spec 001 — Giả định và mặc định](../specs/001-airflow-automation-tool/spec.md#giả-định-và-mặc-định) và phần Các nội dung đã làm rõ. Câu hỏi được tái dựng từ các kết luận đã lưu.

### Q26
**Question:** Ứng dụng có tự cài container runtime hoặc cấp quyền DB bên ngoài không?

**Answer:** Không. Operator chuẩn bị Podman/Docker, Compose provider, engine hoạt động, mạng, cổng và quyền DB. Initialization, migration và seed bên trong ứng dụng vẫn phải tự động theo thiết kế. Nguồn: AS-02.

### Q27
**Question:** Một DAG có hỗ trợ nhiều nguồn, join hoặc source và target là cùng table không?

**Answer:** MVP dùng một source và một target mỗi DAG, không join; chặn source và target cùng physical table. Nguồn: AS-03.

### Q28
**Question:** Snapshot nguồn có phải nhất quán xuyên nhiều DB hoặc nhiều DAG không?

**Answer:** Không. Một DB extraction dùng consistent snapshot của một table trong một transaction nguồn; không lấy từng chunk ở snapshot mới. Nguồn không bảo đảm snapshot thì báo lỗi rõ. Nguồn: AS-03.

### Q29
**Question:** Khi retry, có được thay dataset nguồn không?

**Answer:** Trước khi ghi target có thể extraction lại và phải ghi nhận dataset mới; sau khi đã ghi target không được đổi dataset. Nguồn: AS-03.

### Q30
**Question:** Phiên bản schema Definition ban đầu và chính sách tương thích mẫu cũ là gì?

**Answer:** Dùng schema 1.0; không cam kết tương thích mẫu cũ. Các trường và validation tuân contract; layout cell cụ thể thuộc thiết kế Plan. Nguồn: AS-04.

### Q31
**Question:** Chunk và batch có cùng khái niệm không, mặc định bao nhiêu?

**Answer:** Tách chunk extraction và batch loading; mặc định 1.000, đồng thời phải kiểm soát giới hạn byte và quota. Các mặc định không phải kết quả benchmark. Nguồn: phần làm rõ ETL và AS-05.

### Q32
**Question:** Parser file dùng encoding, delimiter, quote, header và NULL mặc định nào?

**Answer:** UTF-8; CSV dùng comma, double-quote và header true. TXT xác nhận delimiter. NULL marker là `\N` (một backslash rồi N), khác chuỗi rỗng; cho preview và chỉnh parser trước dùng. Nguồn: AS-06.

### Q33
**Question:** Ứng dụng có được trigger hoặc pause mọi DAG có trên Airflow không?

**Answer:** Chỉ điều khiển managed DAG. External DAG chỉ được xem, monitor và mở trên Airflow. Nguồn: AS-07.

### Q34
**Question:** Nếu Airflow không trả schedule history, next run hoặc timestamp thì có tự suy đoán không?

**Answer:** Không; hiển thị không khả dụng, không suy diễn dữ liệu quá khứ từ cấu hình hiện tại. Nguồn: AS-08.

### Q35
**Question:** Lịch cron và múi giờ mặc định được quy định thế nào?

**Answer:** Cron 5 trường, UTC mặc định. Nguồn: phần làm rõ DAG.

## D. Các lựa chọn kỹ thuật do AI tổng hợp trong bước nghiên cứu/thiết kế — feature 001

Câu hỏi trong nhóm này được tái dựng từ quyết định thiết kế, không tính là các câu hỏi nghiệp vụ thực tế đã hỏi người dùng. Nguồn: [research 001](../specs/001-airflow-automation-tool/research.md); mỗi mục chỉ rõ phần tương ứng. Các phê duyệt dependency/security xuất hiện về sau vẫn có thẩm quyền riêng, không được xem là AI tự duyệt.

### Q36
**Question:** Nên dùng executor nào cho Airflow trên một máy local?

**Answer:** Chọn LocalExecutor, parallelism 2, mỗi DAG một task `execute_etl`, max_active_runs 1; không cần broker/Celery worker. Nguồn: research mục 1.

### Q37
**Question:** ETL engine có phụ thuộc trực tiếp Airflow SDK hoặc ORM không?

**Answer:** Wrapper dùng `airflow.sdk`; ETL engine độc lập SDK/ORM Airflow. Engine và metadata package được đóng wheel, cài vào custom Airflow image. Nguồn: research mục 1.

### Q38
**Question:** Dependency dùng latest hay phiên bản cố định và cài lúc startup?

**Answer:** Pin phiên bản, tạo lock/hash, kiểm compatibility bằng resolve/build/pip check; không dùng latest hoặc cài pip tùy ý khi startup. Mọi override sau đó tuân phê duyệt riêng ghi trong research. Nguồn: research mục 2 và 10, các quyết định hiện hành ở đầu file.

### Q39
**Question:** Backend giao tiếp với Airflow qua UI API, metadata DB hay Public API?

**Answer:** Dùng Public API `/api/v2` với service user/JWT SimpleAuthManager; không gọi UI API hoặc ORM metadata. Nguồn: research mục 3.

### Q40
**Question:** Làm sao bảo đảm DAG được generate không thực thi code lấy từ Excel?

**Answer:** Serialize cấu hình bằng canonical JSON, wrapper import engine; không nội suy cell Excel thành Python executable. File có owner tag và revision SHA-256. Nguồn: research mục 3.

### Q41
**Question:** Ghi file DAG xong có đủ để kết luận deploy thành công không?

**Answer:** Không. Pause, đóng admission, drain run, ghi file atomic rồi poll có backoff tối đa 120 giây; đối chiếu tags/hash/fileloc/parse time và DAG version. Timeout là kết quả chưa xác định. Nguồn: research mục 3.

### Q42
**Question:** Run cũ được clear sau redeploy có được chạy với mã mới không?

**Answer:** Task startup phải đối chiếu DAG version với revision; version không khớp thì từ chối, operator tạo run mới. Không coi DagVersion riêng lẻ là đủ để bảo đảm mã cũ. Nguồn: research mục 3.

### Q43
**Question:** Password connection được lưu và đưa đến runtime bằng cách nào?

**Answer:** Mã hóa Fernet theo immutable ConnectionRevision trong app metadata; key lưu private volume riêng. Runtime đọc ciphertext bằng role riêng và giải mã trong memory; API không trả password, kể cả private API. Nguồn: research mục 4.

### Q44
**Question:** Nếu ciphertext đã tồn tại mà mất key thì có tự tạo key mới không?

**Answer:** Không. Key được tạo một lần; rotation có kiểm soát bằng keyring/MultiFernet, không tự thay key khiến mất khả năng giải mã. Nguồn: research mục 4.

### Q45
**Question:** Làm sao giữ consistent snapshot khi đọc PostgreSQL và MySQL theo chunk?

**Answer:** PostgreSQL dùng read-only REPEATABLE READ và server-side cursor; MySQL InnoDB dùng REPEATABLE READ consistent snapshot và unbuffered SSCursor. Giữ một source transaction đến hết extraction, không OFFSET qua nhiều transaction. Nguồn: research mục 5.

### Q46
**Question:** Disk staging dùng định dạng gì để bảo toàn kiểu dữ liệu?

**Answer:** JSON Lines UTF-8, row array và typed schema manifest, không nén ở MVP. Decimal là chuỗi chính xác, date/time ISO, NULL là JSON null; binary không hỗ trợ. Nguồn: research mục 5.

### Q47
**Question:** Làm sao biết chunk staging đã ghi hoàn chỉnh?

**Answer:** Mỗi chunk có checksum, số dòng và số byte; manifest complete chỉ ghi sau fsync. Đường dẫn dùng hash DAG ID/hash Run ID/attempt UUID, không nối trực tiếp ID vào path. Nguồn: research mục 5.

### Q48
**Question:** Làm sao ngăn hai run cùng ghi một target table, kể cả qua connection alias?

**Answer:** Writer session giữ native target lock: PostgreSQL advisory lock hoặc MySQL GET_LOCK theo physical target. Chờ tối đa 300 giây; mất session phải reacquire/reconcile trước ghi tiếp. Nguồn: research mục 6.

### Q49
**Question:** Nếu mất phản hồi COMMIT thì có retry ghi ngay không?

**Answer:** Không. Commit ledger nằm cùng transaction target với DML; retry đối chiếu ledger/checksum dưới target lock. Không chứng minh được commit thì chuyển NEEDS_RECONCILIATION, không replay. Nguồn: research mục 6.

### Q50
**Question:** FULL_REFRESH được hiện thực atomic bằng TRUNCATE, rename hay cách khác?

**Answer:** Staging hoàn chỉnh trước; dùng một transaction DELETE được ủy quyền, batched INSERT, final ledger và verification; commit một lần. Không TRUNCATE/DROP/ALTER target. Nguồn: research mục 6.

### Q51
**Question:** MySQL UPSERT có dùng ON DUPLICATE KEY UPDATE cho target nhiều unique key không?

**Answer:** Không dùng mù vì không chỉ định được conflict target. Chọn UPDATE JOIN theo chosen key rồi INSERT key chưa có trong cùng batch transaction; duplicate khác gây rollback. PostgreSQL dùng ON CONFLICT theo key đã validation. Nguồn: research mục 7.

### Q52
**Question:** Kiểm duplicate key toàn dataset có dùng Python set trong RAM không?

**Answer:** Không; dùng target-typed temporary validation table có unique key/collation đúng target, chuẩn bị trước target DML transaction. Nguồn: research mục 7.

### Q53
**Question:** Validation và deploy chạy trong HTTP request hay công việc nền có thể phục hồi?

**Answer:** Backend-worker xử lý durable Operation trong app metadata bằng FOR UPDATE SKIP LOCKED và lease/heartbeat. Worker không lập lịch hoặc thực thi ETL thay Airflow; không dùng FastAPI BackgroundTasks làm cơ chế bền vững. Nguồn: research mục 8.

### Q54
**Question:** Readiness có chỉ cần HTTP 200 và thứ tự khởi động container không?

**Answer:** Không; cần truy vấn thật và kiểm schema version. Compose có secrets-init/app-init/airflow-init one-shot, phụ thuộc healthy/completed và init idempotent. Nguồn: research mục 8.

### Q55
**Question:** Excel validation có phải nơi cuối cùng quyết định file hợp lệ không?

**Answer:** Không; validation trong Excel hỗ trợ nhập liệu, server validator mới quyết định. Tạo hai template và hai sample bằng openpyxl, schema/version và Instructions tiếng Anh. Nguồn: research mục 9.

### Q56
**Question:** Quyền ONCE và thu hồi được đồng bộ bằng cách nào để tránh cấp quyền cạnh tranh?

**Answer:** RunIntent giữ ONCE trước khi gọi Airflow. Reservation, thu hồi và ReplacementAdmission dùng khóa row quyền trong app DB; target commit vẫn phải chứng minh bằng target ledger, không coi app DB và target DB commit atomic. Nguồn: research mục 11.

### Q57
**Question:** Có suy run định kỳ từ prefix Run ID hoặc conf để cấp SCHEDULED không?

**Answer:** Không; dùng `DAGRunResponse.run_type`. Chỉ scheduled đúng lịch/revision đã xác nhận được dùng SCHEDULED; manual cần ONCE. Các loại còn lại không nhận SCHEDULED trong MVP. Nguồn: research mục 11.

## E. Các lựa chọn giao diện theo ủy quyền — feature 002

Nguồn: [spec 002](../specs/002-ui-refresh/spec.md) và [research 002](../specs/002-ui-refresh/research.md). Câu hỏi được tái dựng; spec ghi không có câu hỏi gửi người dùng.

### Q58
**Question:** Làm mới UI có cần thay framework hoặc thêm dependency lớn không?

**Answer:** Giữ React/Vite, sửa CSS chung và thêm link button dùng lại; không thêm dependency lớn chỉ để đổi giao diện. Nguồn: research — Bố cục và công nghệ; FR-007.

### Q59
**Question:** Giao diện tham khảo được áp dụng đến mức nào?

**Answer:** Dùng màu sắc, mật độ và bề mặt làm gợi ý; chọn nền xám nhạt, panel/sidebar trắng, nhấn teal. Giữ workflow/menu/route, không sao chép hệ thống hoặc branding trong ảnh. Nguồn: FR-001–FR-002 và Giả định.

### Q60
**Question:** Làm sao tăng mật độ thông tin mà vẫn đọc được và không giấu cảnh báo?

**Answer:** Sidebar 216px, header 56px, panel padding 16px, gap 12–16px, chữ bảng 13px và control tối thiểu 36px. Dùng grid, đưa Recent runs trước thông tin phụ; giữ cảnh báo/review hiển thị. Nguồn: research — Mật độ và thứ tự đọc; phần Làm rõ.

### Q61
**Question:** Bố cục trên mobile và bảng rộng được xử lý thế nào?

**Answer:** Mobile chuyển một cột, menu có toggle; không tràn ngang toàn trang, chỉ bảng được cuộn ngang trong vùng riêng. Không thêm cuộn dọc lồng nhau cho bảng thường. Nguồn: US1, FR-005 và Trường hợp biên.

### Q62
**Question:** Link tải template và mở Airflow nên hiển thị ra sao?

**Answer:** Dùng hình thức button có nền/viền, padding, icon và nhãn tiếng Anh rõ; giữ URL, download, hành vi mở tab và keyboard focus. Nguồn: US2 và FR-003.

### Q63
**Question:** Trong phạm vi UI refresh có đổi ngay tài khoản demo thành admin/admin không?

**Answer:** Feature 002 giữ bootstrap/tài khoản và ghi hạn chế; thay demo hiện hữu cần đổi secret/tài khoản nên chưa thực hiện trong phạm vi này. Quyết định đó được mở rộng riêng ở feature 003 bên dưới. Nguồn: research — Tài khoản Airflow.

## F. Tên Definition và tài khoản demo theo ủy quyền — feature 003

Nguồn: [spec 003](../specs/003-definition-names-admin/spec.md). Câu hỏi được tái dựng từ yêu cầu, giả định và phần Làm rõ; không phải bản ghi hỏi–đáp tương tác.

### Q64
**Question:** Người dùng nên thấy tên workbook, template hay Definition ở từng bước?

**Answer:** Dùng ETL Definition/Table Definition xuyên suốt; template chỉ file mẫu tải về. Label upload là ETL Definition file (.xlsx)/Table Definition file (.xlsx). Giữ API scope `workbook`, identifier, message_key, mã WORKBOOK_* và schema Excel. Nguồn: US1, FR-001–FR-003 và Biên và giả định.

### Q65
**Question:** Khi được phép cập nhật demo, admin/admin áp dụng cho môi trường nào và bằng đường nào?

**Answer:** Tạo/cập nhật admin/admin có quyền admin trên demo local hiện hữu và fresh local/demo; dùng đường chính thức SimpleAuthManager, không sửa SQL metadata hay tắt auth. Root Compose là local loopback; helper không mặc định tạo admin nếu chưa opt-in. Nguồn: US2, FR-004–FR-005 và Làm rõ.

### Q66
**Question:** Bootstrap hoặc restart có được đặt lại mọi password và dữ liệu không?

**Answer:** Không. Bootstrap thường giữ password tùy chỉnh, service account và user khác; chỉ lệnh cập nhật được yêu cầu rõ mới đặt lại admin/admin. Giữ dữ liệu/volume/DAG/run/upload, có backup/restore; secret lỗi hoặc môi trường không khớp thì dừng. Nguồn: FR-006–FR-008 và Biên và giả định.

## G. Các mặc định bổ sung để tải User Guide — feature 004

Nguồn: [spec 004](../specs/004-user-guide-download/spec.md). Câu hỏi được tái dựng từ spec; tài liệu ghi không có điểm mơ hồ cần hỏi lại, không có bản ghi ủy quyền riêng cho từng mục. Answer thể hiện mặc định/phạm vi đã chọn, không khẳng định đã triển khai vì spec đang ghi Sẵn sàng triển khai.

### Q67
**Question:** Nút tải hướng dẫn đặt ở đâu và tên gì?

**Answer:** Nút Download User Guide nằm trên thanh Workspace/top bar, xuất hiện ở cả sáu màn hình và trong vùng nhìn ban đầu, tách khỏi danh sách menu. Nguồn: US1, FR-001 và Giả định.

### Q68
**Question:** Tải hướng dẫn dạng PDF, PPT hay HTML, dùng ngôn ngữ nào?

**Answer:** Dùng bản HTML tiếng Việt có sẵn, tên `Airflow-Automation-Tool-Huong-dan-su-dung.html`; không tạo thêm PPT hoặc sửa nội dung trong tính năng này. Nhãn UI vẫn tiếng Anh. Nguồn: FR-002, Đối tượng chính và Giả định.

### Q69
**Question:** File hướng dẫn có cần mạng hoặc backend/Airflow để xem và tải không?

**Answer:** File chứa đủ 16 mục, 12 ảnh nhúng và mục lục, đọc được offline. Đóng gói cùng frontend để vẫn tải được khi backend/Airflow không sẵn sàng, miễn giao diện còn truy cập được. Nguồn: US1, FR-003, FR-005 và SC-002.

### Q70
**Question:** Tải hướng dẫn có cần API mới, lịch sử tải hoặc thay đổi trang hiện tại không?

**Answer:** Không thêm API, xác thực, thống kê lượt tải hoặc dependency. Thao tác chỉ tải tài liệu, giữ màn hình, bộ lọc và dữ liệu nhập; không ghi dữ liệu nghiệp vụ. Nguồn: US1, FR-006 và Giả định.

## Cách sử dụng trong assignment

Có thể mô tả: “Tổng hợp được 70 mục Question–Answer từ tài liệu Spec Kit của bốn feature, gồm 5 mục có bản ghi Q/A và 65 mục tái dựng từ các mặc định, giả định, quyết định thiết kế và phạm vi đã ghi nhận. Các quyết định được giao cho AI được đưa trực tiếp vào Answer.”

Nếu đề yêu cầu riêng số câu hỏi được hỏi trong bước Clarify, dùng con số có bằng chứng Q/A là 5; nếu yêu cầu các vấn đề cần làm rõ và cách AI hỗ trợ quyết định, sử dụng danh sách đầy đủ kèm phân loại nguồn ở trên.
