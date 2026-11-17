# Báo cáo nhóm — Lab 8 LogiX-VN

Báo cáo ngắn gọn theo mẫu Lab 08; số liệu đọc trực tiếp từ JSON do công cụ sinh ngày 17/11/2026.

## 1. Thông tin nhóm

- Tên nhóm: **GroupT — L3B**.
- Thành viên theo [TEAM.md](../../TEAM.md): Bùi Đức Tuấn (P1), Nguyễn Lê Đăng Khoa (P2), Lê Quân Bảo (P3), Mai Xuân Khang (P4).
- Repository: [GroupT](https://github.com/buiductuan2884-max/K5-L3B-DAY08-GroupT-FromWorkflowsToAgents).
- Commit chốt: `d606089` (merge PR #5 vào `main`), ghi trong [TEAM.md](../../TEAM.md). Kết quả thực nghiệm được đo trên commit kỹ thuật `21768c53415405fe43f56a46adc8d34406e49faa`; chạy lại trên `161f109` (commit ghi trong [decision_adr.md](decision_adr.md)) cho cùng nội dung JSON.

## 2. Mục tiêu và cách tiếp cận

LogiX-VN xử lý yêu cầu hoàn phí vận chuyển/hỏng hàng từ ticket. Order và policy hiện hành là nguồn sự thật; ticket là dữ liệu không đáng tin. Tiền do code tính, host kiểm approval và ghi ledger. Nhóm so bốn kiến trúc trên cùng corpus để chọn mức tự chủ ít nhất đáp ứng yêu cầu.

P1 triển khai workflow và tích hợp hồ sơ; P2 triển khai single ReAct; P3 triển khai orchestrator/handoff; P4 kiểm ledger, policy, crash, trace/privacy, benchmark và báo cáo. Kiểm thử gồm cổng host, ma trận public, test an toàn độc lập và kiểm thử tích hợp ba shape.

## 3. Giải pháp

- **Workflow:** bước Python cố định: claim view → order theo principal → quote → host. Không gọi model. Trace ghi claim ID/có order, visibility, quote, kết quả host và quyết định; không ghi ticket.
- **Single ReAct:** `run_react(max_steps=8)`, một MockLLM call mỗi bước. Code chọn read tool theo observation, lưu kết quả rồi quyết quote/ghi tiền sau vòng lặp; không dùng model final để quyết số tiền. Trace chỉ ghi tóm tắt observation và bước ReAct.
- **Orchestrator:** đọc claim, dựng `make_handoff`, investigator đọc order/policy/refund history/quote; orchestrator chuyển quote đầy đủ cho host. Handoff theo `ALLOWED_FIELDS`/`FACT_KEYS`, tools theo `READONLY_TOOLS`; trace ghi handoff đã sanitize và tóm tắt investigator. Order ID toàn khoảng trắng được xử lý như thiếu thông tin trước khi handoff.
- **Swarm tham chiếu:** thêm peer/parse/draft và investigator; giữ nguyên weakness tin delay trong ticket ở seed chia hết cho 5. Đây là đối chứng, không phải mặc định kiến trúc tốt nhất.

Host dùng SQLite transaction cho effect và audit `refund_committed`, khóa `refund:{claim_id}`. Retry giữ một refund; amount khác gây conflict, không sửa tiền cũ. Approval phải đúng claim, còn hiệu lực và không bị thu hồi; effect bị cap bởi approved/paid và phần entitlement còn lại theo order. Shape luôn truyền quote đầy đủ: T14 proposal 150.000, lịch sử 30.000, effect 120.000. Checkpoint hỗ trợ resume, không thay ledger. Quy tắc: [contracts](../../docs/contracts.md), [business rules](../../docs/business_rules.md).

## 4. Kết quả

Nguồn: [benchmark.json](../../src/reports/benchmark.json). Mỗi shape 14 claim × seeds `11,22,33,44,55` = 70 trial. MockLLM, world/as_of `2026-11-15`, pricing và evaluator cố định; mỗi trial một SQLite mới. Giá mô phỏng: input 20/output 80 VND mỗi 1.000 token, tool 10 VND/call. Công thức theo [metrics](../../docs/metrics.md); bảng làm tròn khi trình bày.

| Shape | Pass | Pass^5 | Seed min–max | Variance | Tổng cost | Cost/success | Mean/p95 steps |
| --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
| workflow | 70/70 = 1 | 1 | 1–1 | 0 | 1950.00 | 27.857143 | 4.428571 / 5 |
| single | 70/70 = 1 | 1 | 1–1 | 0 | 2309.10 | 32.987143 | 9.214286 / 10 |
| orchestrator | 70/70 = 1 | 1 | 1–1 | 0 | 3970.40 | 56.720000 | 5.357143 / 6 |
| swarm | 69/70 = 0.985714 | 0.928571 | 0.928571–1 | 0.000816327 | 3420.12 | 49.566957 | 2.800000 / 3 |

Cost là VND mô phỏng, không phải hóa đơn API; latency `unavailable`. Mean/p95 là số event, không phải số bước vòng ReAct. ID thật: `R-workflow-C-001-s11`, `R-single-C-001-s11`, `R-orchestrator-C-001-s11`; fail duy nhất `R-swarm-C-002-s55` (`status resolved != denied`). Các ID xác định theo trial; không có batch run ID trong schema.

| Kiểm tra đã chạy trong src/ | Kết quả |
| --- | --- |
| `python -m lab8.smoke` | PASS, Python 3.13.18, Windows AMD64 |
| `python -m pytest -q` | 200 passed, 340 deselected; không failed/skipped (gồm cả test bonus B7, B6) |
| `python -m pytest -q tests/test_trace_safety_group.py` | 42 passed, 92 deselected |
| `python -m pytest -q tests/test_trace_safety_group.py -m student -o addopts=` | 92 passed, 42 deselected |
| `python -m pytest -q tests/test_trace_safety_group.py -o addopts=` | 134 passed, không skipped/failed |
| `python -m pytest -q -m student -o addopts=` | 340 passed, 200 deselected: ma trận gốc 248 + tích hợp P4 92 |
| Ma trận gốc T01–T14 | workflow/single/orchestrator/swarm: mỗi shape 62/62; swarm có assertion xác nhận weakness cố ý |
| `python -m lab8.crash_test --count 20 --out reports/crash.json` | [crash.json](../../src/reports/crash.json): 20/20, từng scenario passed |
| `python -m lab8.check_submission` | 1 FAIL: tiêu đề `# Bonus report: B7`, vì checker chỉ nhận B1 đến B6 trong khi `docs/bonus_topics.md` có B7 (cần coach xác nhận); ADR, shapes, hai JSON, bảng đóng góp và research card hợp lệ |

Crash suite chính thức chủ yếu kiểm host (17 cửa sổ crash, conflict, thiếu approval) và một resume swarm; không tự suy crash safety cho ba shape. Test P4 bổ sung kiểm cả ba cửa sổ crash/resume/retry cho từng shape nhóm. Public và test mutation không phát hiện approval bypass, double refund hay rò secret/PII; scanner âm tính được thử bằng artifact cố ý hỏng, chỉ trong thư mục tạm. Tự kiểm trên `student_drop/` (40 claim × 5 seed, không nhãn) ghi tại [hidden_selfcheck.json](../../src/reports/hidden_selfcheck.json): workflow, single và orchestrator đều 0 error, 0 `leak_suspect`; mỗi shape 95 denied, 90 resolved, 10 escalated, 5 needs_info, cùng status ở mọi cặp claim và seed. P1 soát tay 40 claim theo business rules, không thấy kết quả sai luật. Chưa có điểm hidden chính thức.

Đã chạy lại hai lệnh chính thức: benchmark và crash JSON giống từng byte với lần trước; checksum và môi trường ở báo cáo cá nhân P4. Hai JSON được giữ nguyên output công cụ.

Lệnh benchmark tái lập:

```text
python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json
```

Workflow có cùng pass rate với B/C, cost/success thấp nhất và variance 0 trên bộ public. Kết quả này là cơ sở cho quyết định kiến trúc trong ADR. Research card R2 phân loại fail swarm là thiếu kiểm chứng; đổi shape còn đổi prompt/lịch tool, nên không chứng minh tác động riêng của topology.

**Đối chiếu độ tin cậy của thước đo — B7.** P1 bổ sung kiểm toán grader tại commit `5c338b9`, báo cáo tại `16e2e22`, đã merge vào `main`. Nguồn số liệu: [bonus_grader_audit.json](../../src/reports/bonus_grader_audit.json); [test kiểm toán](../../src/tests/test_bonus_grader_audit.py) đạt **40 PASS**, nằm trong 200 test của `python -m pytest -q`.

| Đối tượng kiểm toán | Kết quả từ JSON B7 |
| --- | --- |
| grader_a | Cost phụ thuộc thứ tự: 283.5 → 285 hoặc 286 khi đảo/xáo cùng danh sách; oracle ghi cost/success 30 thay vì 20 |
| grader_b | 7/8 kiểm tra giữ quan hệ; kiểm tra nhân đôi làm pass^5 0.666667 → 0 do logic dùng chung |
| grader_c | Tính trial hạ tầng vào mẫu số: graded 12 → 16, pass rate 0.75 → 0.5625; 5/8 kiểm tra giữ quan hệ |
| lab8.metrics | 5/8 kiểm tra giữ quan hệ; trên fixture nhân đôi, pass^5 0.666667 → 0; trên fixture hạ tầng có cùng biến động với grader_c |

Mỗi đối tượng có 8 quan hệ/kiểm tra; ngưỡng nghiệp vụ delay 2 ngày so với 3 ngày được kiểm riêng và đúng. Những vi phạm được test kiểm toán xác nhận là phát hiện lỗi của đối tượng được kiểm, không phải 40 test pytest thất bại. Benchmark chính có đúng một trial cho mỗi bộ (shape, claim, seed), không có `infra_error`, nên các fixture B7 không thay đổi số liệu 280 trial ở bảng trên. Host và thước đo được giữ nguyên. Báo cáo B7 và lệnh tái lập: [bonus_report.md](bonus_report.md). Kết quả kiểm toán không xác nhận điều kiện hidden ≥ 0.80 để tính điểm bonus.

**Bản thử B6: investigator kiểu A2A.** P1 thử thêm orchestrator gọi investigator qua transport có lỗi giả lập (mất, trùng, trễ, đảo thứ tự tin), tối đa 3 lần gửi, commit `5bfb01b`. Nguồn: [bonus_a2a.json](../../src/reports/bonus_a2a.json); [test_bonus_a2a.py](../../src/tests/test_bonus_a2a.py) đạt 11 PASS. Function call gốc là 0 message.

| Fault rate | Pass | Pass^5 | Message/trial | Retry/trial | Fail do investigator không trả lời |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0% | 1 | 1 | 1.86 | 0 | 0 |
| 10% | 1 | 1 | 2.19 | 0.19 | 0 |
| 30% | 0.914286 | 0.642857 | 2.79 | 0.56 | 6 |

Cả ba mức đều 0 secret leak và 0 approval bypass. Ở 30%, cả 6 trial fail đều do mất tin ở cả 3 lần gửi. `bonus_report.md` viết cho B7; B6 là bản thử, không có báo cáo riêng.

Quyết định kiến trúc và lý do: xem `report/team/decision_adr.md`. Phiếu nghiên cứu và ablation: xem `report/team/research_card.md`.

## 5. Khó khăn và cách xử lý

- **Order ID toàn khoảng trắng:** P1 phát hiện khi soát workflow với tình huống kiểu hidden và sửa ở `f8e9c77`; orchestrator sửa ở `34daeb2` (P3) và `21768c5` (P4), single theo cùng quy tắc. Điều kiện `if not claim["order_id"]` bỏ sót chuỗi dấu cách/tab/NBSP, làm lookup thất bại rồi trả `escalated`. Tái hiện bằng `python -m pytest -q tests/test_trace_safety_group.py -m student -o addopts= -k blank_order_id --tb=short`: trước sửa 3 FAIL/18 PASS; sau sửa 21 PASS. Predicate mới trả **needs_info** và trace `has_order_id=false`; mã đơn thật không bị strip. Test ID có padding và chữ Cyrillic vẫn trả `escalated`.
- **Phân biệt quote và effect:** T14 phải giữ proposal 150.000 trong khi ledger chỉ thêm 120.000 do đã hoàn 30.000. Test đối chiếu đồng thời proposal, ledger, lịch sử theo order và audit để phát hiện trừ hai lần hoặc trả sai contract.
- **Tính tái lập trên Windows:** kết nối SQLite được đóng trước reopen/resume. JSON được sinh bằng lệnh lab và đối chiếu sau hai lần chạy. Khác biệt CRLF/LF được phân biệt với thay đổi nội dung JSON; môi trường là Python 3.13.18, pytest 8.4.2 và PyYAML 6.0.3 trong `.venv`.

## 6. Tổng hợp đóng góp

Chi tiết đóng góp của từng thành viên nằm trong `TEAM.md` (bảng đóng góp) và báo cáo cá nhân `report/team/MSSV_HoTen.md`.

| Vai | Bằng chứng đang có |
| --- | --- |
| P1 — Bùi Đức Tuấn | Workflow và `test_workflow_group.py`, commit `2ee7bb6`, `f8e9c77`; kiểm toán B7 ở `5c338b9`, báo cáo `16e2e22`, `test_bonus_grader_audit.py`; bản thử B6 `5bfb01b`, `test_bonus_a2a.py`; tích hợp nhánh, ADR, merge PR #5 `d606089` |
| P2 — Nguyễn Lê Đăng Khoa | Single, `test_single_group.py`, báo cáo cá nhân, commit `c205335`, `b5a1513` |
| P3 — Lê Quân Bảo | Orchestrator/handoff, `test_orchestrator_group.py`, báo cáo cá nhân, commit `ada63e5`, `34daeb2` |
| P4 — Mai Xuân Khang | `test_trace_safety_group.py` (134 case), sửa regression order ID toàn khoảng trắng ở orchestrator, commit `21768c5`; hai JSON chính thức, research card, báo cáo nhóm và [báo cáo cá nhân](2A202603722_MaiXuanKhang.md), commit `d5a8733`; đối chiếu số liệu B7 của P1 với benchmark chính |

Bảng đóng góp trong [TEAM.md](../../TEAM.md) liên kết từng thành viên với commit kỹ thuật và test tương ứng.

## 7. Hạn chế và hướng cải thiện

MockLLM không phải model sản xuất; latency `unavailable`. Public có 14 claim và nhãn đã biết, không đại diện hidden 40 × 5 hoặc production; không tuyên bố hidden ≥ 0.75. Policy/ledger host được tin cậy theo lab; triển khai thật cần kiểm quyền, concurrency nhiều process, hệ thống thanh toán, rollback/đối soát và lưu trữ bền vững bên ngoài SQLite local.

Trace allowlist và scanner chỉ chứng minh các artifact được quan sát; không bảo đảm mọi kênh production đều sạch. Cần kiểm cả log/service/APM và lifecycle dữ liệu khi triển khai thật. Principal mâu thuẫn, thiếu order, approval hết hạn/thu hồi/mượn claim và đề nghị ngoại lệ phải hỏi thêm hoặc chuyển người có thẩm quyền; model không tự cấp approval. Kết luận public cần được đánh giá lại trên hidden hợp lệ và workload thực tế trước khi mở rộng triển khai.

## 8. Tài liệu tham khảo

- [Starter chính thức](https://github.com/VinUni-AI20k/K5-Day8-From-Workflows-to-Agents), [RUBRIC](../../RUBRIC.md), [RULES](../../RULES.md), [SUBMISSION](../../SUBMISSION.md).
- [Business rules](../../docs/business_rules.md), [contracts](../../docs/contracts.md), [architecture](../../docs/architecture.md), [metrics](../../docs/metrics.md).
- Cemri và cộng sự (2025), [Why Do Multi-Agent LLM Systems Fail? — NeurIPS](https://proceedings.neurips.cc/paper_files/paper/2025/hash/b1041e52d3be19f0a9bc491657488e4a-Abstract-Datasets_and_Benchmarks_Track.html); thiết kế và giới hạn áp dụng: [research card](research_card.md).
