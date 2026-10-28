#!/usr/bin/env python3
"""Prepare the weekly commit for the official GitLab repository.

Copies this week's part of the project (see raspored.py) from this repository into a clone of the GitLab
repository, rebuilds the overview files (READMEs, requirements-dev.txt, pytest.ini) so they only describe what
already exists, optionally runs the tests, and stages everything. The team then adds its own work for the week
and commits (or uses --commit).

    python .gitlab-tjedni/tjedni_commit.py --gitlab ../IoTGarage-gitlab --test       # current week by date
    python .gitlab-tjedni/tjedni_commit.py 3 --gitlab ../IoTGarage-gitlab --commit --poruka "..."

Changes the team made in the GitLab clone are kept: when the source changes too, the two are combined with a
three-way merge (git merge-file); real conflicts are reported and the file is left as the team has it.
Only the standard library is needed (Python >= 3.8).
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from raspored import IZOSTAVI, POCETAK, PRAVILA, ROK, TJEDNI, UPRAVLJANE  # noqa: E402

STATE_FILE = "tjedni-stanje-v2.json"  # kept inside the clone's .git directory, never committed


# ---------------------------------------------------------------- helpers
def git(args, cwd, binary=False, check=True):
    p = subprocess.run(["git"] + args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and p.returncode != 0:
        raise SystemExit("git %s failed:\n%s" % (" ".join(args), p.stderr.decode("utf-8", "replace")))
    return p.stdout if binary else p.stdout.decode("utf-8")


def week_dates(week):
    start = POCETAK + datetime.timedelta(weeks=week - 1)
    return start, min(start + datetime.timedelta(days=6), ROK)


def current_week(today=None):
    days = ((today or datetime.date.today()) - POCETAK).days
    return min(max(days // 7 + 1, 1), max(TJEDNI))


def week_of(path):
    if any(path.startswith(p) for p in IZOSTAVI):
        return None
    best = None
    for prefix, week in PRAVILA:
        if path == prefix or (prefix.endswith("/") and path.startswith(prefix)):
            if best is None or len(prefix) > len(best[0]):
                best = (prefix, week)
    return best[1] if best else 0  # 0 = not assigned


def source_files(src, ref):
    """[(path, mode, blob_sha)] of every tracked file at ref."""
    out = git(["ls-tree", "-r", "-z", ref], src)
    files = []
    for entry in out.split("\0"):
        if not entry:
            continue
        meta, path = entry.split("\t", 1)
        mode, kind, blob = meta.split()
        if kind == "blob":
            files.append((path, mode, blob))
    return files


def read_blob(src, blob):
    return git(["cat-file", "blob", blob], src, binary=True)


def write_file(root, path, data, mode="100644"):
    full = os.path.join(root, *path.split("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as f:
        f.write(data)
    if mode == "100755" and os.name == "posix":
        os.chmod(full, 0o755)


def remove_file(root, path):
    full = os.path.join(root, *path.split("/"))
    os.remove(full)
    d = os.path.dirname(full)
    while d != root and os.path.isdir(d) and not os.listdir(d):
        os.rmdir(d)
        d = os.path.dirname(d)


def merge3(ours, base, theirs):
    """Three-way merge of text files: (merged bytes, clean?). Binary files never merge."""
    if b"\0" in ours + base + theirs:
        return ours, False
    with tempfile.TemporaryDirectory() as tmp:
        names = []
        for name, data in (("ours", ours), ("base", base), ("theirs", theirs)):
            path = os.path.join(tmp, name)
            with open(path, "wb") as f:
                f.write(data)
            names.append(path)
        p = subprocess.run(["git", "merge-file", "-p"] + names, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.stdout, p.returncode == 0


def sync(new, base, current):
    """Decide what the GitLab file should become: (action, data).

    base = what the tool wrote last time (None = never), current = file in the GitLab clone (None = missing)."""
    if current == new:
        return "same", None
    if base is None:
        return ("add", new) if current is None else ("exists", None)
    if current is None:
        return "deleted", None  # the team deleted it in GitLab: leave it deleted
    if current == base:
        return "update", new
    if new == base:
        return "same", None  # only the team changed it
    merged, clean = merge3(current, base, new)
    return ("merge", merged) if clean else ("conflict", None)


def read_file(root, path):
    full = os.path.join(root, *path.split("/"))
    if not os.path.isfile(full):
        return None
    with open(full, "rb") as f:
        return f.read()


# ---------------------------------------------------------------- overview files for a given week
VISIBLE_BLOCK = re.compile(r"<!-- gitlab:(od-tjedna=(\d+)|izostavi) -->\n(.*?)<!-- /gitlab -->\n?", re.S)
HIDDEN_BLOCK = re.compile(r"<!-- gitlab:do-tjedna=(\d+)\n(.*?)\n-->\n?", re.S)
LINK = re.compile(r"(!?)\[([^\]]*)\]\(([^)\s]+)\)")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+(?:\*\*)?")


def apply_week_blocks(text, week):
    def visible(m):
        if m.group(1) == "izostavi":
            return ""
        return m.group(3) if week >= int(m.group(2)) else ""

    text = VISIBLE_BLOCK.sub(visible, text)
    return HIDDEN_BLOCK.sub(lambda m: m.group(2) + "\n" if week <= int(m.group(1)) else "", text)


def prune_links(text, md_path, exists):
    """Drop index rows for things that do not exist yet; remove or unlink other links to them."""
    base = os.path.dirname(md_path)

    def missing(target):
        if re.match(r"^[a-z]+:", target) or target.startswith("#"):
            return False
        path = os.path.normpath(os.path.join(base, target.split("#")[0])).replace(os.sep, "/")
        return not path.startswith("..") and not exists(path)

    out, fence = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fence = not fence
        links = [] if fence else LINK.findall(line)
        bad = [(img, label, t) for img, label, t in links if missing(t)]
        if not bad:
            out.append(line)
            continue
        if line.strip().startswith("!["):
            continue  # image of something that does not exist yet
        first = next((t for img, label, t in links if not img), None)
        if line.startswith("|") and first and missing(first):
            continue  # table row describing a folder/file that does not exist yet
        m = LIST_ITEM.match(line)
        if m and line[m.end():].startswith("[") and first and missing(first):
            continue  # list item that is just a link to something that does not exist yet
        for img, label, t in bad:
            link = re.escape("%s[%s](%s)" % (img, label, t))
            new = re.sub(r"\s*[,;·]\s*" + link, "", line, count=1)
            if new == line:
                new = re.sub(link + r"[,;]\s*", "", line, count=1)
            if new == line:
                new = line.replace("%s[%s](%s)" % (img, label, t), label, 1)
            line = new
        out.append(line)
    text = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", text)


def build_overview(path, data, week, exists):
    text = data.decode("utf-8")
    if path.endswith(".md"):
        text = prune_links(apply_week_blocks(text, week), path, exists)
    elif path.endswith("requirements-dev.txt"):
        keep = []
        for line in text.split("\n"):
            m = re.match(r"-e\s+([^\[\s]+)", line)
            if m and not exists(os.path.normpath(os.path.join(os.path.dirname(path), m.group(1))).replace(os.sep, "/")):
                continue
            keep.append(line)
        text = "\n".join(keep)
    elif path.endswith("pytest.ini"):
        keep, in_paths = [], False
        for line in text.split("\n"):
            if line.startswith("testpaths"):
                in_paths = True
            elif in_paths and line.startswith((" ", "\t")) and line.strip():
                rel = os.path.normpath(os.path.join(os.path.dirname(path), line.strip())).replace(os.sep, "/")
                if not exists(rel):
                    continue
            elif line.strip():
                in_paths = False
            keep.append(line)
        text = "\n".join(keep)
    return text.encode("utf-8")


def broken_links(root):
    """Relative Markdown links in the GitLab tree that point to things that do not exist (yet)."""
    found = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            if not name.endswith(".md"):
                continue
            full = os.path.join(dirpath, name)
            fence = False
            for line in open(full, encoding="utf-8", errors="replace"):
                if line.lstrip().startswith("```"):
                    fence = not fence
                if fence:
                    continue
                for _img, _label, t in LINK.findall(line):
                    if re.match(r"^[a-z]+:", t) or t.startswith("#"):
                        continue
                    if not os.path.exists(os.path.normpath(os.path.join(dirpath, t.split("#")[0]))):
                        found.append((os.path.relpath(full, root).replace(os.sep, "/"), t))
    return found


# ---------------------------------------------------------------- tests
def run_tests(gitlab):
    software = os.path.join(gitlab, "SOFTWARE")
    venv = os.path.join(software, ".venv")
    py = os.path.join(venv, "Scripts", "python.exe") if os.name == "nt" else os.path.join(venv, "bin", "python")
    if not os.path.exists(py):
        print("  stvaram virtualno okruženje SOFTWARE/.venv ...")
        subprocess.check_call([sys.executable, "-m", "venv", venv])
    print("  pip install -r requirements-dev.txt ...")
    r = subprocess.run([py, "-m", "pip", "install", "-q", "-r", "requirements-dev.txt"], cwd=software)
    if r.returncode != 0:
        return False
    print("  pytest ...")
    return subprocess.run([py, "-m", "pytest", "-q"], cwd=software).returncode == 0


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Pripremi tjedni commit za službeni GitLab repozitorij.")
    ap.add_argument("tjedan", type=int, nargs="?", choices=sorted(TJEDNI),
                    help="koji tjedan se priprema (1-%d; zadano: tekući tjedan prema datumu)" % max(TJEDNI))
    ap.add_argument("--gitlab", required=True, help="putanja do klona GitLab repozitorija")
    ap.add_argument("--ref", default="HEAD", help="iz koje verzije ovog repozitorija se kopira (zadano: HEAD)")
    ap.add_argument("--test", action="store_true", help="instaliraj pakete i pokreni pytest u GitLab klonu")
    ap.add_argument("--commit", action="store_true", help="napravi commit i oznaku tjedan-N (bez pusha)")
    ap.add_argument("--poruka", default="", help="što je tim još napravio ovaj tjedan (dodaje se u poruku commita)")
    ap.add_argument("--prisili", action="store_true",
                    help="izvor pobjeđuje: zamijeni postojeće/konfliktne datoteke verzijom iz izvora")
    ap.add_argument("--zadrzi", action="append", default=[], metavar="PUTANJA",
                    help="tim pobjeđuje: zadrži GitLab verziju ove datoteke i zaključi konflikt (može više puta)")
    args = ap.parse_args()

    week = args.tjedan or current_week()
    src = git(["rev-parse", "--show-toplevel"], HERE).strip()
    gitlab = os.path.abspath(args.gitlab)
    if not os.path.isdir(gitlab) or git(["rev-parse", "--is-inside-work-tree"], gitlab, check=False).strip() != "true":
        raise SystemExit("%s nije git repozitorij. Prvo: git clone <gitlab-url> %s" % (gitlab, args.gitlab))
    if os.path.realpath(git(["rev-parse", "--show-toplevel"], gitlab).strip()) == os.path.realpath(src):
        raise SystemExit("--gitlab mora biti ZASEBAN klon GitLab repozitorija, ne ovaj repozitorij.")

    git_dir = git(["rev-parse", "--absolute-git-dir"], gitlab).strip()
    state_path = os.path.join(git_dir, STATE_FILE)
    state = {"copied": {}, "generated": {}}
    if os.path.exists(state_path):
        with open(state_path, encoding="utf-8") as f:
            state = json.load(f)

    if week < state.get("tjedan", 0) and not args.prisili:
        raise SystemExit("U GitLab klonu je već pripremljen tjedan %d; tjedan %d bi vratio pregledne datoteke unatrag."
                         " Pokreni tjedan %d ili kasniji." % (state["tjedan"], week, state["tjedan"]))
    state["tjedan"] = max(week, state.get("tjedan", 0))

    files = source_files(src, args.ref)
    unassigned = [p for p, _, _ in files if week_of(p) == 0]

    phase, title = TJEDNI[week]
    first, last = week_dates(week)
    print("Tjedan %d (%s – %s) – %s\nizvor: %s @ %s\n" % (week, first.strftime("%d.%m."), last.strftime("%d.%m.%Y."),
                                                          phase, src, args.ref))

    # 1. bring in every file of weeks <= N (catches up a skipped week) and later source changes to them
    added, updated, merged, conflicts, kept, deleted_by_team, removed = [], [], [], [], [], [], []

    def apply(path, new, base, mode, w):
        current = read_file(gitlab, path)
        action, data = sync(new, base, current)
        if args.prisili and action in ("exists", "merge", "conflict"):
            action, data = "update", new
        elif path in args.zadrzi and action in ("exists", "conflict"):
            return True  # the team's version wins; remember the source version as seen
        if action in ("add", "update", "merge"):
            write_file(gitlab, path, data, mode)
            {"add": added, "update": updated, "merge": merged}[action].append((w, path))
        elif action == "exists":
            kept.append(path)
            return False  # not ours yet: --prisili replaces it on a later run
        elif action == "conflict":
            conflicts.append(path)
            return False
        elif action == "deleted":
            deleted_by_team.append(path)
        return True

    for path, mode, blob in files:
        w = week_of(path)
        if not w or w > week or path in UPRAVLJANE:
            continue
        prev = state["copied"].get(path)
        if prev == blob:
            if read_file(gitlab, path) is None:
                deleted_by_team.append(path)
            continue
        base = read_blob(src, prev) if prev else None
        if apply(path, read_blob(src, blob), base, mode, w):
            state["copied"][path] = blob

    # files that were removed from the source after they had been copied
    in_source = {p for p, _, _ in files}
    for path, prev in sorted(state["copied"].items()):
        if path in in_source:
            continue
        current = read_file(gitlab, path)
        if current is not None and current == read_blob(src, prev):
            remove_file(gitlab, path)
            removed.append(path)
        elif current is not None:
            kept.append(path)
        del state["copied"][path]

    # 2. rebuild the overview files for this week
    def exists(rel):
        return os.path.exists(os.path.join(gitlab, *rel.split("/")))

    by_path = {p: b for p, _, b in files}
    for path in UPRAVLJANE:
        if path not in by_path or week_of(path) > week:
            continue
        new = build_overview(path, read_blob(src, by_path[path]), week, exists)
        base = state["generated"].get(path)
        if apply(path, new, base.encode("utf-8") if base is not None else None, "100644", week):
            state["generated"][path] = new.decode("utf-8")

    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1, sort_keys=True, ensure_ascii=False)

    # 3. report
    changed = added + updated + merged
    top = sorted({"/".join(p.split("/")[:2]) if p.count("/") >= 1 else p for _, p in changed})
    print("Novo: %d, osvježeno iz izvora: %d, spojeno s izmjenama tima: %d, uklonjeno: %d"
          % (len(added), len(updated), len(merged), len(removed)))
    for t in top:
        print("  " + t)
    if conflicts:
        print("\nKONFLIKT – i tim i izvor su mijenjali isto mjesto; datoteka ostaje kako ju je tim ostavio,"
              " riješi ručno pa --zadrzi PUTANJA (ostaje verzija tima) ili --prisili (verzija iz izvora):")
        for p in conflicts:
            print("  " + p)
    if kept:
        print("\nVeć postoje u GitLabu s drugačijim sadržajem (npr. predložak nastavnika) – NISU prepisane"
              " (--prisili ih zamijeni): %d" % len(kept))
        for p in kept[:15]:
            print("  " + p)
    if deleted_by_team:
        print("\nTim ih je obrisao u GitLabu, ne vraćam ih: %d (npr. %s)" % (len(deleted_by_team), deleted_by_team[0]))
    if unassigned:
        print("\nUPOZORENJE: datoteke bez pravila u raspored.py (ne kopiraju se): %d" % len(unassigned))
        for p in unassigned[:15]:
            print("  " + p)
    extra = [p for p in git(["ls-files"], gitlab).split("\n") if p and p not in by_path]
    if extra:
        print("\nU GitLabu postoje i datoteke kojih nema u izvoru (alat ih ne dira): %s" % ", ".join(extra[:10]))
    forward = broken_links(gitlab)
    if forward:
        print("\nPoveznice na dijelove koji dolaze kasnije: %d (u redu – riješe se dolaskom tog dijela)" % len(forward))

    # 4. tests
    ok = True
    if args.test:
        print("\nTestovi u GitLab klonu:")
        ok = run_tests(gitlab)
        print("  " + ("PROLAZE" if ok else "NE PROLAZE – popravi prije commita"))

    # 5. stage, optionally commit
    git(["add", "-A"], gitlab)
    staged = [p for p in git(["diff", "--cached", "--name-only", "-z"], gitlab).split("\0") if p]
    print("\nSpremno za commit: %d datoteka (git -C %s status)" % (len(staged), args.gitlab))
    groups = sorted({"/".join(p.split("/")[:2]) if p.count("/") >= 2 else p.split("/")[0] for p in staged})
    body = ["Promjene:"] + ["- " + g for g in groups]
    if args.poruka:
        body += ["", args.poruka]
    message = title + "\n\n" + "\n".join(body) + "\n"
    if args.commit:
        if not ok:
            raise SystemExit("Testovi ne prolaze – commit nije napravljen.")
        if not staged:
            print("\nNema promjena za commit: raspored ovaj tjedan ne donosi novi dio (npr. blagdani), a tim još"
                  " nije ništa dodao. Dodaj svoj rad u GitLab klon pa pokreni ponovno.")
            return
        subprocess.run(["git", "commit", "-q", "-F", "-"], cwd=gitlab, input=message.encode("utf-8"), check=True)
        tag = "tjedan-%d" % week
        if git(["tag", "-l", tag], gitlab).strip():
            print("Oznaka %s već postoji – nije pomaknuta." % tag)
        else:
            git(["tag", "-a", tag, "-m", title], gitlab)
        print("\nCommit i oznaka %s napravljeni. Objavi s:\n  git -C %s push && git -C %s push --tags"
              % (tag, args.gitlab, args.gitlab))
    else:
        print("\nPrijedlog poruke commita:\n\n" + message)
        print("Dodaj svoj rad za ovaj tjedan, pa:\n  python .gitlab-tjedni/tjedni_commit.py %d --gitlab %s --commit"
              " --poruka \"...\"\n(ili sam: git commit, git tag tjedan-%d, git push --follow-tags)"
              % (week, args.gitlab, week))


if __name__ == "__main__":
    main()
