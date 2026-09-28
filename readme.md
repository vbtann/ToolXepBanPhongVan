# Hệ thống xếp bàn phỏng vấn

Ứng dụng Streamlit sử dụng Google OR-Tools CP-SAT để tự động xếp ứng viên vào bàn phỏng vấn theo:

- Khung giờ ứng viên đăng ký.
- Vai trò/nguyện vọng cần được đánh giá.
- Kỹ năng của interviewer.
- Số lượng bàn và interviewer khả dụng.

Hệ thống bắt buộc phải xếp lịch cho **toàn bộ ứng viên**. Nếu dữ liệu và tài nguyên không đủ, hệ thống báo lỗi infeasible thay vì trả về lịch một phần.

## 1. Cài đặt

Yêu cầu Python 3.10 trở lên.

Mở PowerShell tại thư mục dự án và chạy:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Nếu PowerShell chặn kích hoạt môi trường ảo, có thể chạy trực tiếp bằng Python hệ thống sau khi cài dependencies.

## 2. Chạy ứng dụng

```powershell
streamlit run app.py
```

Sau đó mở URL Streamlit hiển thị trong terminal, thường là:

```text
http://localhost:8501
```

## 3. File input

Sidebar của ứng dụng nhận hai file `.csv` hoặc `.xlsx`:

1. File ứng viên.
2. File interviewer.

Có thể tải file mẫu bằng nút **Download Template Excel File** trong ứng dụng.

### 3.1. File ứng viên

Các cột bắt buộc:

| Cột                             | Ý nghĩa                     | Ví dụ                                                   |
| ------------------------------- | --------------------------- | ------------------------------------------------------- |
| `id` hoặc `mssv`                | Mã sinh viên                | `24125071`                                              |
| `aspirations` hoặc `aspiration` | Danh sách nguyện vọng       | `['Event operator (Academy)', 'Designer (Multimedia)']` |
| `preferred_slots`               | Danh sách khung giờ đã chọn | `['13:00-14:00', '14:00-15:00']`                        |

Tên cột tiếng Việt tương đương cũng được hỗ trợ, ví dụ:

- `nguyện vọng` hoặc `nguyen vong`
- `khung thời gian ứng viên chọn`

Ứng viên không bắt buộc có cột họ tên. Khi thiếu họ tên, `id/mssv` được dùng làm tên hiển thị.

Ví dụ CSV:

```csv
id,aspirations,preferred_slots
24125071,"['Event operator (Academy)','Event operator (Volunteers)','Designer (Multimedia)']","['13:00-14:00','14:00-15:00','15:00-16:00','16:00-17:00']"
```

### 3.2. File interviewer

Các cột bắt buộc:

| Cột                     | Ý nghĩa                            | Ví dụ                                |
| ----------------------- | ---------------------------------- | ------------------------------------ |
| `id` hoặc `mssv`        | Mã interviewer                     | `24125033`                           |
| `name` hoặc `họ và tên` | Họ tên interviewer                 | `Nguyễn Văn A`                       |
| `roles`                 | Danh sách vai trò có thể phỏng vấn | `['Event Operator (Academy)', 'MC']` |

Có thể dùng các tên cột tiếng Việt tương đương như `vai trò` hoặc `các vai trò có thể phỏng vấn`.

Ví dụ CSV:

```csv
id,name,roles
24125033,Nguyễn Văn A,"['Event Operator (Academy)','Technician (Technician)']"
```

## 4. Định dạng danh sách trong CSV/XLSX

Các cột danh sách nên được ghi dưới dạng chuỗi list Python:

```text
['Role 1', 'Role 2', 'Role 3']
```

Ứng dụng cũng chấp nhận chuỗi phân tách bằng dấu phẩy:

```text
Role 1, Role 2, Role 3
```

Trong file CSV, cần đặt toàn bộ list trong dấu ngoặc kép để dấu phẩy bên trong list không làm tách cột.

## 5. Chuẩn hóa vai trò

Vai trò được so khớp không phân biệt chữ hoa/chữ thường. Ví dụ các giá trị sau được xem là tương đương:

- `Event operator (Academy)` và `Event Operator (Academy)`
- `Event operator (Sports)` và `Event Operator (Sport)`
- `Event operator (Volunteers)` và `Event Operator (Voluteers)`
- `Event operator (Entertainment and Arts)` và `Event Operator (Entertaiment & Arts)`

Các role rỗng trong list interviewer sẽ được bỏ qua.

Nên dùng format chuẩn:

```text
Role (Department)
```

Ví dụ:

