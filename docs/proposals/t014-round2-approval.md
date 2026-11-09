# T014 lượt2 — phương án A/B đã được duyệt

**Chủ dự án đã duyệt A và B trong hội thoại ngày 2026-11-09 (Asia/Yakutsk).**
Triển khai theo phạm vi bên dưới, giữ upstream constraints và không tự miễn trừ finding.
Các số liệu trial/phần “Xin duyệt” bên dưới là provenance trước quyết định, không phải
kết quả build/test của implementation mới. Trạng thái triển khai xem báo cáo T014 hiện hành.

A/B đã triển khai và kiểm thực tế; [kết quả, scan/triage và giới hạn còn lại](../testing/t014-ab-report.md).

Ngày: 2026-11-09 (KST). Các trial dưới đây **chưa áp dụng vào baseline**.
Baseline vẫn Airflow3.3.2/official constraints và Playwright1.56.1/Chromium141.0.7390.37.
Npm12.2.2, OS patches, pip26.3, gosu1.19 rebuild Go1.27.3 và loại công cụ không dùng
là hardening tương thích đã được thực hiện theo ủy quyền hiện hành; không đổi BR-08/MVP.

## A. Hai dependency Airflow cần override có kiểm soát

| Package | Constraint hiện tại | Candidate đã thử |
| --- | --- | --- |
| certifi |2026.7.22|2026.10.18|
| urllib3 |2.7.0|2.8.0|

Image trial `localhost/aat-airflow-minimal-overrides:0.1.0`, image ID
`fa46fd3da16ae3104e39fb5fed43c44ab2683f9181261257f4f5e7b536ebb13b`.
Parent là image đã harden cùng core3.3.2 và pip26.3; `pip freeze` chỉ thay hai package
trên, không thêm msgpack hoặc uv. `pip check` và import core/SDK3.3.2 PASS.
[Fresh init + DB/Airflow authenticated probes](../testing/t014-airflow-minimal-overrides-runtime.json)
PASS trong project riêng; containers đã down, volumes giữ nguyên. Không phải full ETL,
DAG deployment/recovery hay toàn bộ API contract PASS.

Scan trial:106HIGH/5CRITICAL, so với parent pip26.3 là108HIGH/6CRITICAL.
Điều này chỉ xử lý phần Python main environment, **không đóng các OS NO_FIX còn lại**.
Trước đó trial4package có vendor copies còn nguyên; đã xác định chúng nằm trong
`pip/_vendor`, nên cần patch pip riêng thay vì giả rằng top-level pip install đã vá hết.

**Xin duyệt A:** cho phép hai override có provenance riêng, giữ nguyên upstream constraints
file/hash và core3.3.2. Sau duyệt sẽ tạo lock artifacts/hashes và delta constraints riêng,
resolve lại app/ETL dưới policy được duyệt, kiểm pip check/SDK/auth/readiness và các gate
bị ảnh hưởng. Không ghi đè constraints Apache rồi giả là bản upstream nguyên gốc.
Phương án nâng core Airflow3.4 chưa được đề nghị áp dụng vì chưa có đủ contract/SDK evidence.

## B. Cặp Playwright/client/browser và OS thử nghiệm

| Thành phần | Baseline | Candidate đã thử |
| --- | --- | --- |
| @playwright/test và playwright-core |1.56.1|1.65.0|
| Official browser image |v1.56.1-noble|v1.65.0-resolute|
| Chromium thực tế |141.0.7390.37|158.0.8127.18|
| OS security patches |Noble exact lock hiện tại|apt/libapt-pkg7.0 =3.2.1ubuntu0.1|

Official manifest Linux/amd64 của Resolute:
`mcr.microsoft.com/playwright@sha256:fb9978a801599ea0a57079eb642ad75cb52dbe1b162c8bf1fc989a603aa39218`.
Image trial đã vá apt: `localhost/aat-pw165-resolute-patched:0.1.0`, ID
`fe730145f636fd53e5ee386b6269c3c8fba302b8e2077460d57af4dce54a261c`.

