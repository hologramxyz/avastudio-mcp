# Sound

The goal is a bed that sounds like the same world as the reference: the same sources, space and restraint. It is arranged so its moments land on our cuts. ElevenLabs makes the material; we arrange it to the cut, because the model ignores timing and arcs.

Two kinds of reference need two paths:

- **Beatless and atmospheric** (Linear Agent): follow the steps below. `arrange.py` builds the bed from offset pad layers, a drone and a hit shaped like the reference's.
- **A beat grid** (a drop, kicks, a clear BPM in `ref.json`, `beat_strength` over about 0.3): follow "Beat path" below.

## Beat path (worked on Perplexity Computer)

1. **Measure the reference's moments.** Run `audio_profile.py <ref> 0 <dur>` on the window the opening copies. Find its hit and drop as rises of over 9 dB in the low band (Perplexity: hit 3.6 s, drop 12.25 s).
2. **Put the picture's moments on them.** A click on the hit, a cut on the drop.
3. **Generate 1 job from the reference's first 30 s:** picture and audio, with no high-pass when the opening's sub share is under about 60%. Make a second only after the person approves the picture.
   - Name the sources and say what must not happen. "Crisp sparse percussion" gave a drum kit the reference does not have. "A pulsing synth bassline, no drum kit" matched.
   - Our own picture with the reference audio gave a sub drone (19.8 dB). Use the reference clip.
4. **With 2 or more tracks, rank by ear before by score.** Gemini picked the pulse bed even though it scored worse (9.4 against 5.3 dB). Its fault, muddy highs, was real, and the band steps below fixed it.
5. **Arrange on the bed's measured drop.** `scripts/music/arrange_beats.py` with segments `[picture start, picture end, bed start]`; one segment that puts the bed's drop on the cut is often enough.
6. **Shape the opening by hand when the reference opens near silent.** High-pass the bed before the hit and swell it in. Bring the full range in on the hit, and layer a real generated low hit there.
7. **Match the arc, then the tone.**
   - `band_match.py` rides sub, low, mid and high over time toward the reference.
   - `tone_match.py` matches third octaves and sets loudness.
   - Perplexity, in steps: 9.4 → 6.7 → 5.5 dB tone distance, and loudness shape r 0.72 → 0.97.
8. **Name the instruments, not only the mood** (Tuyo). "High-energy, glossy, confident" gave a clean pop-house bed that Gemini heard as pop (A/B 1 of 10). "Aggressive electro-house: distorted saw stabs, sidechained bass, crunchy claps; only synthesizers and drum machines: no guitar, no piano, no acoustic instruments" gave the same tempo and form with the right sources (A/B 9 of 10).
   - ElevenLabs kept the reference's tempo and grid in both beds (126 BPM, the same phase), so one arrange plan fit both.
   - A bed with one breakdown and one drop can often be placed with a single segment whose drop lands on the cut.
9. **Keep SFX abstract.** Gemini called the literal library click on the first hit "too literal"; the reference's hit is a muffled thump. Keep a click only on a button press that the picture shows.

## Through Ava (no ElevenLabs key)

Ava's `audio_generate` runs the same model (`music_v2_5`) in two modes. Both spend the user's Studio credits and save the track to their Studio library.

