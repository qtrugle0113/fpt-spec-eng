# Đặc tả tính năng: Airflow Automation Tool — MVP tự động hóa ETL

**Làm rõ môi trường2026-11-11:** chủ dự án duyệt build từ source/locks/config
trên từng máy; IDs dùng truy vết artifact, không bắt cùng IDs giữa các môi trường.
Mỗi artifact phải scan/test riêng theo policy có provenance; không cần registry
hoặc image archive máy cũ. Giữ safety gates, hạn/controls local và T014_FULL.
Nguồn: [quyết định](../../docs/decisions/portable-local-build-20261111.md).

**Thư mục tính năng**: `specs/001-airflow-automation-tool`

**Nhánh tính năng**: Chưa tạo; dự án không có hook Git tạo nhánh.

**Ngày tạo**: 2026-11-06

**Trạng thái**: Đã rà soát và làm rõ ngày 2026-11-06, sẵn sàng lập kế hoạch.

**Đầu vào**: Yêu cầu sản phẩm qua `/speckit-specify` gồm 17 nhóm nội dung; chịu ràng buộc
của Constitution 1.1.0.

**Mục tiêu**: Data Engineer hoặc kỹ sư biết database cơ bản có thể quản lý connections,
tạo table và DAG bằng Excel, chuyển dữ liệu thật, lập lịch và theo dõi kết quả mà không
viết Python DAG hay SQL DDL. MVP phục vụ một operator local.

**Giới hạn bước Specify**: Xác định WHAT và WHY. Airflow, Linux containers, PostgreSQL, MySQL và
staging trên đĩa là yêu cầu đầu vào. Framework, phiên bản, endpoint, thư viện và cấu trúc
mã nguồn chưa được chọn. Không có screenshot, wireframe hoặc Excel mẫu có sẵn.

## Đồng bộ runtime theo Constitution 1.1.0 ngày 2026-11-08

Chủ dự án đã duyệt hỗ trợ Podman. Baseline local hiện chọn Podman; các lệnh trong Spec dùng
`podman compose`. Baseline Docker vẫn được phép dùng `docker compose` tương ứng nếu công bố
và nghiệm thu theo Constitution IX. PASS của một runtime không chứng minh runtime còn lại.
Không đổi nghiệp vụ BR-08 hoặc các tiêu chí readiness/persistence/secrets/ETL; build/stack
trên baseline Podman hiện chưa được kiểm chứng.

## Các nội dung đã làm rõ

### Phiên làm rõ ngày 2026-11-06

Ở lượt làm rõ ban đầu không phát sinh câu hỏi cần trả lời. Người dùng đã ủy quyền chọn mặc định hợp lý;
những quyết định dưới đây là mặc định được áp dụng, không phải câu trả lời tương tác giả định.

| Nhóm quyết định người dùng | Kết luận và nơi áp dụng |
| --- | --- |
| 1–2 | Local một operator, không login; một connection dùng cả source/target — AS-01, FR-003 |
| 3–5 | Một Table workbook nhiều table, ETL workbook nhiều DAG, mapping cùng sheet — FR-021–FR-023, FR-030, FR-042 |
| 6 | Không mapping enabled thì implicit-map theo tên chính xác/type tương thích — FR-044 |
| 7–9 | DAG mới paused; cron/manual; Catchup false — FR-034, FR-037, BR-04, BR-20 |
| 10–13 | Không DROP/ALTER table cũ, APPEND có thể duplicate, UPSERT phải có key thật, FULL_REFRESH atomic/recovery — FR-027, FR-050–FR-054, BR-15 |
| 14–17 | TXT delimited, không code tùy ý, DB-to-DB disk staging, Run ID/path riêng — FR-001, FR-019, FR-055–FR-058 |
| 18–20 | Redeploy có kiểm tra/xác nhận, UI tiếng Anh/Markdown tiếng Việt, không cần ảnh mẫu — FR-036, FR-097, NFR-001, AS-09 |

- **Toàn vẹn dữ liệu**: Chốt transaction theo strategy, snapshot một table nhất quán, dataset
  staging bất biến và commit không rõ phải dừng đối soát; UPSERT thiếu key bị chặn, không tự ALTER.
  FULL_REFRESH extraction fail không động target; công bố chỉ một transaction và không TRUNCATE rồi load batch.
- **ETL**: Tách chunk/batch mặc định 1.000; kiểm soát byte/quota, typed lossless staging,
  fail-fast, schema drift/revalidation, header/delimiter validation, đối soát theo strategy,
  recovery khi kill và không xóa artifact cần phục hồi.
- **DAG**: Phân biệt pending/parse/API unavailable; đối soát identity trước retry;
  serialize cùng DAG/target, update revision có cửa sổ kiểm soát; cron 5 trường, UTC mặc định;
  connection sửa có revision, không chuyển target của run đã bắt đầu.
- **Excel/Docker**: Version 1.0, required/optional/reference/duplicate/location cụ thể;
  readiness thật, init idempotent, hostname nội bộ tách browser URL, volume và secret key bền.
- **Chuyển sang Plan**: Định dạng vật lý staging, isolation/driver, cơ chế khóa/checkpoint,
  triển khai transaction replacement, hạn mức tài nguyên cụ thể và kiểm tra theo phiên bản Airflow.
  Các mục này là lựa chọn cách thực hiện; hợp đồng đúng/sai và tiêu chí nghiệm thu đã được chốt.

- Q: Quyền FULL_REFRESH ONCE nên được gắn cố định với một lần chạy cụ thể từ thời điểm nào? → A: Gắn độc quyền với Run ID ngay khi tiếp nhận yêu cầu chạy, trước khi tạo/khởi động run; gửi lặp cùng yêu cầu và retry dùng lại binding đó.
- Q: Sau khi quyền ONCE đã gắn với Run ID, nếu run thất bại hoặc bị hủy trước khi thay dữ liệu, quyền đó có được chuyển sang run mới không? → A: Không chuyển quyền; retry cùng run khi còn được phép, run mới/rerun cần ONCE mới; thành công tiêu thụ quyền, kết thúc thất bại/hủy đóng quyền, commit chưa rõ giữ chờ đối soát.
- Q: Quyền FULL_REFRESH SCHEDULED có cho phép chạy thủ công ngoài lịch đã xác nhận không? → A: Không; chỉ run Airflow tạo theo lịch đã xác nhận dùng SCHEDULED, manual trigger/rerun mới cần ONCE; retry cùng run định kỳ được phép khi an toàn và quyền còn hiệu lực.
- Q: Khi operator xác nhận allow_empty cho quyền SCHEDULED, quyền làm rỗng target có được áp dụng cho mọi run theo lịch trong cùng phạm vi không? → A: Có, chỉ sau xác nhận riêng rõ hậu quả; ONCE chỉ run đã gắn, SCHEDULED chỉ các run theo lịch trong cùng phạm vi; mặc định không cho phép, thay scope/thu hồi làm mất hiệu lực, lỗi nguồn không là dataset rỗng hợp lệ.
- Q: Nếu operator thu hồi quyền FULL_REFRESH khi run đã giữ quyền nhưng chưa xác định xong kết quả thay dữ liệu, hệ thống nên xử lý thế nào? → A: Thu hồi chặn run mới/retry ghi mới; nếu được ghi nhận trước điểm chấp thuận bắt đầu transaction replacement thì không thay dữ liệu; transaction đã được chấp thuận có thể hoàn tất/rollback an toàn; commit chưa rõ chỉ đối soát, không replay bằng quyền đã thu hồi; UI nêu thu hồi không đồng nghĩa hủy giao dịch đã bắt đầu.

## Kịch bản người dùng và kiểm thử

P1 là nền tảng và ETL cốt lõi; P2 là quan sát tổng hợp và cấu hình. Tất cả đều thuộc MVP.
Mỗi câu chuyện có thể kiểm thử riêng với fixture thật của các phụ thuộc, không cần hoàn
thành toàn bộ màn hình. Mã US, FR, NFR, BR, EC, SC dùng truy vết sang Plan/Tasks/kiểm thử.

### Câu chuyện US-01 — Khởi động môi trường (Ưu tiên: P1)

Là operator, tôi muốn dùng một lệnh để có môi trường đầy đủ với dữ liệu mẫu.

**Lý do ưu tiên**: Điều kiện kiểm chứng mọi tích hợp thật.

**Kiểm thử độc lập**: Khởi động từ mới, chạy luồng mẫu, restart và kiểm tra dữ liệu còn nguyên.

**Kịch bản chấp nhận**:

1. **Cho trước** runtime/provider đã công bố và cổng cần thiết sẵn sàng, **khi** chạy
   `podman compose up --build -d`, **thì** sau initialization/healthchecks hệ thống sử dụng
   được, không cần lệnh migration, seed hoặc cấu hình Airflow thủ công.
2. **Cho trước** có dữ liệu người dùng, **khi** restart, **thì** metadata, file, DAG, logs và
   dữ liệu được lưu bền; initialization không ghi đè chúng.
3. **Cho trước** initialization lỗi, **khi** kiểm tra, **thì** thấy service/nguyên nhân lỗi,
   không báo sẵn sàng giả.

### Câu chuyện US-02 — Quản lý database connections (Ưu tiên: P1)

Là Data Engineer, tôi muốn CRUD, tra cứu và kiểm tra kết nối thật để tái sử dụng cho source/target.

**Lý do ưu tiên**: Table và DB-to-DB phụ thuộc connection hợp lệ.

**Kiểm thử độc lập**: CRUD và Test Connection trên PostgreSQL/MySQL thật, gồm lỗi/dependency.

**Kịch bản chấp nhận**:

1. **Cho trước** cấu hình hợp lệ, **khi** chọn `Test Connection`, **thì** kết nối thật tới DB,
   báo kết quả và thời điểm, không trả mật khẩu.
2. **Cho trước** code đã tồn tại, **khi** tạo trùng, **thì** báo `Connection Code already exists`.
3. **Cho trước** connection đang được DAG/Definition tham chiếu, **khi** xóa hoặc đổi code,
   **thì** bị chặn với danh sách dependency cần xử lý.
4. **Cho trước** connection đã lưu, **khi** xem/sửa, **thì** không đọc được mật khẩu cũ;
   password bỏ trống khi sửa giữ secret hiện tại.
5. **Cho trước** host/port, credential, database sai hoặc timeout, **khi** kiểm tra,
   **thì** trả nhóm lỗi phù hợp, không treo hoặc rò secret.

### Câu chuyện US-03 — Quản lý source file (Ưu tiên: P1)

Là Data Engineer, tôi muốn upload, preview và validate CSV/TXT để dùng làm nguồn ETL.

**Lý do ưu tiên**: Đáp ứng bốn hướng File-to-DB.

**Kiểm thử độc lập**: Upload file đúng/sai; kiểm tra preview giới hạn và persistence sau restart.

**Kịch bản chấp nhận**:

1. **Cho trước** file hợp lệ, **khi** upload, **thì** nhận reference ổn định, metadata parser
   và preview tối đa 100 dòng; không giữ toàn file trong RAM.
2. **Cho trước** quoted delimiter, NULL hoặc file không header, **khi** parse,
   **thì** preview/execution thống nhất; cột không header là `column_1`, `column_2`, ...
3. **Cho trước** nguồn thiếu/quá hạn hoặc sai format, **khi** validate/chạy,
   **thì** fail rõ ràng, không coi lỗi nguồn là dataset rỗng để xóa target.

### Câu chuyện US-04 — Tạo table từ Excel (Ưu tiên: P1)

Là Data Engineer, tôi muốn tải template, khai báo nhiều table, xem SQL DDL và xác nhận tạo.

**Lý do ưu tiên**: Chuẩn bị target không cần viết DDL.

**Kiểm thử độc lập**: Workbook nhiều table trên hai loại DB, gồm composite primary key và table tồn tại.

**Kịch bản chấp nhận**:

1. **Cho trước** workbook hợp lệ và đủ quyền, **khi** preview rồi `Confirm Create Tables`,
   **thì** tạo table thật đúng cột/kiểu/khóa, có kết quả và lịch sử từng table.
2. **Cho trước** workbook thiếu sheet/cột, trùng column hoặc sai type, **khi** validate,
   **thì** lỗi có sheet/row/column/nguyên nhân; không tạo table nào.
3. **Cho trước** table tồn tại hoặc mất quyền sau preview, **khi** execute,
   **thì** báo lỗi table đó, không ALTER/DROP; kết quả table khác vẫn được báo riêng.

