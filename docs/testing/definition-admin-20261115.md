# Kiểm chứng Definition và admin Airflow — 2026-11-15

## Kết luận

Hai mục tiêu bắt buộc của [feature003](../../specs/003-definition-names-admin/spec.md) đã được triển khai và kiểm chứng:

- UI, thông báo backend và Instructions của hai template/hai file mẫu dùng ETL Definition hoặc Table Definition; template chỉ mẫu tải về, input ghi file (.xlsx).
- Demo hiện hữu tại <http://localhost:28080> đăng nhập **admin/admin**, token có role admin; fresh stack cô lập cũng đăng nhập được. Đã kiểm lại sau restart, giữ service account, auth, volume và dữ liệu.

Đây là kiểm chứng source local trên dependency images hiện có, không phải packaged-image acceptance hoặc production deployment. Không commit/push, không xóa/reinitialize volume hoặc dữ liệu demo. Phần UI feature002 chưa commit được giữ nguyên, chỉ điều chỉnh chữ và chiều rộng ngày trong bảng theo nhãn mới.

## Môi trường và nguồn thực thi

- Windows/PowerShell, Node22.23.4, TypeScript5.9.3/Vite7.3.7, Playwright1.65.0/Chromium158; Python3.12 trong dependency image backend.
- Airflow3.3.2, SimpleAuthManager; source đúng phiên bản đang cài được đọc cùng [tài liệu chính thức](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/auth-manager/simple/index.html). User/role từ cấu hình, password từ file secret; không dùng SQL sửa metadata DB.
- Demo:project `aat-portable-demo-a7f852ae`, backend28000, Airflow28080; UI mới preview4179. Frontend demo23000 chưa rollout. Scheduler/worker demo giữ trạng thái dừng như trước, readiness tổng thể còn503; không coi đó là lỗi đăng nhập hoặc khẳng định full stack healthy.
- Fresh:project `aat-definition_admin-e2e-6089c136`, network/volumes riêng, source snapshot RO `/current`; backend/frontend/Airflow/database/scheduler/worker đều đã healthy và readiness200 khi chạy kiểm thử. Không dùng volume demo. Browser chạy trong container cùng network để kiểm dịch vụ thật; các port fresh trên Windows không được dùng làm bằng chứng vì đường forward host đã timeout.
- Không build image mới hoặc đổi dependency lock. Fresh/source demo ghi rõ `CURRENT_SOURCE_ON_EXISTING_DEPENDENCY_IMAGES`, không kế thừa approval của image cũ cho image mới.

## Thuật ngữ và tương thích

Đổi label/button/history/notification, accessibility label và hướng dẫn theo ngữ cảnh. Backend chung dùng Definition file khi chưa phân biệt loại; service chỉ ETL/Table dùng tên cụ thể.

Giữ nguyên route, menu, payload/schema, entity, field workbook_sha256, scope workbook, mã WORKBOOK_* và message_key. `CURRENT_MESSAGE_KEYS` ánh xạ thông báo mới về khóa lịch sử cũ; dữ liệu Issue đã lưu không cần migration. Kiểm thử xác nhận cả câu cũ/câu mới trỏ cùng key.

`scripts/normalize-definition-templates.py` chỉ đổi câu chữ Instructions trong:

- templates/ETL Definition.xlsx
- templates/Table Definition.xlsx
- samples/definitions/ETL Definition.sample.xlsx
- samples/definitions/Table Definition.sample.xlsx

Giữ Version1.0, sheet/header và metadata mẫu; cập nhật SHA256/bytes trong design-validation.json để kiểm artifact đúng bytes mới. Không rewrite các báo cáo/spec lịch sử. Hai template mới được download thật từ backend demo sau khi nạp source/asset mới; Table11599bytes, ETL13072bytes.

## Migration demo và dữ liệu

Lệnh đã chạy:

```powershell
python -X utf8 scripts/configure-local-airflow-admin.py
python -X utf8 scripts/apply-local-definition-source.py
python -X utf8 tests/tools/verify_local_admin.py --project aat-portable-demo-a7f852ae --evidence docs/testing/definition-admin-20261115/demo-restart.json
```

Migration xác minh project/container/loopback/SimpleAuthManager trước khi đổi. Password file cũ được backup bên trong secret volume với quyền hạn chế, Compose cũ nằm `.tools/local-admin-migrations/20261115T021208Z-034bbfc1/`; receipt công khai chỉ chứa metadata và ID, không chứa mật khẩu/token.

