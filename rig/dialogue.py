"""dialogue.py — the one definition of "a spoken line" in a scene line, for every rig part that reads dialogue
(2026-09-27).

Why one module: bin/still (the first-frame prompt), rig/precheck.py (asked vs heard) and rig/audit/lipsync.py each had
their own pattern, allowing 100, 40 and 60 characters of voice direction between the speech verb and the quote. A
directed line ("says, low and firm, leaning on the word keep: '...'", skills/film/references/performance.md) broke
the pre-check's detector silently: no transcript comparison, no lip-sync line. Change the rules here only.

A spoken line = a speech verb, up to MAX_CUE characters of delivery direction without quote marks, then a quoted span.
The quote opens after a space, colon or comma, or at the start (so "Moth's" is not a quote), and closes before a
space, punctuation or the end (so "We've" and "won't" inside the line do not close it). Scene lines are
double-quoted zsh strings, so spoken words use single quotes; curly quotes are accepted too.
"""
from __future__ import annotations
import re

MAX_CUE = 100   # characters of delivery direction between the verb and the quote (performance.md: under 15 words)
# "laughs" is left out on purpose: in "laughs for the first time, and says" the laugh is acting the first frame keeps
VERBS = r"(?:says|asks|whispers|shouts|screams|calls|sings|mutters|hisses|speaks|replies|answers|murmurs|adds|tells(?:\s+\w+)?)"
SPEECH = rf"\b{VERBS}\b[^'‘\"“]{{0,{MAX_CUE}}}"
# any quoted span (bin/still removes these from the image prompt, spoken or not)
QUOTE = r"(?:(?<=[\s:,])|^)['‘\"“].{2,300}?['’\"”](?=[\s.,;:!?)]|$)"
# a spoken line, capturing its words (single or curly single quotes: the scene lines themselves are double-quoted)
# The opening quote must follow a space, colon or comma: with 100 characters of cue allowed, an apostrophe ("the fox's
# leg") would otherwise open a false quote (15-nyc-2000-slavic-neon line 2, found by the 2026-09-27 regression run).
_LINE = re.compile(SPEECH + r"(?<=[\s:,])['‘](.{2,300}?)['’](?=[\s.,;:!?)\"]|$)")


def quoted_lines(text: str) -> list[str]:
    """The words a scene asks to be spoken, in order: every quoted span introduced by a speech verb."""
    return _LINE.findall(text)


_NOT_A_NAME = {"Then", "Her", "His", "She", "He", "They", "The", "A", "An", "As", "After", "Before", "With", "And", "But",
               "On", "In", "At", "Now", "When", "While", "It", "Its", "Their", "This", "That", "Finally", "Still"}


def line_speakers(text: str) -> list[str | None]:
    """Who says each quoted line, in order (2026-10-03, shot lab): the last capitalised word in the clause before the
    speech verb ("Her brows drawn together, Dana says ..." -> Dana; "Then Leo shrugs and answers ..." -> Leo), None when
    the clause names nobody ("she says"). The gate uses it to check that lines written for two different people come
    from two different faces."""
    out = []
    for m in _LINE.finditer(text):
        clause = re.split(r"[.;:!?]\s", text[:m.start()])[-1]
        names = [w for w in re.findall(r"\b[A-Z][a-z]+\b", clause) if w not in _NOT_A_NAME]
        out.append(names[-1] if names else None)
    return out


def has_line(text: str) -> bool:
    return _LINE.search(text) is not None