### Câu chuyện US-05 — Tạo và triển khai DAG (Ưu tiên: P1)

Là Data Engineer, tôi muốn upload ETL workbook nhiều DAG, kiểm tra nguồn/đích/mapping,
xem schedule/load strategy rồi triển khai lên Airflow.

**Lý do ưu tiên**: Giá trị cốt lõi của sản phẩm.

**Kiểm thử độc lập**: Dùng nguồn/đích thật, deploy workbook và đối chiếu Airflow, không cần Dashboard.

**Kịch bản chấp nhận**:

1. **Cho trước** Definition hợp lệ, **khi** preview, **thì** thấy source/target, mapping,
   schedule/timezone, retry và tác động load strategy trước xác nhận.
2. **Cho trước** đã xác nhận generate/deploy, **khi** mới ghi file, **thì** là
   `Deployment Pending`; chỉ `Deployed` sau khi Airflow parse/đăng ký đúng revision mới.
3. **Cho trước** parse lỗi hoặc quá hạn đăng ký, **khi** kiểm tra,
   **thì** `Parse Error` hoặc `Deployment Failed`, có nguyên nhân và cách thử lại.
4. **Cho trước** DAG ID tồn tại, **khi** upload bản mới, **thì** preview và xác nhận update
   cho DAG managed; chặn ghi đè DAG external, không cập nhật im lặng.
5. **Cho trước** Definition yêu cầu enabled, **khi** deploy DAG mới, **thì** vẫn paused;
   cần xác nhận `Activate DAG` riêng.

6. **Cho trước** API timeout sau khi gửi deploy/trigger, **khi** kết nối lại,
   **thì** đối soát identity cũ trước retry, không tạo run/deployment trùng.
7. **Cho trước** đang redeploy hoặc connection đổi target,
   **khi** có scheduled/manual run mới, **thì** không dùng revision chưa xác minh hoặc
   ủy quyền FULL_REFRESH cũ; run cũ giữ revision đã chốt.

### Câu chuyện US-06 — DB-to-DB với mapping và dữ liệu lớn (Ưu tiên: P1)

Là Data Engineer, tôi muốn chuyển dữ liệu giữa PostgreSQL/MySQL, đổi tên cột, xử lý dữ liệu
vượt RAM và biết phần đã ghi/thất bại.

**Lý do ưu tiên**: Chứng minh ETL thật, an toàn tài nguyên.

**Kiểm thử độc lập**: Fixture thật cho cả bốn hướng DB-to-DB, nhiều batch, đối chiếu dữ liệu/staging.

**Kịch bản chấp nhận**:

1. **Cho trước** mapping nguồn/đích hợp lệ, **khi** chạy bốn hướng DB-to-DB,
   **thì** giá trị, NULL, khóa và số dòng đúng load policy.
2. **Cho trước** dataset vượt RAM worker, **khi** chạy nhiều batch, **thì** có staging thật
   trên đĩa, bộ nhớ trong giới hạn, không truyền dataset qua XCom.
3. **Cho trước** cột khác tên, **khi** mapping tường minh, **thì** dữ liệu tới đúng cột;
   mapping mơ hồ hoặc conversion mất dữ liệu bị từ chối.
4. **Cho trước** hết đĩa/mất kết nối giữa chừng, **khi** thất bại, **thì** báo phần đã commit,
   không báo success; retry/rerun đúng policy.

5. **Cho trước** nguồn DB bị update trong lúc extract, **khi** đọc các chunk,
   **thì** toàn dataset vẫn cùng snapshot; snapshot bị mất làm extraction retry từ đầu,
   target chưa bị thay đổi.
6. **Cho trước** staging bị truncate/checksum sai sau một batch target commit,
   **khi** retry load, **thì** dừng đối soát, không re-extract nguồn mới rồi nối vào phần cũ.
7. **Cho trước** decimal chính xác, Unicode, NULL và timestamp có offset,
   **khi** đi qua staging/mapping, **thì** round-trip theo BR-17; target không biểu diễn được thì lỗi.
8. **Cho trước** chunk 1.000 và batch 500, **khi** load,
   **thì** commit theo batch không theo chunk; byte cap vẫn giới hạn RAM và dòng vượt cap báo lỗi.

### Câu chuyện US-07 — File-to-DB (Ưu tiên: P1)

Là Data Engineer, tôi muốn chọn file đã upload, mapping và load vào PostgreSQL/MySQL.

**Lý do ưu tiên**: Hoàn thiện đủ tám hướng ETL.

**Kiểm thử độc lập**: Chạy CSV/TXT vào từng DB thật, đối chiếu delimiter/encoding/NULL và target.

**Kịch bản chấp nhận**:

1. **Cho trước** file/parser hợp lệ, **khi** chạy, **thì** đọc streaming và ghi batch đúng dữ liệu.
2. **Cho trước** dòng sai số trường/type, **khi** xử lý, **thì** fail có vị trí và số đã commit;
   không bỏ dòng âm thầm.
3. **Cho trước** nội dung/parser thay đổi sau preview, **khi** dùng xác nhận cũ,
   **thì** yêu cầu validation lại, không thay nguồn im lặng.

### Câu chuyện US-08 — Load strategies và recovery (Ưu tiên: P1)

Là operator, tôi muốn biết tác động của APPEND/UPSERT/FULL_REFRESH khi chạy, retry và rerun.

**Lý do ưu tiên**: Bảo vệ dữ liệu trước mọi execution thật.

**Kiểm thử độc lập**: Tập dữ liệu biết trước, gây partial failure và kiểm tra target sau retry/rerun.

**Kịch bản chấp nhận**:

1. **Cho trước** APPEND không unique constraint, **khi** chạy hai lần cùng dataset,
   **thì** thêm hai lần dữ liệu, giữ dữ liệu cũ và cảnh báo duplicate.
2. **Cho trước** APPEND không biết chắc batch cuối đã commit, **khi** retry,
   **thì** dừng yêu cầu đối soát, không tự replay phần không chắc chắn.
3. **Cho trước** UPSERT có conflict key hợp lệ, **khi** rerun cùng dữ liệu,
   **thì** không tăng số key và update đúng cột mapping.
4. **Cho trước** FULL_REFRESH chưa có ủy quyền đúng target/revision,
   **khi** thao tác dẫn tới chạy, **thì** bị chặn.
5. **Cho trước** FULL_REFRESH đã được xác nhận, **khi** load/công bố dữ liệu thất bại,
   **thì** giữ hoặc phục hồi dữ liệu cũ, ghi kết quả recovery, không báo thành công cho target partial.

6. **Cho trước** target UPSERT thiếu unique key, **khi** validate hoặc preflight,
   **thì** bị chặn trước ghi và không tự ALTER/CREATE INDEX/downgrade APPEND.
7. **Cho trước** FULL_REFRESH đã được ủy quyền, **khi** source extraction lỗi,
   **thì** dữ liệu target giữ nguyên, không có giai đoạn TRUNCATE trước extraction.
8. **Cho trước** MySQL target không transactional, **khi** validate,
   **thì** từ chối với lý do; không tự đổi engine hoặc hứa rollback DDL như DML.
9. **Cho trước** hai DAG managed dùng connection code khác nhau cùng physical target,
   **khi** chạy chồng lấn, **thì** một run giữ quyền ghi, run kia chờ hoặc timeout 300 giây;
   kill/restart không làm cả hai cùng giành quyền khi chưa xác minh owner cũ.
10. **Cho trước** FULL_REFRESH mất phản hồi commit, **khi** worker restart,
    **thì** đối soát target/revision trước retry; không xóa hoặc phát lại mù.

### Câu chuyện US-09 — Theo dõi và điều khiển DAG (Ưu tiên: P1)

Là operator, tôi muốn xem DAG/run/task/log, trigger, pause/unpause và mở đúng DAG trong Airflow.

**Lý do ưu tiên**: Điều khiển và chẩn đoán ETL; hoàn thiện UI Monitoring sau core ETL.

**Kiểm thử độc lập**: Airflow có DAG managed/external và run thật đủ trạng thái.

**Kịch bản chấp nhận**:

1. **Cho trước** hai nhóm DAG, **khi** mở `DAG Monitoring`, **thì** phân biệt `Managed`/`External`;
   chỉ managed liên kết Definition, không giả định mọi DAG đến từ Excel.
2. **Cho trước** managed DAG đủ điều kiện, **khi** `Trigger DAG`, **thì** một run được tạo,
   trạng thái tiếp nhận khác kết quả success; pause không hủy run đang chạy.
3. **Cho trước** task failed, **khi** xem run, **thì** thấy task status, duration, error summary,
   log đã che secrets hoặc lý do log không khả dụng.
4. **Cho trước** `Open in Airflow`, **khi** mở, **thì** tới đúng DAG ID bằng URL browser truy cập được.

### Câu chuyện US-10 — Dashboard đáng tin cậy (Ưu tiên: P2)

Là operator, tôi muốn KPI, xu hướng và recent runs theo khoảng ngày rõ ràng.

**Lý do ưu tiên**: Quan sát tổng hợp sau ETL/Monitoring cơ bản.

**Kiểm thử độc lập**: So sánh Dashboard với tập DAG Runs thật đã biết, gồm phân trang và queued/other.

**Kịch bản chấp nhận**:

1. **Cho trước** tập run chuẩn, **khi** lọc ngày/timezone, **thì** số run và biểu đồ đúng;
   DAG inventory không bị nhầm thành số execution trong khoảng.
2. **Cho trước** queued/running, **khi** tính success rate, **thì** mẫu số chỉ success+failed;
   tổng run vẫn gồm mọi trạng thái.
3. **Cho trước** dữ liệu next run/lịch sử thiếu, **khi** hiển thị, **thì** `Not available` hoặc
   `Incomplete data`; không suy đoán.
4. **Cho trước** Airflow down, **khi** refresh, **thì** dữ liệu cũ nếu giữ có nhãn `Stale`
   và lần cập nhật cuối, không biến lỗi thành KPI 0.

### Câu chuyện US-11 — Settings và trải nghiệm nhất quán (Ưu tiên: P2)

Là operator, tôi muốn chỉnh mặc định an toàn và dùng giao diện tiếng Anh dễ hiểu.

**Lý do ưu tiên**: Hoàn thiện khả dụng, tránh hệ thống settings phức tạp.

**Kiểm thử độc lập**: Lưu đúng/sai, restart, mở cấu hình mới/cũ, kiểm tra màn hình desktop/hẹp.

**Kịch bản chấp nhận**:

1. **Cho trước** settings hợp lệ, **khi** lưu batch/refresh/timezone/retention,
   **thì** tồn tại qua restart, áp dụng đúng phạm vi BR-14.
2. **Cho trước** giá trị âm/không hợp lệ, **khi** lưu, **thì** báo validation tiếng Anh,
   giữ cấu hình hợp lệ trước đó.
3. **Cho trước** dữ liệu rỗng/thao tác dài/thất bại, **khi** xem UI,
   **thì** có empty/loading/success/failure state phù hợp, hành động chính truy cập được.

### Các trường hợp biên

