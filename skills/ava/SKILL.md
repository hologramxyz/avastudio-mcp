---
name: ava
description: Use Ava Studio to research references, clone videos or photo carousels, manage campaigns and brand media, continue saved project conversations, generate media, and edit or export projects through its hosted MCP tools.
---

# Ava Studio workflows

Use the connected Ava tools and the user's own account. `whoami` shows brands,
the credit balance, and the connection's monthly budget. The available tool
list reflects granted scopes. If a tool is missing, explain the needed
permission; never ask the user to paste credentials into chat.

## Choose the planning workflow first

Start with `whoami` and the brand context. Carry the app/product summary, audience,
goal, reference links and supplied assets into the selected workflow.

- **The user asks to use a campaign:** reuse the selected campaign with
  `campaign_list` / `campaign_get`, or create it with the actual `brief` and
  `objectives`. Check `plan_get`, then call `plan_run` after approval of its
  200-credit new-run cost. Review `concept_list`, approve the selected concepts,
  and use `creative_produce` after production approval. Keep the same
  `campaign_id` throughout. Creating a campaign or linking a project does not run
  the planner; verify the actual run before claiming campaign planning happened.
- **The user asks for one complete original video or clone:** use
  `project_create` / `project_list`, then `project_ask`, Studio's content-planning
  agent. Pass the full brief and assets. For planning only, use `generate:false`
  and `media_credit_limit:0`; AI usage is still charged. After approval continue
  on the **same project** with `generate:true` and the approved media estimate
  allowance, poll the job, inspect the project and export. If the user selected
  a campaign for organization, pass its `campaign_id` to `project_create`.
- **The user asks only for written briefs, scripts or prompts:** use
  `draft_briefs` / `draft_clone`. `draft_briefs` always saves in the separate
  “From your agent” draft container; it cannot target the user's selected
  campaign, run its planner or supply concepts to `creative_produce`.
- **The user asks for an individual asset or manual editing:** use the model
  catalog, quote and individual generation/timeline tools. Do not silently
  replace a requested planning workflow with manual scene-by-scene generation.

If the user changes direction while work is running, inspect the existing jobs
and saved work. Reuse the selected campaign/project and successful clips; do not
create a second campaign just because standalone briefs are running. Explain any
additional planning cost before starting it. If tools are deferred, discover/load
`plan_run` or `project_ask`; if permissions prevent their use, explain the missing
permission rather than substituting another workflow.

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

For each editable project, use its exact returned `studio_url` from
`project_get` when offering an Open or Edit link. Do not substitute the Studio
homepage or invent a project URL. Deliver the completed export's
`result.output_url` as the download link, distinct from the editing link.

A standalone `video_generate` result is a clip in Library → Media, not an
editable timeline project. To edit or caption that clip, create a project and
use `timeline_add` to import the existing video with `include_audio:true`.
Do not regenerate it just to create a project. Campaign projects stay under
their campaign; standalone editable projects appear in Library → Projects.


## Reference cloning and media

When asked to clone a TikTok, Reel, or Short, let Ava fetch and analyze the
link. Your own browser does not need access to it. Try the Ava tool before
declaring a public reference inaccessible; report its actual error if it fails.
For an editable clone, use a project and `project_ask` with the reference URL
attachment below. `draft_clone` creates only a brief. After the user approves
production, use `generate:true` with the agreed media budget, then poll and
export. Do not silently change a request to generate into planning only.

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

For a clone with a reference MP4 and actor/product photos, import those files
first. Attach the MP4 as `type:"video"` and the photos as `type:"image"`, each
with its returned `source:{library_asset_id}`. Include the user's script and
instructions in the `project_ask` message; no manual rebuild in Studio is needed.

Poll the import job, check both `result.assets` and `result.failed`, then use
the returned `library_asset_id` in the actual generation inputs. For example,
an image reference can be `video_generate.reference_images` containing
`{library_asset_id}`, or a `project_ask` attachment with
`{type:"image",source:{library_asset_id}}`.
If ChatGPT does not supply the attachment or its download has expired, ask
for a fresh attachment or accessible HTTPS link. Do not silently substitute a
text description for the requested photo and spend on that altered request;
obtain approval for such a fallback.
When a required attachment cannot be transferred, explain the failed handoff
and ask for it here. Do not create an empty project or spend on a placeholder
production plan as a substitute for the requested video. Reuse an existing
project when the file is available; offer a planning-only fallback if the user
wants one.

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
