"""
Scores every non-date column of a dataset against the "Project Name" and
"Region" target fields, using several independent, individually-weak
signals combined into one score -- rather than relying on any single
signal (header text alone is not reliable; see the Financial_Dataset.xlsx
case where "Region", "Region summary", "Sales Region", "Company" and
"State" are all plausible header names for a location-like column).

None of this is machine-learned; every weight and threshold here is a
plain constant, tunable in ScoringWeights. As discussed with the client:
these constants were set by hand against one real sample dataset and
should be re-tuned once more structurally different sample datasets are
available -- this file deliberately keeps every constant in one place
(ScoringWeights) to make that recalibration a config change, not a
rewrite.
"""

from dataclasses import dataclass, field
from difflib import SequenceMatcher

from ingestion.column_profiling import (
    ColumnProfile,
    co_occurrence_spread,
    pick_detail_columns_for_cooccurrence,
)
from ingestion.reference_data import (
    ALL_REGION_VALUE_TOKENS,
    PROJECT_HEADER_SYNONYMS,
    REGION_HEADER_SYNONYMS,
    US_STATE_CODES,
)


@dataclass
class ScoringWeights:
    """All tunable constants for project/region scoring, in one place."""

    # --- Project Name ---
    project_header_weight: float = 0.35
    project_cooccurrence_weight: float = 0.35
    project_cardinality_weight: float = 0.15

    # Cardinality band a Project-Name-shaped column is expected to sit in
    # (distinct / non-null rows). Real project lists are neither near-unique
    # per row (that's an ID column) nor tiny (that's a category column).
    project_cardinality_sweet_low: float = 0.001
    project_cardinality_sweet_high: float = 0.05

    # --- Region ---
    region_header_weight: float = 0.30
    region_gazetteer_weight: float = 0.40
    region_cardinality_weight: float = 0.15

    region_cardinality_sweet_low: float = 0.00005
    region_cardinality_sweet_high: float = 0.01

    # Penalize a candidate whose values look like US states specifically --
    # a real signal that it's a finer-grained "State" field, not "Region".
    us_state_penalty: float = 0.25

    # --- Ambiguity handling ---
    # A column becomes a genuine, shown-to-the-user candidate for a field
    # when it clears an ABSOLUTE evidence bar -- not merely by landing in
    # the top few by blended score (see ScoredCandidate.meets_inclusion_bar
    # for why a rank-based cutoff isn't safe here).
    # Region: real header resemblance, OR at least this fraction of
    # sample values recognized as region-like tokens.
    region_gazetteer_inclusion_threshold: float = 0.40

    # Project: real header resemblance, OR at least this much
    # co-occurrence "spread" (repeated values with varied detail rows
    # underneath -- the structural project-shaped pattern).
    project_cooccurrence_inclusion_threshold: float = 0.50

    # Safety valve only -- NOT a substitute for the inclusion bar above.
    # This just caps how many qualifying candidates get displayed, for
    # the rare case where an unusually messy dataset clears the bar on
    # many columns at once.
    max_candidates_to_display: int = 10

    # Minimum score to accept ANY automatic resolution at all, used only
    # when exactly one candidate clears the inclusion bar.
    min_confidence: float = 0.40


@dataclass
class ScoredCandidate:
    column: str
    score: float
    reasons: list[str] = field(default_factory=list)
    sample_values: list = field(default_factory=list)
    meets_inclusion_bar: bool = False

    # True if this column has REAL, independent evidence (a genuine name
    # match, or a genuine value/content match) of representing the
    # field -- as opposed to only scoring above zero via secondary
    # signals (cardinality shape, etc.) riding along with essentially
    # no direct evidence. This drives which candidates get shown for
    # clarification (see resolve_field) -- NOT relative rank, which
    # previously caused a real bug: a column with strong VALUE evidence
    # but no name evidence (e.g. a column literally named "Company"
    # whose values are actually country codes) could rank 5th-7th and
    # get silently truncated out of a fixed top-4 list, even though it
    # was the column the client's own business actually uses for Region.
    # Inclusion must be an absolute bar, not a top-N cutoff.