Đặt riêng admin/admin, giữ aat_service/operator và user khác. Lưu role override vào Compose record để recreate vẫn hoạt động; chỉ recreate Airflow API bằng image cũ, không chạy init lại hoặc start scheduler demo. Service account đã lấy token201 và GET DAG200 sau migration.

Source overlay sau đó chỉ recreate backend: volume code riêng RO, `PYTHONPATH`/`AAT_ASSETS_ROOT` trỏ source mới, template thật và thông báo khớp UI. Compose backend-worker được cập nhật cho lần start sau nhưng worker không tự chạy. Có backup Compose riêng; không đổi các volume dữ liệu.

Các bằng chứng:

- [demo-migration.json](definition-admin-20261115/demo-migration.json): login API, account khác giữ nguyên, image/volume/tập ID trước–sau không đổi.
- [demo-source-overlay.json](definition-admin-20261115/demo-source-overlay.json): source mới, image cũ, tập ID dữ liệu giữ nguyên.
- [demo-restart.json](definition-admin-20261115/demo-restart.json): admin/service/auth đúng, password file và volume không đổi sau restart.
- [demo-target-rows.json](definition-admin-20261115/demo-target-rows.json): chỉ đọc hai bảng đích thật, mỗi bảng4rows, khớp loaded_rows của run thành công đã có. Không thực hiện DML.

Metadata được đối chiếu gồm4 connection,2 Definition upload,2 job,4 file và2 DAG cùng run ID đã tồn tại. Secret/service account/keyring và các volume DB/DAG/log/upload/staging không bị xóa hoặc tạo lại.

## Fresh, idempotence và restore

Fresh runner thực hiện root Compose với project/network/volume mới, source overlay và entrypoint/helper từ source hiện tại. Bootstrap local flag=1 tạo admin/admin; service/operator vẫn random và tách biệt. Source overlay cập nhật cuối giữ image và ghi source fingerprint riêng.

```powershell
python -X utf8 tests/tools/verify_local_admin.py --project aat-definition_admin-e2e-6089c136 --fresh --evidence docs/testing/definition-admin-20261115/fresh-restart.json
```

[fresh-restart.json](definition-admin-20261115/fresh-restart.json) xác nhận login/quyền admin, service auth, wrong-password/unauthenticated bị từ chối, password store không đổi qua init/restart. Reset rồi restore bằng helper trên chính persistent secret fixture khôi phục bytes gốc và giữ account khác; bootstrap thật được start lại, không reset account. Custom admin password và opt-out không tạo weak default được kiểm bằng unit tests. Không chạy rollback toàn bộ Compose trên demo vì sẽ tháo tài khoản đang cần dùng; đường restore/config backup được ghi trong hướng dẫn vận hành.

Fixture được giữ volume sau kiểm chứng, không dùng `down --volumes`; các service fixture được dừng sau khi lưu bằng chứng. Demo vẫn hoạt động ở các service cần cho UI/auth như trước.

## Kiểm thử và kết quả cuối

| Nhóm | Lệnh/nguồn | Kết quả |
| --- | --- | --- |
| Typing/build | `npm.cmd --prefix frontend run typecheck`, `npm.cmd --prefix frontend run build` với Node22.23.4 | Đạt,107modules |
| Unit | `tests/tools/run_definition_units.py --image <backend-id> --evidence .../unit-results.txt` | 29/29 đạt, không network hoặc volume demo |
| UI hồi quy | `npm.cmd --prefix frontend run test:ui` | 25/25 đạt, desktop1366×768 và mobile390×844 |
| Fresh E2E | definition_admin.spec.ts + language.spec.ts + bootstrap.spec.ts trong browser fixture | 10/10 đạt |
| Demo browser sau restart | definition_admin.spec.ts, lọc admin signs, URL28080 | 2/2 đạt, desktop/mobile |
| Runtime restart | verify_local_admin.py cho cả2 project | Đạt |
| Dữ liệu đích | SELECT count và đối chiếu run metrics, chỉ đọc | 2 bảng,4rows/bảng khớp |
| Whitespace | `git diff --check` | Đạt |

Unit29 bao gồm opt-in, custom password, idempotence, account khác, JSON hỏng/mất secret, role merge, backup/restore/path guard, ổn định message_key, canonical artifact hash và validation Table/ETL.