| Mã | Tình huống | Kết quả bắt buộc |
| --- | --- | --- |
| EC-01 | Trùng code/DAG ID, yêu cầu tạo đồng thời | Một định danh, chặn conflict, không ghi đè |
| EC-02 | Xóa/đổi code dependency | Chặn và chỉ rõ Definition/DAG tham chiếu |
| EC-03 | Host/port/credential/database sai, timeout | Lỗi phân loại, không treo/rò secret |
| EC-04 | File rỗng/chỉ header/quoted newline/encoding sai | Phân biệt empty hợp lệ và lỗi parser; refresh rỗng cần xác nhận riêng |
| EC-05 | Upload ngắt/quá quota/path traversal | Không công bố file dở; từ chối đường dẫn nguy hiểm, cleanup |
| EC-06 | Workbook hỏng/version sai/macro/formula | Từ chối, không chạy code/công thức hoặc tạo side effect |
| EC-07 | Thiếu sheet/cột, ordinal trùng, mapping reference sai | Lỗi có vị trí, chặn workbook chưa hợp lệ |
| EC-08 | Key nullable, precision/scale/type sai | Validation trước DDL |
| EC-09 | Table xuất hiện/quyền bị thu hồi sau preview | Lỗi riêng từng table, không ALTER/DROP |
| EC-10 | Schema đổi sau preview | Kiểm tra lại trước execution, fail an toàn |
| EC-11 | File DAG đã ghi nhưng chưa parse, bản cũ còn đăng ký | Không Deployed đến khi xác minh đúng revision mới |
| EC-12 | External DAG trùng ID, redeploy lúc run active | Chặn update, bảo vệ cấu hình run hiện tại |
| EC-13 | DST/cron sai/start date quá khứ/catchup | Hiển thị timezone/backfill, tuân lịch Airflow |
| EC-14 | Mapping mơ hồ/cột bắt buộc thiếu/tràn số/cắt chuỗi | Báo lỗi, không mất dữ liệu âm thầm |
| EC-15 | UPSERT key NULL/trùng, unique khác xung đột | Fail rõ, không update sai bản ghi |
| EC-16 | APPEND mất xác nhận commit | Dừng đối soát, không auto-replay batch không chắc chắn |
| EC-17 | FULL_REFRESH lỗi/dataset rỗng | Giữ/phục hồi dữ liệu cũ; rỗng cần quyền riêng |
| EC-18 | Disk full/worker ngắt/canceled task | Trạng thái thật, tiến độ commit, recovery/cleanup |
| EC-19 | Hai runs cùng target, cleanup gặp run active | Tuần tự hóa/chặn ghi xen kẽ, không xóa file đang dùng |
| EC-20 | File thiếu/quá hạn sau deploy | Fail trước ghi, không coi là 0 rows |
| EC-21 | Dashboard nhiều trang/no runs/queued-only | Tổng đủ hoặc nhãn thiếu, success rate không xác định là Not available |
| EC-22 | Log/next run thiếu, Airflow down | Không khả dụng/stale rõ, không suy đoán |
| EC-23 | Trigger/deploy gửi lặp | Không tạo logical run/revision dư ngoài ý muốn |
| EC-24 | Filter/default chứa SQL/Python tùy ý | Từ chối, không thực thi nội dung workbook |
| EC-25 | Nguồn update giữa các chunk hoặc snapshot mất | Một snapshot xuyên extraction; mất thì bỏ incomplete, retry từ đầu trước ghi target |
| EC-26 | Target UPSERT thiếu key thật sau deploy | Runtime preflight chặn, không tự ALTER/index/downgrade |
| EC-27 | Unicode/decimal/timezone/NULL không round-trip | Lỗi rõ không làm tròn/thay NULL/đoán timezone |
| EC-28 | Staging corrupt sau commit hoặc worker bị kill | Đối soát, không thay dataset/xóa recovery artifact |
| EC-29 | Schema version lạ/duplicate/orphan cross-sheet | Chặn workbook, đúng sheet/row/column thật |
| EC-30 | First init lỗi hoặc key secret mất sau restart | Chẩn đoán, không reset volume/secret hay báo healthy giả |

## Yêu cầu

### Yêu cầu chức năng

Mọi FR dưới đây là bắt buộc. Hợp đồng metadata mô tả thông tin sản phẩm phải hỗ trợ,
không quyết định cấu trúc lưu trữ hoặc endpoint triển khai.

#### Phạm vi, navigation và connections

- **FR-001**: Hỗ trợ PostgreSQL → PostgreSQL, MySQL → MySQL, PostgreSQL → MySQL,
  MySQL → PostgreSQL, CSV → PostgreSQL, CSV → MySQL, TXT → PostgreSQL, TXT → MySQL.
  TXT là dữ liệu bảng với delimiter cấu hình được.
- **FR-002**: Sáu màn hình chính: `Dashboard` là Home, `Connections`, `Table Management`,
  `DAG Builder`, `DAG Monitoring`, `Settings`. File Sources truy cập từ DAG Builder.
- **FR-003**: Connection có Connection Code, Connection Name, Database Type, Host, Port,
  Database Name, Schema nếu áp dụng, Username, Password, Description, Created At, Updated At.
  Chỉ PostgreSQL/MySQL, mỗi connection dùng được cho cả source và target.
- **FR-004**: Code bắt buộc/unique sau trim, không phân biệt hoa thường; name/type/host/port/
  database/username bắt buộc; port 1–65535; credential theo chính sách database đích.
- **FR-005**: Có Add/Edit/Delete/Test Connection, details/status; search code/name/host,
  filter database type và connection status.
- **FR-006**: Connection status là chưa test/thành công/thất bại kèm thời điểm; đổi thông tin
  kết nối làm kết quả cũ mất hiệu lực. Test thành công cũ không đảm bảo kết nối hiện tại.
- **FR-007**: Test kết nối thật, timeout hữu hạn, phân loại host unreachable, port không kết nối,
  credential sai, database thiếu, timeout, DB không hỗ trợ; lỗi không phân loại chắc chắn ghi đúng giới hạn.
- **FR-008**: Chặn xóa/đổi code connection đang có dependency, hiển thị nơi tham chiếu.
  Mỗi lần sửa connection tạo revision. Host/port/database/schema/type là thay đổi vị trí:
  chặn khi có run active; Definition/DAG phụ thuộc phải validation và xác nhận lại trước
  trigger/unpause/run kế tiếp, không tự chuyển sang đích mới. Đổi credential cần test thật;
  run đã bắt đầu giữ nguyên revision và credential reference đã chốt, không đổi giữa các task.
  Run mới chỉ dùng revision đã xác thực; sửa credential không tự khôi phục run thất bại.

- **FR-009**: Không hiển thị/trả lại password đã lưu; sửa bằng secret mới, bỏ trống giữ secret cũ.

#### File Sources

- **FR-010**: Có Upload File, Preview Data, Validate Format, View Uploaded Files và Select File as ETL Source.
- **FR-011**: File có reference duy nhất, File Name, File Type, File Size, Encoding, Delimiter,
  Header Present, Quote Character, Escape Character nếu cần, NULL Representation,
  Uploaded At, validation status và retention/expiry nếu áp dụng.
- **FR-012**: File ở container-managed persistent storage, dùng được sau restart;
  reference xác định đúng nội dung upload, không chỉ tên file có thể trùng.
- **FR-013**: Validate extension, kích thước, đường dẫn/quyền; không công bố upload chưa xong,
  không cho input chỉ định path ngoài khu vực cho phép; có cleanup upload lỗi.
- **FR-014**: Preview tối đa 100 dòng và parser configuration; Validate Format kiểm tra toàn
  file với bộ nhớ hữu hạn, xác định lỗi dòng/encoding/số trường. Preview không thay full validation.
- **FR-015**: Cho xác nhận encoding/delimiter/header/quote/escape/NULL representation;
  không dùng kết quả tự đoán chưa cho người dùng kiểm tra.
- **FR-016**: Công bố retention/dependency; không tự xóa file đang được Definition/DAG/run tham chiếu.
  Nguồn thiếu/quá hạn làm validation/run fail rõ, không biến thành empty dataset.
- **FR-017**: File không header có tên cột theo vị trí; thay nội dung/parser cần validate lại.
  Excel không được làm nguồn dataset ETL.

#### Excel Definition và Table Management

- **FR-018**: Download `Table Definition.xlsx`, `ETL Definition.xlsx` có Template Version,
  Required/Optional fields, Example values, Validation rules; sheet/header/hướng dẫn bằng tiếng Anh.
- **FR-019**: Chỉ nhận workbook .xlsx hợp lệ, không macro/code hoặc formula trong metadata;
  không thực thi công thức, external link hoặc source code. Template Version ban đầu là `1.0`,
  so khớp chính xác danh sách hỗ trợ; thiếu/version lạ bị từ chối trước side effect.
  Không tự migration workbook hoặc suy đoán schema từ tên file.

- **FR-020**: Lỗi Excel nêu sheet/row/column/nguyên nhân; lỗi cấp workbook ghi phạm vi workbook
  và vị trí không áp dụng, không tạo vị trí giả. Có tổng hợp lỗi để sửa và upload lại.
- **FR-021**: Table workbook có Instructions/Tables/Columns; ETL workbook có
  Instructions/ETL_Definitions/Column_Mappings, kể cả khi không khai báo mapping tường minh.
  Mỗi Instructions có đúng một Template Version. Sheet/header bắt buộc phải đúng tên/case
  theo template; header trùng hoặc không hỗ trợ bị báo lỗi, không bỏ qua âm thầm.
  Dòng hoàn toàn trống được bỏ qua; dòng có dữ liệu thiếu required field vẫn là lỗi.
  Required fields theo FR-023/FR-031/FR-042; cột optional có trong template nhưng cell có thể trống.
  Boolean chỉ nhận TRUE/FALSE; ngày ISO 8601, không đoán locale hoặc serial date Excel.

- **FR-022**: Table flow: chọn target connection → upload → parse/validate → preview table/column
  → SQL DDL preview → Confirm Create Tables → execute → kết quả/lịch sử. Một workbook chứa nhiều table.
- **FR-023**: Table Definition hỗ trợ hợp đồng sau, composite primary key và validation
  duplicate table/column, ordinal/type/length/precision/scale, nullable/key/default và connection/schema.

| Nhóm | Trường template | Tính bắt buộc và ý nghĩa |
| --- | --- | --- |
| Table | Target Connection Code | Bắt buộc; phải trùng target chọn trên UI trong lần xác nhận |
| Table | Target Schema | Có điều kiện; PostgreSQL kế thừa schema connection nếu bỏ trống; MySQL dùng Database Name, không trỏ DB khác qua schema |
| Table | Table Name | Bắt buộc, unique theo connection/schema trong workbook |
| Table | Table Description | Tùy chọn |
| Column | Target Connection Code, Target Schema, Table Name | Tham chiếu đúng table cha, schema theo quy tắc trên |
| Column | Column Name, Column Order, Data Type | Bắt buộc; tên và ordinal nguyên dương unique trong table |
| Column | Length, Precision, Scale | Có điều kiện theo kiểu, scale không vượt precision |
| Column | Nullable, Primary Key | Boolean bắt buộc, primary key không nullable; nhiều cột key tạo khóa ghép |
| Column | Default Value | Tùy chọn, literal đúng kiểu, không là biểu thức SQL tùy ý |
| Column | Column Description | Tùy chọn |

- **FR-024**: Công bố type hỗ trợ theo target dialect; tối thiểu integer, bigint, decimal,
  varchar, text, boolean, date, timestamp. Type/precision không hỗ trợ báo lỗi, không tự đổi kiểu im lặng.
- **FR-025**: SQL Preview đúng dialect PostgreSQL/MySQL và cấu hình validated; không cần người dùng sửa DDL.
- **FR-026**: Workbook lỗi cấu trúc/ngữ nghĩa không tạo table nào; execute kiểm tra lại quyền,
  connection, table existence để bắt thay đổi sau preview.
- **FR-027**: Table đã tồn tại báo lỗi riêng, không ALTER/DROP/xóa dữ liệu; lỗi runtime một table
  không che kết quả table khác. Sau validation toàn workbook, kết quả từng table độc lập,
  không hứa transaction toàn workbook.
- **FR-028**: Có Upload/Creation History, SQL Preview, Table Detail, Operation Result;
  lưu thời điểm, target, workbook version, SQL và kết quả/error từng table không có secrets.

#### DAG Builder và deployment

- **FR-029**: Flow upload → parse/validate → kiểm tra connection/table/file → mapping →
  preview cấu hình/schedule/strategy → Confirm Generate DAG → generate/deploy → kiểm tra
  Airflow nhận diện → Deployment Result → Open in Airflow.
- **FR-030**: ETL workbook chứa nhiều DAG; mỗi DAG MVP một source/một target và mapping riêng,
  có validation/deployment result từng DAG.
- **FR-031**: ETL Definition hỗ trợ bảng sau, không có option Collection Method riêng.

| Nhóm | Trường template | Tính bắt buộc và ý nghĩa |
| --- | --- | --- |
| Định danh | DAG ID, DAG Description | ID bắt buộc/unique, description tùy chọn |
| Nguồn | Source Type | Suy ra DB/CSV/TXT từ reference; nếu nhập phải khớp |
| DB source | Source Connection Code, Source Schema, Source Table | Connection/table bắt buộc cho DB; schema theo dialect |
| File source | Source File Reference | Bắt buộc với file, không đồng thời khai báo DB source |
| Target | Target Connection Code, Target Schema, Target Table | Connection/table bắt buộc; schema theo dialect |
| Schedule | Schedule, Start Date, Timezone, Catchup | Cron hoặc Manual; cron cần Start Date; timezone hợp lệ, catchup boolean |
| Load | Load Strategy, Conflict Key | Strategy bắt buộc, key một/nhiều cột bắt buộc với UPSERT |
| Execution | Batch Size, Retry Count, Retry Delay | Tùy chọn dùng mặc định công bố; batch > 0, retry nguyên không âm, delay có đơn vị |
| Activation | Enabled/Paused | Mặc định paused; enabled không tự kích hoạt DAG mới |
| Filtering | Optional Source Filtering | Tùy chọn cho DB, tập phép lọc có kiểm soát, không SQL tùy ý |
| Mapping | Column Mapping Reference | Liên kết Column_Mappings theo DAG ID; bỏ trống chỉ khi auto-map chắc chắn |

