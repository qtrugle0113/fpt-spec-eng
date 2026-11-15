"""Tạo hướng dẫn HTML độc lập, nhúng ảnh thật và kiểm tra không thiếu asset."""
from pathlib import Path
import base64
import html
import json
import struct

ROOT=Path(__file__).resolve().parents[2]
ASSETS=ROOT/'.tools/user-guide'
OUTPUT=ROOT/'outputs/user-guide/Airflow-Automation-Tool-Huong-dan-su-dung.html'
META=json.loads((ASSETS/'images.json').read_text(encoding='utf-8'))['images']
used=[]


def picture(name,caption):
    path=ASSETS/(name+'.png')
    if not path.is_file():raise FileNotFoundError(path)
    used.append(name)
    raw=path.read_bytes()
    width,height=struct.unpack('>II',raw[16:24])
    data=base64.b64encode(raw).decode()
    annotations=META.get(name,{}).get('annotations',[])
    overlays=''.join(f'<span class="pin" style="left:{max(1,min(96,a["x"])):.2f}%;top:{max(1,min(96,a["y"])):.2f}%" aria-hidden="true">{a["number"]}</span>' for a in annotations)
    legend=''.join(f'<li><b>{a["number"]}</b> {html.escape(a["label"])}</li>' for a in annotations)
    compact=' style="max-width:560px;margin-inline:auto"' if name=='airflow-login' else ''
    return f'<figure><button class="screen"{compact} type="button" aria-label="Phóng to ảnh: {html.escape(caption)}"><img src="data:image/png;base64,{data}" width="{width}" height="{height}" alt="{html.escape(caption)}" loading="lazy">{overlays}</button><figcaption>{html.escape(caption)} <span>• Bấm ảnh để phóng to</span></figcaption>{f"<ul class=legend>{legend}</ul>" if legend else ""}</figure>'


def table(headers,rows):
    return '<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+c+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'


sections=[]
def section(identity,title,body):sections.append((identity,title,body))

section('bat-dau','Đọc trước khi bắt đầu', '''
<p class="lead">Bạn dùng công cụ này để khai báo cách lấy và chuyển dữ liệu bằng file Excel, đưa luồng xử lý lên Airflow rồi theo dõi từng lần chạy. Bạn không cần tự viết DAG Python hay câu lệnh tạo bảng.</p>
<div class="cards"><div><span class="kicker">Bạn chuẩn bị</span><h3>Nguồn, đích và quyền truy cập</h3><p>Biết lấy dữ liệu từ đâu, đưa vào bảng nào và được phép làm gì với dữ liệu đích. Nhờ người quản trị cung cấp thông tin kết nối database.</p></div><div><span class="kicker">Bạn sử dụng</span><h3>Excel + trình duyệt</h3><p>Dùng file mẫu tải từ ứng dụng. Giữ nguyên tên sheet, tên cột và phiên bản của mẫu; chỉ điền thông tin ở các dòng dữ liệu.</p></div></div>
<div class="note"><strong>Thống nhất cách gọi trong tài liệu</strong><p><b>Table Definition</b> là file Excel mô tả bảng và các cột. <b>ETL Definition</b> là file Excel mô tả luồng chuyển dữ liệu. <b>Template</b> chỉ là file mẫu ban đầu. Khi điền xong mẫu, file đó vẫn được gọi là ETL Definition hoặc Table Definition.</p></div>
<p>Tài liệu dành cho người trực tiếp vận hành. Tên nút trên ảnh vẫn là tiếng Anh để bạn tìm đúng chỗ bấm; phần giải thích dùng tiếng Việt. Các tên bảng, file và mã trên ảnh là dữ liệu demo, không phải giá trị bạn phải nhập y hệt.</p>
''')

section('quy-trinh','Nhìn nhanh toàn bộ quy trình', '''
<div class="flow"><div><b>01</b><strong>Kết nối</strong><span>Lưu và kiểm tra database</span></div><div><b>02</b><strong>Bảng đích</strong><span>Tạo bằng Table Definition nếu chưa có</span></div><div><b>03</b><strong>Nguồn</strong><span>Database hoặc file CSV/TXT</span></div><div><b>04</b><strong>Định nghĩa ETL</strong><span>Điền Excel, kiểm tra và xem lại</span></div><div><b>05</b><strong>Đưa lên Airflow</strong><span>Xác nhận triển khai, mở chạy</span></div><div><b>06</b><strong>Theo dõi</strong><span>Xem run, log và dữ liệu đích</span></div></div>
<ul><li><b>Nếu nguồn là database:</b> chuẩn bị kết nối nguồn và đích; không cần tải CSV/TXT.</li><li><b>Nếu nguồn là CSV/TXT:</b> tải file trong File Sources, kiểm tra cách đọc và xác thực toàn bộ file; vẫn cần kết nối database đích.</li><li><b>Nếu bảng đích đã có:</b> có thể bỏ bước tạo bảng. Hãy kiểm tra cấu trúc và quyền ghi trước khi làm ETL.</li></ul>
<div class="important"><strong>Ba mốc khác nhau, đừng nhầm</strong><p><b>VALIDATED</b>: file định nghĩa đã được kiểm tra. <b>DEPLOYED</b>: Airflow đã nhận DAG. <b>success</b> của một run: lần chạy đó đã hoàn tất. Upload thành công hoặc triển khai thành công chưa có nghĩa dữ liệu đã được chuyển xong.</p></div>
'''+picture('overview','Giao diện tổng quan: menu bên trái và Dashboard theo dõi tình hình chạy.'))

section('truy-cap','Mở ứng dụng và đăng nhập Airflow', '''
<p>Dùng địa chỉ do người phụ trách hệ thống cung cấp. Với bản local được dùng để chụp hướng dẫn này:</p>
'''+table(['Nơi cần mở','Địa chỉ và cách dùng'],[
['Airflow Automation Tool','<a href="http://127.0.0.1:4179" target="_blank" rel="noreferrer">http://127.0.0.1:4179</a> — bản giao diện hiện tại để xem thử. Ứng dụng local này không có bước đăng nhập riêng.'],
['Airflow','<a href="http://localhost:28080" target="_blank" rel="noreferrer">http://localhost:28080</a> — username <code>admin</code>, password <code>admin</code>. Tài khoản này chỉ dành cho bản local/demo.'],
['Nếu địa chỉ khác','Dùng đường dẫn được bàn giao cho môi trường của bạn. Cổng có thể khác theo cách cài đặt; địa chỉ trên không áp dụng cho mọi máy.']]) + '''
<ol class="steps"><li>Mở Airflow hoặc bấm <b>Open Airflow</b> từ ứng dụng.</li><li>Nhập <b>Username</b> và <b>Password</b>, chọn <b>Sign in</b>.</li><li>Trước khi chạy ETL, xem trạng thái <b>Scheduler</b> trong Airflow. Nếu chưa sẵn sàng hoặc đang đỏ, nhờ người quản trị bật dịch vụ trước.</li></ol>
<div class="note"><strong>Đừng dùng nhầm tài khoản</strong><p>admin/admin là tài khoản vào màn hình Airflow của demo. Đây <b>không phải</b> username/password để khai báo database trong Connections. Không dùng tài khoản này cho môi trường production.</p></div>
'''+picture('airflow-login','Màn hình đăng nhập Airflow.'))

