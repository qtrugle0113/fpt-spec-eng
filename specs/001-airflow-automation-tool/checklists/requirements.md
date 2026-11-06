# Checklist chất lượng đặc tả: Airflow Automation Tool

**Mục đích**: Kiểm tra tính đầy đủ và chất lượng yêu cầu trước khi lập kế hoạch.

**Ngày tạo**: 2026-11-06

**Tính năng**: [Đặc tả MVP](../spec.md)

**Trách nhiệm rà soát**: AI thực hiện Specify; chủ dự án có thể rà soát các giả định trước Plan.

**Ý nghĩa dấu kiểm**: `[x]` chỉ xác nhận tiêu chí chất lượng tài liệu đã được rà soát;
không có nghĩa application đã triển khai hoặc kiểm thử sản phẩm đã chạy.
Checklist này được duy trì theo vòng đời Specify/Clarify.

## Chất lượng nội dung

- [x] CHK001 Không chọn framework, ngôn ngữ triển khai, endpoint, thư viện hoặc cấu trúc mã.
- [x] CHK002 Tập trung giá trị operator, nhu cầu nghiệp vụ và kết quả có thể quan sát.
- [x] CHK003 Tài liệu tiếng Việt, UI/Excel dùng tiếng Anh, giữ thuật ngữ kỹ thuật theo Constitution.
- [x] CHK004 Đủ phần bắt buộc template, giữ cấp và thứ tự heading; dịch heading theo yêu cầu người dùng.

## Tính đầy đủ của yêu cầu

- [x] CHK005 Không còn placeholder hoặc câu hỏi chặn chưa giải quyết.
- [x] CHK006 FR/NFR/BR có mã, kiểm thử được; hành vi lỗi, transaction, retry và rerun được xác định.
- [x] CHK007 Success criteria có thước đo thời gian, độ chính xác, khối lượng và an toàn.
- [x] CHK008 Success criteria mô tả kết quả, không áp đặt framework hoặc cơ chế thực hiện.
- [x] CHK009 Mỗi câu chuyện có ưu tiên, lý do, kiểm thử độc lập và kịch bản cho trước/khi/thì.
- [x] CHK010 Trường hợp biên gồm partial failure, thiếu dữ liệu, duplicate, retry, tài nguyên và recovery.
- [x] CHK011 Tám hướng ETL, single-operator và ngoài MVP được phân định rõ.
- [x] CHK012 Có giả định, phụ thuộc, default và giới hạn cần công bố tại Plan.

## Mức sẵn sàng của tính năng

- [x] CHK013 Mỗi nhóm FR có tiêu chí chấp nhận qua US, EC, BR, ma trận nghiệm thu và bảng phân bổ phạm vi.
- [x] CHK014 Luồng chính bao phủ connections, file, table, DAG, mapping/load, monitoring, Dashboard, Settings và startup.
- [x] CHK015 SC-001–SC-012 có thể kiểm chứng và phản ánh đầu ra MVP mong muốn.
- [x] CHK016 Không có mã ứng dụng hoặc quyết định chi tiết implementation trong tài liệu.

## Ghi chú rà soát

- Đã đối chiếu 17 nhóm yêu cầu đầu vào và Constitution 1.0.0.
- Có 11 US, 87 FR, 10 NFR, 14 BR, 24 EC, 12 SC, 9 AS và 26 ca A–Z.
- Kiểm tra mã: không trùng, không tham chiếu không tồn tại, không placeholder.
- A–T giữ đủ các ca người dùng yêu cầu; U bổ sung CSV → MySQL, TXT → PostgreSQL để đủ tám hướng;
  V–Z bổ sung tài nguyên, deployment, retention, an toàn, ngôn ngữ và khả dụng.
- Ràng buộc Airflow/public API, Docker, PostgreSQL/MySQL, SQL validation và disk staging là
  yêu cầu đầu vào/Constitution; không phải lựa chọn implementation phát sinh ở Specify.
- Transaction/retry/recovery mô tả kết quả bắt buộc, chưa chọn thuật toán hoặc thiết kế lưu trữ.
- AS-01–AS-09 cần chủ dự án xem trước Plan, đặc biệt defaults, external DAG chỉ đọc,
  source filtering giới hạn, date-range semantics và dataset ổn định khi retry.
- Không có blocker cho `/speckit-plan`; có thể dùng `/speckit-clarify` để điều chỉnh giả định.
- Không có extension hooks được cấu hình tại thời điểm hoàn tất.
- Chưa chạy unit/integration/end-to-end tests hoặc benchmark: chưa có application source code.
