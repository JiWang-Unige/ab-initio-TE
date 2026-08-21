请作为独立研究审稿人，用简体中文输出结构化评审，并以精确标题 `### 1. Overall judgment` 开始。

TE-FM direct-superfamily S0 的一个 claim-ineligible CPU 前置实验 Job11533175：冻结6个Dfam3.9 versioned accessions，逐一查询12个leaf，正式科学调用固定且仅一次6×12=72次 `FamDBLeaf.get_family_by_accession`；禁name/prefix/case/alias/copy fallback。PASS要求6个均exact-once且partition/accession/name/raw class/consensus length/SHA全匹配；missing/duplicate/drift是rc0 typed block；API/runtime/integrity错误是rc2 failed run。即使PASS也只允许另提leaf-adapter CPU方案，不自动开放RepeatMasker、DATA、homology、GPU S0或S1。

作业exact 1CPU/4GiB/10m/0GPU，gate、scheduler和23/23 tests通过。单次内存72-call probe函数返回；之后cleanup错误调用 `FamDB.finalize()`。installed read-mode `FamDBLeaf`不定义write bookkeeping属性`added`，finalizer访问它并抛AttributeError。72个观察未冻结/发布，所以当前结果未知，不能推断PASS或typed block。语义审计=`FAILED_RUN_FAMDB_READ_MODE_FINALIZE_API`，semantic_success=false、valid_negative=false；failure bundles/logs/gate/audit/validation均由已验证SHA manifest闭合。此前aggregate Job11528885也因`added`失败，随后才用新contract替换为本leaf probe；本probe one-shot授权已消耗。

核心问题：永久停止该FamDB access/export路线，还是仅允许一次新的、独立审查的close-only生命周期修复？若允许，科学72-call probe必须完全不变；read mode禁用`FamDB.finalize()`，显式关闭HDF5 handles，先stage观察再cleanup，测试cleanup失败不会擦除/升级结果，fresh gate，仅一次同资源CPU尝试；任何再次API/lifecycle失败永久关闭。当前任何下游S阶段均不得开放。

必须包含：
1. Overall judgment：只选 continue-current-route / replace-component / run-sanity-check-first / abandon-route / comparability-blocker 之一。
2. SOTA gap（N/A）。
3. comparability表。
4. semantic/reproducibility表。
5. 判断是exact-access失败还是cleanup失败。
6. track recommendation。
7. risks。
8. exactly one next action及永久stop/re-entry条件。
9. confidence。
