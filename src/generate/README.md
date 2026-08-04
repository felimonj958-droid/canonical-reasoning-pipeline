# Generation Helpers

This package contains the synthetic LR content generation, parsing, validation, and content-quality checks used by the live pipeline. It is the upstream source of the payloads that the normalize layer turns into canonical records.

## What this package does

The generation layer is responsible for:

- building prompts for synthetic LR item generation,
- sending requests through the LLM client,
- cleaning and parsing raw model output,
- validating the payload structure,
- running lightweight content-quality checks before canonical mapping.

## Files

### `synthetic_lr.py`
Synthetic LR generation and parsing helpers.

Main responsibilities:
- build the generation prompt,
- clean raw model output,
- call the active LLM backend,
- parse generated text into a structured payload.

Key functions:
- `build_synthetic_lr_prompt`
- `clean_synthetic_lr_output`
- `generate_synthetic_lr`
- `parse_synthetic_lr_output`

### `validation.py`
Basic structural validation for the synthetic LR payload.

Main responsibilities:
- verify required fields,
- validate the item shape,
- return a structured validation result.

Key function:
- `validate_synthetic_lr_payload`

### `content_quality_checks.py`
Heuristic quality checks that score or flag obvious generation issues before mapping.

Main responsibilities:
- check length and style constraints,
- detect meta-language or templating,
- flag weak argument or choice construction,
- produce a content-quality result for downstream routing.

Key functions:
- `run_content_quality_checks`
- `check_lengths`
- `check_meta_language`
- `check_question_style`
- `check_argument_signals`
- `check_choice_quality`
- `check_choice_templating`
- `check_flaw_label_leakage`
- `check_reasoning_centeredness`
- `compute_quality_score`

## Dependency flow

This package depends on:

- `src.llm_client` for model calls,
- `src.persist.models` indirectly through the normalize layer.

It is used by:

- `src.normalize.run_synthetic_lr_lane`
- `src.normalize.run_synthetic_lr_batch` indirectly through the lane

## What to inspect first

If you are debugging generation quality, inspect these files in order:

1. `synthetic_lr.py`
2. `validation.py`
3. `content_quality_checks.py`
4. `src.normalize.run_synthetic_lr_lane`

## Commands

Run the generation-related tests:

```bash
pytest -q tests/test_synthetic_lr.py tests/test_synthetic_lr_integration.py tests/test_synthetic_lr_validation.py tests/test_content_quality_checks.py
```

Inspect key generation functions:

```bash
grep -R "def build_synthetic_lr_prompt\|def generate_synthetic_lr\|def parse_synthetic_lr_output\|def validate_synthetic_lr_payload\|def run_content_quality_checks" -n src/generate
```

## Notes

- This package is the first place to look when item phrasing, distractor quality, or parsing behavior changes.
- Keep generation logic here and orchestration logic in `src.normalize`.
- If prompt design changes, update the evaluation docs as well because judge performance often tracks generation shape.
