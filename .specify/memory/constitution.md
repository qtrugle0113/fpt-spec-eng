<!--
Báo cáo tác động đồng bộ — D1 được chủ dự án duyệt trong hội thoại ngày2026-11-09.
- Phiên bản đề xuất: 1.1.0 → 1.2.0 (MINOR): thêm quyền phát triển local có hạn,
  tách khỏi nghiệm thu đầy đủ; không thay yêu cầu an toàn/chức năng hoặc task completion.
- Đồng bộ Spec/Plan/Tasks/Research/README/Quickstart và báo cáo hiện hành.
- Quyết định, reviewer, baseline, controls, hạn và thu hồi theo đề xuất T014 local.
- Quyết định: docs/decisions/t014-local-gate-approval.md; local đã kích hoạt có hạn theo
  docs/decisions/t014-local-activation.json sau xác nhận D3/LEX-003; full T014 vẫn BLOCKED.
-->

# Hiến chương dự án Airflow Automation Tool

## Các nguyên tắc cốt lõi

Các từ PHẢI, KHÔNG ĐƯỢC và CHỈ ĐƯỢC biểu thị yêu cầu bắt buộc. Mọi quyết định về
đặc tả, kiến trúc, triển khai và nghiệm thu PHẢI chứng minh tuân thủ các nguyên tắc này.

### I. Ngôn ngữ nhất quán theo đối tượng sử dụng

- Mọi prompt do AI tạo, giải thích, phân tích và báo cáo của AI PHẢI sử dụng tiếng Việt.
- Toàn bộ tài liệu Markdown được tạo hoặc cập nhật PHẢI dùng tiếng Việt, bao gồm heading,
  câu chuyện người dùng, tiêu chí chấp nhận, mô tả chức năng và phần giải thích.
  Quy định áp dụng cho `constitution.md`, `spec.md`, `plan.md`, `research.md`,
  `data-model.md`, `tasks.md`, `quickstart.md`, `README.md`, checklist, tài liệu kiến trúc,
  vận hành và báo cáo kiểm thử.
- Nội dung trực tiếp hiển thị trên UI PHẢI dùng tiếng Anh: navigation, button, form label,
  placeholder, notification, validation message, dialog, dashboard, table header, tooltip
  và empty state. Lỗi từ hệ thống phụ thuộc PHẢI được ánh xạ thành thông báo UI phù hợp.
- Label, tên sheet, tên cột và hướng dẫn cho người dùng trong Excel Definition Template,
  kể cả file mẫu, PHẢI dùng tiếng Anh.
- Tên công nghệ, API, class, function, variable, database field, enum, command, file path
  và thuật ngữ kỹ thuật tiêu chuẩn được giữ nguyên tiếng Anh. KHÔNG ĐƯỢC dịch làm sai nghĩa.
  Chuỗi UI và nội dung Excel trích dẫn trong tài liệu được giữ nguyên để phản ánh sản phẩm.

**Kiểm chứng:** rà soát tài liệu, UI và Excel Template theo đúng nhóm ngôn ngữ trước nghiệm thu.

### II. Nhận diện và thiết kế dựa trên quy trình thực tế

- Tên ứng dụng PHẢI là **Airflow Automation Tool**. Đây là dự án phát triển mới từ đầu,
  không có screenshot, wireframe hoặc UI mẫu làm đầu vào.
- Giao diện PHẢI được thiết kế từ requirement và workflow thực tế; KHÔNG ĐƯỢC tự suy diễn
  yêu cầu sao chép giao diện của hệ thống khác.
- Thiết kế PHẢI theo phong cách modern data engineering platform: chuyên nghiệp, trực quan,
  responsive và nhất quán về navigation, biểu mẫu, trạng thái, bảng dữ liệu và phản hồi lỗi.
- KHÔNG ĐƯỢC sử dụng logo, watermark hoặc branding của công ty hay sản phẩm bên thứ ba.
  Có thể dùng tên ứng dụng dạng chữ và biểu tượng trung tính do dự án tự thiết kế.

