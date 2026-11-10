# Checkpoint engine ETL — 2026-11-10

## Tiếp tục hướng tới luồng hoàn chỉnh — T078 trở đi

Yêu cầu hiện hành của owner cho phép tiếp tục xuyên checkpoint/phase theo dependency,
ưu tiên UI → API → Airflow → dữ liệu đích, không commit/push, không đổi dependency
baseline hoặc ngoại lệ security. Lượt này giữ các thay đổi từ checkpoint trước.
Prerequisites/checklists16/16 và48/48 PASS; không AGENTS.md hoặc extension hooks.

Đã kiểm bằng source-copy trên exact baseline runner399adacf…e2fc,
PG87507379…cf03 và MySQLc691f53c…c60f, Podman6.1.1. Fixture mới dùng anonymous
volumes trên đĩa khi kiểm scratch/ledger, không mount volume hiện hữu hoặc publish
port. Driver cleanup chỉ containers/network/anonymous volumes do chính nó tạo.

| Phạm vi | Kết quả | Bằng chứng trong resume-20261110 |
| --- | --- | --- |
| T078 target-typed scratch/NULL/duplicate xa nhiều batch/collation/quota |8PASS|t078-accounting-green.log|
| T079 native locks/alias/session kill, không reconnect ngầm |4PASS|t079-native-lock-green.log|
| T080 signature/consent/collision/DML+marker cùng commit và rollback |3PASS|t080-target-ledger-green.log|
| T081 preparation source COMPLETE → map/full validate → mapped COMPLETE, không load; staging regression |13PASS|t081-disk-preparation-green.log|
| T082 projection từ target markers đã commit, idempotent/app projection lỗi không replay |1PASS|t082-projection-green.log|
| APPEND/UPSERT: partial batch, retry, rerun trùng, khóa ghép/key-only3run, unique phụ |9PASS|t086-t088-policy-acceptance-green.log|
| Admission/FULL_REFRESH: scope/revoke/response loss/allow_empty/rollback/FK/trigger |11PASS|t084-t089-safety-green.log|
| FULL_REFRESH COMMIT lost/corrupt staging và batch COMMIT lost trên hai DB |11PASS|t089-t090-commit-safety-green.log|
| T091 cleanup: native owner kết thúc, retention, không xóa protected |3PASS|t091-native-cleanup-green.log|

Các suite có ca trùng nhau, không cộng thành tổng số test độc lập. JSON cùng prefix
ghi exact IDs, storage, actual memory và exit status. Các lượt RED/FAIL được giữ;
`t081-preparation-red.log` thực tế4PASS vì source mới đã có khi driver copy vào
runner; tên phase không được dùng thay kết quả thực trong log/results.

Scratch MySQL dùng InnoDB temporary tables, đúng target collation. Charge bảo thủ
2MiB +4×(encoded row bytes+256) mỗi row, giới hạn10GiB/5triệu rows; test-only
root probe đo session temp tablespace212992bytes cho3001rows, dưới charge5321788bytes.
Runtime không cần PROCESS/root để đo. PG kiểm thêm pg_total_relation_size thực.
Stress lớn có bằng chứng riêng dưới đây; số đo nhỏ không thay bằng chứng stress.

Source bootstrap MySQL bổ sung CREATE TEMPORARY TABLES cho scratch và TRIGGER để
kiểm tra trigger trước FULL_REFRESH, chỉ etl_test.*. Không áp dụng grant lên DB/volume
hiện hữu trong lượt này. FULL_REFRESH từ chối khi không chứng minh được quyền xem
trigger; không suy rows rỗng của information_schema thành bằng chứng an toàn.

### Checkpoint dispatch, file, recovery và stress

| Phạm vi | Kết quả | Log trong resume-20261110 |
| --- | --- | --- |
| Bốn route DB, retry cùng run sau khi source thay đổi |4 PASS|t092-cross-database-green.log|
| CSV/TXT → hai DB, full format/checksum, key validation, lỗi nonkey giữ batch đã commit |9 PASS|t093-file-policy-acceptance-green.log|
| File FULL_REFRESH bốn route và bootstrap quyền bằng tài khoản MySQL thực |2 PASS, có subcases|t093-bootstrap-and-replacement-green.log|
| Hủy replacement sau INSERT: rollback, ONCE CLOSED; file replacement |2 PASS|t092-terminal-cancellation-green.log|
| Hồi quy admission, DB dispatch, file sau config guard |18 PASS|t090-t093-dispatch-regression-green.log|
| Startup deadline, protected staging GC và worker heartbeat thật |7 PASS|t091-bounded-maintenance-green.log|
| SIGKILL không finally; mất staging sau partial rồi trả lại chính files cũ |2 PASS, hai DB|t095-crash-and-volume-green.log|
| Stress disk và RSS, nguồn lớn hơn 1 GiB |1 PASS|t095-final-source-stress-green.log|

