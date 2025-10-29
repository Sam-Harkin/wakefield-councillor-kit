# bootstrap.py — generates the whole Wakefield Councillor Kit, static dashboard, and CI
import os, pathlib, textwrap, json
base = pathlib.Path(".")
def w(path, content):
    p = base / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")

# .gitignore
w(".gitignore", """
__pycache__/
*.pyc
storage/wakefield.db
.env
""")

# requirements
w("requirements.txt", """
requests
beautifulsoup4
feedparser
pandas
pydantic
SQLAlchemy>=2.0
python-dateutil
pyyaml
python-dotenv
rich
""")

# README
w("README.md", """
# Wakefield Councillor Kit (free iPhone setup)
This repo pulls key Wakefield data (meetings, consultations, TRO/PSPO, planning list link, crime, floods) into a local SQLite DB,
THEN exports JSON files for a static dashboard hosted by **GitHub Pages**. Updates run via **GitHub Actions** on a schedule.
No hosting bills. No laptop. All iPhone-safe.

## How it works
1) GitHub Actions (every 30 minutes): `python app.py run-all` → builds DB → `python export/static_site.py` → writes `docs/data/*.json`.
2) GitHub Pages serves `docs/index.html` that reads those JSON files.

## Local dev
If you ever use a real computer: `pip install -r requirements.txt` → `python app.py run-all` → `python export/static_site.py` → open docs/index.html.
""")

# config
w("config/example.env", "THEYWORKFORYOU_API_KEY=\n")
w("config/settings.yml", """
timezone: "Europe/London"
council_name: "City of Wakefield Metropolitan District Council"
wards_of_interest:
  - "Wakefield East"
  - "Wakefield North"
  - "Wakefield South"
  - "Wakefield West"
  - "Ossett"
  - "Horbury and South Ossett"
  - "Castleford Central and Glasshoughton"
  - "Pontefract North"
  - "Pontefract South"
  - "Normanton"
  - "Featherstone"
  - "Knottingley"
  - "Altofts and Whitwood"
  - "Hemsworth"
  - "Crofton, Ryhill and Walton"
  - "South Elmsall and South Kirkby"

crime_points:
  wakefield_city_centre: {lat: 53.6833, lon: -1.4970}
  pontefract: {lat: 53.6911, lon: -1.3110}
  castleford: {lat: 53.7240, lon: -1.3550}
""")

# utils
w("utils/common.py", """
from pydantic import BaseModel
from pathlib import Path
import yaml, os
from dotenv import load_dotenv

class Settings(BaseModel):
    timezone: str = "Europe/London"
    council_name: str
    wards_of_interest: list[str]
    crime_points: dict

def load_settings(path: str | Path) -> Settings:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Settings(**data)

def load_env(dotenv_path: str | Path | None = None):
    if dotenv_path is None:
        dotenv_path = Path(".") / ".env"
    if Path(dotenv_path).exists():
        load_dotenv(dotenv_path)
""")

# storage/db.py
w("storage/db.py", """
from sqlalchemy import create_engine, Integer, String, Text, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from pathlib import Path

DB_PATH = Path(__file__).parent / "wakefield.db"
engine = create_engine(f"sqlite:///{DB_PATH}", future=True, echo=False)

class Base(DeclarativeBase): pass

class Meeting(Base):
    __tablename__ = "meetings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(80))
    committee: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(500))
    start_time: Mapped[str] = mapped_column(String(64))
    location: Mapped[str] = mapped_column(String(255), default="")
    url: Mapped[str] = mapped_column(Text)
    published: Mapped[str] = mapped_column(String(64), default="")

class Consultation(Base):
    __tablename__ = "consultations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500))
    closes: Mapped[str] = mapped_column(String(64), default="")
    category: Mapped[str] = mapped_column(String(255), default="")
    url: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(80))

class PlanningApplication(Base):
    __tablename__ = "planning_applications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reference: Mapped[str] = mapped_column(String(64))
    address: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    received_date: Mapped[str] = mapped_column(String(64), default="")
    ward: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(100), default="")
    url: Mapped[str] = mapped_column(Text)

class OrderNotice(Base):
    __tablename__ = "orders_notices"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_type: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(500))
    ward: Mapped[str] = mapped_column(String(255), default="")
    url: Mapped[str] = mapped_column(Text)
    open_date: Mapped[str] = mapped_column(String(64), default="")
    close_date: Mapped[str] = mapped_column(String(64), default="")

class CrimeStat(Base):
    __tablename__ = "crime_stats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    point_key: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(100))
    month: Mapped[str] = mapped_column(String(7))
    count: Mapped[int] = mapped_column(Integer)

class FloodAlert(Base):
    __tablename__ = "flood_alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ta_code: Mapped[str] = mapped_column(String(32))
    area_name: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(Text)
    timeRaised: Mapped[str] = mapped_column(String(64))

def get_session():
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)()
""")

