# Bonus report: B7

- Topic + nguồn (tên, năm, slide): B7 · Kiểm toán grader. *Rethinking Evaluation of MAS Efficiency*, EMNLP 2026, slide 44 và 59.
- CLAIM của nguồn (1 câu): kết luận về hiệu năng của hệ multi-agent có thể đến từ cách đo, nên thước đo sai thì mọi so sánh giữa các kiến trúc cũng sai theo.
- BOUNDARY (model / dataset / setup): nguồn nói về benchmark hiệu năng MAS chạy model thật. Ở LogiX, đối tượng bị kiểm là ba bản `summarize` do giảng viên đưa (`grader_audit/grader_a.py`, `grader_b.py`, `grader_c.py`) và bản gốc `lab8.metrics.summarize`. Dữ liệu là ba cặp fixture có sẵn (12 đến 24 trial, một shape) cộng một bộ 5 trial tự tạo có đáp án tính tay. Không có model nào tham gia; MockLLM không liên quan đến phần này.
- HYPOTHESIS trên LogiX: cùng một danh sách trial, ít nhất một bản grader sẽ vi phạm quan hệ metamorphic. Độ lệch đủ lớn để đổi kết luận so sánh shape: pass rate lệch hơn 0.1, hoặc cost/success lệch hơn 10%.
- Biến cố định / biến thay đổi: cố định danh sách trial (fixture), quan hệ và ngưỡng so sánh (sai số 1e-9). Biến duy nhất thay đổi là bản `summarize` được gọi.
- Lệnh tái lập (copy-paste được), chạy trong `src/`:
  - `python -m pytest -q tests/test_bonus_grader_audit.py`
  - `python -m bonus.grader_audit --out reports/bonus_grader_audit.json --md reports/bonus_grader_audit_table.md`
- File report + run id: `src/reports/bonus_grader_audit.json`, bảng `src/reports/bonus_grader_audit_table.md`, commit `5c338b9`. Topic này không có biến thể shape nên không có run id benchmark. Test `test_committed_report_matches_a_fresh_run` bảo đảm file JSON trùng với một lần chạy mới.

## Kết quả

Ba quan hệ đề cho, một quan hệ mới của nhóm (`NEW_trial_order_does_not_matter`: đảo ngược hoặc xáo trộn cố định thứ tự trial thì mọi số phải giữ nguyên), bốn kiểm tra phụ. Bảng dưới do script sinh ra (`LECH` = lệch, kèm giá trị đúng):

| Quan he | grader_a | grader_b | grader_c | lab8_metrics |
|---|---|---|---|---|
| duplicated_list_keeps_rates_doubles_totals | LECH pass_5: 0 (dung: 0.6667); cost_per_success_vnd: 26.28 (dung: 31.5); total_simulated_cost_vnd: 473 (dung: 567) | LECH pass_5: 0 (dung: 0.6667) | LECH pass_5: 0 (dung: 0.6667) | LECH pass_5: 0 (dung: 0.6667) |
| infra_errors_do_not_move_pass_rate | dat | dat | LECH pass_rate: 0.5625 (dung: 0.75); pass_5: 0.5 (dung: 0.6667); seed_pass_rates: {11: 0.625, 22: 0.5} (dung: {11: 0.8333, 22: 0.6667}); graded_trials: 16 (dung: 12) | LECH pass_rate: 0.5625 (dung: 0.75); pass_5: 0.5 (dung: 0.6667); seed_pass_rates: {11: 0.625, 22: 0.5} (dung: {11: 0.8333, 22: 0.6667}); graded_trials: 16 (dung: 12) |
| NEW_trial_order_does_not_matter | LECH cost_per_success_vnd: 31.67 (dung: 31.5); total_simulated_cost_vnd: 285 (dung: 283.5); cost_per_success_vnd: 31.78 (dung: 31.5); total_simulated_cost_vnd: 286 (dung: 283.5) | dat | dat | dat |
| extra_other_shape_does_not_leak | dat | dat | dat | dat |
| extra_flip_one_fail_to_pass | dat | dat | dat | dat |
| extra_drop_seed_row_lowers_pass5 | dat | dat | dat | dat |
| extra_relabel_seeds_and_claims | dat | dat | dat | dat |
| extra_oracle_docs_metrics | LECH total_simulated_cost_vnd: 90 (dung: 60); cost_per_success_vnd: 30 (dung: 20) | dat | LECH graded_trials: 5 (dung: 4); pass_rate: 0.6 (dung: 0.75); seed_pass_rates: {11: 0.3333, 22: 1} (dung: {11: 0.5, 22: 1}); seed_variance: 0.1111 (dung: 0.0625); seed_min: 0.3333 (dung: 0.5); pass_5: 0.3333 (dung: 0.5); total_simulated_cost_vnd: 65 (dung: 60); cost_per_success_vnd: 21.67 (dung: 20); mean_steps: 4.2 (dung: 5) | (giống grader_c) |
| delay_days_2_vs_3 (quote, không qua summarize) | dat (chung cho mọi bản) | | | |