Stress dùng 270000 rows, payload nguồn 1107000000 bytes, 270 batch commits thật.
Target kiểm đủ count, ID sum 36450135000 và payload không sai khác. Staging payload
2220257790 bytes, allocated 2220482560 bytes, 266 parts. Peak RSS 106405888 bytes
trong budget 512 MiB; thời gian 117.149 giây. Không dùng test nhỏ thay stress.
Lượt stress trước cũng PASS; chạy lại để có source SHA256 snapshot và kiểm config
guard mới. Không cộng số test giữa các suite có ca trùng nhau.

Các prefix mới có `*-fixture-sources.json` lưu SHA256 source thực sự được copy trước
khi runner chạy; JSON results dẫn tới snapshot đó. Mất phản hồi COMMIT được tiêm
sau COMMIT thật trên DB; mất volume được mô phỏng bằng đổi tên thư mục staging của
fixture, không tháo/xóa volume hiện hữu. SIGKILL là process death thật.

Startup recovery đã có deadline hữu hạn và pool tối đa hai target inspections;
target chậm không giữ worker heartbeat. File raw manifest có validated_rows=0 cần
khôi phục mapping typed trước khi kiểm batch payload; test restart với resolver
encrypted-revision thật đang được kiểm thêm. Lượt `t091-file-restart` FAIL ở test
scaffolding do tên tham số trùng field `name`, chưa tới engine; giữ nguyên evidence
và sửa fixture trước khi chạy lại. Lượt fixture-fix tiếp theo phát hiện RunIntent
đang bắt buộc authorization ngay cả APPEND/UPSERT. Migration mới
`0003_nonreplacement_intents` cho phép NULL ở intent; admission vẫn NOT NULL,
repository vẫn kiểm quyền replacement. Không chạy migration trên DB hiện hữu.
`t091-nonreplacement-restart-green.log`:18 PASS gồm2 test restart (mỗi test hai DB)
và16 test authorization hồi quy. Khôi phục đúng typed payload từ raw-file staging,
resume prefix2→3, final marker→metrics3/3 mà không ghi lặp. Pool/deadline test riêng
vẫn PASS ở `t091-file-restart-green.log` dù hai test fixture cùng lượt FAIL.

Retry coordinator chỉ tự retry commit uncertainty đã đối soát; source failure dừng
an toàn, không tự lấy snapshot khác hoặc giải phóng protected capacity. Generation
extraction retry do runtime caller quản lý trước target ghi; chưa nghiệm thu runtime
SDK/Airflow ở checkpoint engine.

Gate wheel: runtime baseline không có setuptools, nên lượt
`t095-current-wheel-routes` dừng trước test; không cài tool vào image runtime.
Build hai pure-Python wheels bằng venv cô lập trên host với đúng build tools baseline
setuptools80.9.0/wheel0.45.1, không đổi lock/dependency sản phẩm. Runner extract
offline hai wheel vào thư mục riêng, re-exec bỏ source import paths, assert origin.
`t095-built-wheel-routes-green.log`:13 PASS gồm đủ tám route và các file failure
cases. Hash engine126f4aaf774e7d5156c82f72e0345f4b928ba64d7936359b2835c6e71d5331f2;
metadataedae334f32d3208136430f6d1806ae06eeaaf8ce1cc810a1197c0089e4579f41.
JSON wheel snapshot đi cùng kết quả. T090–T095 khép trong phạm vi engine trực tiếp;
T069 Files UI đã có nghiệm thu riêng. Chuyển Phase6 theo gate, không suy thành
Airflow ETL/UI E2E hoặc packaged image acceptance.

Đã build/kiểm wheel mới; chưa build image mới hoặc chạy Airflow ETL/UI vertical
workflow. T014_FULL vẫn BLOCKED. Các checkpoint phía dưới là lịch sử, không phải
trạng thái mới nhất của phần đã triển khai thêm.

## Cập nhật hiện hành — T070/T076/T077

