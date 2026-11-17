# Research card

File này nằm cố định ở `report/team/research_card.md`; `python -m lab8.check_submission` đọc cột "Nhóm điền" bằng máy.

Phần này nối tiếp phần mini research ở buổi lý thuyết (slide 62–63). Chọn **một** câu R1–R4, điền 6 dòng, rồi biến nó thành **một ablation** chạy được trong lab: giữ nguyên model (MockLLM), tool, seed, corpus và giá, chỉ thay đổi một biến.

| Câu | Nguồn (thư viện tham khảo, slide 68–69) | Câu hỏi gợi ý cho lab |
| --- | --- | --- |
| R1 · Scaling | Google Research 2026, *Towards a Science of Scaling Agent Systems* | Task claims chủ yếu tuần tự hay song song được? Dự đoán thêm investigator sẽ làm pass rate và cost/success thay đổi thế nào. |
| R2 · Failure taxonomy | MAST, NeurIPS 2025, *Why Do Multi-Agent LLM Systems Fail?* | Các trial fail của swarm (seed 55) thuộc nhóm nào: lỗi giao việc, lệch mục tiêu, hay lỗi kiểm chứng? |
| R3 · Architecture choices | AgentArch, AACL 2026 | Nếu đổi topology mà giữ nguyên mọi thứ khác, biến nào phải cố định để kết luận còn đúng? |
| R4 · Evaluation confounders | EMNLP 2026, *Rethinking Evaluation of MAS Efficiency* | Làm sao chứng minh chênh lệch giữa A/B/C/D là do topology, không phải do prompt, tool hay seed? |

## Phiếu của nhóm

Điền vào cột cuối. Không xóa hai cột đầu.

| Field | Hướng dẫn | Nhóm điền |
| --- | --- | --- |
| CÂU | R1 / R2 / R3 / R4 | R2 — phân loại lỗi kiểm chứng của swarm, đối chiếu độ tin cậy và cost/success với workflow. |
| SOURCE | Paper/blog, năm, URL, loại bằng chứng (benchmark, production report, blog kinh nghiệm) | Mert Cemri và cộng sự, *Why Do Multi-Agent LLM Systems Fail?*, NeurIPS 2025, Datasets and Benchmarks Track. [Proceedings chính thức](https://proceedings.neurips.cc/paper_files/paper/2025/hash/b1041e52d3be19f0a9bc491657488e4a-Abstract-Datasets_and_Benchmarks_Track.html); [arXiv:2503.13657](https://arxiv.org/abs/2503.13657). Bằng chứng: phân tích trace và taxonomy thực nghiệm MAST; đã đối chiếu tiêu đề, tác giả, năm và nội dung abstract. |
| CLAIM | Một kết luận gốc của nguồn. Không viết rộng hơn phạm vi paper | MAST phân loại 14 kiểu lỗi thành ba nhóm: thiết kế hệ thống, lệch phối hợp giữa agent và kiểm chứng task. Phân loại trace giúp xác định chỗ cần cải thiện trong thiết kế MAS. |
| BOUNDARY | Model / dataset / setup giới hạn kết luận đó | Nguồn nghiên cứu nhiều framework/model trên coding, math và general agent; không đánh giá LogiX-VN, MockLLM hay độ an toàn ledger của lab. Gán nhãn lỗi lab dưới đây là diễn giải trong nghiên cứu P4, không phải nhãn do tác giả paper xác nhận. |
| HYPOTHESIS | Nếu đổi shape A→B (hoặc bật/tắt một thành phần), metric X sẽ đổi theo hướng nào, khoảng bao nhiêu | Thay cấu hình swarm bằng workflow trên cùng 70 trial sẽ loại lỗi T02 seed 55: số trial pass tăng 69→70, pass^5 tăng 13/14→14/14, variance về 0 và cost/success giảm. Đây là giả thuyết từ weakness được starter công bố trước khi so sánh; không phải khám phá độc lập. |
| METHOD | Biến giữ cố định: model, tools, seed, corpus, giá, evaluator. Biến duy nhất được thay đổi: … | Factor so sánh là shape; ghép cặp theo claim/seed. Giữ 14 public claim, seeds 11/22/33/44/55, world, as_of 2026-11-15, MockLLM, host, tool registry, pricing và evaluator; SQLite mới mỗi trial. Dùng công cụ benchmark sẵn có, không sửa shape để tạo variant. Đây là ablation cấu hình A/D: prompt, lịch gọi tool/model và nhánh tin ticket thay đổi theo shape, là confounder; không nhận diện riêng tác động nhân quả của topology/số agent. |
| FAILURE / METRIC | Một lỗi dự kiến và cách đo nó: pass rate, pass^5, variance, cost/success, leak, bypass | Đo theo docs/metrics.md: pass rate, pass^5, phương sai tổng thể của 5 seed, min/max, tổng cost và cost/success kể cả trial fail, mean/p95 số event. Lỗi dự kiến là dùng delay trong ticket thay order; phân loại diễn giải là thiếu kiểm chứng task, với nguyên nhân thiết kế REFERENCE_WEAKNESS. Approval và privacy được kiểm bằng test P4 riêng, không suy từ pass rate. |

## Kết quả ablation

- Lệnh đã chạy (trong `src/`, Python 3.13.18 của `.venv`):

  ```text
  python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json
  ```

- Run id / file report: [`src/reports/benchmark.json`](../../src/reports/benchmark.json), 4 × 14 × 5 = 280 trial, code tại commit `21768c53415405fe43f56a46adc8d34406e49faa`. Cặp đối chiếu: `R-workflow-C-002-s55` và `R-swarm-C-002-s55`. JSON không có batch run ID; các ID là định danh trial xác định theo shape/claim/seed, không phải timestamp duy nhất.
- Kết quả so với hypothesis: **ủng hộ trong setup public này**. Workflow pass rate 1, pass^5 1, seed min/max 1/1, variance 0; swarm lần lượt 0.985714286, 0.928571429, 0.928571429/1, 0.000816326531. Cost/success mô phỏng giảm 49.566956522→27.857142857 VND; tổng cost giảm 3420.12→1950 VND. Mean/p95 steps A là 4.428571429/5, D là 2.8/3; số event thấp không đồng nghĩa ít tool/model call.
- Trial fail duy nhất: `R-swarm-C-002-s55`, reason `status resolved != denied`, cost 62.22 VND mô phỏng. Code swarm cố ý lấy delay từ ticket khi seed chia hết cho 5; order thực tế chỉ trễ 2 ngày. Bốn seed còn lại của swarm đều đạt 14/14. Không sửa weakness để nâng điểm.
- Giới hạn: benchmark đối chứng cấu hình có confounder, corpus nhỏ và có nhãn public, weakness được biết trước; không chứng minh workflow luôn tốt hơn MAS. MockLLM không phải model sản xuất, latency là `unavailable`; chưa có hidden score, không kết luận hidden ≥ 0.75.

Muốn đi xa hơn một ablation để lấy điểm cộng thì xem [docs/bonus_topics.md](../../docs/bonus_topics.md).
