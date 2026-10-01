**English** | [简体中文](README.zh-CN.md)

<p align="center">
  <img src="assets/cashing-icon.png" width="88" alt="Cashing icon">
</p>

# Cashing

**Log an expense. See your month.**

Cashing is a simple local expense tracker for Windows, built for lunches, printing, subscriptions, and everyday spending.
No account required. Your records stay on your computer, with no ads, telemetry, or cloud classification.

**[Download 1.2.0 for Windows](https://github.com/Lorentz-Caldfilis/Cashing/releases/tag/v1.2.0)** · [User guide (Chinese)](docs/USER_GUIDE.md) · [Report an issue](https://github.com/Lorentz-Caldfilis/Cashing/issues)

## Features

- **Quick entry**: enter an amount and a description, then press Enter to save. You can also paste an expense such as `18.5 午饭` (lunch).
- **Simple categories**: choose Daily living (生活), Tools (工具), or Entertainment (娱乐), or leave the choice to local rules. Correct categories and let the app learn from your choices.
- **Review spending**: monthly totals, category shares, daily records, and history search.
- **Easy corrections**: edit, delete, and undo records. Unfinished input is saved as a draft.
- **Local backups**: back up your ledger from the menu. Data is stored separately from the app.
- **System appearance**: light and dark colors follow your system settings.

| Log an expense | Review spending |
| --- | --- |
| ![Cashing expense entry](docs/images/capture.png) | ![Cashing monthly review](docs/images/review.png) |

Screenshots use demo data. Colors follow your system settings.
The current app interface and detailed guides are in Simplified Chinese.

## Get started

1. Open the [1.2.0 release page](https://github.com/Lorentz-Caldfilis/Cashing/releases/tag/v1.2.0) and download `Cashing-v1.2.0-windows.zip`.
2. Extract the entire ZIP and run `Cashing/Cashing.exe`. Keep the whole folder, including `_internal`. No Python installation is needed.
3. Enter an amount, press Enter, add a description, and press Enter again to save. Both the description and category are optional.

Click **看账单** (Review) at the bottom to see your spending, and click a record to edit it.
The top-right menu provides the data folder, backups, and app information.
Before updating, back up your ledger, close the app, and extract the new version into a new folder.

On Windows, data is stored in `%LOCALAPPDATA%\Cashing` by default. Replacing the app does not delete your records.
Ledgers and backups are not encrypted; make regular backups yourself.
See the [user guide (Chinese)](docs/USER_GUIDE.md) for shortcuts, backup recovery, and detailed instructions.

## Scope and limitations

The current download is **1.2.0, a pre-release for Windows x64**. The app is not digitally signed; the release page includes a SHA-256 checksum file.
It tracks expenses in Chinese yuan (CNY) only. Income, budgets, multiple accounts, cloud sync, and ledger import/export are not supported.
Automatic classification can leave a category undecided or get it wrong. You can correct it manually; expense totals are unaffected.
Classification accuracy and the interface are still being improved.

## Run from source

With Python 3.14 x64 installed, run these PowerShell commands from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Installing dependencies requires an internet connection; everyday use does not.
See the [developer guide (Chinese)](docs/development/DEVELOPER_GUIDE.md) for development, tests, and Windows packaging.

## Contributing and license

Issues, suggestions, and pull requests are welcome. Use fictional expenses when reporting problems to protect your ledger and logs.
Before contributing, read the [contributing guide](CONTRIBUTING.md) and [product design principles](docs/PRODUCT.md), both in Chinese.
Report security issues privately as described in the [security policy (Chinese)](SECURITY.md).

Cashing is licensed under the [MIT License](LICENSE), © 2026 Lorentz-Caldfilis.
You may use, modify, and redistribute it for free, provided you retain the copyright and license notice.
Third-party components retain their own licenses; see the [dependency notes (Chinese)](docs/THIRD_PARTY.md).
