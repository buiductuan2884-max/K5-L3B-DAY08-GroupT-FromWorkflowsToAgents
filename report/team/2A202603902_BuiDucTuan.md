# Báo cáo Day 08

Bùi Đức Tuấn · 2A202603902 · L3B · GroupT

## 1. Thông tin thành viên

- Họ tên: Bùi Đức Tuấn
- MSSV: 2A202603902
- Email: buiductuan2884@gmail.com
- GitHub: buiductuan2884-max

## 2. Phần việc phụ trách

P1: nhóm trưởng, shape A `workflow` và bonus.

- **Điều phối:** tạo repo nhóm, mời thành viên, chia việc, review và merge các nhánh, điền `TEAM.md` và `report/team/decision_adr.md`.
- **Code:** `src/lab8/shapes/workflow.py`, test `src/tests/test_workflow_group.py`.
- **Bonus:** B7 kiểm toán grader (`src/bonus/grader_audit.py`, `src/tests/test_bonus_grader_audit.py`, `report/team/bonus_report.md`) và bản thử B6 investigator A2A (`src/bonus/a2a_*.py`, `src/tests/test_bonus_a2a.py`).

## 3. Đóng góp cụ thể

**Commit chính**

- `2ee7bb6`: shape workflow và test ticket nói dối (PR #1).
- `f8e9c77`: `order_id` toàn khoảng trắng ra `needs_info`; điền vai trong `TEAM.md` (PR #2).
- `5c338b9`, `16e2e22`: bonus B7 và báo cáo bonus.
- `5bfb01b`: bản thử bonus B6.
- `161f109`: hoàn thiện `TEAM.md`; đây là commit ghi trong ADR.

**Cách chia việc**

- Tôi chia theo file thay vì chia mỗi checkpoint cho 4 người. Lý do: việc của CP3 (truyền `crash_at`) nằm ngay trong hàm của CP2, nên nếu tách người sẽ phải chờ nhau và sửa chung một file. Crash suite chạy trên swarm có sẵn, nên P4 có việc ngay từ đầu.
- Mỗi checkpoint vẫn có một mốc tổng hợp: shape nào đạt 62/62 test thì merge ngay, không dồn đến cuối buổi.

**Workflow**

- Các bước cố định: đọc claim view → kiểm `order_id` → tra đơn theo principal → `compute_compensation` → `durability.issue_refund` với quote đầy đủ và `crash_at`. Không gọi model lần nào.
- Trace chỉ ghi status, số tiền, reason và clause_ids. Không ghi ticket, claim row hay order row.
- Khi crash: ghi trace rồi ném lỗi tiếp, không nuốt `InjectedCrash`.

**Quyết định kỹ thuật**

- **`order_id` toàn khoảng trắng.** Khi soát workflow với 20 tình huống kiểu hidden, tôi thấy `"   "` ra `escalated` vì code chỉ coi null hoặc chuỗi rỗng là thiếu. Tôi cân nhắc 3 cách:
  - A: giữ nguyên.
  - B: chỉ coi chuỗi toàn khoảng trắng là thiếu.
  - C: cắt khoảng trắng rồi mới tra đơn.

  Tôi chọn B. C làm shape và host hiểu mã đơn khác nhau, vì host tra đúng mã gốc: `" O-107 "` sẽ được shape tìm thấy nhưng host từ chối. P2 và P3 sửa theo cùng quy tắc.
- **Chọn workflow trong ADR.** Ba shape nhóm viết đều đạt pass rate 1.000 trên bộ public. Workflow có cost/success thấp nhất (27.86 VND, so với 32.99 của single và 56.72 của orchestrator) và không gọi model, nên là shape ít tự chủ nhất mà vẫn đủ tốt.
- **Bonus B7.** Tôi chọn B7 vì không phụ thuộc shape của nhóm và có thể bắt đầu ngay. Quan hệ mới của nhóm là: đảo thứ tự trial thì mọi số phải giữ nguyên.
- **Bonus B6.** Ở mức lỗi 30%, tôi cho orchestrator nhận cả trả lời đến muộn rồi đo lại, nhưng kết quả không đổi. Đọc trace thì thấy cả 6 trial fail đều do mất tin ở cả 3 lần gửi. Tôi giữ 3 lần gửi lại thay vì tăng lên để đẩy pass rate.

## 4. Bằng chứng

| Lệnh (trong `src/`) | Kết quả |
| --- | --- |
| `python -m pytest -q -m student -o addopts= -k workflow` | 62 passed |
| `python -m pytest -q` (sau khi gộp mọi nhánh) | 200 passed |
| `python -m pytest -q -m student -o addopts=` | 340 passed |
| `python -m pytest -q tests/test_bonus_grader_audit.py` | 40 passed |
| `python -m pytest -q tests/test_bonus_a2a.py` | 11 passed |
| `python -m lab8.crash_test --count 20 --out reports/crash.json` | `crash_safety 20/20` |

- **Benchmark:** chạy lại trên commit `161f109` ra `reports/benchmark.json` giống hệt file P4 đã nộp. Workflow 70/70, ví dụ `R-workflow-C-002-s55` ra `denied` đúng, trong khi `R-swarm-C-002-s55` ra `resolved`.
- **Soát kiểu hidden:** 20 tình huống, gồm ticket lừa, chữ Cyrillic giả chữ O, đơn của khách khác, approval mượn, hết hạn, bị thu hồi, đơn hủy, hỏng hàng và 3 điểm crash. Kết quả 20/20 sau khi sửa `order_id` toàn khoảng trắng; không lần nào trace lộ SĐT, địa chỉ hay secret.
- **B7** (`reports/bonus_grader_audit.json`):
  - grader_a cộng thêm cost của trial đầu tiên mỗi claim (tổng 473 thay vì 567 khi nhân đôi; 285 thay vì 283.5 khi đảo thứ tự).
  - grader_c tính trial hạ tầng là fail (pass rate 0.5625 thay vì 0.75).
  - `pass_5` của `lab8.metrics` ra 0 khi một cặp (claim, seed) lặp lại.
- **B6** (`reports/bonus_a2a.json`): lỗi 0% và 10% pass 1.000; lỗi 30% pass 0.914, 6 trial `failed` vì investigator không trả lời, 0 lần lộ secret, 0 lần hoàn tiền sai approval.

## 5. Công cụ AI đã dùng

- **Claude Code (Opus) trong Claude desktop app:**
  - Đọc đề và tóm tắt luật, chia việc, viết code workflow và bonus, soạn nháp ADR, báo cáo bonus và báo cáo này.
  - Một agent khác của Claude viết phần lớn code B6 theo brief tôi duyệt. Một agent reviewer soát B7 và chỉ ra 7 điểm cần sửa.
- **Cách tôi kiểm tra:**
  - Mỗi thay đổi đều chạy lại cổng host và test student của shape trước khi merge.
  - Tôi chạy lại kết quả của agent trên máy mình rồi mới dùng. Ví dụ: agent B6 nói các trial fail là do bỏ trả lời đến muộn; tôi cho đo lại và đọc trace thì thấy nguyên nhân thật là mất tin.
  - Số liệu trong ADR và báo cáo đọc từ JSON do `lab8.benchmark`, `lab8.crash_test` và `bonus.grader_audit` sinh ra, không chép tay.
- **Quyết định do tôi chốt:** cách chia việc, cách xử lý `order_id` toàn khoảng trắng, chọn workflow, chọn B7 và giữ 3 lần gửi lại ở B6. AI đưa phương án và số liệu.

## 6. Tự đánh giá

**Làm được**

- Workflow qua 62/62 test student và 20/20 tình huống kiểu hidden. Chi phí thấp nhất trong 4 shape.
- Cả nhóm làm song song gần như không phải chờ nhau, vì mỗi người giữ file riêng. Lần xung đột duy nhất là P3 và P4 cùng sửa một dòng trong `orchestrator.py` với cùng nội dung; tôi giữ bản của P3 vì P3 là chủ file.
- B7 tìm ra lỗi ở cả 3 bản grader và một lỗi trong chính thước đo gốc.

**Hạn chế và điều chưa kiểm chứng**

- Chưa chạy được bộ hidden (`student_drop/`), nên chưa biết workflow có đạt 0.75 và 0.80 hay không.
- `check_submission` chỉ nhận tiêu đề bonus từ B1 đến B6, trong khi đề có B7, nên báo cáo B7 bị báo FAIL. Điểm này cần coach xác nhận.
- Phần lớn code B6 do AI viết; tôi kiểm bằng test và số liệu, chưa tự đọc hết từng dòng.

**Bài học**

- Với một việc có luật rõ ràng, shape ít tự chủ nhất thường đủ dùng và rẻ hơn. Multi-agent chỉ đáng khi có việc mà bước cố định không làm được.
- Thước đo cũng cần được kiểm. Cùng một danh sách trial, ba bản grader cho pass rate khác nhau tới 0.19, lớn hơn khoảng cách giữa workflow và swarm.
