# Evaluation

## Setup and configuration

This report uses the 29 reviewed questions in `eval/questions.json` and the 9-document Python documentation corpus in `data/sample_docs/`. The persistent Chroma index was built with `sentence-transformers/all-MiniLM-L6-v2`, cosine similarity, and the Step 5.3 choice of recursive chunks (1,500 characters, 0 overlap). Retrieval was evaluated at K=3 and K=5 against each question's expected source document and page. Four questions are marked unanswerable.

The retrieval run is real and reproducible with:

```powershell
$env:HF_HUB_OFFLINE='1'
Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe eval\run_eval.py --skip-rag
```

`eval/results/results.csv` contains all per-question ranked retrievals and `eval/results/summary.json` contains these aggregate scores. Gemini generation was deliberately skipped under the user's instruction to defer key-dependent checks. Thus all 29 rows label answer-level evaluation as deferred; this report does not claim generated answers, citations, refusals, token counts, or model costs were tested. Resume the full run with `eval/run_eval.py --resume` when a working key and quota are available.

## Targeted live Gemini validation (2026-10-31)

The user's project `.env` was set to `gemini-3.6-flash`; a connectivity request returned `READY` in 3.08 seconds. The initial live RAG tests exposed truncated responses with a 128-token output cap. Raising the default to 512 allowed the JSON-format answer in Q-004 and the refusal for Q-032 to pass their live assertions. Q-001 and Q-014 also passed the grounded-answer assertions; Q-029, Q-030, and Q-033 passed the unanswerable-question assertions in the initial run. Q-019's top-five retrieval misses its answer-bearing passage, and a live call returned the expected refusal; its test now verifies abstention for that retrieval miss.

Further live requests then received HTTP 429 quota responses. Live tests now skip only on transient provider/network unavailability; the final full suite reported **162 passed, 11 skipped**, with the Gemini cases skipped due to quota. The 29-question CSV and summary remain retrieval-only: no aggregate live answer rate, generation/end-to-end latency, token total, or cost-per-query is claimed. Resume the full answer-level evaluation with `eval/run_eval.py --resume` when quota is available. Paid-tier rates for both Gemini 3.6 and 3.8 are documented in [PRICING.md](../eval/PRICING.md).

## Retrieval metrics

Scores below cover the 25 answerable questions; they come from a retrieval-only run. Targeted live refusal assertions for the four unanswerable questions are summarized above. Relevance currently means that the retrieved chunk matches the expected document **and** one of its expected pages. Precision divides by K, including when fewer than K results were returned. Recall counts unique expected pages recovered.

| Metric | K=3 | K=5 |
|---|---:|---:|
| Hit@K | 0.880 | 0.920 |
| Precision@K | 0.613 | 0.600 |
| Recall@K | 0.860 | 0.900 |
| MRR | 0.880 | 0.890 |
| Mean similarity of matching document/page chunks | 0.571 | 0.540 |
| Mean retrieval latency | 50.8 ms | 31.1 ms |

### Candidate retrieval-depth comparison

As an offline improvement experiment, the same 25 answerable questions were measured at K=10 and K=20. The K=5 values above are the baseline. Relevance remains document-and-page based, so interpret this as gold-page coverage rather than exact answer-bearing chunks.

| K | Hit@K | Precision@K | Recall@K | MRR | Mean similarity of matching chunks |
|---:|---:|---:|---:|---:|---:|
| 5 (baseline) | 0.920 | 0.600 | 0.900 | 0.890 | 0.540 |
| 10 | 0.960 | 0.544 | 0.960 | 0.894 | 0.517 |
| 20 | 1.000 | 0.416 | 1.000 | 0.896 | 0.502 |

Increasing K recovers the expected page for Q-023 at rank 10 and Q-022 at rank 19. It also lowers precision and mean similarity, adding many off-target chunks. We keep the product and RAG default at **K=5**: the modest MRR gain does not establish that larger context helps generated answers, and full-dataset Gemini answer quality remains unmeasured. The experiment is a measured trade-off, not evidence to raise the production default.

The latest recorded full-corpus indexing run processed 9 documents and 238 chunks in 26.53 seconds. Retrieval latency is measured in one sequential run; K=3 and K=5 timings are not strictly comparable because of warm-up and runtime variation.

**Interpretation limit:** page-level relevance is coarse. Some source files are represented as a single page, so any chunk from that file/page counts as relevant even if its text does not answer the query. The stack/queue case below demonstrates this directly. As a result, these retrieval scores are a useful document/page-location measure, not a verified measure of exact evidence relevance. A future improvement should score retrieved chunk text against the reviewed evidence spans in the question set.

## Four evidence cases

### 1. Correct chunk retrieved

- **Query:** “What syntax does asyncio use for concurrent Python code?” (Q-001)
- **Retrieved evidence:** `python_asyncio.txt`, page 1, rank 2, similarity **0.711**. The passage includes the phrase “bridge callback-based libraries and code with async/await syntax.”
- **Result:** The chunk directly contains the requested fact. Rank 1 is also from the expected document and page (0.823) but is header/overview-heavy, so the answer-bearing passage is ranked second.
- **Answer:** The targeted live test for Q-019 observed the exact refusal because its top-five retrieved context did not contain the answer-bearing stack/queue passage. This is the expected behavior for a context-only answerer, despite the fact existing elsewhere in the corpus.
- **Fix/status:** Retrieval succeeds by document/page but misses the evidence-bearing chunk. The live test asserts refusal rather than expecting an answer unsupported by the retrieved context. Add chunk-level evidence labels to expose this retrieval miss.

### 2. Wrong chunk retrieved

