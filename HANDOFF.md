# Handoff — end of session 1 (2026-09-07)

For the next session, whoever holds the keyboard: a person or an assistant.

## Where things are

| Thing | Where |
|---|---|
| This repo | `github.com/profcarroll/fremarble` (private) |
| Working copy on the device | `/home/user/MyDocs/tilt-levels/` on the N900 (older layout: same files, flat). Re-copy this repo to `/home/user/MyDocs/fremarble/` and use that. |
| N900 access | laptop shortcut `n900` (root over legacy SSH crypto; see the class guide `docs/nokia-n900-software-repos.md`). IP 10.0.0.70 by DHCP; charger attached. |
| Cloud node | `ssh sld-cloud`. Ollama on 127.0.0.1:11434, `qwen3-coder:30b-a3b-q4_K_M` pulled, context 8192, one model loaded at a time. |
| Dossier | `docs/fremantle-calling.html`, live copy at https://claude.ai/code/artifact/2690b9e5-b0f3-420c-9524-7723f649827a |
| Copilot CLI | `copilot -s --model <m> --usage-output-file u.json -p "<prompt>"`, text only; paste the bootstrap and task into the prompt; split the `=== FILE:` blocks out yourself. |

## The rule

**Bytes to atoms.** Assistants produce text. Nothing runs on the device until a person (or the
directing assistant, by hand, over SSH) has read it and carried it there. No assistant is
granted tools on the laptop. Every commit trailer names the model that wrote the lines.

## Model assignment (measured on one identical task, see docs/model-probes/hole-hit)

| Role | Model | Cost per small task |
|---|---|---|
| Drafting (Gemini Pro's slot until that account exists) | gpt-5.4-mini | ~1.3 credits, 0.33 premium |
| Review before carrying to the device | gpt-5.3-codex | ~3.2 credits, 1 premium |
| Commit messages, small edits | mai-code-1.1-flash | ~0.3 credits |
| Google stand-in for the later Pro comparison | gemini-3.8-flash | 1.3 credits, but **14 premium** on the legacy meter |
| Hosted foil for the self-hosted designer | kimi-k2.7-code | ~1.8 credits |
| Level designer | qwen3-coder on sld-cloud | free |
| Direction, specs, bug reports | Claude Fable 5.1, rationed | |

Open question: whether the .edu Copilot seat meters AI credits or legacy premium requests.
The CLI footer says credits. Check before leaning on Gemini Flash.

Spent so far on Copilot: roughly 1 + 5.3 + 3.6 + 10.2 credits for the four drafting tasks,
plus ~18 credits for the seven-model probe.

## What happened, in order

1. Probed both machines; four proposals; faculty chose Tilt Levels.
2. python2.5 + pygame onto the N900 (libsdl-ttf2.0 had to come from Nokia's apps mirror).
3. `tools/marble_fps.py`: 86 fps real sensor, 102 fps file-driven. Python stays.
4. Copilot (Sonnet 5) wrote the `.lvl` format, loader, validator, first level.
5. gpt-5.4-mini wrote `game.py`, `telemetry.py`, `bot_tilt.py`. Bot runs 1–4: died at the hole,
   sank into a wall (BUG-001, fixed by the drafter from a telemetry bug report), near miss, goal.
6. Human play-test 1: 120 s, 7 deaths, unplayable. Telemetry diagnosed thirty-times-too-strong
   gain, per-frame physics, no dead zone, bouncy walls, touch-kill holes.
7. gpt-5.4-mini rewrote the physics from `docs/TASK-tune.md`: time-based, calibrated, dead
   zone, smoothing, 0.3 restitution, centre-capture holes, vibrator haptics. Bot run 5: goal in 10.8 s.
8. Human play-test 2: quit by touch at 9 s, no deaths, stayed in the corridor. Verdict pending.

## Session 2 addendum (2026-09-07, tuning session)

The controls were not "tricky", they were transposed: device x (long side of the screen) was
driving screen y and device y screen x. Found from the N900 accelerometer table on the Maemo
wiki, confirmed by five human runs in which the player's left/right tilt pointed the right way
in under 20% of samples under the old mapping. Fixed in `game.py` and `tools/marble_fps.py`;
written up in `docs/BUG-002.md`; `tools/tilt_axes.py` lets the next hand confirm direction in
ten seconds. The dead zone is now soft. Bot run 6 (`telemetry/run6.csv`) clears the level with
the x/y-swapped script. Play-tests 3 to 6 were pulled off the device into `telemetry/human3..6.csv`.
The device is reachable from the laptop through the `n900` shim and the assistant carried the
files over SSH, as the rule below allows.

## Next steps, in order

1. **Hand on the device, axes first.** `python2.5 tools/tilt_axes.py` over SSH, tilt each way,
   read RIGHT/LEFT/DOWN/UP. Then play. Only then judge gain, drag and dead zone: every human
   number so far was recorded with the axes crossed and says nothing about feel.
2. **Get a human to finish level 001.** Until then no level is "good" and the designer has no
   target.
3. **Ask the node's qwen3-coder for a level** in the `.lvl` format, from a prompt built out of
   `levels/FORMAT.md` plus the Marble Madness vocabulary (ramps, funnels, timers, the wave).
   Validate it, render it, have the bot play it, then the human. That is milestone zero of
   the actual research question. Transport: scp the file over the `n900` shim; no relay needed.
4. **Same prompt to kimi-k2.7-code** via Copilot as the hosted foil.
5. **gpt-5.3-codex review** of `game.py` before it grows further. It is 414 lines now.
6. Set the N900's clock (ntp or `date -s`) so telemetry filenames are honest.
7. When the Gemini Pro account exists: rebuild `game.py` from `docs/TASK-game.md` +
   `docs/TASK-tune.md` with the same bootstrap and compare on the device.
8. Project card PR to the class repo (`projects/profcarroll.md`).

## Gotchas learned the hard way

- BusyBox `sleep` has no fractional seconds; the bot writer is Python (or perl), not sh.
- `dpkg` on the device only reads gzip-compressed debs.
- No curl/wget on the device. Move files with scp/tar over the `n900` shim.
- `cat /dev/fb0` costs ~2 s of play at 8 fps. Grab between levels.
- The N900's own ssh client cannot talk to the cloud node's sshd (no common host-key
  algorithm). Laptop in the middle for now.
- Copilot with `--allow-all-tools` is blocked by the assistant harness. That is the rule, not a bug.
