# Yêu cầu ban đầu — Airflow Automation Tool

## Bối cảnh

Data Engineer thường cần chuyển dữ liệu giữa các cơ sở dữ liệu hoặc từ tệp CSV/TXT vào cơ sở dữ liệu. Để thiết lập mỗi luồng, họ phải cấu hình kết nối, viết SQL, tạo DAG bằng Python và biết cách vận hành Apache Airflow. Việc này tốn thời gian và thường cần đến lập trình viên chuyên môn.

## Mục tiêu

Xây dựng một công cụ chạy bằng container (Podman hoặc Docker), có giao diện web và mẫu Excel, giúp Data Engineer hoặc người vận hành tạo, chạy và theo dõi các luồng ETL mà không cần tự viết SQL tạo bảng hay mã DAG bằng Python. Toàn bộ dịch vụ cần được cấu hình để khởi động bằng một lệnh `podman compose up --build -d`, không cần khởi động từng dịch vụ riêng.

Người dùng có thể:

- Tạo và quản lý kết nối cơ sở dữ liệu để dùng làm nguồn hoặc đích.
- Tải lên Table Definition để khai báo và tạo bảng trong cơ sở dữ liệu đích.
- Điền ETL Definition để khai báo và triển khai các DAG ETL lên Apache Airflow.
- Khai báo ánh xạ giữa các cột nguồn và cột đích trong ETL Definition, kể cả khi tên cột không giống nhau.
- Theo dõi DAG và các lần chạy trên Dashboard, rồi mở DAG tương ứng trực tiếp trong Airflow.
- Tải mẫu Table Definition, ETL Definition và hướng dẫn sử dụng từ giao diện web.

Nguồn dữ liệu cần hỗ trợ PostgreSQL, MySQL, CSV và TXT có dấu phân cách. Đích dữ liệu cần hỗ trợ PostgreSQL và MySQL.
