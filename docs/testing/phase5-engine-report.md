# Checkpoint engine ETL — 2026-11-10

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