**Kiểm chứng:** các luồng chính sử dụng được trên màn hình desktop và màn hình hẹp;
người dùng nhận biết được bước tiếp theo, trạng thái xử lý và cách khắc phục lỗi.

### III. Phát triển dựa trên đặc tả với Spec Kit

- PHẢI tuân thủ workflow Spec Kit: Constitution → đặc tả → làm rõ khi cần → kế hoạch
  → phân rã task → kiểm tra tính nhất quán → triển khai → kiểm thử và nghiệm thu.
- KHÔNG ĐƯỢC triển khai tính năng khi chưa có `spec.md` và `plan.md` phù hợp.
- Requirement, specification, plan, tasks, implementation và testing PHẢI truy vết được
  với nhau bằng mã yêu cầu, câu chuyện người dùng hoặc tham chiếu tương đương.
- KHÔNG ĐƯỢC bỏ qua yêu cầu đã xác định hoặc thay đổi nghiệp vụ quan trọng mà không cập nhật
  specification và các tài liệu liên quan trước khi triển khai thay đổi.
- Mỗi task PHẢI nêu mục tiêu, đầu ra, phụ thuộc và tiêu chí kiểm chứng rõ ràng.

**Kiểm chứng:** mọi chức năng được nghiệm thu đều có yêu cầu gốc, task và bằng chứng kiểm thử;
mọi chênh lệch tài liệu được giải quyết trước khi đánh dấu hoàn thành.

### IV. Sản phẩm hoạt động thực sự và kiến trúc dễ bảo trì

- Frontend PHẢI tích hợp Backend API thật; Backend PHẢI tích hợp Apache Airflow và database
  thật. KHÔNG ĐƯỢC dùng mock data để thay thế chức năng đã tuyên bố hoàn thành.
- Mock và stub CHỈ ĐƯỢC dùng trong phạm vi kiểm thử cô lập hoặc phát triển tạm thời được
  ghi nhận rõ; chúng không phải bằng chứng nghiệm thu tích hợp.
- Mọi đầu vào PHẢI được validation phía Backend; lỗi PHẢI có exception handling,
  logging và status feedback đủ để người dùng và người vận hành xác định kết quả.
- Mã nguồn PHẢI có typing phù hợp với ngôn ngữ, phân tách module theo trách nhiệm và
  giao diện rõ ràng. Kiến trúc mặc định PHẢI đơn giản; việc thêm microservices hoặc
  thành phần phức tạp PHẢI có nhu cầu cụ thể và quyết định kiến trúc được ghi lại.

**Kiểm chứng:** luồng UI → Backend → database/Airflow thực hiện được nghiệp vụ thật,
bao gồm phản hồi khi hệ thống phụ thuộc không sẵn sàng.

### V. Tự động hóa bằng metadata có kiểm soát

- Người dùng PHẢI tạo được table và DAG bằng cách upload Excel Definition, không cần
  tự viết Python DAG hoặc SQL DDL.
- Excel Definition PHẢI có schema rõ ràng, version, quy tắc tương thích, validation
  và template mẫu. Version không hỗ trợ PHẢI bị từ chối với thông báo có thể xử lý được.
- PHẢI validate cấu trúc sheet/cột, kiểu dữ liệu, trường bắt buộc, SQL identifiers,
  connection reference và tính hợp lệ ngữ nghĩa trước khi thay đổi database hoặc triển khai DAG.
  Lỗi Excel PHẢI chỉ rõ vị trí sheet, dòng hoặc cột liên quan khi có thể xác định.
- KHÔNG ĐƯỢC thực thi Python code tùy ý từ Excel. Metadata PHẢI được ánh xạ qua các
  thao tác và kiểu dữ liệu được cho phép; không được trở thành mã thực thi không kiểm soát.
