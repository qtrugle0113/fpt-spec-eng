# Kiểm thử tải User Guide — 2026-11-15

## Phạm vi và quy trình

[Spec](../../specs/004-user-guide-download/spec.md) → [plan](../../specs/004-user-guide-download/plan.md) → [tasks](../../specs/004-user-guide-download/tasks.md).

Đã dùng skills speckit-specify, speckit-plan, speckit-tasks, speckit-analyze, speckit-implement trong repo. Constitution giữ nguyên; không cần hỏi lại. Checklist specify đạt 9/9; không có extensions.yml nên không có extension hook cần chạy. setup-plan/setup-tasks/check-prerequisites xác định đúng feature 004.

Analyze read-only trước khi sửa code: 6 yêu cầu, 6 task, coverage 100%; 0 mơ hồ, 0 trùng lặp, 0 lỗi CRITICAL/HIGH. T001/T002 quản trị trước triển khai, T006 bằng chứng bàn giao; không có task ngoài phạm vi.

Thêm ActionLink Download User Guide ở workspace-bar dùng chung; bar/actions wrap trên mobile. Giữ sáu menu. File static tiếng Việt đóng gói từ public; builder ghi cả outputs/public, Dockerfile COPY public trước build. Không sửa nghiệp vụ.

## Truy vết

| Yêu cầu | Task | Bằng chứng |
| --- | --- | --- |
| FR-001 | T004/T005 | Tải từ 6/6 route ở desktop và mobile |
| FR-002 | T003/T004/T005 | Tên đúng, URL giữ nguyên, Connections giữ nội dung bộ lọc |
| FR-003 | T003/T005 | SHA256 khớp; file offline có 16 mục/12 ảnh và zoom |
| FR-004 | T004/T005 | 1366/390/320px, trong viewport, focus/Enter, không tràn ngang |
| FR-005 | T003/T005 | HTTP static từ dist; tắt API vẫn tải; kiểm tra Docker COPY |
| FR-006 | T004/T005 | Giữ sáu menu, 0 request ghi, regression shell đạt |

## Lệnh và môi trường

Windows PowerShell, Node 22.23.4, Chromium 158.0.8127.18, frontend dependencies hiện có. Từ repo root, PATH trỏ `.tools/node-ui`:

```powershell
npm --prefix frontend run build
npm --prefix frontend run test:user-guide
npm --prefix frontend run test:shell
python -X utf8 docs/user-guide/build_guide.py
git diff --check -- frontend docs/user-guide/build_guide.py specs/004-user-guide-download README.md
```

## Kết quả

- **PASS build/typecheck**: tsc --noEmit và Vite build; HTML static không đi vào JS bundle.
- **PASS 13 lượt tải**: sáu route × hai kích thước 1366/390px, thêm Settings 320px. HTTP/download thật trên production preview; Settings tải bằng Enter ở cả ba kích thước.
- **PASS backend unavailable**: chặn tất cả `/api/v1/**` trong scenario nhưng vẫn tải; 0 request ghi, 0 pageerror.
- **PASS đồng nhất**: outputs/public/dist/HTTP/download cùng SHA256 `eab34cc68ec74e9465652a40e4cc2119a14d2d5e9e615c1f56084a4eb839b6ec`, 645922 bytes. Tái chạy builder giữ hash, đồng bộ hai bản.
- **PASS offline**: mở file tải bằng file:// khi offline, lang=vi, 16 chapter, 12 ảnh decode, zoom mở/đóng được, 0 request HTTP(S).
- **PASS regression shell**: 18 tổ hợp route/viewport, navigation search/mobile menu, không tràn ngang, 0 pageerror.
- Đã xem ảnh desktop/mobile: nút rõ trên thanh trên cùng, menu giữ nguyên. Xem [evidence](user-guide-download-20261115/).

SC-001–004 đạt trong phạm vi bản build frontend local. Constitution I–IV/X–XII đạt theo evidence; V–IX không áp dụng vì không sửa ETL/Excel/secrets/staging/runtime nghiệp vụ.

## Giới hạn

Dockerfile đã kiểm tra COPY public và dist thật; chưa build/scan image mới, chưa rollout container demo/production. Không suy nghiệm thu toàn hệ thống từ thay đổi static UI. Kiểm thử không thay dữ liệu nghiệp vụ.