- **FR-032**: Suy ra source type từ connection/file reference, chặn thiếu nguồn/nguồn kép/type sai;
  file dùng parser metadata đã được xác nhận của reference đó.
- **FR-033**: Kiểm tra connection/source readable, target tồn tại/writable, cột/type/key/
  mapping/filter; target thiếu hướng dẫn Table Management, không tự tạo. Source=target cùng
  physical table bị chặn kể cả qua hai Connection Code. Target MySQL phải là InnoDB;
  nguồn MySQL cần InnoDB để bảo đảm snapshot. Không tự chuyển storage engine cho table cũ.

- **FR-034**: Cron/manual, Start Date/Timezone/Catchup được validate và preview; cảnh báo
  start date quá khứ/catchup có thể tạo backfill; lịch thực do Airflow điều phối.
- **FR-035**: Phân biệt Validation Failed, Ready to Deploy, Deployment Pending, Deployed,
  Deployment Failed, Parse Error; lỗi parse/generate/transfer/timeout có lý do, không gộp deployment với execution.
- **FR-036**: DAG ID unique trên cả Airflow; managed DAG update cần preview khác biệt/xác nhận,
  giữ revision history; chặn ghi đè external DAG hoặc redeploy khi DAG có run active.
- **FR-037**: DAG mới luôn paused, activate cần xác nhận riêng sau deploy, nêu lịch/catchup/load/ủy quyền dữ liệu.
- **FR-038**: Chỉ Deployed khi Airflow parse/đăng ký đúng DAG và revision mới;
  file ghi xong hoặc DAG ID bản cũ còn tồn tại không đủ điều kiện.
- **FR-039**: Trong 120 giây phải xác minh deployment hoặc báo lỗi/timeout, không pending vô hạn.
  Airflow API unavailable/timeout sau gửi yêu cầu nghĩa là chưa xác định kết quả, không chứng minh
  DAG chưa được đăng ký. Hiển thị lỗi API và revision chưa xác minh; đối soát cùng deployment ID
  khi kết nối lại trước retry, không tạo bản triển khai mới hoặc báo Deployed từ dữ liệu cache.
  Parse Error chỉ khi có bằng chứng lỗi parse; redeploy thất bại chỉ rõ revision cũ còn dùng được không.

- **FR-040**: Lưu Definition gốc, template version, cấu hình xác nhận, revision và deployment result,
  liên kết được managed DAG với Definition tương ứng.
- **FR-041**: Gửi lại cùng xác nhận generate/deploy không tạo revision dư; đổi cấu hình cần validation/xác nhận mới.

#### Mapping và transformations

- **FR-042**: Column_Mappings nằm trong ETL workbook, không cần file riêng; gồm DAG ID,
  Source Column, Target Column, Optional Transformation Type, Optional Default Value, Enabled.
  DAG ID/Target Column/Enabled bắt buộc; Source Column tùy transformation.
- **FR-043**: MVP có Direct Mapping, Constant Value, NULL Handling và type conversion trong
  danh mục công bố; transformation trống là Direct Mapping; không arbitrary Python expression.
- **FR-044**: Không có dòng mapping enabled cho DAG thì implicit mapping theo tên cột chính xác
  và tương thích kiểu; không tự đổi case. Column_Mappings vẫn tồn tại với header, có thể rỗng.
  Có mapping enabled thì dùng tập tường minh, không tự bổ sung cột ngoài tập này.
  Target không mapping chỉ hợp lệ nếu nullable/default an toàn; nguồn thừa có thể bỏ và phải
  hiển thị preview. Mơ hồ phải báo lỗi hoặc người dùng sửa/xác nhận mapping cụ thể trước deploy.

- **FR-045**: Target column không có nhiều mapping enabled; cột phải tồn tại; disabled không áp dụng;
  target bắt buộc thiếu mapping/default hợp lệ bị từ chối.
- **FR-046**: Default đúng kiểu, phân biệt NULL/chuỗi rỗng; Constant Value không cần source,
  NULL Handling chỉ thay NULL, không tự thay mọi giá trị falsy.
- **FR-047**: Không cắt chuỗi/làm tròn/mất dữ liệu âm thầm; conversion lỗi dừng run, có vị trí;
  kiểm tra schema lại trước mỗi run.
- **FR-048**: Source Filtering MVP cho DB: điều kiện có cấu trúc trên cột với `=`, `!=`, `<`,
  `<=`, `>`, `>=`, `IN`, `IS NULL`, `IS NOT NULL`, kết hợp AND, kiểm tra kiểu operand;
  không SQL fragment/join/subquery/filter file.

#### Load và ETL Engine

- **FR-049**: Chọn APPEND/UPSERT/FULL_REFRESH; preview transaction/retry/rerun/partial failure theo BR-07/BR-08.
- **FR-050**: APPEND chỉ insert, không xóa dữ liệu cũ; cảnh báo duplicate; unique violation
  làm fail, không tự UPSERT/skip dòng.
- **FR-051**: APPEND retry chỉ tiếp tục các batch chưa commit trên cùng dataset bất biến khi
  có bằng chứng bền vững xác định tiến độ. Không có checkpoint đáng tin hoặc commit không rõ
  thì dừng với thông báo cần đối soát, không tự replay, xóa bù hoặc coi exception là rollback chắc chắn.
  Cùng logical run không được tự tạo dataset mới sau khi đã ghi target; rerun mới vẫn append mới có cảnh báo.

- **FR-052**: UPSERT cần conflict key khớp trọn một primary/unique key thật trên target,
  hỗ trợ khóa ghép ở hai DB. Thiếu unique key chặn validation và runtime preflight;
  không tự CREATE UNIQUE INDEX/ALTER hoặc downgrade thành APPEND. Key NULL/trùng trong dataset
  bị từ chối trước ghi target; so sánh duplicate theo equality/collation của target.
  Unique key khác xung đột không được update nhầm bản ghi; rerun cùng dataset/key không tạo duplicate.

- **FR-053**: FULL_REFRESH xác nhận đúng scope/revision và vòng đời quyền theo BR-08, hoàn tất extraction, validation toàn
  dataset và kiểm tra số dòng trước thay dữ liệu target. Extraction/parse/validation thất bại
  giữ target nguyên trạng. Công bố dữ liệu mới phải atomic đối với người đọc theo isolation
  được hỗ trợ: thấy dữ liệu cũ hoặc mới, không thấy target rỗng/nửa chừng đã commit.
  Không dùng TRUNCATE rồi commit từng batch vào target; lỗi công bố giữ/phục hồi cũ.
  Connection/commit mất tín hiệu cần đối soát trước retry; chưa xác minh không báo thành công.

- **FR-054**: Dataset zero rows cần quyền làm rỗng riêng; recovery không tự hoàn tất phải
  báo cần can thiệp, giữ artifact phục hồi, không tiếp tục ghi đè.
- **FR-055**: Không đọc toàn dataset vào RAM hoặc fetchall() dữ liệu lớn. Mọi DB-to-DB:
  một snapshot nguồn → chunked extraction → disk staging hoàn tất → mapping/validation
  → batched target loading. Chỉ bắt đầu ghi target sau khi staging nguồn hoàn tất và được xác minh.
  Source extraction thất bại không ghi target ở cả ba strategy; staging chưa hoàn tất không được reuse.

- **FR-056**: File-to-DB: streaming reader → mapping/validation → batch loading; batch cấu hình được.
- **FR-057**: Staging ở disk/volume thật, không memory-only/tmpfs; namespace theo DAG ID/Run ID,
  attempt có artifact riêng khi ghi lại, không dùng logical date làm định danh duy nhất.
  Retry cùng Run ID chỉ reuse dataset hoàn tất cùng checksum/schema/revision đã chốt;
  rerun mới có Run ID/path mới, không ghi đè file run trước.

- **FR-058**: Không dataset lớn qua XCom; chỉ metadata nhỏ/tham chiếu không chứa secrets.
- **FR-059**: Có giới hạn memory/disk, batch commit/retry/duplicate control theo policy;
  vượt quota báo lỗi rõ, không tiêu thụ tài nguyên vô hạn.
- **FR-060**: Xử lý Disk Full, Source/Target Connection Lost, Invalid Data, Type Conversion Failure,
  Duplicate Key, Interrupted Execution, Retry, Canceled Task, Partial Load; báo tiến độ commit/recovery thật.
- **FR-061**: Có retention/cleanup/failure recovery; không xóa artifact active, retry hoặc recovery còn cần;
  quan sát được kết quả dọn dẹp, không dùng cleanup để che lỗi.
- **FR-062**: Metrics: Extracted Rows, Loaded Rows, Failed Rows, Duration, Staging Bytes,
  Execution Status, Error Summary; dựa dữ liệu thật, không cộng trùng attempts, không biết khác 0.
  Loaded Rows đếm bản ghi nguồn đã commit/công bố, không lấy affected rows theo dialect làm số UPSERT.

#### Monitoring, Dashboard và Settings

- **FR-063**: List/search/filter DAG theo ID, paused/active, managed/external, latest run status.
- **FR-064**: Details có schedule, timezone nếu có, paused/active, latest run, history,
  task status, duration/error; lấy từ Airflow thật.
- **FR-065**: Managed DAG liên kết Definition/revision; external không có Definition giả;
  external ETL metrics không có phải không khả dụng, không gán 0.
- **FR-066**: Có Trigger DAG, Pause/Unpause, View Logs, Open in Airflow; managed cho điều khiển,
  external chỉ xem và mở Airflow trong MVP theo giả định AS-07.
- **FR-067**: Trigger một logical run có identity bền, chống gửi lặp; tiếp nhận khác
  execution success. Khi managed DAG paused, manual run queued và chỉ thực thi sau
  thao tác unpause được xác nhận riêng. Ứng dụng không tự unpause/kích hoạt lịch từ
  manual trigger; UI phải nói rõ điều kiện chờ. Với cron FULL_REFRESH, activation
  vẫn cần SCHEDULED authority đúng scope; ONCE không cấp quyền bật lịch.
- **FR-068**: Pause/unpause chỉ success sau Airflow xác nhận; pause không cancel run đang chạy;
  không gộp canceled/upstream-failed thành success.
- **FR-069**: Log theo DAG/run/task/attempt, che secrets, giới hạn tải; thiếu log có lý do,
  không giả dữ liệu khi Airflow down.
- **FR-070**: Open in Airflow đúng DAG ID/base URL browser truy cập được, không hostname chỉ có trong network container.
- **FR-071**: Dashboard KPI thật: Total/Active/Paused DAGs, Total DAG Runs, Successful/Failed/Running Runs, Success Rate.
- **FR-072**: Date range/timezone, Manual Refresh, Auto Refresh, lần cập nhật cuối và
  loading/error/stale state; lỗi kết nối không biến thành số 0.
- **FR-073**: Đếm DAG và số execution theo Hourly/Daily/Weekly/Monthly/Custom/Manual;
  Unknown nếu không xác định, không nhầm DAG count với run count.
- **FR-074**: Success/failure theo thời gian, recent runs có ID/status/start/end/duration,
  click mở details hoặc Airflow.
- **FR-075**: Last successful run, next scheduled run nếu Airflow cung cấp;
  lifetime và date-filtered có nhãn riêng theo BR-11.
- **FR-076**: Phân biệt success/failed/running/queued/other; Total DAG Runs bao gồm mọi trạng thái.
- **FR-077**: Tổng hợp đủ phân trang; thiếu lịch sử/phân loại phải incomplete/unknown và nêu phạm vi,
  không trình bày tổng thiếu như chính xác.
- **FR-078**: Dữ liệu thiếu là Not available/Incomplete data, dữ liệu cũ là Stale;
  không truy vấn trực tiếp bảng nội bộ Airflow metadata DB.