section('menu','Chọn đúng màn hình cần dùng',table(['Menu trên ứng dụng','Khi nào bạn cần vào?'],[
['<b>Dashboard</b>','Xem nhanh số DAG, số lần chạy, tỷ lệ thành công và các run gần đây.'],
['<b>Connections</b>','Thêm, sửa và kiểm tra kết nối PostgreSQL/MySQL.'],
['<b>Table Management</b>','Tải mẫu Table Definition, kiểm tra cấu trúc, tạo bảng và xem lịch sử tạo bảng.'],
['<b>DAG Builder</b>','Chuẩn bị CSV/TXT, tải mẫu ETL Definition, xem lại nguồn–đích–lịch chạy rồi đưa DAG lên Airflow.'],
['<b>DAG Monitoring</b>','Xem từng DAG, từng lần chạy, số dòng xử lý và log của từng task.'],
['<b>Settings</b>','Chỉnh giá trị mặc định như số dòng mỗi đợt xử lý, múi giờ và chu kỳ làm mới Dashboard.']]) + '<p>Trên màn hình nhỏ, bấm <b>Open menu</b> để mở danh sách. Với bảng rộng, kéo ngang ngay trong vùng bảng để thấy các cột và nút ở bên phải.</p>')

section('ket-noi','Bước 1 · Khai báo và kiểm tra kết nối', '''
<ol class="steps"><li>Mở <b>Connections</b>, bấm <b>Add connection</b>.</li><li>Điền thông tin theo bảng dưới rồi bấm <b>Save connection</b>.</li><li>Trong danh sách, bấm vào mã kết nối để xem chi tiết; bấm <b>Test connection</b>.</li><li>Chỉ dùng kết nối cho các bước tiếp theo khi đã kiểm tra thành công. Nếu lỗi, xem lại host, port, tên database, username, password và quyền truy cập.</li></ol>
'''+picture('connections','Tạo mới hoặc tìm kết nối trong Connections.')+table(['Trường','Cách hiểu và cách điền'],[
['Connection code','Mã ngắn, dễ nhớ, ví dụ <code>pg_etl</code>. Điền đúng mã này trong Excel; không dùng tên hiển thị thay cho mã.'],
['Connection name','Tên để người vận hành dễ nhận biết, ví dụ “Database nhận dữ liệu thử nghiệm”.'],
['Database type','Chọn PostgreSQL hoặc MySQL đúng với máy chủ đang dùng.'],
['Host / Port','Tên máy chủ và cổng database do người quản trị cung cấp. Trong demo container, các host được cấu hình thường là <code>postgres</code>, <code>mysql</code>; không mặc định điền localhost.'],
['Database name / Schema','Tên database; PostgreSQL thường có schema như <code>public</code>. Với MySQL, schema gắn với tên database.'],
['Username / Password','Tài khoản database có quyền cần thiết. Giữ mật khẩu ngoài các file Excel.']]) + picture('connection-form','Biểu mẫu thêm kết nối: điền mã và thông tin database, sau đó lưu.')+'''
<p><b>Khi sửa kết nối:</b> mở chi tiết → <b>Edit connection</b>. Bỏ trống Password nếu muốn giữ mật khẩu cũ. Nếu kết nối đang được một luồng sử dụng, một số thay đổi hoặc thao tác xóa sẽ bị chặn; xem phần <b>Dependencies</b> trước khi xử lý.</p>
<p class="result"><b>Xong bước này khi:</b> bạn có mã kết nối nguồn/đích cần dùng và đã Test connection thành công. Save connection đơn thuần chưa chứng minh database truy cập được.</p>
''')

section('tao-bang','Bước 2 · Tạo bảng đích bằng Table Definition', '''
<p>Nếu bảng đích chưa có, tạo bảng ở đây trước khi khai báo ETL. Nếu đã có bảng đúng cấu trúc, chuyển sang bước chuẩn bị nguồn.</p>
<ol class="steps"><li>Mở <b>Table Management</b> → <b>Download Table Definition template</b>.</li><li>Mở Excel, giữ nguyên ba sheet <code>Instructions</code>, <code>Tables</code>, <code>Columns</code>. Điền thông tin bảng và các cột rồi lưu dạng <code>.xlsx</code>.</li><li>Chọn file tại <b>Table Definition file (.xlsx)</b> → <b>Upload Table Definition</b>.</li><li>Chọn <b>Target connection</b> đúng với kết nối đích đã kiểm tra → <b>Validate Table Definition</b>.</li><li>Ở <b>Review tables</b>, kiểm tra tên database/schema/bảng, kiểu dữ liệu, khóa chính và <b>Generated SQL</b>.</li><li>Chỉ sau khi đã đọc và thấy đúng, tích ô xác nhận rồi bấm <b>Confirm and create tables</b>.</li><li>Xem <b>Table creation jobs</b> → <b>View results</b> để biết kết quả của từng bảng; dùng <b>View table details</b> để kiểm tra cấu trúc thực tế.</li></ol>
'''+picture('table-upload','Tải mẫu Table Definition, chọn file và upload trước khi kiểm tra cấu trúc.')+table(['Sheet','Bạn cần điền gì?'],[
['Instructions','Giữ phiên bản <code>1.0</code> và tên tài liệu đúng mẫu. Không đổi tên sheet hoặc header.'],
['Tables','Mỗi dòng mô tả một bảng: mã kết nối đích, schema, tên bảng và mô tả.'],
['Columns','Mỗi dòng mô tả một cột của bảng: tên cột, thứ tự, kiểu dữ liệu, độ dài, cho phép để trống hay không, có phải khóa chính hay không.']])+'''
<div class="note"><strong>Các chỗ hay điền sai</strong><ul><li><b>Varchar</b> cần Length; <b>Decimal</b> cần Precision và Scale.</li><li>Cột khóa chính không được Nullable. Điền TRUE/FALSE theo đúng mẫu.</li><li>Không chèn công thức Excel hoặc câu SQL vào các ô dữ liệu.</li><li>Mỗi lượt xác nhận chọn một kết nối đích; các bảng trong file phải phù hợp với kết nối đó.</li></ul></div>
<p><b>CREATED</b> nghĩa là đã tạo bảng. <b>ALREADY_EXISTS</b> nghĩa là bảng đã tồn tại và được giữ nguyên; không có nghĩa ứng dụng vừa sửa lại bảng đó. <b>PARTIALLY_SUCCEEDED</b> nghĩa là chỉ một phần công việc thành công — phải mở từng kết quả để xem.</p>
<p class="result"><b>Xong bước này khi:</b> bảng đích đã có, cấu trúc đúng và bạn đã kiểm tra kết quả từng bảng.</p>
''')