- PHẢI tái sử dụng ETL logic và DAG template; KHÔNG ĐƯỢC xây một hệ thống độc lập cho mỗi DAG.

**Kiểm chứng:** Excel hợp lệ tạo được table/DAG; Excel sai hoặc chứa nội dung thực thi
bị từ chối mà không tạo tác động thay đổi database hoặc triển khai DAG.

### VI. An toàn và toàn vẹn dữ liệu theo chính sách load

- KHÔNG ĐƯỢC tự ý `DROP TABLE`, `DELETE` hoặc `TRUNCATE` dữ liệu người dùng.
  Thao tác có khả năng ghi đè hoặc phá hủy dữ liệu PHẢI có xác nhận rõ ràng về đối tượng,
  phạm vi và hậu quả trước khi thực thi. Với lịch chạy lặp lại, phạm vi ủy quyền PHẢI
  được lưu và kiểm tra; thay đổi vượt phạm vi PHẢI yêu cầu xác nhận lại.
- PHẢI phân biệt chính sách load và ghi rõ hành vi khi retry/rerun:

  | Chính sách | Quy định bắt buộc |
  | --- | --- |
  | `APPEND` | Thêm bản ghi; không mặc định chống duplicate. PHẢI công bố và kiểm thử nguy cơ trùng khi retry/rerun cùng biện pháp kiểm soát đã chọn. |
  | `UPSERT` | PHẢI xác định khóa khớp, quy tắc cập nhật, xử lý khóa thiếu/trùng và tính nhất quán khi retry/rerun. |
  | `FULL_REFRESH` | PHẢI xác nhận phạm vi thay thế và xác định cách bảo vệ, phục hồi dữ liệu khi thất bại; không được suy ra quyền xóa từ việc chọn policy đơn thuần. |

- KHÔNG ĐƯỢC lưu mật khẩu plaintext trong database. Credential cần truy xuất PHẢI được
  quản lý bằng secret store hoặc mã hóa với khóa được quản lý tách biệt; mật khẩu đăng nhập
  nếu có PHẢI được băm bằng cơ chế phù hợp.
- KHÔNG ĐƯỢC đưa credentials vào DAG source, API response, log hoặc XCom.
  DAG PHẢI tham chiếu connection/secret thay vì nhúng credential.
- Giá trị SQL PHẢI dùng parameterized queries. SQL identifiers PHẢI được validation
  và xử lý theo dialect được hỗ trợ; KHÔNG ĐƯỢC nối trực tiếp đầu vào tùy ý vào SQL.
  Dynamic SQL CHỈ ĐƯỢC sinh từ metadata đã kiểm tra và template được kiểm soát.

**Kiểm chứng:** có kiểm thử SQL injection, rò rỉ secret, thao tác ghi đè chưa xác nhận,
và partial failure/retry/rerun cho từng chính sách load được hỗ trợ.

### VII. Xử lý dữ liệu lớn với bộ nhớ hữu hạn và staging trên đĩa

- KHÔNG ĐƯỢC đọc toàn bộ source dataset vào RAM; PHẢI dùng streaming hoặc bounded chunk
  processing với giới hạn được cấu hình và ghi nhận trong kế hoạch.
- DB-to-DB ETL PHẢI sử dụng disk-backed staging files trên lưu trữ thực sự dựa trên đĩa;
  không được thay thế bằng danh sách trong RAM hoặc `tmpfs` chứa toàn bộ dataset.
- Staging PHẢI có đường dẫn riêng theo execution, phân biệt các attempt khi cần,
  tránh xung đột khi chạy đồng thời, có cleanup, failure recovery và giới hạn tài nguyên.
- PHẢI xác định giới hạn RAM, dung lượng staging, batch size, thời gian lưu file lỗi,
  hành vi khi hết đĩa và cách phục hồi khi worker/process khởi động lại.