# connectors
w("connectors/modgov_wakefield.py", """
import feedparser, pandas as pd
BASE = "https://mg.wakefield.gov.uk/"

def _parse(url: str) -> pd.DataFrame:
    f = feedparser.parse(url)
    rows=[]
    for e in f.entries:
        rows.append({
            "source": "Wakefield ModernGov",
            "committee": (e.get("tags") or [{}])[0].get("term",""),
            "title": e.get("title",""),
            "start_time": e.get("published",""),
            "location": "",
            "url": e.get("link",""),
            "published": e.get("published",""),
        })
    return pd.DataFrame(rows)

def whats_new(days=14) -> pd.DataFrame:
    return _parse(f"{BASE}mgWhatsNew.aspx?b={days}&RT=2")
""")

w("connectors/modgov_wyca.py", """
import feedparser, pandas as pd
BASE = "https://westyorkshire.moderngov.co.uk/"

def whats_new(days=14) -> pd.DataFrame:
    f = feedparser.parse(f"{BASE}mgWhatsNew.aspx?b={days}&RT=2")
    rows=[]
    for e in f.entries:
        rows.append({
            "source": "WYCA ModernGov",
            "committee": (e.get("tags") or [{}])[0].get("term",""),
            "title": e.get("title",""),
            "start_time": e.get("published",""),
            "location": "",
            "url": e.get("link",""),
            "published": e.get("published",""),
        })
    return pd.DataFrame(rows)
""")

w("connectors/consultations.py", """
import requests, pandas as pd
from bs4 import BeautifulSoup
BASE = "https://www.wakefield.gov.uk"
CONSULT = BASE + "/about-the-council/consultation-and-engagement/wakefield-council-consultations"
TRO = BASE + "/about-the-council/consultation-and-engagement/wakefield-council-consultations/traffic-regulation-orders"
PSPO = BASE + "/anti-social-behaviour/public-space-protection-orders-pspos"

def _grab(url):
    r = requests.get(url, timeout=30); r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    rows=[]
    for a in soup.select("a[href]"):
        t=a.get_text(strip=True); h=a["href"]
        if not t: continue
        if h.startswith("/"): h=BASE+h
        if h.startswith("http"):
            rows.append({"title": t, "url": h})
    return rows

def consultations() -> pd.DataFrame:
    df = pd.DataFrame(_grab(CONSULT))
    if df.empty: return df
    df["source"]="Wakefield Council"; df["category"]=""; df["closes"]=""
    return df[["title","closes","category","url","source"]]

def traffic_reg_orders() -> pd.DataFrame:
    df = pd.DataFrame(_grab(TRO))
    if df.empty: return df
    df["order_type"]="TRO"; df["ward"]=""; df["open_date"]=""; df["close_date"]=""
    return df

def pspo() -> pd.DataFrame:
    df = pd.DataFrame(_grab(PSPO))
    if df.empty: return df
    df["order_type"]="PSPO"; df["ward"]=""; df["open_date"]=""; df["close_date"]=""
    return df
""")

