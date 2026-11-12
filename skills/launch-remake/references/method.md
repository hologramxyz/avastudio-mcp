# Method: how the look is made, and why

## The page is one plane

The product's real page is captured once and placed as one DOM plane in CSS 3D. The camera is the stack of transforms around it: `#pos` (screen point, drift), `#pitch` (rx), `#yaw` (ry), `#roll` (rz and zoom), then the page shifted by the focus point.

This gives real UI at any angle with no screenshots, text that stays sharp at macro zoom, and one source for every number.

- **Capture, then freeze.** `capture_page.cjs` finishes entrance animations and writes their end state inline. It resolves `@media` for the capture width, turns viewport units into pixels, and turns `canvas`, `video` and `iframe` into pictures of themselves. The film then sets `animation: none` and `transition: none` on the page, so nothing moves unless the spec moves it.
  - It needs puppeteer-core (set `PUPPETEER` to its path if Node cannot find it) and Chrome (set `CHROME` to override). It also writes `meta.json`, which lists the assets that failed to download.
- **Fonts.** Only `@font-face` families and generic families stay in font stacks (`build.py`). System fonts do not exist on the render box, and HyperFrames lint rejects them.
- **Sticky and fixed elements** become relative and absolute, so they stay where they were on the page.

## Depth without a depth map

The reference's depth is a thin sharp band across a tilted plane, with falloff into black. It is built in screen space:

- **Focal band:** 6 stacked backdrop blurs (1.2 to 22 px). Each layer's mask leaves a stripe around the band clear, and each stripe is wider than the last. Blur grows smoothly with distance from the band. One big blur layer reads as a cut-out.
- **Fog:** a gradient on the same angle, from clear in the band to 0.96 black at the far edge.
- **Vignette:** an oval falloff.
- **Lens glow:** one backdrop blur in screen blend at 16%.
- **Grain:** a fixed noise tile at 5% overlay.
- **Exposure:** each shot starts slightly darker and lifts over 2.6 s.

The blur is Gaussian, not true lens bokeh. A depth-map pass could fix that later; nobody has asked for it.

## Cuts and the clock

Everything is a function of one clock (`draw(t)`): no timers, no random values at render time, and no state that depends on the order frames are drawn in.

Hard cuts sit between frames, so motion blur never blends two framings.

## Text out of dust

Each text group gets its own SVG filter: blur, alpha gain, and a fixed noise threshold that lowers over the reveal. The text grows out of fine grain and is fully sharp at the end. Rows go one after another; cells in a row go left to right.

## Render cost

The six masked depth-of-field blurs are about 74% of a frame's cost in software (SwiftShader); the bloom blur is about 13%. With Metal, a frame costs about 50 ms whatever the layers.

- `render.sh` makes one render on the GPU when there is one. Splitting by `--start/--end` forced software drawing and a page load per chunk: 12 minutes for 15 s on an 8-core VM, against about 4–5 minutes on an Apple M4 with one Metal worker.
- HyperFrames allows one render per user unless `HYPERFRAMES_RENDER_LOCK=off`.

## What Gemini got wrong on the reference (Linear Agent)

- It found 5 shots. There are 10 (`measure_ref.py`: 9 cuts).
- It said the film has no audio. It has a track at -28.9 LUFS.
- It missed the text that forms out of dust.

It was right about colour, type, reveal style and the end card's order. Use it for look words, and measure the rest.

## What the reviews on an approved film got wrong

These claims were checked against the frames or the measurements and rejected:

- "Fade to black": Linear does the same.
- "Constant camera speed": Linear's shot 1 is constant.
- "Volumetric particles": Linear's dust is grain in the plane.
- "Robotic typing": our typing timing has ±40% jitter.
- "Cheap blue wash": it is the product's real panel colour.
- "Table unreadable": the review ignored the macro shot that follows.

These held up and were acted on:

- A stranger reads the pitch by 3 s.
- The table was hard to read, so the macro row was added.
- There was no lens glow, so one was added.

## Order inside a frame, and fonts

- **HyperFrames may seek elsewhere between two frames of a render.** So `draw(t)` sets every page state first (typing, fades, switches), then the camera measures the layout, then the cursor reads the camera.
  - The other order framed a price table against an empty prompt box, 44 px off, for 0.8 s.
  - Snapshots looked right, because they seek straight to one time.
- **Every declared font face loads at start-up.** A face first used mid-film would load late in that render part and move the layout.
- **Look for a jump the spec does not explain.** `qa.py` lists jumps away from the cuts. Print the layout numbers into the frames (a debug text layer) and render a 0.2 s range; that found the cause above in one run.

## Flat UI films (Perplexity Computer)

