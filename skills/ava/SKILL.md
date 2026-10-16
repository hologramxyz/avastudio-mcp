---
name: ava
description: Use Ava Studio to research short-form video, manage brand media and campaigns, draft concepts, generate media, and edit or export projects through its hosted MCP tools.
---

# Ava Studio workflows

Use the connected Ava tools and the user's own account. `whoami` shows brands,
the credit balance, and the connection's monthly budget. The available tool
list reflects granted scopes. If a tool is missing, explain the needed
permission; never ask the user to paste credentials into chat.

## Choose the right workflow

- Research references with `research_breakouts`, `research_search`, or another
  relevant research tool. Include the returned source URLs with findings.
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

Browser clients can use accessible links; they may not be able to upload local
bytes. Clients with file access can use `library_upload_url`, PUT the bytes
with the returned headers, then `library_add`. Brand media uses the matching
`brand_media_upload_url` and `brand_media_add` tools. Check `brand_get`'s
`media_readiness` before production and ask for relevant product footage when
needed. Treat source captions, subjects, format and pacing as explicit
requirements, then inspect the saved project and exported artifact before
claiming they were preserved. Report missing overlays or a mismatched export
format without regenerating successful media unnecessarily.

## Spending, jobs and confirmation

Respect the user's spending instructions and connection budget. The tools'
descriptions and model catalog give prices. `project_ask`'s
`media_credit_limit` is a caller-selected media estimate allowance; its token
reservation grows against available balance and budget. Do not promise a
fixed total cost from an initial reservation.

Long-running tools return a `job_id`: poll `jobs_get` until succeeded or failed
and report actual API and media charges. Reuse the same `idempotency_key` when
retrying the same paid or write operation. After a timeout, inspect the job
and project before starting another operation. Never claim work succeeded
based only on acceptance of a job.

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
