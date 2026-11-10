# Review image phase8 — chờ chủ dự án

Bản source local đã chạy được; quyền local hiện có không tự áp dụng cho image IDs mới.
T014_FULL vẫn BLOCKED. Đây là delta kỹ thuật, không phải approval hoặc security PASS.

| Image cuối | Image ID | HIGH | CRITICAL | Context mới so baseline runtime |
| --- | --- | --- | --- | --- |
| backend-wheels | `a18041d29f9ad61194b397382ccb23726e6215151c4d2e3937450ca56fd62b7e` | 59 | 2 | 0 |
| backend | `3151393626735176b171c13da7a0b269e6c27d5fcb8a76046a609507e06d09be` | 56 | 2 | 0 |
| airflow-wheels | `069bcdae973eacc4ec714efc3fa902eae09492196d4069d2e790d91a647ab7ff` | 59 | 2 | 0 |
| airflow | `b9920b0e7a7c58fabf87feb0db69379186943a726a33ec15303274a116335ad6` | 141 | 5 | 0 |
| frontend-build | `40b5c4665c138783aac64080b0dc96f35d3ea3ddafa61caf924a4f8a3f010f05` | 34 | 1 | 0 |
| frontend | `eec1733adc9de3ca198a7677bbb5d39e05e15c04aca056a0134147819abcf0d7` | 0 | 0 | 0 |

Chi tiết context mới/đã bỏ và cả sáu stage candidate trong [delta](owner-review-delta.json).
Các finding đầy đủ, counts và snapshot scanner trong [scan](candidate-security.json).
Payload wheel đã đối chiếu mã hiện tại trong [kiểm chứng package](packaged-source.json).

Quy tắc hiện hành tại `docs/proposals/t014-conditional-local-gate.md`: “owner phải ký delta trước mốc tiếp theo”.
Cần quyết định riêng cho đúng image IDs/context, giữ hạn/controls local; không tự mở gate tiếp theo hoặc miễn trừ findings.
