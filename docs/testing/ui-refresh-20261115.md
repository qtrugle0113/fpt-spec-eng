# Kiểm chứng UI — 2026-11-15

## Kết quả và phạm vi

Đã triển khai source của feature [002-ui-refresh](../../specs/002-ui-refresh/spec.md): sáu màn hình dùng theme trắng/xám nhạt/teal, panel và toolbar gọn, button download/Airflow, bảng có nhãn trạng thái. Giữ nguyên menu, route, API và các điều kiện review/confirmation/authority. Không thêm dependency giao diện.

Nghiệm thu trong báo cáo này chỉ dành cho source/UI và hồi quy liên quan. Không rollout image, không thay demo frontend23000, không đổi tài khoản Airflow, không sửa volumes hoặc dữ liệu ETL. Không coi thay đổi này là nghiệm thu lại baseline T014/T152 hoặc chấp thuận security cho image mới.

## Môi trường

- Windows/PowerShell, Node22.23.4 được tải từ nodejs.org vào `.tools/node-ui`; SHA256 đối chiếu đúng SHASUMS256 chính thức. Host ban đầu Node24.22.1; kết quả cuối dùng đúng22.23.4.
- Dependency frontend và e2e cài theo package-lock bằng `npm ci --ignore-scripts`; không sửa lock hoặc thêm thư viện.
- Chromium158.0.8127.18 / Playwright1.65.0.
- Preview loopback riêng: `http://127.0.0.1:4179`, phục vụ `frontend/dist`, proxy `/api` đến backend thật28000. Test tự quản lý preview tương tự trên4178.
- Podman machine ban đầu dừng. Đã start lại machine và đúng năm container hiện hữu của project `aat-portable-demo-a7f852ae`: PostgreSQL, MySQL, Airflow API, DAG processor, backend. Không build/recreate container, không chạy init lại, không đổi secrets/volume và không start scheduler/worker.
- API liveness/dashboard và Airflow monitor đều trả200. Readiness tổng thể còn503 do scheduler đang dừng; Settings hiển thị trạng thái kết nối thực tế. Không tuyên bố full stack healthy hoặc kiểm chứng ETL execution ở phiên này.

## Lệnh và kết quả

Các lệnh frontend dưới đây dùng Node22.23.4 trong PATH:

| Kiểm tra | Lệnh | Kết quả |
| --- | --- | --- |
| Typing | `npm.cmd --prefix frontend run typecheck` | Đạt |
| Build | `npm.cmd --prefix frontend run build` | Đạt,107 modules |
| UI | `npm.cmd --prefix frontend run test:ui` | 25/25 đạt, không lỗi JS hoặc tràn ngang |
| Shell | `AAT_SHELL_BASE_URL=http://127.0.0.1:4179`, `npm.cmd --prefix frontend run test:shell` | 18 cặp route/viewport đạt, search/menu mobile đạt |
| E2E hiện hữu | Trong `tests/e2e`, đặt `PLAYWRIGHT_BASE_URL=http://127.0.0.1:4179`; `node node_modules/@playwright/test/cli.js test accessibility.spec.ts dashboard.spec.ts --config playwright.config.ts` | 4/4 đạt trên desktop/mobile |
| Whitespace | `git diff --check` | Đạt |

Không có lint script/config riêng trong repo; không báo lint đã chạy. `npm ci` ban đầu cảnh báo host Node24 khác engine; đã khắc phục bằng runtime22.23.4 cho typecheck/build/test cuối.

Script shell cũ lỗi strict selector do trang có nhiều loading status hoặc không có status sau khi tải xong. Đã sửa để kiểm nhãn backend ổn định, không phụ thuộc số lượng thông báo tạm thời, và bổ sung viewport1366×768.

## Bằng chứng dữ liệu thật

25 kiểm tra UI gồm sáu route ở1366×768/390×844, menu/search, keyboard, hai download, popup Airflow, mở form Connections rồi Cancel, xem workflow/run/task attempts, các ca biên cô lập và kiểm palette/link.

Hai template thật tải qua button, file có ZIP/XLSX signature và kích thước:

- Table Definition.xlsx:11600bytes.
- ETL Definition.xlsx:13067bytes.

Popup Airflow đi đến đúng origin thật, cho phép redirect đăng nhập. Các đích Airflow khác giữ nguyên biểu thức href/target/rel; link deployment được rà code, không thực hiện deployment mới chỉ để hiện link.

Ở1366×768, đáy hàng dữ liệu đầu tiên đo từ đầu viewport:

| Trang | Đáy hàng đầu tiên |
| --- | --- |
| Dashboard | 737px |
| Connections | 420px |
| Table Management | 691px |
| DAG Builder | 402px |
| DAG Monitoring | 377px |
| Settings | Control đầu tiên181px; form cấu hình hiển thị trong viewport |

Tất cả đều nhỏ hơn768px. Ở390×844 không có cuộn ngang toàn trang; bảng rộng cuộn trong vùng riêng, button không bẻ giữa từ. Desktop còn cuộn dọc khi dữ liệu nhiều; mobile vẫn cuộn để đọc đủ nội dung, không giấu cảnh báo hoặc thu nhỏ chữ dữ liệu.

## Kiểm thử cô lập và tương phản

