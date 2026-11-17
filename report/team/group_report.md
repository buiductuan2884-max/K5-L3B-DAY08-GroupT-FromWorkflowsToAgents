# Báo cáo nhóm — Lab 8 LogiX-VN

Báo cáo ngắn gọn theo mẫu Lab 08; số liệu đọc trực tiếp từ JSON do công cụ sinh ngày 17/11/2026.

## 1. Thông tin nhóm

- Tên nhóm: **GroupT — L3B**.
- Thành viên theo [TEAM.md](../../TEAM.md): Bùi Đức Tuấn (P1), Nguyễn Lê Đăng Khoa (P2), Lê Quân Bảo (P3), Mai Xuân Khang (P4).
- Repository: [GroupT](https://github.com/buiductuan2884-max/K5-L3B-DAY08-GroupT-FromWorkflowsToAgents).
- Commit chốt (trùng `report/team/decision_adr.md`): **P1 chưa chốt**. Bằng chứng kỹ thuật P4 chạy trên `21768c53415405fe43f56a46adc8d34406e49faa`, kế thừa `origin/main` tại `c2eba6a1f319cf175b135acaca5e6008b8ee21aa`. Nhánh P4 local `2A202603722`, chưa push theo yêu cầu của thành viên.

## 2. Mục tiêu và cách tiếp cận

LogiX-VN xử lý yêu cầu hoàn phí vận chuyển/hỏng hàng từ ticket. Order và policy hiện hành là nguồn sự thật; ticket là dữ liệu không đáng tin. Tiền do code tính, host kiểm approval và ghi ledger. Nhóm so bốn kiến trúc trên cùng corpus để chọn mức tự chủ ít nhất đáp ứng yêu cầu.

P1 triển khai workflow và tích hợp hồ sơ; P2 triển khai single ReAct; P3 triển khai orchestrator/handoff; P4 kiểm ledger, policy, crash, trace/privacy, benchmark và báo cáo. P4 đọc contract trước, chạy baseline, bổ sung test độc lập rồi kiểm tích hợp sau khi cập nhật đầy đủ P1–P3.

## 3. Giải pháp

- **Workflow:** bước Python cố định: claim view → order theo principal → quote → host. Không gọi model. Trace ghi claim ID/có order, visibility, quote, kết quả host và quyết định; không ghi ticket.
- **Single ReAct:** `run_react(max_steps=8)`, một MockLLM call mỗi bước. Code chọn read tool theo observation, lưu kết quả rồi quyết quote/ghi tiền sau vòng lặp; không dùng model final để quyết số tiền. Trace chỉ ghi tóm tắt observation và bước ReAct.
- **Orchestrator:** đọc claim, dựng `make_handoff`, investigator đọc order/policy/refund history/quote; orchestrator chuyển quote đầy đủ cho host. Handoff theo `ALLOWED_FIELDS`/`FACT_KEYS`, tools theo `READONLY_TOOLS`; trace ghi handoff đã sanitize và tóm tắt investigator. P4 chỉ sửa lỗi order toàn khoảng trắng theo yêu cầu riêng; phần triển khai còn lại thuộc P3.
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
| `python -m pytest -q` | 139 passed, 340 deselected; không failed/skipped |
| `python -m pytest -q tests/test_trace_safety_group.py` | 42 passed, 92 deselected |
| `python -m pytest -q tests/test_trace_safety_group.py -m student -o addopts=` | 92 passed, 42 deselected |
| `python -m pytest -q tests/test_trace_safety_group.py -o addopts=` | 134 passed, không skipped/failed |
| `python -m pytest -q -m student -o addopts=` | 340 passed, 139 deselected: ma trận gốc 248 + tích hợp P4 92 |
| Ma trận gốc T01–T14 | workflow/single/orchestrator/swarm: mỗi shape 62/62; swarm có assertion xác nhận weakness cố ý |
| `python -m lab8.crash_test --count 20 --out reports/crash.json` | [crash.json](../../src/reports/crash.json): 20/20, từng scenario passed |
| `python -m lab8.check_submission` sau hoàn thiện P4 | 8 FAIL thuộc ADR (7) và bảng đóng góp TEAM (1), cần P1 |

Crash suite chính thức chủ yếu kiểm host (17 cửa sổ crash, conflict, thiếu approval) và một resume swarm; không tự suy crash safety cho ba shape. Test P4 bổ sung kiểm cả ba cửa sổ crash/resume/retry cho từng shape nhóm. Public và test mutation không phát hiện approval bypass, double refund hay rò secret/PII; scanner âm tính được thử bằng artifact cố ý hỏng, chỉ trong thư mục tạm. Không có `student_drop/`, chưa chạy hidden selfcheck hay nhận điểm hidden.

Đã chạy lại hai lệnh chính thức: benchmark và crash JSON giống từng byte với lần trước; checksum và môi trường ở báo cáo cá nhân P4. Hai JSON được giữ nguyên output công cụ.

Lệnh benchmark tái lập:

```text
python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json
```

P4 đề xuất workflow dựa trên public: cùng pass với B/C, cost/success thấp nhất, variance 0. Đây là khuyến nghị cho P1, chưa thay quyết định ADR. Research card R2 phân loại fail swarm là thiếu kiểm chứng; đổi shape còn đổi prompt/lịch tool, nên không chứng minh tác động riêng của topology.

Quyết định kiến trúc và lý do: xem `report/team/decision_adr.md`. Phiếu nghiên cứu và ablation: xem `report/team/research_card.md`.

## 5. Khó khăn và cách xử lý

- Máy ban đầu chỉ có Python 3.14, Git/CLI không trong PATH. Đã chuẩn bị Python 3.13.18, `.venv`, pytest 8.4.2/PyYAML 6.0.3 và Git/CLI trong khu vực công cụ ngoài repo. Không đổi dependency của lab. Đăng nhập lại bằng credential Windows sẵn có, xác minh `KhangMai123` và quyền push; không đưa credential vào repo.
- Lần clone đầu tại `b5a1513`, P3 còn stub: baseline 81 host PASS; student 186 PASS/62 FAIL. Khi main có PR #4, đã fetch và fast-forward tới `c2eba6a`, không ghi đè công việc đồng đội. Benchmark chẩn đoán cũ được thay bằng output lệnh chính thức sau tích hợp; không sửa JSON bằng tay.
- Regression P3: `if not claim["order_id"]` không nhận diện chuỗi toàn khoảng trắng, nên lookup thất bại rồi trả `escalated`. Tái hiện: `python -m pytest -q tests/test_trace_safety_group.py -m student -o addopts= -k blank_order_id --tb=short`: trước sửa 3 FAIL/18 PASS; sau sửa các case đều PASS. Sửa riêng predicate để trả **needs_info** và trace `has_order_id=false`; không strip mã đơn thật. Test padded ID và chữ Cyrillic vẫn `escalated`.
- Blocker hồ sơ: ADR chưa điền 7 trường, bảng đóng góp TEAM trống. File P3 tên `2A20260388_LeQuanBao.md` khác MSSV `2A202603888` trong TEAM; P1/P3 cần xác minh. P4 không đổi hồ sơ thuộc người khác. Chưa push theo chỉ dẫn của Mai Xuân Khang.

## 6. Tổng hợp đóng góp

Chi tiết đóng góp của từng thành viên nằm trong `TEAM.md` (bảng đóng góp) và báo cáo cá nhân `report/team/MSSV_HoTen.md`.

| Vai | Bằng chứng đang có |
| --- | --- |
| P1 — Bùi Đức Tuấn | Workflow và `test_workflow_group.py`, commit `2ee7bb6`, `f8e9c77`; hồ sơ tích hợp/ADR còn cần hoàn tất |
| P2 — Nguyễn Lê Đăng Khoa | Single, `test_single_group.py`, báo cáo cá nhân, commit `b5a1513` |
| P3 — Lê Quân Bảo | Orchestrator/handoff, `test_orchestrator_group.py`, báo cáo cá nhân, commit `ada63e5` |
| P4 — Mai Xuân Khang | `test_trace_safety_group.py` (134 case), fix nhỏ P3 được yêu cầu, commit `21768c5`; hai JSON chính thức, research card, báo cáo nhóm và [báo cáo cá nhân](2A202603722_MaiXuanKhang.md) |

Dòng đề nghị P1 đưa vào bảng TEAM: `Mai Xuân Khang — P4 ledger/safety/evaluation/report — 21768c5 — src/tests/test_trace_safety_group.py (42 độc lập + 92 tích hợp)`. Không quy triển khai P1–P3 thành đóng góp P4.

## 7. Hạn chế và hướng cải thiện

MockLLM không phải model sản xuất; latency `unavailable`. Public có 14 claim và nhãn đã biết, không đại diện hidden 40 × 5 hoặc production; không tuyên bố hidden ≥ 0.75. Policy/ledger host được tin cậy theo lab; triển khai thật cần kiểm quyền, concurrency nhiều process, hệ thống thanh toán, rollback/đối soát và lưu trữ bền vững bên ngoài SQLite local.

Trace allowlist và scanner chỉ chứng minh các artifact được quan sát; không bảo đảm mọi kênh production đều sạch. Cần kiểm cả log/service/APM và lifecycle dữ liệu khi triển khai thật. Principal mâu thuẫn, thiếu order, approval hết hạn/thu hồi/mượn claim và đề nghị ngoại lệ phải hỏi thêm hoặc chuyển người có thẩm quyền; model không tự cấp approval. P1 chỉ chốt ADR/commit nộp sau khi hoàn tất hồ sơ, kiểm hidden hợp lệ nếu được phát và chạy lại trên nhánh nộp.

## 8. Tài liệu tham khảo

- [Starter chính thức](https://github.com/VinUni-AI20k/K5-Day8-From-Workflows-to-Agents), [RUBRIC](../../RUBRIC.md), [RULES](../../RULES.md), [SUBMISSION](../../SUBMISSION.md).
- [Business rules](../../docs/business_rules.md), [contracts](../../docs/contracts.md), [architecture](../../docs/architecture.md), [metrics](../../docs/metrics.md).
- Cemri và cộng sự (2025), [Why Do Multi-Agent LLM Systems Fail? — NeurIPS](https://proceedings.neurips.cc/paper_files/paper/2025/hash/b1041e52d3be19f0a9bc491657488e4a-Abstract-Datasets_and_Benchmarks_Track.html); thiết kế và giới hạn áp dụng: [research card](research_card.md).