section('nguon-file','Bước 3 · Chuẩn bị nguồn database hoặc CSV/TXT', '''
<div class="cards"><div><h3>Nguồn là database</h3><p>Dùng kết nối nguồn đã Test connection. Ghi đúng mã kết nối, schema và tên bảng nguồn trong ETL Definition. Không cần upload file CSV/TXT.</p></div><div><h3>Nguồn là file</h3><p>Trong DAG Builder, kéo tới <b>File Sources</b>. Tải CSV/TXT ở đây, không đưa file CSV vào ô upload ETL Definition.</p></div></div>
<ol class="steps"><li>Chọn CSV/TXT tại <b>Source file</b>.</li><li>Kiểm tra Encoding, Delimiter, dấu ngoặc kép, cách đọc ký tự đặc biệt và dòng tiêu đề. Bấm <b>Upload source file</b>.</li><li>Trong Uploaded files, bấm <b>Open file</b>, rồi <b>Preview with these settings</b> để xem cột và vài dòng đầu.</li><li>Nếu sửa cách đọc file, xem Preview lại và bấm <b>Confirm parser change</b> để lưu thay đổi. Nếu không có thay đổi thì không cần xác nhận lại parser.</li><li>Bấm <b>Validate full file</b>. Chờ kiểm tra xong toàn bộ file, không chỉ phần Preview.</li><li>Khi file hợp lệ, bấm <b>Select as ETL source</b>. Sao chép mã <b>Reference</b> của file để điền vào Excel.</li></ol>
'''+picture('file-upload','File Sources: chọn CSV/TXT và xác định cách đọc file.')+picture('file-preview','Mở file để xem Reference, kiểm tra parser và xem trước dữ liệu.')+table(['Trường','Bạn cần chú ý'],[
['Encoding','Thường là <code>utf-8</code>. Nếu chữ tiếng Việt bị lỗi, kiểm tra lại mã hóa lúc xuất file; có thể cần utf-8-sig nếu file có BOM.'],
['Delimiter preset','Chọn đúng dấu phân cách: Comma là dấu phẩy, Semicolon là chấm phẩy, Pipe là <code>|</code>, Tab là tab.'],
['First record contains column headers','Bật khi dòng đầu là tên cột. Nếu tắt, hệ thống đặt tên <code>column_1</code>, <code>column_2</code>…'],
['NULL marker',r'Mặc định <code>\N</code>. Giá trị trống, chữ “0”, chữ “false” và NULL không phải cùng một thứ; hãy xem Preview trước.']])+'''
<div class="important"><strong>Reference khác tên file và đường dẫn</strong><p>Điền mã Reference vào cột <b>Source File Reference</b> của ETL Definition. Không điền <code>C:\\…\\khach_hang.csv</code> hay chỉ tên file. Chọn file trên UI không tự sửa nội dung Excel giúp bạn.</p></div>
<p>Preview chỉ xem tối đa một phần nhỏ dữ liệu. File hiển thị đẹp ở vài dòng đầu vẫn có thể lỗi ở cuối; chỉ dùng nguồn sau khi Validate full file thành công cho cấu hình đang dùng. Nếu thay parser, cần kiểm tra lại.</p>
''')

section('dinh-nghia-etl','Bước 4 · Điền ETL Definition', '''
<p>Mở <b>DAG Builder</b> → <b>Download ETL Definition template</b>. Một dòng trong <code>ETL_Definitions</code> mô tả một DAG: lấy dữ liệu từ một nguồn, đưa vào một bảng đích. Sheet <code>Column_Mappings</code> mô tả cách ghép cột nguồn với cột đích.</p>
'''+picture('etl-upload','ETL Definition là file Excel định nghĩa luồng; ô này không dùng để tải CSV/TXT.')+table(['Nhóm trường','Điền thế nào cho đúng?'],[
['DAG ID','Đặt mã riêng cho luồng, ví dụ <code>demo_khach_hang_01</code>. Nếu mã đã được dùng, chọn mã khác và sửa các dòng mapping liên quan cho khớp.'],
['Nguồn DB','Điền Source Connection Code, Source Schema và Source Table. Để trống Source File Reference.'],
['Nguồn CSV/TXT','Điền Source Type là CSV hoặc TXT và Source File Reference vừa sao chép. Để trống các trường kết nối/schema/bảng nguồn DB.'],
['Đích','Điền Target Connection Code, Target Schema và Target Table. Bảng đích phải có trước; DAG Builder không tự tạo bảng đích.'],
['Schedule / Start Date','<code>Manual</code> để tự bấm chạy. Nếu dùng lịch cron, cần Start Date phù hợp và múi giờ rõ ràng.'],
['Timezone / Catchup','Ví dụ <code>Asia/Ho_Chi_Minh</code>. Catchup FALSE để tránh tự chạy bù các khoảng thời gian trong quá khứ ngoài ý muốn.'],
['Load Strategy / Conflict Key','Chọn APPEND, UPSERT hoặc FULL_REFRESH. UPSERT phải chỉ rõ khóa dùng để khớp bản ghi, phù hợp khóa chính/unique ở bảng đích.'],
['Batch Size / Retry','Batch Size là số dòng xử lý mỗi đợt. Có thể để trống để dùng mặc định; không tự tăng lớn chỉ để xử lý một lỗi dữ liệu.'],
['Enabled/Paused','Nên bắt đầu bằng Paused. Dù Excel ghi Enabled, DAG mới vẫn cần bước xác nhận mở chạy riêng.'],
['Column Mapping Reference','Nếu có mapping, dùng đúng DAG ID để gắn các dòng ở Column_Mappings với luồng này.']])+'''
<h3>Cách ghép cột trong Column_Mappings</h3>
'''+table(['Cách xử lý','Dùng khi nào?'],[
['Direct Mapping','Ghép trực tiếp cột nguồn sang cột đích khi kiểu dữ liệu phù hợp.'],
['Type Conversion','Cần chuyển kiểu, ví dụ mã id trong CSV là chữ nhưng cột đích là Integer.'],
['Constant Value','Gán một giá trị cố định; điền theo định dạng JSON mà mẫu yêu cầu.'],
['NULL Handling','Xử lý giá trị NULL theo cấu hình và giá trị mặc định đã khai báo.']])+'''
<p>Dòng mapping cần đúng DAG ID, Source Column, Target Column và Enabled=TRUE. Với CSV/TXT, hệ thống đọc giá trị dưới dạng chuỗi hoặc NULL; <b>không tự đoán kiểu số/ngày</b>. Hãy dùng Type Conversion khi chuyển sang kiểu số hoặc ngày.</p>
<p class="result"><b>Trước khi upload:</b> lưu .xlsx, đóng file nếu Excel đang khóa, kiểm tra lại tên cột và mã kết nối. File Definition tối đa10MiB; đừng đổi tên header để “dễ đọc hơn”.</p>
''')

