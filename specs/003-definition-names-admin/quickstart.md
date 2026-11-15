# Kiểm chứng

1. Dùng Node22.23.4 để chạy frontend typecheck/build/test:ui và test nhãn Definition.
2. Chạy unit bootstrap/local_admin và validation messages trong runner Python dependency hiện có.
3. Trên demo đúng record, chụp tập ID/volume; chạy script cập nhật local admin; login browser, kiểm quyền/service token; restart API và kiểm lại; so sánh dữ liệu.
4. Fresh fixture source overlay với project/ports/volumes riêng: init mới, login thật, restart/init lại, kiểm custom password và restore bằng unit/integration; không đụng volumes demo.
5. Cập nhật bằng chứng, chạy analyze/converge; chỉ đóng task đủ điều kiện.

Hướng dẫn lệnh cụ thể và kết quả được ghi tại docs/operations/local-airflow-admin.md và docs/testing/definition-admin-20261115.md sau triển khai.

## Lệnh tái lập đã dùng

```powershell
python -X utf8 scripts/configure-local-airflow-admin.py
python -X utf8 scripts/apply-local-definition-source.py
python -X utf8 tests/tools/verify_local_admin.py --project aat-portable-demo-a7f852ae --evidence docs/testing/definition-admin-20261115/demo-restart.json
```

Lệnh apply source từ chối chồng overlay lần hai; không chạy lại để reset dữ liệu. Build/typecheck dùng Node22.23.4; unit dùng `tests/tools/run_definition_units.py --image <backend-image-id> --evidence <workspace-file>`, không cần cài dependency Python lên host. Fresh dùng suite definition_admin của runner hiện hữu, `--source-overlay --frontend-artifact frontend/dist --keep-running --extra-spec language.spec.ts`, xem record và lệnh đầy đủ trong báo cáo. Không xóa volume để tái lập trên demo.