FUZZY_TOKEN_MIN_LEN = 4
FUZZY_TOKEN_THRESHOLD = 0.82


def _normalize_header(name: str) -> str:
    return "".join(
        ch if ch.isalnum() else " "
        for ch in name.lower()
    ).strip()


def _tokenize(normalized: str) -> set[str]:
    return {t for t in normalized.split() if t}


def _header_match_score(
        header: str,
        synonyms: set[str],
) -> tuple[float, str | None]:
    """
    Token-based matching, NOT whole-string character similarity.

    Whole-string fuzzy ratios (e.g. difflib.SequenceMatcher over the full
    normalized header) are unreliable for short business words: "Filler"
    vs "Billed" scores 0.67 on raw character overlap despite being
    unrelated words. Comparing token-by-token, and only fuzzy-matching
    tokens that are long enough for a ratio to mean anything, avoids
    that class of false positive.

    - Single-word synonyms: exact token match -> 1.0. Otherwise, a fuzzy
      match against individual header tokens ONLY when both the token and
      synonym are at least FUZZY_TOKEN_MIN_LEN long, and only above
      FUZZY_TOKEN_THRESHOLD (catches things like "regoin" -> "region",
      not "filler" -> "billed").
    - Multi-word synonyms ("project name"): all words present as tokens
      anywhere in the header -> 1.0. No fuzzy fallback for multi-word
      synonyms -- partial/fuzzy multi-word matching is where most false
      positives crept in during testing.
    """
    normalized = _normalize_header(header)

    if not normalized:
        return 0.0, None

    tokens = _tokenize(normalized)

    best_ratio = 0.0
    best_synonym = None

    for syn in synonyms:
        syn_tokens = syn.split()

        if len(syn_tokens) == 1:
            word = syn_tokens[0]

            if word in tokens:
                ratio = 1.0
            else:
                ratio = 0.0

                if len(word) >= FUZZY_TOKEN_MIN_LEN:
                    for t in tokens:
                        if len(t) >= FUZZY_TOKEN_MIN_LEN:
                            r = SequenceMatcher(None, t, word).ratio()
                            if r > ratio:
                                ratio = r

                if ratio < FUZZY_TOKEN_THRESHOLD:
                    ratio = 0.0

        else:
            ratio = (
                1.0
                if all(w in tokens for w in syn_tokens)
                else 0.0
            )

        if ratio > best_ratio:
            best_ratio = ratio
            best_synonym = syn

    return best_ratio, best_synonym


def _cardinality_band_score(
        ratio: float,
        low: float,
        high: float,
) -> float:
    """
    1.0 inside [low, high], decaying smoothly outside it. Avoids a hard
    cliff so a column just outside the band still gets partial credit.
    """
    if low <= ratio <= high:
        return 1.0

    if ratio < low:
        if low == 0:
            return 0.0
        return max(
            0.0,
            1.0 - (low - ratio) / low,
            )

    span = max(high, 1e-9)

    return max(
        0.0,
        1.0 - (ratio - high) / span,
        )


MIN_ROWS_FOR_CARDINALITY_TRUST = 30


def _cardinality_confidence_shrinkage(non_null_count: int) -> float:
    """
    Cardinality RATIOS are noisy on small samples -- 2 distinct values out
    of 4 rows (ratio 0.5) says nothing like what 2,000 distinct values out
    of 40,000 rows (ratio 0.05) says, even though a raw band-score treats
    them by the same rule. Scales the cardinality signal's influence down
    toward "neutral" (0.5) as row count drops below
    MIN_ROWS_FOR_CARDINALITY_TRUST, instead of trusting the ratio outright
    on tiny datasets (a real gap found via testing, not just theory).
    """
    return min(
        1.0,
        non_null_count / MIN_ROWS_FOR_CARDINALITY_TRUST,
        )


def _shrink_toward_neutral(
        raw_score: float,
        confidence: float,
) -> float:
    return (
            confidence * raw_score
            + (1 - confidence) * 0.5
    )


