#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import argparse
from typing import Callable, Dict, List, Optional, Set, Tuple

# -----------------------------
# Core helpers & rule predicates
# -----------------------------

VOWELS = set("AEIOU")  # Y is treated as a consonant (adjust if desired)
ALPHA_RE = re.compile(r"^[A-Z]+$")

def load_words(path: str) -> List[str]:
    """Load unique, uppercase alphabetic words in first-seen file order."""
    seen: Set[str] = set()
    words: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            w = line.strip().upper()
            if not w:
                continue
            if not ALPHA_RE.match(w):
                continue
            if w in seen:
                continue
            seen.add(w)
            words.append(w)
    return words

def count_vowels(w: str) -> int:
    return sum(ch in VOWELS for ch in w)

def has_no_repeats(w: str) -> bool:
    return len(w) == len(set(w))

def has_double_letter(w: str) -> bool:
    return any(w[i] == w[i+1] for i in range(len(w) - 1))

def alternates_vc(w: str) -> bool:
    """Letters must alternate vowel/consonant; Y is considered a consonant."""
    if not w:
        return False
    prev_is_vowel = w[0] in VOWELS
    for ch in w[1:]:
        is_vowel = ch in VOWELS
        if is_vowel == prev_is_vowel:
            return False
        prev_is_vowel = is_vowel
    return True

def overlap_end_to_start(a: str, b: str) -> int:
    """Max k ≥ 1 such that b startswith a[-k:]. Returns 0 if none."""
    maxk = min(len(a), len(b))
    for k in range(maxk, 0, -1):
        if b.startswith(a[-k:]):
            return k
    return 0

def overlap_start_to_end(a: str, b: str) -> int:
    """Max k ≥ 1 such that b endswith a[:k]. Returns 0 if none."""
    maxk = min(len(a), len(b))
    for k in range(maxk, 0, -1):
        if b.endswith(a[:k]):
            return k
    return 0

# -----------------------------
# Rule registry & interactive UI
# -----------------------------

class RuleSpec:
    def __init__(self, code: str, label: str, needs_param: bool,
                 builder: Callable[[Optional[int]], Callable[[str], bool]]):
        self.code = code
        self.label = label
        self.needs_param = needs_param
        self.builder = builder  # returns predicate(word)->bool

def pred_len_exact(n: Optional[int]) -> Callable[[str], bool]:
    assert n is not None
    return lambda w: len(w) == n

def pred_exact_vowels(n: Optional[int]) -> Callable[[str], bool]:
    assert n is not None
    return lambda w: count_vowels(w) == n

def pred_no_repeats(_: Optional[int]) -> Callable[[str], bool]:
    return has_no_repeats

def pred_has_double(_: Optional[int]) -> Callable[[str], bool]:
    return has_double_letter

def pred_alt_vc(_: Optional[int]) -> Callable[[str], bool]:
    return alternates_vc

RULES: List[RuleSpec] = [
    RuleSpec("LEN", "Must be exactly X letters", True,  pred_len_exact),
    RuleSpec("NOVAR", "No repeated letters", False,      pred_no_repeats),
    RuleSpec("VOWELS", "Exactly X vowels (Y is consonant)", True, pred_exact_vowels),
    RuleSpec("ALTVC", "Alternating vowel/consonant (Y consonant)", False, pred_alt_vc),
    RuleSpec("DOUBLE", "Has a double letter (e.g., leTTer)", False, pred_has_double),
]

def prompt_seed() -> str:
    while True:
        s = input("Enter seed word (letters only): ").strip().upper()
        if s and ALPHA_RE.match(s):
            return s
        print("  Please enter letters only (A–Z).")

def prompt_rule(position: int) -> Tuple[RuleSpec, Optional[int]]:
    print(f"\nChoose rule for WORD {position}:")
    for i, r in enumerate(RULES, start=1):
        print(f"  {i}. {r.label}")
    while True:
        choice = input(f"Enter 1-{len(RULES)}: ").strip()
        if not choice.isdigit() or not (1 <= int(choice) <= len(RULES)):
            print("  Invalid choice. Try again.")
            continue
        spec = RULES[int(choice) - 1]
        param: Optional[int] = None
        if spec.needs_param:
            while True:
                raw = input("  Enter X (positive integer): ").strip()
                if raw.isdigit() and int(raw) > 0:
                    param = int(raw)
                    break
                print("    Please enter a positive integer.")
        print(f"  Selected: {spec.label}" + (f" (X={param})" if param is not None else ""))
        return spec, param

# -----------------------------
# Solver (fast dynamic pipeline)
# -----------------------------

def build_candidates(words: List[str],
                     seed: str,
                     r1_pred: Callable[[str], bool],
                     r2_pred: Callable[[str], bool],
                     r3_pred: Callable[[str], bool]) -> Tuple[List[str], List[str], List[str]]:
    """Apply per-position rules + structural constraints:
       - w1 must start with a suffix of seed
       - w3 must end with a prefix of seed
    """
    start_prefixes = [seed[:k] for k in range(1, len(seed) + 1)]

    rule1, rule2, rule3 = [], [], []
    for w in words:
        if r1_pred(w) and overlap_end_to_start(seed, w) > 0:
            rule1.append(w)
        if r2_pred(w):
            rule2.append(w)
        if r3_pred(w) and any(w.endswith(pref) for pref in start_prefixes):
            rule3.append(w)
    return rule1, rule2, rule3

