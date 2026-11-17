# Báo cáo cá nhân — 2A202603722_MaiXuanKhang

## 1. Thông tin thành viên

- Họ tên: Mai Xuân Khang.
- MSSV: 2A202603722.
- Email: maixkhang2004@gmail.com.
- GitHub: [KhangMai123](https://github.com/KhangMai123).
- Vai trò: P4 — Ledger, Safety Testing, Evaluation & Reporting.

## 2. Phần việc phụ trách

Kiểm chứng ledger/idempotency, approval/policy, trace/privacy và handoff; chạy crash suite, benchmark công bằng; hoàn thiện research card, báo cáo nhóm, bảng đóng góp và báo cáo cá nhân. Giữ nguyên host, thước đo, fixture, config và ma trận chuẩn. Bổ sung test và sửa regression xử lý order ID toàn khoảng trắng của orchestrator, có bằng chứng trước/sau.

## 3. Đóng góp cụ thể

- Thêm `src/tests/test_trace_safety_group.py`: **134 case pytest**, gồm 42 độc lập (host/swarm) và 92 tích hợp (`student`); không skip/xfail, không API/mạng. `tmp_path` chứa SQLite/trace; chỉ đổi thư mục làm việc, không patch logic refund/approval/grader. SQLite connection đóng trước khi reopen/resume, phù hợp Windows.
- Ledger: đúng một effect và audit, retry nhiều lần, conflict giữ nguyên tiền/checkpoint, ba cửa sổ crash với trạng thái trước resume, lịch sử refund/cap theo order, T13/T14 và trần approved/paid.
- Policy: thiếu/hết hạn/thu hồi/approval của claim khác phải bị từ chối, quote dương phải tới host để có audit `policy_denied`; test retry không bypass approval. Injection không đổi nguồn sự thật order hay tạo approval.
- Trace: RunResult/run ID/events/freshness, mọi nhánh public, phát hiện missing/stale/invalid/mismatch; scanner đọc sibling `<run_id>*`. Quét giá trị secret/header và PII từ fixture trên artifact lẫn stdout/stderr, không in chuỗi nhạy cảm khi assert fail. Negative scanner test chỉ cố ý làm bẩn file tạm.
- Handoff: đối chiếu trực tiếp `ALLOWED_FIELDS`, `FACT_KEYS`, `READONLY_TOOLS`; worker không nhận/call tool ghi. Kiểm payload handoff thật của orchestrator/swarm thay vì tự đặt allowlist.
- Regression: orchestrator coi `None`, chuỗi rỗng, dấu cách, tab, NBSP là thiếu order → `needs_info`, không handoff/ledger. ID có padding/ký tự giống vẫn giữ nguyên để lookup và `escalated`, không normalize thành đơn hợp lệ.
- Dùng lệnh lab sinh `benchmark.json`, `crash.json`; không chỉnh JSON thủ công. Viết research card R2 với nguồn MAST chính thức và so sánh A/D có chỉ rõ confounder; hoàn thiện báo cáo nhóm theo mẫu và bảng đóng góp trong TEAM bằng commit/test có thật.
- Đối chiếu kết quả kiểm toán B7 của P1 với bộ benchmark chính; ghi riêng revision và kết quả bonus để không cộng gộp test hay thay đổi metric giữa hai bộ dữ liệu.

## 4. Bằng chứng

- Commit kỹ thuật: **`21768c53415405fe43f56a46adc8d34406e49faa`**, thông điệp `[P4] Add ledger and trace safety tests; fix blank order ID regression`.
- Commit báo cáo và bằng chứng: **`d5a8733d256493e11b8eb883a196aaaf2fdc2035`**.
- Base nhóm: `c2eba6a1f319cf175b135acaca5e6008b8ee21aa`, đã tích hợp P1/P2/P3.
- Test tiêu biểu: `test_host_crash_durable_state_survives_connection_reopen`, `test_conflicting_retries_preserve_effect_checkpoint_and_committed_audit`, `test_approval_gate_denies_positive_quote_and_retry_without_effect`, `test_reference_writes_current_trace_on_all_public_branches`, `test_trace_validator_rejects_corrupted_real_run`, `test_student_positive_quote_reaches_host_denial`, `test_blank_order_id_needs_info_before_handoff`.

Các lệnh sau đã chạy trong `src/`, dùng Python 3.13.18 của `.venv`:

| Lệnh | Kết quả thực tế |
| --- | --- |
| `python -m lab8.smoke` | PASS |
| `python -m pytest -q` | 139 passed, 340 deselected, không skipped/failed |
| `python -m pytest -q tests/test_trace_safety_group.py` | 42 passed, 92 deselected |
| `python -m pytest -q tests/test_trace_safety_group.py -m student -o addopts=` | 92 passed, 42 deselected |
| `python -m pytest -q tests/test_trace_safety_group.py -o addopts=` | 134 passed, không deselected/skipped/failed |
| `python -m pytest -q -m student -o addopts=` | 340 passed, 139 deselected; gồm 248 matrix gốc + 92 P4 tích hợp |
| `python -m lab8.crash_test --count 20 --out reports/crash.json` | 20/20 scenario passed |
| `python -m lab8.check_submission` | Còn 1 file chưa hoàn thiện: ADR, với 7 FAIL theo từng trường; các mục shapes, reports, TEAM và research card hợp lệ |

Trước sửa regression: lọc `-k blank_order_id` có 3 failed/18 passed; ba lỗi là spaces, tab và NBSP của orchestrator trả `escalated` thay vì `needs_info`. Sau sửa, cả 92 test tích hợp P4 PASS, bao gồm các test regression và kiểm tra mã đơn không bị normalize.

Lệnh tạo benchmark:

```text
python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json
```

Nguồn [benchmark.json](../../src/reports/benchmark.json): 280 trial, mỗi shape 70, SQLite mới/trial. Workflow/single/orchestrator lần lượt pass 70/70, pass^5 1, variance 0; cost/success mô phỏng 27.857142857 / 32.987142857 / 56.72 VND. Swarm pass 69/70, pass^5 13/14, variance 0.000816326531, cost/success 49.566956522 VND. Trial fail `R-swarm-C-002-s55`; cặp ablation `R-workflow-C-002-s55` / `R-swarm-C-002-s55`. [crash.json](../../src/reports/crash.json) là 20/20 của host/reference; kết quả crash từng shape nhóm được chứng minh riêng bằng test P4, không gán nhầm từ suite này.

Chưa có kết quả hidden để đối chiếu. Mọi số liệu là public/test mutation; latency `unavailable`. Báo cáo nhóm và research card dẫn tới cùng JSON, cùng commit kỹ thuật.

Đối chiếu bổ sung: `python -m pytest -q tests/test_bonus_grader_audit.py` đã chạy riêng trên revision B7 của P1 `16e2e22` và đạt **40 PASS**. [JSON kiểm toán](https://github.com/buiductuan2884-max/K5-L3B-DAY08-GroupT-FromWorkflowsToAgents/blob/16e2e22/src/reports/bonus_grader_audit.json) cho thấy grader_a có cost phụ thuộc thứ tự, grader_c đổi pass rate 0.75 → 0.5625 khi thêm trial hạ tầng, và pass^5 của logic dùng chung đổi 0.666667 → 0 khi nhân đôi trial. Benchmark chính có đúng 280 bộ (shape, claim, seed) phân biệt và không chứa `infra_error`, nên vẫn giữ số liệu gốc. Triển khai và test B7 thuộc P1; đóng góp P4 là kiểm tra, đối chiếu và đồng bộ báo cáo. Kết quả 40 PASS không cộng vào số test của revision phần chính.

Đã lặp lại hai lệnh chính thức trên cùng code/môi trường Windows: benchmark/crash JSON trùng từng byte với lần chạy trước. SHA-256 của hai file được Git lưu với newline LF lần lượt là `1a52a4311f4631feb3480e321f06686ae8bc53dfd44de574555b74fb17c330f3` và `20a61898de6b4570202221f752e05b130a83f56ed3830452e4d4de120c3f9f57`. Nội dung JSON không đổi khi chuẩn hóa CRLF/LF. Môi trường: Python 3.13.18 trong `src/.venv`, pytest 8.4.2, PyYAML 6.0.3; `.venv` không nằm trong bài nộp.

## 5. Công cụ AI đã dùng

**AI hỗ trợ** đọc source/contract, thiết kế và triển khai test, phân tích kết quả kiểm thử, JSON và soạn báo cáo. Kết quả được kiểm chứng bằng:

1. Đối chiếu expected công khai và luật nghiệp vụ gốc, không sửa expected để test xanh.
2. Chạy code thật với SQLite; assert effect, audit, checkpoint trước/sau crash và sau reopen; test âm kiểm chứng scanner fail-closed.
3. Tái hiện regression trước sửa, chạy toàn bộ host/student sau sửa; giữ weakness swarm và không dùng mock thay host.
4. Đọc JSON được công cụ sinh để lấy metric/run ID, đối chiếu công thức metrics.md; xác minh nguồn MAST qua proceedings NeurIPS.
5. Rà Git diff để đối chiếu phạm vi đóng góp; giữ nguyên host, thước đo và dữ liệu chuẩn. Không coi nhận định AI hay public PASS là hidden PASS.

## 6. Tự đánh giá

Đã hoàn thành phần triển khai và thực nghiệm P4: test độc lập, tích hợp ba shape, crash suite chính thức 20/20 và benchmark đủ bốn kiến trúc. Đóng góp được đối chiếu với commit kỹ thuật, test, hai JSON và bảng đóng góp trong [TEAM.md](../../TEAM.md). Kết quả hiện giới hạn ở public/test mutation, không thay thế điểm hidden hoặc chứng minh an toàn production. Phần triển khai kiến trúc của P1–P3 được ghi nhận riêng trong báo cáo nhóm.

**Đối chiếu rubric, không tự quy đổi thành điểm:**

| Hạng mục | P4 trực tiếp chứng minh | Phụ thuộc / giới hạn |
| --- | --- | --- |
| C3 — 20 điểm | Crash JSON 20/20; ledger/retry/conflict, crash/resume từng shape trong test P4; T11/T12 matrix gốc đều PASS | Suite chính thức chủ yếu host/reference; hidden vẫn do giảng viên |
| C4 — 10 điểm | Approval missing/expired/revoked/borrowed, cap, audit, T13/T14 và injection; public matrix PASS | Policy host nguyên bản; counter hidden chưa được cấp |
| C5 — 10 điểm | Trace contract, fail-closed scanner, PII/stdout, handoff thật theo allowlist | Không chứng minh mọi kênh production sạch; hidden leak counters chưa có |
| C6 — 10 điểm | 4 shape × 14 claim × 5 seeds, research R2/ablation có nguồn và confounder | Quyết định kiến trúc được ghi riêng trong ADR |
| C7 — 10 điểm | Lệnh, môi trường, commit kỹ thuật, trial ID/checksum; chạy lại JSON giống từng byte | Commit chốt bài nộp theo ADR |
| C8 — 5 điểm | Test/commit kỹ thuật, bảng đóng góp TEAM và báo cáo cá nhân | Đối chiếu lịch sử Git của nhánh nộp |

Ba must-pass được kiểm trên public/test P4: thiếu approval không tạo refund, không thấy canary/PII trong artifact được quét, crash/retry không thêm refund. Ngưỡng hidden ≥ 0.75 trên 200 trial và các counter chính thức **chỉ grader giảng viên xác nhận**, không suy từ public PASS. `check_submission` kiểm format và một số public case, không thay grader hidden.
