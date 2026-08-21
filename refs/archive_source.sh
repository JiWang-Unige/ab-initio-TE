#!/usr/bin/env bash
# archive_source.sh — best-effort archive of a paper + its code repo into refs/.
#
# Used by /sota-inventory (--type sota) and /note-add (--type note).
# Best-effort: download failures are recorded, never fatal — so the caller can
# still proceed and the user can drop the PDF in manually later.
#
# Usage:
#   bash refs/archive_source.sh --slug <slug> [--arxiv <id>] [--pdf-url <url>] \
#        [--repo <git-url>] [--supp-url <url>]... [--title "..."] [--type sota|note] [--why "..."] [--refs-dir refs]
#
#   --supp-url 可重复多次：下载补充材料(supplementary)到 refs/supp/<slug>/。关键指标的精确
#   定义/数据集是否预滤过 FP 等常只在补充材料里，故单独归档。下载失败按 failed(url) 记录，
#   由 /sota-inventory 的失败源汇报列给主人手动补。
set -uo pipefail

SLUG="" ARXIV="" PDF_URL="" REPO="" TITLE="" TYPE="note" WHY="" REFS="refs"
SUPP_URLS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --slug) SLUG="$2"; shift 2;;
    --arxiv) ARXIV="$2"; shift 2;;
    --pdf-url) PDF_URL="$2"; shift 2;;
    --repo) REPO="$2"; shift 2;;
    --supp-url) SUPP_URLS+=("$2"); shift 2;;
    --title) TITLE="$2"; shift 2;;
    --type) TYPE="$2"; shift 2;;
    --why) WHY="$2"; shift 2;;
    --refs-dir) REFS="$2"; shift 2;;
    *) echo "WARN: unknown arg $1" >&2; shift;;
  esac
done

if [ -z "$SLUG" ]; then echo "ERROR: --slug required" >&2; exit 2; fi
mkdir -p "$REFS/pdfs" "$REFS/repos" "$REFS/dossiers"

PDF_STATUS="none"; REPO_STATUS="none"; REPO_COMMIT=""

# --- 1. PDF (arXiv id preferred, else explicit url) ---
PDF_PATH="$REFS/pdfs/${SLUG}.pdf"
DL_URL=""
[ -n "$ARXIV" ] && DL_URL="https://arxiv.org/pdf/${ARXIV}.pdf"
[ -z "$DL_URL" ] && [ -n "$PDF_URL" ] && DL_URL="$PDF_URL"
if [ -n "$DL_URL" ]; then
  if [ -s "$PDF_PATH" ]; then
    PDF_STATUS="exists"
  elif curl -fsSL --max-time 60 "$DL_URL" -o "$PDF_PATH" 2>/dev/null && [ -s "$PDF_PATH" ]; then
    PDF_STATUS="downloaded"
  else
    rm -f "$PDF_PATH"
    PDF_STATUS="failed($DL_URL)"
  fi
fi

# --- 2. Repo (shallow clone; record commit) ---
REPO_DIR="$REFS/repos/${SLUG}"
if [ -n "$REPO" ]; then
  if [ -d "$REPO_DIR/.git" ]; then
    REPO_STATUS="exists"
    REPO_COMMIT="$(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null || echo '?')"
  elif git clone --depth 1 --quiet "$REPO" "$REPO_DIR" 2>/dev/null; then
    REPO_STATUS="cloned"
    REPO_COMMIT="$(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null || echo '?')"
  else
    # too big / private / no git access — keep a link stub instead
    printf '# %s (repo not cloned)\n\n- URL: %s\n- Reason: clone failed (private/large/no-net). Clone manually if needed.\n' \
      "$SLUG" "$REPO" > "$REFS/repos/${SLUG}.link.md"
    REPO_STATUS="link-only"
  fi
fi

