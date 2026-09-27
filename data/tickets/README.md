# Ticket routing data (milestone M5, interview Stage 11)

The HR assistant opens a ticket when it can't answer. Each ticket must reach the right queue. Stage 11 of the interview mock is the "when not to use an LLM" story: compare LLM prompting with classic ML and fine-tuned small models on this routing task.

There are no real HR tickets for a fictional company, so this milestone uses a public dataset. It is not stored in this repo. Download it yourself.

## Dataset

| Item | Value (from the dataset card; check it when you download) |
|---|---|
| Name | `Tobi-Bueck/customer-support-tickets` on Hugging Face |
| Licence | CC BY-NC 4.0: non-commercial use, attribution required. A personal portfolio is fine; credit the author in your README. |
| Size | About 61,765 tickets |
| Fields | subject, body, answer, type, queue, priority, language, tags |
| Label | `queue` (10 queues, including "Human Resources", "IT Support" and "Billing and Payments") |
| Languages | English and German |
| Nature | Synthetic (generated), so there is no real personal data and no real label noise |

A smaller, rebalanced derivative also exists: `ale-dp/bilingual-ticket-classification` (about 7,900 rows, same licence).

```python
from datasets import load_dataset
ds = load_dataset("Tobi-Bueck/customer-support-tickets")   # check the split names it returns
```

## How to use it honestly

- **No timestamps.** You can't do the time-based split the mock recommends. Use a stratified, seeded split (70/15/15) and say why in the interview: a random split can leak future patterns, which is why you'd split by time on real tickets.
- **A shift test instead:** train on English only and test on German, and the reverse. This shows how a model degrades under distribution shift, which is the real reason for time-based splits.
- **Synthetic data flatters models.** Expect higher scores than on real tickets. Say so.
- **Class imbalance:** report macro-F1 and a confusion matrix, not accuracy.

## What to compare (all on the same test split)

1. Majority-class baseline
2. TF-IDF + logistic regression (scikit-learn)
3. SetFit with 8, 16 and 64 labelled examples per class
4. A fine-tuned small multilingual encoder
5. Zero-shot and few-shot LLM prompting, run on a fixed sample of 500 test tickets to control cost

Record for each: macro-F1, per-queue F1, latency per ticket on CPU, and cost per 1,000 tickets. Optional: a LoRA fine-tune of a small open model for the same task, to practise the fine-tuning vocabulary in Stage 11.
