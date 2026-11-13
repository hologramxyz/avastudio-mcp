# spec.json

`build.py` reads it. Start from `../templates/spec.json`.

## Time

- **Shot starts are numbers, and they snap.** Every shot's `t0` after the first snaps to the middle between two frames: `(round(t*fps)+0.5)/fps`. That way, motion blur never blends two framings at a cut.
- **Marks snap too.** `marks` names extra snapped times, such as `"end": 11.5`.
- **Any other time field can be an expression.** It can use `cut1..cutN` (the snapped shot starts), any mark, and `dur`. Examples: `"cut3-0.34"`, `"cut1+0.62"`, `"end"`.
- **The real cut times** are written to `<project>/build.json`. Use them for the sound spec.

## Top level

- `size`: `[1920, 1080]`. `fps`: 60 (the motion is slow and fine, so 30 fps judders on drift). `dur`: in seconds.
  - `build.py ... --fps 30` builds a draft at 30 fps for measuring. `measure_ref.py` samples about 30 fps, so the numbers hold. Deliver at the spec's rate.
- `reference`: the title, style id and `post_url` for the credit. `brand_url`: the captured page. Both are notes; the build does not use them.
- `marks`: named times. They snap like cuts.

## page

- `hide`: selectors to hide. Their space stays. Use it for buttons, logo rows and anything that is not part of the story.
- `drop`: selectors to remove. Their space closes. Use it for sections after the last one you show, and for canvases that were captured as images.
- `css`: extra CSS after the page's own CSS. Use it for fixes such as `.hero { min-height: 0 }`.
  - A dust group wraps the text it reveals, so a child selector such as `.title > span` stops matching. Restate the rule, for example `.title .dp span { color: ... }`.

## overlays

Screen-space layers above the page: titles, an "Introducing" line, a logo lockup. Each one is `{id, html?, clone?, css?}`. Hide one until its entrance with a `fade`.

- `clone` copies page elements, such as `".site-header .logo"`, so the logo is the product's real one.
- Overlays and clones sit inside copies of the page's ancestors (with `display: contents`), so the page's CSS still styles them.
- Overlays run no page CSS animations or transitions, and the page ancestors copied around them draw no `::before` or `::after`.
- Each overlay is a centred flex column. Use `order` to stack its parts, and CSS `zoom` (not `scale`) to enlarge a clone so its text stays sharp.

## device (optional)

A phone around the page, for films that show the product on a phone (Tuyo). Capture the page at the phone width (`capture_page.cjs <url> <out> 390 844`).

- `screen`: `[390, 844]`, the screen in page px. `bezel`: 12. `radius`: 58. `top`: 50, the status bar height; the page starts under it.
- `html`: markup on the screen above the page (it does not scroll), such as a big price that pops in. Style it in `page.css`.
- `time`: `"9:41"`, the status bar clock. `bg`: the screen colour behind the status bar (`#121212`). `frame`, `edge`: the body and rim colours.
- The page scrolls inside the screen only through a `scroll` event. Sticky parts of the page, such as the header, stay pinned at the top of the screen.
- **Focus is in phone px:** `[0, 0]` is the phone's top left corner, and the screen starts at `[bezel, bezel]`. A page element's place on screen is its page y minus the scroll, so use px focus on the phone, not a page selector.

## look (optional, defaults in build.py)

- `bg`: `#000`. `perspective`: 1050 (px). `origin`: `[50, 46]` (perspective origin, %).
- `edge`: the box-shadow line around the page plane.
- `dof.offsets`: `[0, 3, 7, 12, 18, 26]`. `dof.blurs`: `[1.2, 2.4, 4.5, 8, 14, 22]` (px). `dof.ramp`: 6.
  - These are the 6 stacked backdrop-blur layers. Each one starts the given % further out from the sharp band.