E2E kiểm upload/validate ETL Definition qua API thật, nhãn và layout, login form thật, token role admin và đọc API Variables có bảo vệ. Password sai trả401; thiếu xác thực không vào được API. API config không được dùng làm phép thử quyền vì Airflow mặc định tắt expose_config ngay cả với admin; không bật expose_config để làm test pass.

Ảnh desktop/mobile được mở để rà nhãn và bố cục. Đã nới cột ngày để nhãn dài không làm ngày bị bẻ giữa số; bảng rộng vẫn chỉ cuộn trong vùng riêng. Ảnh auth chỉ chụp sau đăng nhập, không lưu token/password vào evidence.

Kết quả máy đọc được: [UI](definition-admin-20261115/ui/results.json), [fresh E2E cuối](definition-admin-20261115/fresh-final/e2e-results.json), [demo E2E cuối](definition-admin-20261115/demo-browser/e2e-results.json), [unit](definition-admin-20261115/unit-results.txt). Ảnh nằm cùng các thư mục đó.

## Các lượt sửa bộ kiểm thử

Giữ kết quả fresh đầu trong `fresh/`:8pass/2fail do test đọc response body sau navigation; sửa test dùng token API riêng và form login thật. Một phép thử API config403 là do expose_config mặc định, đã đổi sang quyền Variables và JWT role, không nới cấu hình bảo mật.

Sau restart backend fixture, nginx giữ DNS upstream cũ gây504/download canceled; đã đợi readiness200 và restart frontend fixture trước lượt cuối10/10. Lượt unit dùng thư mục /tmp của backend cũ thất bại sau recreate vì writable layer đã mất; chuyển sang runner cô lập tái lập source,29/29 đạt. Các lỗi harness này không được báo là app pass ở thời điểm chưa sửa; kết quả cuối và lượt đầu tách riêng.

Không có lint script/config riêng trong repo. Không chạy lại toàn bộ ETL stress/FULL_REFRESH/recovery hoặc build/scan image mới vì không thay các cơ chế đó. Không tuyên bố production-ready hoặc nghiệm thu lại T014/T152.

## Truy vết và Spec Kit

| Yêu cầu | Task | Bằng chứng |
| --- | --- | --- |
| FR-001 | T002,T004 | UI/regex/ảnh/E2E |
| FR-002 | T003,T004 | Message keys, parser unit, Instructions/hash/download thật |
| FR-003 | T002,T003,T010 | Docs hiện hành/selector/typecheck/build |
| FR-004 | T001,T005,T007,T008 | Migration receipt, backup, browser/quyền thật |
| FR-005 | T005,T006,T009 | Fresh bootstrap, opt-out unit, entrypoint local |
| FR-006 | T005,T006,T008,T009 | Custom password unit, init/restart thật |
| FR-007 | T001,T005–T009 | Account khác, ID/volume/rows, auth guard |
| FR-008 | T004,T008–T010 | Toàn bộ bằng chứng thực tế, giới hạn công bố |

Đã áp dụng hướng dẫn local của specify → clarify → plan → checklist → tasks → analyze → implement → converge. Đã chạy script template/setup/prerequisite, không giả lập việc gọi slash command. Không có extensions.yml/hook cần dispatch. Clarify0 câu hỏi theo ủy quyền; checklist đặc tả7/7 và UX/auth6/6 được review trước implementation. Analyze8/8 FR có task, không có critical issue hoặc yêu cầu bỏ sót.

Constitution:I–III đạt ngôn ngữ/nhận diện/Spec Kit; IV–VI/VIII đạt trong phạm vi dữ liệu thật, metadata/auth đúng cơ chế và không phá dữ liệu; VII không áp dụng vì không đổi ETL/staging; IX là source overlay trên container thật, không nhận là fresh packaged-image acceptance; X có unit/API/browser/runtime; XI tài liệu đồng bộ; XII hai mục tiêu kiểm độc lập. Không sửa constitution hoặc tự cấp approval security mới.

Converge cuối đối chiếu8 FR,4 SC,7 kịch bản chấp nhận,6 nhóm thiết kế và12 nguyên tắc trong phạm vi thay đổi:0 gap cần triển khai thêm.10/10 task đã hoàn tất; không append task rỗng hoặc sửa tasks.md trong lượt converge. `source-manifest.json` ghi SHA256 của52 file source liên quan và bản dist cuối để đối chiếu evidence.
