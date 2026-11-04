#!/usr/bin/env bash
# Open the PR for one collect.yml run as TechEngineBot:
#
#   bash .github/scripts/open-collect-pr.sh <run-id>
#
# collect.yml can't push or open PRs: its token is read-only. A run that
# changes data uploads its commit as collect.patch, with pr-body.md and
# pr.json, in a collect-* artifact. Run this by hand from a TechAPI clone to
# push the run's changes to the task's collect/* branch and open the PR, or
# update the task's open one. It never touches your checkout or your branches.
# Your account pushes the branch and TechEngineBot opens the PR, so pr-checks
# runs on it like on any PR.
#
# TechEngineBot's gh login lives in its own config directory, so your own gh
# login is never used for the PR or changed. Log it in once, signing in to
# GitHub as TechEngineBot in the browser:
#
#   GH_CONFIG_DIR="$HOME/.config/gh-techenginebot" gh auth login -h github.com -p ssh --skip-ssh-key -s project -w
#
# Set TECHENGINEBOT_GH_CONFIG_DIR to keep it somewhere else.
#
# The artifact is the run's output, so nothing in it is trusted. GitHub's own
# record of the run, its title, says which task ran, and so which branch and PR
# it may update. Only the patch's changes are used: they are applied to the
# run's develop base in a scratch index, and may only add or change plain files
# under data/. The commit is made here, with the task's fixed title as its
# whole message, and the body loses every @ and issue reference before
# TechEngineBot posts it.
set -euo pipefail

run=${1:?usage: bash .github/scripts/open-collect-pr.sh <run-id>}
repo=GetTechAPI/TechAPI

cd "$(git rev-parse --show-toplevel)"
# Both where origin fetches from and where it pushes to.
urls=$(git remote get-url --all origin; git remote get-url --push --all origin)
while IFS= read -r url; do
  case "$url" in
    *[/:]GetTechAPI/TechAPI | *[/:]GetTechAPI/TechAPI.git) ;;
    *) echo "Run this from a clone of $repo (as origin, to fetch and push)." >&2; exit 1 ;;
  esac
done <<<"$urls"
# Run each name: on Windows, python3 is often a Store stub that only says so.
py=
for c in python3 python; do
  if "$c" -I -c 'import sys; sys.exit(sys.version_info < (3,))' >/dev/null 2>&1; then py=$c; break; fi
done
[ -n "$py" ] || { echo "Python 3 is needed on PATH, as python3 or python." >&2; exit 1; }

# Check TechEngineBot's login before anything is pushed.
bot_config=${TECHENGINEBOT_GH_CONFIG_DIR:-$HOME/.config/gh-techenginebot}
# A GH_TOKEN or GITHUB_TOKEN in the environment would win over that login.
bot() { env -u GH_TOKEN -u GITHUB_TOKEN GH_CONFIG_DIR="$bot_config" gh "$@"; }
if [ "$(bot api user --jq .login 2>/dev/null)" != TechEngineBot ]; then
  echo "gh in $bot_config is not logged in as TechEngineBot. Log it in once with:" >&2
  echo "  GH_CONFIG_DIR=\"$bot_config\" gh auth login -h github.com -p ssh --skip-ssh-key -s project -w" >&2
  exit 1
fi

# collect.yml titles each run "collect ingest <category>", "collect refresh" or
# "collect promote" from its inputs, and the run can't change that.
info=$(gh run view "$run" --repo "$repo" --json workflowName,event,headBranch,conclusion,displayTitle \
  --jq '"\(.workflowName)|\(.event)|\(.headBranch)|\(.conclusion)|\(.displayTitle)"')
case "$info" in
  "collect|workflow_dispatch|develop|success|collect "*) task=${info##*|collect } ;;
  *) echo "Run $run is \"$info\", not a successful collect run on develop." >&2; exit 1 ;;
