# Checkpoint Phase2 đang thực hiện — 2026-11-09

**Hiện hành Phase5, 2026-11-10:** Files đã khép T061–T069: source regression116PASS, browser12PASS và persistence2PASS sau recreate backend/worker, desktop/mobile, ảnh đã kiểm và cleanup0. Backend Files `b194…b352` được owner xác nhận đúng ID; Frontend0HIGH/CRITICAL. Tiếp T070/T071 engine. Đọc [checkpoint Phase5](phase5-file-sources-report.md); không hỏi lại ID đã duyệt. T014_FULL vẫn BLOCKED. Các khối dưới là lịch sử.

**Hiện hành:** foundation và Connections đến T046 đã hoàn thành theo từng task;
T014_FULL vẫn BLOCKED. Owner đã xác nhận Backend runtime mới; Connections E2E6/6PASS
desktop/mobile, cleanup0, không ports public. Task tiếp theo T047/T048 của Table
Management. Các khối chờ Backend mapping/E2E bên dưới là lịch sử.

**Hiện hành sau mất mạng:** foundation đã đóng, T035–T044 đã kiểm và cập nhật checkbox.
Connections23/23PASS, foundation regression47/47PASS, frontend build/typecheckPASS.
T045/T046 chưa đóng: chờ mapping Backend runtime mới để chạy E2E trên artifacts đã
build/scan. Không hỏi lại ba image đã được duyệt. Xem
[checkpoint Phase3](phase3-connections-report.md) và [review Backend](phase3-us2-image-review.md).
Các khối “T034 còn mở” bên dưới là lịch sử.

**Foundation hiện đã đạt:** owner xác nhận thêm ID Airflow theo hồ sơ. Live readiness
2/2PASS, aggregate49/49PASS, Compose profile51/51PASS và response contract1/1PASS.
Đã sửa hai lỗi fixture/profile (worker trong installed wheel và credential fixture
idempotent); các lượt FAIL giữ riêng cùng thư mục bằng chứng. Đóng T034 và mở Phase3
theo phạm vi T152 đã được chủ dự án cho phép. T014_FULL vẫn BLOCKED/security ngoại lệ
local còn hạn; đây không phải nghiệm thu MVP hoặc public deployment.

**Cập nhật sau xác nhận owner:** mapping backend-tests/PostgreSQL mới đã được duyệt
đúng hai ID theo hội thoại, không hỏi lại. Owner-role initialization 1PASS (hai
initializer cạnh tranh bằng non-superuser), T015 9PASS, T018 7PASS. Đã đóng thêm
T028/T029/T030/T031/T033 theo bằng chứng mới; chỉ T034 còn mở trong Phase2.
Airflow candidate build/scan xong, 110HIGH/CRITICAL giống baseline (0 thêm/0 bớt),
đang chờ xác nhận riêng cho ID mới tại [hồ sơ Airflow](phase2-resume-airflow-review.md).
Driver `tests/tools/run_airflow_foundation.py` đã chuẩn bị để chạy readiness,
aggregate và Compose profile trên network/DB tmpfs riêng, không publish ports.

**Lượt implement mới, ưu tiên hơn các snapshot dưới đây:** chủ dự án đã mở phạm vi
đến T152 trong hội thoại, giữ dependency và mọi gate an toàn. Hai image mới đã build
và scan; delta HIGH/CRITICAL bằng baseline (0 thêm/0 bớt), đang chờ owner xác nhận
mapping theo [hồ sơ review](phase2-resume-security-review.md). Không tự kế thừa ngoại lệ.
T022 23PASS, T023–T026 16PASS, T027 2PASS, T032 6PASS, T033 3PASS, T017 28PASS,
migration/seed/key-loss 5PASS; unit toàn image 37PASS. T034/Airflow trên máy mới chưa
nghiệm thu; không mở Phase3 trước foundation gate. Kết quả mới tại `resume-20261109/`.

**Cập nhật môi trường sau bật ảo hóa:** Podman machine WSL2 đã chạy rootful,
CLI 6.1.1/server 6.1.4/Compose 5.6.0. Container UID0, cgroupv2 và giới hạn RAM
128MiB đã kiểm thật; Compose runtime smoke và config dự án PASS. Điểm chặn thiếu
runtime bên dưới đã được giải quyết. Machine mới chưa có image/network fixture của
phiên trước; cần khôi phục trước integration, không suy nghiệm thu từ smoke engine.
Xem [bằng chứng cài đặt](podman-install-results.json).