- **FR-079**: Settings gồm Default Batch Size, Dashboard Refresh Interval, Default Timezone,
  Staging Retention, Airflow Connectivity Status, Application Information.
- **FR-080**: Validate settings/range/unit, lưu bền, tách status chỉ đọc khỏi cấu hình;
  phạm vi áp dụng thay đổi theo BR-14.

#### Môi trường, mẫu và tài liệu

- **FR-081**: Một lệnh `podman compose up --build -d` chạy Frontend/Backend/Airflow/PostgreSQL/
  MySQL và phụ trợ cần thiết; không thêm lệnh thủ công sau initialization/healthchecks.
- **FR-082**: PostgreSQL tách logical databases cho application metadata/Airflow metadata/ETL test;
  MySQL dùng ETL test; không trộn dữ liệu nghiệp vụ với bảng Airflow nội bộ.
- **FR-083**: Persistent volumes: database, Airflow logs, generated DAGs, uploads, staging;
  tự init/migrate/configure Airflow/seed source-target và sample connections;
  seed chạy lại an toàn, connection mẫu dùng địa chỉ service nội bộ đúng.
- **FR-084**: Sample templates/datasets hỗ trợ table khác nhau cùng server, cross-server khác loại,
  mapping khác tên, NULL, khóa ghép, nhiều batch và dữ liệu lỗi.
- **FR-085**: Có unit/integration/end-to-end tests tự động và tái hiện; ETL dùng DB thật,
  DAG đăng ký/thực thi trên Airflow thật; chưa chạy không báo PASS.
- **FR-086**: README, kiến trúc, API documentation, Excel template specification, troubleshooting,
  báo cáo kiểm thử bằng tiếng Việt; UI/Excel Template bằng tiếng Anh.
- **FR-087**: Hướng dẫn startup/connections/workbook/mapping/load/staging/recovery/logs/giới hạn;
  tài liệu đồng bộ, không nhận chức năng mock là đã hoàn thành.

- **FR-088**: Tách Chunk Size (số dòng tối đa mỗi lần đọc nguồn) và Batch Size (số dòng tối đa
  mỗi lần ghi); mặc định mỗi giá trị 1.000, có thể khác nhau. Batch Size trong Excel không ngầm
  đổi chunk extraction; giới hạn byte có thể chia nhỏ thêm. Dòng đơn vượt giới hạn phải lỗi rõ,
  không tăng RAM vô hạn. Chunk Size là cấu hình runtime, không thêm UI setting bắt buộc.
- **FR-089**: Dataset DB-to-DB có identity, source snapshot/time, schema/mapping revision,
  row count, danh sách file và checksum, trạng thái incomplete/complete. Complete chỉ khi
  mọi file đã ghi bền và xác minh; thiếu/truncated/corrupt file làm fail trước load/retry.
- **FR-090**: Snapshot nguồn phải nhất quán xuyên chunk; lỗi kết nối làm snapshot extraction
  chưa hoàn tất bị loại bỏ. Retry extraction lấy snapshot mới toàn bộ trước khi target bị ghi,
  không ghép chunk của hai snapshot. Không cần COUNT(*) trên nguồn sống sau extraction.
- **FR-091**: Thay schema nguồn/đích được phát hiện trước run; fingerprint bao gồm cột/kiểu/
  nullable/key được dùng. Schema drift làm bản validation hết hiệu lực và yêu cầu xác nhận lại;
  thay đổi giữa extraction làm fail nếu không còn bảo đảm snapshot/schema, không tự sửa mapping/DDL.
- **FR-092**: Header CSV/TXT bắt buộc unique, không rỗng khi Header Present true;
  trim/BOM normalization được công bố, không tự sửa tên hoặc duplicate. Sai delimiter/số trường/
  unmatched quote/encoding làm fail, có physical line và record index khi record nhiều dòng.
  Một cột là hợp lệ khi đúng cấu hình; không thể suy ra sai delimiter chỉ từ số cột nếu không có schema kỳ vọng.
- **FR-093**: Đối soát Extracted Rows/Validated Rows/Loaded Rows cho dataset đã filter;
  thành công yêu cầu mọi dòng hợp lệ được xử lý đúng policy, không skip. APPEND so delta số dòng
  và bản ghi thêm khi không có writer ngoài; UPSERT so key/giá trị, không dùng delta row count
  làm loaded count; FULL_REFRESH count/giá trị target bằng dataset mới trước báo success.
- **FR-094**: Quota tính cả artifact hoàn tất/lỗi/đang bảo vệ; kiểm tra trước chạy và trong ghi.
  Disk full, I/O error, mất volume/quyền truy cập hoặc checksum sai dừng an toàn; không fallback RAM,
  không xóa dữ liệu phục hồi để lấy chỗ. Nếu xảy ra trước load thì target không đổi;
  sau commit thì báo partial/recovery theo strategy, không infinite retry lỗi storage.
- **FR-095**: Kill không chạy cleanup hook vẫn phải recovery được: sau restart/heartbeat hết hạn,
  xác minh task/process cũ đã chết trước thu hồi ownership hoặc xóa file. Không suy run stale là
  chắc đã rollback. Cleanup orphan sau đối soát, bảo vệ commit không rõ và artifact recovery;
  không cần dựa vào thao tác thủ công trong trường hợp phục hồi bình thường.
- **FR-096**: Airflow API lỗi khi trigger/pause/deploy phải phân biệt từ chối và kết quả chưa xác định.
  Giữ request/run/deployment identity, đối soát trước gửi lại; không blind retry tạo duplicate.
  Scheduled runs hiện hữu có thể tiếp tục trong Airflow khi UI/backend/API mất liên lạc;
  Dashboard/Monitoring báo không khả dụng/stale, không ghi đè trạng thái Airflow bằng trạng thái cục bộ.
- **FR-097**: Update/redeploy managed DAG cần chốt revision gốc để phát hiện stale edit,
  kiểm tra không active run và không có update cạnh tranh; tạm dừng nhận run mới trong cửa sổ
  chuyển revision. Chỉ khôi phục trạng thái active cũ khi revision mới đăng ký và được xác minh,
  quyền FULL_REFRESH còn hợp lệ; lỗi giữ paused và nêu revision cuối xác minh.
- **FR-098**: Duplicate table/DAG definitions trong workbook bị từ chối, không last-row-wins;
  Columns tham chiếu đúng table composite identity, mapping tham chiếu DAG trong cùng workbook.
  Orphan/cross-sheet reference sai là lỗi; Source/Target Connection Code và file reference
  được kiểm tra ở registry. Row/column location là vị trí Excel thật, kể cả dòng trống đã bỏ qua.
- **FR-099**: First init/migrations/seed/config Airflow chạy đúng phụ thuộc và idempotent;
  healthcheck DB phải kết nối/truy vấn được, Backend cần schema/migration sẵn sàng, Airflow phải
  cung cấp chức năng tương ứng. ETL connection ngoài mẫu hỏng không làm core health giả là healthy/unhealthy;
  hiển thị riêng connectivity. Internal traffic dùng service name/port container, browser dùng host URL.
- **FR-100**: Restart dùng lại volume và secret key bền, không tự regenerate khóa làm mất quyền
  giải mã connections. Không tự xóa/reset volume khi migration/init lỗi; lỗi readiness có chẩn đoán.
  Recovery startup đối soát runs/deployments/staging trước retry/cleanup; phải kiểm thử restart
  giữa extraction, sau batch commit và trong FULL_REFRESH.
### Yêu cầu phi chức năng

- **NFR-001 — Ngôn ngữ và nhận diện**: Markdown/prompt/giải thích/báo cáo tiếng Việt;
  UI và Excel sheet/header/hướng dẫn tiếng Anh, giữ thuật ngữ kỹ thuật; không branding bên thứ ba.
- **NFR-002 — Khả dụng**: Desktop-first, responsive; tại 1440 px và 390 px, hành động chính
  truy cập được, không bị che; bảng rộng cuộn trong vùng chứa. Form có label/lỗi gắn trường,
  wizard có tiến độ, hành động chính dùng được bằng bàn phím; có đủ empty/loading/success/failure.
- **NFR-003 — An toàn**: Không plaintext password trong DB; không credentials ở DAG source,
  API response/log/XCom. Giá trị SQL parameterized, identifiers kiểm tra theo dialect;
  từ chối SQL/Python tùy ý, path traversal, workbook thực thi code.
- **NFR-004 — Tài nguyên**: Upload/preview/extract/map/load dùng bộ nhớ hữu hạn; có giới hạn
  theo cả số dòng và byte, không chỉ batch size. Công bố quota upload/RAM/disk, free-space reserve
  và số run tối đa trước implementation; thiếu cấu hình dùng mặc định hữu hạn của môi trường mẫu,
  không vô hạn. Nghiệm thu dataset lớn hơn hai lần RAM worker, ít nhất 20 batch, có disk staging.
  Giá trị quota/định dạng vật lý/thư viện thuộc Plan; hành vi vượt quota theo FR-094 là bắt buộc.

- **NFR-005 — Toàn vẹn**: Không DROP/DELETE/TRUNCATE ngoài ủy quyền; không conversion mất dữ liệu
  âm thầm; partial failure/retry/rerun theo BR-07–BR-09; target successful run đúng giá trị/khóa/NULL.
- **NFR-006 — Quan sát**: Definition/deployment/run/task đối chiếu được timestamps/status/attempt/
  metrics/error; log che secrets; không biết là không khả dụng, không giả 0/success.
- **NFR-007 — Độ bền**: Restart không mất metadata/file/log/DAG cần lưu; worker ngắt không gây
  replay commit không kiểm soát; retention không phá active/recovery artifacts.
- **NFR-008 — Tích hợp thật**: Airflow orchestration/scheduling/execution, ưu tiên public API
  tương thích phiên bản sẽ chọn tại Plan, không truy cập bảng nội bộ làm nghiệp vụ;
  không scheduler thay thế, không mock thay nghiệm thu.
- **NFR-009 — Phản hồi**: Với dữ liệu mẫu trong môi trường nghiệm thu đã công bố,
  95% thao tác danh sách/chi tiết/preview 100 dòng trả kết quả trong 3 giây; Test Connection
  kết quả/timeout trong 30 giây; deployment đăng ký hoặc báo lỗi/timeout trong 120 giây.
  Tác vụ dài có trạng thái, không chặn UI đến khi ETL kết thúc.
- **NFR-010 — Tái lập và bảo trì**: Test có input/cấu hình tài nguyên/lệnh/kết quả tái hiện;
  Plan giải thích quyết định quan trọng, kiến trúc đơn giản, module rõ và typing theo Constitution IV.

### Quy tắc nghiệp vụ

- **BR-01 — Định danh**: Connection Code trim, so sánh không phân biệt hoa thường;
  DAG ID theo Airflow; tên table/column theo dialect, không tự đổi hoa/thường làm đổi đối tượng.
  Không xóa/đổi định danh gây dependency mồ côi.
- **BR-02 — Preview/xác nhận**: Preview không thay DB/deploy. Xác nhận gắn workbook revision,
  target và cấu hình; input đổi làm xác nhận cũ mất hiệu lực; revalidate điều kiện dễ thay đổi trước execute.
- **BR-03 — Workbook**: Validation toàn workbook trước generate/create/deploy;
  lỗi runtime sau xác nhận báo riêng từng table/DAG, không rollback ngầm đối tượng thành công
  hoặc báo toàn workbook thành công khi có phần lỗi.
- **BR-04 — Lịch**: Default timezone UTC, Catchup false, DAG mới paused. Manual không có next
  scheduled run. Cron/Start Date dùng IANA timezone; DST/catchup theo Airflow, preview tác động
  trước xác nhận, không tự xây lịch khác.
- **BR-05 — Mapping**: Mapping enabled tường minh ưu tiên; auto-map chỉ tên duy nhất/type tương thích.
  Target không mapping chỉ được khi nullable/default hợp lệ; key UPSERT phải có giá trị ổn định,
  không NULL; không join nhiều source trong MVP.
- **BR-06 — Giao dịch**: Validation lỗi không tác động target. APPEND/UPSERT commit từng
  batch, lỗi rollback batch chưa commit; batch trước có thể còn và phải báo partial load.
  FULL_REFRESH có thể ghi batch vào khu vực chuẩn bị nhưng công bố target chỉ có một ranh giới
  commit cho toàn replacement, không commit từng batch vào target đang phục vụ.
  Không hứa atomic toàn workbook; không coi lỗi mạng sau COMMIT là bằng chứng rollback.

