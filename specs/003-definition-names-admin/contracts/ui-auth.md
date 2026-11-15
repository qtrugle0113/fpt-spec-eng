# Hợp đồng tên và xác thực

UI: ETL Definition/Table Definition; template chỉ tải mẫu, input có file (.xlsx). Không đổi menu/route hoặc payload. Backend đổi message nhưng code/key ổn định. Excel Instructions thay câu chữ, giữ Version1.0/sheet/header.

Local auth: AAT_LOCAL_DEMO_AUTH=1 chỉ trong profile local loopback. Fresh tạo admin/admin; init lại không reset. Script existing phải xác minh project/ports/volume rồi backup, update admin, giữ user khác và recreate API không build. Sai password vẫn từ chối; role admin được xác minh thực tế. Không trả credential trong API response/log.
