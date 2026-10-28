# Dataset and evaluation guidance

## Dataset policy

Use real public code/configuration sources with permission-compatible licenses. Pin repository URLs and commit IDs. Record collection date, selected file types, exclusions, license, label schema, and split strategy. Do not commit raw third-party datasets unless redistribution is allowed; provide reproducible source references instead.

Keep generated examples under a visibly synthetic fixture directory. Synthetic fixtures are useful for deterministic positive/negative behavior but must not be included in real-data precision/recall denominators.

If using a benchmark such as CryptoAPI-Bench, state its language and task accurately. A Java API-misuse benchmark does not validate a Python detector or prove discovery quality in a banking estate.

## Labels and metrics

Record presence, evidence location, operation/purpose, algorithm family only when supported, active/test/generated status, migration relevance, confidence, and rationale. Define the metric unit before evaluation (for example, labelled instances rather than raw regex matches).

For TP=true positive, FP=false positive, FN=false negative:

- Precision = TP / (TP + FP)
- Recall = TP / (TP + FN)

Show counts, dataset size, supported languages, and limitations. Split by repository/project to avoid near-duplicate leakage. Never copy paper scores into CryptoShift results or invent missing labels/results.