# Kiểm chứng tải User Guide

Từ repo root, với Node 22.23.4 và node_modules hiện có:

```powershell
$env:PATH = (Resolve-Path .tools/node-ui).Path + ';' + $env:PATH
npm --prefix frontend run build
npm --prefix frontend run test:user-guide
```

Test mở production preview loopback tạm, tải file thật từ sáu route và mở file offline; không cần backend. Request API bị chặn rõ để kiểm tra backend unavailable; request static không mock. Evidence ở `.tools/user-guide-download/`.

Thủ công: Download User Guide trên thanh trên cùng → kiểm tra không đổi trang → mở HTML tải về, đọc tiếng Việt, bấm ảnh phóng to. Thử Enter và mobile. Sáu menu giữ nguyên.

Tái sinh guide: `python -X utf8 docs/user-guide/build_guide.py` cần ảnh nguồn `.tools/user-guide/`, ghi đồng thời outputs/public. Frontend build không cần Python hoặc ảnh nguồn. Không suy PASS image/rollout từ kiểm tra Dockerfile.