def _gazetteer_overlap(sample_values: list) -> float:
    if not sample_values:
        return 0.0

    hits = 0
    checked = 0

    for v in sample_values:
        if v is None:
            continue

        checked += 1
        token = str(v).strip().lower()

        if token in ALL_REGION_VALUE_TOKENS:
            hits += 1

    return hits / checked if checked else 0.0


def _us_state_overlap(sample_values: list) -> float:
    if not sample_values:
        return 0.0

    hits = sum(
        1
        for v in sample_values
        if v is not None
        and str(v).strip().lower() in US_STATE_CODES
    )

    return hits / len(sample_values)


def score_project_candidates(
        profiles: list[ColumnProfile],
        df,
        weights: ScoringWeights = ScoringWeights(),
) -> list[ScoredCandidate]:
    """Scores every eligible text column as a Project Name candidate."""

    eligible = [
        p
        for p in profiles
        if not p.is_month_year
           and not p.is_numeric
           and p.non_null_count > 0
    ]

    detail_cols = pick_detail_columns_for_cooccurrence(
        profiles,
        exclude={p.name for p in eligible},
    )

    results = []

    for p in eligible:
        header_score, matched_syn = _header_match_score(
            p.name,
            PROJECT_HEADER_SYNONYMS,
        )

        raw_cardinality_score = _cardinality_band_score(
            p.cardinality_ratio,
            weights.project_cardinality_sweet_low,
            weights.project_cardinality_sweet_high,
        )

        cardinality_confidence = _cardinality_confidence_shrinkage(
            p.non_null_count
        )

        cardinality_score = _shrink_toward_neutral(
            raw_cardinality_score,
            cardinality_confidence,
        )

        cooccurrence_score = co_occurrence_spread(
            df,
            p.name,
            detail_cols,
        )

        total = (
                weights.project_header_weight * header_score
                + weights.project_cooccurrence_weight * cooccurrence_score
                + weights.project_cardinality_weight * cardinality_score
        )

        reasons = []

        if header_score:
            reasons.append(
                f"header text resembles '{matched_syn}' ({header_score:.2f})"
            )

        if cooccurrence_score:
            reasons.append(
                "repeated values show varied detail rows underneath "
                f"({cooccurrence_score:.2f})"
            )

        if cardinality_score:
            reasons.append(
                f"cardinality ratio {p.cardinality_ratio:.4f} "
                "fits project-shaped range"
            )

        meets_bar = (
                header_score > 0
                or cooccurrence_score
                >= weights.project_cooccurrence_inclusion_threshold
        )

        results.append(
            ScoredCandidate(
                column=p.name,
                score=round(total, 4),
                reasons=reasons,
                sample_values=p.sample_values,
                meets_inclusion_bar=meets_bar,
            )
        )

    results.sort(
        key=lambda c: c.score,
        reverse=True,
    )

    return results


