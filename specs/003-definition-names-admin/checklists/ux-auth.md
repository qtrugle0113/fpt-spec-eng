# Checklist chất lượng yêu cầu

**Ngày**:2026-11-15 | **Mục đích**: Review tên và local auth trước triển khai.
**Quyền review**: AI được người dùng ủy quyền tự review; dấu x chỉ chất lượng yêu cầu.

- [x] CHK001 Có quy định tên Definition/template/file và phạm vi UI/backend/Excel không? [Đầy đủ, FR-001–003]
- [x] CHK002 Có ranh giới giữ API/schema/key rõ ràng không? [Nhất quán, FR-002]
- [x] CHK003 Có yêu cầu login/quyền thật ở cả demo/fresh không? [Đo lường, FR-004,005,008]
- [x] CHK004 Có phân biệt reset tường minh và bootstrap không reset custom password không? [Rõ ràng, FR-006]
- [x] CHK005 Có backup/restore, project validation và dữ liệu trước–sau không? [Bao phủ, FR-004,007]
- [x] CHK006 Có giới hạn loopback/local, giữ service account và cấm tắt auth không? [An toàn, FR-005,007]
