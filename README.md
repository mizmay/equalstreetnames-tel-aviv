# EqualStreetNames Tel Aviv

Gender-based street name map for Tel Aviv, Israel, forked from [EqualStreetNames](https://github.com/EqualStreetNames/equalstreetnames).

## Workflows

All `process.php` commands run from `~/Repos/equalstreetnames/process/`. Tel Aviv requires `-d memory_limit=512M` — the PHP default of 128MB is not sufficient.

### Data Update

Run periodically to keep GeoJSON current with OpenStreetMap and Wikidata.

```bash
# 1. Fetch current street data from OpenStreetMap
php -d memory_limit=512M process.php overpass --city=israel/tel-aviv

# 2. Fetch gender data for streets with a wikidata tag in OSM
php -d memory_limit=512M process.php wikidata --city=israel/tel-aviv

# 3. Build ways.geojson and relations.geojson
#    Applies manual overrides from data.csv if present
php -d memory_limit=512M process.php geojson --city=israel/tel-aviv

# 4. Regenerate gender.csv, other.csv, and metadata.json
php -d memory_limit=512M process.php statistics --city=israel/tel-aviv
```

`data/other.csv` is the list of streets still without a gender designation.

### Manual Import

Run when `other.csv` is manually updated.

```bash
# 1. Convert annotated CSV to data.csv and generate audit report
# From ~/Repos/equalstreetnames-tel-aviv
python3 scripts/import_other_csv.py <annotated-other.csv> data.csv data/other.csv
# Audit report written to data/import_audit.csv

# 2. Rebuild GeoJSON applying the new data.csv overrides
php -d memory_limit=512M process.php geojson --city=israel/tel-aviv

# 3. Update statistics
php -d memory_limit=512M process.php statistics --city=israel/tel-aviv
```

See [Gender Codes](#gender-codes) for the alternative manual coding scheme, since spreadsheets are finicky about '+' and '-'.

---

## Local Development

```bash
# Build and serve
cd ~/Repos/equalstreetnames/website
npm run build:israel:tel-aviv -- --serve
# Open http://localhost:1234
```

After updating GeoJSON, kill and restart the server to rebuild:

```bash
lsof -ti:1234 | xargs kill -9
npm run build:israel:tel-aviv -- --serve
```

---

## CI / GitHub Actions

### Deploy (automatic)

`.github/workflows/deploy-standalone.yml` — builds the website and deploys to GitHub Pages.

**Triggers:** push to `main` when `data/`, `html/`, `assets/`, or the workflow file changes; or `workflow_dispatch`.

**Required repo variables** (already set):
- `CITY_PATH` = `israel/tel-aviv`
- `CITY_KEY` = `israel:tel-aviv`

After committing updated GeoJSON, this runs automatically — no manual deploy step needed.

### Data Update (not active)

`.github/workflows/update-data.yml` — upstream workflow for automated monthly data refresh.

This workflow is **not active** for this repo. It requires GitHub App credentials (`BOT_APP_ID` variable, `BOT_PRIVATE_KEY` secret) and expects the city repo to be a submodule of a forked `equalstreetnames` parent. It also runs without `-d memory_limit=512M`, which would cause Tel Aviv's wikidata and geojson steps to run out of memory.

Data updates are run locally instead — see [Data Update](#data-update) above.

---

## Gender Codes

`data/gender.csv`, `data/other.csv`, and `data.csv` use the following codes:

| Code | Meaning |
| ---- | ------- |
| `F` | Female (cisgender) |
| `M` | Male (cisgender) |
| `+` | Multiple people (mixed gender) |
| `-` | Not related to a person |
| `X` | Intersex |
| `?` | Unknown gender |

The import script also accepts these alternative codes: `FF`→`F`, `MM`/`m`→`M`, `N`/`NN`→`-`, `MU`→`+`.

`data.csv` (at repo root) is the manual override input for the process. Format:

| Column | Description |
| ------ | ----------- |
| `type` | OSM object type (`way` or `relation`) |
| `id` | OSM object ID |
| `name` | Street name |
| `gender` | Gender code |
| `person` | Person's name (optional) |
| `description` | Description (optional) |