def score_region_candidates(
        profiles: list[ColumnProfile],
        weights: ScoringWeights = ScoringWeights(),
) -> list[ScoredCandidate]:
    """Scores every eligible text column as a Region candidate."""

    eligible = [
        p
        for p in profiles
        if not p.is_month_year
           and not p.is_numeric
           and p.non_null_count > 0
    ]

    results = []

    for p in eligible:
        header_score, matched_syn = _header_match_score(
            p.name,
            REGION_HEADER_SYNONYMS,
        )

        gazetteer_score = _gazetteer_overlap(
            p.sample_values
        )

        raw_cardinality_score = _cardinality_band_score(
            p.cardinality_ratio,
            weights.region_cardinality_sweet_low,
            weights.region_cardinality_sweet_high,
        )

        cardinality_confidence = _cardinality_confidence_shrinkage(
            p.non_null_count
        )

        cardinality_score = _shrink_toward_neutral(
            raw_cardinality_score,
            cardinality_confidence,
        )

        state_overlap = _us_state_overlap(
            p.sample_values
        )

        # A column needs at least SOME direct evidence -- a name that
        # resembles "region", or values that look like place names/codes
        # -- before it counts as a region candidate at all. Without this
        # gate, a dataset with genuinely no region column could still
        # manufacture a phantom candidate purely from small-sample
        # cardinality noise, turning "no region in this dataset" into
        # a false "ambiguous, please clarify".
        if header_score == 0.0 and gazetteer_score == 0.0:
            continue

        total = (
                weights.region_header_weight * header_score
                + weights.region_gazetteer_weight * gazetteer_score
                + weights.region_cardinality_weight * cardinality_score
        )

        total -= weights.us_state_penalty * state_overlap
        total = max(0.0, total)

        reasons = []

        if header_score:
            reasons.append(
                f"header text resembles '{matched_syn}' ({header_score:.2f})"
            )

        if gazetteer_score:
            reasons.append(
                f"{gazetteer_score:.0%} of sample values match "
                "known country/region tokens"
            )

        if cardinality_score:
            reasons.append(
                f"cardinality ratio {p.cardinality_ratio:.5f} "
                "fits region-shaped range"
            )

        if state_overlap:
            reasons.append(
                f"values look like US state codes ({state_overlap:.0%}) "
                "-- likely too fine-grained for Region"
            )

        # Inclusion is about REAL evidence, name or value -- not overall
        # rank. This is what makes a column like "Company" (zero header
        # match, but values that are actually country codes) surface as
        # a candidate instead of being silently outranked and truncated
        # by columns that only match on name.
        meets_bar = (
                header_score > 0
                or gazetteer_score
                >= weights.region_gazetteer_inclusion_threshold
        )

        results.append(
            ScoredCandidate(
                column=p.name,
                score=round(total, 4),
                reasons=reasons,
                sample_values=p.sample_values,
                meets_inclusion_bar=meets_bar,
            )
        )

    results.sort(
        key=lambda c: c.score,
        reverse=True,
    )

    return results


@dataclass
class FieldResolution:
    resolved_column: str | None
    needs_clarification: bool
    candidates: list[ScoredCandidate]
    message: str | None = None


def resolve_field(
        candidates: list[ScoredCandidate],
        field_label: str,
        weights: ScoringWeights = ScoringWeights(),
) -> FieldResolution:
    """
    Applies the accept/ambiguous/not-found decision on top of already-
    scored candidates. Shared by project and region resolution so this
    logic isn't duplicated.

    Ambiguity is decided by counting how many candidates clear an
    ABSOLUTE evidence bar (ScoredCandidate.meets_inclusion_bar) -- name
    match OR value match -- not by a fixed top-N cutoff or a relative
    score-margin between 1st and 2nd place.
    """

    if not candidates:
        return FieldResolution(
            resolved_column=None,
            needs_clarification=True,
            candidates=[],
            message=f"No column in the dataset could be identified as {field_label}.",
        )

    qualifying = [
        c
        for c in candidates
        if c.meets_inclusion_bar
    ]

    if not qualifying:
        # Nothing cleared a real evidence bar -- fall back to the single
        # best-scoring candidate, but only accept it automatically if
        # its score is still reasonable; otherwise ask.
        best = candidates[0]

        if best.score >= weights.min_confidence:
            qualifying = [best]

        else:
            return FieldResolution(
                resolved_column=None,
                needs_clarification=True,
                candidates=candidates[
                    :weights.max_candidates_to_display
                ],
                message=(
                    f"Couldn't confidently identify a column for "
                    f"{field_label}. Please choose one."
                ),
            )

    if len(qualifying) == 1:
        best = qualifying[0]

        if best.score >= weights.min_confidence:
            return FieldResolution(
                resolved_column=best.column,
                needs_clarification=False,
                candidates=qualifying,
            )

        return FieldResolution(
            resolved_column=None,
            needs_clarification=True,
            candidates=qualifying,
            message=(
                f"Couldn't confidently identify a column for "
                f"{field_label}. Please choose one."
            ),
        )

    # 2+ candidates cleared the evidence bar -- genuine ambiguity. Show
    # ALL of them (score-sorted), not just a fixed top few.
    return FieldResolution(
        resolved_column=None,
        needs_clarification=True,
        candidates=qualifying[
            :weights.max_candidates_to_display
        ],
        message=(
            f"Multiple columns could represent {field_label} "
            "-- please choose which one."
        ),
    )