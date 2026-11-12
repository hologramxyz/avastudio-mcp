# QA

Every cut gets all three checks before it goes to the person.

## 1. Frames (yours, decisive)
- **Do this on the rendered file.** A snapshot seeks straight to one time; a render plays in order. In one film, a grey box at 1.2 s and flashing cards at 10.2 s were in the render, absent from snapshots, and unnoticed by three Gemini reviews and by a 4 fps strip. Only a person watching the render caught them.
- **Scene entrances:** tile every frame from 0.1 s before each scene shows until its first element has landed. A flash lasts 2–10 frames.
- **Moves:** tile every frame of every move, cut and typing run.
  `bash $X/frames.sh <video> <start> <dur> <out.png>`
  Look for:
  - elements that drop out for a frame or two
  - double exposure
  - smears across a cut
  - layers that do not clear the frame
  - text that jumps
  - a line of text cut by the frame edge, or a card half off screen, where the reference keeps it whole
- **Banding:** stretch the dark levels of the light. `bash $X/frames.sh <video> <t> band <out.png>` crops the top of the frame and applies `colorlevels`. You want smoky texture and no hard steps. Also measure the longest flat run of one value along a line; tens of px is fine, 100+ needs more dither.
- **Overview:** a 3 fps strip of the whole cut for the overall read: `bash $X/frames.sh <video> strip <out.png>`.
- **Length:** ffprobe duration must equal the root `data-duration`.

## 2. Gemini at 10 fps (a list of faults to check, not a score)
- **Its scores do not rank films.** With `film-review.md` it gave the approved films (after Linear and Perplexity) 3–4 of 10 and called both slideshows; rejected films got 4–5. A closeness prompt gave one approved film 4–6 and a rejected one 8–9. Gate on `check.cjs` and `compare.py`, not on these numbers.
- **Run:** `python $X/gemini_review.py <video> <filled copy of $X/../prompts/film-review.md> 10` with `GEMINI_API_KEY` set. The third argument is the upload frame rate; Gemini's default of 1 fps is too coarse for easing. An optional fourth argument sets the model (default `gemini-3.1-pro-preview`).
- **Style note:** fill `STYLE_HERE` with the cut's intent and what is fixed, such as "UI sizes are the shipped app's".
- **Known false claims.** Check each one against the code or the frames before you act:
  - It "hears" speech in muted clips. Confirm the stream count with ffprobe.
  - It calls cuts late. Measured kick onsets were within 10 ms.
  - "The typing jumps in chunks." That is its 10 fps sampling; check every frame.
  - "The button does not react" or "no overshoot". Those last 2 frames; it cannot see them.
  - "Severe banding." That is the upload compression; measure the decoded file.
  - BPMs and timestamps of music events are often wrong.
  - It wants bigger UI text. Check the text sizes that `check.cjs` prints for the shot: under 2.5% of the frame height, Gemini is right.
  - It "hears" typing or click SFX that are not in the mix. List the `<audio>` elements.
  - It calls fast pair transitions "CapCut whips". That is the person's call, not a defect.
  - It calls a 0.3 s morph overlap "a double exposure" and a long dolly "drags". Check the frames: a morph overlaps by design; the dolly's length is the person's pace call.
  - It says a silence is missing. Measure it (`scripts/music/audio_profile.py`).
  - It reviews moves that are no longer in the cut (one film's third review described a "slow orbit" and a "cover flow" that had been replaced, with timestamps 3–4 s off) and calls jittered typing "perfectly uniform". If a note names a move you removed, discard the whole review and run it again.
- **Notes that held up:**
  - cards crossing in no fixed order when they stack (give them a fixed z-order)
  - logo letters that start before the mark has landed
  - dead air (an empty loading state for a beat)
  - an element that looks orphaned during a move
  - a transition where everything starts at once (stagger it, biggest first)
  - double exposure
- **Scores:** they swing from 3 to 6.5 between near-identical cuts (one film: 6.5, 6, 3). Do not chase the score; chase the verified issues.

## 3. Your call, against the reference
Before you send, watch the side by side (`sbs.py`) and read each shot against its reference shot: cut rhythm, camera, reveals and sound. The person decides.

- Usage: `sbs.py <out.mp4> <dur> --tile "file|map|label" [--tile ...] [--passes 0,1] [--gain 0:2.0] [--fps 60]`. The films sit in one row on a 1920x1080 frame, and the film plays once per sound pass.
- `map` places reference pieces on the film's clock, such as `0-11.27@0,45.10-49.0925@11.5075`. An empty map uses the file as it is.
- `--passes` names whose sound plays in each pass, by tile index (default: the last tile only). `--gain` lifts a tile's sound in dB.
- Labels need an ffmpeg with `drawtext`. Without it, the labels are left out.