Lượt này áp dụng `.github/skills/speckit-implement/SKILL.md`: prerequisites PASS,
checklists requirements16/16 và spec-quality48/48, không AGENTS.md trong repo,
không extension hooks. Reviewer checklists không bị sửa. Các đoạn phía dưới mục
này là checkpoint lịch sử; ghi chú T074 còn RED và Start Date chưa hồi quy đã
được thay bằng kết quả hiện hành ở đây.

- Hồi quy T071–T075: **41/41 PASS**, gồm Start Date/IANA/DST và instrumented
  cursor không warning, PostgreSQL/MySQL thật. Bằng chứng:
  `resume-20261110/t071-t075-regression-green.log`.
- Baseline T076: quota3PASS, supervisor2FAIL đúng do thiếu module; giữ log RED.
  Đã nối optional quota manager vào StagingWriter: reservation trước tạo artifact,
  tính cả part/manifest, không ghi vượt reservation, lỗi thì giữ capacity protected,
  không tự release hoặc xóa artifact. Writer bị lỗi append không thể publish tiếp.
  API không quota còn dành cho durability primitives; preparation T081 bắt buộc
  cung cấp quota manager và run UUID từ binding, không coi đường primitive là runtime.
- T076 + staging: **18/18 PASS**. Có race10GiB trên hai DB sessions, global20GiB
  tính ACTIVE/PROTECTED, idempotency/release evidence, free reserve1GiB, giới hạn
  reservation, manifest accounting và ENOSPC tiêm tại fsync trên file staging thật.
  Không tuyên bố đã làm đầy ổ đĩa vật lý; stress/storage gate vẫn thuộc T095.
- Supervisor Linux đọc RSS qua procfs, dừng process group ở480MiB để chừa32MiB
  headroom trong budget512MiB, wait/reap tiến trình. Đo thực tế peak503689216bytes,
  exit-9/MEMORY_BUDGET_EXCEEDED. Test harness1GiB chứa cả unittest parent và child;
  child vẫn budget512MiB, inspect runner OOMKilled=false. Đây là sampled budget,
  không hard per-process allocation limit; tích hợp LocalExecutor/stress còn T147.
- T077 bổ sung implicit exact-name hoặc explicit enabled mapping, DIRECT/CONSTANT/
  NULL_HANDLING/TYPE_CONVERSION, chuyển kiểu lossless qua whitelist, không đoán
  numeric string ở DIRECT, không round/truncate/gán timezone. Thiếu required target
  không default/generated bị từ chối; lỗi có vị trí row/column không echo dữ liệu.
  Filter DB tiếp tục dùng AND whitelist/parameter binding đã kiểm ở readers.
- Tổng hồi quy T070–T077 **58/58 PASS**; bổ sung mapping từ snapshot/introspection
  PostgreSQL/MySQL thật sang typed disk staging **2/2 PASS**, target vẫn0row.
  Sau bổ sung required-target guard, contract/type **16/16 PASS**. Các suite có
  phần trùng nhau, không cộng số PASS thành số test độc lập.

Logs, exact image IDs, exit status và actual memory limit nằm trong
`resume-20261110/*-fixture-results.json`. Lỗi mapping source integer overflow ở
lượt đầu được giữ tại `t077-mapping-green.log`/results(exit1), đã sửa và kiểm lại.
Tên green chỉ phase yêu cầu của driver, không thay trạng thái FAIL trong log/results.

Runtime lượt này Podman client/server6.1.1, Linux containers; không chạy Compose.
Các IDs gần nhất b5e…/c938…/76ef… không có trong image store hiện tại. Dùng đúng
baseline đã duyệt còn hiện hữu: runner399adacf…e2fc, PG87507379…cf03,
MySQLc691f53c…c60f; không rebuild/pull hoặc chuyển approval sang IDs khác.
DB dùng tmpfs cô lập như fixture cũ; dataset staging ở filesystem overlay trên
đĩa của runner, không dùng tmpfs cho dataset. Không published port hay mount volume
hiện hữu. Chỉ cleanup containers/network do mỗi driver tạo.

T070/T076/T077 được khép trong phạm vi riêng; T071–T075 giữ hoàn thành. Việc tiếp
theo là T078 full-dataset validation/scratch theo target collation, rồi các task
lock/ledger/writers theo dependency. Chưa có target load, retry/recovery hoặc
stress engine acceptance. T014_FULL vẫn BLOCKED; không commit/push/deploy,
không sửa dữ liệu hoặc volume hiện hữu, không mở rộng ngoại lệ security.

## Phạm vi và bằng chứng