section('vi-du','Ví dụ dễ làm theo · CSV → bảng PostgreSQL', '''
<p>Ví dụ này giúp bạn hiểu các thông tin phải khớp với nhau. Hãy làm trên database thử nghiệm và đổi tên bảng/DAG nếu các tên dưới đây đã tồn tại.</p>
<div class="example"><h3>1. File CSV gồm hai cột</h3><pre>id,name
1,An
2,Bình</pre><a class="button secondary" download="khach_hang_demo.csv" href="data:text/csv;charset=utf-8,id%2Cname%0A1%2CAn%0A2%2CB%C3%ACnh%0A">Tải CSV của ví dụ</a><p>File dùng UTF-8, dấu phẩy và có dòng tiêu đề. Tải file lên File Sources, kiểm tra toàn bộ file rồi lấy Reference.</p></div>
<h3>2. Tạo bảng bằng Table Definition</h3>
<p>Trong Tables: mã kết nối đích là mã đã được kiểm tra, ví dụ <code>pg_etl</code>; schema <code>public</code>; bảng <code>khach_hang_demo</code>. Trong Columns:</p>
'''+table(['Column Name','Column Order','Data Type','Length','Nullable','Primary Key'],[
['id','1','Integer','Để trống','FALSE','TRUE'],['name','2','Varchar','100','TRUE','FALSE']])+'''
<h3>3. Khai báo ETL và mapping</h3>
'''+table(['Trường','Giá trị cho ví dụ'],[
['DAG ID','<code>demo_khach_hang_01</code>'],['Source Type','CSV'],['Source File Reference','Mã Reference thật của file vừa upload; không chép nguyên câu hướng dẫn này vào Excel.'],['Target Connection Code / Schema / Table','<code>pg_etl</code> / <code>public</code> / <code>khach_hang_demo</code> — thay mã kết nối nếu môi trường dùng mã khác.'],['Schedule / Timezone / Catchup','<code>Manual</code> / <code>Asia/Ho_Chi_Minh</code> / <code>FALSE</code>'],['Load Strategy / Conflict Key','<code>APPEND</code> / để trống — chỉ chạy thử một lần vào bảng vừa tạo.'],['Enabled/Paused / Column Mapping Reference','<code>Paused</code> / <code>demo_khach_hang_01</code>']])+table(['DAG ID','Source Column','Target Column','Optional Transformation Type','Enabled'],[
['demo_khach_hang_01','id','id','Type Conversion','TRUE'],['demo_khach_hang_01','name','name','Direct Mapping','TRUE']])+'''
<p>Giữ các trường không áp dụng trống theo mẫu; không điền thông tin DB nguồn cho nguồn CSV. Sau khi validate, triển khai và mở chạy theo các bước tiếp theo. Với đúng file này và bảng đích mới, kết quả cần kiểm tra là <b>2 dòng với id1 và2</b>.</p>
<div class="note"><strong>Nếu muốn chạy lại ví dụ</strong><p>APPEND không tự xóa dữ liệu cũ. Với khóa chính id, chạy lại một lượt mới có thể báo lỗi trùng khóa. Đừng chuyển sang FULL_REFRESH chỉ để bỏ qua lỗi; hãy xem lại mục đích hoặc cấu hình UPSERT đúng khóa nếu cần cập nhật dữ liệu.</p></div>
''')

section('trien-khai','Bước 5 · Kiểm tra, xem lại và đưa DAG lên Airflow', '''
<ol class="steps"><li>Chọn <b>ETL Definition file (.xlsx)</b> → <b>Upload ETL Definition</b> → <b>Validate ETL Definition</b>.</li><li>Nếu có lỗi, xem phần ETL validation issues. Dựa vào sheet, row và column để sửa đúng ô rồi upload bản mới. Không bấm triển khai khi còn lỗi.</li><li>Ở <b>Sources and mappings</b>, kiểm tra nguồn, bảng đích, tên cột và cách chuyển kiểu. Nếu file có nhiều DAG, chỉ chọn những luồng bạn muốn triển khai.</li><li>Bấm <b>Review schedules and load policies</b>, kiểm tra lịch, múi giờ, cách ghi dữ liệu và cấu hình chạy lại.</li><li>Ở <b>Confirm and deploy</b>, đọc lại từng luồng. Nếu có SQL tạo đối tượng hỗ trợ, xem nội dung và xác nhận riêng khi bạn đồng ý.</li><li>Tích ô xác nhận phạm vi rồi bấm <b>Confirm and deploy workflows</b>. Chờ kết quả của từng DAG.</li><li>Chỉ coi là triển khai xong khi <b>Registration: DEPLOYED</b>. Khi có nút <b>Open Airflow</b>, có thể mở để đối chiếu DAG.</li></ol>
<div class="stage-strip"><span>1. Upload and validate</span><span>2. Sources and mappings</span><span>3. Schedules and load</span><span>Confirm and deploy</span></div>
<div class="important"><strong>DAG mới chưa tự chạy ngay</strong><p>Sau khi triển khai, DAG mới ở trạng thái Paused để bạn có thời gian kiểm tra. Bạn còn cần xác nhận mở chạy hoặc bật lịch. Triển khai DAG cũng không tự cấp quyền thay thế toàn bộ dữ liệu cho FULL_REFRESH.</p></div>
<p>Nếu bản xem lại đã hết hạn hoặc thông tin nguồn/đích vừa thay đổi, dùng <b>Refresh ETL preview</b> hoặc mở lại bước xem lại theo nút đang hiển thị. Kiểm tra lại trước khi xác nhận; không cố dùng lần xác nhận cũ.</p>
<p>Luồng đã validate có thể mở lại bằng <b>Open ETL Definition</b> trong <b>ETL Definition history</b>. Không cần upload lại cùng một cấu hình chỉ để tiếp tục xem hoặc thao tác.</p>
''')

section('chay','Bước 6 · Chạy thử, bật lịch và tạm dừng', '''
<h3>DAG vừa triển khai trong DAG Builder</h3>
<ol class="steps"><li>Ở kết quả DEPLOYED, đọc phần <b>Workflow commands</b>.</li><li>Tích xác nhận đổi trạng thái, rồi chọn <b>Enable manual execution</b> nếu Schedule=Manual, hoặc <b>Activate schedule</b> nếu dùng lịch.</li><li>Khi cần chạy ngay, đọc phần xác nhận lượt chạy mới, tích ô xác nhận và chọn <b>Run workflow now</b>.</li><li>Mở <b>DAG Monitoring</b> để theo dõi run thực tế. Đừng chỉ dựa vào thông báo lệnh gửi thành công.</li></ol>
<h3>DAG đã có sẵn trong DAG Monitoring</h3>
<ol class="steps"><li>Bấm <b>View workflow</b>.</li><li>Trong Command, chọn <b>Trigger manual run</b>, <b>Unpause / activate schedule</b> hoặc <b>Pause future scheduling</b> theo việc cần làm.</li><li>Bấm <b>Review workflow command</b>, kiểm tra revision, bảng đích và cách ghi dữ liệu.</li><li>Nếu cần, chọn quyền thay thế phù hợp. Đọc cảnh báo, tích xác nhận rồi bấm <b>Confirm workflow command</b>.</li></ol>
'''+picture('workflow-controls','Workflow commands: chọn việc cần làm và xem lại trước khi xác nhận.')+'''
<div class="important"><strong>Chạy tay không tự bỏ Paused</strong><p>Nếu gửi run khi DAG còn Paused, run có thể nằm ở queued cho đến khi bạn xác nhận mở chạy riêng. Kiểm tra trạng thái DAG trước; <b>không gửi thêm nhiều run</b> để xử lý một run đang chờ.</p></div>
<p><b>Pause future scheduling</b> chỉ dừng các lượt lên lịch tiếp theo, không hủy một run đã bắt đầu. Nếu cần xử lý run đang chạy hoặc bị kẹt, xem log và phối hợp với người quản trị.</p>
''')

