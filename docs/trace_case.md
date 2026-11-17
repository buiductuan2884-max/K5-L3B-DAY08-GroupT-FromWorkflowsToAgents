# Trace case: từ trace tới quyết định sai đầu tiên

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, item E-002; trace run `R-seeded_regression-C-002-s11`; report `E-seeded_regression-20261117-28cb` trong src/reports/eval_seeded_regression.json. |
| Triệu chứng | Status resolved, proposal=20.000, ledger=20.000, refund_count=1; expected denied, proposal=0, ledger=0, refund_count=0. Reply: “Dạ, LogiX đã hoàn 20.000đ cho đơn O-202.” |
| Bước sai đầu tiên | **Event 3**, kind model_override, payload `{"delay_days": 5}`: thay DB trễ 2 ngày bằng lời ticket nói trễ 5 ngày. |
| Vì sao là bước đầu tiên | Event 1 tạo handoff allowlist đúng claim; event 2 investigator trả order nhìn thấy được và delay_days=2. Chưa có ghi tiền hoặc ghi đè sự thật DB. Quote 20.000 ở event 4 là hậu quả của event 3. |
| Failure mode | FM-03 trong [failure_taxonomy.md](failure_taxonomy.md). Approval hợp lệ và unexpected_rows=0; không quy lỗi này thành approval bypass. |
| Đối chứng | `fixed C-002@11`, trace R-fixed-C-002-s11: không có model_override, giữ 2 ngày; event 3 quote=0/no_entitlement, event 4 reply từ chối. Ledger=0, refund_count=0, status denied; TrialPass PASS. |
| Regression test | `tests/test_lab9_regression.py::test_trace_first_error_and_fixed` kiểm thứ tự event, DB=2, override=5 và ledger 20.000 so với 0. RefundAmountCorrect từ chối trial lỗi, chấp nhận fixed; test đã chạy thành công. |
| Chưa chắc chắn | MockLLM chỉ chứng minh cơ chế trong fixture. Trace không ghi mọi suy luận, nên không suy diễn ý định hay tần suất trên model thật. |

```powershell
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11
python -m pytest -q -m student -o addopts= -k trace_first_error_and_fixed
```

Ledger và expected là bằng chứng chính. Ở case này reply khớp ledger nên FM-08 không bắt lỗi; refund_amount_correct/pass_rate mới phát hiện kết quả sai. Regression `test_reply_metric_rejects_misreport_accepts_fixed` kiểm case bổ sung C-008: ledger đúng 20.000 nhưng reply sai 35.000; metric FM-08 từ chối misreport và chấp nhận fixed/honest_refactor.