- KHÔNG ĐƯỢC dùng Airflow XCom để chuyển dataset lớn. XCom CHỈ ĐƯỢC truyền metadata nhỏ,
  như tham chiếu staging, số lượng bản ghi hoặc trạng thái, và không được chứa credentials.
- Mỗi batch PHẢI có ranh giới commit, chính sách retry và kiểm soát duplicate phù hợp
  với load policy. Tiến độ đã commit PHẢI được xác định khi xảy ra partial failure.

**Kiểm chứng:** kiểm thử dataset vượt giới hạn RAM của worker, xác minh file staging thực
trên đĩa, xử lý song song, cleanup, hết đĩa và khả năng phục hồi sau thất bại.

### VIII. Apache Airflow là nền tảng điều phối duy nhất

- Airflow PHẢI chịu trách nhiệm orchestration, scheduling và execution ETL;
  ứng dụng KHÔNG ĐƯỢC xây scheduler thay thế Airflow.
- PHẢI ưu tiên public API tương thích với phiên bản Airflow được chọn; phiên bản và
  phương thức tích hợp PHẢI được ghi trong `plan.md` và tài liệu kiến trúc.
- KHÔNG ĐƯỢC truy cập trực tiếp các bảng nội bộ Airflow metadata DB để thực hiện nghiệp vụ.
  Việc khởi tạo/nâng cấp metadata DB PHẢI dùng cơ chế chính thức của Airflow.
- Sau khi tạo DAG, PHẢI kiểm tra Airflow parse và đăng ký đúng DAG thành công.
  Ghi file DAG thành công không phải deployment thành công.
- PHẢI phân biệt trạng thái đang triển khai, đã đăng ký, parse lỗi và hết thời gian chờ;
  trạng thái thực thi PHẢI dựa trên kết quả Airflow thực tế.

**Kiểm chứng:** kiểm thử DAG hợp lệ được đăng ký và chạy trong Airflow;
DAG parse lỗi hoặc không đăng ký trong thời hạn không được báo triển khai thành công.

### IX. Môi trường Linux containers khởi động bằng một lệnh

- Môi trường PHẢI chạy bằng Linux containers trên Docker Engine/Desktop hoặc Podman.
  README PHẢI công bố runtime, phiên bản engine/client và Compose provider đã nghiệm thu.
- Khi engine đã hoạt động và điều kiện đầu vào đã chuẩn bị theo README, toàn bộ stack
  PHẢI khởi động bằng đúng một lệnh của runtime đã chọn:

  `docker compose up --build -d` hoặc `podman compose up --build -d`.

  Đây là hai lựa chọn thay thế; KHÔNG ĐƯỢC yêu cầu chạy cả hai để khởi động một môi trường.
- Môi trường PHẢI gồm Frontend, Backend, Airflow, PostgreSQL, MySQL và các service phụ trợ
  cần thiết. PHẢI tự initialization, migrations, seed, cấu hình persistent volumes và
  healthchecks theo dependency; nhận cấu hình qua environment variables/secret files.
- Lần khởi động đầu tiên PHẢI tự hoàn tất phần nội bộ ứng dụng, KHÔNG ĐƯỢC yêu cầu chạy
  migration, tạo schema hoặc cấu hình service thủ công sau lệnh startup. Cài runtime,
  Compose provider và khởi động engine/machine là điều kiện đầu vào được công bố,
  tương tự khởi động Docker daemon, không phải bước setup nghiệp vụ ngầm.
- Init/migrations/seed PHẢI chạy lại an toàn, không xóa hoặc ghi đè dữ liệu người dùng;
  sample namespace PHẢI tách dữ liệu thực. Dữ liệu, uploads, DAGs, logs, staging và key
  cần lưu PHẢI bền qua restart; engine/provider không được làm thay đổi nghĩa vụ recovery.
- Container running KHÔNG thay service readiness. Healthchecks PHẢI phản ánh khả năng
  phục vụ; startup dependencies, init Exited(0), restart behavior và resource limits
  PHẢI được kiểm bằng runtime/provider thật được công bố, không suy từ Compose config.