w("connectors/planning_public_access.py", """
import requests, pandas as pd
BASE = "https://planning.wakefield.gov.uk/online-applications/"
WEEKLY = BASE + "weeklyListResults.do?action=firstPage"

def search_recent(days_back: int = 7) -> pd.DataFrame:
    r = requests.get(WEEKLY, timeout=30); r.raise_for_status()
    return pd.DataFrame([{
        "reference":"", "address":"", "description":"See weekly list for recent applications",
        "received_date":"", "ward":"", "status":"", "url": WEEKLY
    }])
""")

w("connectors/police_api.py", """
import requests, pandas as pd
API = "https://data.police.uk/api"

def monthly_crime_counts(lat: float, lon: float, months: list[str]) -> pd.DataFrame:
    rows=[]
    for m in months:
        r = requests.get(f"{API}/crimes-street/all-crime?lat={lat}&lng={lon}&date={m}", timeout=60)
        r.raise_for_status()
        data=r.json(); tally={}
        for c in data:
            tally[c["category"]]=tally.get(c["category"],0)+1
        for cat, count in tally.items():
            rows.append({"category":cat,"month":m,"count":count})
    return pd.DataFrame(rows)
""")

w("connectors/floods_api.py", """
import requests, pandas as pd
BASE = "https://environment.data.gov.uk/flood-monitoring/alerts"

def active_alerts(area: str | None = None) -> pd.DataFrame:
    r=requests.get(BASE, timeout=30); r.raise_for_status()
    js=r.json(); rows=[]
    for it in js.get("items", []):
        if area and area.lower() not in (it.get("area","")+it.get("description","")).lower():
            continue
        rows.append({
            "ta_code": it.get("floodAreaID",""),
            "area_name": it.get("area",""),
            "severity": it.get("severity",""),
            "message": it.get("message",""),
            "timeRaised": it.get("timeRaised",""),
        })
    return pd.DataFrame(rows)
""")

# pipelines/orchestrator.py
w("pipelines/orchestrator.py", """
from storage.db import get_session, Meeting, Consultation, PlanningApplication, OrderNotice, CrimeStat, FloodAlert
from connectors import modgov_wakefield as wf, modgov_wyca as wyca, consultations as cons, planning_public_access as planning
from connectors import police_api, floods_api
from utils.common import load_settings
from datetime import datetime
import pandas as pd

def save_df(df, model, session, map_cols: dict):
    if df is None or df.empty: return 0
    count=0
    for _, row in df.iterrows():
        obj = model(**{k: row.get(v, None) for k,v in map_cols.items()})
        session.add(obj); count+=1
    session.commit(); return count

def run_all(settings_path: str = "config/settings.yml") -> dict:
    settings = load_settings(settings_path)
    s = get_session()
    report = {}

    df_wf = wf.whats_new(14)
    report["wf_whatsnew"] = save_df(df_wf, Meeting, s, {
        "source":"source","committee":"committee","title":"title","start_time":"start_time",
        "location":"location","url":"url","published":"published"
    })

    df_wy = wyca.whats_new(14)
    report["wyca_whatsnew"] = save_df(df_wy, Meeting, s, {
        "source":"source","committee":"committee","title":"title","start_time":"start_time",
        "location":"location","url":"url","published":"published"
    })

    df_c = cons.consultations()
    report["consultations"] = save_df(df_c, Consultation, s, {
        "title":"title","closes":"closes","category":"category","url":"url","source":"source"
    })

    df_tro = cons.traffic_reg_orders()
    report["tro"] = save_df(df_tro, OrderNotice, s, {
        "order_type":"order_type","title":"title","ward":"ward","url":"url","open_date":"open_date","close_date":"close_date"
    })
    df_pspo = cons.pspo()
    report["pspo"] = save_df(df_pspo, OrderNotice, s, {
        "order_type":"order_type","title":"title","ward":"ward","url":"url","open_date":"open_date","close_date":"close_date"
    })

    df_pl = planning.search_recent(7)
    report["planning"] = save_df(df_pl, PlanningApplication, s, {
        "reference":"reference","address":"address","description":"description","received_date":"received_date",
        "ward":"ward","status":"status","url":"url"
    })

    # Police: last 3 months yyyy-mm
    months=[]
    today = pd.Timestamp.utcnow()
    for i in range(1,4):
        months.append((today - pd.DateOffset(months=i)).strftime("%Y-%m"))
    total=0
    for key, pt in load_settings(settings_path).crime_points.items():
        df = police_api.monthly_crime_counts(pt["lat"], pt["lon"], months)
        if not df.empty:
            df["point_key"]=key
            total += save_df(df, CrimeStat, s, {
                "point_key":"point_key","category":"category","month":"month","count":"count"
            })
    report["crime"] = total

    df_fl = floods_api.active_alerts("Wakefield")
    report["floods"] = save_df(df_fl, FloodAlert, s, {
        "ta_code":"ta_code","area_name":"area_name","severity":"severity","message":"message","timeRaised":"timeRaised"
    })
    return report
""")

