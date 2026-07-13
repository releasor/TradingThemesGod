---
name: agent-operational-rules
description: Framework-level operational rules for AI agents — handling Edit failures, Read offsets, test output hygiene, and escalation. These apply to all agents regardless of role.
tags: [general, agent, operational]
---

# Agent Operational Rules

These rules apply to ALL agents in the PrizmKit ecosystem. They cover common operational patterns that prevent wasted context and infinite loops.

## Edit Failure Recovery

When an Edit call fails with 'String to replace not found':
1. STOP editing immediately — do NOT retry the same Edit.
2. Run `grep -n` to locate the exact line of the target text.
3. Read with offset = max(grep_line - 20, 0), limit = 50.
4. Copy the exact text from the Read result into the Edit old_string.
5. Never guess or extrapolate an offset — grep first, then read, then edit.

## Read Offset Safety

Before any Read with offset + limit:
- Compute offset + limit. If the last tool_result for this file shows it has N lines, offset MUST be < N.
- Never request an offset >= known file length.

## Stale Line Counts (Large Files)

Before editing a large file (>1000 lines), verify you know its current line count from the most recent tool_result. Old line counts from earlier turns may be stale if you have since edited the file.