```text
Event operator (Entertainment & Arts)
Photographer (Multimedia)
Content writer (Multimedia)
Designer (Multimedia)
Editor (Multimedia)
MC
```

## 6. Khung giờ

Khung giờ được chuẩn hóa tự động, nên các giá trị sau tương đương:

```text
8:00-9:00
08:00-09:00
08:00 - 09:00
```

Mặc định hệ thống tạo các slot một giờ từ `08:00` đến `17:00` và nghỉ trưa `12:00-13:00`.

Các thiết lập có thể thay đổi trong **Advanced Settings**:

- Số lượng bàn.
- Giờ bắt đầu.
- Giờ kết thúc.
- Thời gian nghỉ.

Nếu ứng viên chọn slot nằm ngoài thời gian cấu hình, hệ thống sẽ báo lỗi.

## 7. Quy tắc xếp lịch

Mô hình CP-SAT áp dụng các ràng buộc sau:

- Mỗi ứng viên được xếp đúng một lần.
- Ứng viên chỉ được xếp trong các slot đã chọn.
- Một bàn tại một slot chỉ có tối đa một ứng viên.
- Một slot có thể dùng nhiều bàn đồng thời.
- Bàn có ứng viên phải có từ 1 đến 4 interviewer.
- Bàn không có ứng viên không có interviewer.
- Một interviewer không thể ngồi ở hai bàn trong cùng một slot.
- Một interviewer có thể cover nhiều aspiration của cùng một ứng viên nếu họ có các role tương ứng.
- Các aspiration trùng nhau chỉ được tính một lần khi kiểm tra skill coverage, nhưng vẫn được hiển thị đầy đủ trong output.
- Tất cả role khác nhau của ứng viên phải được cover bởi interviewer tại bàn đó.

Mục tiêu tối ưu là:

1. Bắt buộc xếp toàn bộ ứng viên.
2. Trong các lịch hợp lệ, giảm số interviewer được sử dụng.

## 8. Kết quả

Sau khi bấm **Run Optimization**, ứng dụng hiển thị:

- Số ứng viên đã được xếp trên tổng số ứng viên.
- **Flat Table View**: mỗi dòng là một ứng viên được xếp vào một bàn và một slot.
- **Matrix View**: hàng là bàn, cột là slot.
- Nút tải xuống CSV cho cả hai dạng kết quả.

Các cột của Flat Table View gồm:

```text
Slot
Table
Candidate
Candidate_Aspirations
Interviewer_1
Interviewer_2
Interviewer_3
Interviewer_4
```

## 9. Lỗi thường gặp

### Không thể xếp toàn bộ ứng viên

Nguyên nhân thường gặp:

- Thiếu interviewer cho một role.
- Role ứng viên và interviewer bị viết sai khác nhau.
- Có quá ít khung giờ hoặc bàn.
- Khung giờ ứng viên chọn nằm ngoài Advanced Settings.
- Một interviewer bị yêu cầu ở quá nhiều bàn trong cùng slot.

Cách xử lý:

- Kiểm tra chính tả role.
- Dùng format `Role (Department)` nhất quán.
- Tăng số bàn.
- Mở rộng khung giờ.
- Bổ sung interviewer có role còn thiếu.

### Thiếu cột bắt buộc

Kiểm tra đúng tên cột hoặc dùng nút tải template. App hỗ trợ cả tên tiếng Anh và một số tên tiếng Việt tương đương.

### Lỗi đọc danh sách

Đảm bảo list trong CSV được đặt trong dấu ngoặc kép:

```csv
"['MC','Designer (Multimedia)']"
```

## 10. Chạy bộ giải trực tiếp bằng Python

Có thể gọi core scheduler mà không chạy Streamlit:

```python
import pandas as pd
from app import normalize_input_columns, parse_list_cell
from interview_scheduler import run_scheduler

candidates = pd.read_csv("candidate.csv")
interviewers = pd.read_csv("interviewer.csv")

candidates = normalize_input_columns(candidates, "candidates")
interviewers = normalize_input_columns(interviewers, "interviewers")

for column in ["aspirations", "preferred_slots"]:
    candidates[column] = candidates[column].apply(parse_list_cell)
interviewers["roles"] = interviewers["roles"].apply(parse_list_cell)

df_flat, df_matrix = run_scheduler(candidates, interviewers)
print(f"Scheduled: {len(df_flat)}/{len(candidates)}")
```

Core scheduling logic nằm trong [interview_scheduler.py](interview_scheduler.py), còn giao diện web nằm trong [app.py](app.py).
