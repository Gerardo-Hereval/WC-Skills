---
name: escalating-support-cases
description: Use when a support case (for example from #wc-issues-support) is already diagnosed and has to be escalated to a lead with full context ("mándaselo a Guille", "escálalo", "avísale al lead con contexto"). Sends two Slack messages - a short "we have a problem" greeting with the support thread link, and a threaded reply with the evidence, how the data got there, the fix MR and the open question of how to correct the case.
user-invocable: true
---

# Escalate a diagnosed support case to a lead

## Language

This skill is written in English, but both Slack messages are written in **Spanish**, in a direct, teammate tone. Amounts use thousands separators and two decimals.

## Before sending

1. Only escalate a diagnosed case. Every claim must come from verified data: read-only queries, code you read, or filtered logs. Do not escalate hypotheses.
2. Never include customer emails, RFCs or names. Identify the case by loan, application or contract number.
3. Ask who the lead is if the requester did not say. Find their Slack user ID with slack_search_users and DM them unless the requester names a channel.
4. Do not reply to the reporter in the support channel until the requester says so. The lead usually decides the correction first.

## Message 1 - greeting (parent message)

One line: the bot prefix if your setup uses one, the lead's mention, a greeting with "we have a problem :sweat_smile:", what happened in one sentence, the link to the original support thread, and "te dejo el detalle en el hilo".

## Message 2 - details (reply in the thread of message 1)

Start with the lead's mention, then these sections as Slack bold headings, in this order:

1. **Qué reportó soporte** - the data exactly as support gave it (amounts, dates, what the customer sees).
2. **Qué hay en la base / en los logs** - a Slack code block with the key rows (trimmed, aligned columns) and a short note of what they mean, for example "-> 5.17% de 500,000 + IVA".
3. **Cómo llegamos ahí** - a numbered cause-to-effect list, citing the commit, MR or file behind each step, so it is clear why every amount or state is what it is.
4. **Diferencia / impacto** - the concrete number or effect in one line.
5. **Solución en código** - the link to the MR that fixes the root cause. If it is closed or in Draft, say so and offer to reopen it ("si te late, lo reabrimos"). Say whether the bug can repeat until it ships.
6. **Duda: ¿cómo corregimos este caso?** - two or three options as bullets, with your recommendation and why you discard the others (for example, a data fix that only makes the records match what happened versus one that corrects the record and makes the customer whole). Add side effects to check: invoices, contracts, reconciliation. End with a direct question: which option they prefer, or who should own it.

Reference example: the 480399 disbursement case (LOAN_FEE computed on the old notional, Kanto dispersing NOTIONAL − SUM(LOAN_FEE)), escalated on 2026-10-29.

## After sending

- Record in your task tracking: waiting on the lead in the thread, the requester's decision with its date, and the thread link.
- Reply to the requester with links to both messages and a 3-5 line summary.
- No reminders or re-pings to the lead. If it takes long, tell the requester and let them decide.
