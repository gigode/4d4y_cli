# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a personal workspace containing `zaima`, a bash script that runs self-diagnostic checks against multiple AI CLI tools (codex, claude, and openclaw agents).

## Commands

```bash
./zaima "prompt here"          # Run AI CLI diagnostics with prompt
ZAIMA_TIMEOUT=60 ./zaima "hi"  # Run with custom timeout (default: 30s)
ZAIMA_HOME_ROOT=.zaima-home ./zaima "test"  # Store per-tool homes in a custom directory
ZAIMA_USE_TEMP_HOME=1 ./zaima "test"        # Keep OpenClaw home under /tmp
```

## Architecture

The `zaima` script sequentially runs three AI agents and aggregates their results:
1. **codex** - Codex CLI via `codex exec`
2. **claude** - Claude CLI via `claude -p`
3. **openclaw** - OpenClaw agents (auto-detected via `openclaw agents list`)

Results are collected with status (ok/timeout/error plus common diagnostic states such as not_logged_in/fs_error/blocked), exit codes, and truncated output previews, then printed as a summary table.