File Sources T061–T069 đã khép riêng tại [checkpoint Files](phase5-file-sources-report.md).
Image Files đã được owner xác nhận đúng ID, E2E14PASS, Tables regression10PASS,
Connections regression6PASS; từng fixture cleanup0. Không kế thừa kết quả runtime
đó cho engine mới đang phát triển bằng source tests.

- T070 đã viết tests trước implementation và chạy **RED19tests**, không lỗi
  collect, tại `resume-20261109/t070-engine-red.log`. Các tests mapping/staging
  vẫn chờ module tương ứng; không đánh dấu engine hoàn thành khi chúng còn RED.
- T071 có strict typed execution contracts, source union DB/file, strategy/key,
  mapping/filter whitelist, literal lossless, cron5fields/IANA/Start Date/DST,
  canonical config hash và Excel transformation enum mapping.
  `t071-schema-contract-green.log` **7/7 PASS** gồm schema round-trip OpenAPI.
- T072/T073 source snapshot readers có cùng session read-only REPEATABLE READ,
  PG server cursor/MySQL SSCursor và consistent snapshot InnoDB, SQL CASE guard
  trước transport, parameterized filter, giữ decimal/microsecond/Unicode.
  `snapshot-final-source-green.log` **20/20 PASS** gồm13reader +7contract trên PG/
  MySQL thật. Có ảnh hưởng concurrent update trên bảng không PK, session bị kill,
  MyISAM từ chối, read-only DML bị chặn, UTC timestamp và inspection raw wire
  chứng minh giá trị2MiB được trả NULL thay vì truyền nguyên cell.
- Sau lượt20PASS đã đóng cursor test instrumentation trước khi raise, tránh
  ResourceWarning của fixture. Cần lượt hồi quy tiếp theo xác nhận không warning.

Các readers luôn bỏ incomplete dataset khi source session mất; không reconnect
để ghép snapshot. Fetch cap còn tính khả năng Python Unicode mở rộng4bytes/char
và object headers, không chỉ serialized wire bytes. RSS512MiB/quota/stress sẽ được
nghiệm thu ở T076/T095; chưa có bằng chứng để khẳng định gate đó đã đạt.

## Việc tiếp tục

**Mốc mới nhất:** `t071-t074-acceptance-green.log` **32/32 PASS** (contract7,
reader15, preflight10), không warning. T071–T074 đã đóng. Preflight có kiểm
collation/nullability/key/type và identity pin trên hai DB thật; alias cùng table
bị từ chối, không tự ALTER hoặc tự map lại.

T075: `t075-durability-green.log` **9/9 PASS** trên filesystem thật. Có typed
round-trip decimal30digits, Unicode/multiline/NULL/date/naive+aware timestamp,
checksum/binding/schema mismatch, corrupt part cuối bị chặn trước row đầu,
process con `os._exit` trước COMPLETE không publish manifest, record1MiB và
decimal exponent cực lớn bị từ chối trước format tốn RAM. Manifest SHA-256 được
pin ngoài file để không thể đổi schema rồi tự khai lại hash; part/manifest read-only.
Writer không overwrite dataset đã có, không tự xóa incomplete/recovery artifacts.
`COMPLETE` chứng minh extraction bền; `validated_rows=0` mặc định **không** là
nghiệm thu target-typed validation T078 hoặc quyền load. T076 cần tích hợp quota
atomic và RSS supervision; chưa dùng dataset cap nội bộ thay cho global gate.

Sau lượt32PASS có chuẩn hóa Start Date không offset bằng IANA timezone sang ISO
có offset, từ chối giờ DST ambiguous nếu thiếu offset; bổ sung test. Cần lượt hồi
quy tiếp theo trước khi coi source mới này đã kiểm. MySQL cho identifier64bytes;
PostgreSQL giữ giới hạn63bytes tại adapter, không cắt identifier.

T074: tests preflight đang RED trước implementation, cần chứng minh fingerprint
used-column/type/nullability/key, alias physical source=target từ chối và drift
được chặn trước run/load. Sau đó T075 staging typed JSONL/fsync/checksum/COMPLETE,
T076 quota/RSS và T077 mapping lossless theo dependency. Không mở rộng phạm vi.

T014_FULL còn BLOCKED; không tuyên bố MVP/engine acceptance hoàn tất. Không commit,
push, public port hoặc thay dữ liệu/volume hiện hữu. Source fixtures dùng approved
Airflow runner cùng PG/MySQL IDs, tmpfs/network cô lập; chưa build runtime engine
mới, nên không cần kế thừa hoặc giả ID image cho phần này.
