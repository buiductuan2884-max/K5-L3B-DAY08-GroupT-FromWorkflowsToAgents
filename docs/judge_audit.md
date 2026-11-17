# Judge audit

Nguồn: hai CSV replay chính thức trong src/data/eval; FAIL là lớp dương. Cột human là nhãn có sẵn. Phân tích đối chiếu reply và ghi chú rubric của CSV, không phải một vòng gán nhãn mới được con người xác nhận. Nhãn và ngưỡng giữ nguyên.

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Có | Có thể dùng cho tone trong phạm vi replay |
| helpful | 100 | 0.375 | 1.000 | 0.300 | Không | Loại khỏi gate |

| Judge | FAIL→FAIL (TP) | PASS→FAIL (FP) | FAIL→PASS (FN) | PASS→PASS (TN) |
|---|---|---|---|---|
| tone_ok | 24 | 4 | 6 | 66 |
| helpful | 9 | 0 | 21 | 70 |

Tone: specificity=66/70, observed fail rate=0.28, Rogan–Gladen corrected=0.30. Helpful: specificity=1, observed=0.09, corrected=0.30. Hiệu chỉnh prevalence không chữa được recall thấp.

## Audit bất đồng từ dữ liệu replay

| # | Case | Judge nói | Nhãn human | Ai đúng theo rubric/bằng chứng? | Hành động sửa rubric/cách chấm |
|---|---|---|---|---|---|
| 1 | H-008 | PASS | FAIL | Human phù hợp: “Em… nha… check” quá suồng sã theo ngữ cảnh CSKH trong CSV. | Thêm ví dụ âm về xưng hô; thân thiện không tự động đạt. |
| 2 | H-017 | PASS | FAIL | Human phù hợp: “bạn ơi… rồi nha” sai xưng hô theo ghi chú khách lớn tuổi. | Cung cấp ngữ cảnh đối tượng, tránh chỉ nhìn từ Dạ. |
| 3 | H-029 | PASS | FAIL | Human phù hợp: “không cần nhắn thêm” mang tính ra lệnh. | Chấm toàn câu và quyền phản hồi của khách. |
| 4 | H-042 | FAIL | PASS | Human phù hợp: câu ngắn đủ số tiền, thời gian và kính ngữ; không bắt buộc xin lỗi ở mọi thông báo. | Bỏ tiêu chí luôn phải xin lỗi; không thưởng độ dài. |
| 5 | H-051 | FAIL | PASS | Human phù hợp: CSV cho phép từ refund, câu vẫn lịch sự. | Ghi rõ từ vay mượn được phép, thêm ví dụ dương. |
| 6 | H-063 | PASS | FAIL | Human phù hợp: hứa sẽ hoàn thêm ngoài kết quả hệ thống. | Tách độ đúng của cam kết khỏi tone; so ledger/approval bằng code. |
| 7 | H-070 | PASS | FAIL | Human phù hợp: emoji cười trong khiếu nại trái quy tắc ngữ cảnh CSV. | Thêm ví dụ âm cho emoji. |
| 8 | H-081 | FAIL | PASS | Ghi chú CSV nói nhãn human sai do đọc nhầm ticket, nhưng không có ticket để xác minh độc lập. Chưa kết luận lại được từ tone đơn thuần. | Cần ngữ cảnh và nhãn mới; giữ nguyên dữ liệu hiện tại. |
| 9 | HL-015 | PASS | FAIL | Human phù hợp: reply 55.000đ, ghi chú ledger 40.000đ. | Grader tiền bằng code; tách helpful khỏi lịch sự. |
| 10 | HL-016 | PASS | FAIL | Human phù hợp: xin lỗi dài che số tiền 55.000đ, ghi chú ledger 35.000đ. | Không dùng độ dài/đồng cảm thay độ đúng; đối chiếu effect bằng FM-08. |

## Kết luận

Tone đạt cả ba sàn nhưng bỏ sót 6/30 lỗi và báo nhầm 4/70 câu tốt. Helpful bỏ sót 21/30 lỗi (70%), nên không dùng làm gate. Cấu hình hiện tại dùng code cho tiền/phê duyệt, không dùng judge replay để quyết định hoàn tiền.

Kappa không xác định bị từ chối; precision/recall có mẫu số 0 trả 0; Rogan–Gladen yêu cầu tỷ lệ hợp lệ và sensitivity+specificity>1. Replay công khai chỉ có 100 dòng mỗi tiêu chí, có nguy cơ chọn rubric theo dữ liệu đã biết. Cần held-out, ngữ cảnh đầy đủ và nhãn người mới trước khi suy rộng.

```powershell
cd src
python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 10
python -m lab9.judge --csv data/eval/judge_helpful_public.csv --audit 10
```

Tone trả exit 0; helpful trả exit 1 đúng yêu cầu calibration.