Build, browser launch/version và4E2E desktop/mobile/private-runtime smoke PASS.
Scan **0HIGH/0CRITICAL** cho image trial này tại snapshot đã ghi, không phải chứng nhận
không còn mọi rủi ro native browser. Scan nguồn ở
[final trial security](../testing/t014-round2-final-trial-security.json).
Chỉ nâng Noble lên1.65 vẫn có findings; Resolute ban đầu còn hai apt HIGH, đã vá exact
versions rồi build/test/scan lại. Không lấy kết quả image trước sửa làm PASS cho image sau.

Baseline Noble còn CVE-2025-3887 trong GStreamer H265 parser. Vendor Ubuntu có bản vá
Noble qua ESM/Ubuntu Pro; không tự mua/kích hoạt dịch vụ hoặc bỏ finding vì scanner NO_FIX.
[Ubuntu advisory](https://ubuntu.com/security/CVE-2025-3887),
[CVE record](https://www.cve.org/CVERecord?id=CVE-2025-3887).

**Xin duyệt B:** thay đồng bộ hai manifest/lock frontend và tests/e2e, official image/digest,
browser version, OS lock và compatibility expectations sang cặp đã thử; chạy lại thật các
runner/UI/nginx smoke và scan build/final stages. Không chỉ sửa expected string để test PASS.
Không áp dụng một phía hoặc dùng browser latest không khóa.

## C. Finding chưa được miễn trừ và phần reviewer cần quyết định

- [52occurrences đề xuất không reachable trong build-base](../testing/t014-build-base-review.json)
  ghi từng advisory: old gosu không được thực thi trong các target build, runtime binary
  đã được thay bằng cùng source1.19/Go1.27.3. MySQL shell không có dependent và không có
  RPM scriptlets; target chỉ gỡ package rồi COPY gosu. Đây là **đề xuất chờ reviewer**,
  không phải waiver đã chấp nhận và không áp cho các OS/library findings khác.
- Các finding OS NO_FIX hoặc chưa đủ bằng chứng vẫn OPEN/BLOCKED. Không dùng kết luận
  “local/test-only” hoặc “chưa thấy exploit” làm bằng chứng not-affected.
- Cần vendor/advisory/reachability review từng finding còn lại; nếu phải rebase OS hoặc
  backport ngoài baseline hiện tại, chuẩn bị candidate/build/scan/compatibility riêng.
  Không tự thay sang distro mới hoặc tự nhận rủi ro còn lại đã được chấp nhận.

**Duyệt A/B không tự mở gate T014.** Gate chỉ đóng khi các finding còn lại đã xử lý hoặc
có kết luận not-affected được reviewer duyệt theo bằng chứng, cùng CI và runtime gates
đúng source. Không chuyển Phase2 trong khi còn blocker. Constitution/reviewer checkbox
không bị sửa trong lượt này.

## Tái lập và provenance

Dockerfiles trial và metadata registry/manifest đặt trong [t014-round2-trials](t014-round2-trials).
Build parent từ `airflow/docker/Dockerfile` với tag trial parent nêu ở Dockerfile;
không trỏ image thử vào project baseline hoặc dùng `up --build` làm mất image trial.
Package graph, artifact hashes, image IDs, scan DB metadata và giới hạn test được giữ
trong report; thử nghiệm không thay việc resolve lock cuối sau khi được duyệt.

CI sample bytes Windows/Linux đã PASS ở SHA `99cdfefc1c287033f35cad4085fa9ef242db8c56`:
[run42493618597](https://github.com/qtrugle0113/fpt-spec-eng/actions/runs/42493618597).
CI này không phải full bootstrap hoặc security PASS; các thay đổi source sau đó phải có
run mới đúng SHA và chạy lại kiểm chứng bị ảnh hưởng.
