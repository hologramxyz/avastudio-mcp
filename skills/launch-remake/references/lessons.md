# Lessons from past films

Read the entry that matches what you see. Each one is a case, not a rule.

## Measuring the reference

- **Gemini's counts.** On Linear Agent it found 5 shots where there are 10, said the film has no audio and missed the dust reveal. Take every count and time from `measure_ref.py`.
- **A window that hides a swap.** On one reference, a window started and ended on different content (a dissolve the measure missed). The window images showed it; split by hand.
- **Stillness varies a lot.** Linear Agent is 87% still; Grok Imagine is 39%. Compare each shot with its own window, never with a number from another film.

## Rendering

- **Waiting with `pgrep -f`** matched its own wait loop and hung until the tool timed out: 10 minutes lost in one test.
- **Workers on a Mac.** A 15 s, 60 fps film took 263 s on an Apple M4 with Metal and 1 worker. Two workers took about 2.5 minutes but lost the end line on every other frame in 2 of 4 renders. An older split render took 12 minutes on an 8-core VM.

## Product and story

- **The motion matched and the product was barely there.** A batch of five openings all copied the reference's first 15 s, which were mostly logo builds, titles and teases. The motion was good, but the product hardly showed. The product-time check in `check.cjs` exists because of this; on the best of the five, with its subjects set by hand, it measured 2% product time, first at 12 s.
- **Every payoff was the same weak asset.** The page had one original-and-remake pair, a third party's footage with sparse early frames. All five used it as the payoff. Rate the hero material before you plan.
- **A live-action reference with no live-action material** opened on a still UI card with no hook. Pick the reference by fit.
- **The pixel text measure misread graphics.** A dot-matrix car read as a 29% line of text and cost a run its fix rounds. The text floor is now measured in the DOM.
- **A film failed the stillness rule for moving more than the reference** (74% against 85%). The rule is now one-sided.
- **A builder's report described a shot that was not in the film** ("the remake playing full frame"; the film showed a progress row). The frame read in step 10 exists because of this.
- **A resumed session for one round of notes cost more than the whole first run,** because it read its long history on every turn. Start notes rounds fresh from `STATE.md`.
- **A 0.5 s white blank frame passed the old black-only blank check.** `qa.py` now finds blank runs on any background colour.

## Sound

- **Music calls.** The first film used 6 ElevenLabs video-to-music calls. With the filtered reference clip, one or two do.
- **Gemini's sound scores were noise:** 6 and 2 of 10 for near-identical mixes, and one mix went from 2 to 9 after small edits. Score with `music_score.py` and say nobody has heard it.
- **After Linear Agent, 0–15.5 s (the sound that was approved by ear):** tone distance 4.0 dB (15.1 with library hits), loudness shape r 0.71, −24.4 LUFS against −25.9, sub share 95.7% against 92.9%, beat strength 0.23 against 0.13.
