# Chunking experiments

Evaluated 18 configurations using 25 answerable evaluation questions and top-5 retrieval. Hit, precision, recall, and MRR use the expected document and page(s); mean chunk length and count are measured from the indexed corpus.

| Strategy | Size | Overlap | Chunks | Avg. chars | Hit@5 | Precision@5 | Recall@5 | MRR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| recursive | 300 | 0 | 1208 | 234.9 | 0.880 | 0.640 | 0.880 | 0.821 |
| recursive | 300 | 120 | 1519 | 248.8 | 0.920 | 0.696 | 0.900 | 0.868 |
| recursive | 800 | 0 | 454 | 626.8 | 0.880 | 0.632 | 0.860 | 0.840 |
| recursive | 800 | 120 | 477 | 645.4 | 0.880 | 0.664 | 0.860 | 0.853 |
| recursive | 1500 | 0 | 238 | 1196.5 | 0.920 | 0.632 | 0.900 | 0.890 |
| recursive | 1500 | 120 | 244 | 1203.8 | 0.920 | 0.616 | 0.900 | 0.890 |
| sentence | 300 | 0 | 1198 | 236.6 | 0.880 | 0.672 | 0.880 | 0.801 |
| sentence | 300 | 120 | 1576 | 252.2 | 0.880 | 0.688 | 0.860 | 0.833 |
| sentence | 800 | 0 | 450 | 632.2 | 0.920 | 0.656 | 0.900 | 0.847 |
| sentence | 800 | 120 | 487 | 660.8 | 0.920 | 0.656 | 0.900 | 0.823 |
| sentence | 1500 | 0 | 238 | 1196.5 | 0.920 | 0.632 | 0.900 | 0.890 |
| sentence | 1500 | 120 | 244 | 1204.8 | 0.920 | 0.600 | 0.900 | 0.890 |
| section | 300 | 0 | 1250 | 227.0 | 0.880 | 0.656 | 0.880 | 0.821 |
| section | 300 | 120 | 1521 | 242.0 | 0.920 | 0.688 | 0.900 | 0.861 |
| section | 800 | 0 | 516 | 551.3 | 0.880 | 0.664 | 0.860 | 0.860 |
| section | 800 | 120 | 530 | 571.2 | 0.880 | 0.632 | 0.860 | 0.853 |
| section | 1500 | 0 | 305 | 933.2 | 0.920 | 0.616 | 0.900 | 0.890 |
| section | 1500 | 120 | 308 | 939.8 | 0.920 | 0.608 | 0.900 | 0.890 |

## Selected configuration

**recursive**, chunk size **1500**, overlap **0**. The selection maximizes MRR, then recall, hit rate, and precision; ties prefer fewer chunks.

## Observed misses and trade-offs

