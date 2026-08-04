# Flaw Rubric and Generator Rules

## Rubric

Score each item in four categories, 0 to 2 each.

### 1) Logical correctness
- 2: The keyed choice precisely identifies the flaw in the stimulus.
- 1: Mostly right, but slightly overbroad or slightly underfit.
- 0: Wrong flaw or ambiguous key.

### 2) Key uniqueness
- 2: Only one answer choice cleanly matches the flaw, and no other choice paraphrases it.
- 1: One distractor is close but still clearly worse.
- 0: Two choices are effectively the same, or the key is trivially obvious by wording repetition.

### 3) Distractor quality
- 2: Distractors are plausible, parallel, and drawn from realistic misunderstanding patterns.
- 1: Some distractors are plausible, but one or more are weak or off-topic.
- 0: Distractors are absurd, redundant, or too easy to eliminate.

### 4) Batch diversity
- 2: The item’s flaw family and phrasing are not overused in the batch.
- 1: The flaw family repeats once or the wording feels familiar.
- 0: The same flaw template appears repeatedly across nearby items.

## Pass/fail rule

- Pass if the item scores at least 7/8 and no category scores 0.
- Revise if it scores 5–6.
- Reject if it scores 4 or less, or if any key duplication occurs.

## Generator rule set

### A) Flaw selection rules
- Use a flaw bank with separate buckets: necessary/sufficient, causal, scope, sampling, equivocation, and misc.
- Cap repeated use of any one flaw family per batch.
- Do not allow two adjacent items to use the same canonical flaw template unless explicitly intended.

### B) Key-writing rules
- Do not reuse the same answer template twice in a row.
- Prefer different surface forms for the same flaw family.
- Avoid answer choices that repeat the stem’s exact wording too closely.
- Ban near-duplicate keys within the same item.

### C) Distractor rules
- Each distractor should represent a realistic student error.
- Keep distractors homogeneous in form and similar in length.
- Avoid absurd, off-topic, or throwaway answers.
- Make sure each distractor is wrong for a distinct reason.

### D) Batch diversity rules
- Track the previous 5 to 10 items’ flaw family and key template.
- If a template has been used too often, force a rewrite.
- If two items share both flaw family and phrase shape, regenerate one.

### E) Rewrite triggers
Regenerate the item if:
- Another option paraphrases the key.
- The key is a canonical stock phrase already used recently.
- A distractor is obviously false or irrelevant.
- The item feels answerable by pattern recognition rather than reasoning.

## Suggested prompt language

Write one LSAT-style flaw question. The correct answer must identify the flaw accurately, but do not use repetitive stock phrasing across the batch. Distractors must be plausible, parallel, and mutually exclusive. Reject any item where another answer choice paraphrases the key or where the key is obvious from recurring wording.

## Revision standards:
•	Vary item structure, topic, and wording so no flaw type becomes visually or syntactically memorable.
•	Avoid repetitive answer-choice formats, ordering, or distractor patterns.
•	Include near-miss distractors that are plausible but distinguishable through careful reasoning.
•	Ensure correct answers depend on comprehension of meaning, not recognition of a familiar template.
•	Check that each item can be justified in plain language, not just selected by pattern matching.
Quality check: If a test-taker can answer mainly by recalling the previous items, the bank is too repetitive. If the item requires careful reading, interpretation, and explanation of why alternatives are wrong, it meets the intended standard.