# --- 2b. Supplementary materials (best-effort; each url recorded, failures surfaced) ---
SUPP_STATUS="none"
if [ "${#SUPP_URLS[@]}" -gt 0 ]; then
  mkdir -p "$REFS/supp/${SLUG}"
  ok=0; fail=0; failed_urls=""; i=0
  for u in "${SUPP_URLS[@]}"; do
    i=$((i+1))
    ext="${u##*.}"; case "$ext" in pdf|zip|gz|tgz|tar|txt|csv|tsv|xlsx|xls|docx|json) ;; *) ext="dat";; esac
    dest="$REFS/supp/${SLUG}/supp-${i}.${ext}"
    if [ -s "$dest" ]; then ok=$((ok+1))
    elif curl -fsSL --max-time 120 "$u" -o "$dest" 2>/dev/null && [ -s "$dest" ]; then ok=$((ok+1))
    else rm -f "$dest"; fail=$((fail+1)); failed_urls="${failed_urls:+$failed_urls;}$u"; fi
  done
  if [ "$fail" -eq 0 ]; then SUPP_STATUS="downloaded($ok)"
  elif [ "$ok" -gt 0 ]; then SUPP_STATUS="partial(ok=$ok,failed($failed_urls))"
  else SUPP_STATUS="failed($failed_urls)"; fi
fi

# --- 3. Dossier skeleton (only if missing — never clobber filled-in detail) ---
DOSSIER="$REFS/dossiers/${SLUG}.md"
if [ ! -f "$DOSSIER" ]; then
  {
    echo "# Dossier: ${TITLE:-$SLUG}"
    echo
    echo "- slug: \`$SLUG\` · type: $TYPE · added: $(date +%F)"
    echo "- Links: ${ARXIV:+arXiv:$ARXIV } ${REPO:+repo:$REPO}"
    echo "- PDF: refs/pdfs/${SLUG}.pdf ($PDF_STATUS)"
    echo "- Repo: refs/repos/${SLUG}/ ($REPO_STATUS${REPO_COMMIT:+ @ $REPO_COMMIT})"
    [ "${#SUPP_URLS[@]}" -gt 0 ] && echo "- Supplementary: refs/supp/${SLUG}/ ($SUPP_STATUS)"
    [ -n "$WHY" ] && echo "- Why relevant: $WHY"
    echo
    echo "## Dataset source (⏳ verify via WebFetch)"
    echo "- Which dataset / version / where obtained:"
    echo "- Public download / license:"
    echo
    echo "## Metric implementation (⏳ verify)"
    echo "- Metric name + exact definition (e.g., segment F1 boundary rule):"
    echo "- Official impl / script / library:"
    echo
    echo "## Split scheme (⏳ verify)"
    echo "- Train/val/test split source + leakage notes:"
    echo
    echo "## Weights / license"
    echo "- Pretrained weights URL + version + license:"
    echo
    echo "## Reproducibility notes"
    echo "- Setup difficulty / known gotchas:"
    echo
    echo "## Relevance to our project"
    echo "- ${WHY:-}"
  } > "$DOSSIER"
  DOSSIER_STATUS="created"
else
  DOSSIER_STATUS="exists"
fi

# Record supp status even if dossier pre-existed (append once so failures get surfaced).
if [ "${#SUPP_URLS[@]}" -gt 0 ] && ! grep -q "^- Supplementary:" "$DOSSIER" 2>/dev/null; then
  printf -- '- Supplementary: refs/supp/%s/ (%s)\n' "$SLUG" "$SUPP_STATUS" >> "$DOSSIER"
fi

# --- 4. Append to index (avoid dup slug row) ---
INDEX="$REFS/sources.md"
[ -f "$INDEX" ] || printf '# Archived Sources Index\n\n| slug | title | type | pdf | repo | dossier | added_by | date |\n|---|---|---|---|---|---|---|---|\n' > "$INDEX"
if ! grep -q "| \`\?${SLUG}\`\? |" "$INDEX" 2>/dev/null && ! grep -q "^| ${SLUG} |" "$INDEX" 2>/dev/null; then
  printf '| %s | %s | %s | %s | %s | %s | %s | %s |\n' \
    "$SLUG" "${TITLE:-}" "$TYPE" "$PDF_STATUS" "$REPO_STATUS" "dossiers/${SLUG}.md" "${ADDED_BY:-archive_source}" "$(date +%F)" >> "$INDEX"
fi

echo "ARCHIVED slug=$SLUG pdf=$PDF_STATUS repo=$REPO_STATUS${REPO_COMMIT:+@$REPO_COMMIT} supp=$SUPP_STATUS dossier=$DOSSIER_STATUS"
