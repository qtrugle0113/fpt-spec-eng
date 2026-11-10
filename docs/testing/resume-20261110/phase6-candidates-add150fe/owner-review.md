# Review image Phase6 — chờ chủ dự án

Bản source local đã chạy được; quyền local hiện có không tự áp dụng cho image IDs mới.
T014_FULL vẫn BLOCKED. Đây là delta kỹ thuật, không phải approval hoặc security PASS.

| Image cuối | Image ID | HIGH | CRITICAL | Context mới so baseline runtime |
| --- | --- | --- | --- | --- |
| backend | `6cc5f892b2b67c2eda06e776ad5b760524dc9c3b271786d323aa058084d837e3` | 56 | 2 | 0 |
| airflow | `b9920b0e7a7c58fabf87feb0db69379186943a726a33ec15303274a116335ad6` | 141 | 5 | 0 |
| frontend | `ce4629efec1d124414117906d5396d133357fa4daf15a27c6a2e72570399c906` | 0 | 0 | 0 |

Chi tiết context mới/đã bỏ và cả sáu stage candidate trong [delta](owner-review-delta.json).
Các finding đầy đủ, counts và snapshot scanner trong [scan](candidate-security.json).
Payload wheel đã đối chiếu mã hiện tại trong [kiểm chứng package](packaged-source.json).

Quy tắc hiện hành tại `docs/proposals/t014-conditional-local-gate.md`: “owner phải ký delta trước mốc tiếp theo”.
Cần quyết định riêng cho đúng image IDs/context, giữ hạn/controls local; không tự mở Phase7 hoặc miễn trừ findings.