- `fog`: `{far 0.96, far_at 42, near 0.6, near_at 16}`. This is the darkness at that many % outside the band.
- `vignette`: `{size [66, 74], inner 52, dark 0.86}`.
- `bloom`: `{blur 18, bright 1.5, opacity 0.16}`, a lens glow in screen blend.
- `grain`: 0.05, the noise overlay opacity.
- `expo_s`: 2.6, the seconds a shot takes to lift from its `expo` start value.
- `dust`: `{d 1.25, grain 1.9}`, the default reveal length (s) and noise frequency.
- **A flat look** (a 2D UI film such as Perplexity Computer): set `"dof": {"offsets": [], "blurs": []}`, `"fog": {"far": 0, "near": 0}`, `"vignette": {"dark": 0}`, `"bloom": {"opacity": 0}`, `"grain": 0` and `"edge": "none"`, and leave `rot` at 0. It also renders about 8 times faster.

## shots

Each shot has a camera. The page point `focus` sits at screen point `at`. The plane turns around that point, then drifts.

- **`t0`, optional `t1`:** the shot's start, and its end when the shot does not end at the next shot's start (for example `"end"`).
- **`ref`, `ref_window`:** the reference shot index it copies, or `[start, end]` in the reference. `compare.py` measures that part of the reference. Use `ref_window` when a reference shot is long and the film copies part of it.
- **`subject`:** what the shot shows and which element shows it: `{"kind": "product", "sel": "...", "text": "...", "nth": 0}`.
  - `kind`: `product` (its real UI in use, its real output, or the product itself), `proof` (a real number, table or result), `brand` (a logo, a title, the end card) or `other`.
  - The element form is as in `focus`. Without `sel`, the subject is the focus element; a shot whose focus is a page point needs a `sel`. The end card is `#end`.
  - `check.cjs` measures the product time from it: the seconds where a `product` subject is visible at 25% of the frame or more, or spans 80% of the frame's height or width at 10% of its area or more. Pick the element that holds the product (a video, a panel, a card), not a small label or a whole section around it.
  - The hero is always `product`, even when it is a number or a response (an API's result). `proof` is a second fact.
  - In `device` mode the product is the phone screen: use `{"kind": "product", "sel": "#screen"}`, or an element inside it.
- **`bleed`:** `true` when the reference also cuts its subject with the frame edge. Without it, `check.cjs` fails a subject that is more than 25% outside the frame.
- **`solo`:** a list of page selectors. Only those parts of the page show in this shot; everything else, the page background included, is hidden. `[]` hides the whole page (for titles and the end card).
- **`focus`:** in page px (the top left of the captured page is `[0, 0]`, at the capture width), or an element.
  - The element form is `{"sel": "...", "text": "...", "nth": 0, "ax": 0.5, "ay": 0.5, "dx": 0, "dy": 0, "live": false}`.
  - `live: true` measures the element every frame, so the camera follows a card that grows while text is typed into it. The card's steps show as small jumps, as in the reference.
  - `text` keeps only matches that contain it. `ax` and `ay` are the anchor inside the element's box.
  - The element form uses layout offsets and ignores CSS transforms, such as a marquee frozen at `translate(-444px)`. For an element moved by a transform, focus on its page px from `boxes.json`, which holds where it shows.
  - At high zoom a small focus move moves the frame a lot: 22 page px at 9-13x zoom made a whip 93% too fast. Check the move in screen px: page px times zoom.
- **`focus_to`, `ease`:** a move inside the shot. The focus point travels to `focus_to` while `zoom` runs, both on `ease` (`linear` by default, or `in`, `out`, `inout`). Use it for a spatial transition, such as pulling back from a toggle to the card it sits in, or pushing in to one table row.
- **`move_d`:** the seconds the `zoom` and `focus_to` move takes; the camera then holds. Without it, the move runs over the whole shot. Use it for a fast zoom that settles (Tuyo: 0.35 s on `expo`).
- **`at`:** the screen px where the focus point sits at the shot's start.
- **`rot`:** `[rx, ry, rz]` in degrees. `rx` tilts the plane back (40–55 reads as a desk-angle UI), `ry` turns it sideways, and `rz` rolls it.
- **`zoom`:** `[start, end]` scale of the plane, linear over the shot.
- **`drift`:** `[x, y]` in % of frame width per second. This is how the content moves on screen.
  - Take it straight from the reference shot's `vel_pct_w_s` in `ref.json`. That is measured content motion, so the sign carries over.
- **`drift0`, `tau`, `rv`:** a settling start. Speed begins at `drift0` and eases to `drift` over about `3 * tau` s, and the roll grows by up to `rv * tau` degrees as it settles.
  - Use it when the reference shot's start speed is well above its end speed.
- **`dof`:** the sharp band, a stripe across the frame.
  - `angle`: the gradient angle in degrees. 160–180 is a band across a plane tilted back.
  - `center`: `[start, end]`, the band's place in % along that angle.
  - `width`: the half width in %. 5–7 is tight, 10 is loose.
  - `rack`: `[t0, t1]` moves the band from start to end in that window (a focus pull). Without it, the band moves over the whole shot.
  - Read the band from the reference shot's image and its `focus.grid` (sharpness per cell, 6 by 4). `sharpest_pct` is where the band sits. `ratio` runs high on dark frames, so it is only a hint.
- **`vignette`:** `[x, y]`, the vignette centre in %.
- **`expo`:** `[start, end]`, the black overlay opacity. A shot that starts darker reads as an exposure settling after the cut.

## events

All times are absolute seconds or expressions.

- **`dust`:** text forms out of fine grain.
  - `sel`: the elements. `t`: the start.
  - `step`: the delay between matched elements. `d`: the length (default 1.25). `blur`: 1 by default; 2.2 for big titles.
  - `split: "br"`: each line of one element (split at `<br>`) is its own group, `step` apart. `split: "word"`: each word is its own group, `step` apart.
  - `sel` matches the page first, then overlays.
  - `cells: "th, td"`: each cell of each matched row is its own group. The delay is `t + row * step + cell * cell_step`.
- **`type`:** typing into a field.
  - `target` is an element (as in `focus`). A textarea or input becomes a div with the same class and the field's padding, font, colour, width and min-height. It keeps its placeholder until the first character.
  - On any other element, its own text is the placeholder until the first character. `placeholder: false` hides it, for text typed on from nothing.
  - `text`, `t`: the first character's time. `cps`: about 22. `jitter`: 0.4 (±40% per character). `seed`. `space_pause`: 0.05.
  - `caret_from`: when the caret shows. `blink`: 0.5 s.
- **`press`:** a button press. `target`, `t`, `depth` (0.035 dips to 96.5% for 80 ms, then recovers over 200 ms).
- **`fade`:** opacity, scale, slide and blur between two states.
  - `sel` (every match, `step` s apart) or `target` (one element); `t`, `d` (0.5); `ease`: `out` (default), `in`, `inout` or `linear`.
  - `from` and `to` take any of `{opacity, scale, x, y, blur}`. Fields you leave out stay at the plain state (1, 1, 0, 0, 0).
  - **Before its first fade, an element shows that fade's `from` state.** If it must show earlier, add an identity fade at `t: 0` (`{"type": "fade", "sel": "...", "t": 0, "d": 0.001}`). Watch for parents: a form held at opacity 0 hides the tab row inside it.
  - For several fades on one element, the latest one that has started wins. An instant cut-away is `{"t": "cut1", "d": 0.001, "to": {"opacity": 0}}`.
  - A fade adds its slide and scale on top of the element's captured transform.
  - Do not fade an element that `dust` or `press` also moves.
- **`scroll`:** scrolls the page inside the `device` screen.
  - `keys`: a list of `{t, y, ease?}`. `y` is a scroll in px, or an element `{sel, text?, at}` to scroll so its top sits `at` px under the status bar. Each key's `ease` (or the event's, default `inout`) shapes the move into it. `expo` gives a fast scroll that brakes hard.
  - `blur`: 0.35, the vertical motion blur per px of movement per frame. `blur_max`: 40 px.
