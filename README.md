# Variance Studio

Offline financial variance analysis for revenue and cost. Attach an Excel dataset, confirm anything the app is unsure about, and explore Month-on-Month, Quarter-on-Quarter and Year-on-Year variances by project or by region. The analysis sentence, a variance bridge, a monthly trend and a project breakdown are one click away from the filters.

Everything runs on your own computer. No internet connection is used, and analysed datasets are saved locally as workspaces so they can be reopened without uploading the file again.

## Run it (single process, fully offline)

```bash
# one-time setup
cd backend
python -m venv venv
venv\Scripts\activate         # Windows (macOS/Linux: source venv/bin/activate)
python -m pip install -r requirements.txt

cd ../frontend
npm install
npm run build

# every time
cd ../backend
python run.py
```

`run.py` starts the backend and the built interface together on `http://127.0.0.1:8000` and opens your browser.

## Develop

```bash
# terminal 1
cd backend && uvicorn api.app:app --reload

# terminal 2
cd frontend && npm run dev     # http://localhost:5173, /api is proxied to the backend
```

## Where data is stored

Workspaces live in a local SQLite file in your user data folder:

| OS      | Location                                          |
| ------- | ------------------------------------------------- |
| Windows | `%APPDATA%\VarianceStudio\workspaces.sqlite3`     |
| macOS   | `~/Library/Application Support/VarianceStudio/`   |
| Linux   | `~/.local/share/VarianceStudio/`                  |

Set `VARIANCE_STUDIO_DATA_DIR` to use a different folder. Re-importing a file with the same name and sheet replaces its earlier workspace. Delete a workspace from the sidebar to remove its data.

## Currency

Amounts are read as actual currency values with no scaling. Only the month-year columns are inspected: if their headers or text cell values carry a currency symbol or code (for example `$`, `€`, `₹`, `USD`), that currency is used. If nothing is found, US dollars are assumed. If different currencies are found, amounts are shown without a symbol and are never converted. Text amounts such as `$1,200.50` or `(3,400)` are converted to numbers automatically.

## Tests

```bash
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest
```

## Settings

- `VARIANCE_STUDIO_PORT` changes the port used by `run.py` (default `8000`).