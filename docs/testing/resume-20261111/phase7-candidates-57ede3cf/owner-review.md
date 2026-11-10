# Review image phase7 — chờ chủ dự án

Bản source local đã chạy được; quyền local hiện có không tự áp dụng cho image IDs mới.
T014_FULL vẫn BLOCKED. Đây là delta kỹ thuật, không phải approval hoặc security PASS.

| Image cuối | Image ID | HIGH | CRITICAL | Context mới so baseline runtime |
| --- | --- | --- | --- | --- |
| backend-wheels | `fcd9b9180e139d8b51bdaeef15b431e4b4eed4ac80bd5a66b34801969845653c` | 59 | 2 | 0 |
| backend | `97af4b9a2185ee4bd338390cbc199a3772fd1e41354af69487d8cc682aa06049` | 56 | 2 | 0 |
| airflow-wheels | `069bcdae973eacc4ec714efc3fa902eae09492196d4069d2e790d91a647ab7ff` | 59 | 2 | 0 |
| airflow | `b9920b0e7a7c58fabf87feb0db69379186943a726a33ec15303274a116335ad6` | 141 | 5 | 0 |
| frontend-build | `9845c7c03c0c88772380ba19b3eb0a85b38b252126233384cc6864565f58855d` | 34 | 1 | 0 |
| frontend | `367002047b585ea85c1bbeab18ec7cdfa68b932fa0ff6dd4967e6733cf914e03` | 0 | 0 | 0 |

Chi tiết context mới/đã bỏ và cả sáu stage candidate trong [delta](owner-review-delta.json).
Các finding đầy đủ, counts và snapshot scanner trong [scan](candidate-security.json).
Payload wheel đã đối chiếu mã hiện tại trong [kiểm chứng package](packaged-source.json).

Quy tắc hiện hành tại `docs/proposals/t014-conditional-local-gate.md`: “owner phải ký delta trước mốc tiếp theo”.
Cần quyết định riêng cho đúng image IDs/context, giữ hạn/controls local; không tự mở gate tiếp theo hoặc miễn trừ findings.

Chỉ bốn IDs mới cần duyệt: backend-wheels, backend, frontend-build, frontend.
Hai IDs airflow-wheels/airflow giữ nguyên approval Phase6, không xin duyệt lại.
JS/CSS/HTML offline khớp candidate trong [parity](frontend-artifact-parity.json);
50x.html là file thêm của nginx base. Hồ sơ đề nghị ban đầu tại
[approval request](approval-request.json); quyết định chủ dự án hiện đã được ghi
tại `docs/decisions/phase7-local-image-approval.json`.
