# Search examples

Measured results from the persistent corpus index. Correctness is judged against the expected source document and page in `eval/questions.json`; the final query is intentionally off-topic.

| Example query | Retrieved document and page | Similarity | Result |
|---|---|---:|---|
| What kind of application code is asyncio described as a good fit for? | python_asyncio.txt, page 1 | 0.693 | Correct |
| Why should an application limit the size of untrusted JSON input? | python_json.docx, page 1 | 0.522 | Correct |
| How do pure paths differ from concrete paths? | python_pathlib.docx, page 1 | 0.464 | Correct |
| When does Python raise an exception, and are exceptions always fatal? | python_errors_exceptions.txt, page 1 | 0.702 | Correct |
| How do the tutorial's stack and queue examples differ? | python_data_structures.txt, page 1 | 0.497 | Correct |
| What kinds of command-line arguments can ArgumentParser.add_argument() describe? | python_argparse.pdf, page 19 | 0.740 | Partial |
| What logger pattern does the logging example recommend using in each module? | python_logging.pdf, page 3 | 0.775 | Correct |
| Which string method requires you to supply the values to be formatted, using { and } as replacement fields? | python_input_output.pdf, page 6 | 0.567 | Partial |
| How do I configure Kubernetes horizontal pod autoscaling for production? | No relevant result | — | Weak match |
