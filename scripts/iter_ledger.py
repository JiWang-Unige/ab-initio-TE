#!/usr/bin/env python3
"""Iteration ledger reconciliation — catch the "autonomous loop dropped the docs" drift.

During /pursue's multi-round autonomy, per-iteration doc maintenance (docs/04
iterations, docs/05 Run tracker, docs/06 results) can silently fall behind the
actual runs on disk. This deterministic check compares ground truth (reports/,
runs/, outputs/<id>/STATUS) against the records and reports any drift.

It also catches the "ghost RUNNING" failure (a run whose STATUS is still RUNNING
but which is no longer alive on the machine or the cluster) — exactly the
"autonomous loop launched a run that died and nobody noticed" hazard /pursue is
meant to prevent. See GB EXP-B-011.

Advisory by design — it never edits anything. Used two ways:
  1. manually:  python3 scripts/iter_ledger.py            (pretty report)
  2. from a Stop / PostToolUse hook: parse JSON, surface a reminder on drift.

Exit code: 0 = in sync, 1 = drift detected (so a hook can branch on it).

A run's exp_id is "recorded" iff it appears in ALL of: docs/05 Run tracker,
docs/06 results, docs/04 iterations. A finished run also needs
outputs/<id>/STATUS so `validate_goal.py --run-status` can verify it.
"""
import os, re, json, sys, glob, subprocess, time


def exp_ids_on_disk(root):
    ids = set()
    for p in glob.glob(os.path.join(root, "reports", "*.json")):
        ids.add(os.path.splitext(os.path.basename(p))[0])
    for p in glob.glob(os.path.join(root, "runs", "*")):
        if os.path.isdir(p):
            ids.add(os.path.basename(p))
    for p in glob.glob(os.path.join(root, "outputs", "*", "STATUS")):
        ids.add(os.path.basename(os.path.dirname(p)))
    return ids


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def mentions(text, eid):
    # exact token: eid not followed by another word char or hyphen, so
    # "EXP-B-005" does NOT falsely match inside "EXP-B-005-s2".
    return re.search(re.escape(eid) + r"(?![\w-])", text) is not None


def explicit_reproduce_waiver(text):
    """Recognize only intentional waivers, not template prose mentioning the token."""
    return re.search(r'(?im)^\s*(?:[-*]\s*)?"?reproduce_waived"?\s*[:=]\s*\S', text) is not None


def has_reproduction_ledger_entry(text):
    if re.search(r"(?m)^##\s+Baseline Reproduction Report:\s*(?!<).+\S", text):
        return True
    in_runs = False
    for line in text.splitlines():
        if line.startswith("## 1. Reproduction Runs"):
            in_runs = True
            continue
        if in_runs and line.startswith("## "):
            break
        if not in_runs or not line.strip().startswith("|"):
            continue
        low = line.lower()
        if " id |" in low or re.match(r"^\|\s*-+", line.strip()):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 10:
            continue
        entry_id, model, report_path, verdict = cells[0], cells[2], cells[8], cells[9]
        if all(x and "<" not in x for x in [entry_id, model, report_path, verdict]):
            return True
    return False


def table_value(text, field):
    pattern = r"(?m)^\|\s*" + re.escape(field) + r"\s*\|\s*([^|]+?)\s*\|"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def chosen_value(value):
    if not value or "<" in value:
        return False
    if "/" in value:
        return False
    return True


def has_dataset_contract_row(text):
    in_sec = False
    for line in text.splitlines():
        if line.startswith("## 3. Dataset And Split Contract"):
            in_sec = True
            continue
        if in_sec and line.startswith("## "):
            break
        if not in_sec or not line.strip().startswith("|"):
            continue
        low = line.lower()
        if "dataset | version" in low or re.match(r"^\|\s*-+", line.strip()):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 5 and all(c and "<" not in c for c in cells[:4]):
            return True
    return False


def has_candidate_inventory(text):
    if not re.search(r"(?m)^## Candidate models", text):
        return False
    in_sec = False
    for line in text.splitlines():
        if line.startswith("## Candidate models"):
            in_sec = True
            continue
        if in_sec and line.startswith("## "):
            break
        if not in_sec or not line.strip().startswith("|"):
            continue
        low = line.lower()
        if "model | paper" in low or re.match(r"^\|\s*-+", line.strip()):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0] and "<" not in cells[0]:
            return True
    return False


