# Hướng dẫn kiểm chứng giao diện

## Điều kiện

Node22.23.4 theo package.json, dependency theo lock, Chromium Playwright. Backend demo loopback28000, Airflow28080; không đổi stack/volumes.

## Lệnh

Tại `frontend`:

```powershell
npm.cmd ci --ignore-scripts
npm.cmd run typecheck
npm.cmd run build
npm.cmd run test:ui
```

`test:ui` phục vụ build trên loopback riêng, proxy `/api` đến backend thật; hỗ trợ `AAT_UI_API_TARGET` nếu khác cổng. Không ghi dữ liệu nghiệp vụ. Ảnh/kết quả tạm tại `.tools/ui-refresh/`; báo cáo chọn lọc tại `docs/testing/ui-refresh-20261115.md`.

Với máy chưa có API thật, có thể đặt `AAT_UI_FIXTURES_ONLY=1` để kiểm tra cô lập; kết quả này không thay cho nghiệm thu tích hợp. Bộ shell sẵn có chạy bằng `npm.cmd run test:shell`; có thể trỏ `AAT_SHELL_BASE_URL` đến preview có proxy. E2E đọc dữ liệu thật dùng `PLAYWRIGHT_BASE_URL` và chạy `accessibility.spec.ts dashboard.spec.ts` trong `tests/e2e`.

Để giữ preview phục vụ source mới và proxy API cho việc xem thủ công, tại `frontend`:

```powershell
node --input-type=module -e "import {preview} from 'vite'; await preview({configFile:false,preview:{host:'127.0.0.1',port:4179,strictPort:true,proxy:{'/api':{target:'http://127.0.0.1:28000',changeOrigin:true}}}})"
```

## Kết quả mong đợi

Sáu route ở1366×768 và390×844 không lỗi JS/tràn ngang, control đầu tiên trong viewport, menu/search hoạt động, template tải có dữ liệu, link Airflow bảo toàn URL/tab và có hình thức button, keyboard focus rõ. Fixture loading/empty/error là kiểm thử cô lập, không phải nghiệm thu API thật.

Repo chưa có lint script; typecheck/build và `git diff --check` là kiểm tra áp dụng. Không deploy preview thành demo chính thức.

## Tài khoản Airflow

Giữ operator/service account. Không cấu hình admin/admin do secret bootstrap một lần và yêu cầu không ghi đè tài khoản cũ; xem [research.md](research.md). Không in mật khẩu trong báo cáo.