- **BR-07 — Retry/rerun**:

  | Strategy | Commit và partial failure | Retry cùng logical run | Rerun mới |
  | --- | --- | --- | --- |
  | APPEND | Chỉ thêm, giữ batch đã commit và báo partial | Chỉ tiếp tục nếu dataset/tiến độ commit chắc chắn; không rõ commit dừng đối soát, không auto-replay | Thêm lại với cảnh báo duplicate; unique violation làm fail, không skip/update |
  | UPSERT | Insert/update theo key, batch cũ có thể đã đổi target | Cho áp dụng lại cùng dữ liệu ổn định/key; nguồn thay đổi không xác định thì dừng revalidate | Cùng dữ liệu/key không tăng số key, không xóa key ngoài nguồn |
    | FULL_REFRESH | Chuẩn bị/validate mới trước công bố, bảo toàn/phục hồi cũ khi lỗi | Chỉ tiếp tục/tạo lại khi trạng thái xác định và quyền của run còn hiệu lực; recovery công bố trước thử tiếp | Manual trigger/rerun mới cần ONCE mới; run mới theo lịch chỉ dùng SCHEDULED đúng phạm vi; kiểm tra empty và rủi ro như lần đầu |

  Retry không vượt Retry Count; lỗi không retry-safe được dừng sớm với lý do.
  An toàn dữ liệu ưu tiên hơn chạy đủ số retry.
- **BR-08 — Ủy quyền thay thế**: FULL_REFRESH xác nhận connection/schema/table/revision,
  toàn bộ target, chạy một lần hay theo lịch; scope/target/strategy/revision đổi cần xác nhận lại.
  Zero-row refresh cần quyền riêng, lỗi nguồn không là empty. Nếu dependency target không cho
  bảo toàn/khôi phục an toàn, phải chặn với lý do, không tự DROP/DELETE/TRUNCATE để vượt qua.
  Với scope ONCE, khi tiếp nhận yêu cầu chạy phải reservation (giữ quyền độc quyền) gắn
  với một logical run có Run ID ổn định trước khi tạo hoặc khởi động run. Một quyền chỉ
  được gắn với một Run ID; hai yêu cầu khác nhau tranh cùng quyền chỉ một yêu cầu được
  chấp thuận, yêu cầu còn lại bị từ chối trước khi khởi động. Gửi lặp cùng yêu cầu hoặc
  retry cùng logical run dùng lại binding đã chốt, không tạo reservation hay Run ID mới.
  Quyền ONCE không được chuyển sang Run ID khác hoặc trả về chưa sử dụng sau reservation.
  Retry cùng run chỉ được dùng quyền còn hiệu lực, chưa bị thu hồi và đáp ứng BR-07,
  kể cả retry extraction trước khi target được ghi; không tự thay dataset sau target commit.
  Thành công đã xác minh tiêu thụ quyền. Khi run kết thúc thất bại không còn retry hoặc
  bị hủy đã xác minh, quyền đóng vĩnh viễn cho lần chạy đó, dù target chưa thay đổi.
  Rerun/run mới luôn cần quyền ONCE mới. Commit chưa rõ giữ quyền chờ đối soát gắn run cũ,
  không giải phóng hoặc replay; chỉ đóng/tiêu thụ sau khi xác định kết quả thật.
  Quyền SCHEDULED chỉ áp dụng cho run do Airflow tạo theo lịch đã xác nhận của đúng DAG,
  ETL revision, physical target và strategy FULL_REFRESH. Manual trigger/rerun mới không
  thuộc quyền này và cần ONCE riêng; retry cùng run định kỳ chỉ được tiếp tục khi an toàn
  và quyền còn hiệu lực. Mỗi run định kỳ chốt tham chiếu quyền trong binding riêng;
  thành công của một run không tiêu thụ toàn bộ quyền lịch cho các run định kỳ kế tiếp.
  Thay DAG/revision/target/strategy/schedule/timezone/start date/catchup hoặc phạm vi
  ủy quyền làm quyền SCHEDULED cũ không hợp lệ; phải xác nhận lại trước run kế tiếp.
  allow_empty mặc định false và cần xác nhận riêng về hậu quả làm rỗng toàn target.
  Khi được chấp thuận, quyền này gắn cùng authorization và phạm vi: ONCE chỉ logical run
  đã reservation; SCHEDULED cho các run theo lịch trong phạm vi còn hiệu lực, không cho
  manual run. Xác nhận SCHEDULED phải nêu rõ mọi run theo lịch trong phạm vi này có thể
  làm rỗng target khi dataset rỗng hợp lệ. Thay scope hoặc thu hồi làm quyền allow_empty
  cũ không hợp lệ. Không được tự bật allow_empty từ việc chọn FULL_REFRESH; extraction,
  parse hoặc validation lỗi không được diễn giải thành dataset rỗng.
  Thu hồi quyền chặn run mới và retry ghi mới. Phải kiểm tra lại quyền và chốt điểm chấp
  thuận bắt đầu transaction replacement với thứ tự rõ ràng so với thu hồi: thu hồi
  được ghi nhận trước điểm này thì run không được thay dữ liệu; transaction đã được
  chấp thuận trước thu hồi có thể hoàn tất hoặc rollback an toàn theo BR-06/BR-15.
  Thu hồi không tự hủy hoặc đảo ngược transaction đang chạy; UI phải nêu giới hạn này.
  Với commit chưa rõ, chỉ được đối soát kết quả hoặc rollback an toàn khi còn khả thi,
  không replay replacement bằng quyền đã thu hồi. Thu hồi không xóa binding, marker
  hoặc artifact còn cần phục hồi. Đã xác minh replacement commit của một logical run
  thì retry/clear cùng run chỉ được đối soát kết quả đã có, không replacement lần hai.

  Các trạng thái nghiệp vụ phải phân biệt quyền đã cấp, ONCE đã reservation, run đã
  được chấp thuận replacement, chờ đối soát, ONCE đã tiêu thụ/đóng và quyền bị thu hồi.
  Reservation/binding và trạng thái này phải lưu bền qua restart; timeout, mất heartbeat
  hoặc mất phản hồi tạo run không tự giải phóng quyền, phải đối soát cùng Run ID.
  Cơ chế transaction/khóa và schema thực hiện các ranh giới trên được chọn tại Plan.

  **Tiêu chí chấp nhận vòng đời quyền**:
  - Hai yêu cầu khác nhau dùng cùng ONCE chỉ một yêu cầu được reservation; gửi lại cùng
    yêu cầu dùng cùng Run ID. Run không nhận quyền không được bắt đầu replacement.
  - Extraction lỗi trước target ghi có thể retry cùng run khi quyền còn hiệu lực;
    run kết thúc thất bại/hủy không chuyển quyền sang run mới, rerun cần ONCE mới.
  - Replacement commit thành công chỉ một lần cho mỗi logical run; retry/clear không
    thay dữ liệu lần nữa, kể cả khi source đã đổi.
  - Commit mất phản hồi/restart giữ quyền và artifact chờ đối soát; xác minh đã commit
    thì ghi kết quả đã tiêu thụ, chưa xác định thì không replay hoặc giải phóng quyền.
  - Run định kỳ chỉ dùng SCHEDULED đúng phạm vi; manual run thiếu ONCE bị chặn.
    Dataset rỗng chỉ thay target khi allow_empty được xác nhận riêng và còn hiệu lực.
  - Thu hồi trước điểm chấp thuận replacement chặn ghi; thu hồi sau điểm đó không
    hứa rollback transaction đã bắt đầu. Retry sau thu hồi không được ghi mới nhưng
    vẫn đối soát được kết quả. Thay phạm vi ủy quyền phải xác nhận lại trước ghi mới.
- **BR-09 — Đồng thời**: Mỗi DAG chỉ một run đang thực thi; run tiếp theo chờ theo cơ chế
  Airflow, không bị mất hoặc tự gộp. Các managed DAG khác nhau cùng physical target phải
  chờ quyền ghi độc quyền xuyên mọi strategy, kể cả qua connection code khác nhau.
  Mặc định timeout chờ 300 giây thì fail có lý do; không chiếm quyền của run cũ chưa xác minh kết thúc.
  Physical target xác định từ DB server/database/schema/table đã resolve, không chỉ Connection Code;
  không resolve chắc chắn alias thì chặn cấu hình có thể xung đột. Không cam kết phối hợp writer
  bên ngoài ứng dụng; nghiệm thu integrity yêu cầu không có writer ngoài trong cửa sổ load/đối soát.
  Source=target cùng physical table bị từ chối; không distributed ETL.

- **BR-10 — Ownership/revision**: Không sửa cấu hình run đã bắt đầu; không redeploy managed DAG
  còn run active, không ghi đè external DAG. Failed redeploy chỉ rõ revision cũ còn dùng được hay không.
- **BR-11 — Thống kê Dashboard**:
  - Phạm vi mặc định mọi DAG Airflow quan sát được, gồm managed/external, có nhãn phạm vi.
  - Total DAGs là inventory hiện tại; Active là đã đăng ký, không paused và active theo Airflow;
    Paused là inventory paused. Trạng thái khác/không rõ hiển thị riêng, không ép Active+Paused=Total.
  - Date range mặc định 7 ngày, timezone Settings; chọn ngày gồm cả ngày cuối:
    từ 00:00 ngày đầu đến trước 00:00 ngày sau ngày cuối trong timezone đã chọn.
  - Run thuộc khoảng lọc theo start time thực tế; chưa start dùng queued/created time khi
    Airflow cung cấp, ghi rõ cơ sở thời gian. Thiếu cả hai là không xác định; không thay bằng
    logical date để giả thời gian thực. Run start ngoài khoảng không tính dù end trong khoảng.
  - Total DAG Runs đếm run duy nhất, gồm success/failed/running/queued/other;
    KPI từng trạng thái không đếm task. Success Rate = success/(success+failed) × 100%;
    mẫu số 0 là Not available; queued/running/other không vào mẫu số.
  - Lifetime dùng toàn lịch sử lấy đủ, khác metric lọc ngày; thiếu lịch sử phải incomplete.
    Biểu đồ theo ngày cùng mốc chọn run/timezone; recent runs sắp mới nhất theo mốc đó.
    Run running hiển thị elapsed duration có nhãn, không có end time giả.
- **BR-12 — Nhóm schedule**: Manual không có lịch định kỳ; preset Hourly/Daily/Weekly/Monthly
  và cron tương đương trong danh mục template phân nhóm tương ứng; cron hợp lệ khác là Custom,
  không diễn giải được là Unknown. DAG count dùng schedule hiện tại; run count dùng schedule
  lúc run nếu biết, thiếu lịch sử là Unknown, không giả dùng lịch hiện tại cho quá khứ.
- **BR-13 — Dòng lỗi/metrics**: Mặc định fail-fast, không skip/quarantine ngầm. Extracted Rows
  là số dòng đã đọc; Loaded Rows là dòng nguồn đã commit/công bố không đếm lặp retry;
  Failed Rows chỉ dòng xác định sai, không gán mọi dòng chưa xử lý là failed. Không biết là
  không khả dụng; Staging Bytes phản ánh hiện hữu/đỉnh dung lượng run nếu đo được.
- **BR-14 — Settings/retention**: Default Batch Size 1.000, refresh 30 giây, timezone UTC,
  Retry Count 0/Retry Delay 60 giây, staging retention 7 ngày sau terminal state nếu hết nhu cầu
  recovery, file nguồn không tham chiếu giữ 30 ngày. Đây là baseline giả định có thể chỉnh
  trước Plan. Refresh tối thiểu 5 giây; batch/retention nguyên dương, retry nguyên không âm.
  Default mới dùng cho cấu hình tạo sau đó, không tự đổi DAG deployed/run active; UI refresh
  dùng ở lần kế tiếp, retention không xóa artifact đang dùng/được bảo vệ recovery.

- **BR-15 — Khác biệt transaction PostgreSQL/MySQL**: Mọi target DML phải có rollback batch
  thực sự; target MySQL MVP dùng InnoDB, không dùng table engine không transactional.
  Không mặc định DDL hoặc TRUNCATE rollback giống DML; MySQL có implicit commit với các lệnh này.
  Table creation là thao tác độc lập từng table, không bảo đảm rollback toàn workbook.
  FULL_REFRESH chỉ công bố replacement đã chuẩn bị/validated trong một transaction target,
  giữ nguyên cấu trúc/quyền/constraints của table hiện hữu; không DROP/ALTER/rename table người dùng.
  Dependency, trigger có side effect ngoài giao dịch, hoặc storage engine không bảo đảm an toàn
  phải bị từ chối với lý do; không tắt constraint hoặc tự đổi engine để chạy tiếp.