# app.py
w("app.py", """
from pipelines.orchestrator import run_all
from rich import print
if __name__ == "__main__":
    print(run_all())
""")

# exporter for static site
w("export/static_site.py", """
import json, time
from pathlib import Path
from storage.db import get_session, Meeting, Consultation, PlanningApplication, OrderNotice, CrimeStat, FloodAlert

out = Path("docs/data"); out.mkdir(parents=True, exist_ok=True)
s = get_session()

def dump(name, rows):
    (out / f"{name}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

dump("meetings", [
    {"when": r.start_time, "committee": r.committee, "title": r.title, "source": r.source, "url": r.url}
    for r in s.query(Meeting).order_by(Meeting.id.desc()).limit(200)
])

dump("consultations", [
    {"title": r.title, "closes": r.closes, "url": r.url, "source": r.source}
    for r in s.query(Consultation).order_by(Consultation.id.desc()).limit(400)
])

dump("orders", [
    {"type": r.order_type, "title": r.title, "ward": r.ward, "url": r.url}
    for r in s.query(OrderNotice).order_by(OrderNotice.id.desc()).limit(400)
])

dump("planning", [
    {"ref": r.reference, "desc": r.description, "ward": r.ward, "url": r.url}
    for r in s.query(PlanningApplication).order_by(PlanningApplication.id.desc()).limit(200)
])

dump("crime", [
    {"point": r.point_key, "month": r.month, "category": r.category, "count": r.count}
    for r in s.query(CrimeStat).order_by(CrimeStat.id.desc()).limit(2000)
])

dump("floods", [
    {"area": r.area_name, "severity": r.severity, "message": r.message, "raised": r.timeRaised}
    for r in s.query(FloodAlert).order_by(FloodAlert.id.desc()).limit(200)
])

(Path("docs/meta.json")).write_text(json.dumps({"last_updated_utc": time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime())}), encoding="utf-8")
print("Exported static JSON to docs/data/")
""")

# static site (GitHub Pages)
w("docs/index.html", """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Wakefield Councillor Dashboard (Static)</title>
<link rel="stylesheet" href="style.css"/>
</head>
<body>
<header>
  <h1>Wakefield Councillor Dashboard</h1>
  <div id="updated"></div>
</header>
<nav>
  <button data-target="meetings">Meetings</button>
  <button data-target="consultations">Consultations</button>
  <button data-target="orders">TRO / PSPO</button>
  <button data-target="planning">Planning</button>
  <button data-target="crime">Crime</button>
  <button data-target="floods">Floods</button>
</nav>
<main id="content"></main>
<footer>
  <p>Free, phone-friendly, no hosting bill. Data from public sources; links go to originals.</p>
</footer>
<script src="app.js"></script>
</body>
</html>
""")