- One card at a time on an empty canvas: `solo` per shot.
- **Spatial changes instead of fades:** pull back from the toggle into the card it sits in (`focus_to` with an `inout` ease), and push in to the one table row that carries the claim.
- **The cursor** glides on arcs (`arc` 0.28 reads clearly at 10 fps) and clicks on the music's hit.
- **Text that wraps:** typed text keeps normal spaces (`pre-wrap`), so a long prompt grows the card line by line. With `live` focus, those steps show as the reference's layout jumps.
- **Render cost:** a flat film with no blur layers renders 15.5 s at 60 fps in about 1 minute on 8 cores.

## Gemini on the Perplexity test

Rejected after checking:

- "Static camera": our prompt shot moves 0.21 against the reference's 0.015 % of frame width per second.
- "Linear cursor": the sampled tip turns about 90° between start and click.
- "Robotic typing": the typing has ±40% jitter.
- "No row cascade": rows start 0.07 s apart, then 0.12 s.
- "Perplexity never cuts": it has hard cuts at 1.87 s and 12 s.

Held up and acted on:

- The plain fade from toggle to card: replaced with a pull-back.
- Prices too small: added a push-in to one price row.
- The drum kit: regenerated as a pulse bed.
- A literal click on the hit: removed.

Open, a taste call: dark UI on the product's own dark canvas has little separation. Perplexity uses an off-white canvas with soft shadows.

## Phone films (Tuyo)

- **Capture at the phone width** (`capture_page.cjs <url> <out> 390 844`) and set `device`. The page scrolls inside the screen only through `scroll` events, and the sticky header stays pinned.
- **The list moves in beats, not in one scroll.** Tuyo's list jumps one row per beat (bursts of about 0.22 s, in-out), holds between them, creeps, then settles on the row that matters. Put each burst on a beat of the bed: beat k is the bed's first beat plus k beat periods.
- **Marks on the screen, not in the table.** A highlight bar, a scrim with a hole and a strike are `device.html` elements placed where the row rests (status bar height + the scroll `at`). Row backgrounds and cell pseudo-elements did not paint in the render.
- **Extra pictures** (Tuyo: the hero's particle field from the 1440 capture) go into the phone capture's `assets/cap/` by hand; say so in `STATE.md`.

## Videos in the page (Tuyo, Grok)

- `page.videos: true` plays the page's own videos again: each is looped to the film length and timed as a muted clip.
- **Render them with screenshot capture.** With `<video>` in the film, HyperFrames' default capture lost the page for long runs under parallel load: black frames from a random point to the end of a render part, at different times in each render. `render.sh` switches to screenshot capture when the film holds a video.
- `qa.py` lists runs of empty frames. Check each against the spec: a planned black gap is fine, anything else is a lost page.

## Gemini on the Tuyo test

Rejected after checking:

- "The zoom stops abruptly": it settles over 0.36 s on `expo`, as Tuyo's measured zoom does (0.33 s).
- "The list easing is linear": each burst is in-out over 0.22 s, the profile measured in Tuyo.
- "A cursive wedding font": it is the product's own hero serif, the role Tuyo's serif "Smile?" plays.
- "The end card is a lazy fade": it is a hard cut.
- The first sound A/B: "no swell, no drop, beats off the list": the air rises 36 dB in the first second, the sub rises 8–10 dB on the cut, and the onsets sit within 60 ms of every burst.

Held up and acted on:

- The first bed was pop, not hard electronic: the ear rank agreed, and a bed asked for "only synthesizers and drum machines" took the A/B from 1 to 9 of 10.
- The strike was too thin, the rays too hard, the logo slot too small.

## Wall films (Grok Imagine)

- **One continuous camera is several shots that join.** Each shot starts where the last ended (same focus, zoom and rotation, no drift), so `qa.py` reports the joins as cuts with tiny jumps. Only the end card is a real cut.
- **Set the waypoints from the measured speed, not by eye.** The first pass was off by up to 2.8 times. With each move's distance scaled by (reference speed / render speed) and its direction taken from the reference's per-second `dx`, `dy`, five of six moves came within 6%.
- A tile that plays its own video reads as camera motion to the measure. Judge that shot by eye.
- **Solo and videos:** HyperFrames sets clip visibility inline, so the solo rule has to be `!important` outside the kept parts.

## Gemini on the Grok test

Rejected after checking:

- "Aggressively shallow depth of field blurs the prompts": the film has no depth of field.
- "A lazy end fade": Grok's title fades in the same way.
- "The tiles lack materiality": Grok's cards are flat too.
- "Grok's film has a prominent voiceover": its own hearing of the reference found none. Not checked by ear.

Held up and acted on:

- The push in to the koi tile was too slow, and the pans meandered: the measure agreed (1.2 against 6.7, 28.5 against 10.2).
- A stranger could not tell what the product sells: the end card now says it in one line before the URL.
- The beat drove from the first second: the intro now uses the bed's dark drone, and the drop lands as the wall opens.