section('cach-ghi','Chọn đúng cách ghi dữ liệu',table(['Load Strategy','Cách hiểu','Điểm cần nhớ'],[
['<b>APPEND</b>','Thêm dữ liệu mới vào bảng, giữ dữ liệu đã có.','Một lượt chạy mới có thể tạo dữ liệu trùng hoặc lỗi trùng khóa. Không coi bấm chạy lại là thao tác vô hại.'],
['<b>UPSERT</b>','Khớp theo khóa: đã có thì cập nhật, chưa có thì thêm.','Conflict Key phải khớp khóa chính/unique thật của bảng đích. Không chọn tùy ý một cột chỉ vì “trông giống mã”.'],
['<b>FULL_REFRESH</b>','Thay toàn bộ dữ liệu của bảng đích bằng dữ liệu của lượt chạy.','Chỉ dùng khi bạn có quyền và đã xác nhận đúng phạm vi. Có bước cấp quyền riêng; không chỉ chọn giá trị này trong Excel.']])+'''
<h3>Nếu dùng FULL_REFRESH</h3>
<ol class="steps"><li>Mở phần <b>Replacement authority</b> ở DAG Builder sau khi đã xem lại định nghĩa.</li><li>Chọn <b>ONCE</b> cho một lượt chạy tay, hoặc <b>SCHEDULED</b> cho lịch chạy lặp lại đã được duyệt.</li><li>Đọc đúng tên bảng đích, revision và phạm vi. Tích xác nhận rồi bấm <b>Grant ONCE authority</b> hoặc <b>Grant SCHEDULED authority</b>.</li><li>Chọn quyền vừa cấp qua <b>Use for manual run</b> hoặc <b>Use for schedule activation</b> khi cần, rồi mới xác nhận lệnh chạy/bật lịch.</li></ol>
<div class="important"><strong>Quyền làm rỗng bảng là một quyết định riêng</strong><p>Chỉ bật <b>Allow a valid empty dataset to empty the target</b> khi bạn thực sự đồng ý: nguồn hợp lệ nhưng không có dòng nào thì bảng đích cũng sẽ bị làm rỗng. Nguồn bị lỗi không được coi là nguồn rỗng hợp lệ.</p></div>
<p>ONCE không thay cho quyền bật lịch SCHEDULED. Một run mới sau khi ONCE đã được dùng cần quyền mới. Thu hồi quyền không tự hủy một giao dịch đã được chấp nhận trước đó.</p>
''')

section('theo-doi','Xem kết quả, số dòng và log', '''
<ol class="steps"><li>Vào <b>DAG Monitoring</b>, tìm DAG ID. Có thể lọc theo Ownership, Schedule state và Latest run state.</li><li>Bấm <b>View workflow</b> để xem lịch sử; chọn <b>View run details</b> của đúng run cần kiểm tra.</li><li>Đọc State, thời gian bắt đầu/kết thúc và phần <b>ETL evidence</b>: Extracted rows, Validated rows, Loaded rows, Failed rows.</li><li>Ở <b>Task attempts</b>, bấm <b>View attempt logs</b>. Chọn đúng attempt nếu task đã thử lại; dùng <b>Next log page</b> khi có thêm log.</li><li>Nếu cần xem sâu hơn, dùng <b>Open Airflow</b>. Đối chiếu cả dữ liệu ở bảng đích trước khi kết luận công việc đã đúng.</li></ol>
'''+picture('monitoring','Danh sách DAG: View workflow để xem chi tiết, Open Airflow để mở màn hình Airflow.')+picture('run-details','Chi tiết một run thực tế: trạng thái, số dòng và từng task.')+table(['Trạng thái','Bạn nên hiểu và làm gì?'],[
['queued','Run đang chờ. Kiểm tra DAG còn Paused không, Scheduler có sẵn sàng không và có đang bị giới hạn tài nguyên không.'],
['running','Đang chạy. Xem task/log và tiến độ; không gửi thêm một run chỉ vì chưa thấy kết quả ngay.'],
['success','Run đã hoàn tất thành công. Đối chiếu số dòng và dữ liệu đích để xác nhận đúng nhu cầu.'],
['failed','Có bước thất bại. Mở đúng task/attempt để đọc log trước khi quyết định chạy lại.'],
['NEEDS_RECONCILIATION / UNKNOWN','Chưa thể kết luận chắc chắn tác động đã hoàn tất hay chưa. Nhờ người quản trị đối chiếu; không xóa file, bảng hoặc gửi lệnh mới liên tục.'],
['Not available / Stale data','Dữ liệu không có hoặc chưa được làm mới. Không hiểu thành số0 hay tự kết luận chưa có lỗi.']])+'''
<p><b>Ownership=EXTERNAL</b> là luồng bên ngoài ứng dụng quản lý. Bạn có thể xem nhưng không mặc định có các lệnh điều khiển hoặc số liệu ETL của ứng dụng cho luồng đó.</p>
''')

section('dashboard-settings','Dashboard và các giá trị mặc định', '''
<h3>Dashboard: xem nhanh, nhưng nhớ chọn đúng khoảng thời gian</h3>
<p>Chọn From date, To date, Timezone và Ownership scope. Bấm <b>Refresh dashboard</b> để lấy lại số liệu; bật <b>Auto Refresh</b> nếu muốn tự làm mới theo chu kỳ.</p>
<ul><li><b>Total DAGs / Active DAGs / Paused DAGs:</b> số luồng hiện tại, không phải số lần chạy.</li><li><b>Total DAG Runs / Successful Runs / Failed Runs:</b> các lần chạy trong khoảng thời gian đã chọn.</li><li><b>Success Rate:</b> tỷ lệ successful trên successful + failed; không tính run đang chạy vào mẫu số này.</li><li><b>Recent runs:</b> mở đúng run để xem chi tiết. <b>Lifetime history</b> là toàn bộ lịch sử trong phạm vi Ownership đang chọn, không bị giới hạn bởi From date/To date.</li></ul>
<h3>Settings: thay mặc định cho công việc mới</h3>
'''+table(['Trường','Ý nghĩa và giới hạn'],[
['Default Batch Size','Số dòng mỗi đợt xử lý,1–10.000. Chỉ áp dụng khi ETL Definition mới để trống Batch Size; không phải tổng số dòng tối đa của file.'],
['Dashboard Refresh Interval','Chu kỳ làm mới Dashboard khi bật Auto Refresh,5–3.600giây.'],
['Default Timezone','Múi giờ mặc định cho nơi có dùng giá trị mặc định. ETL Definition vẫn cần khai báo Timezone rõ ràng.'],
['Staging Retention','Số ngày giữ dữ liệu tạm,1–365. Không tự xóa các dữ liệu đang được giữ để xử lý sự cố.']])+picture('settings','Settings: sửa giá trị rồi Save settings; thông tin ứng dụng ở bên phải chỉ để xem.')+'''
<p>Chỉnh xong bấm <b>Save settings</b>. Nếu báo có người/phiên khác vừa sửa, bấm <b>Reload settings</b>, đọc lại rồi mới thay đổi. Các định nghĩa đã validate hoặc DAG đã triển khai <b>không tự đổi theo Settings mới</b>.</p>
''')

