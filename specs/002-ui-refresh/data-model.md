# Mô hình dữ liệu và trạng thái

Không thêm entity, migration, field, validation rule hoặc API. Giữ kiểu từ `frontend/src/lib/api.generated.ts`.

| Đối tượng | Trình bày | Ràng buộc giữ nguyên |
| --- | --- | --- |
| Dashboard/DAGRun | Metrics, chart, recent runs, thông tin phụ | Null là Not available; command không đồng nghĩa run thành công |
| Connection | Bộ lọc, bảng, form/detail | ETag, secret redaction, dependency, disabled |
| DefinitionUpload/TableCreationJob | Wizard và history | Review SQL/token, validation, phân trang |
| DAG/Deployment/Operation | Workbook, deployment, monitoring | Authority, confirmation, expiry, trạng thái thật |
| Settings | Trường nhiều cột và thông tin ứng dụng | ETag/conflict, range và thông báo |

Loading/empty/error/stale/pending giữ từ query/operation hiện tại. Link button chỉ nhận anchor props, không chuyển đổi dữ liệu nghiệp vụ.