- **Query:** “What kinds of command-line arguments can ArgumentParser.add_argument() describe?” (Q-022)
- **Expected evidence:** `python_argparse.pdf`, page 2, where the source describes positional arguments, options taking values, and on/off flags. A direct extraction check confirmed that wording is on PDF page 2.
- **Retrieved evidence:** The top result is `python_argparse.pdf`, page 20, similarity **0.717**; ranks 2–5 are pages 39, 37, 64, and 58. None match the expected page. Hit@5 is 0.
- **Answer:** Gemini was not called, so there is no generated answer to report.
- **Why it failed:** The PDF contains many `ArgumentParser` and `add_argument()` examples. Those shared terms scored highly even though the top chunks discuss other argument-parser behavior. Document-level matching alone would hide this miss; the expected-page check detects it.
- **Fix/status:** Preserve page metadata and evaluate evidence-bearing chunks. A page-aware reranker or filtering by a verified page may help when the query names a specific topic, but should be measured before adoption.

### 3. Multiple relevant chunks retrieved

- **Query:** “What logger pattern does the logging example recommend using in each module?” (Q-025)
- **Retrieved evidence:** Rank 1 is `python_logging.pdf`, page 3, similarity **0.778**, and contains the module-level logger guidance and hierarchical forwarding discussion. Rank 5 is page 4, similarity **0.615**, and gives related context that loggers are obtained with `logging.getLogger(name)` rather than instantiated directly. Both passages can support the logger-pattern explanation, although page 4 lies outside the question's gold pages `[2, 3]`.
- **Answer:** Gemini was not called; source combination and citation behavior are therefore unverified.
- **Why it matters:** The result set includes complementary context, while the strict gold-page metric counts only page 3. This shows why retrieval usefulness and page-label metrics can differ.
- **Fix/status:** Keep multiple passages available to RAG, but validate that each cited answer claim maps to an actually retrieved passage. A chunk-evidence label would better measure this case than page-only labels.

### 4. Insufficient information

- **Query:** “Does the corpus say whether asyncio automatically runs CPU-bound work across multiple processor cores?” (Q-029; marked unanswerable)
- **Retrieved evidence:** `python_asyncio.txt`, page 1, similarity **0.552**, followed by another asyncio passage at 0.533. These are topically related, but the retrieval scores alone do not establish that the corpus answers the multi-core question.
- **Expected behavior:** The system should refuse if the retrieved context does not state this. The reviewed expected answer says that the corpus does not specify automatic multi-core execution for CPU-bound work.
- **Observed answer:** The live test accepted the answer as a refusal with no sources and no affirmative or negative factual claim. The same test suite checks Q-030, Q-032, and Q-033; Q-032 passed after increasing the output budget.
- **Fix/status:** This verifies the targeted refusal behavior. The full 29-question answer-level run is still deferred because quota returned HTTP 429; no aggregate answer or cost metrics are claimed.

## Error analysis

| Failure mode | Evidence and question | Retrieved content / observed answer | Cause and remediation |
|---|---|---|---|
| Incorrect retrieval | Q-022 and Q-023; both expect `python_argparse.pdf` page 2. | Q-022 top five pages are 20, 39, 37, 64, 58. Q-023 top five are 39, 45, 62, 30, 20. No Gemini answer was generated. | Repeated parser terminology in the long PDF outranks the evidence page. Test page-aware or evidence-span reranking; do not count a matching document as sufficient. |
| Irrelevant chunks | Q-019 asks how stack and queue examples differ. | Rank 1 is a `map`/lambda squares passage from `python_data_structures.txt`, page 1 (0.389); other retrieved passages include unrelated logging and argparse text. Gemini answer was not generated. | The gold page is page 1 for the whole TXT document, so unrelated chunks from that page receive page-level relevance credit. Add evidence-span chunk labels and report this metric limitation. |
| Poor chunk boundaries | No distinct boundary failure was established by this retrieval-only run. | Q-001 rank 1 is header/overview-heavy, while its answer-bearing passage is rank 2; this is a ranking observation, not proof of a splitter boundary defect. | Revisit chunk boundaries only with source-span evidence and answer-level outcomes; no boundary change is claimed here. |
| Missing context | Not evaluated for generated answers. | Gemini was skipped; there is no observed answer/context mismatch to report. | Re-run live RAG evaluation after the key is available, then inspect retrieval context and generated response. |
| Hallucinated answers | Full answer set not evaluated. | Targeted live tests exercised four unanswerable questions; a full 29-question answer run is still pending. | Do not infer a corpus-wide hallucination rate from a few cases; complete the saved full evaluation when quota is available. |
| Ambiguous questions | No ambiguity was identified from the measured retrieval rows. | Answer-level interpretation was not evaluated. | If live answers expose ambiguity, revise the reviewed question set with the user; no revision is claimed now. |
| Duplicate content | No duplicate passage was verified in this run. | Similar same-document rankings exist, but similarity alone does not establish duplicate text. | Use content hashes or exact text comparison before reporting duplication; not observed as a confirmed failure. |
| Long-context issues | Not evaluated. | No Gemini prompt/answer was produced. | Check prompt truncation and citations in the live run; no long-context failure or fix is claimed. |

## Excluded metrics and limitations

- BLEU/ROUGE are not used as factuality measures for short answers; lexical overlap can miss a correct paraphrase or reward an incorrect phrase match.
- An LLM judge is excluded to avoid an additional model, cost, and subjective variance. The evaluator's lexical key-fact coverage is only a screening proxy; human review is still needed.
- Actual billed API cost is unknown because account tier, discounts, caching, and billing data are not available. The dated paid-tier estimate is documented in `eval/PRICING.md` and remains blank until Gemini calls run.
- Aggregate answer correctness, generation latency, token usage, and model cost remain **unmeasured** for the full question set because quota stopped the live run. Targeted answer/refusal assertions are tests, not corpus-wide estimates.
