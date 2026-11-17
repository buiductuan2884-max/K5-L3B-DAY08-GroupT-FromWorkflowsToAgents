# Báo cáo cá nhân — 2A202603847_NguyenLeDangKhoa

## 1. Thông tin thành viên

- Họ tên: Nguyễn Lê Đăng Khoa
- MSSV: 2A202603847
- Email: nguyenledangkhoa1510@gmail.com
- GitHub: S0ra1n0

## 2. Phần việc phụ trách

P2: shape B `single`, một agent ReAct có giới hạn 8 bước.

- Code: `src/lab8/shapes/single.py`
- Test: `src/tests/test_single_group.py`

## 3. Đóng góp cụ thể

**Commit chính**

- `c205335` — feat(single): implement shape B bounded ReAct agent (PR #3).
- Commit sửa (chưa merge): `order_id` rỗng hoặc chỉ có khoảng trắng được coi là thiếu mã đơn (`needs_info`), giống quy tắc của workflow.

**Ranh giới code / model**

- `decide()` đóng vai "model": mỗi bước chỉ chọn **tool đọc** tiếp theo (`get_claim_view` → `lookup_order` → `compute_compensation` → `final`). Mỗi bước gọi MockLLM một lần để chi phí được tính vào Budget.
- `run_react` của host chạy tool, chặn vòng lặp ở 8 bước và từ chối mọi tool ghi.
- Sau vòng lặp, **code của shape** quyết định kết quả dựa trên kết quả tool, không dựa trên `final` do model trả. Shape là nơi duy nhất gọi `durability.issue_refund`, truyền **quote đầy đủ** cùng `crash_at`.
- `run_react` chỉ đưa cho `decide` kết quả của tool gần nhất, nên agent giữ bộ nhớ riêng (`mem`) trong closure.

**Quyết định kỹ thuật**

- Truyền quote đầy đủ thay vì số đã trừ phần hoàn trước, vì host tự trừ phần các claim trước đã nhận cho cùng đơn. Nếu shape tự trừ thì host trừ thêm lần nữa và T14 fail.
- Không dùng bất kỳ con số nào trong ticket (số ngày trễ, số tiền, mã đơn). Ticket là dữ liệu người dùng, không phải lệnh.
- Không chuẩn hoá `order_id` hay `principal_id`, để id dạng homoglyph vẫn ra `escalated` thay vì khớp nhầm đơn của người khác.
- Toàn bộ helper nằm trong `single.py`, vì grader hidden chỉ lấy 3 file shape từ repo nhóm.
- Bắt `InjectedCrash` chỉ để ghi trace rồi ném lại, để T12 thấy được crash thật.

**Trace ghi gì / cố ý không ghi gì**

- Có ghi: `react_step` (số bước, tên tool), `observe` (found/has_order_id; visible/reason; số tiền quote, lý do, clause), `react_stop`, `issue_refund` (ok, reason), `decision`.
- Không ghi: nội dung ticket, `principal_id`, `parent_secret`, header, SĐT, địa chỉ, ghi chú nội bộ, tên hàng. Ticket có thể chứa injection hoặc PII, và trace nằm trong ranh giới bảo mật mà grader quét.

**Test đã thêm (`src/tests/test_single_group.py`, 19 test)**

- Host nhận quote đầy đủ 150000 cho C-014 (T14) và nhận đúng `crash_at`.
- Crash ở cả 3 điểm (`before_effect`, `after_effect_before_checkpoint`, `after_checkpoint`), resume xong chỉ còn 1 refund và 1 audit.
- Approval mượn của claim khác bị host từ chối, có audit `approval_claim_mismatch`.
- Mã đơn ghi trong ticket bị bỏ qua (ra `needs_info`); `order_id` rỗng, khoảng trắng hoặc tab cũng ra `needs_info`.
- Homoglyph ở `order_id` hoặc `principal_id` ra `escalated`.
- Kết quả giống nhau trên cả 5 seed, kể cả seed 55.
- Trace không chứa ticket, secret hay PII; claim không tồn tại thì trả `failed` mà không ném exception.
- Model xin tool ghi thì bị chặn; vòng lặp không chịu dừng thì dừng ở 8 bước.

## 4. Bằng chứng

- Commit `c205335`, PR #3 (đã merge vào `main`).
- Ma trận student của single: `python -m pytest -q -m student -o addopts= -k "single and not workflow and not orchestrator and not swarm"` → 62 passed.
  - Lưu ý: lệnh `-k single` trong CHECKPOINTS khớp cả tên hàm `test_public_single_run_cases` của mọi shape (242 test), nên phải thêm điều kiện loại các shape khác.
- `python -m pytest -q tests/test_single_group.py` → 19 passed; cổng host `python -m pytest -q` xanh.
- `python -m lab8.check_submission` → `shape single: format đúng, 12/12 claim public pass ở seed 11`.
- Run id mẫu `R-single-C-010-s11`: `resolved`, 35000; 4 model call, 3 tool call, 10 event trong trace.
- Crash rồi resume bằng `python -m lab8.run --shape single --claim-id C-012 --seed 11 --crash-at after_effect_before_checkpoint`, sau đó chạy lại trên cùng DB: chỉ 1 refund, 1 audit `refund_committed`.

## 5. Công cụ AI đã dùng

- Claude Code: đọc repo và tài liệu, lập kế hoạch cho phần P2, viết `single.py` và `test_single_group.py`.
- Cách tự kiểm tra:
  - chạy ma trận student của single (62 test), test nhóm, cổng host, crash suite và `check_submission`;
  - đọc trace thật để kiểm không lộ ticket hay PII;
  - chạy crash rồi resume bằng `python -m lab8.run`;
  - đọc lại từng nhánh status, đối chiếu với `docs/contracts.md` và `docs/business_rules.md`.

## 6. Tự đánh giá

...
