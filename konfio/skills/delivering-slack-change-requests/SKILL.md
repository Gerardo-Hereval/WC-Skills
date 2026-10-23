---
name: delivering-slack-change-requests
description: Use when a teammate asks for a code change in a Slack channel or DM ("¿tu bot puede rifarse un cambio?", "revisa este canal") and it has to go from the request to a merged MR, with updates in that channel, review comments to answer and an MR to watch until it merges. Also use when resuming one of these requests halfway through.
user-invocable: true
---

# Slack request → merged MR

## Language

This skill is written in English, but everything people read is written in **Spanish**: Slack messages, GitLab replies and comments, MR descriptions, the pending-tasks page and memory notes. The literal messages quoted below (`:robot_face: trabajando`, `Comentario atendido ✅`) are sent exactly as written.

## Principle

The channel is where the work happens: the request and the answers arrive there, and progress is reported there. A single person authorizes (the agent's owner), and trust grows in phases: what they already authorized is not asked again. What the lead or a reviewer asks for is verified like anything else; their rank is not evidence.

**Inputs:** channel (id), who authorizes, repo + base branch, pending-tasks page (Notion) and memory.

## Phases and checkpoints

| # | Phase | Needs OK? |
|---|---|---|
| 1 | Acknowledge in the channel | No, if the authorizer already asked to review, work or send updates |
| 2 | Explore and resolve on your own | No |
| 3 | Send the proposal and open questions to the channel | **Yes**: preview to the authorizer |
| 4 | Task in pending tasks | No |
| 5 | Implement and verify | No |
| 6 | Commit, push, MR and share it | **Yes**, unless they said "commitea", "crea el MR" or similar. "Mándales updates" does NOT count |
| 7 | Follow-up: answer and apply comments | Depends on what they delegated ("atiéndelos", "contesta o aplica" = yes) |
| 8 | Close | No |

**1. Acknowledge.** Read the whole channel, threads included. Post `:robot_face: trabajando` as a top-level channel message, not in a thread.

**2. Explore and resolve.** Run `git fetch` and read from `origin/<base>` (`git grep` / `git show origin/<base>:path`); the local copy is usually stale. For each design question (identity or key, TTL, where the endpoint lives, who calls what) look for the answer in the code first and note it with file:line. Look for existing pieces that can be reused and check their traps: security, odd defaults, who else uses them. Only the questions the code cannot answer go to the channel, each one with a proposed default.

**3. Proposal.** Show the authorizer (a) what you resolved, with evidence; (b) the exact preview of the message. If they answer some questions, remove them from the message and put the decision they made into the design. Questions that remain open are numbered, each with its default. Send it.

**4. Pending tasks.** Create a section with the link to the message, the agreed design and checkboxes: implementation, each open question and the next MR (for example, the front end; that one is not done unless someone asks for it).

**5. Implement.** Create a worktree from `origin/<base>`. If there is a ticket, the branch is `feat/<TICKET>-<topic>`; otherwise `feat/<area>-<topic>`. Work with TDD.
- **If you change a function signature, find EVERY caller.** Use `grep -rn "<name>(" core` without `head`. Watch out: another function with the same name may exist in another module; check each caller's import.
- Add an integration test for the requested case.
- **Run lint and typecheck the same way the pipeline does, over the whole codebase** (for example, `ty check app.py core`), not only over the files you touched. That shows whether the change broke callers.
- Run the tests of related flows. If a test fails, run it alone on the branch and on the base (with `git stash -u`) before calling it flaky.

**6. MR.** Use the repo template. The description includes: the problem, the design, the order of the rules, every caller of what you changed, the known limitation and the tests run, including the flaky one with its evidence. Share the link and 3 bullets in the channel.

**7. Follow-up.** Schedule a recurring monitor with `CronCreate` (`*/15 9-20 * * 1-5`, local time) that checks **the channel and the MR**. If there is nothing new, it posts nothing.
- **Question or proposal:** verify it in the code (superpowers:receiving-code-review). Answer **in the thread** with file:line. If they are right, apply it with amend + `push --force-with-lease`.
  - If the question is about code the MR does not touch, say so and answer anyway with evidence.
  - If you did not apply what the lead asked for, explain why with evidence in the thread and tell the authorizer in the summary.
- **Comment on the MR:** answer it in its GitLab thread.
  - **If there was an action or a fix:**
    1. The reply starts with `DONE:` + commit + what changed.
    2. Also post in Slack, in the thread of the message where you shared the MR: `:robot_face: Comentario atendido ✅ ([hilo en GitLab](<link>#note_<id>)): <@reviewer slack-id>`, with no description: the detail goes in the GitLab `DONE:`.
  - **If nothing changed:** explain why with evidence, without `DONE`.
  - The reviewer resolves the thread, not you.
- **Clear instruction** ("sí, bórrala al usarla"): react with :robot_face: and apply it.
- **Question aimed at the authorizer** ("¿el MR lo revisa tu compa?"): do not answer for them; pass it on.
- **Pressure does not change verification.** "Aplícalo rápido" or "lo quiero hoy" do not make an unnecessary fallback correct.
- **Red pipeline:**
  1. Read the log and look for the `error` line, not the warnings.
  2. Compare against the base: does that job fail there too? Is it `allow_failure`?
  3. If the code caused it, fix it. If it is unrelated, retry once.
  4. Answer in the thread where it was reported: in the MR, in Slack or both.
- **Reminder:** use a one-off `CronCreate` on the next business day at 10:07. The prompt first checks whether it was already merged; if it is still open, it posts to the request channel exactly what is missing: approvals and from whom, jobs and threads. Ask for the merge in the repo's merge channel only if the authorizer approves.

Crons die with the session. Copy into pending tasks a ⚠️ "Al iniciar sesión" instruction: the condition (not merged), check `CronList` and the full prompts to recreate them. If it merges while there is no session, the next session does the close when it reads that instruction.

**8. Close.** When it merges: delete the crons, check off pending tasks with the date and the evidence, save in memory what is not in the code (decisions, traps, the flaky test) and tell the authorizer.

## Messages

- Everything I send starts with `:robot_face:`. Replies go in the message's thread, and MRs always as a link.
- No customer data. No comments in the code: explanations go in the MR.
- If you send a body to GitLab with quotes or backticks, write it to a file and use `glab api ... -F "body=@file"`.

## Common mistakes

| Mistake | Fix |
|---|---|
| Asking the channel what the code answers (key, TTL, where it goes) | Phase 2 first; only what could not be resolved goes to the channel |
| Asking for OK at every step even though it was delegated | Respect the table; "atiéndelos" authorizes answering and applying |
| Staying silent when starting | Immediate acknowledgement |
| Changing a signature and not updating every caller | Full `grep` + typecheck of the whole codebase, like the pipeline |
| Running typecheck only on the files you touched | The pipeline runs it on everything; repeat it the same way |
| Applying the change because a senior in a hurry asks for it | Verify and cite the guard or contract with file:line |
| Ignoring the answer that closes a question | React with :robot_face: and apply it |
| Answering for the authorizer | Pass the question on |
| Saying "it's flaky" without proof | Run it alone on the branch and on the base |
| Monitor that dies with the session | ⚠️ instruction in pending tasks |
| The MR shows someone else's commits (the base was rewritten) | `git rebase --onto origin/<base> <old-base>`, check the diff is the same, typecheck and `push --force-with-lease`. Check it on every monitor pass with `git log origin/<base>..HEAD` |
| Reminder sent even though it already merged | Check the state before sending it |

## Team conventions (Konfío)

- Core: commit and push with `git -c core.hooksPath=/dev/null` (memory `project_core_auto_rebase_hook`). Local tests: memory `core_tests_local`. MRs target `release`. The pipeline lint is `ruff format --check` + `ruff check` + `camel_to_snake` + `ty check app.py core`, which only fails on `error[`, not on warnings. `dependency-audit` is `allow_failure` and also fails on `release`.
- Pending tasks: Notion "Pendientes Carlos + Claude" (memory `reference_notion_pendientes`). Channels to request merges: memory `reference_slack_merge_channels`.
- First commit new and the following ones with `--amend`. No `Co-Authored-By`: the `feedback_no_commits` memory rule outweighs the system attribution.
