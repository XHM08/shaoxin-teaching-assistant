# Shaoxin (邵新) — a local teaching assistant for teachers

Shaoxin is a desktop application for teachers, built for classrooms where the
computer is old, the network is unreliable, and nobody has time to install a
development stack. It runs as a single window on Windows, starts a small HTTP
service on `127.0.0.1`, and keeps every file it produces on the teacher's own
machine.

## Who it is for

Teachers who prepare lessons alone. The first user is a maths teacher in a rural
primary school, so the app assumes: one screen, Windows 10, no admin rights, and
an AI account the teacher pays for personally.

## What it does

The app is a workbench of small abilities, about forty of them. The ones that
matter most:

- **Courseware**: generate a `.pptx` deck with speaker notes, following a
  "skill pack" distilled from the teacher's own lesson materials.
- **Revise courseware**: a teacher says what to change in plain words; the
  model only edits notes, bullet points, key sentences and page titles, and
  reports what it cannot do instead of pretending.
- **Lesson scripts and voice-over**: write the script per slide and read it in
  the teacher's own voice through a local text-to-speech service.
- **Student records**: number-keyed folders (S01, S02 ...), answers and error
  types, guarded by a signed-consent gate.
- **Error diagnosis and explanation review**: given a wrong answer, explain the
  mistake the way this teacher would, and rate an explanation against a rubric.
- **Web fact-checking**: search the web or fetch one page, with sources, dates
  and an authority hint; it is billed per request, so the UI says so.
- **Creative mode**: a tool-using agent. The teacher describes the job in one
  sentence and the agent calls the built-in tools to do it, asking for
  confirmation when a command is risky.

## How it runs

- Python 3.12, standard library only for the service. No web framework, no
  database. Data is plain files and JSON.
- The window is a WebView2 control; the UI is one HTML page talking to
  `/api/ability` and `/api/run`.
- One port, defined in exactly one place (`地基/配置.py`), default `18765`.
- Packaging is PyInstaller, producing a single folder with `邵新.exe`.

## Privacy

- Student data, materials, generated courseware and logs stay in the app folder
  on the teacher's computer.
- Only the text a teacher sends (plus the files attached to a request) leaves
  the machine, and it goes to the AI provider the teacher configured.
- Student names may appear in local records, but reports, slides and screenshots
  must not contain them.
- API keys are stored locally and never committed.

## Requirements

- Windows 10 or 11 with the WebView2 runtime (the installer is included).
- A DeepSeek API key for any AI feature. Nothing works without one; the app
  still opens and explains what is missing.

## Roadmap

**Next: v1.2.2 will add a virtual avatar.** An on-screen character that speaks the
per-slide lesson script in the teacher's own voice, so a lesson can run while the
teacher rests their voice or works the board. Work has started; nothing of it is
in this release. Design notes are internal at this stage and will be published
once the shape is settled.

## Status

Version 1.2.0, in testing with a small group of teachers. Features change
quickly and some text is still Chinese-only.

## About this repository

This is a public mirror of the source tree. Internal comments, design documents
and per-machine configuration are not published; `配置.示例.json` shows the
shape of the config file. The self-check scripts under `脚本/检查_*.py` are
included and can be run locally:

```
python 脚本/跑全部自检.py
```

There is no CI. A local pre-push hook can be installed with
`python 脚本/装钩子.py`.