- **`prop`:** runs a CSS custom property from `from` (0) to `to` (1) over `t`, `d` on `ease` (`linear` by default), for every match of `sel` (or one `target`). `name`: `--p`. Several `prop` events on one element and name hand over by start time: each holds its `to` until the next starts.
  - Write the look in `page.css` or an overlay's `css` with `var(--p)`. Examples: a sheen across a row (`background-position`), a strike line (`width: calc(var(--p) * 100%)`), a gradient that shifts inside text.
- **Eases:** every `ease` field takes `linear`, `in`, `out`, `inout`, `expo` (fast start, hard brake), `expo_in` (slow start that speeds up exponentially), `whip` (fast start that settles into a steady drift, not a stop: 60% of the move as `expo`, 40% linear) and `back` (overshoots, then settles: a pop-in).
- **`set`:** switches attributes at `t`, such as the pressed tab: `{"target": ..., "t": 3.53, "before": {"aria-pressed": "true"}, "after": {"aria-pressed": "false"}}`. Several `set` events on one element hand over by start time: each attribute takes the `after` of the last started event, else the `before` of the first.
- **`cursor`:** a pointer in screen space.
  - `path` is a list of `{t, to, arc?}`, where `to` is screen px or an element (the point inside it set by `ax`, `ay`, `dx`, `dy`). It glides between points on an arc (`arc`, 0.12 of the distance by default; a negative value bends the other way) with an in-out ease.
  - `clicks`: times when it dips to 82% and recovers. Pair each with a `set` or a `press`.
  - `hide`: when it fades out. `size`: 64 px. `fill`, `stroke`.
  - Elements are measured after the camera moves, so the cursor stays on its target through zooms and drifts.
