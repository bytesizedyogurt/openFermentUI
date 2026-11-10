"""Row counts of every table in the openferment and sci_rag schemas of one bh_ database, as JSON.
Usage: python rowcounts.py bh_h10_a"""
import json
import subprocess
import sys

db = sys.argv[1]
assert db.startswith("bh_")
url = f"postgresql://openferment:openferment@127.0.0.1:5432/{db}"
tables = subprocess.run(["psql", url, "-XAtc", "select table_schema||'.'||table_name from information_schema.tables "
                         "where table_schema in ('openferment','sci_rag') and table_type='BASE TABLE' order by 1"],
                        capture_output=True, text=True, check=True).stdout.split()
sql = " union all ".join(f"select '{t}', count(*) from {t}" for t in tables)
out = subprocess.run(["psql", url, "-XAtF", "\t", "-c", sql], capture_output=True, text=True, check=True).stdout
print(json.dumps(dict((a, int(b)) for a, b in (l.split("\t") for l in out.splitlines() if l)), indent=0))
