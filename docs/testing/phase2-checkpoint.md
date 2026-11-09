# Checkpoint Phase2 đang thực hiện — 2026-11-09

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