w("docs/style.css", """
:root { --bg: #0f172a; --fg: #e2e8f0; --accent:#38bdf8; --muted:#94a3b8; }
html,body{margin:0;padding:0;background:var(--bg);color:var(--fg);font:16px/1.4 system-ui,-apple-system;}
header{padding:16px;border-bottom:1px solid #1f2937}
h1{margin:0;font-size:20px}
#updated{color:var(--muted);font-size:13px;margin-top:6px}
nav{display:flex;gap:8px;flex-wrap:wrap;padding:12px;border-bottom:1px solid #1f2937}
nav button{background:#111827;color:var(--fg);border:1px solid #334155;padding:8px 10px;border-radius:6px}
nav button:focus{outline:2px solid var(--accent)}
main{padding:12px}
.table{width:100%;border-collapse:collapse}
.table th,.table td{border-bottom:1px solid #1f2937;padding:8px;vertical-align:top}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
@media (max-width:600px){ .table th,.table td{font-size:14px} }
""")

w("docs/app.js", """
async function getJSON(path){ const r = await fetch(path); return r.json(); }
function el(tag, attrs={}, children=[]){
  const e=document.createElement(tag);
  Object.entries(attrs).forEach(([k,v])=> e.setAttribute(k,v));
  [].concat(children).forEach(c=> e.append(c.nodeType?c:document.createTextNode(c)));
  return e;
}
function table(headers, rows){
  const t=el('table',{class:'table'});
  const thead=el('thead'); const tr=el('tr');
  headers.forEach(h=> tr.append(el('th',{},h))); thead.append(tr); t.append(thead);
  const tb=el('tbody');
  rows.forEach(r=>{
    const tr=el('tr');
    r.forEach(cell=> tr.append(el('td',{}, cell)));
    tb.append(tr);
  });
  t.append(tb); return t;
}
function link(href, text){ const a=el('a',{href,target:'_blank',rel:'noopener'}); a.textContent=text; return a;}

const loaders = {
  async meetings(){
    const data = await getJSON('data/meetings.json');
    return table(['When','Committee','Title','Source'], data.map(d=>[
      d.when, d.committee, link(d.url, d.title), d.source
    ]));
  },
  async consultations(){
    const data = await getJSON('data/consultations.json');
    return table(['Title','Closes','Source'], data.map(d=>[
      link(d.url, d.title), d.closes||'—', d.source||'Wakefield Council'
    ]));
  },
  async orders(){
    const data = await getJSON('data/orders.json');
    return table(['Type','Title','Ward'], data.map(d=>[
      d.type, link(d.url, d.title), d.ward||''
    ]));
  },
  async planning(){
    const data = await getJSON('data/planning.json');
    return table(['Ref','Description','Ward'], data.map(d=>[
      d.ref||'', link(d.url, d.desc), d.ward||''
    ]));
  },
  async crime(){
    const data = await getJSON('data/crime.json');
    return table(['Point','Month','Category','Count'], data.map(d=>[
      d.point, d.month, d.category, String(d.count)
    ]));
  },
  async floods(){
    const data = await getJSON('data/floods.json');
    return table(['Area','Severity','Message','Raised'], data.map(d=>[
      d.area, d.severity||'', d.message||'', d.raised||''
    ]));
  }
};

async function load(section){
  const main=document.getElementById('content');
  main.innerHTML='Loading…';
  const view = await loaders[section]();
  main.innerHTML=''; main.append(view);
}
document.querySelectorAll('nav button').forEach(b=>{
  b.addEventListener('click', ()=> load(b.dataset.target));
});
(async()=>{
  try{
    const meta = await getJSON('meta.json');
    document.getElementById('updated').textContent = 'Last update: '+ meta.last_updated_utc + ' (UTC)';
  }catch(e){}
  load('meetings');
})();
""")

# GitHub Actions workflow: scheduled updates + manual trigger
w(".github/workflows/update.yml", """
name: Update data and publish dashboard
on:
  schedule:
    - cron: "*/30 * * * *"
  workflow_dispatch:
permissions:
  contents: write
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install deps
        run: pip install -r requirements.txt
      - name: Run pipeline
        run: python app.py
      - name: Export static site data
        run: python export/static_site.py
      - name: Commit JSON
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add docs/data/*.json docs/meta.json
          git commit -m "Update dashboard data [skip ci]" || echo "No changes to commit"
          git push
""")

print("Project scaffolded. Commit & push these files, then enable GitHub Pages -> /docs.")