def evaluator_contract_ready(text):
    if not text:
        return False
    match = re.search(r"(?im)^\s*-\s*Status:\s*(.+?)\s*$", text)
    status = match.group(1).strip() if match else ""
    if not status or re.search(r"\b(draft|incomplete|todo|待填)\b", status, re.I):
        return False
    metric_name = table_value(text, "Metric name")
    direction = table_value(text, "Direction")
    granularity = table_value(text, "Prediction granularity")
    label_mapping = table_value(text, "Positive class / label mapping")
    our_evaluator = re.search(r"(?m)^\|\s*Our evaluator script\s*\|\s*([^|]+?)\s*\|", text)
    our_evaluator_path = our_evaluator.group(1).strip() if our_evaluator else ""
    schema_ready = all(x in text for x in ['"exp_id"', '"primary_metric"', '"semantic_success"'])
    return (
        chosen_value(metric_name)
        and direction in {"higher_is_better", "lower_is_better"}
        and chosen_value(granularity)
        and chosen_value(label_mapping)
        and bool(our_evaluator_path and "<" not in our_evaluator_path)
        and has_dataset_contract_row(text)
        and schema_ready
    )


def _remote_squeue_prefix():
    """['ssh', host] when submission.mode==remote_ssh, else []. A remote_ssh box
    has no local Slurm, so the bare-`squeue` check below would always miss a live
    REMOTE job and falsely flag it stale_signal (→ /pursue HALTs a healthy run).
    Run squeue on the cluster instead. Reads cluster_config.yaml; absent /
    on_cluster / local_direct → [] (unchanged local+squeue behavior)."""
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:
        txt = open(os.path.join(root, "cluster_config.yaml"), encoding="utf-8", errors="ignore").read()
    except OSError:
        return []
    m = re.search(r"^submission:\s*\n(.*?)(?=^\S|\Z)", txt, re.M | re.S)
    block = m.group(1) if m else txt
    mode = re.search(r"^\s+mode:\s*([^\s#]+)", block, re.M)
    host = re.search(r"^\s+ssh_host:\s*[\"']?([^\s\"'#]+)", block, re.M)
    if mode and mode.group(1) == "remote_ssh" and host:
        return ["ssh", host.group(1)]
    return []


