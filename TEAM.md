# Team

## Thông tin nhóm

- Tên nhóm: GroupT
- Lớp: L3B
- Repo nhóm: `K5-L3B-DAY08-GroupT-FromWorkflowsToAgents` (xem [SUBMISSION.md](SUBMISSION.md))
- URL repo, nhánh nộp, commit chốt: https://github.com/buiductuan2884-max/K5-L3B-DAY08-GroupT-FromWorkflowsToAgents, `main`, `d606089`

## Thành viên

| STT | Họ tên | MSSV | Email | GitHub | Vai trò |
| --: | ------ | ---- | ----- | ------ | ------- |
|   1 | Bùi Đức Tuấn | 2A202603902 | buiductuan2884@gmail.com | buiductuan2884-max | Nhóm trưởng; P1 workflow + tích hợp |
|   2 | Nguyễn Lê Đăng Khoa |2A202603847|nguyenledangkhoa1510@gmail.com| S0ra1n0 | P2 single agent |
|   3 | Lê Quân Bảo | 2A202603888 | lebaosg@gmail.com | LeBao403 | P3 orchestrator + handoff |
|   4 |Mai Xuân Khang|2A202603722|maixkhang2004@gmail.com| KhangMai123 | P4 ledger, đánh giá, báo cáo |

Gợi ý chia vai:

- Nhóm 6 người: integration; workflow; single agent; orchestrator; ledger/policy/crash; eval/report.
- Nhóm 4 người: workflow + integration; single; orchestrator + handoff; ledger + evaluation.

## Bảng đóng góp

`python -m lab8.check_submission` đọc bảng này bằng máy: giữ nguyên tiêu đề `## Bảng đóng góp` và các cột. Mỗi người một dòng: commit có nội dung và ít nhất một test đã thêm hoặc sửa.

| Người | Vai | Commit | Test đã thêm hoặc sửa |
| --- | --- | --- | --- |
| Bùi Đức Tuấn | P1 — Workflow, tích hợp và bonus | `2ee7bb6`, `f8e9c77` (workflow); `5c338b9`, `16e2e22` (bonus B7); `5bfb01b` (bonus B6) | `src/tests/test_workflow_group.py`, `src/tests/test_bonus_grader_audit.py`, `src/tests/test_bonus_a2a.py` |
| Nguyễn Lê Đăng Khoa | P2 — Single ReAct | `c205335`, `b5a1513` | `src/tests/test_single_group.py` (19 test) |
| Lê Quân Bảo | P3 — Orchestrator và handoff | `ada63e5`, `34daeb2` | `src/tests/test_orchestrator_group.py` |
| Mai Xuân Khang | P4 — Ledger, safety, evaluation và báo cáo | `21768c5`, `d5a8733` | `src/tests/test_trace_safety_group.py` — 42 test độc lập và 92 test tích hợp |

## Cá nhân

Mỗi thành viên đồng thời tạo một báo cáo riêng trong `report/` theo dạng:

```text
report/team/MSSV_HoTen.md
```

Ví dụ: `report/team/20241234_NguyenVanAn.md`.

Sao chép mục dưới đây cho từng thành viên.

## MSSV_HoTen

### Phần việc phụ trách

-

### Đóng góp cụ thể

-

### Bằng chứng

-

## 2A202603902_BuiDucTuan

### Phần việc phụ trách

- Nhóm trưởng: chia việc, merge nhánh, điền `TEAM.md` và `report/team/decision_adr.md`.
- Shape A (workflow): `src/lab8/shapes/workflow.py`, test `src/tests/test_workflow_group.py`.
- Bonus B7 (kiểm toán grader) và bản thử B6 (investigator A2A) trong `src/bonus/`.
- Báo cáo cá nhân: `report/team/2A202603902_BuiDucTuan.md`.

### Đóng góp cụ thể

- Workflow: các bước cố định, tiền do `compute_compensation` tính, truyền quote đầy đủ và `crash_at` vào `durability.issue_refund`; trace không ghi ticket hay order row.
- Phát hiện và sửa trường hợp `order_id` toàn khoảng trắng trả `escalated` thay vì `needs_info`.
- B7: ba quan hệ đề cho, một quan hệ mới (thứ tự trial không được làm đổi kết quả) và bốn kiểm tra phụ; chỉ ra grader_a đếm cost hai lần, grader_c tính trial hạ tầng là fail, `pass_5` của `lab8.metrics` sai khi một cặp (claim, seed) lặp lại.

### Bằng chứng

- Commit: `2ee7bb6`, `f8e9c77` (workflow); `5c338b9`, `16e2e22` (B7); `5bfb01b` (B6).
- `python -m pytest -q -m student -o addopts= -k workflow`: 62 passed.
- Chi tiết: `report/team/2A202603902_BuiDucTuan.md`, `report/team/bonus_report.md`.

## 2A202603888_LeQuanBao

### Phần việc phụ trách

- Shape C (orchestrator) và handoff: file `src/lab8/shapes/orchestrator.py`.
- Test riêng của shape: `src/tests/test_orchestrator_group.py`.
- Báo cáo cá nhân: `report/team/2A202603888_LeQuanBao.md`.

### Đóng góp cụ thể

- Cài orchestrator theo luồng: đọc claim, kiểm `order_id`, dựng handoff, chạy investigator chỉ có tool đọc, lấy quote từ `compute_compensation`, rồi gọi `durability.issue_refund` với quote đầy đủ.
- Handoff dùng `make_handoff` (allowlist, tool chỉ đọc). Trace chỉ ghi handoff đã sanitize và vài field chọn lọc, không ghi ticket, claim row, order row hay secret.
- Truyền `crash_at` xuống host và không nuốt `InjectedCrash`, nên crash rồi resume vẫn còn một refund và một audit `refund_committed`.
- Coi `order_id` toàn khoảng trắng là thiếu mã đơn: trả `needs_info` thay vì `escalated`, thống nhất với shape workflow và single.
- Thêm 26 test (đã tính các case tham số hóa): không lộ secret hoặc PII, handoff chỉ có field allowlist, ticket nói dối vẫn bị `denied` trên 5 seed, T14 ghi 120.000, crash rồi resume, `order_id` trống.

### Bằng chứng

- Commit: `ada63e5` (cài shape C và test), `34daeb2` (xử lý `order_id` toàn khoảng trắng).
- `python -m pytest -q -m student -o addopts= -k orchestrator`: 62 passed.
- `python -m pytest -q tests/test_orchestrator_group.py`: 26 passed.
- `python -m pytest -q`: 107 passed.
- Chi tiết: `report/team/2A202603888_LeQuanBao.md`.

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
- Tự kiểm hidden `python -m lab8.benchmark --shapes single --cases student_drop/hidden_claims.jsonl --world student_drop/hidden_world_state.json`: 200 trial, 0 error, 0 `leak_suspect`, status trùng workflow và orchestrator ở mọi cặp (claim, seed).
- Chi tiết: `report/team/2A202603847_NguyenLeDangKhoa.md`.

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
