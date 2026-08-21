You are an independent post-run reviewer. Review this failed, claim-ineligible CPU asset run and recommend exactly one next decision. Do not edit files or run compute.

Research sequence: a direct RepeatMasker superfamily S0 baseline must first obtain leakage-safe identity/homology components. GPU S0 and hierarchical S1 remain forbidden. Dfam 3.9 partition 3 lacks Lookup/ByName, so exact case-sensitive Families metadata must be exhaustively scanned for 279 frozen missing identifiers (6,432,583 occurrences). X13_LINE is audit-only; prefix/case/copy-derived fallbacks are forbidden.

Prior evidence: serial Job 11525316 scanned 30,000/321,856 datasets in ~1,480 s and was cancelled because projected runtime was 15,878 s (4.41 h). Partial zero hits were declared non-evidence. A proposed 20-minute preflight was stopped before submission because 15,878/4=3,969.5 s exceeds its 900 s feasibility ceiling. A new resumable four-worker implementation passed separate code review (25/25 tests) and was authorized exactly once at 4 CPU/48 GiB/3 h/0 GPU.

Current Job 11526687 facts:
- Slurm state FAILED, ExitCode=1:0, elapsed 4 s on gpu034, 4 CPU/48 GiB/0 GPU.
- pre_submit gate passed; no H5 dataset enumeration, tests, workers, or checkpoints started.
- Source guard failed before payload. Login-frozen identity: symlink target SHA256 217f18..., st_dev=42, inode=3873985988255185360, size=63,939,647,016, mtime_ns=1781725800000000000, mode=0644. Compute observed identity: same symlink hash, same inode, same size, same mtime, same mode, but st_dev=65.
- The project root is a shared BeeGFS path reachable through /home and /srv aliases. Device IDs can differ by mount namespace/node even for the same shared inode.
- Runner correctly fail-closed and atomically published FORMAL_FAILED_INTEGRITY; immutable state manifest verifies. Its canonical metrics contain generic SBATCH_POST_PREPARE_EXIT:1, while traceback and independent audit preserve SOURCE_IDENTITY_DRIFT and the exact fields.
- validate_goal returns failed_run/rc3. No identity recovery result exists.
- No automatic retry is authorized.

Questions:
1. Is this best classified as asset content drift, execution-environment identity-contract bug, or ambiguous integrity failure? Explain using the field evidence.
2. Should st_dev be binding across login and compute nodes? Propose the narrowest fail-closed source identity contract that is stable across mount namespaces without weakening ordinary-drift detection. Consider symlink-target hash, canonical path alias, inode, size, mtime, mode, HDF5 metadata/layout/rmlib, and the admitted absence of a 64GB full-content hash.
3. Is one repair-only retry defensible, or should the route stop/use a different asset mechanism? If retry is defensible, list mandatory behavior tests and fresh code-review gates. Do not authorize automatic retry yourself.
4. Check data leakage/scientific comparability: could this repair alter the 279-target denominator, exact-match semantics, or downstream split? State hard boundaries.
5. Choose exactly one judgment from: run-sanity-check-first, replace-component, abandon-route, continue-current-route. Give confidence and one next action.

Return a concise structured review with: verdict, root-cause classification, evidence audit, leakage/comparability, recommended identity contract, required tests, resource/retry recommendation, risks, exact next action, and confidence.
