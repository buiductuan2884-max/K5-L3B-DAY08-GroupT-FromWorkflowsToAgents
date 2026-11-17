# Báo cáo nhóm — Lab 8 LogiX-VN

Tối đa 5 trang ngoài phụ lục. Số liệu lấy từ file trong `src/reports/`, không chép tay từ terminal.

## 1. Thông tin nhóm

- Tên nhóm:
- Thành viên: xem `TEAM.md`
- Commit chốt (trùng `report/team/decision_adr.md`):

## 2. Mục tiêu và cách tiếp cận

Nhóm hiểu bài toán thế nào, chia việc ra sao, thứ tự làm bốn shape.

...

**Phần P4 — Mai Xuân Khang:** thiết kế kiểm thử ledger, approval, crash và trace/privacy; chạy benchmark cùng corpus, seeds, pricing và evaluator; đối chiếu số liệu từ JSON để làm bằng chứng đánh giá.

## 3. Giải pháp

Mô tả ba shape nhóm viết (workflow, single, orchestrator): mỗi shape đọc gì, quyết định gì, gọi host ra sao. Chỉ rõ ranh giới code / model (tham khảo [docs/architecture.md](../../docs/architecture.md)), cách handoff được sanitize và trace ghi những event nào.

...

**Phần P4 — Kiểm chứng an toàn:** `src/tests/test_trace_safety_group.py` có 134 case: 42 độc lập và 92 tích hợp. Test dùng SQLite thật và `tmp_path`, không thay refund/approval bằng mock. Các assert đối chiếu effect, audit, checkpoint, approval, trần theo order, T13/T14 và trạng thái sau retry/crash. Trace được kiểm `run_id`, events, freshness và các sibling `<run_id>*`; quét canary, header và PII trên artifact, stdout/stderr. Handoff được đối chiếu với allowlist của host, worker bị chặn tool ghi.

## 4. Kết quả

Bảng so sánh 4 shape trên bộ public (từ `src/reports/benchmark.json`): pass rate, pass^5, seed min–max, variance, cost/success, mean/p95 steps. Kèm crash safety (`src/reports/crash.json`) và, nếu có, kết quả tự kiểm trên `student_drop/`.

**Phần P4 — Kết quả đo và kiểm thử.** Nguồn: [benchmark.json](../../src/reports/benchmark.json), [crash.json](../../src/reports/crash.json), code đánh giá tại `21768c53415405fe43f56a46adc8d34406e49faa`. Mỗi shape có 14 public claim × seeds `11,22,33,44,55` = 70 trial; tổng 280 trial, SQLite mới mỗi trial, cùng MockLLM, pricing và as_of `2026-11-15`. Công thức theo [metrics.md](../../docs/metrics.md).

| Shape | Pass rate | Pass^5 | Seed min–max | Variance | Tổng cost | Cost/success | Mean/p95 steps |
| --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
| workflow | 70/70 = 1.000000 | 1.000000 | 1.000000–1.000000 | 0.000000000 | 1950.00 | 27.857143 | 4.428571 / 5 |
| single | 70/70 = 1.000000 | 1.000000 | 1.000000–1.000000 | 0.000000000 | 2309.10 | 32.987143 | 9.214286 / 10 |
| orchestrator | 70/70 = 1.000000 | 1.000000 | 1.000000–1.000000 | 0.000000000 | 3970.40 | 56.720000 | 5.357143 / 6 |
| swarm | 69/70 = 0.985714 | 0.928571 | 0.928571–1.000000 | 0.000816327 | 3420.12 | 49.566957 | 2.800000 / 3 |

Cost là VND mô phỏng, không phải hóa đơn API; latency `unavailable`. Steps là số event trong trace. Trial fail duy nhất là `R-swarm-C-002-s55` với reason `status resolved != denied`, đúng weakness được starter công bố. ID đối chiếu: `R-workflow-C-001-s11`, `R-single-C-001-s11`, `R-orchestrator-C-001-s11`.

| Kiểm tra P4 đã thực hiện | Kết quả |
| --- | --- |
| Test P4 độc lập | 42 PASS |
| Test P4 tích hợp | 92 PASS |
| Toàn bộ test P4 | 134 PASS, không failed/skipped |
| Cổng kiểm thử mặc định | 139 PASS |
| Student: ma trận gốc + test tích hợp P4 | 340 PASS; ma trận gốc mỗi shape 62/62 |
| Crash suite chính thức | 20/20 scenario PASS |

Crash suite chính thức chủ yếu kiểm host/reference; kiểm thử P4 bổ sung ba cửa sổ crash/resume/retry cho từng shape nhóm. Không phát hiện approval bypass, double refund hoặc rò secret/PII trong phạm vi test P4. Public benchmark không xác nhận hidden pass rate.

Lệnh tái lập trong `src/`, dùng `.venv`:

```text
python -m pytest -q tests/test_trace_safety_group.py -o addopts=
python -m lab8.crash_test --count 20 --out reports/crash.json
python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json
```

Quyết định kiến trúc và lý do: xem `report/team/decision_adr.md`. Phiếu nghiên cứu và ablation: xem `report/team/research_card.md`.

## 5. Khó khăn và cách xử lý

Lỗi gặp phải (kèm lệnh, output hoặc ảnh chụp) và cách nhóm xử lý.

...

**Phần P4:** test phải tách quote đầy đủ với effect sau khi trừ refund lịch sử, kiểm lại SQLite sau reopen và tránh trace cũ gây false positive. Dùng thư mục tạm riêng cho mỗi test, đóng connection trước resume và xác nhận cả ledger lẫn audit. Test hồi quy order ID toàn khoảng trắng yêu cầu `needs_info`, không handoff/refund; ID có padding hoặc ký tự giống nhau vẫn được lookup nguyên dạng và `escalated`.

## 6. Tổng hợp đóng góp

Chi tiết đóng góp của từng thành viên nằm trong `TEAM.md` (bảng đóng góp) và báo cáo cá nhân `report/team/MSSV_HoTen.md`.

| Người | Vai | Bằng chứng |
| --- | --- | --- |
| Mai Xuân Khang — 2A202603722 | P4 — Ledger, safety testing, evaluation và báo cáo | `test_trace_safety_group.py` (134 case), commit `21768c5`; hai JSON chính thức, research card và [báo cáo cá nhân](2A202603722_MaiXuanKhang.md), commit `d5a8733` |

## 7. Hạn chế và hướng cải thiện

MockLLM không phải model sản xuất; latency là `unavailable`. Nêu thêm giới hạn của nhóm và điều kiện làm kết luận thay đổi.

...

**Phần P4:** bằng chứng giới hạn ở public/test mutation và artifact được quét. Không suy hidden PASS hoặc độ an toàn production từ kết quả này. Nghiên cứu so sánh shape có confounder về prompt/lịch tool; không chứng minh riêng tác động của topology. Scanner cần được mở rộng tới các kênh log khác khi triển khai thực tế.

## 8. Tài liệu tham khảo

...

**Tài liệu dùng cho phần P4:**

- [RUBRIC](../../RUBRIC.md), [SUBMISSION](../../SUBMISSION.md), [RULES](../../RULES.md).
- [Business rules](../../docs/business_rules.md), [contracts](../../docs/contracts.md), [metrics](../../docs/metrics.md).
- Cemri và cộng sự (2025), [Why Do Multi-Agent LLM Systems Fail? — NeurIPS](https://proceedings.neurips.cc/paper_files/paper/2025/hash/b1041e52d3be19f0a9bc491657488e4a-Abstract-Datasets_and_Benchmarks_Track.html), sử dụng trong [research card](research_card.md).