- `recursive`, size 300, overlap 0: Hit@5 0.880, MRR 0.821, 1208 chunks averaging 234.9 chars. Observed misses: q-022 expected python_argparse.pdf p.2, got python_argparse.pdf p.18; q-023 expected python_argparse.pdf p.2, got python_argparse.pdf p.64; q-024 expected python_argparse.pdf p.3, got python_argparse.pdf p.5
- `recursive`, size 300, overlap 120: Hit@5 0.920, MRR 0.868, 1519 chunks averaging 248.8 chars. Observed misses: q-022 expected python_argparse.pdf p.2, got python_argparse.pdf p.50; q-023 expected python_argparse.pdf p.2, got python_argparse.pdf p.62
- `recursive`, size 800, overlap 0: Hit@5 0.880, MRR 0.840, 454 chunks averaging 626.8 chars. Observed misses: q-022 expected python_argparse.pdf p.2, got python_argparse.pdf p.15; q-023 expected python_argparse.pdf p.2, got python_argparse.pdf p.62; q-028 expected python_input_output.pdf p.2, got python_input_output.pdf p.6
- `recursive`, size 800, overlap 120: Hit@5 0.880, MRR 0.853, 477 chunks averaging 645.4 chars. Observed misses: q-022 expected python_argparse.pdf p.2, got python_argparse.pdf p.19; q-023 expected python_argparse.pdf p.2, got python_argparse.pdf p.62; q-028 expected python_input_output.pdf p.2, got python_input_output.pdf p.6
- `recursive`, size 1500, overlap 120: Hit@5 0.920, MRR 0.890, 244 chunks averaging 1203.8 chars. Observed misses: q-022 expected python_argparse.pdf p.2, got python_argparse.pdf p.20; q-023 expected python_argparse.pdf p.2, got python_argparse.pdf p.39
- `sentence`, size 300, overlap 0: Hit@5 0.880, MRR 0.801, 1198 chunks averaging 236.6 chars. Observed misses: q-022 expected python_argparse.pdf p.2, got python_argparse.pdf p.18; q-023 expected python_argparse.pdf p.2, got python_argparse.pdf p.44; q-024 expected python_argparse.pdf p.3, got python_argparse.pdf p.5
- `sentence`, size 300, overlap 120: Hit@5 0.880, MRR 0.833, 1576 chunks averaging 252.2 chars. Observed misses: q-022 expected python_argparse.pdf p.2, got python_argparse.pdf p.50; q-023 expected python_argparse.pdf p.2, got python_argparse.pdf p.62; q-024 expected python_argparse.pdf p.3, got python_argparse.pdf p.5
- `sentence`, size 800, overlap 0: Hit@5 0.920, MRR 0.847, 450 chunks averaging 632.2 chars. Observed misses: q-023 expected python_argparse.pdf p.2, got python_argparse.pdf p.62; q-028 expected python_input_output.pdf p.2, got python_input_output.pdf p.6
- `sentence`, size 800, overlap 120: Hit@5 0.920, MRR 0.823, 487 chunks averaging 660.8 chars. Observed misses: q-023 expected python_argparse.pdf p.2, got python_argparse.pdf p.62; q-028 expected python_input_output.pdf p.2, got python_input_output.pdf p.6
- `sentence`, size 1500, overlap 0: Hit@5 0.920, MRR 0.890, 238 chunks averaging 1196.5 chars. Observed misses: q-022 expected python_argparse.pdf p.2, got python_argparse.pdf p.20; q-023 expected python_argparse.pdf p.2, got python_argparse.pdf p.39
- `sentence`, size 1500, overlap 120: Hit@5 0.920, MRR 0.890, 244 chunks averaging 1204.8 chars. Observed misses: q-022 expected python_argparse.pdf p.2, got python_argparse.pdf p.20; q-023 expected python_argparse.pdf p.2, got python_argparse.pdf p.39
- `section`, size 300, overlap 0: Hit@5 0.880, MRR 0.821, 1250 chunks averaging 227.0 chars. Observed misses: q-022 expected python_argparse.pdf p.2, got python_argparse.pdf p.18; q-023 expected python_argparse.pdf p.2, got python_argparse.pdf p.64; q-024 expected python_argparse.pdf p.3, got python_argparse.pdf p.5
- `section`, size 300, overlap 120: Hit@5 0.920, MRR 0.861, 1521 chunks averaging 242.0 chars. Observed misses: q-022 expected python_argparse.pdf p.2, got python_argparse.pdf p.50; q-023 expected python_argparse.pdf p.2, got python_argparse.pdf p.62
- `section`, size 800, overlap 0: Hit@5 0.880, MRR 0.860, 516 chunks averaging 551.3 chars. Observed misses: q-022 expected python_argparse.pdf p.2, got python_argparse.pdf p.15; q-023 expected python_argparse.pdf p.2, got python_argparse.pdf p.62; q-028 expected python_input_output.pdf p.2, got python_input_output.pdf p.6
- `section`, size 800, overlap 120: Hit@5 0.880, MRR 0.853, 530 chunks averaging 571.2 chars. Observed misses: q-022 expected python_argparse.pdf p.2, got python_argparse.pdf p.19; q-023 expected python_argparse.pdf p.2, got python_argparse.pdf p.62; q-028 expected python_input_output.pdf p.2, got python_input_output.pdf p.6
- `section`, size 1500, overlap 0: Hit@5 0.920, MRR 0.890, 305 chunks averaging 933.2 chars. Observed misses: q-022 expected python_argparse.pdf p.2, got python_argparse.pdf p.20; q-023 expected python_argparse.pdf p.2, got python_argparse.pdf p.39
- `section`, size 1500, overlap 120: Hit@5 0.920, MRR 0.890, 308 chunks averaging 939.8 chars. Observed misses: q-022 expected python_argparse.pdf p.2, got python_argparse.pdf p.20; q-023 expected python_argparse.pdf p.2, got python_argparse.pdf p.39

The miss descriptions name the actual expected and retrieved document/page for each failed top-5 match; they are evidence for the observed trade-offs, rather than assumptions based only on configured chunk size.
