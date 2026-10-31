# Gemini API pricing used by evaluation

Checked **2026-10-31** against Google's [Gemini Developer API pricing page](https://ai.google.dev/gemini-api/docs/pricing), Gemini 3.8 Flash Standard tier:

| Token type | Paid-tier price per 1 million tokens through 2026-12-31 |
|---|---:|
| Input | $0.75 USD |
| Output (including thinking tokens) | $3.75 USD |

The evaluator reports the **estimated paid-tier list cost**. It is not the account's actual bill: free-tier eligibility, billing tier, discounts, and other account-specific adjustments are unknown. Gemini response `usageMetadata` is used when available. If a test double or provider response omits usage, the output records a rough token estimate from prompt/answer character counts (4 characters per token) and labels the estimate source.

Pricing is versioned by date in `eval/run_eval.py`; refresh this source and the rates when the model's published price changes.

The evaluator excludes BLEU/ROUGE as standalone factuality metrics and does not use a second LLM judge. It reports transparent lexical key-fact coverage as a screening proxy and leaves final semantic answer review to humans. Actual billed cost is excluded because it depends on account-specific billing information unavailable to this project.