- **BR-16 — Snapshot và staging**: Snapshot nguồn một table bao trùm toàn extraction và filter,
  có ngữ nghĩa consistent read trên PostgreSQL và MySQL/InnoDB; isolation thực hiện chọn tại Plan.
  Dataset complete là bất biến. Retry load dùng đúng dataset đó; mất staging sau target commit
  phải dừng đối soát, không tự lấy nguồn mới. Rerun luôn là Run ID mới và snapshot mới; chỉ khi
  nguồn không đổi mới được gọi là rerun cùng dataset. Không bảo đảm snapshot nhiều nguồn.
  Định dạng vật lý staging do Plan chọn; bắt buộc có schema/version, đọc chunk được, kiểm tra
  toàn vẹn và round-trip không mất NULL/Unicode/decimal/temporal theo BR-17.
  Không dùng CSV không schema hoặc stringify mọi kiểu rồi suy đoán lại. Dữ liệu nguồn không
  có key vẫn được extract bằng snapshot/cursor đúng, không phân trang OFFSET không ổn định qua nhiều snapshot.
- **BR-17 — Hợp đồng kiểu và giá trị**: NULL khác chuỗi rỗng, `0`, false và chuỗi literal `NULL`;
  NULL marker file chỉ nhận token không quoted, token quoted giữ chuỗi. Nếu delimiter/quote/parser
  không biểu diễn không mơ hồ được thì validation lỗi. Unicode giữ nguyên code point, không thay
  ký tự sai encoding bằng replacement character; loại BOM đầu file theo parser công bố.
  Decimal giữ chính xác và scale, không đi qua float; tràn/rút precision hoặc làm tròn mất giá trị
  phải lỗi. Integer ngoài miền target, ký tự NUL target không hỗ trợ, NaN/Infinity không được hỗ trợ
  trong MVP phải lỗi, không biến thành NULL. Date dùng ISO calendar date; datetime có offset được
  giữ cùng instant, chỉ chuyển timezone/loại offset bằng mapping tường minh. Datetime không timezone
  được giữ dạng naive, không tự suy từ schedule timezone; DST ambiguous/nonexistent khi cần gán timezone
  phải lỗi. Timestamp precision vượt target không được cắt âm thầm; MySQL zero date bị từ chối.
  Chỉ conversion trong danh mục được cho phép; không tương thích thì fail. UPSERT chỉ update cột
  non-key được mapping; cột không mapping của bản ghi cũ giữ nguyên, default áp dụng khi insert.
- **BR-18 — Validation toàn bộ và đối soát**: Với DB-to-DB, validate toàn dataset staging,
  kể cả duplicate/key equality theo target, trước ghi. Với file, full format/schema validation
  gắn checksum trước run; validation type theo dòng có thể phát hiện khi load, APPEND/UPSERT
  khi đó báo partial đúng BR-06. FULL_REFRESH phải validate toàn bộ dữ liệu trước công bố.
  Không COUNT(*) trên nguồn đã đổi sau snapshot để kết luận mất dòng. Dataset rỗng hợp lệ:
  APPEND/UPSERT thành công no-op, FULL_REFRESH chặn nếu chưa cho phép rỗng; lỗi nguồn không là empty.
  APPEND successful Loaded Rows bằng số dòng nguồn hợp lệ và target tăng tương ứng khi không writer ngoài;
  UPSERT đối soát tập key/giá trị, không đòi tổng target bằng source; FULL_REFRESH đối soát target mới.
- **BR-19 — Kill/recovery và cleanup**: Không giả định finally/cleanup hook chạy khi task bị kill.
  Mặc định heartbeat quá 120 giây chỉ là nghi ngờ, cần đối soát Airflow và quyền sở hữu trước hành động.
  Không xác minh worker cũ đã dừng hoặc không rõ commit thì giữ artifact/khóa bảo vệ và báo cần can thiệp;
  không tự phát lại/xóa target. Orphan incomplete được dọn sau xác minh, artifact complete theo retention.
  Sau restart, trong 120 giây kể từ khi dependencies sẵn sàng phải đối soát hoặc hiển thị lý do chưa thể;
  disk quota không cho phép xóa file recovery được bảo vệ để bắt đầu run khác.
- **BR-20 — Deployment/API và trigger**: Scheduled và manual đều tuân giới hạn đồng thời,
  quota, revision và ủy quyền; manual là run mới, retry task không phải trigger mới.
  Manual schedule không tự tạo periodic runs; manual trigger một cron DAG không đổi lịch của nó.
  Cron MVP là 5 trường, không seconds/macro tùy ý; `Manual` là giá trị tường minh.
  Start Date phải có offset hoặc timezone IANA đi kèm; mâu thuẫn offset/timezone bị báo lỗi.
  API lỗi không tự pause/stop execution Airflow; lệnh chưa rõ kết quả cần reconcile cùng identity.
  Nút retry deployment không xóa parse error bằng trạng thái giả; chỉ revalidate/reconcile/redeploy được xác nhận.
- **BR-21 — Connection revision**: Mỗi run chốt connection/source/target/schema/mapping revision
  và secret reference trước task đầu. Credential revision cũ được bảo vệ đến khi run kết thúc,
  không đưa secret value vào metadata công khai. Sửa credential không đổi đích vật lý;
  đổi vị trí làm ủy quyền FULL_REFRESH cũ mất hiệu lực và chặn run mới tới khi xác nhận lại.
  Connection update phải phản ánh vào execution Airflow trước run mới; chỉ cập nhật DB ứng dụng
  không đủ để báo đã đồng bộ. Run dùng revision lỗi phải fail an toàn, không fallback connection khác.
- **BR-22 — Template version và tham chiếu**: Version `1.0` áp dụng cho cả hai template;
  mỗi sheet giữ đúng header contract. Table identity là connection/schema/table; DAG ID unique
  theo Airflow. Không dùng thứ tự dòng để suy table/DAG cha. Duplicate definitions và reference
  orphan chặn toàn workbook, không chọn dòng cuối. Optional field trống dùng default đã công bố;
  required field trống báo lỗi ở cell thật. Column_Mappings có thể chỉ có header để implicit-map;
  dòng mapping có dữ liệu nhưng Enabled trống vẫn là lỗi, không coi như không có mapping.

### Các thực thể chính

- **Connection**: Code, DB type, vị trí/schema/username, secret reference, description,
  timestamps/status test/revision; Table/ETL Definition tham chiếu, run giữ revision và secret reference đã chốt.
- **Source File**: Reference nội dung, parser metadata, size/time/retention/dependency;
  nhiều Definition dùng được cùng file.
- **Definition Upload**: Workbook gốc, Table/ETL type, template version/revision,
  validation issues và confirmation history.
- **Table/Column Definition**: Target connection/schema/table, cột có thứ tự/type/key/default;
  một upload chứa nhiều table.
- **Table Creation Operation**: Confirmation, SQL preview và result/error riêng từng table.
- **ETL Definition/Column Mapping**: DAG ID, một source/target, schedule/strategy/key/batch/retry,
  mapping, revision; liên kết managed DAG.
- **Deployment**: Revision xác nhận, generate/deploy/registration status, error/time/kết quả Airflow.
- **DAG**: ID Airflow, ownership/schedule/paused/active; external không bắt buộc Definition ứng dụng.
- **DAG Run/Task Attempt/Execution Metrics**: Execution ID/status/time/attempt/log references,
  số dòng/error có nguồn thật.
- **Staging Artifact**: Owner run/attempt, dataset ID, snapshot/schema/revision, checksum/row count, vị trí, bytes, completion/expiry/recovery protection.
- **Settings/Data Replacement Authorization**: Defaults hợp lệ; phạm vi cho phép thay target
  theo revision/lịch, không là hệ thống phân quyền nhiều người.

## Tiêu chí thành công

### Kết quả đo lường được

- **SC-001**: Khởi động môi trường mới bằng đúng một lệnh; sau sẵn sàng, chạy workflow mẫu
  không có cấu hình nội bộ bổ sung; restart không mất dữ liệu đã thay đổi.
- **SC-002**: Với dữ liệu/workbook mẫu chuẩn bị sẵn, operator tạo table và deploy workflow
  đầu tiên trong tối đa 10 phút thao tác, không viết Python hay SQL.
- **SC-003**: 100% tám hướng ETL kiểm chứng bằng bản ghi thật; target đúng số dòng/giá trị/khóa/NULL.
- **SC-004**: 20 ca workbook lỗi có 100% lỗi chỉ đúng vị trí/phạm vi và nguyên nhân;
  không side effect trước validation/xác nhận.
- **SC-005**: Ba lần cùng dữ liệu/key ổn định không tăng số key trong chế độ insert/update;
  chế độ chỉ insert thể hiện đúng cảnh báo và số dòng tăng kỳ vọng.
- **SC-006**: Mọi ca lỗi thay toàn bộ dữ liệu trong ma trận đều giữ/phục hồi dữ liệu cũ;
  không báo success cho dữ liệu rỗng/partial ngoài xác nhận.
- **SC-007**: Hoàn tất dataset lớn hơn hai lần giới hạn RAM xử lý và ít nhất 20 batch,
  không vượt quota, có bằng chứng lưu tạm trên đĩa và cleanup/recovery.
- **SC-008**: KPI/nhóm lịch/lọc ngày khớp 100% tập execution chuẩn đủ trạng thái;
  dữ liệu thiếu luôn có nhãn, không suy đoán.
- **SC-009**: 100% workflow báo deploy thành công được nền tảng điều phối nhận diện đúng revision;
  link mở đúng workflow, mỗi hướng ETL có ít nhất một execution thật thành công.
- **SC-010**: 95% thao tác xem/preview mẫu trong 3 giây; test connection/deployment luôn có
  kết quả hoặc timeout trong hạn mức công bố của môi trường nghiệm thu.
- **SC-011**: Không tìm thấy credentials trên các bề mặt cấm khi kiểm tra dữ liệu lưu/source/
  response/log/metadata task; các ca input nguy hiểm bị chặn.
- **SC-012**: Mọi ca A–T và bổ sung U–AM có kết quả thực, tái hiện được, truy vết yêu cầu;
  không test bắt buộc nào bị bỏ qua khi tuyên bố MVP hoàn thành.

- **SC-013**: Trong các ca nguồn được cập nhật đồng thời, mọi DB extraction thành công
  khớp một snapshot; 100% extraction fail của FULL_REFRESH giữ target cũ nguyên trạng.
- **SC-014**: Mọi ca commit chưa rõ, API timeout, worker kill và target overlap đều đối soát
  hoặc báo bị chặn đúng thời hạn; không có duplicate replay tự động hoặc mất artifact recovery.
- **SC-015**: Tập fixture Unicode/NULL/decimal/temporal round-trip đúng 100% giá trị được hỗ trợ;
  mọi giá trị không tương thích bị từ chối rõ, không cắt/đổi kiểu âm thầm.

### Ma trận nghiệm thu bắt buộc

Đây là yêu cầu kiểm thử tương lai; chưa có application source code và chưa chạy kiểm thử
sản phẩm tại bước Specify. Chỉ ghi đạt khi có execution/bằng chứng thật.