def solve_best_chain(seed: str,
                     dict_path: str,
                     r1_pred: Callable[[str], bool],
                     r2_pred: Callable[[str], bool],
                     r3_pred: Callable[[str], bool]) -> Optional[Dict[str, object]]:
    seed = seed.upper()
    words = load_words(dict_path)

    rule1, rule2, rule3 = build_candidates(words, seed, r1_pred, r2_pred, r3_pred)

    # STEP 1: For every prefix p of any rule3 word, record the best end-overlap (w3 -> seed)
    # H[p] = (best_end_overlap_len, best_w3)
    H: Dict[str, Tuple[int, str]] = {}
    for w3 in rule3:
        end_ov = overlap_start_to_end(seed, w3)  # how much w3 ends with a seed prefix
        if end_ov == 0:
            continue
        for k in range(1, len(w3) + 1):
            p = w3[:k]
            cur = H.get(p)
            if cur is None or end_ov > cur[0]:
                H[p] = (end_ov, w3)

    # STEP 2: For each rule2 word, pick the best "tail":
    # choose a suffix s of w2 that is a key in H; tail = len(s) + H[s].end_ov
    # Publish under every prefix p of w2:
    # M[p] = (tail_score, w2, suffix_used (w2->w3), w3, end_ov)
    M: Dict[str, Tuple[int, str, str, str, int]] = {}
    for w2 in rule2:
        best_tail = -1
        best_suffix = ""
        best_w3 = ""
        best_end_ov = 0
        for k in range(1, len(w2) + 1):
            s = w2[-k:]
            if s in H:
                end_ov, cand_w3 = H[s]
                tail = k + end_ov
                if tail > best_tail:
                    best_tail = tail
                    best_suffix = s
                    best_w3 = cand_w3
                    best_end_ov = end_ov
        if best_tail <= 0:
            continue
        for k in range(1, len(w2) + 1):
            p = w2[:k]
            if p not in M or best_tail > M[p][0]:
                M[p] = (best_tail, w2, best_suffix, best_w3, best_end_ov)

    # STEP 3: Combine each w1 with best available tail keyed by a suffix of w1
    best_score = -1
    best_tuple: Optional[Tuple[str, str, str]] = None
    best_breakdown: Optional[Tuple[int, int, int, int]] = None

    for w1 in rule1:
        ov1 = overlap_end_to_start(seed, w1)  # seed -> w1
        if ov1 == 0:
            continue
        best_for_w1 = -1
        chosen_pack = None
        for k in range(1, len(w1) + 1):
            s = w1[-k:]           # this must be the start of w2
            pack = M.get(s)
            if not pack:
                continue
            tail_score, w2, s2, w3, end_ov = pack
            ov2 = len(s)          # w1 -> w2 (by construction)
            ov3_start = len(s2)   # w2 -> w3
            ov3_end = end_ov      # w3 -> seed
            total = ov1 + ov2 + ov3_start + ov3_end
            if total > best_for_w1:
                best_for_w1 = total
                chosen_pack = (w2, w3, ov1, ov2, ov3_start, ov3_end)

        if chosen_pack and best_for_w1 > best_score:
            w2, w3, ov1, ov2, ov3_start, ov3_end = chosen_pack
            best_score = best_for_w1
            best_tuple = (w1, w2, w3)
            best_breakdown = (ov1, ov2, ov3_start, ov3_end)

    if not best_tuple:
        return None

    w1, w2, w3 = best_tuple
    ov1, ov2, ov3_start, ov3_end = best_breakdown  # type: ignore
    return {
        "sequence": [seed, w1, w2, w3],
        "score": best_score,
        "breakdown": {
            "seed→w1": ov1,
            "w1→w2": ov2,
            "w2→w3": ov3_start,
            "w3→seed": ov3_end,
        },
    }

# -----------------------------
# Glue: interactive + CLI
# -----------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Flexible 3-word chain solver with selectable rules."
    )
    parser.add_argument("dict", help="Path to dict.txt")
    args = parser.parse_args()

    seed = prompt_seed()

    r1_spec, r1_param = prompt_rule(1)
    r2_spec, r2_param = prompt_rule(2)
    r3_spec, r3_param = prompt_rule(3)

    r1_pred = r1_spec.builder(r1_param)
    r2_pred = r2_spec.builder(r2_param)
    r3_pred = r3_spec.builder(r3_param)

    result = solve_best_chain(seed, args.dict, r1_pred, r2_pred, r3_pred)
    if not result:
        print("\nNo valid chain found with these rules.")
        return

    seq = result["sequence"]  # type: ignore
    bd = result["breakdown"]  # type: ignore
    print("\n" + "=" * 60)
    print("BEST SEQUENCE")
    print(" -> ".join(seq))  # type: ignore
    print(f"Score: {result['score']}")
    print("Overlaps:",
          f"{bd['seed→w1']} + {bd['w1→w2']} + {bd['w2→w3']} + {bd['w3→seed']}")

if __name__ == "__main__":
    main()