- **Video-to-music (use this):** make the input clip with `v2m_clip.sh` (step 3 below; up to 30 s, and under the 50 MB that Ava's upload takes). Upload it: `library_upload_url { filename, content_type: "video/mp4", size_bytes }`, then PUT the bytes to `upload_url` with the returned headers. Then `audio_generate { kind: "music", model: "eleven_labs_music", text, video: { url: media_url } }` and poll `jobs_get`. The music follows the clip's length and its sound steers the style. It is held at the 30 s price (quote `generation_estimate { items: [{ model: "eleven_labs_music", duration: 30 }] }`, 18 credits) and charged per second of music, about 0.6 credits per second. Leave `duration_sec` out. A server older than Ava 0.9.2 answers "takes no video": use prompt mode there.
- **Prompt mode:** `{ kind: "music", model: "eleven_labs_music", text, duration_sec }`, 10-30 s in steps of 5, 0.6 credits per second. Quote with `duration` (or `duration_sec`) set to the same length; without it the quote is for 10 s.

- Write the words from the measurement and the hearing: genre, BPM from `ref.json`, the sources by name, and what must not happen (point 8 above).
- In prompt mode, ask for the full 30 s. Then arrange, band-match and tone-match as below. The arrange, match and score steps are free and local.
- Start with 1 job for the opening, as with video-to-music.
- Score against the reference cut like the film (its pieces joined on the film's clock with ffmpeg concat), not its first seconds.
- With no Gemini ear, take the words from the numbers: BPM, the key from the bass peaks in the spectrum, and the band balance. When the BPM is unclear, read it from the low-band onsets: on one reference `audio_profile.py` said 92.3, and the low hits fit 139.6 in half time (a bar of 1.72 s); a bed asked at 69.8 came back on that grid.
- A prompt-mode bed can come back far darker than the reference (tone distance 26-28 dB, top octaves 35-47 dB down). `tone_match.py` reached 15 dB at cap 10 and 4.6 dB at cap 25. That lifts 1-6 kHz of an mp3 bed by up to 16 dB, so listen for harsh highs before you deliver.

## Steps

1. **Measure the reference.**
   - Run `python $X/music/audio_profile.py refs/<ref>/source.mp4 [start] [dur]` for the whole film and for the window that matches the opening.
   - It reports loudness, loudness range, peak, the share of energy per band, the brightness centre, BPM and beat strength, onsets, and a band table per 0.5 s.
   - Read the band table: it shows the bed level, each hit (its start, peak and end), and the fade.
2. **Hear it.** Make a black-picture reel of the reference parts with the sub removed (`sound_reel.sh`), then run 1 Gemini call with a filled copy of `$X/../prompts/sound-hear.md`.
   - Use its words for the sources (pad, choir, strings, glass, grain).
   - Use the measurement for every time and level.
3. **Make the input clip:** `bash $X/music/v2m_clip.sh <picture> <ss> refs/<ref>/source.mp4 <ss> <dur> 130 26 clips/<name>.mp4`.
   - The audio is the reference's own sound, high-passed twice at 130 Hz and lifted 26 dB.
   - Keep the high-pass on a reference with more than about 60% of its energy under 70 Hz. With the sub left in, round 1 came back as one flat sub drone with no texture (20–23 dB from the reference).
   - Take the film's length plus at least 5 s of the reference bed, up to 30 s. `arrange.py` uses two pieces of the bed 4 s apart, each 0.5 s longer than the film. From a shorter track it loops the bed with a crossfade. Our own picture with the reference audio also works.
   - The picture fits in 960 px at 30 fps with a capped bitrate, so a 30 s clip stays near 12 MB.
4. **Generate:** `ELEVEN_LABS_API_KEY=... python $X/music/gen_music.py jobs.json music/out` (video-to-music, `music_v2_5`, `use_audio_as_reference`, no SFX).
   - **One job for the opening:** the filtered reference clip with the description from step 2. Add a variant only after the person approves the picture.
   - **Words:** keep "sub", "bass" and "drone" out of the description; they pull everything into the low end. Say what must not happen: no drums, no pulse, no melody, no words.
   - **Receipts:** `receipts.jsonl` keeps the song id and cost of each job.
5. **Score and rank.**
   - Score: `python $X/music/music_score.py <ref> <start> <dur> music/out/*.mp3`. A lower `spec_db` means a closer tone, and `chroma_any_key` means the same pitch set.
   - With 2 or more tracks, rank by ear: put the reference first in a `sound_reel.sh` reel, then run 1 Gemini call with a filled copy of `$X/../prompts/sound-rank.md`.
   - Pick where both agree. On one film, bed b2 (16.0 dB, the same top notes A#, C, G) was first on both. The prompt-only control was 23.4 dB, so the reference step earns its cost.
6. **Arrange:** write `sound.json` (its keys are under "Script reference" below; set every value from your own measurement), then run `python $X/music/arrange.py sound.json`.
   - **Pad:**
     - two pieces of the best bed, offset so one's swells fill the other's dips
     - a third-octave match to the reference bed (capped at ±10 dB)
     - a high shelf if the top is brighter than the reference
     - a slow rider, then the level of the reference bed
   - **Drone:** the low end of a generated bed, at the reference's sub level.
   - **Hit:** the reference's own low envelope, measured from its window, with the floor removed.
     - It is carried by a generated low tone moved to the reference's partials. Use `"auto"` or measured values; Linear's are 32.2, 33.3, 28.9 and 41.1 Hz.
     - Then add harmonics at the reference's 70–200 Hz level, so small speakers hear a trace of it.
   - **Placement:**
     - `at: [{t}]` puts the window at a film time.
     - `{onset_at, db, tail}` puts the hit's onset on a cut, quieter and under the tail fade.
   - **SFX:** library files only, on real actions, such as a soft click on the button press at -20 dB.
   - **Level:** a peak of -2 dBFS. The reference's loudness is the target, not -14 LUFS.
7. **Put it on the film and score again.**
   - Mux: `ffmpeg -i raw.mp4 -i mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest film.mp4`.
   - Run `music_score.py` against the same reference window, and `audio_profile.py` on both.
8. **Say nobody has heard it.** Gemini's sound scores swing on near-identical mixes, so do not chase them. Make the side by side play both sounds (`sbs.py ... --passes 0,1 --gain 0:<dB>`, lifting the reference to the same peak) so the person can listen.

## Lessons

- **The model ignores timing.** Structure asked for in words came back as one long arc. Arrange it yourself.
- **A full-range sub-heavy reference gives a drone.** High-pass the reference before you send it.
- **One hit pitch sounds like a note.** Several close partials beat like the reference. Too much beating pulses (beat strength 0.29); trim the outer partials (0.23, Linear 0.13).
- **Gemini's ear finds real faults:** the high band 5–8 dB too bright, a library impact that sounded generic, a sparkle that read as a ding. It also hears things that are not there: typing in a mix with one click. List the SFX in the mix before you act on a claim.
- **Phone speakers do not play under 70 Hz.** A sub-heavy reference is nearly silent on a phone. Say so when you deliver.
- **ElevenLabs credits lag** for a few minutes. Count jobs from the receipts, not from the balance.
- **The reference's audio shapes our bed.** The person who posts must clear that style match.

## Script reference

- `arrange.py <sound.json>`: paths in sound.json are relative to the current folder. Keys: `dur`, `ref`, `ref_bed [start, len]`, `pad {file, hp, piece_s, min_gap_s, shelf, fade_in, rider}`, `drone {file, ss, lp, fade_in}`, `hit {ref_window [start, len], carrier | carriers, partials [[hz, amp], ...] | "auto", at [{t} | {onset_at, db, tail}], body_window [start, len], body_mix}`, `tail [[t, ...], [dB, ...]]`, `sfx [{file, t, db}]`, `peak_db`, `out {mix, bed, json}`.
- `arrange_beats.py <plan.json> <out.mp3>`: plan keys `bed`, `duration`, `bar`, `segments [[picture start, picture end, bed start], ...]`, and optional `silences` (one beat, bar/4, of silence ends at each time), `open_filter` (`[[t, Hz], ...]`, a low-pass sweep under the opening), `fade_in`, `fade_out`. Paths are relative to the plan file. Splices get a 6 ms crossfade. Cut on the bed's bar lines: the intro's build under the opening (its drop on the title hit), the body under the run, the intro's last bars as the breakdown, the drop again on the payoff, the bed's own ending under the end card. Check the result with `bands.py`: the curve should step at each section.
- `bands.py <track>`: loudness per 0.5 s in three bands (low under 150 Hz, mid 150 Hz-2 kHz, hi over 5 kHz). A kickless intro has low near -30 dB; the drop jumps to about -10.
- `band_match.py <ref> <ref start> <in> <out.wav> [cap dB=15] [smooth s=0.75]`: Linkwitz-Riley bands at 70, 200 and 2000 Hz that sum back flat. Run `tone_match.py` after it.
- `tone_match.py <ref> <ref start> <ref dur> <in> <out.wav> [cap dB=10] [lufs=-16]`: use it after arranging, when `spec_db` is over about 6 dB.
- `sound_reel.sh <out.mp4> <secs> <hp> <file@start> [file@start ...]`: track 1 is the reference. Each track is `secs` long with 1.5 s of silence after, all at one loudness. `hp` is a high-pass in Hz (0 for none) that removes the sub.
- `gen_music.py`: runs 4 jobs at a time (the limit is 5). Job: `{name, description, tags?, video?, secs?}` (`video` = video-to-music; `secs` = prompt mode).
- `music_score.py`: `env_r` near 1 means the same loudness shape over time.
- `audio_profile.py` prints one JSON line, then a band table.