- **`end_line`:** the end card cuts in at `t` on `bg` (`#000`).
  - **Words:** `word` blurs in with a `sheen` colour sweep. Then the line slides it left and wipes in `rest` and then `accent` (in `accent_color`, default `sheen`).
  - **Type:** `font` (a CSS font stack whose family the captured page declares), `size` (64), `weight` (500), `rest_weight` (400), `color`, `tracking` (`-.02em`).

## Finding the numbers

1. Plan from `windows`, not `shots`. Map each film shot to one window, or to windows next to each other in the same shot, and put their `[t0, t1]` in `ref_window`. `compare.py` then reads the same frames, so the window's `speed_pct_w_s.median`, `still_pct` and `fill_pct` are the targets.
   - Choose the ease from `ease.shape`: `settle` is `out`, `expo` or `drift0`. `ramp` is `in` or `expo_in`. `bell` is `inout`. `flat` is `linear` or a steady `drift`.
   - A window is one camera move. One push that the eye reads as two beats stays one `bell` window (one reference at 10.3-11.7 s). Split it at its peak by hand if the film needs two shots there.
2. Read `ref.json` for the reference window or shot: `vel_pct_w_s` gives `drift`. `speed_pct_w_s.start` against `.end` tells you whether to use `drift0`. `zoom_pct_s` gives the zoom change (end = start × (1 + zoom_pct_s/100 × shot length)). `focus` gives `dof`.
3. Pick `focus` from `boxes.json` (page px) and `at` from where the reference frames its subject (`shots/sNN.jpg`).
4. Build, snapshot the middle of the shot, and set the shot image beside it. Change `rot`, `zoom` and `at` until the framing and the angle match. Change nothing that was measured.
5. How the numbers are measured. Speed is the median move of the frame centre, in % of frame width per second; a window's camera speed also counts zoom, as the move of a pixel 0.31 W from the centre. Still % is the share of frames where under 1.5% of the frame changes. Fill % is the median share of a 16 by 9 grid whose cells hold sharp detail (at least a quarter of the busiest cell's edges), so it grows with the amount of text and UI on screen, clutter included, and ignores faint background lines; the hint `less fill` means under 60% of the reference. Text % is the height of the biggest edge blob that is wider than high, in % of frame height, so a row of dots can count as text; the hint `smaller text` means under 70% of the reference. Hints are not failures. `STILL` means a shot's still % is over 25 points above its reference window's. `EMPTY` means a shot's longest blank span (fill under 1%) is more than 0.2 s longer than its reference window's. The whole-film line weights each shot's still % and its window's still % by the shot's length.
   - The `measure_ref.py` thresholds come from six measured launch films, Linear, Perplexity, Tuyo and Grok among them. A hold is under 2.5 %W/s (hand-marked holds stay under it; Linear's slow drifts run 3-5), a move ends under 12 %W/s and under 25% of its peak (hand-marked ends: 7-16), and two moves split below 0.2 of the slower peak (one reference at 6.54 s: 0.8 against 33).
   - A cut out of a fast move needs a colour jump of 0.23 or more (one reference at 0.917 s: 0.28; non-cuts stay under 0.19). A picture swap under a fixed overlay has a likeness under 0.65 (one reference at 3.33 s: 0.60; non-swaps 0.70 and 0.90).
