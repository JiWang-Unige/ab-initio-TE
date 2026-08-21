#!/usr/bin/env bash
# wiki.sh — lightweight, searchable research wiki for the lab.
#
# Stores three indexable kinds and ties them to the archived papers in refs/:
#   - ideas/<slug>.md  : a hypothesis/direction (status: untried|tried|parked)
#   - notes/<slug>.md  : a "ran it once" note (quick result + takeaway + next step)
#   - (papers)         : live in refs/dossiers/ (via refs/archive_source.sh); INDEX links them too
#
# Subcommands:
#   add-idea  --slug S --title "T" [--hypothesis "..."] [--why "..."] [--next "..."] [--refs "s1,s2"] [--status untried]
#   add-note  --slug S --title "T" [--what "..."] [--result "..."] [--takeaway "..."] [--next "..."] [--refs "s1,s2"]
#   index     # regenerate wiki/INDEX.md from refs/sources.md + ideas/ + notes/
#   search "<query>"   # grep across refs/, wiki/, docs/
#
# Run from project root (lab/). Paths are relative to it.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"   # project root (lab)
WIKI="$ROOT/wiki"; REFS="$ROOT/refs"; DOCS="$ROOT/docs"
cmd="${1:-}"; shift || true

kv() { # parse --key value pairs into assoc-like vars via eval-free lookup
  :; }

parse() { # populate global A_* from --flags
  SLUG="" TITLE="" HYP="" WHY="" NEXT="" REFLIST="" STATUS="untried" WHAT="" RESULT="" TAKE=""
  while [ $# -gt 0 ]; do case "$1" in
    --slug) SLUG="$2"; shift 2;; --title) TITLE="$2"; shift 2;;
    --hypothesis) HYP="$2"; shift 2;; --why) WHY="$2"; shift 2;;
    --next) NEXT="$2"; shift 2;; --refs) REFLIST="$2"; shift 2;;
    --status) STATUS="$2"; shift 2;; --what) WHAT="$2"; shift 2;;
    --result) RESULT="$2"; shift 2;; --takeaway) TAKE="$2"; shift 2;;
    *) shift;; esac; done
}

case "$cmd" in
  add-idea)
    parse "$@"; [ -z "$SLUG" ] && { echo "ERROR: --slug required" >&2; exit 2; }
    f="$WIKI/ideas/${SLUG}.md"
    { echo "# Idea: ${TITLE:-$SLUG}"; echo;
      echo "- slug: \`$SLUG\` · status: **$STATUS** · added: $(date +%F)";
      echo "- refs: ${REFLIST:-}";
      echo; echo "## Hypothesis"; echo "${HYP:-}";
      echo; echo "## Why it matters"; echo "${WHY:-}";
      echo; echo "## Next step"; echo "${NEXT:-}";
      echo; echo "## Log"; echo "- $(date +%F): created (status=$STATUS)";
    } > "$f"
    echo "WIKI idea -> $f"; "$0" index >/dev/null; ;;
  add-note)
    parse "$@"; [ -z "$SLUG" ] && { echo "ERROR: --slug required" >&2; exit 2; }
    f="$WIKI/notes/${SLUG}.md"
    { echo "# Note (tried-once): ${TITLE:-$SLUG}"; echo;
      echo "- slug: \`$SLUG\` · added: $(date +%F)";
      echo "- refs: ${REFLIST:-}";
      echo; echo "## What I ran"; echo "${WHAT:-}";
      echo; echo "## Quick result"; echo "${RESULT:-}";
      echo; echo "## Takeaway"; echo "${TAKE:-}";
      echo; echo "## Next direction"; echo "${NEXT:-}";
    } > "$f"
    echo "WIKI note -> $f"; "$0" index >/dev/null; ;;
  index)
    out="$WIKI/INDEX.md"
    {
      echo "# Wiki Index"; echo;
      echo "> 由 \`wiki.sh index\` 自动生成。汇总 papers(refs/) + ideas + notes，随时检索下一步方向。"; echo;
      echo "## Ideas"; echo "| slug | title | status | next step |"; echo "|---|---|---|---|";
      for f in "$WIKI"/ideas/*.md; do [ -e "$f" ] || continue;
        t=$(grep -m1 '^# Idea: ' "$f" | sed 's/^# Idea: //');
        s=$(grep -m1 'status:' "$f" | sed -E 's/.*status: \*\*([^*]+)\*\*.*/\1/');
        n=$(awk '/^## Next step/{getline; print; exit}' "$f");
        sl=$(basename "$f" .md);
        echo "| [$sl](ideas/$sl.md) | ${t:-} | ${s:-} | ${n:-} |"; done
      echo; echo "## Notes (tried-once)"; echo "| slug | title | takeaway | next direction |"; echo "|---|---|---|---|";
      for f in "$WIKI"/notes/*.md; do [ -e "$f" ] || continue;
        t=$(grep -m1 '^# Note' "$f" | sed -E 's/^# Note[^:]*: //');
        tk=$(awk '/^## Takeaway/{getline; print; exit}' "$f");
        n=$(awk '/^## Next direction/{getline; print; exit}' "$f");
        sl=$(basename "$f" .md);
        echo "| [$sl](notes/$sl.md) | ${t:-} | ${tk:-} | ${n:-} |"; done
      echo; echo "## Papers (archived in refs/)";
      if [ -f "$REFS/sources.md" ]; then
        grep -E '^\| ' "$REFS/sources.md" | grep -v -- '---' | sed 's#dossiers/#../refs/dossiers/#';
      else echo "(refs/sources.md 不存在)"; fi
    } > "$out"
    echo "WIKI index -> $out ($(grep -c '^| \[' "$out" 2>/dev/null || echo 0) entries)"; ;;
  search)
    q="${1:-}"; [ -z "$q" ] && { echo "ERROR: search <query>" >&2; exit 2; }
    echo "== wiki/ =="; grep -rin --include='*.md' "$q" "$WIKI" 2>/dev/null | grep -v INDEX.md | head -30
    echo "== refs/ =="; grep -rin --include='*.md' "$q" "$REFS" 2>/dev/null | head -30
    echo "== docs/ =="; grep -rin --include='*.md' "$q" "$DOCS" 2>/dev/null | head -30
    ;;
  *) echo "usage: wiki.sh {add-idea|add-note|index|search} ..." >&2; exit 2;;
esac
