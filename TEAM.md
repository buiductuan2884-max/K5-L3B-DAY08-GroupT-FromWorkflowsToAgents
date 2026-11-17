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
| | | | |

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
- Coi `order_id` toàn khoảng trắng là thiếu mã đơn: trả `needs_info` thay vì `escalated`, thống nhất với shape workflow và single.
- Thêm 26 test (đã tính các case tham số hóa): không lộ secret hoặc PII, handoff chỉ có field allowlist, ticket nói dối vẫn bị `denied` trên 5 seed, T14 ghi 120.000, crash rồi resume, `order_id` trống.

### Bằng chứng

- Commit: ada63e5
- `python -m pytest -q -m student -o addopts= -k orchestrator`: 62 passed.
- `python -m pytest -q tests/test_orchestrator_group.py`: 26 passed.
- `python -m pytest -q`: 107 passed.
- Chi tiết: `report/team/2A20260388_LeQuanBao.md`.
