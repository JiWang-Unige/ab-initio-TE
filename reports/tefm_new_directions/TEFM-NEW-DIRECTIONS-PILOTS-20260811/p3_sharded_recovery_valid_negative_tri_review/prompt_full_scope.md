You are an independent post-run reviewer. Review this claim-ineligible CPU identity-recovery result and recommend exactly one next decision. Do not edit files or run compute.

Research sequence: before training a direct RepeatMasker-superfamily S0 baseline, the project needs leakage-safe family/homology components. Direct RepeatMasker labels remain prediction truth; homology is split-only and cannot relabel examples. GPU S0 and hierarchical/open-set S1 remain forbidden. Ten label-contract-excluded identifiers remain U/ignore, and X13_LINE remains audit-only. Prefix, case-fold, suffix, genome-copy and copy-derived consensus fallbacks are forbidden.

Question: Can an exhaustive, index-independent, case-sensitive exact-name scan of Dfam 3.9 partition 3 Families metadata recover 279 frozen identifiers that the prior exact resolver could not resolve (6,432,583 annotation occurrences)?

Execution facts for repair Job 11526905:
- Slurm COMPLETED, ExitCode=0:0, elapsed 01:40:52 on gpu034; private partition; 4 CPU, 48 GiB, 0 GPU.
- The allocation-side suite passed 34/34 tests. All 35 atomic units completed; no temp checkpoint remains.
- The scan covered exactly 321,856 Families datasets, 321,856 unique canonical paths and 321,856 unique HDF5 object addresses. It observed 321,856 consensus attributes and 321,818 model attributes, matching the frozen denominator.
- Target denominator is exactly 279 unique identifiers and occurrence mass 6,432,583; identifier and occurrence conservation deltas are zero.
- Exact candidate rows=0. Recovered=0, ambiguous=0, invalid metadata=0, missing=279; all 6,432,583 target occurrences remain missing.
- X13_LINE is excluded from primary and remains an independent audit row: one identifier, 686 occurrences, two exact candidates with distinct provenance.
- Canonical status is IDENTITY_RECOVERY_TYPED_BLOCK, semantic_success=true, valid_negative=true, claim_eligible=false. All downstream authorization flags are false.
- Independent audit verified the immutable current state exact file set/hash, the 64-file attempt payload exact file set/hash, all 35 two-level checkpoint manifests and payload hashes, unique unit count, denominator sums, inventory uniqueness, and 279 resolution rows all marked missing.
- Source stable identity fields match across login/compute nodes. Each checkpoint records device 42->65 as audit_only. The 63.9 GB H5 does not have a cryptographic full-content hash; binding uses symlink target hash, inode, size, mtime, mode, HDF5 metadata/layout and rmlib. This limitation is explicit.
- scripts/validate_goal.py returns failed_run only because ACTIVE_GOAL is an older selector/decoder milestone that expects selector_top2_contains_best. Treat this as a mandatory stop signal for a mismatched active goal, not as evidence that the asset run failed semantically.

Prior context: the original job 11526687 failed before scanning because st_dev was incorrectly binding across mount namespaces. A narrow audited repair made st_dev audit-only without changing targets, matching, resolver, topology or resources. This job is the single authorized retry; no further automatic retry exists.

Questions:
1. Is the result a valid negative under the frozen exact-name contract? Audit denominator, exact-match semantics, integrity closure and source-identity limitation.
2. What scientific statement is supported, and what stronger statements are not supported? In particular, distinguish “partition 3 contains no exact-name match” from “the biological families do not exist”.
3. Does this close the partition-3 recovery hypothesis, or is any further scan/retry justified?
4. What is the narrowest next action toward a leakage-safe direct-S0 baseline? Options may include stopping the current identity contract, a human-gated contract revision using another official identity source, or abandoning direct S0; do not authorize GPU/S1 automatically.
5. Assess leakage/comparability: labels must remain direct RepeatMasker labels; any sequence homology may define split components only. No majority relabeling, genome-copy proxy or target-derived split leakage.
6. Choose exactly one judgment from: continue-current-route, run-sanity-check-first, replace-component, abandon-route. Give confidence and one concrete next action.

Return a concise structured review with these exact headings: Overall judgment, Result validity, Supported conclusion, Unsupported conclusions, Leakage/comparability, Route decision, Exact next action, Risks, Confidence.
