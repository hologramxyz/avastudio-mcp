---
name: launch-remake
description: Make a launch video for a product by remaking a viral launch film's cuts, camera, depth, text reveals and sound, built in HyperFrames from that product's real page. Capture the product first, pick the reference that its material can fill, measure the reference, write a film spec, check it, render, score the render against the reference, then deliver it side by side. Use when someone asks for a launch video or a product launch film (such as "make a launch video for <url>"), a launch video "in the style of" a reference film, or the mograph_rebuild path of Ava's launch style library.
---

# Launch remake

The film moves like the reference: the same cut rhythm, camera speeds, depth, reveals and sound. On screen is the new product's real page, copy and prices, and the product fills most of the film. Motion that copies the reference well but barely shows the product is a failed film.

Read `references/hyperframes-gotchas.md` and `references/qa.md` first. They hold the render traps and Gemini's known false claims. This skill adds the remake method on top of them.

## Rules

- **Measure first, then copy.** Cut times, camera speeds, focus and sound come from `measure_ref.py`. Do not use the library's `beats`, which are evenly spaced estimates, and do not take counts or times from Gemini.
- **Product truth.** Capture the product's page. Take every number and line of copy from its source code or live page. Never draw a fake UI, invent a number or make a stand-in for the product. Pills, chips, cards and lists show the product's real content (features, plans, results), never nav links, footer links or legal text.
- **Product share.** The product (its real UI in use, its real output, or the product itself) fills at least 25% of the frame for at least half of the film, and first does so by 3 s. `check.cjs` measures this. Titles, stats, step cards and headlines are short beats between product shots.
- **Copy the structure, not the content.** Keep the reference's structure, pacing and look. Never copy its product, people, claims or words.
- **Third-party material.** Footage, posters and logos of other companies on the product page are not the product's own. They cannot be the hero or the payoff without the person's OK.
- **Credit the reference** in every side by side.
- **The sound is a style match.** Video-to-music uses the reference's audio as its style input, so the person must clear it before anyone posts.
- **Paid calls.**
  - Say the count per model before you run them.
  - Start with the smallest test.
  - Keys come only from the environment (`GEMINI_API_KEY`, `ELEVEN_LABS_API_KEY`). Never print them.
  - With no ElevenLabs key, make the music through Ava (`audio_generate`, `references/sound.md`). With no Gemini key, do the Gemini steps yourself from the frames and the numbers.
- **Opening first.** Build a 9–15 s opening and wait for the person's OK. Then build the full film.
- **Ask once, then work.** Put every question in one message (step 4). If the person asked for no stops, decide yourself and say what you chose in the delivery.
- **Say where you are.** At each new step, say the step and the time since the start. Say a file is ready only after it exists and has the right frame count.
- **Scripts give the verdicts.** `check.cjs` (product and quality) and `compare.py` (motion match) print their verdict and exit non-zero on a failure. Never report a pass that a script did not print.

## Inputs

- **The product page:** the URL of the running page. A local dev server works.
- **The reference video,** if the person names one: the `video_url` from `launch_style_get`, or a file. Also keep its title and `post_url` for the credit.
- **The film's words:** the one message, the claim, the CTA, and the source of every number.

## Process

Run from a work folder that holds `refs/`, `page/`, `film/` and `out/`. `X` is this skill's `scripts/` folder. `python` below means the `PY` that `doctor.sh` prints: a venv with numpy and OpenCV.

1. **Before you start.**
   - Run `bash $X/doctor.sh`. If it reports a missing tool, run `bash $X/setup_mac.sh` on a Mac or `bash $X/setup_linux.sh` on a fresh Debian or Ubuntu VM, then run the doctor again. Use the `PY` it prints for every Python step.
   - Check your Ava tools. You need `launch_style_list`, `launch_style_get`, `brand_get`, `library_upload_url`, `audio_generate` and `jobs_get`. If `library_upload_url` or `audio_generate` is missing, the connection is Read only. With Sign in with Ava, ask the person to connect again (`/mcp`) and keep Full access or choose Custom with Produce media. With an API key, ask them to set the key to Custom in Ava Studio > Settings > Developers, with Account, Read brands, Read campaigns and Produce media (and Edit brands to create a brand). If `launch_style_list` itself is missing, call `whoami`: if the connection lacks Read campaigns, connect again with it; otherwise the Ava server is older than the skill, so say so and stop.
   - A `GEMINI_API_KEY` is optional. Without it, read the frames yourself.
   - Call `whoami`. The opening's music is 1 track, about 18 credits (held at the 30 s price). New accounts get 500 starter credits after their first brand.
   - If you do not have the product page or the aspect ratio, ask for them now. They are the only questions before the capture. With no stops, use 16:9.