section('su-co','Gặp lỗi thì xử lý theo thứ tự nào?',table(['Bạn đang gặp gì?','Cách xử lý nên làm'],[
['Test connection thất bại','Kiểm tra host/port/database, username/password và quyền. Nếu dùng container, nhờ người quản trị xác nhận tên host được phép; không tự thay host thành localhost.'],
['Validate báo sheet/row/column','Mở đúng sheet và ô được báo. Giữ tên header/version; sửa dữ liệu rồi upload bản mới. Nếu không hiểu kiểu dữ liệu, đối chiếu bảng đích.'],
['Target identity or connection could not be verified','Nhờ người quản trị xác minh database và kết nối đích vẫn đúng môi trường. Không đổi sang bảng khác chỉ để vượt bước kiểm tra.'],
['Nút Confirm bị mờ','Đọc các điều kiện ngay phía trên: đã validate chưa, đã chọn DAG chưa, đã tích xác nhận chưa, review có hết hạn không, FULL_REFRESH đã có đúng quyền chưa.'],
['Run nằm queued lâu','Kiểm tra Paused, Scheduler và tài nguyên. Chỉ mở chạy bằng bước xác nhận phù hợp; không bấm Run nhiều lần.'],
['Nguồn CSV sai cột hoặc lỗi dấu tiếng Việt','Kiểm tra Encoding, Delimiter và Header; Preview lại. Nếu đổi parser, lưu thay đổi và Validate full file lại.'],
['Mạng ngắt khi đang gửi lệnh','Mở lịch sử và Refresh saved operation / Refresh deployment results để xem trạng thái đã lưu trước khi thử lại. Lệnh có thể đã được nhận dù trình duyệt chưa nhận phản hồi.'],
['Báo lỗi409 hoặc412','409 thường là xung đột/đang có công việc dùng dữ liệu;412 thường là thông tin đã thay đổi ở phiên khác. Tải lại, đọc trạng thái mới rồi xử lý, không cố xác nhận bằng thông tin cũ.'],
['UNKNOWN / NEEDS_RECONCILIATION','Giữ nguyên hiện trạng và liên hệ người quản trị. Không xóa bảng, source file, dữ liệu tạm hoặc volume để làm mất thông báo lỗi.']])+'''
<div class="note"><strong>Khi cần nhờ hỗ trợ, gửi đúng thông tin</strong><p>Gửi DAG ID, Run ID hoặc Operation reference, thời điểm và múi giờ, ảnh lỗi, sheet/dòng/cột nếu là lỗi Excel. <b>Không gửi mật khẩu, token hoặc toàn bộ file dữ liệu nhạy cảm</b> qua ảnh chụp/log.</p></div>
''')

section('checklist','Bảng nhắc nhanh trước khi xác nhận', '''
<div class="checklist"><label><input type="checkbox"> Đúng môi trường và đúng database đích; đang dùng bảng thử nghiệm nếu chỉ chạy thử.</label><label><input type="checkbox"> Các kết nối cần dùng đã Test connection thành công.</label><label><input type="checkbox"> Bảng đích có đủ cột và đúng kiểu dữ liệu.</label><label><input type="checkbox"> Nếu dùng CSV/TXT: đúng Encoding, Delimiter, Header và đã Validate full file.</label><label><input type="checkbox"> ETL Definition dùng đúng mã kết nối/Reference, đúng mapping và cách chuyển kiểu.</label><label><input type="checkbox"> Đã kiểm tra lịch, múi giờ, Catchup và Load Strategy.</label><label><input type="checkbox"> Đã đọc phạm vi ảnh hưởng; FULL_REFRESH có đúng quyền và không vô tình cho phép làm rỗng bảng.</label><label><input type="checkbox"> DAG đã DEPLOYED, đã mở chạy đúng cách và Scheduler sẵn sàng.</label><label><input type="checkbox"> Sau khi chạy: đã xem đúng run, số dòng/log và kiểm tra dữ liệu đích.</label></div>
<p class="small">Các ô đánh dấu này chỉ giúp bạn tự rà soát trong tài liệu. Chúng không cấp quyền hoặc gửi lệnh vào hệ thống và không được lưu lại khi đóng file.</p>
'''+table(['Từ trên màn hình','Nói đơn giản'],[
['DAG','Một luồng công việc do Airflow quản lý.'],['Run','Một lần chạy cụ thể của DAG.'],['Task / Attempt','Một bước trong luồng / một lần thử thực hiện bước đó.'],['Validate','Kiểm tra file và các thông tin liên quan trước khi cho đi tiếp.'],['Review / Preview','Xem lại cấu hình, dữ liệu mẫu hoặc câu SQL trước khi xác nhận.'],['Deploy','Đưa định nghĩa luồng lên Airflow và xác minh Airflow đã nhận.'],['Paused / Unpaused','Đang tạm khóa chạy / đã mở chạy theo điều kiện cấu hình.'],['Mapping','Quy tắc ghép cột nguồn vào cột đích.'],['Revision','Phiên bản cấu hình đã được lưu để biết chính xác run dùng bản nào.']]))

