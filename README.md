# Shaoxin — a local teaching assistant

A local Python application that turns one teacher's own way of explaining a subject into a
reusable "skill pack", and then answers questions, writes slide decks, and classifies
student mistakes according to that teacher's method.

**This is the comment-free distribution.** Comments and docstrings have been removed from
the source. The annotated working copy is kept separately and is not part of this
repository.

## Requirements

- Python 3
- Exactly one third-party package: `python-pptx`, used only to write `.pptx` files

```
pip install python-pptx
```

Everything else uses only the Python standard library.

## Running

Double-click `启动.bat` ("start"), or run:

```
python 本地服务.py
```

Then open <http://127.0.0.1:8765>.

The server binds to the loopback interface by default. A LAN mode also exists; requests
from another device need the access token that the server prints at startup. There is no
mobile build.

## Layout

| Path | Contents |
|---|---|
| `地基/` | Core: registry, prompt loading, model client, file writing, configuration, audit log, skill packs, MCP client |
| `能力/` | One file per ability. Each ability registers itself through `注册表.登记`, so adding one needs no change elsewhere |
| `网页/` | Single-file HTML with inline JavaScript. No build step |
| `提示词/` | Prompt templates containing `{placeholders}`; read at runtime |
| `脚本/` | Self-check scripts, named `检查_*.py` |
| `技能包/` | Three synthetic skill packs, used for demonstration and by the self-checks |

## Self-checks

```
python 脚本/检查_参数契约.py     # declared parameters vs function signatures
python 脚本/检查_页面资源.py     # page/route consistency (needs a running server)
python 脚本/检查_MCP.py          # offline; no network access, no API calls
python 脚本/检查_命令门禁.py     # offline; executes nothing
```

Scripts that write to disk require `--确认`: they back up first and restore afterwards.

## Contents of this repository

- 34 abilities, 14 tools, 15 pages
- No credentials are included
- The skill packs under `技能包/` are synthetic samples, not recordings of a real teacher

## Execution model

This is a single-user local application. It contains no sandbox: abilities that run
commands execute them with the privileges of the user running the server. Access to those
abilities is gated by four mechanisms:

1. The model can only *register* a command for approval; it cannot execute one.
2. Non-loopback clients must present an access token.
3. A deny-list of destructive command patterns.
4. A per-command confirmation ticket, valid once.

## License

No license file is included.