esac
want=collect/${task// /-}

dir=$(mktemp -d "${TMPDIR:-/tmp}/open-collect-pr.XXXXXX")
trap 'rm -rf "$dir"' EXIT
gh run download "$run" --repo "$repo" --pattern 'collect-*' --dir "$dir/artifact" || {
  echo "Run $run has no collect-* artifact: it changed no data, or the artifact expired." >&2
  exit 1
}
patch=$(find "$dir/artifact" -type f -name collect.patch)
if [ -z "$patch" ] || [ "$(printf '%s\n' "$patch" | wc -l)" -ne 1 ]; then
  echo "Run $run should have exactly one collect.patch." >&2
  exit 1
fi
art=$(dirname "$patch")

# Check pr.json against the run's task, and write the body to post: the task's
# tracker link, then the run's report cleaned like final-check.yml's comment,
# so it can't mention anyone or link an issue.
meta=$("$py" -I - "$art/pr.json" "$art/pr-body.md" "$dir/body.md" "$want" <<'PY'
import json, re, sys

meta_path, body_path, out_path, want = sys.argv[1:5]
m = json.load(open(meta_path, encoding="utf-8"))
if not isinstance(m, dict):
    sys.exit("pr.json is not what collect.yml writes.")
branch, title, draft, base = (m.get(k) for k in ("branch", "title", "draft", "base"))
# The branch and title each TechEngine collector sets. The title is also the
# commit message and the PR title, so it must be one of these exactly.
titles = {"collect/refresh": "chore(data): refresh benchmark data",
          "collect/promote": "data(verify): promote records to verified"}
for category in ("cpu", "gpu", "smartphone"):
    titles["collect/ingest-" + category] = "feat(data/%s): ingest new SKUs" % category
if want not in titles:
    sys.exit("%s is not a task this script knows." % want)
if not (branch == want and title == titles[want]
        and isinstance(draft, bool)
        and isinstance(base, str) and re.fullmatch(r"[0-9a-f]{40}", base)):
    sys.exit("pr.json is not what %s's collector writes." % want)

link = "Closes #295" if want.startswith("collect/ingest-") else "Closes #296"
zw = chr(0x200B)  # zero-width space
lines = open(body_path, encoding="utf-8", errors="replace").read().split("\n")
if lines and lines[0].strip() == link:
    lines = lines[1:]
rest = "\n".join(lines).replace("@", "")
rest = re.sub(r"(?<!&)#(?=\d+\b)", "#" + zw, rest)
rest = re.sub(r"\bgh-(?=\d+\b)", lambda g: g.group(0) + zw, rest, flags=re.IGNORECASE)
rest = re.sub(r"/(issues|pull|discussions)/(?=\d)", lambda g: g.group(0) + zw, rest)
open(out_path, "w", encoding="utf-8").write((link + "\n" + rest)[:65000])

print(branch, title, "true" if draft else "false", base, sep="\t")
PY
)
IFS=$'\t' read -r branch title draft base <<<"$meta"

# The full ref name: a local branch or tag called origin/develop would win over
# the short one, and a single-branch clone's refspec may not cover develop.
git fetch --quiet origin +refs/heads/develop:refs/remotes/origin/develop
if ! git merge-base --is-ancestor "$base" refs/remotes/origin/develop 2>/dev/null; then
  if [ "$(git rev-parse --is-shallow-repository)" = true ]; then
    echo "This clone is shallow, so the run's base $base can't be checked: run git fetch --unshallow origin first." >&2
  else
    echo "The run's base $base is not on develop." >&2
  fi
  exit 1
fi

# Apply the patch's changes to the base in a scratch index: your checkout and
# branches stay as they are, and nothing of the patch but its changes is kept.
index=$dir/index
GIT_INDEX_FILE=$index git read-tree "$base"
if ! GIT_INDEX_FILE=$index git apply --cached "$patch"; then
  echo "collect.patch does not apply on $base." >&2
  exit 1
fi
tree=$(GIT_INDEX_FILE=$index git write-tree)

# The collectors only add and change records. Check the tree that would be
# pushed, not the patch text: --no-renames so that a rename into data/ can't
# hide the file it removes outside it, and --ignore-submodules=none so that no
# submodule setting can hide a change to the TechEngine pin.
changes=$(git diff-tree -r --no-renames --ignore-submodules=none "$base" "$tree")
bad=$(printf '%s\n' "$changes" |
  grep -vE '^:(000000|100644) 100644 [0-9a-f]+ [0-9a-f]+ [AM]'$'\t''data/' || true)
if [ -z "$changes" ] || [ -n "$bad" ]; then
  echo "collect.patch may only add or change plain files under data/, so it is not pushed:" >&2
  printf '%s\n' "${bad:-(it changes nothing)}" >&2
  exit 1
fi

# The collector is the author and you are the committer, as with any run.
commit=$(GIT_AUTHOR_NAME='github-actions[bot]' \
  GIT_AUTHOR_EMAIL='41898282+github-actions[bot]@users.noreply.github.com' \
  git commit-tree "$tree" -p "$base" -m "$title")
# The task's branch belongs to the collector, so each run replaces it.
git push --quiet --force origin "$commit:refs/heads/$branch"

# Not gh pr list --head: that also matches a fork's branch of the same name.
number=$(gh api "repos/$repo/pulls?state=open&base=develop&head=${repo%/*}:$branch" \
  --jq '.[0].number // empty')
if [ -n "$number" ]; then
  # gh pr edit can't set draft. A drafts run writes incomplete records, so its
  # PR goes back to draft first, even if it was marked ready.
  if [ "$draft" = true ]; then bot pr ready "$number" --repo "$repo" --undo; fi
  bot pr edit "$number" --repo "$repo" --title "$title" --body-file "$dir/body.md" \
    --add-assignee Seungpyo1007 --add-assignee TechEngineBot \
    --add-label data --add-label enhancement \
    --milestone "Massive dataset rebuild (1989-2026)"
else
  set -- --repo "$repo" --base develop --head "$branch" --title "$title" \
    --body-file "$dir/body.md" \
    --assignee Seungpyo1007 --assignee TechEngineBot \
    --label data --label enhancement \
    --milestone "Massive dataset rebuild (1989-2026)"
  if [ "$draft" = true ]; then set -- "$@" --draft; fi
  bot pr create "$@"
fi