- Quyền volume/UID/GID, secret mounts, network isolation và loopback exposure PHẢI được
  giữ đúng thiết kế. KHÔNG ĐƯỢC dùng privileged, tắt healthcheck/constraint, chmod777,
  bỏ memory/disk limits hoặc xóa volumes để né khác biệt runtime.
- Nghiệm thu PHẢI ghi runtime/provider/phiên bản và kết quả thực. PASS trên một tổ hợp
  KHÔNG chứng minh tổ hợp khác đã được kiểm. Chỉ cần nghiệm thu baseline được công bố
  cho lần bàn giao; KHÔNG ĐƯỢC quảng bá runtime khác đã tương thích khi chưa có evidence.

**Kiểm chứng:** fresh startup đúng một lệnh trên baseline đã công bố, init/readiness thật,
workflow mẫu khi đủ chức năng, restart và xác minh persistence/secret/recovery. Không còn
mandatory test chưa chạy trong phạm vi tuyên bố hoàn thành.

### X. Kiểm thử thực tế và báo cáo trung thực

- Chức năng CHỈ ĐƯỢC xem là hoàn thành sau khi được kiểm thử theo tiêu chí chấp nhận.
- PHẢI có unit tests, integration tests và end-to-end tests. Workflow ETL PHẢI được
  kiểm thử bằng database thật; tích hợp Airflow PHẢI được kiểm thử trên Airflow thật.
- Phạm vi kiểm thử PHẢI bao gồm happy path, validation error, connection failure,
  partial failure, retry và rerun, cùng hành vi của từng load policy được hỗ trợ.
- PHẢI có kiểm thử xác minh disk-backed staging và kiểm thử DAG đăng ký, thực thi trong
  Airflow; kiểm tra source code hoặc mock API không thay thế được các bằng chứng này.
- Báo cáo PHẢI nêu lệnh đã chạy, môi trường/phiên bản, kết quả thực tế và giới hạn còn lại.
  KHÔNG ĐƯỢC báo `PASS` khi test chưa chạy. Test bị bỏ qua, bị chặn hoặc thất bại
  PHẢI được ghi đúng trạng thái và không được tính là bằng chứng hoàn thành.

**Kiểm chứng:** kết quả kiểm thử có thể tái lập, đối chiếu được với yêu cầu và dữ liệu đích;
không còn tiêu chí bắt buộc chưa kiểm chứng trong phạm vi tuyên bố hoàn thành.

### XI. Tài liệu đầy đủ và đồng bộ với triển khai

- PHẢI có README, tài liệu kiến trúc, API documentation, đặc tả Excel Template và
  troubleshooting bằng tiếng Việt; sample Excel và hướng dẫn trong template bằng tiếng Anh.
- Tài liệu PHẢI giải thích các quyết định kiến trúc quan trọng, cách khởi động,
  cấu hình connection, upload Excel, load policy, staging, triển khai DAG và theo dõi kết quả.
- PHẢI ghi rõ giới hạn hỗ trợ, quy trình xử lý lỗi và phục hồi, quản lý secrets và
  bằng chứng kiểm thử liên quan. Không được mô tả chức năng chưa kiểm chứng như đã hoàn thành.
- Thay đổi API, schema Excel, cấu hình hoặc hành vi nghiệp vụ PHẢI cập nhật tài liệu
  liên quan trong cùng thay đổi triển khai.

**Kiểm chứng:** người khác làm theo tài liệu thực hiện được workflow mẫu và xử lý
các lỗi đã mô tả mà không cần bước cài đặt ngầm.

### XII. Phát triển theo giai đoạn có đầu ra kiểm thử độc lập

- PHẢI chia dự án thành các giai đoạn có phạm vi, phụ thuộc, đầu ra và tiêu chí nghiệm thu
  riêng; mỗi giai đoạn PHẢI kiểm thử được khi các phụ thuộc đã sẵn sàng.
