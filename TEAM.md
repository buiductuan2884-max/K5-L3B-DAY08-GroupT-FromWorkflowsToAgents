# Team

## Thông tin nhóm

- Tên nhóm: GroupT
- Lớp: L3B
- Repo nhóm: `K5-L3B-DAY08-GroupT-FromWorkflowsToAgents` (xem [SUBMISSION.md](SUBMISSION.md))
- URL repo, nhánh nộp, commit chốt: https://github.com/buiductuan2884-max/K5-L3B-DAY08-GroupT-FromWorkflowsToAgents, `main`,

## Thành viên

| STT | Họ tên | MSSV | Email | GitHub | Vai trò |
| --: | ------ | ---- | ----- | ------ | ------- |
|   1 | Bùi Đức Tuấn |2A202603902|       | buiductuan2884-max | Nhóm trưởng; P1 workflow + tích hợp |
|   2 | Nguyễn Lê Đăng Khoa |2A202603847|nguyenledangkhoa1510@gmail.com| S0ra1n0 | P2 single agent |
|   3 | Lê Quân Bảo |2A202603888|       | LeBao403 | P3 orchestrator + handoff |
|   4 |Mai Xuân Khang|2A202603722|maixkhang2004@gmail.com| KhangMai123 | P4 ledger, đánh giá, báo cáo |

Gợi ý chia vai:

- Nhóm 6 người: integration; workflow; single agent; orchestrator; ledger/policy/crash; eval/report.
- Nhóm 4 người: workflow + integration; single; orchestrator + handoff; ledger + evaluation.

## Bảng đóng góp

`python -m lab8.check_submission` đọc bảng này bằng máy: giữ nguyên tiêu đề `## Bảng đóng góp` và các cột. Mỗi người một dòng: commit có nội dung và ít nhất một test đã thêm hoặc sửa.

| Người | Vai | Commit | Test đã thêm hoặc sửa |
| --- | --- | --- | --- |
| Nguyễn Lê Đăng Khoa | P2 single agent (ReAct) | c205335, b5a1513 | `src/tests/test_single_group.py` (19 test) |

## Cá nhân

Mỗi thành viên đồng thời tạo một báo cáo riêng trong `report/` theo dạng:

```text
report/team/MSSV_HoTen.md
```

Ví dụ: `report/team/20241234_NguyenVanAn.md`.

Sao chép mục dưới đây cho từng thành viên.

## 2A20260388_LeQuanBao

### Phần việc phụ trách

- Shape C (orchestrator) và handoff: file `src/lab8/shapes/orchestrator.py`.
- Test riêng của shape: `src/tests/test_orchestrator_group.py`.
- Báo cáo cá nhân: `report/team/2A20260388_LeQuanBao.md`.

### Đóng góp cụ thể

- Cài orchestrator theo luồng: đọc claim, kiểm `order_id`, dựng handoff, chạy investigator chỉ có tool đọc, lấy quote từ `compute_compensation`, rồi gọi `durability.issue_refund` với quote đầy đủ.
- Handoff dùng `make_handoff` (allowlist, tool chỉ đọc). Trace chỉ ghi handoff đã sanitize và vài field chọn lọc, không ghi ticket, claim row, order row hay secret.
- Truyền `crash_at` xuống host và không nuốt `InjectedCrash`, nên crash rồi resume vẫn còn một refund và một audit `refund_committed`.
- Thêm 16 test: không lộ secret hoặc PII, handoff chỉ có field allowlist, ticket nói dối vẫn bị `denied` trên 5 seed, T14 ghi 120.000, crash rồi resume.

### Bằng chứng

- Commit: ada63e5
- `python -m pytest -q -m student -o addopts= -k orchestrator`: 62 passed.
- `python -m pytest -q tests/test_orchestrator_group.py`: 16 passed.
- `python -m pytest -q`: 75 passed.
- Chi tiết: `report/team/2A20260388_LeQuanBao.md`.

## 2A202603847_NguyenLeDangKhoa

### Phần việc phụ trách

- Shape B (single agent ReAct, tối đa 8 bước): file `src/lab8/shapes/single.py`.
- Test riêng của shape: `src/tests/test_single_group.py`.
- Báo cáo cá nhân: `report/team/2A202603847_NguyenLeDangKhoa.md`.

### Đóng góp cụ thể

- Cài vòng ReAct qua `run_react`: `decide()` chỉ chọn tool đọc (`get_claim_view` → `lookup_order` → `compute_compensation`), mỗi bước một lần gọi MockLLM để chi phí được tính.
- Sau vòng lặp, code của shape quyết định kết quả dựa trên kết quả tool, không dựa trên câu trả lời của model. Shape là nơi duy nhất gọi `durability.issue_refund`, truyền quote đầy đủ và `crash_at`, không nuốt `InjectedCrash`.
- Không dùng số trong ticket; `order_id` rỗng hoặc chỉ khoảng trắng ra `needs_info`; không chuẩn hoá id nên homoglyph ra `escalated`. Trace không ghi ticket, principal, secret hay PII.
- Thêm 19 test: host nhận quote đầy đủ (T14), crash ở cả 3 điểm rồi resume, approval mượn của claim khác, injection, `order_id` trống, homoglyph, kết quả giống nhau trên 5 seed, trace sạch, model xin tool ghi bị chặn, dừng ở 8 bước.

### Bằng chứng

- Commit: c205335 (PR #3), b5a1513.
- `python -m pytest -q -m student -o addopts= -k "single and not workflow and not orchestrator and not swarm"`: 62 passed.
- `python -m pytest -q tests/test_single_group.py`: 19 passed.
- `python -m pytest -q`: 97 passed.
- `python -m lab8.check_submission`: `shape single: format đúng, 12/12 claim public pass ở seed 11`.
- Chi tiết: `report/team/2A202603847_NguyenLeDangKhoa.md`.
