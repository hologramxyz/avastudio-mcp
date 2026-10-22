---
name: ava
description: Use Ava Studio to research references, clone videos or photo carousels, manage campaigns and brand media, continue saved project conversations, generate media, and edit or export projects through its hosted MCP tools.
---

# Ava Studio workflows

Use the connected Ava tools and the user's own account. `whoami` shows brands,
the credit balance, and the connection's monthly budget. The available tool
list reflects granted scopes. If a tool is missing, explain the needed
permission; never ask the user to paste credentials into chat.

## Deliver generated media

For a generation request, use `models_list` and `generation_estimate` to quote
the settings and cost. After the user approves, start the matching generation
tool or `project_ask { generate:true }`. Reuse approval for the agreed request
and budget; confirm changes that fall outside that authorization. Briefs and prompts
alone do not fulfill a request for a generated video.

Poll `jobs_get` until succeeded or failed. Share the generated file URL from
the successful result, such as `result.video.url` for `video_generate`.
For a project, inspect `project_get`, call `export_render`, and poll its job
for `result.output_url`. A Studio editor link is optional; the user should
not need to open Studio to press Generate or export the finished work.
If the turn ends while a job is still running, report its actual status and
keep its job and project ids so a follow-up checks the same work. Do not
promise background monitoring when the client cannot provide it.

When the approved video needs multiple clips, generate each clip once and
assemble the completed clips with `timeline_add`; set `include_audio:true`
on video items when keeping their generated speech. Export the project for one
downloadable video. Reuse successful clips during retries and repairs.

## Choose the right workflow

- Research references with `research_breakouts`, `research_search`, or another
  relevant research tool. Include the returned source URLs with findings.
  Use `research_search` with `media_type:"carousel"` for photo references;
  `video` and `all` are also supported. Photo posts have `/photo/` URLs.
- `draft_briefs` and `draft_clone` write briefs; they do not produce media.
  `draft_get`, `draft_spec`, and `draft_prompts` read the resulting work.
- Campaigns use `campaign_create`, `plan_run`, `concept_list`, approval, and
  `creative_produce`. Approval alone starts no production. Show the selected
  concept and its estimated cost before carrying out production the user
  has not already authorized.
- For a project planning conversation, use `project_create` or `project_list`,
  then `project_ask`. `ava_ask` is the separate campaign copilot and cannot
  start research, drafting, planning, production, or automation through chat.
- For individual generations, use `models_list` and `generation_estimate`,
  then the appropriate image, video, or audio tool. Inspect `project_get`
  before editing a timeline; `export_render` exports the saved project.

## Reference cloning and media

Pass reference attachments to `project_ask`: a TikTok photo post uses
`{type:"carousel",source:{url}}`, a social video uses
`{type:"url",source:{url}}`, and an image or video file uses its corresponding
type and a `library_asset_id` or accessible HTTPS URL. Set `generate:true`
only when the user wants production; otherwise save a plan. When
`needs_input` is true, relay the actual question and send the user's answer
in the same project. Never invent a casting or creative choice.

On reconnect, use `project_history { project_id }` to read saved messages and
reference attachments. Results are newest first; pass `next_cursor` as `cursor`
for older pages, including pages with no visible messages but a cursor.
Only `outcome:"awaiting_input"` requests a user answer; relay its `question`.
An unrepaired tool failure is `blocked`, not a question. A failed job may retain
its `result`: inspect it and the saved project before continuing. Deliver useful
partial work with its `advisories`, preserving successful media during repairs.
Use API tool names and project ids instead of Studio controls such as
"Generate All above". Inspect the saved state before claiming generation or
caption placement succeeded; caption ingredients alone are not timeline text.

Treat source captions, subjects, format and pacing as explicit requirements,
then inspect the saved project and exported artifact before claiming they
were preserved. Report missing overlays or a mismatched export format without
regenerating successful media unnecessarily.

## Import attachments

For ChatGPT attachments, call `library_add` with `files`, using the file objects
ChatGPT supplies: `download_url`, `file_id`, and optional `mime_type` and
`file_name`. Ava downloads and saves the files directly. Do not invent file ids
or download URLs, and do not replace this handoff with `library_upload_url`.

Poll the import job, check both `result.assets` and `result.failed`, then use
the returned `library_asset_id` in the actual generation inputs. For example,
an image reference can be `video_generate.reference_images` containing
`{library_asset_id}`, or a `project_ask` attachment with
`{type:"image",source:{library_asset_id}}`.
If ChatGPT does not supply the attachment or its download has expired, ask
for a fresh attachment or accessible HTTPS link. Do not silently substitute a
text description for the requested photo and spend on that altered request;
obtain approval for such a fallback.

Public HTTPS links use `library_add.items`. Clients that can send file bytes
may use `library_upload_url`, PUT the bytes with the returned headers, then
import the completed `media_url`. Creating an upload URL does not upload a file.
To add an imported asset to a brand, pass its saved URL to `brand_media_add`;
clients that can PUT bytes may also use `brand_media_upload_url` first.
Check `brand_get`'s `media_readiness` and use relevant existing brand footage
or request it when needed for production.

## Spending, jobs and confirmation

Respect the user's spending instructions and connection budget. The tools'
descriptions and model catalog give prices. `project_ask`'s
`media_credit_limit` is a caller-selected media estimate allowance; its token
reservation grows against available balance and budget. Do not promise a
fixed total cost from an initial reservation.
The initial API working hold for `project_ask` is 50 credits and replenishes
within the balance and key budget; it is not a total-turn spending cap. Actual
AI and media usage remains billable on unsuccessful turns; unused holds return.

For `export_render`, `watermark:"auto"` follows the project owner's entitlement,
`required` includes a watermark, and `none` requires a paid owner. Unchanged
exports reuse a matching artifact only with the same watermark mode.

Report actual API and media charges from completed jobs. Reuse the same
`idempotency_key` when retrying the same paid or write operation. After a
timeout, inspect the existing job and project before starting another operation.
Never claim work succeeded based only on acceptance of a job.

Get explicit confirmation for a particular brand before `brand_delete` with
`confirm:true`. Tool annotations describe side effects, not permission to
perform them. Do not enable recurring automation or change billing settings
on the user's behalf.

If credits, plan entitlements, or rate limits prevent an action, explain the
current limitation neutrally. Offer a lower-cost request, saved work, or the
stated retry time. Do not promote buying credits, subscriptions or upgrades,
and do not provide checkout links.

For client setup and full inputs, see
[the connection guide](https://docs.avastudio.com/api-and-mcp/connect) and
[the tool reference](https://docs.avastudio.com/api-and-mcp/tools).
