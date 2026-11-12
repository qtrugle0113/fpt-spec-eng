# Quyết định cần thiết cho findings Kerberos mới

**Cập nhật:** chủ dự án đã duyệt đúng phạm vi local qua câu trả lời trực tiếp.
Hồ sơ tại [quyết định](../decisions/portable-local-finding-approvals.json).
JSON đề xuất và hash bên dưới giữ nguyên bản đã được duyệt để truy vết.

Trạng thái lúc lập đề xuất: **CHỜ CHỦ DỰ ÁN**; đã được duyệt như cập nhật trên.
Hồ sơ cụ thể tại
[JSON306contexts](portable-local-krb5-20261111.json), SHA256
`ac4b8d8ad19b26bc81167dce06f8db99b811dbca78c93bfb97ac0439d71123f7`.

Scan mới trên máy công ty phát hiện14advisory ngoài các contexts đã duyệt,
trên9package Kerberos phiên bản1.20.1-2+deb12u5,306occurrences ở6target:
backend/backend-wheels/backend-tests/Airflow/airflow-wheels/PostgreSQL.
Trường FixedVersion của scanner chưa có giá trị cho các contexts này; không suy
thành vendor xác nhận chưa có bản vá hoặc not-affected. Không gỡ thư viện mù
quáng để làm sạch scan vì có thể phá dependency PostgreSQL/Airflow.

Phương án xin quyết định: chấp nhận tạm đúng các advisory/package/version/severity/
target trong JSON, cho local operator/dữ liệu tổng hợp/loopback, đến
2026-11-23T00:00:00+09:00, review2026-11-16. Không public/dữ liệu thật; giữ
secrets/auth/data integrity/BR-08 và mọi test chức năng. T014_FULL vẫn BLOCKED.
IDs trong JSON chỉ truy vết lượt phát hiện; portable policy áp theo context đã
duyệt, không đòi máy khác có cùng ID. Finding/version/severity/target mới vẫn chặn.

Hai findings libxslt của frontend không nằm trong đề nghị ngoại lệ: đã chọn vá
có mục tiêu1.1.43-r3→1.1.43-r4 và đang kiểm scan artifact mới.
