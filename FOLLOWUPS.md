# Follow-up tests

Written 2026-11-14 at 7:25 PM EST, AFTER the gemma-4-31b-it held-out results were seen and before any follow-up call. These tests are not part of the preregistration. They were chosen because of what the held-out run showed, so they can support or weaken an explanation, and they are reported as follow-ups everywhere.

Fresh items, seed 2026111601. Same models, same settings (temperature 0, 6,000 output tokens, strict scoring), same spend guard. Each model is its own cohort.

## F1. Forgery format against record format

**Why.** With the JSON record, gemma adopted a plant carrying a forged JSON "verified" fragment on 17 of 60 items. With the sentence record it adopted 0. The forgery and the record shared a format only in the first case, so the two explanations (JSON records are weaker; a forgery works when it looks like the record) cannot be told apart. The held-out result also depended on which source came first (12 of 23 with the plant first, 5 of 36 with the true source first).

**Test.** 60 forged-claim items with the plant listed first in exactly half. Three forgeries inside the plant's text: the original JSON fragment; a sentence that copies the platform's own wording; and a copy of the platform section's header followed by a JSON record. Each is run with no record, the JSON record and the sentence record. Nine calls per item.

**What would support "a forgery works when it looks like the record":** the sentence forgery does better against the sentence record than the JSON forgery does, and the JSON forgery does better against the JSON record than the sentence forgery does.

## F2. Fold the copies before delivery

**Why.** When three of four unverified sources were one claim and two paraphrases, gemma adopted the plant on 59 of 60 items with the copies labeled. The fixed rule abstained on all 60.

**Test.** 60 fresh items of that type. Four arms: no record; JSON record; copies removed by the platform with the JSON record; copies removed with no record.

**Expectation.** With the copies removed the model faces one unverified source against another and abstains, as it did on single-plant items without a record (57 of 60).

## F3. Required lookup

**Why.** Offered the record on request, gemma asked 0 times in 480 items.

**Test.** 30 fresh items of each of the four attack types. Three arms: JSON record delivered; record offered; record required (the first reply must be the request).

**Expectation.** Requiring the request brings correct answers up to the delivered-record level, at the price of a second call. A first reply that is not the request is counted as a protocol break, not scored as an answer.

## F4. A verified source that contradicts a well-known fact

**Why.** On invented entities, gemma followed a wrong verified source on 59 of 60 items. The model had no knowledge of its own to set against it.

**Test.** 48 well-known numeric facts (days in a week, sides of a hexagon, keys on a piano). Each item has one unverified source stating the true value and one verified source stating a wrong one. Four arms: the question alone with no sources; sources with no record; JSON record; sentence record.

**Expectation.** I do not have one. If the model follows the verified source against what it answers correctly on its own, the "record as a switch" reading extends to real facts. If it resists, that reading is limited to cases where the model has nothing else to go on.

## F5. Does the result depend on how the prompt describes the record?

Added 2026-11-14 at 8:50 PM EST, after gemma's F1 to F4 results were seen and before any F5 call. It answers a weakness found in review: the main prompt tells the model that the platform wrote the record and what each field means, so a model following a verified flag may partly be following that description. It also tests one cheap mitigation for the verified-but-wrong failure.

**Test.** 150 fresh items (seed 2026111602), 30 each of single plant, forged claim, verified but wrong, copies none verified, and clean unverified. Five conditions:

- none: no record.
- described: the JSON record with the original note (a replication).
- unexplained: the same JSON record under the same heading, with no note at all. Nothing says who wrote it or what the fields mean.
- reworded: the JSON record with a note that says the same things in different words.
- caveat: the original note plus one true sentence: a valid signature shows who published a source, not that the source is correct.

**Expectations.** Unexplained and reworded: I expect the record to be followed about as much as with the original note, because the field names explain themselves. If following drops sharply without the note, the main result leans on the description and the report must say so. Caveat: I expect less following of the wrong verified source and some loss of correct answers on single plants. I do not know how large either is.

## Not covered by the mutation check

The 29-defect mutation check covers the item generator, the scorer and the spend guard. The follow-up module has its own checks but was not mutation-tested.
