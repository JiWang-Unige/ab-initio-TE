# Reviewer A · Claude

Verdict: `replace-component`; confidence high (~95%).

Root cause is an execution-environment identity-contract bug, not asset content drift. Symlink-target SHA256, inode, size, mtime and mode matched exactly; only `st_dev` differed (42 versus 65), which is expected for the same BeeGFS object across node/mount namespaces. The runner correctly failed closed, but the contract selected a non-portable binding field.

Recommended identity contract:

- Binding: exact symlink target hash, explicit canonical `/home`↔`/srv` alias mapping, inode, size, nanosecond mtime, mode, HDF5 structure/metadata/partition identity and rmlib identity, with checks before and after use.
- Audit-only: `st_dev` and unnormalized absolute path strings.
- Any binding-field change, unknown alias, HDF5 mismatch or pre/post change remains fail-closed.
- The absence of a 64 GB full-content hash remains an explicit residual limitation.

The repair must not alter the 279 identifiers, 6,432,583 occurrence mass, case-sensitive exact matching, X13 audit-only status, label contract, split or downstream gates. Required behavior tests cover mount-namespace device changes, actual inode/size/mtime/mode/symlink drift, alias normalization, HDF5 metadata and TOCTOU. A single repair-only retry at unchanged 4 CPU/48 GiB/3 h/0 GPU is defensible after fresh code review, but this reviewer does not directly authorize submission.

Exact next action: replace only the source-identity guard component, run behavior tests and fresh code-review gate, then manually decide the one repair-only retry.
