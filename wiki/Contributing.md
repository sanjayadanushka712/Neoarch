# Contributing to NeoArch

Thanks for taking the time to contribute! NeoArch is a community project and
every bug report, idea, and pull request helps.

## Ways to contribute

| Contribution | Where |
|---|---|
| 🐛 Bug report | [Open an issue](https://github.com/sanjayadanushka712/NeoArch/issues/new?template=bug_report.md) |
| 💡 Feature request | [Open an issue](https://github.com/sanjayadanushka712/NeoArch/issues/new?template=feature_request.md) |
| 🛠 Code | Fork `sanjayadanushka712/Neoarch`, branch off `dev`, open a pull request |
| 📖 Documentation | Edit the files under `docs/` or `wiki/` |
| 🌐 Translation | Add or correct a locale file under `neoarch/locale/` |

## Development workflow

1. Fork the repository and clone your fork.
2. Check out the `dev` branch — that is where changes land.
3. Create a topic branch: `git checkout -b feature/my-change`.
4. Make your change and verify it locally:
   ```bash
   QT_QPA_PLATFORM=offscreen python -m pytest tests -q
   ```
5. Push the branch and open a pull request against `dev`.
6. Keep pull requests focused — one logical change per PR.

## Code style

- Follow the surrounding style of the file you are editing; the project uses
  standard PEP 8 with a 127-character line limit.
- Keep the backend free of GUI imports so it stays usable from the `neo` CLI.
- Public UI strings must be routed through the translation system
  (`neoarch/locale/`) so all 10 shipped languages stay in sync.

## Reporting bugs

Please include:

- NeoArch version (**About → Version**) and your Python/PyQt6 versions
- Your distribution and desktop environment
- Exact steps to reproduce
- The relevant log output (**Settings → Logs**)

## See also

- [Development Setup](Development-Setup.md)
- [Architecture](Architecture.md)
- [Plugin Development](Plugin-Development.md)
- Full guide: [docs/CONTRIBUTING.md](https://github.com/sanjayadanushka712/NeoArch/blob/main/docs/CONTRIBUTING.md)
