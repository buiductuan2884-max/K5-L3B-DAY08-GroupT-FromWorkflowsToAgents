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
| Mai Xuân Khang | P4 — Ledger, safety, evaluation và báo cáo | `21768c5`, `d5a8733` | `src/tests/test_trace_safety_group.py` — 42 test độc lập và 92 test tích hợp |

## Cá nhân

Mỗi thành viên đồng thời tạo một báo cáo riêng trong `report/` theo dạng:

```text
report/team/MSSV_HoTen.md
```

Ví dụ: `report/team/20241234_NguyenVanAn.md`.

Sao chép mục dưới đây cho từng thành viên.

## 2A202603722_MaiXuanKhang

### Phần việc phụ trách

- P4 — Ledger, safety testing, evaluation và báo cáo.
- Kiểm thử idempotency, retry/crash, approval, trace/privacy và handoff.
- Chạy benchmark bốn kiến trúc, crash suite và hoàn thiện research card, phần P4 trong báo cáo nhóm, báo cáo cá nhân.

### Đóng góp cụ thể

- Thêm `src/tests/test_trace_safety_group.py` với 134 case: 42 test độc lập và 92 test tích hợp. Dùng SQLite thật, `tmp_path`; không thay logic refund/approval bằng mock.
- Kiểm đúng một refund và audit, retry không ghi trùng, amount conflict giữ tiền cũ, ba cửa sổ crash/resume, approval thiếu/hết hạn/thu hồi/sai claim, trần theo order và T13/T14.
- Kiểm trace đúng contract, phát hiện missing/stale/invalid/mismatch, quét sibling `<run_id>*`, secret/PII và stdout/stderr; đối chiếu handoff với allowlist của host.
- Bổ sung test hồi quy và sửa xử lý order ID toàn khoảng trắng để trả `needs_info`; giữ nguyên mã đơn có padding hoặc ký tự giống nhau khi lookup.
- Sinh `src/reports/benchmark.json` và `src/reports/crash.json` bằng lệnh lab; lập research card R2 và báo cáo dựa trên số liệu thực tế, không sửa JSON thủ công hoặc thước đo.

### Bằng chứng

- Commit kỹ thuật: `21768c5`; commit báo cáo và bằng chứng: `d5a8733`.
- `python -m pytest -q tests/test_trace_safety_group.py -o addopts=`: 134 passed.
- `python -m pytest -q`: 139 passed; `python -m pytest -q -m student -o addopts=`: 340 passed trên revision đánh giá `21768c5`.
- `src/reports/crash.json`: `crash_safety = 20/20`. Kiểm thử P4 bổ sung crash/resume riêng cho ba shape nhóm.
- `src/reports/benchmark.json`: 4 shape × 14 public claim × seeds `11,22,33,44,55` = 280 trial; mỗi trial dùng SQLite mới. Run ID đối chiếu: `R-workflow-C-001-s11`, `R-swarm-C-002-s55`.
- Chi tiết đóng góp và giới hạn: [báo cáo cá nhân P4](report/team/2A202603722_MaiXuanKhang.md).