# ---------- the flat-direction lint (2026-09-27, iteration 5; `docs/dialogue-sync.md`) ----------
# liminal-clowns' ten lines were each directed with one soft voice word ("in a low voice") and nothing else, and the
# bible froze everyone ("uncanny stillness"); the human heard the delivery as flat or awkward. The render
# tools refuse a project whose spoken lines are directed that way, so the director redirects them before rendering.
_CUE = re.compile(rf"\b({VERBS})\b([^'‘\"“]{{0,{MAX_CUE}}})(?<=[\s:,])['‘]")
_FLAT_CUE = re.compile(r"^[\s,]*(?:(?:in|with)\s+an?\s+)?(?:[\w-]+,?\s+){0,3}voice[\s,:]*$|^[\s,:]*$", re.I)
_BODY = re.compile(r"\b(eyes?|brows?|gaze|glanc\w*|looks?|looking|stares?|blinks?|breath\w*|sighs?|exhales?|inhales?|"
                   r"jaw|swallows?|shoulders?|leans?|nods?|tilts?|chin|squares|straightens|hands?|fingers?|turns?|"
                   r"lifts?|drops?|narrow\w*|widen\w*|frowns?|trembl\w*|pauses?|beat|flinch\w*|grips?|tightens?|"
                   r"softens?|hesitat\w*|steps?|crouch\w*|kneels?|wipes?|touch\w*)\b", re.I)
_FREEZE = re.compile(r"\b(stillness|motionless|frozen|unmoving|statue-like)\b", re.I)
_TOKENS = re.compile(r"^(\[[^\]]*\]\s*)+")


# ---------- who speaks: an ambiguous pronoun speaker (2026-10-04, the iteration-9 film, shot 3) ----------
# The project line read "Aldemar, a king of about fifty-five, ... looks down the hall beside his first minister, a thin
# man of about sixty in a pearl-grey robe, silent with mouth closed, holding a ledger. His eyes lift up the hall, brow
# lifting, and he says, dry, ...". The clip gave the king's line to the minister: his mouth moved through the line and
# the king's never opened. The sync gate passed it (one face in sync, no second mouth moving) and the director kept it.
# The video model hands a pronoun's line to whichever matching person the text left it with, so when the shot
# describes two men, "he says" is a coin toss (likewise two women and "she says"). Name the speaker or use a role right
# before the verb. One man and one woman with "she says" is fine (the-last-car, 8/8 in sync). Run over the 33 projects
# of 2026-10-04 it flags that shot 3, nine Clown Sighting interview lines whose background clown was also described
# as a man (in sync there only because the clown stood small and far back) and three early films' lines.
# Only `lint --who` runs it, so a director whose render tools predate it keeps its old checks.
_MALE = r"man|boy|king|prince|father|brother|husband|son|grandfather|uncle|monk|priest|waiter|groom|gentleman|lord|knight|minister"
_FEMALE = r"woman|girl|lady|queen|princess|mother|sister|wife|daughter|grandmother|aunt|nun|waitress|maid|bride|actress"
_MALE_PL = r"men|boys|kings|princes|brothers|monks|priests|gentlemen|lords|knights"
_FEMALE_PL = r"women|girls|ladies|queens|princesses|sisters|nuns|maids"
_PRONOUN = re.compile(r"\b(he|she|they)\b", re.I)


def _people(text: str, sing: str, plural: str) -> int:
    """People of one gender a scene describes: each "a/an ... <noun>" is one person, a plural noun counts as two."""
    one = len(re.findall(r"\b(?:a|an)\s+(?:[\w'-]+\s+){0,4}?(?:" + sing + r")\b", text, re.I))
    return one + 2 * len(re.findall(r"\b(?:" + plural + r")\b", text, re.I))


def pronoun_speakers(scenes: list[str], only: list[int] | None = None) -> list[str]:
    """Spoken lines whose speaker is only "he", "she" or "they" while the shot describes two or more people that the
    pronoun fits, one problem string per line."""
    out = []
    for n, raw in enumerate(scenes, 1):
        if only is not None and n not in only:
            continue
        text = _TOKENS.sub("", raw)
        bare = _LINE.sub(lambda m: m.group(0).replace(m.group(1), ""), text)   # people named inside a quote don't count
        men, women = _people(bare, _MALE, _MALE_PL), _people(bare, _FEMALE, _FEMALE_PL)
        for m, who in zip(_LINE.finditer(text), line_speakers(text)):
            if who:
                continue
            clause = re.split(r"[.;:!?]\s", text[:m.start()])[-1]
            p = _PRONOUN.search(clause)
            if not p:
                continue
            pron = p.group(1).lower()
            fits = men if pron == "he" else women if pron == "she" else men + women
            if fits < 2:
                continue
            tail = " ".join(clause.split()[-5:])
            verb = text[m.start():].split()[0].strip(",:")
            out.append(f"clip {n}: the speaker is only '{pron}' ({tail} {verb}) while the shot describes {fits} people "
                       f"it could mean; name the speaker or use a role right before the verb, e.g. 'and Aldemar says' or "
                       f"'the king says'. The video model gave such a line to the wrong man in the iteration-9 film, shot 3 "
                       f"(2026-10-04), and the sync gate passed it")
    return out


