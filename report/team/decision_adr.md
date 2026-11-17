# Decision record

Điền sau dấu `:` trên cùng dòng, không xóa nhãn. Giảng viên và `python -m lab8.check_submission` (chạy trong `src/`) đọc các dòng này bằng máy. Không đổi tên hay dời file này khỏi `report/team/`.
`Shape chọn` phải là đúng một trong: `workflow`, `single`, `orchestrator`, `swarm`. Đây là shape được chấm cổng hidden.

- Shape chọn: workflow
- Commit hash: 161f109
- Run id dẫn chứng: R-workflow-C-002-s55 (đối chiếu R-swarm-C-002-s55), R-workflow-C-014-s11; toàn bộ 70 trial R-workflow-* trong src/reports/benchmark.json
- Pass rate / pass^5 / seed min-max / variance: 1.000 (70/70) / 1.000 / 1.000-1.000 / 0.000 (src/reports/benchmark.json)
- Cost per success (mô phỏng, VND): 27.86 (tổng 1950 / 70 trial pass)
- Crash safety: 20/20 (src/reports/crash.json)
- Secret leak / approval bypass: 0 / 0 trên bộ public (test nhóm quét trace và ledger của cả 3 shape); hidden chưa có số

Ví dụ một dòng đã điền: `- Shape chọn: workflow`, `- Crash safety: 20/20 (src/reports/crash.json)`.

## Vì sao shape này

Cùng 14 claim public, cùng 5 seed `11,22,33,44,55`, cùng MockLLM và bảng giá, ba shape nhóm viết đều đạt pass rate 1.000, pass^5 1.000 và variance 0. Swarm đạt 0.986 / 0.929 vì trượt `C-002` ở seed 55 (tin số ngày trong ticket). Khi chất lượng bằng nhau, nhóm chọn shape ít tự chủ nhất: workflow không gọi model lần nào (`mean_model_calls` 0), cost/success 27.86 VND, thấp hơn single (32.99), swarm (49.57) và orchestrator (56.72). Với workflow, mọi quyết định tiền nằm trong code có thể đọc và test được; model không có chỗ nào để tin chữ trong ticket.

## Có đáng đổi lấy multi-agent không

Không, trên dữ liệu hiện có. Orchestrator tốn gấp khoảng 2 lần workflow mà không tăng pass rate. Swarm vừa đắt hơn khoảng 1,8 lần vừa có variance khác 0. Quyết định sẽ đảo lại nếu:

- Có claim mà bước cố định không xử lý được, ví dụ ticket phải đọc hiểu để biết loại yêu cầu trước khi tra đơn. Khi đó single hoặc orchestrator đáng thêm chi phí, miễn tiền vẫn do code tính.
- Các bước tra cứu độc lập và chậm thật (gọi hệ thống ngoài), lúc đó chạy investigator song song có thể rút ngắn thời gian. MockLLM không đo latency nên bộ public không trả lời được câu này.
- Bộ hidden cho thấy workflow dưới 0.75 ở một nhóm claim mà shape khác vượt qua.

## Trace và bằng chứng

Trace workflow ghi 5 loại event: `claim` (claim_id và có order_id hay không), `lookup_order` (visible, reason), `quote` (số tiền, reason, clause_ids), `issue_refund` (ok, reason) và `decision` (status, proposal_amount, reason). Khi crash, trace ghi thêm `crash` rồi mới ném lỗi tiếp.

Cố ý không ghi: nội dung ticket (có thể chứa SĐT, số tài khoản hoặc câu lệnh lừa), claim row (có `parent_secret` và header), order row (có SĐT, địa chỉ, ghi chú nội bộ, tên hàng). Trace chỉ chứa field nhóm tự chọn, không chép kết quả tool nguyên khối. Test `tests/test_workflow_group.py` và `tests/test_trace_safety_group.py` quét trace của cả 3 shape để tìm secret, SĐT, địa chỉ, ghi chú nội bộ và nội dung ticket.

Nếu trace nằm ngoài chỗ scanner quét được, đội security không chứng minh được hệ thống sạch. Vì vậy workflow chỉ ghi qua `lab8.trace.Trace` vào `traces/<run_id>.json`, không `print` dữ liệu khách ra stdout và không ghi file phụ nào khác.

## Giới hạn

MockLLM không phải model sản xuất, nên kết quả của single và orchestrator không nói được model thật sẽ làm gì. Latency để `unavailable`. Bộ public chỉ có 14 claim và đã biết nhãn; chưa có số trên bộ hidden 40 × 5. Số trong file này đọc từ JSON do `lab8.benchmark` và `lab8.crash_test` sinh ra, không sửa tay.