Các lỗi, gọi tên bằng hành vi:

| Bản | Lỗi | Fixture làm lệch | Độ lệch |
|---|---|---|---|
| grader_a | Cộng thêm một lần cost của trial được chấm đầu tiên gặp ở mỗi claim | duplicate, quan hệ mới, oracle | Tổng cost 473 thay vì 567 khi nhân đôi; 285 hoặc 286 thay vì 283.5 khi đảo thứ tự; cost/success 30 thay vì 20 trên oracle (+50%) |
| grader_c | Tính trial hạ tầng là fail và đưa vào mẫu số | infra, oracle | Pass rate 0.5625 thay vì 0.75 (−0.19); graded 16 thay vì 12 |
| lab8.metrics (bản gốc, cả ba bản dùng lại) | `pass_5` đếm số dòng (`len(claim_rows) == len(seeds)`) thay vì số seed đã phủ | duplicate | `pass_5` 0 thay vì 0.667 khi một cặp (claim, seed) xuất hiện hai lần |
| grader_b | Không thấy lỗi riêng trên các quan hệ đã viết; thừa hưởng lỗi `pass_5` của bản gốc | | |

Quan hệ mới bắt được loại lỗi mà ba quan hệ cũ bỏ sót. Bằng chứng: test `test_new_relation_catches_a_defect_the_three_given_relations_miss` gài một grader lấy `seed_min`/`seed_max` theo seed gặp đầu tiên và cuối cùng. Grader này chỉ lệch `pass_5` (lỗi chung của bản gốc) ở quan hệ nhân đôi, qua quan hệ hạ tầng, nhưng lệch `seed_min` và `seed_max` khi đảo thứ tự. Trên ba bản a, b, c, quan hệ mới không phát hiện thêm bản nào sai. Nó cho thấy lỗi của grader_a là lỗi phụ thuộc thứ tự, không chỉ là lỗi khi nhân đôi.

## Kết luận

Ủng hộ claim, trong phạm vi fixture. Cùng một danh sách trial, ba bản grader cho pass rate khác nhau (0.75 so với 0.5625) và cost khác nhau (283.5 so với 473 hoặc 567). Mức lệch này lớn hơn khoảng cách giữa workflow và swarm trên bộ public (pass rate swarm ≈ 0.986, theo `docs/metrics.md`), nên đủ để đổi kết luận chọn shape. Không có test nào của lab bắt được các lỗi này nếu không viết quan hệ metamorphic.

Một lỗi thước đo vẫn có thể lọt qua mọi quan hệ metamorphic đã viết: lỗi nào không đổi dưới mọi phép biến đổi đều lọt. Ví dụ: tính variance chia N−1 thay vì N vẫn qua quan hệ nhân đôi, đảo thứ tự và đổi tên, vì số seed không đổi. Vì vậy nhóm thêm một bộ 5 trial có đáp án tính tay theo `docs/metrics.md` (oracle). Quan hệ metamorphic hữu ích vì không cần biết pass rate hay số tiền đúng tuyệt đối, chỉ cần biết output phải đổi (hoặc không đổi) thế nào khi input đổi. Oracle bổ sung cho những lỗi mà phép biến đổi không chạm tới.

Điều kiện làm kết luận đảo ngược:
- Benchmark thật của lab (`lab8/benchmark.py`) không có cờ `infra_error`: shape ném exception thì trial bị ghi là fail, giống cách grader_c làm. Khi không có trial hạ tầng, grader_b và grader_c cho cùng kết quả; chỉ grader_a còn lệch cost.
- Lỗi `pass_5` chỉ xuất hiện khi một cặp (claim, seed) bị chạy lặp, ví dụ retry hay gộp hai lần chạy. Lab chạy mỗi cặp đúng một lần, nên lỗi này không làm sai `reports/benchmark.json` hiện tại. Nó là lỗi theo quan hệ README phát biểu (tỉ lệ không đổi khi nhân đôi), chặt hơn định nghĩa trong `docs/metrics.md`. Cách sửa khi có retry: so tập seed đã phủ với tập seed, không so số dòng.

## Giới hạn

- MockLLM không phải model sản xuất; latency là `unavailable`. Phần này không đo shape nên không phụ thuộc MockLLM, nhưng không nói gì về grader chạy trên model thật.
- Fixture nhỏ (một shape, hai seed, 12 đến 16 trial). Độ lệch đo được là của fixture này, không phải ước lượng cho bộ hidden 40 × 5.
- Oracle có hai chỗ diễn giải, ghi trong `bonus/oracle_trials.json`: không tính cost của trial hạ tầng (60, không phải 65), và không đếm claim chỉ có trial hạ tầng vào mẫu số `pass_5`. Các ô cost và `pass_5` của grader_c trên oracle phụ thuộc hai lựa chọn này; ô pass rate thì không.
- Ba bản grader là bản giảng viên dựng sẵn để kiểm toán. Kết luận "lệch" ở đây là lệch so với quan hệ trong `grader_audit/README.md`, không phải so với một grader production.
