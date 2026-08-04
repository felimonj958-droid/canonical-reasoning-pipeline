# Synthetic LR Quality Rubric

Use this rubric to judge whether a synthetic LR item is strong enough to keep in the batch set. The human review rubric is for quick pass/fail checks; this file is for item-quality decisions.

## Core Criteria

1. **Flaw accuracy.** The correct answer must describe the actual reasoning flaw in the stimulus.
2. **Freshness.** The item should not rely on a stock phrase that can be memorized across many items.
3. **Distractor quality.** Wrong choices should be plausible, logically close, and not obviously silly.
4. **One-best-answer strength.** Only one choice should clearly win without ambiguity.
5. **Surface fairness.** Grammar, length, and tone should not give away the answer.

## Templated Item Flags

Revise or drop the item if any of these are true:

- The correct answer is a generic stock phrase repeated across many items.
- The same flaw family dominates multiple items in the batch.
- Two or more choices could reasonably be defended as correct.
- One distractor is obviously weaker than the rest.
- The item is easy to answer from wording alone instead of reasoning.

## Batch Variety Checks

A healthy batch should vary across flaw families such as:

- Causal inference.
- Conditional reasoning.
- Scope shifts.
- Sampling or representativeness.
- Analogy or parallel structure.
- Necessary vs. sufficient confusion.

## Decision Rule

- **Keep.** The item is specific, fresh, and tests real reasoning.
- **Revise.** The item is mostly valid but feels templated or too easy.
- **Drop.** The item has weak logic, weak distractors, or a repeated stock flaw pattern.

## Practical Standard

If a reviewer can memorize the correct answer after seeing one item, the item should be revised unless the batch already has strong variation around it.