CSS='''
:root{--ink:#183b45;--muted:#526a74;--teal:#007f79;--line:#d9e6e8;--soft:#f2f8f7;--paper:#fff}*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:26px}body{margin:0;background:#f4f7f8;color:var(--ink);font:16px/1.7 "Segoe UI",Arial,sans-serif}a{color:#006d67;text-underline-offset:3px}button,input{font:inherit}button{cursor:pointer}:focus-visible{outline:3px solid #006963;outline-offset:3px}.top{background:#fff;border-bottom:1px solid var(--line);padding:17px 32px;display:flex;align-items:center;justify-content:space-between;gap:14px}.brand{font-weight:750;letter-spacing:-.3px}.brand em{font-style:normal;background:var(--teal);color:#fff;padding:5px 11px;border-radius:7px;margin-right:9px}.button{display:inline-block;padding:8px 14px;border:1px solid var(--teal);border-radius:6px;background:var(--teal);color:#fff;text-decoration:none;font-weight:600;font-size:14px}.button.secondary{background:#fff;color:#006963}.layout{display:grid;grid-template-columns:258px minmax(0,1fr);max-width:1530px;margin:auto}.toc{position:sticky;top:0;max-height:100vh;overflow-y:auto;padding:28px 18px 30px 24px;align-self:start}.toc h2{font-size:13px;text-transform:uppercase;letter-spacing:.12em;color:var(--teal);margin:0 0 14px}.toc a{display:block;font-size:13px;line-height:1.5;text-decoration:none;color:#526a74;padding:8px 10px;border-radius:5px;margin-bottom:3px}.toc a:hover,.toc a.active{background:#dff1ed;color:#005c56}.toc .small{margin:20px 10px;font-size:12px}main{min-width:0;background:#fff;border-inline:1px solid var(--line)}.cover{padding:54px 56px 40px;background:linear-gradient(125deg,#edf8f4,#fff 75%);border-bottom:1px solid var(--line)}.eyebrow{font-size:12px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:var(--teal)}h1{font-size:clamp(30px,4vw,48px);line-height:1.18;letter-spacing:-1.3px;margin:14px 0 18px}h1 span{display:block;color:var(--teal);font-size:.58em;line-height:1.4;letter-spacing:-.5px;margin-top:12px}.cover p{max-width:740px;color:var(--muted)}.tags{display:flex;gap:8px;flex-wrap:wrap;margin-top:24px}.tags span{border:1px solid #b9d8d3;padding:5px 10px;border-radius:25px;font-size:12px;background:#fff}.content{padding:0 56px}section.chapter{padding:35px 0 40px;border-bottom:1px solid var(--line);scroll-margin-top:10px}h2{font-size:26px;line-height:1.35;letter-spacing:-.5px;margin:0 0 22px}h2 .num{display:block;color:var(--teal);font-size:11px;letter-spacing:.14em;text-transform:uppercase;margin-bottom:8px}h3{font-size:19px;line-height:1.4;margin:26px 0 12px}p{margin:12px 0}li{margin-block:8px}b,strong{font-weight:650}.lead{font-size:19px;line-height:1.75}.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin:24px 0}.cards>div{border:1px solid var(--line);border-radius:8px;padding:18px;background:#fbfdfd}.cards h3{margin:8px 0 10px}.cards p{font-size:15px;color:var(--muted)}.kicker{font-size:12px;text-transform:uppercase;color:var(--teal);font-weight:650;letter-spacing:.08em}.note,.important{padding:17px 20px;border-radius:6px;margin:24px 0;font-size:15px}.note{background:#edf7f4;border-left:4px solid var(--teal)}.important{background:#fff6e4;border-left:4px solid #c68b19;color:#67450f}.note p,.important p{margin-bottom:0}.note ul{margin-bottom:0}.result{border:1px solid #b7dcd1;background:#f4faf7;padding:14px 18px;border-radius:6px}.flow{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:26px 0}.flow>div{padding:14px;border:1px solid #b8d9d4;border-radius:6px;background:#f8fcfb}.flow b{color:var(--teal);font-size:12px;letter-spacing:.1em}.flow strong{display:block;margin:6px 0}.flow span{display:block;font-size:13px;color:var(--muted)}.steps{counter-reset:step;list-style:none;padding:0;margin:24px 0}.steps>li{counter-increment:step;position:relative;padding:2px 0 13px 42px;margin:0 0 10px}.steps>li:before{content:counter(step);position:absolute;left:0;top:2px;display:grid;place-items:center;width:27px;height:27px;border-radius:50%;background:var(--teal);color:#fff;font-size:13px;font-weight:700}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:7px;margin:20px 0}table{border-collapse:collapse;width:100%;font-size:14px;line-height:1.65}th{background:#eef6f4;color:#27554f;font-weight:650;text-align:left;padding:12px 14px;white-space:nowrap}td{padding:12px 14px;border-top:1px solid var(--line);vertical-align:top;min-width:80px}td:first-child{min-width:150px;color:#244d51}code{font:13px/1.5 Consolas,monospace;background:#edf2f4;border-radius:4px;padding:2px 5px;overflow-wrap:anywhere}pre{padding:18px;background:#173b42;color:#eaf7f4;border-radius:7px;overflow:auto;font:15px/1.8 Consolas,monospace}.example{padding:20px;background:#f6fafb;border:1px solid var(--line);border-radius:8px}.example h3{margin-top:0}.stage-strip{display:flex;flex-wrap:wrap;gap:8px;margin:22px 0}.stage-strip span{padding:8px 11px;border:1px solid #afd2cd;border-radius:5px;font-size:12px;background:#f2faf7}figure{margin:27px 0;background:#f8fafb;border:1px solid var(--line);padding:12px;border-radius:8px}.screen{display:block;position:relative;width:100%;background:#fff;border:0;padding:0;text-align:left;cursor:zoom-in}.screen img{display:block;width:100%;height:auto;max-width:100%;border:1px solid #e4ecee;border-radius:3px}.pin{position:absolute;display:grid;place-items:center;min-width:25px;height:25px;padding:0 6px;background:#a43333;color:#fff;border:2px solid #fff;border-radius:50%;font-size:12px;font-weight:750;transform:translate(-7px,-7px);box-shadow:0 1px 5px #0004}figcaption{font-size:13px;color:#455f6b;padding:10px 3px 3px;line-height:1.6}figcaption>span{color:#6e7e85}.legend{list-style:none;padding:8px 3px 0;display:flex;flex-wrap:wrap;gap:7px 20px;margin:0;font-size:12px}.legend li{margin:0}.legend b{display:inline-grid;place-items:center;width:20px;height:20px;border-radius:50%;background:#a43333;color:#fff;margin-right:4px}.small{font-size:13px;color:var(--muted)}.checklist{padding:12px 20px;background:#f5faf8;border:1px solid #cee4dc;border-radius:8px}.checklist label{display:flex;gap:11px;margin:13px 0;font-size:15px;align-items:flex-start}.checklist input{accent-color:var(--teal);width:17px;height:17px;flex-shrink:0;margin-top:5px}footer{padding:30px 56px;color:var(--muted);font-size:12px;background:#fafcfc}.back{display:inline-block;margin-top:20px;font-size:13px}.mobile-toc{display:none}dialog{border:0;border-radius:10px;width:min(96vw,1700px);max-height:94vh;padding:14px;background:#fff;overflow:auto}dialog::backdrop{background:#0c252ee0}dialog header{display:flex;align-items:center;justify-content:space-between;gap:15px;margin-bottom:12px;font-size:13px}dialog img{display:block;max-width:100%;height:auto;margin:auto}dialog button{border:1px solid var(--line);background:#f4f8f9;border-radius:5px;padding:6px 13px}.skip{position:absolute;left:10px;top:-80px;background:#fff;padding:8px;z-index:10}.skip:focus{top:8px}
@media(max-width:1100px){.layout{grid-template-columns:220px minmax(0,1fr)}.cover{padding:36px}.content{padding:0 30px}.toc{padding-left:12px}footer{padding:26px 30px}}
@media(max-width:760px){.layout{display:block}.toc{position:static;max-height:none;background:#fff;border-bottom:1px solid var(--line);padding:18px}.toc nav{columns:2;column-gap:12px}.toc a{break-inside:avoid}.toc .small{display:none}.cover{padding:30px 22px}.content{padding:0 20px}.top{padding:14px 16px}.brand{font-size:13px}.brand em{display:none}.top .button{padding:7px 10px;font-size:12px}.cards{grid-template-columns:1fr}.flow{grid-template-columns:repeat(2,minmax(0,1fr))}h2{font-size:23px}body{font-size:15px}section.chapter{padding-top:28px}figure{padding:7px}.pin{min-width:19px;height:19px;font-size:10px;border-width:1px}footer{padding:22px}.toc a{font-size:12px;padding:5px}.table-wrap{max-width:100%}.stage-strip span{font-size:11px}}
@media print{@page{size:A4;margin:16mm 14mm}html{scroll-behavior:auto}body{background:#fff;font-size:10pt;line-height:1.5;-webkit-print-color-adjust:exact;print-color-adjust:exact}.top,.toc,.skip,.back,.cover .button,dialog{display:none!important}.layout{display:block;max-width:none}main{border:0}.cover{padding:0 0 12mm;background:#fff;break-after:page}.cover h1{font-size:34pt}.content{padding:0}section.chapter{padding:6mm 0;break-inside:auto}h2{font-size:20pt;break-after:avoid}h3{font-size:13pt;break-after:avoid}figure,.note,.important,.result,.flow,.cards,pre{break-inside:avoid}.table-wrap{overflow:visible}th,td{font-size:9pt;padding:6px 8px}tr{break-inside:avoid}a{color:inherit;text-decoration:none}figure .screen{cursor:default}figure img{max-height:170mm;width:auto;max-width:100%;margin:auto}.pin{display:none}.legend{font-size:9pt}.legend b{background:#555}.button{font-size:9pt}.screen{border:0}figcaption>span{display:none}footer{padding:6mm 0;background:#fff}.checklist input{appearance:none;border:1px solid #888;width:12px;height:12px}.tags{margin-top:10mm}}
'''