**Tiếp nhận mới trên checkout HEAD `b389d2e`:** Git ban đầu sạch; log T034 GREEN
đã hoàn tất 2/2 PASS trong phiên trước. Lượt mới khôi phục đúng bytes LF của mẫu
từ Git và chạy 12/12 kiểm tra nguồn PASS, cú pháp 50 file PASS. Chưa thể chạy lại
integration vì Windows/Ubuntu WSL không có Podman/Docker trong PATH. Giữ nguyên
checkbox chưa hoàn thành; xem [báo cáo tiếp nhận](phase2-resume-report.md).
Các số liệu dưới đây là checkpoint của phiên trước, không phải kết quả chạy mới.

Phạm vi chủ dự án đã duyệt: liên tục T022–T034; không Phase3. Đọc
[scope](../decisions/phase2-local-scope.json), activation và Git diff trước khi tiếp nhận.
Không reset/revert, không apply lại patch. T014_FULL BLOCKED/security FAIL.
Quyền local hết2026-11-23 00:00 UTC+09, review16/11; không mở rộng image/findings approval.

## Tiến độ hiện tại, chưa phải nghiệm thu cuối

- T022:23PG tests PASS (7 mới và16 regression T020).
- T023–T026:13checks graph ORM PASS sau sửa active deployment unique theo DAG và
  ngăn thay dataset pointer COMPLETE. Binding/parser FK thật đã được thêm nhưng
  chưa kiểm đủ mọi binding/recovery branch; không suy thành target recovery PASS.
- T027:2checks settings PASS. Lượt file mang nhãn red thực tế GREEN vì source-copy xảy ra
  sau implementation; không được dùng làm bằng chứng RED. Tests được viết trước source.
- T028–T030:2checks init cạnh tranh/optimistic setting PASS; static Alembic snapshot
  0001_metadata có69DDL statements, không live-import ORM. Cần thêm parity/preservation
  checks và hoàn thiện wiring/package/owner secrets trước đóng task.
- T031/T017:28/28 PASS PostgreSQL thật, gồm hai lock-order branches và runtime privileges.
- T032:3ASGI checks PASS trước thêm operations router/CORS; cần affected rerun.
- T033:3checks operation/confirmation PASS trước đổi claim kinds filter; cần affected rerun.
- T016:7/7 PASS, gồm process worker restart. Log latest hiện còn tên
  local-t016-foundation-red.log; đó là GREEN thực tế, không báo nó là RED.
- T034:2checks RED đã ghi; lượt GREEN readiness mới khởi chạy, phải nhận kết quả/process
  hiện hữu trước khi chạy trùng. Runner nối network Airflow local hiện có chỉ để đọc health.

## Các việc tiếp theo còn được phép, không cần hỏi lại

1. Nhận kết quả readiness; chạy aggregate --foundation khi affected source ổn định.
2. Kiểm migration parity/seed preservation/key loss/grants/runtime role scope đầy đủ;
   hoàn thiện app-init owner secret mount, Docker packaging và test profile.
3. Chạy affected ORM/T018/T015, compose/profile tests, build/scan candidate nếu cần.
   Candidate IDs mới không tự được kế thừa ngoại lệ; chuẩn bị delta cho reviewer khi có.
4. Rà soát source an toàn: reservation/admission scope, lease ownership, immutable history,
   DTO/errors/Origin, seeds không overwrite, full readiness failure branches.
5. Cập nhật Tasks chỉ khi tiêu chí đủ bằng chứng; hiện checkbox T022–T034 chưa được đóng.
6. Hoàn tất báo cáo/results hashes và kiểm services/cleanup/hooks; prompt tiếp tục ở cuối.

## Lệnh

```powershell
python -X utf8 tests/tools/run_metadata_foundation.py --model-task t022 --phase green
python -X utf8 tests/tools/run_metadata_foundation.py --model-task t026 --phase green
python -X utf8 tests/tools/run_metadata_foundation.py --model-task t027 --phase green
python -X utf8 tests/tools/run_metadata_foundation.py --repositories --phase green
python -X utf8 tests/tools/run_metadata_foundation.py --authorization --phase green
python -X utf8 tests/tools/run_metadata_foundation.py --api-foundation --phase green
python -X utf8 tests/tools/run_metadata_foundation.py --operations --phase green
python -X utf8 tests/tools/run_metadata_foundation.py --readiness --phase green
python -X utf8 tests/tools/run_metadata_foundation.py --foundation --phase green
```

Driver sở hữu PG tmpfs/network/runner riêng, không dùng volumes đang chạy.
Không chạy migrations lên A/B/R3/local services hiện hữu. Ba candidate IDs vẫn theo scope,
chưa build image mới; deployed services chưa chứa Phase2 source. Không claim MVP hoàn thành.
