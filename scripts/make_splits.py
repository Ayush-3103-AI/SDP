"""Leave-parts-out splits → data/splits/logo.json (T-0007; 06 §Frozen eval, 09 §Data).

    python scripts/make_splits.py [--data data] [--out data/splits/logo.json] [--seed 0]

GroupKFold by geometry (= print), 5 folds, balanced by single-cause image count; calibration = 20 % of each
fold's training prints by seeded shuffle. Run ONCE: logo.json is frozen after T-0007 (CLAUDE.md hard rule), so the
script refuses to overwrite it, and --force only works while the file is not yet tracked by git.
"""
import argparse
import hashlib
import json
import random
import subprocess
import sys
from pathlib import Path

import pandas as pd

FOLDS, CALIB_FRAC = 5, 0.2


def group_folds(weight: dict[str, int], k: int, seed: int) -> list[list[str]]:
    """Heaviest group first into the lightest fold (sklearn's GroupKFold rule); equal weights in seeded order."""
    groups = sorted(weight)
    random.Random(seed).shuffle(groups)
    groups.sort(key=lambda g: -weight[g])  # stable: the shuffle breaks ties
    folds, load = [[] for _ in range(k)], [0] * k
    for g in groups:
        i = load.index(min(load))
        folds[i].append(g)
        load[i] += weight[g]
    return [sorted(f) for f in folds]


def splits(trials: pd.DataFrame, images: pd.DataFrame, k: int = FOLDS, seed: int = 0) -> dict:
    geo = dict(zip(trials.trial_id, trials.geometry))
    single = images[~images.cause.isin(["none", "multi"])]
    n_single = single.trial_id.map(geo).value_counts()
    weight = {g: int(n_single.get(g, 0)) for g in sorted(set(geo.values()))}
    rng = random.Random(seed)
    folds = []
    for test_geo in group_folds(weight, k, seed):
        test = sorted(t for t, g in geo.items() if g in test_geo)
        rest = sorted(t for t in geo if t not in test)
        rng.shuffle(rest)
        n_calib = max(1, round(CALIB_FRAC * len(rest)))
        folds.append({"test_geometries": test_geo, "train_trials": sorted(rest[n_calib:]),
                      "calib_trials": sorted(rest[:n_calib]), "test_trials": test})
    return {"version": 2, "kind": "leave-parts-out", "seed": seed, "folds": folds}


def tracked(path: Path) -> bool:
    """True if git knows the file (committed or staged). Outside a repo: False."""
    r = subprocess.run(["git", "ls-files", "--error-unmatch", path.name], cwd=path.parent, capture_output=True,
                       check=False)
    return r.returncode == 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data", help="folder with trials.csv and images.csv")
    ap.add_argument("--out", default="data/splits/logo.json")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--force", action="store_true", help="overwrite a logo.json that git does not track yet")
    a = ap.parse_args(argv)
    data, out = Path(a.data), Path(a.out)
    if out.exists() and (not a.force or tracked(out)):
        print(f"refusing to overwrite {out}: it is frozen (CLAUDE.md hard rule). git pull; don't re-run.",
              file=sys.stderr)
        return 1
    trials, images = pd.read_csv(data / "trials.csv"), pd.read_csv(data / "images.csv")
    if trials.geometry.nunique() < FOLDS:
        print(f"need ≥ {FOLDS} geometries for {FOLDS} folds, got {trials.geometry.nunique()}", file=sys.stderr)
        return 2
    s = splits(trials, images, FOLDS, a.seed)
    s["sha256"] = {n: hashlib.sha256((data / n).read_bytes()).hexdigest() for n in ("trials.csv", "images.csv")}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(s, indent=1) + "\n", encoding="utf-8")
    for i, f in enumerate(s["folds"]):
        print(f"fold {i}: test {len(f['test_trials'])} · train {len(f['train_trials'])} · "
              f"calib {len(f['calib_trials'])} prints")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
