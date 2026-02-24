#!/usr/bin/env python3
"""
Convert a client-coded other.csv export to data.csv for the EqualStreetNames process.
Also generates an audit report of name corrections and unmatched streets.

Usage: python3 scripts/import_other_csv.py <input.csv> [output.csv] [other.csv]
  output defaults to data/data.csv
  other.csv defaults to data/other.csv
  audit report written to data/import_audit.csv
"""
import csv
import json
import subprocess
import sys
import urllib.request

CODE_MAP = {
    'F': 'F', 'FF': 'F',
    'M': 'M', 'MM': 'M', 'm': 'M',
    'N': '-', 'NN': '-',
    'MU': '+',
    '?': '?',
    'X': 'X',
    '': '',
}

input_path  = sys.argv[1] if len(sys.argv) > 1 else 'data/tel aviv street names comprehensive.xlsx - other.csv'
output_path = sys.argv[2] if len(sys.argv) > 2 else 'data.csv'
ref_path    = sys.argv[3] if len(sys.argv) > 3 else 'data/other.csv'
audit_path  = 'data/import_audit.csv'

# Load reference other.csv names by row index (skip header)
with open(ref_path, encoding='utf-8') as f:
    ref_names = [row[0] for row in csv.reader(f)][1:]

# Build name → [(osm_type, osm_id)] and (osm_type, osm_id) set from current GeoJSON files
name_index = {}
geojson_ids = set()
for geojson_path, osm_type in [('data/ways.geojson', 'way'), ('data/relations.geojson', 'relation')]:
    with open(geojson_path, encoding='utf-8') as f:
        for feature in json.load(f)['features']:
            name = feature['properties'].get('name')
            fid = feature['id']
            geojson_ids.add((osm_type, fid))
            if name:
                name_index.setdefault(name, []).append((osm_type, fid))

# Build name → [(osm_type, osm_id)] from committed GeoJSON (for audit lookup)
committed_index = {}
for git_path, osm_type in [('data/ways.geojson', 'way'), ('data/relations.geojson', 'relation')]:
    result = subprocess.run(['git', 'show', f'HEAD:{git_path}'], capture_output=True)
    if result.returncode == 0:
        for feature in json.loads(result.stdout.decode('utf-8'))['features']:
            name = feature['properties'].get('name')
            fid = feature['id']
            if name:
                committed_index.setdefault(name, []).append((osm_type, fid))

# Read input CSV (skip header row)
with open(input_path, encoding='utf-8') as f:
    rows = list(csv.reader(f))[1:]

written, skipped, corrected_count = 0, 0, 0
out = []
corrections = []  # (row, client_name, ref_name, gender, osm_type)
unmatched = []    # (row, client_name, ref_name, gender, osm_type)

for i, row in enumerate(rows):
    name, _, gender, wikidata, osm_type = row[0], row[1], row[2], row[3], row[4]
    mapped = CODE_MAP.get(gender, gender)
    if not mapped:
        continue

    client_name = name
    if i < len(ref_names) and name != ref_names[i]:
        corrections.append((i + 2, client_name, ref_names[i], mapped, osm_type))
        name = ref_names[i]
        corrected_count += 1

    matches = name_index.get(name, [])
    if not matches:
        unmatched.append((i + 2, client_name, name, mapped, osm_type))
        skipped += 1
        continue

    for (match_type, match_id) in matches:
        if osm_type != 'relation+way' and match_type != osm_type:
            continue
        out.append([match_type, match_id, name, mapped, '', ''])
        written += 1

# Write data.csv
with open(output_path, 'w', encoding='utf-8', newline='') as f:
    csv.writer(f).writerows(out)

# Validate data.csv entries against current GeoJSON
unresolvable = []
for entry in out:
    if (entry[0], entry[1]) not in geojson_ids:
        print(f'WARNING: not in current GeoJSON — {entry[0]} {entry[1]} "{entry[2]}" ({entry[3]})', file=sys.stderr)
        unresolvable.append(entry)
if unresolvable:
    print(f"{len(unresolvable)} data.csv entries will be ignored by the geojson step.", file=sys.stderr)

# OSM API lookup helper
def osm_api_status(osm_type, osm_id):
    try:
        url = f'https://api.openstreetmap.org/api/0.6/{osm_type}/{osm_id}.json'
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.load(r)
        tags = data['elements'][0].get('tags', {})
        name = tags.get('name', '(no name tag)')
        tag_summary = ', '.join(f'{k}={v}' for k, v in list(tags.items())[:5])
        return name, tag_summary
    except Exception as e:
        return '(error)', str(e)

# Write audit report
with open(audit_path, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['row', 'status', 'client_name', 'ref_name', 'gender', 'osm_type', 'committed_osm_id', 'current_osm_name', 'current_osm_tags'])

    for (row, client_name, ref_name, gender, osm_type) in corrections:
        writer.writerow([row, 'corrected', client_name, ref_name, gender, osm_type, '', '', ''])

    for (row, client_name, ref_name, gender, osm_type) in unmatched:
        committed_matches = committed_index.get(ref_name, [])
        if committed_matches:
            for (match_type, match_id) in committed_matches:
                osm_name, osm_tags = osm_api_status(match_type, match_id)
                writer.writerow([row, 'unmatched', client_name, ref_name, gender, osm_type, match_id, osm_name, osm_tags])
        else:
            writer.writerow([row, 'unmatched', client_name, ref_name, gender, osm_type, '', 'not in committed GeoJSON', ''])

    for entry in unresolvable:
        osm_name, osm_tags = osm_api_status(entry[0], entry[1])
        writer.writerow(['', 'unresolvable', entry[2], entry[2], entry[3], entry[0], entry[1], osm_name, osm_tags])

print(f"Wrote {written} rows to {output_path} ({corrected_count} names corrected, {skipped} skipped)")
print(f"Audit report: {audit_path}")
