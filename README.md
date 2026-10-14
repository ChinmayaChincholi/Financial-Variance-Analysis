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

## Web demo edition (hosted)

The same code can run as a website, so a client can try the application from a link without installing anything. This is an additional way to run Variance Studio; the offline desktop application above is unchanged and remains the core product.

Web mode is switched on with `VARIANCE_STUDIO_MODE=web` (the default is `desktop`). It adds:

- **Private workspaces per browser.** Each browser gets an anonymous random cookie and its own storage, so visitors never see each other's data. There are no accounts or sign-in.
- **Limits.** Upload size cap, a cap on simultaneous processing, a cap on saved workspaces per visitor, and automatic deletion of data after a period of inactivity.
- **Web hardening.** Security headers, cache headers, compression (never on the live progress stream), and the API docs switched off.
- **A clear notice.** A banner reminds visitors not to upload confidential data.

### Run the web edition locally

Build the interface in web mode, then start the backend in web mode.

Windows PowerShell:

```powershell
cd frontend
$env:VITE_APP_MODE = "web"
npm run build

cd ..\backend
$env:VARIANCE_STUDIO_MODE = "web"
python -m uvicorn api.app:app
```

macOS / Linux:

```bash
cd frontend
VITE_APP_MODE=web npm run build

cd ../backend
VARIANCE_STUDIO_MODE=web python -m uvicorn api.app:app
```

Then open `http://127.0.0.1:8000`. Rebuild without `VITE_APP_MODE` (and start without `VARIANCE_STUDIO_MODE`) to return to the desktop edition.

### Deploy

The `Dockerfile` builds the interface in web mode and runs the API with it in one container (`render.yaml` is a ready-made Render blueprint; any host that runs Docker works). Run a single instance: storage is SQLite and the processing limit is counted in-process.

```bash
docker build -t variance-studio-web .
docker run -p 8000:8000 -v variance-data:/data variance-studio-web
```

Mounting a volume at `/data` keeps demo workspaces across restarts; without one they are lost whenever the container is replaced.

**Memory.** Analysing a workbook loads all of it into memory. In testing, a 30 MB workbook (85,000 rows) took about 13 seconds and roughly 560 MB for a single upload. Size the server for the largest file you expect times `VARIANCE_STUDIO_MAX_CONCURRENT_JOBS` (default 2), with headroom: 2 GB of RAM is a comfortable starting point for files in the tens of megabytes. Lower the upload limit or the concurrency if the server has less.

### Web settings

| Variable                             | Default | Meaning                                            |
| ------------------------------------ | ------- | -------------------------------------------------- |
| `VARIANCE_STUDIO_MODE`               | desktop | `web` enables the web edition                      |
| `VARIANCE_STUDIO_MAX_UPLOAD_MB`      | 50      | Largest Excel file a visitor may upload            |
| `VARIANCE_STUDIO_RETENTION_HOURS`    | 24      | Visitor data is deleted after this much inactivity |
| `VARIANCE_STUDIO_MAX_WORKSPACES`     | 10      | Saved analyses kept per visitor                    |
| `VARIANCE_STUDIO_MAX_CONCURRENT_JOBS`| 2       | Uploads processed at the same time                 |
| `VARIANCE_STUDIO_DATA_DIR`           | (OS)    | Where visitor data is stored (`/data` in Docker)   |
| `PORT`                               | 8000    | Port used by the Docker image                      |