def process_mentions(eid):
    """True if exp_id is referenced by a LIVE local process OR a Slurm job.

    A STATUS=RUNNING with neither a local process nor a squeue job mentioning
    the exp_id is a zombie. On a Slurm cluster the real run is a job (local ps
    sees nothing), so we check both; if squeue is absent (no Slurm) that branch
    quietly fails and only the local ps check applies. For remote_ssh installs
    the squeue runs over ssh on the cluster (see _remote_squeue_prefix).
    """
    # 1) local foreground/background process (smoke runs, local-mode installs)
    try:
        out = subprocess.check_output(["ps", "-eo", "cmd"], text=True, stderr=subprocess.DEVNULL)
        if eid in out:
            return True
    except Exception:
        pass
    # 2) Slurm job — match against job name (%j) and submit command (%o), since the
    #    canonical template names jobs / writes runs/<exp_id>. Local on_cluster, or
    #    over ssh for remote_ssh.
    try:
        out = subprocess.check_output(
            _remote_squeue_prefix() + ["squeue", "--noheader", "-o", "%j|%o"],
            text=True, stderr=subprocess.DEVNULL, timeout=15)
        if eid in out:
            return True
    except Exception:
        pass
    return False


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else (os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    ids = exp_ids_on_disk(root)
    tracker = read(os.path.join(root, "docs", "05_todo.md"))
    results = read(os.path.join(root, "docs", "06_results_log.md"))
    iters = read(os.path.join(root, "docs", "04_experiment_iterations.md"))
    ledger24 = read(os.path.join(root, "docs", "24_sprint_pursue_ledger.md"))

    drift = []
    open_status = []
    for eid in sorted(ids):
        miss = []
        status_path = os.path.join(root, "outputs", eid, "STATUS")
        status = read(status_path).strip().splitlines()[0] if os.path.exists(status_path) else ""
        report_exists = os.path.exists(os.path.join(root, "reports", eid + ".json"))
        if status and status.upper() != "COMPLETED":
            age_sec = time.time() - os.path.getmtime(status_path)
            no_proc = status.upper() == "RUNNING" and not process_mentions(eid)
            state = {"exp_id": eid, "status": status, "age_minutes": round(age_sec / 60, 1)}
            if no_proc:
                state["stale_signal"] = "RUNNING but no local process / Slurm job mentions exp_id"
            if not report_exists:
                state["missing_report"] = True
            open_status.append(state)
        
        in_ledger24 = mentions(ledger24, eid)
        if not mentions(tracker, eid) and not in_ledger24:
            miss.append("docs/05-tracker")
        if not mentions(results, eid) and not in_ledger24:
            miss.append("docs/06-result")
        if not mentions(iters, eid) and not in_ledger24:
            miss.append("docs/04-iter")
        if report_exists and not os.path.exists(status_path):
            miss.append("outputs/STATUS(run-status闸缺)")
        if status.upper() == "RUNNING" and not process_mentions(eid):
            miss.append("outputs/STATUS=RUNNING(no live process/job)")
        if miss:
            drift.append({"exp_id": eid, "missing": miss})

    # --- Loop-closure (sequence) check: the MOST RECENT result should be
    # tri-reviewed (docs/07) and pivoted (docs/08) before the next iteration starts.
    # This is the "iteration done -> tri-review -> pivot" backstop. Checked on the
    # latest result only, to stay low-noise. A hook can NUDGE on this; it cannot
    # *run* /tri-review — only the agent invokes skills.
    chain = []
    tri = read(os.path.join(root, "docs", "07_tri_review.md"))
    piv = read(os.path.join(root, "docs", "08_pivot_decisions.md"))
    rms = re.findall(r"(?m)^##\s*Result:\s*([A-Za-z0-9_.\-]+)", results)
    if rms:
        latest = rms[-1]
        if not mentions(tri, latest):
            chain.append({"exp_id": latest, "missing": "docs/07-tri-review"})
        elif not mentions(piv, latest):
            chain.append({"exp_id": latest, "missing": "docs/08-pivot"})

    # --- Phase gates (#13): deterministic "did we skip a required pre-step" checks ---
    gates = []
    roadmap = read(os.path.join(root, "docs", "03_benchmark_roadmap.md")) or ""
    inv = read(os.path.join(root, "docs", "02_sota_model_inventory.md")) or ""
    goal_txt = read(os.path.join(root, "ACTIVE_GOAL.json")) or ""
    started = bool(rms) or any(os.path.isdir(os.path.join(root, "runs", e)) for e in ids)
    baseline_repro = read(os.path.join(root, "docs", "20_baseline_reproduction.md")) or ""
    reproduced = has_reproduction_ledger_entry((results or "") + "\n" + baseline_repro)
    waived = explicit_reproduce_waiver(roadmap) or explicit_reproduce_waiver(goal_txt)
    if roadmap and started and not reproduced and not waived:
        gates.append("未复现 SOTA 就开始迭代 → 先 /reproduce-baselines 核实指标算法/数据集口径，并写 docs/20_baseline_reproduction.md（或在 docs/03 标 reproduce_waived:<理由>）。")
    evaluator_contract = read(os.path.join(root, "docs", "19_evaluator_contract.md")) or ""
    if started and not evaluator_contract_ready(evaluator_contract):
        gates.append("已有迭代但 evaluator contract 仍未完成 → 先补 docs/19_evaluator_contract.md，固化 metric/split/schema，避免 evaluator 漂移。")
    dossiers = glob.glob(os.path.join(root, "refs", "dossiers", "*.md"))
    if has_candidate_inventory(inv) and not dossiers:
        gates.append("SOTA inventory 已建但 refs/dossiers 为空 → sota-inventory 应归档 PDF/repo/dossier（artifact 后续可比性/复现要用）。")

    out = {"checked": len(ids), "drift_count": len(drift), "drift": drift,
           "open_status": open_status, "chain_gaps": chain, "phase_gates": gates,
           "ok": (not drift and not chain and not gates)}
    if drift or chain or gates:
        lines = []
        if drift:
            lines.append(f"⚠️ iter_ledger: {len(drift)} 个 run 未完整记录（可能 /pursue 漏写文档）：")
            for d in drift:
                lines.append(f"  - {d['exp_id']}: 缺 {', '.join(d['missing'])}")
            lines.append("  → 跑 /result-log 把 docs/04+05+06 补齐。")
        stale = [s for s in open_status if s.get("stale_signal")]
        if stale:
            lines.append("🧯 检测到疑似中断 run（STATUS=RUNNING 但无存活进程/作业 = 幽灵 run）：")
            for s in stale:
                lines.append(f"  - {s['exp_id']}: STATUS={s['status']}, {s['stale_signal']} (age {s['age_minutes']}min)")
            lines.append("  → 先 validate_goal.py 判定（预期 failed_run）+ 写 docs/08 intervention + 通知主人；不要直接开新实验。")
        if chain:
            c = chain[0]
            lines.append(f"🔁 迭代链未闭合：最近的 result {c['exp_id']} 还缺 {c['missing']}。")
            lines.append("  → 跑 /tri-review→/pivot 闭合本轮再开下一轮；若正停在 human gate 等你确认则属正常。")
        if gates:
            lines.append("🚦 阶段闸（跳过了必做前置步）：")
            for g in gates:
                lines.append(f"  - {g}")
        out["reminder"] = "\n".join(lines)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(0 if out["ok"] else 1)


if __name__ == "__main__":
    main()