CSS+='''html{scroll-behavior:auto}.toc-toggle{display:none}dialog img{max-width:none;min-width:100%;width:auto}dialog header{position:sticky;top:0;left:0;background:#fff;z-index:2;padding:5px 0}dialog header strong{max-width:70%}@media(max-width:760px){.toc>h2{display:none}.toc-toggle{display:flex;align-items:center;justify-content:space-between;width:100%;padding:8px 11px;color:#006963;border:1px solid #b5d7d1;border-radius:6px;background:#f5faf8;font-weight:650;font-size:14px}.toc nav{display:none;margin-top:12px}.toc nav.is-open{display:block;columns:2}}@media print{.legend b{display:none}.legend li:before{content:"• "}}'''

toc=''.join(f'<a href="#{identity}">{index:02d} · {title}</a>' for index,(identity,title,_) in enumerate(sections,1))
chapters=''.join(f'<section class="chapter" id="{identity}"><h2><span class="num">Mục {index:02d}</span>{title}</h2>{body}<a class="back" href="#dau-trang">↑ Về đầu tài liệu</a></section>' for index,(identity,title,body) in enumerate(sections,1))
JS='''
const viewer=document.getElementById('viewer');
document.querySelectorAll('.screen').forEach(button=>button.addEventListener('click',()=>{const image=button.querySelector('img');document.getElementById('viewer-image').src=image.src;document.getElementById('viewer-image').alt=image.alt;document.getElementById('viewer-title').textContent=image.alt;viewer.showModal()}));
document.getElementById('close-viewer').addEventListener('click',()=>viewer.close());
viewer.addEventListener('click',e=>{if(e.target===viewer)viewer.close()});
document.getElementById('print').addEventListener('click',()=>window.print());
const nav=[...document.querySelectorAll('.toc a')];
if('IntersectionObserver' in window){const observer=new IntersectionObserver(entries=>{entries.forEach(entry=>{if(entry.isIntersecting){nav.forEach(a=>a.classList.toggle('active',a.getAttribute('href')==='#'+entry.target.id))}})},{rootMargin:'-8% 0px -70% 0px'});document.querySelectorAll('.chapter').forEach(el=>observer.observe(el))}
const toggle=document.getElementById('toc-toggle'),toc=document.getElementById('guide-toc');
toggle.addEventListener('click',()=>{const open=toggle.getAttribute('aria-expanded')!=='true';toggle.setAttribute('aria-expanded',String(open));toc.classList.toggle('is-open',open)});
toc.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>{if(matchMedia('(max-width:760px)').matches){toggle.setAttribute('aria-expanded','false');toc.classList.remove('is-open')}}));
'''

document=f'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Hướng dẫn sử dụng Airflow Automation Tool bằng tiếng Việt, có ảnh thao tác và ví dụ CSV."><title>Hướng dẫn sử dụng · Airflow Automation Tool</title><style>{CSS}</style></head><body id="dau-trang"><a class="skip" href="#noi-dung">Đi tới nội dung hướng dẫn</a><header class="top"><div class="brand"><em>A</em> Airflow Automation Tool</div><button class="button secondary" id="print" type="button">In / Lưu thành PDF</button></header><div class="layout"><aside class="toc" aria-label="Mục lục"><h2>Mục lục</h2><nav>{toc}</nav><p class="small">Ảnh được nhúng trong file.<br>Mở tài liệu không cần Internet.<br>Cập nhật:15/11/2026.</p></aside><main id="noi-dung"><div class="cover"><div class="eyebrow">Tài liệu dành cho người sử dụng</div><h1>Hướng dẫn sử dụng<span>Airflow Automation Tool</span></h1><p class="lead">Từ khai báo kết nối đến theo dõi dữ liệu sau mỗi lần chạy.</p><p>Làm theo từng bước, đối chiếu tên nút trên ảnh và kiểm tra kết quả trước khi đi tiếp. Có ví dụ CSV đơn giản để bạn dễ bắt đầu.</p><div class="tags"><span>Tiếng Việt dễ hiểu</span><span>Ảnh từ giao diện thực tế</span><span>File HTML độc lập</span><span>15/11/2026</span></div></div><div class="content">{chapters}</div><footer><b>Airflow Automation Tool · Hướng dẫn sử dụng</b><p>Nội dung đối chiếu với giao diện và tài liệu vận hành hiện tại. Ảnh chụp dữ liệu demo; ID, thời gian và số liệu trên môi trường của bạn có thể khác. Các bước có xác nhận phải được thực hiện trên đúng môi trường và đúng phạm vi bạn được giao.</p><p>Để in hoặc lưu PDF, dùng nút ở đầu trang; chọn khổ A4 và bật in nền nếu muốn giữ màu. Ảnh có thể bấm phóng to khi đọc trên trình duyệt.</p></footer></main></div><dialog id="viewer" aria-labelledby="viewer-title"><header><strong id="viewer-title"></strong><button id="close-viewer" type="button">Đóng ảnh ✕</button></header><img id="viewer-image" alt=""></dialog><script>{JS}</script></body></html>'''
document=document.replace('<h2>Mục lục</h2><nav>', '<h2>Mục lục</h2><button class="toc-toggle" id="toc-toggle" aria-expanded="false" aria-controls="guide-toc" type="button">Mở mục lục <span aria-hidden="true">⌄</span></button><nav id="guide-toc">')
document=document.replace('<strong id="viewer-title"></strong>', '<strong id="viewer-title"></strong>')
OUTPUT.parent.mkdir(parents=True,exist_ok=True)
OUTPUT.write_text(document,encoding='utf-8')
summary={'output':str(OUTPUT.relative_to(ROOT)),'sections':len(sections),'images':used,'bytes':OUTPUT.stat().st_size,'self_contained':True}
(ASSETS/'build.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