Các ca sau dùng route interception, được tách rõ khỏi tích hợp backend:

- Empty,503 và loading của Connections.
- DAG ID rất dài, cuộn ngang/focus bằng keyboard trong vùng bảng.
- Settings đang Saving bị disabled và lỗi412 yêu cầu review lại; không gửi PATCH tới backend thật.
- Dashboard stale/thiếu dữ liệu, Success Rate là Not available, không bịa số liệu.

Các cặp màu chữ chính đo được tương phản4.87–11.38:1; focus trên trắng>=3:1. Đây là kiểm tra palette và keyboard, không phải tuyên bố audit WCAG toàn diện.

## Rà soát ảnh

Đã mở ảnh của cả sáu trang desktop/mobile. Đã sửa qua ảnh: khoảng trống ở lịch sử Tables, thứ tự deployment so với history, chữ trạng thái bị xuống dòng, nhãn action bị bẻ giữa từ. Ảnh toàn trang có thể dài trên mobile vì vẫn giữ đủ thông tin.

Ảnh và kết quả máy đọc được tại [thư mục bằng chứng](ui-refresh-20261115/). `ui-results.json` ghi tách ca thật/cô lập, viewport, số đo và download; `baseline-results.json` ghi ba lỗi có trước khi refactor (metrics cao, hai link download không có style button). Các file XLSX tải tạm nằm `.tools/ui-refresh/current`, không cần nhân bản vào báo cáo.

## Truy vết và tuân thủ

| Yêu cầu | Task | Bằng chứng |
| --- | --- | --- |
| FR-001 | T003,T004 | CSS token, ảnh sáu trang, palette |
| FR-002 | T003,T005,T006 | Route/menu/search và E2E; không đổi callback nghiệp vụ |
| FR-003 | T002,T006 | ActionLink, hai XLSX thật, popup và inventory link |
| FR-004 | T003–T005 | Số đo viewport, ảnh và grid |
| FR-005 | T002,T003,T005 | Mobile và ID dài không tràn toàn trang |
| FR-006 | T002–T006,T008 | Keyboard, label trạng thái, palette, lỗi/busy/stale |
| FR-007 | T003,T005,T006 | Diff không đổi backend/API/ETL/lock |
| FR-008 | T007 | Rà bootstrap và quyết định giữ tài khoản |
| FR-009 | T001,T008,T009 | Artifact Spec Kit, báo cáo và giới hạn |

I–III đạt: tài liệu tiếng Việt, UI tiếng Anh, giữ branding trung tính, quy trình Spec Kit có truy vết. IV–VI/VIII đạt trong phạm vi UI: dữ liệu thật, giữ metadata/review/authority/secrets. VII không áp dụng vì không đổi ETL/staging. IX đạt trong phạm vi build/preview source, không phải fresh-stack acceptance. X đạt kiểm tra trong phạm vi thay đổi; XI tài liệu đồng bộ; XII là đợt UI sau baseline nghiệp vụ. Không sửa constitution hoặc kế thừa image approval.

## Giới hạn

- Không chạy lại các test tạo bảng, deploy/trigger DAG, FULL_REFRESH, retry/rerun hoặc stress vì không sửa các phần đó và không ghi dữ liệu demo cho kiểm thử UI.
- Preview không có nginx production; không dùng nó để kết luận kiểm thử routing bảo mật nginx.
- Airflow admin/admin không áp dụng: bootstrap giữ password/tài khoản cũ; đổi sẽ vi phạm điều kiện không ghi đè tài khoản. Xem [quyết định](../../specs/002-ui-refresh/research.md).
- Scheduler/worker vẫn dừng; kiểm chứng này không bao gồm chạy ETL mới.

## Quy trình Spec Kit

Đã đọc và áp dụng trực tiếp hướng dẫn local cho specify → clarify → plan → checklist → tasks → analyze → implement → converge; không tuyên bố gọi slash command không có trong môi trường. Các script setup/prerequisite/template đã chạy. Không có `.specify/extensions.yml`, không có hook cần dispatch. Feature pointer local `.specify/feature.json` được tạo theo quy trình và được ignore theo quy ước repo.

Clarify:0 câu hỏi, tự ghi giả định theo ủy quyền. Checklist yêu cầu14/14 và UX10/10 được review chất lượng trước implementation. Analyze đọc spec/plan/tasks:9/9 FR có task,0 requirement thiếu coverage,0 issue nghiêm trọng. Việc điều chỉnh bố cục qua ảnh được đồng bộ trong plan/research.

Converge cuối:đã đối chiếu9 FR,5 SC,8 kịch bản chấp nhận,7 nhóm quyết định thiết kế và12 nguyên tắc constitution theo phạm vi;0 thiếu/partial/contradicts/unrequested cần triển khai thêm. Không append task hoặc header rỗng; tasks.md giữ nguyên sau lần kiểm converge.9/9 task đã hoàn tất. US3 hoàn tất bằng kết luận giữ tài khoản theo nhánh có điều kiện, không phải đã đổi admin/admin.

`source-manifest.json` ghi SHA256 của17 file frontend liên quan và bản build đã kiểm; `e2e-results.json` ghi4 expected,0 unexpected,0 skipped. Bằng chứng này áp dụng source/preview tại workspace, không phải approval image/container mới.