- Thứ tự ưu tiên PHẢI là môi trường Linux containers và database → connections → tạo table
  từ Excel → ETL Engine và staging → sinh DAG và tích hợp Airflow thực tế
  → hoàn thiện Dashboard, Monitoring và UI/UX.
- Validation, bảo mật, logging và phản hồi trạng thái cơ bản PHẢI đi cùng chức năng lõi,
  không được trì hoãn đến giai đoạn hoàn thiện Monitoring.
- KHÔNG ĐƯỢC dành công sức đáng kể cho hiệu ứng UI trước khi chức năng lõi hoạt động.
  Thay đổi thứ tự ưu tiên PHẢI có lý do về phụ thuộc hoặc rủi ro, được cập nhật trong plan
  và không được làm mất các cổng kiểm chứng.

**Kiểm chứng:** mỗi giai đoạn có kịch bản chạy thực tế và báo cáo kết quả;
giai đoạn chưa nghiệm thu không được tuyên bố là đã hoàn thành.

## Ràng buộc kiến trúc và phạm vi sản phẩm

Ứng dụng PHẢI cho phép người dùng tạo bảng dữ liệu, tạo DAG, lập lịch và theo dõi quá trình
chuyển dữ liệu thông qua Excel Definition. Backend quản lý metadata, validation và tích hợp;
Airflow điều phối và thực thi; database lưu dữ liệu theo vai trò được xác định trong kế hoạch.

`plan.md` PHẢI xác định phiên bản công nghệ, database được hỗ trợ, hợp đồng API, schema Excel,
ranh giới module, cơ chế quản lý secrets, chiến lược DAG deployment và chính sách tài nguyên.
Framework Frontend/Backend và chi tiết hạ tầng chưa được chọn tại bước Constitution;
quyết định sau này PHẢI có lý do và tuân thủ toàn bộ nguyên tắc trên.

Việc database nằm trong cùng môi trường container không cho phép ứng dụng truy cập trực tiếp
các bảng nội bộ Airflow. Staging, dữ liệu ứng dụng và metadata Airflow PHẢI có ranh giới
trách nhiệm, quyền truy cập và vòng đời được tài liệu hóa.

## Quy trình phát triển và các cổng chất lượng

1. **Trước lập kế hoạch:** `spec.md` PHẢI có phạm vi, câu chuyện người dùng, yêu cầu chức năng,
   tình huống lỗi và tiêu chí chấp nhận có thể kiểm thử. Điểm chưa rõ ảnh hưởng an toàn dữ liệu
   hoặc nghiệp vụ PHẢI được giải quyết trước khi triển khai phần phụ thuộc.
2. **Trước triển khai:** `plan.md` PHẢI có đánh giá tuân thủ từng nguyên tắc liên quan,
   thiết kế tích hợp thật, chiến lược kiểm thử và quản lý failure/retry/rerun.
   `tasks.md` PHẢI truy vết yêu cầu, chỉ rõ phụ thuộc và tiêu chí kiểm chứng.
3. **Trong triển khai:** PHẢI cập nhật đồng bộ đặc tả, kế hoạch và tài liệu khi thay đổi;
   task chỉ được đánh dấu hoàn thành khi tiêu chí kiểm chứng của task đã đạt.
4. **Trước nghiệm thu:** PHẢI chạy các kiểm thử áp dụng, đối chiếu kết quả dữ liệu,
   xác minh đăng ký/thực thi DAG, staging, an toàn credentials và khởi động trên runtime/provider đã công bố theo phạm vi.
5. **Trước bàn giao:** PHẢI có báo cáo kiểm thử trung thực, tài liệu cập nhật và đánh giá
   tuân thủ Constitution. Mục bắt buộc còn thiếu PHẢI được ghi rõ; không được báo hoàn thành.

