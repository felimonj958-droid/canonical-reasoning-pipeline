# Synthetic LR Human Review Rubric

Use this rubric for quick human spot-checks on small synthetic LR batches. The LLM judge handles the detailed scoring; this file is only for fast legitimacy checks before accepting a batch.

## Pass/Fail Checks

1. **Specific flaw match.** The correct answer must fit the stimulus, not just a generic flaw category.
2. **Fresh wording.** The correct answer should not repeat a stock phrase that can be memorized across items.
3. **Plausible distractors.** Wrong choices should be believable and logically close to the correct answer.
4. **One best answer.** Only one choice should clearly win; the other choices should not overlap too much.
5. **No giveaways.** Grammar, length, or wording should not make the correct answer obvious.

## Batch-Level Checks

- **Variety across items.** The batch should not overuse one flaw family.
- **Reasoning coverage.** Mix different reasoning shapes such as causal, conditional, scope, sampling, analogy, and necessity/sufficiency errors.
- **No template feel.** The items should not sound like the same answer pattern repeated with different nouns.

## Decision Rule

- **Keep.** The item is specific, fresh, and hard to game.
- **Revise.** The item is understandable but too templated or too easy.
- **Drop.** The item has a giveaway, multiple plausible correct answers, or a repeated stock flaw label.

## Quick Reference

If a reviewer can memorize the correct answer after seeing one item, the item bank needs more variation.