2. **Capture the product and decide the hero.**
   - Capture: `NODE_PATH=$(npm root -g) node $X/capture_page.cjs <url> page 1440 900`. For a film on a phone, capture at the phone's width (`references/spec.md`, "device"). It writes `page.html` and `page.css` (frozen as captured: entrance animations finished, media queries resolved, viewport units turned into pixels), `assets/`, `page.png` (the full page) and `boxes.json` (the page-pixel box of every heading, button, field, table cell and element with an id).
   - Write `film/material.md`: one row for each thing the film could show. Give its type (UI screen, screen recording, output media, photo, logo, number, copy), its pixel size, its length and whether it moves, its owner (the product's own or a third party), and whether it shows the product working.
   - Decide the hero, the thing that shows the product best:
     - software with a UI: one real task done on screen, from start to result
     - a product that makes media or documents: its best finished output, full frame
     - a physical product: the product itself in real photos or footage
     - a service or an API: the result the customer gets (a real response, a real number), shown large
   - The hero's shots are `product` shots. `proof` is a second fact, such as a number.
   - Rate the hero material: its pixel size against the frame (it goes soft past about 1.5 times its pixels), how much it holds, whether it moves, and its owner. If it is weak (small, sparse, one asset only, or a third party's), say so in step 4 and ask for better material. With no stops, say so first in the delivery.
3. **Choose the reference by fit.**
   - If the person named a reference, still do this step for it, and state its gaps before you build.
   - Otherwise list candidates with `launch_style_list` (`mograph_rebuild`, the film's aspect ratio). For the best 3–5, read the summary and look at the poster or a 1 fps sheet. Write what each part of the film shows (UI close-up, full-frame media, many tiles, live action, type only, logo) and for how many seconds.
   - Fit is the share of those seconds that your material can fill with real assets of enough size. A reference that is mostly type, logo or live action leaves little room for the product.
   - Pick the best fit. Keep the next two as swaps, each with its fit and its unfilled parts.
4. **Ask once.** In one message, ask for the one message and the CTA, opening only or full film, and a spend limit. Show the hero and its rating, the reference (poster, credit, `post_url`, fit, the parts the material cannot fill) and the two swaps, and any third-party material you want to use. State both costs: about 18 Ava credits for the opening's music, and your own usage (see "Cost per opening").
5. **Get and measure the reference.**
   - `curl -L -o refs/<ref>/source.mp4 "<video_url>"`, then `python $X/measure_ref.py refs/<ref>/source.mp4 refs/<ref>`.
   - `ref.json` holds:
     - the cuts, and the layout jumps. In a layout jump, the whole UI shifts at once (a card grows a line) but the flow still tracks it, so it is not a cut.
     - for each shot: camera speed in % of frame width per second (start, median, end), direction, zoom and roll
     - `windows`: each window is one move, one hold or one transition (a whip, a blur or a dissolve). Cuts, layout jumps, transitions and the start or end of each camera move split the film, so a film with few cuts still gets its parts. Each window gives `t0`, `t1`, `kind`, `enter` (start, cut, jump, transition or continuous), median and peak speed, direction, zoom, still % and `ease`.
     - focus: how much sharper the sharpest cell is than the median, and where it sits
     - the palette, stillness per second and the sound profile. If it has no sound profile, the reference has no audio: the music uses prompt mode.
   - `sheet.jpg` shows 1 frame per second. `shots/sNN.jpg` and `windows/wNN.jpg` show the start, middle and end of each shot and each window, with times.
   - Look at every shot and window image before you plan. If a window starts and ends on different content, the measure missed a dissolve or a swap there. Split that window by hand.
   - To see exact frames: `python $X/measure_ref.py refs/<ref>/source.mp4 refs/<ref> --grab 3.29,3.33,3.38`. It writes labelled stills and `sheet.jpg` to `refs/<ref>/grab/` in about 1 s, and does not measure again.
6. **Read the look (optional, 1 Gemini call).** Make a 720p proxy, then run `python $X/gemini_review.py proxy.mp4 $X/../prompts/ref-read.md 10`. Without a key, answer `$X/../prompts/ref-read.md` yourself from `sheet.jpg` and the shot images. Use it for look words only: colours, how text arrives, type, light. Check every count, time and sound claim against `ref.json`.
7. **Plan the opening.**
   - **The opening is a condensed cut, not the reference's first 15 s.** Take a hook, then the reference's strongest windows that can show the product, from anywhere in the film, then the end line. Keep each window's own motion and the uneven cut rhythm. Keep the reference's order unless it leaves the product off screen.
   - **Plan the product time.** Give each shot a `subject`: `product`, `proof`, `brand` or `other`, with the element that shows it. Product shots fill at least half of the film, and the first one starts by 3 s.
   - Show three things: the one message, the hero, and one proof (a number, a table, a result).
   - Show output as finished work: a finished piece playing, never a loading or progress state.
   - Map the reference's moving subject to a moving real asset of the product: footage to its real videos, flying objects to its real thumbnails or cards, particles to its real tiles or UI parts. A shot that holds a still card where the reference moves is a slideshow.
   - **A shot with no real material:** use another reference window that the material fits. If none fits, drop the shot and retime. If several shots have no material, go back to step 3 and change the reference. Never fill the gap with a drawn or generated stand-in for the product.
   - End on the product's line.
   - Start the music now (step 11). It needs only the reference's audio and the film's length, and Ava's video-to-music takes about 10 minutes.
8. **Write the spec.**
   - `film/spec.json` is the machine version (`references/spec.md`). Start from `$X/../templates/spec.json` and set every value from your own plan and measurements.
   - `film/SPEC.md` is the human version: the hero, the reference and its fit, and each shot with its reference window, subject, measured numbers and the real data it uses.
9. **Build and check, before any render.**
   - Build: `python $X/build.py film/spec.json page film/<name>`.
   - Check: `NODE_PATH=$(npm root -g) node $X/check.cjs film/<name>`. It prints each shot's subject size, biggest text and media count, then the product time. It fails on:
     - a shot target or subject that is missing, hidden or off screen; images or video files that do not load; fonts that fail
     - a shot with no `subject`
     - product time under half of the film, or the first product shot later than 3 s. A `product` subject counts while it is visible at 25% of the frame or more, or spans 80% of the frame's height or width at 10% of its area or more (a phone or a bottle in a wide frame)
     - focus text under 2.5% of the frame height (too small on a phone), or a `proof` subject's text under it when the focus is a page point
     - a subject that is not visible, or is covered by an opaque title or the end card
     - a `product` or `proof` subject more than 25% outside the frame, unless the shot has `"bleed": true` because the reference cuts its subject too
     - the subject's image or video, over 10% of the frame, drawn above 1.5 times its pixels (soft). For a recording that is mostly text (a terminal, a chat), set its exact words as live type in its font and colours, timed to the recording.
   - Lines that start with `note:` are for you to judge, such as readable text cut by the frame edge.
   - Lint: `(cd film/<name> && npx hyperframes lint)` (0 errors).
   - Look: `(cd film/<name> && npx hyperframes snapshot --no-end --at <mid of each shot, each event>)`. Fix framing in the spec, rebuild and check again, until every still frames the right thing.
10. **Draft render, motion match and frame read.**
    - Drafts run at 30 fps, which halves the frames: `python $X/build.py film/spec.json page film/<name>-d --fps 30`, then `bash $X/render.sh film/<name>-d out/<name>-d.mp4 "" draft`. Run it in the foreground with a 10-minute tool timeout. It checks the frame count and runs `qa.py`.
    - Measure: `python $X/measure_ref.py out/<name>-d.mp4 out/<name>-d-m`. Compare: `python $X/compare.py refs/<ref> out/<name>-d-m film/spec.json`. It takes the frame rate from the render, sets each shot against its `ref_window` or `ref` shot, then prints `motion match: pass` or `motion match: FAIL` with the reasons.
    - It fails on:
      - `STILL`: a shot over 25 points stiller than its reference window. Look at what moves in the reference's shot images and move a real asset of the product the same way: play its videos, move the camera across its UI, bring its thumbnails or cards in on the reference's paths.
      - `EMPTY`: a shot that holds a blank frame (fill under 1%) more than 0.2 s longer than its reference does. Bring the next element in before the last one has gone.
      - the film over 10 points stiller than the reference windows it uses. More motion than the reference is not a fault.
      - a shot with no `ref` or `ref_window`, or no shot compared at all.
    - Its hints (`less fill`, `smaller text`) come from pixels and can be wrong. Check them on the frames; the text floor in `check.cjs` is the rule.
    - **Fix only the shots that miss.** Change the spec, then rebuild only those shots as a window from the cut before them to the cut after them: `python $X/build.py film/spec.json page film/<name>-dw --window <a>,<b> --fps 30`. Render it, measure it and compare with `--window <a>,<b>`. When it matches, put it into the draft: `python $X/splice.py out/<name>-d.mp4 out/<name>-dw.mp4 film/<name>-dw out/<name>-d.mp4`.
    - Stop after 3 rounds.
    - **Frame read, while a fix round is left.** Write the frames into a new folder for each round: `rm -rf out/read-<round> && mkdir -p out/read-<round> && ffmpeg -i out/<name>-d.mp4 -vf "select='not(mod(n\,15))',setpts=N/(2*TB)" -r 2 -q:v 3 out/read-<round>/f%03d.jpg`. The draft is 30 fps, so frame N is at exactly (N − 1) × 0.5 s. Start a fresh agent with no build context. Give it only the `out/read-<round>` folder and `$X/../prompts/frame-read.md`, never the spec or your notes. Compare its notes with the shot table in `SPEC.md`. Each mismatch is a fault: a `product` shot it does not read as the product, a payoff that reads as a loading state, text cut by the edge, a blank. Fix it, or list it in the delivery. If you cannot start a fresh agent, write what each frame shows before you open `SPEC.md` again, then compare.
11. **Make the sound** (`references/sound.md`). One track for the opening: video-to-music from the reference's filtered audio (or prompt mode), with an input of the film's length plus at least 5 s (up to 30 s), arranged to the cut, then tone and loudness matched. Make a second track only after the person approves the picture. Score it with numbers only: tone distance, loudness and the hit on the cut. Say in the delivery that nobody has heard it.
12. **Delivery render.**
    - Build at the spec's frame rate: `python $X/build.py film/spec.json page film/<name>`, run `check.cjs` once more, then `bash $X/render.sh film/<name> out/<name>-raw.mp4`.
    - `render.sh` renders on the GPU when there is one, checks the frame count and runs `qa.py`. If it finds one-frame flashes or drops, it renders again without the GPU. If flashes remain, it exits with code 3 and lists them: look at those frames and go on only if the spec plans them. Never wait on a render with `pgrep -f`.
    - `qa.py` writes `cut-N.jpg` (the frames around each cut), a strip and `qa.txt` to `out/<name>-raw-qa/`. It lists jumps away from the cuts, flashes, and blank or near-blank runs on any background colour. Look at each image and each run.
    - Measure and compare the delivery render once (step 10). Mux the sound.
13. **Side by side and review.**
    - Side by side: `python $X/sbs.py` with the reference on the left.
    - Watch it against the reference, shot by shot: cut rhythm, camera, reveals and sound. If a change since the draft touches a shot the frame read covered, read those frames again.
    - Optional: Gemini on a 720p proxy of the side by side with a filled copy of `$X/../prompts/film-review.md`, as a list of faults to check. Its scores do not rank films.
14. **Deliver.**
    - If `check.cjs` or `compare.py` still fails after 3 rounds, start your message with `FAILED GATE:` and the open failures. Call the film a draft. If the person asked for a slow tease or a very short opening, report a failed product-time or 3 s line as their choice instead.
    - Send the film and the side by side with its credit line.
    - Send `SPEC.md` with the hero, the reference and its fit, both verdicts as the scripts printed them, the frame-read mismatches, what you rejected, and the cost from the job receipts.
    - Write `STATE.md` for the next round: the paths (page, reference, spec, film, music), the last verdicts, what is approved, what is open, and the receipts. A notes round starts a fresh session from `STATE.md`, `spec.json` and the notes. Do not resume the long build session: it reads its whole history again on every turn.
    - Then stop for the person's call.

## The gate

These are floors. The person's eye decides.

| Check | Where | Floor |
|---|---|---|
| Product time | `check.cjs` | a `product` subject at 25% of the frame or more (or spanning 80% of its height or width) for half of the film, first by 3 s |
| Text | `check.cjs` | focus text at 2.5% of the frame height or more |
| Edges | `check.cjs` | no subject more than 25% outside the frame, unless `bleed` |
| Sharpness | `check.cjs` | no subject image or video drawn above 1.5 times its pixels |
| Motion | `compare.py` | no `STILL` or `EMPTY` shot; the film at most 10 points stiller than its reference windows |
| Camera | `compare.py` table | each shot's median speed within about 15% of its window, in the same direction family, with the same ease |
| Focus | shot images | the band in the same place and of the same width as in the reference; `focus.grid` runs high on dark frames |
| Frame read | step 10 | no mismatch left with the spec |
| Sound | `music_score.py`, `audio_profile.py` | third-octave distance under 6 dB, loudness within 2 LU, about the same sub share |

## Cost per opening

- **Ava credits:** 1 music track, about 18 credits.
- **Gemini (optional):** about 3 calls: 1 reference read, 1 sound hearing, 1 film review.
- **Render:** a 15 s film at 60 fps takes about 4–5 minutes on a Mac with a GPU. CPU-only machines are several times slower. A 30 fps draft has half the frames. A window of a few shots takes about 30 s plus about 0.25 s per frame.
- **Your own usage:** a fresh agent at xhigh effort on a CPU-only machine typically takes about 45–100 minutes and $13–17 of Claude tokens per opening. About half of the time goes to renders, measuring and waits.

## What the runtime can do, and how to add a move

`scripts/runtime.js` plays these moves, each from one clock:

- **Camera:** the page as one 3D plane under a cut camera, with drift and a settling start.
- **Depth:** a focal band made of stacked masked backdrop blurs, fog into black, a vignette, a lens glow and grain.
- **Dust:** text that forms out of grain.
- **Typing:** typing into a real field.
- **Press:** a button press.
- **End line:** a one-line end card. The word blurs in with a sheen, then the line wipes in.
- **Flat UI moves:** solo shots with one card on an empty canvas; overlays for titles and the real logo lockup; fades with blur, scale and slide; attribute switches, such as a tab changing on a click; a cursor that glides on arcs and clicks.
- **Phone moves:** a phone around the page (`device`) with markup on its screen; a scroll inside the screen with motion blur and a pinned header; a CSS value that runs over time (`prop`) for sheens, strikes and gradient text; a camera move that finishes early and holds (`move_d`); the `expo` and `back` eases.
- **The page's own videos** play again (`page.videos`), for a wall of clips or a demo recording.

Some references move in other ways still, such as a cover flow. For one of those, add an event type:

1. Write `EVENTS.<name> = (ev) => (t) => { ... }` in `runtime.js`. Every value must come from `t`.
2. Put any static markup it needs in `build.py`.
3. Document its fields in `references/spec.md`.
4. Use `x-` tags for any element you add to the page, so the page's own CSS cannot style it.

Add a move only when a film needs it, and keep the moves that films repeat.

## Files

- `scripts/measure_ref.py`: cuts, windows, camera, focus, palette, stillness and sound of any film. `--grab` writes exact stills.
- `scripts/capture_page.cjs`: freezes a live page into markup, CSS and local assets.
- `scripts/build.py` and `scripts/runtime.js`: turn the spec and the page into a HyperFrames project. `--fps` builds a draft at another frame rate.
- `scripts/check.cjs`: checks a built film before any render: targets, images, fonts, product time, text size, edges and sharpness.
- `scripts/render.sh`: one render on the GPU when there is one, the frame count, `qa.py`, and safer retries on flashes. The fourth argument is the quality (`draft` or `delivery`).
- `scripts/qa.py`: tiles every cut, finds jumps, flashes and blank frames.
- `scripts/compare.py`: compares the render with the reference, shot by shot, and prints the motion match verdict.
- `scripts/splice.py`: puts a window render back into the film at its frames.
- `scripts/sbs.py`: the side by side. Reference pieces are placed on the film's clock; one pass plays per sound.
- `scripts/frames.sh`: tiles every frame of a window, a banding crop, or a strip (`references/qa.md`).
- `scripts/gemini_review.py`: one Gemini call on a video at a real frame rate.
- `scripts/doctor.sh`: checks the machine. `scripts/setup_mac.sh` (Homebrew) and `scripts/setup_linux.sh` install what it needs.
- `scripts/music/`: measure, generate, arrange and match the sound (`references/sound.md`).
- `templates/spec.json`: the starting spec.
- `prompts/`: the reference read, frame read, film review, sound hear and sound rank prompts. Fill the `{...}` fields.
- `references/hyperframes-gotchas.md`: render traps in HyperFrames.
- `references/qa.md`: the frame checks, and Gemini's known false claims.
- `references/spec.md`: every spec field, its unit, and how to read it off the measurement.
- `references/sound.md`: the sound steps and levels.
- `references/method.md`: how the look is made and why.
- `references/lessons.md`: what went wrong in past films, by symptom. Read the matching entry when you see that symptom.
