# AOJ Command OS AI Assistant

## Purpose

The AI Assistant module provides local, advisory-only support for field operators. It is meant to help with planning, summaries, troubleshooting prompts, and communication drafts during an airsoft event.

It is not a control plane.

## Current Implementation

Backend route:
- `/api/ai/ask`

Backend service:
- `backend/app/services/ai_service.py`

Current model identity returned by the service:
- `mock-local-advisor-v1`

The service is currently a rules-based mock advisor, not a live model integration.

## Safety Model

The AI assistant is intentionally restricted.

Current safety rules:
- It does not execute hardware commands.
- It does not authorize operational actions.
- It flags prompts that appear to request command-like actions.
- It marks those responses as requiring admin confirmation.

Restricted terms currently include words such as:
- arm
- disarm
- start
- stop
- reset
- trigger
- activate
- deactivate

If one of those terms is detected in a prompt, the service returns a blocked advisory response instead of a command-like answer.

## Practical Use Cases

Good uses on game day:
- draft a marshal briefing
- summarize results for a round
- suggest the next game type
- draft a team announcement
- propose recovery steps for a schedule delay
- outline a prop troubleshooting checklist

Bad uses on game day:
- asking it to arm a prop
- asking it to start or stop a round directly
- treating it as a safety or rules authority without human confirmation

## Example Prompts

Useful prompt ideas:
- `Draft a marshal briefing for a 20-minute domination game.`
- `Summarize results for the red team winning by 15 points with 2 penalties.`
- `Suggest next game format for 40 players after a delayed lunch break.`
- `Give me a prop issue checklist for a low-signal domination point.`

Expected current behavior:
- The response is textual advice only.
- The response includes a safety notice.
- Command execution never occurs.

## API Contract

Request:

```json
{
  "prompt": "Draft a marshal briefing for a 20-minute domination game."
}
```

Response shape:
- `answer`
- `advisory_only`
- `requires_admin_confirmation`
- `blocked_action`
- `safety_notice`
- `model`

Interpretation guidance:
- `advisory_only=true` means the response is informational only
- `requires_admin_confirmation=true` means the prompt approached an operational action boundary
- `blocked_action=true` means the assistant intentionally refused to act like a control interface

## Logging Behavior

Each AI request is logged in `system_logs` with category `AI`.

Current logging behavior:
- informational log when a normal advisory response is returned
- warning log when the request crosses into blocked-action territory

This helps operators review whether staff are trying to use AI beyond its intended scope.

## Operational Guidelines

- Use AI for wording, planning, and summaries
- Do not use AI as a replacement for marshal judgment
- Require human confirmation for anything that affects player safety, score, or prop state
- If the AI produces a briefing or announcement, review it before reading it to players

## Current Built-In Response Areas

The mock advisor already contains canned guidance for:
- next game suggestions
- result summaries
- marshal briefings
- prop issue diagnostics
- schedule delay recovery
- team announcements

Everything else falls back to a general advisory response.

## Limitations

- No live LLM integration yet
- No memory of previous conversation state beyond a single request
- No direct access to live mission state or database data inside responses
- No operator identity or permission-based response shaping yet

## Suggested Future Enhancements

- Connect to a local or offline-capable LLM runtime
- Add context injection from mission, schedule, results, and prop status
- Add role-aware prompt templates for marshals versus technicians
- Add a visible approval flow for AI-suggested but sensitive actions
- Keep command execution separated from AI even after model integration