Mỗi đánh giá tuân thủ PHẢI ghi nguyên tắc, bằng chứng và kết luận: đạt, chưa đạt hoặc không
áp dụng kèm lý do. Không áp dụng chỉ hợp lệ khi chức năng nằm ngoài phạm vi thay đổi;
không được dùng để bỏ yêu cầu bắt buộc của sản phẩm khi nghiệm thu tổng thể.

## Quản trị và sửa đổi

- Constitution là chuẩn quản trị cao nhất trong dự án đối với specification, plan, tasks,
  implementation, testing và tài liệu. Mọi rà soát thay đổi PHẢI kiểm tra tính tuân thủ.
- Khi phát hiện xung đột, PHẢI dừng phần triển khai bị ảnh hưởng và giải quyết bằng cách
  điều chỉnh thiết kế/tài liệu hoặc sửa đổi Constitution; không được âm thầm bỏ qua nguyên tắc.
- Đề xuất sửa đổi PHẢI nêu quy định cũ/mới, lý do, tác động đến dữ liệu và tương thích,
  danh sách tài liệu/task cần đồng bộ, kế hoạch chuyển đổi và cách kiểm chứng.
- Chủ dự án hoặc người được chủ dự án ủy quyền PHẢI phê duyệt thay đổi quy tắc quản trị
  trước khi áp dụng. Ngoại lệ đối với yêu cầu bắt buộc PHẢI đi qua quy trình sửa đổi này;
  ghi chú trong plan không tự tạo ra ngoại lệ.
- Phiên bản PHẢI theo `MAJOR.MINOR.PATCH`: tăng `MAJOR` khi loại bỏ hoặc định nghĩa lại
  nguyên tắc không tương thích; tăng `MINOR` khi thêm nguyên tắc hoặc mở rộng đáng kể;
  tăng `PATCH` khi làm rõ câu chữ mà không thay đổi nghĩa vụ.
- Mỗi sửa đổi PHẢI cập nhật phiên bản, ngày sửa đổi theo `YYYY-MM-DD`, báo cáo tác động
  đồng bộ và các tài liệu bị ảnh hưởng. Ngày thông qua ban đầu được giữ nguyên.
- Bản 1.0.0 là lần ban hành đầu tiên theo yêu cầu của chủ dự án. Bước này chỉ thiết lập
  quy tắc quản trị; chưa phải bằng chứng triển khai hoặc nghiệm thu chức năng ứng dụng.

**Phiên bản**: 1.2.0 | **Ngày thông qua**: 2026-11-06 | **Ngày sửa đổi gần nhất**: 2026-11-09

## Quyền phát triển local có điều kiện, tách khỏi nghiệm thu đầy đủ

Sau phê duyệt quản trị của chủ dự án, có thể cấp quyền phát triển local có hạn cho
một operator/dữ liệu tổng hợp/loopback khi bootstrap có bằng chứng và mọi ngoại lệ được
ghi theo exact advisory/package/image IDs. Đây không phải nghiệm thu task/sản phẩm.
T014 đầy đủ vẫn BLOCKED và checkbox chưa hoàn thành khi security chưa đạt.
Hồ sơ PHẢI có owner/reviewer/approval timestamp, baseline, controls, hạn và thu hồi;
không tự duyệt/gia hạn. Finding bắt buộc trước local PHẢI được khép theo hồ sơ.
Không miễn trừ secrets/auth/data integrity/BR-08, tests chức năng hoặc safety gates.
Phase sau chỉ bắt đầu theo ngoại lệ dependency đã đồng bộ trong Tasks và quyết định
đang hiệu lực. Hết hạn/vượt scope/mismatch/exploit thì dừng phần phụ thuộc và review lại.
Quyền này không áp dụng cho public/dữ liệu quan trọng hoặc bàn giao đầy đủ.
Cơ sở: docs/proposals/t014-conditional-local-gate.md và quyết định chủ dự án ghi riêng.