def lint(scenes: list[str], bible: str = "", only: list[int] | None = None, lab: bool = False) -> list[str]:
    """Problems with how the spoken lines are directed, one string per problem (empty = fine). lab=True (a project
    that sets LAB=1, 2026-10-03): a controlled experiment repeats one delivery on purpose, so the variety check is off;
    every other check stays."""
    out, prev_cue = [], None
    for n, raw in enumerate(scenes, 1):
        text = _TOKENS.sub("", raw)
        m = _CUE.search(text)
        if not m:
            continue
        cue = re.sub(r"\s+", " ", m.group(2)).strip(" ,:")
        before = text[:m.start()]
        # the character sentence is usually "Name, a woman of about 30, ..."; face paint and noses are not acting
        before_acting = re.sub(r"\b(face paint|red nose|nose)\b", "", before, flags=re.I)
        check = only is None or n in only
        if check and _FLAT_CUE.match(cue):
            shown = '"' + cue + '"' if cue else "none"   # no backslash inside an f-string: the engine's venv is Python 3.11
            out.append(f"clip {n}: the only direction is {shown} before the line; write the "
                       f"voice in under 15 words (pitch, pace, volume, texture, where it changes), e.g. \"says, low and "
                       f"firm, leaning on the word keep:\"")
        if check and not _BODY.search(before_acting.split(".")[-1] if "." in before_acting else before_acting):
            out.append(f"clip {n}: no face or body cue right before the speech verb; add what the eyes, brows, breath or "
                       f"posture do in that moment (e.g. \"her eyes on Pip just beside the lens, she takes a slow breath "
                       f"and says, ...\")")
        if check and not lab and prev_cue and cue and cue.lower() == prev_cue.lower():
            out.append(f"clip {n}: the same delivery as the previous spoken line (\"{cue}\"); vary pace, pitch or texture")
        prev_cue = cue
    if _FREEZE.search(bible or ""):
        out.append(f"BIBLE: \"{_FREEZE.search(bible).group(0)}\" freezes every actor, including the ones who speak; "
                   f"put stillness only in the lines of silent shots")
    return out


if __name__ == "__main__":
    import subprocess, sys
    if sys.argv[1:2] == ["lint"]:
        args = sys.argv[2:]
        who = "--who" in args          # the pronoun-speaker check (2026-10-04); render tools before it never pass it
        args = [a for a in args if a != "--who"]
        proj = args[0]
        only = [int(x) for x in args[1:]] or None
        r = subprocess.run(["zsh", "-c", 'SCENES=(); BIBLE=""; LAB=""; source "$1" >/dev/null 2>&1; '
                            'for s in "${SCENES[@]}"; do print -r -- "S:$s"; done; print -r -- "B:$BIBLE"; print -r -- "L:$LAB"',
                            "_", proj], capture_output=True, text=True)
        sc = [l[2:] for l in r.stdout.splitlines() if l.startswith("S:")]
        bi = next((l[2:] for l in r.stdout.splitlines() if l.startswith("B:")), "")
        lab = next((l[2:] for l in r.stdout.splitlines() if l.startswith("L:")), "") == "1"
        probs = lint(sc, bi, only, lab) + (pronoun_speakers(sc, only) if who and not lab else [])
        print("\n".join(probs))
        sys.exit(1 if probs else 0)