| Mã | Kịch bản | Kết quả cần đối chiếu | Truy vết |
| --- | --- | --- | --- |
| A | Table Excel → PostgreSQL | Cột/type/key ghép đúng preview và DB | US-04, FR-022–FR-028 |
| B | Table Excel → MySQL | Đúng dialect/cấu trúc, bảo vệ table cũ | US-04, FR-023–FR-028 |
| C | PostgreSQL → PostgreSQL | Table khác cùng server, dữ liệu/staging đúng | US-06, FR-001, FR-055–FR-062 |
| D | MySQL → MySQL | Table khác cùng server, dữ liệu/staging đúng | US-06, FR-001, FR-055–FR-062 |
| E | PostgreSQL → MySQL | Cross-server, conversion đúng | US-06, FR-047, FR-055 |
| F | MySQL → PostgreSQL | Cross-server, giá trị/NULL đúng | US-06, FR-047, FR-055 |
| G | CSV → PostgreSQL | Parser xác nhận, streamed load đúng | US-07, FR-010–FR-017, FR-056 |
| H | TXT → MySQL | Delimiter cấu hình, target đúng | US-07, FR-015, FR-056 |
| I | Cột khác tên | customer_id → cust_id, customer_name → name | US-06, FR-042–FR-047 |
| J | UPSERT lặp | Ba lần không duplicate, update đúng | US-08, FR-052, BR-07 |
| K | APPEND | Giữ cũ/thêm đúng/cảnh báo, retry không replay không chắc chắn | US-08, FR-050–FR-051 |
| L | FULL_REFRESH success | Dataset mới đúng và có ủy quyền | US-08, FR-053–FR-054 |
| M | FULL_REFRESH failure | Giữ/phục hồi cũ, kết quả recovery rõ | US-08, FR-053–FR-054 |
| N | Cron schedule | Execution thật đúng lịch/timezone và history | US-05, FR-034, US-09 |
| O | Vượt nhiều batch/RAM, disk staging | File trên đĩa/path riêng/quota/cleanup | US-06, FR-055–FR-062, NFR-004 |
| P | Excel sai | Lỗi vị trí/phạm vi, không side effect | US-04–US-05, FR-019–FR-020 |
| Q | Connection sai | Kết nối thật fail/timeout, không secret | US-02, FR-007–FR-009 |
| R | Source/target tạm down | Partial progress/retry/rerun đúng | US-06–US-08, FR-060, BR-07 |
| S | Dashboard thật | KPI/lịch/trạng thái/phân trang/thời gian đúng | US-10, FR-071–FR-078, BR-11–BR-12 |
| T | Open in Airflow | Browser mở đúng DAG ID | US-09, FR-070 |
| U | CSV → MySQL và TXT → PostgreSQL | Bổ sung đủ tám hướng | US-07, FR-001 |
| V | Disk full/interrupt/cancel/concurrent | Commit/status thật, staging riêng/target không xen kẽ | FR-057–FR-062, BR-09 |
| W | Parse error/timeout/old revision/external conflict | Không Deployed giả hoặc ghi đè sai | FR-035–FR-041 |
| X | Retention/restart/settings/dependency | Không mất artifact đang dùng, scope settings đúng | US-01–US-03, US-11 |
| Y | Injection/macro/path traversal/secret leak | Input nguy hiểm chặn, không credential leak | NFR-003, EC-05–EC-06, EC-24 |
| Z | UI/Excel/Markdown và unavailable states | Đúng ngôn ngữ/responsive, không dữ liệu giả | US-10–US-11, NFR-001–NFR-002 |
| AA | Update source giữa các chunk, mất snapshot | Dataset nhất quán hoặc fail trước target; không ghép snapshot | FR-089–FR-090, BR-16, SC-013 |
| AB | UPSERT target thiếu key, key bị xóa sau deploy | Chặn validation/preflight, không ALTER/index/APPEND ngầm | FR-052, BR-15 |
| AC | FULL_REFRESH source extraction fail, MySQL DDL boundary | Target nguyên trước công bố, một commit replacement; không TRUNCATE rồi load batch | FR-053, BR-06, BR-15 |
| AD | Chunk/batch khác nhau và dòng vượt cap | Chunk không quyết định commit, RAM/byte cap có hiệu lực | FR-088, NFR-004 |
| AE | NULL/Unicode/decimal/date/time và conversion lỗi | Giá trị round-trip hoặc lỗi, không làm tròn/cắt âm thầm | BR-17, SC-015 |
| AF | Header trùng/rỗng, delimiter/quote sai, schema drift | Lỗi vị trí và revalidation, không sửa mapping ngầm | FR-091–FR-092 |
| AG | APPEND/UPSERT/FULL_REFRESH row reconciliation | Đối soát đúng mỗi strategy, không dùng affected rows hoặc live source count sai | FR-093, BR-18 |
| AH | Staging I/O fail/checksum sai, kill không cleanup | Không fallback RAM/re-extract sau commit; giữ recovery, cleanup sau đối soát | FR-089, FR-094–FR-095 |
| AI | Hai DAG/connection alias cùng physical target | Tuần tự hóa; owner chưa rõ không chiếm lại, timeout đúng | BR-09, SC-014 |
| AJ | API timeout sau request, pending quá hạn, stale revision | Reconcile cùng identity, không blind retry/success giả | FR-039, FR-096–FR-097 |
| AK | Manual/scheduled chồng lấn, UTC/IANA/DST, đổi connection | Cùng concurrency/policy, revision chốt, không đổi đích giữa run | BR-04, BR-20–BR-21 |
| AL | Version 1.0, duplicate/orphan, dòng trống, implicit mapping | Required/optional và vị trí thật chính xác, không last-row-wins | FR-019–FR-021, FR-044, FR-098, BR-22 |
| AM | First boot/restart giữa extraction/commit/refresh, mất volume/secret | Readiness thật, persistence/recovery an toàn, không reset dữ liệu | FR-099–FR-100, BR-19 |

### Phân bổ phạm vi nghiệm thu theo câu chuyện

| Câu chuyện | Nhóm yêu cầu chức năng chính | Bằng chứng chấp nhận |
| --- | --- | --- |
| US-01 | FR-081–FR-084 | Startup mới/restart/seed và chạy mẫu |
| US-02 | FR-003–FR-009 | CRUD/test thật, lỗi và dependency |
| US-03 | FR-010–FR-017 | Upload/parser/preview/full validation/retention |
| US-04 | FR-018–FR-028 | Template, Excel lỗi, DDL đúng hai DB, kết quả từng table |
| US-05 | FR-018–FR-021, FR-029–FR-041 | Workbook nhiều DAG, deploy/revision/parse/activation |
| US-06 | FR-001, FR-042–FR-048, FR-055–FR-062 | Bốn DB routes, mapping/filter/metrics/staging thật |
| US-07 | FR-001, FR-010–FR-017, FR-042–FR-047, FR-056 | Bốn file routes, parser/NULL/dòng lỗi |
| US-08 | FR-049–FR-054 | Ba strategies, partial failure/retry/rerun/recovery |
| US-09 | FR-063–FR-070 | Managed/external, history/log/task/control/link |
| US-10 | FR-071–FR-078 | Tập runs chuẩn và dữ liệu thiếu/stale |
| US-11 | FR-002, FR-079–FR-080 | Settings đúng/sai, persistence, navigation/states |
| Xuyên suốt | FR-085–FR-100, BR-15–BR-22, NFR-001–NFR-010 | Tests thật/tài liệu/khả dụng/an toàn/quota và phản hồi |

## Giả định, phụ thuộc và phạm vi ngoài MVP

### Giả định và mặc định

- **AS-01**: Một operator local tin cậy, không yêu cầu login hay multi-user authorization.
  Môi trường mặc định chỉ công bố ứng dụng trên loopback; chưa nghiệm thu triển khai Internet.
  Kết nối dịch vụ/DB/Airflow vẫn cần credential phù hợp, không suy ra được bỏ xác thực service.

- **AS-02**: Podman hoặc Docker và Compose provider đã cài/engine đã hoạt động theo README;
  operator có quyền mạng/DB và cổng phù hợp. Ứng dụng không tự cài runtime/provider hoặc cấp
  quyền trên DB bên ngoài môi trường mẫu. Khởi động engine/machine là điều kiện đầu vào,
  không thay tự động initialization/migrations/seed bên trong ứng dụng.
- **AS-03**: Một source/target mỗi DAG, không join; source=target cùng physical table bị chặn.
  Mỗi DB extraction dùng một consistent snapshot của một table trong một transaction nguồn;
  không hứa snapshot xuyên nhiều DB/DAG. Thay đổi dữ liệu sau mốc snapshot không thuộc dataset run.
  Không lấy từng chunk ở snapshot mới; source không bảo đảm snapshot thì fail rõ, không tự hạ mức nhất quán.
  Retry extraction trước ghi target có thể tạo dataset mới và phải ghi nhận; sau ghi target không được đổi dataset.

- **AS-04**: Template schema ban đầu `1.0`, không tương thích mẫu cũ; hợp đồng trường và
  validation ở FR-019–FR-023/FR-031/FR-042/FR-098 là bắt buộc. Layout cell cụ thể, encoding
  vật lý staging và danh mục conversion chi tiết thuộc Plan, phải đáp ứng BR-16/BR-17.

- **AS-05**: Các mặc định runtime và timeout là baseline được dùng nếu không cấu hình khác,
  không phải kết quả benchmark. Plan xác định quota upload/RAM/disk/free-space reserve,
  max row bytes, chunk bytes và môi trường nghiệm thu trước implementation; không có quota vô hạn.
  Giới hạn format vật lý staging, cơ chế khóa/commit recovery và API theo phiên bản là quyết định
  Plan phải chứng minh đáp ứng hợp đồng toàn vẹn, không phải câu hỏi nghiệp vụ còn treo.

- **AS-06**: Definition chỉ .xlsx, dataset chỉ CSV/TXT; mặc định UTF-8, CSV delimiter comma,
  quote double-quote, header true; TXT xác nhận delimiter. NULL marker mặc định `\N`
  (một backslash và chữ N), khác chuỗi rỗng; preview và chỉnh parser trước dùng.
- **AS-07**: External DAG chỉ xem/monitor/open Airflow; trigger/pause/unpause trong ứng dụng
  chỉ cho managed DAG. Đây là giới hạn ownership MVP, không là phân quyền nhiều người.
- **AS-08**: Airflow thiếu schedule history/next run/timestamp thì công bố không khả dụng,
  không suy diễn giá trị quá khứ từ cấu hình hiện tại.
- **AS-09**: Không screenshot/wireframe/Excel mẫu; thiết kế mới theo workflow. Stage ưu tiên
  container/DB → connections/table → ETL/staging → DAG tích hợp thật → hoàn thiện Dashboard/
  Monitoring/UI. Validation/logging/status cơ bản phải đi cùng core.

### Phụ thuộc

- Phiên bản Airflow/public API tương thích được chọn tại Plan, browser truy cập được Airflow UI.
- PostgreSQL/MySQL thật có quyền phù hợp; logical databases/sample connections/datasets đã seed;
  không dùng bảng nội bộ Airflow cho nghiệp vụ ứng dụng.
- Persistent disk storage, quota RAM/disk, quyền truy cập staging/upload cho execution.
- Secret configuration và environment inputs được tài liệu hóa; startup tự xử lý phần nội bộ.
- Constitution 1.1.0; mọi thay đổi phạm vi/hành vi phải cập nhật specification trước triển khai.

- Hành vi transaction/snapshot được đối chiếu tài liệu chính thức; đây là cơ sở làm rõ,
  không khóa phiên bản triển khai: [PostgreSQL — Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html),
  [MySQL — Consistent Reads](https://dev.mysql.com/doc/refman/8.4/en/innodb-consistent-read.html),
  [MySQL — Implicit Commit](https://dev.mysql.com/doc/refman/8.4/en/implicit-commit.html).

### Ngoài phạm vi MVP

- Oracle, SQL Server, MongoDB, Snowflake và DB engine khác ngoài PostgreSQL/MySQL.
- CDC, real-time streaming, Spark, distributed ETL, arbitrary Python transformation.
- Multi-user authentication/authorization, outbound data export workflows.
- L1 hoặc phân hệ nghiệp vụ không liên quan ETL.
- Excel làm dataset source; bắt buộc Mapping Definition workbook riêng.
- SQL/Python tùy ý, join nhiều nguồn, bộ transformation tổng quát, filter file nâng cao.
- Tự ALTER/DROP table hiện hữu, migration schema dữ liệu người dùng, ghi đè external DAG,
  scheduler thay thế Airflow.

Các giả định được ghi rõ để chủ dự án rà soát. Không có câu hỏi chặn lập Plan;
việc hoàn thành tài liệu không có nghĩa MVP đã triển khai hoặc kiểm thử thành công.

## Mốc phát triển/demo local có điều kiện

Chỉ sau khi chủ dự án duyệt hồ sơ T014 local theo Constitution, cho phép mốc demo
local/một operator/dữ liệu tổng hợp/loopback theo hạn và baseline đã duyệt.
Không thu hẹp FR/US/NFR/SC, tám hướng ETL hoặc BR-08. Không dùng demo một bảng làm
nghiệm thu MVP. Chức năng/secrets/data integrity/recovery phải kiểm theo phase.
Không dữ liệu quan trọng/public/LAN/tunnel/endpoint không tin cậy. Trạng thái full gate
và NOT_RUN vẫn công bố theo bằng chứng, không dùng quyền local như security PASS.
