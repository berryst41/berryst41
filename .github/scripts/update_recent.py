# 프로필 README의 자동 칸들을 다른 저장소 내용으로 새로 채워요.
#   TOOLS  : school 저장소 README의 "한눈에 보기" 표를 묶음(업무용·수업용)째 가져와요.
#   TOYS   : toy-store 안의 장난감 폴더마다 README 첫 소개 줄을 가져와요. 폴더에 zip이 있으면 받기 단추도 달아요.
#   RECENT : 최근 업데이트된 공개 저장소 5개 (설명이 없으면 README 첫 소개 줄).
import datetime, json, os, re, urllib.error, urllib.parse, urllib.request

USER = "berryst41"
API = "https://api.github.com"
TOKEN = os.environ["GITHUB_TOKEN"]

# 가장 최근에 만든 것 옆에 붙는 노란 배지
NEW = ' <img src="https://img.shields.io/badge/new!-ffd43b?style=flat-square" alt="new!" height="16">'

# 프로필에서만 다르게 보이고 싶은 설명 (도구 이름: 설명)
OVERRIDES = {
    "폭탄원숭이": "3명이 협동해서 폭탄을 해체하며 서로 돕는 법을 배우는 게임",
    "자료 공유 사이트": "사진·영상·파일을 QR코드로 학생들이 업로드하고 다운로드할 수 있는 공간",
}

# 도구를 처음 본 날짜 (new! 배지를 누구에게 달지 정할 때 써요)
SEEN = os.path.join(os.path.dirname(__file__), "tools-seen.json")


def get(path, raw=False):
    accept = "application/vnd.github.raw" if raw else "application/vnd.github+json"
    # 한글 폴더 이름도 주소에 쓸 수 있게 바꿔요
    req = urllib.request.Request(API + urllib.parse.quote(path, safe="/?=&"), headers={"Accept": accept, "Authorization": f"Bearer {TOKEN}"})
    try:
        body = urllib.request.urlopen(req).read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    return body if raw else json.loads(body)


def summary(md):
    """README에서 제목·배지·표를 건너뛰고 첫 소개 문장을 뽑아요."""
    for line in (md or "").splitlines():
        line = line.strip()
        if not line or line[0] in "#<!|>`-*" and not line.startswith("**"):
            continue
        line = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", line)
        line = line.replace("**", "").replace("|", "/").strip()
        if re.search(r"[가-힣A-Za-z]", line):
            return line[:80]
    return ""


def tools_block():
    md = get(f"/repos/{USER}/school/readme", raw=True) or ""
    m = re.search(r"## ✨ 한눈에 보기\s*\n(.*?)\n---", md, re.S)
    rows, out = [], []  # rows: [이름, 칸 html...]
    for tr in re.findall(r"<tr>(.*?)</tr>", m.group(1) if m else "", re.S):
        if "<th" in tr:
            out.append(tr.replace("<sub>(누르면 설명으로)</sub>", "").replace("도구 <", "도구<"))
            continue
        cells = re.findall(r"<td([^>]*)>(.*?)</td>", tr, re.S)
        if len(cells) == 1:  # 묶음 제목 (업무용·수업용)
            out.append(f"<td{cells[0][0]}>{cells[0][1]}</td>")
            continue
        name = re.sub(r"<[^>]+>", "", cells[0][1]).split(" ", 1)[-1].strip()
        cells = [[attr, html.replace('href="#', f'href="https://github.com/{USER}/school#')] for attr, html in cells]
        if name in OVERRIDES:
            cells[1][1] = OVERRIDES[name]
        rows.append((name, cells))
        out.append(cells)
    # 표 순서는 마음대로 바꿀 수 있으니, 처음 본 날짜를 기억해 두고 가장 늦게 들어온 도구에 new!를 달아요
    seen = json.load(open(SEEN, encoding="utf-8")) if os.path.exists(SEEN) else {}
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for name, _ in rows:
        seen.setdefault(name, now)
    if rows:
        max(rows, key=lambda r: seen[r[0]])[1][0][1] += NEW
    with open(SEEN, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)
        f.write("\n")
    lines = ["<table>"]
    for r in out:
        if isinstance(r, str):
            lines.append(f"<tr>{r.strip()}</tr>")
        else:
            lines += ["<tr>"] + [f"<td{a}>{h}</td>" for a, h in r] + ["</tr>"]
    return "\n".join(lines + ["</table>"])


def toys_block():
    items = get(f"/repos/{USER}/toy-store/contents/") or []
    out = ["| 장난감 | 어떤 거예요? | 받기 |", "|:---|:---|:---:|"]
    toys = []
    for it in (i for i in items if i["type"] == "dir" and not i["name"].startswith(".")):
        commits = get(f"/repos/{USER}/toy-store/commits?path={it['path']}&per_page=100") or []
        born = commits[-1]["commit"]["committer"]["date"] if commits else ""
        readme = get(f"/repos/{USER}/toy-store/contents/{it['path']}/README.md", raw=True)
        desc = summary(readme)
        # 장난감 README의 "지금 버전: **v0.3.3**"을 읽어 받기 단추에 함께 적어요
        ver = re.search(r"지금 버전:\s*\*\*(v?[\d.]+)\*\*", readme or "")
        ver = " " + ver.group(1) if ver else ""
        # 폴더 바로 안에 있는 zip을 프로필에서 바로 내려받게 해요
        files = get(f"/repos/{USER}/toy-store/contents/{it['path']}") or []
        zips = [f for f in files if f["type"] == "file" and f["name"].lower().endswith(".zip")]
        link = f"[**⬇️ 받기{ver}**](https://github.com/{USER}/toy-store/raw/main/{urllib.parse.quote(zips[0]['path'])})" if zips else ""
        toys.append((born, it, desc, link))
    toys.sort(key=lambda t: t[0], reverse=True)  # 최근에 만든 장난감이 위로
    for n, (born, it, desc, link) in enumerate(toys):
        out.append(f"| [**{it['name']}**]({it['html_url']}){NEW if n == 0 else ''} | {desc} | {link} |")
    if len(out) == 2:
        out.append("| 📦 *곧 첫 장난감이 들어와요!* | | |")
    return "\n".join(out)


def recent_block():
    kst = datetime.timezone(datetime.timedelta(hours=9))
    out = ["| 저장소 | 설명 | 마지막 업데이트 |", "|:---|:---|:---:|"]
    repos = [r for r in get(f"/users/{USER}/repos?sort=pushed&per_page=20")
             if r["name"] != USER and not r["fork"] and not r["private"]]
    newest = max((r["created_at"] for r in repos), default="")
    for r in repos:
        desc = (r["description"] or "").replace("|", "/") or summary(get(f"/repos/{USER}/{r['name']}/readme", raw=True))
        day = datetime.datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00")).astimezone(kst)
        badge = NEW if r["created_at"] == newest else ""
        out.append(f"| [**{r['name']}**]({r['html_url']}){badge} | {desc} | {day:%Y.%m.%d} |")
        if len(out) == 7:
            break
    return "\n".join(out)


def fill(text, key, block):
    start, end = f"<!-- {key}:START -->", f"<!-- {key}:END -->"
    return re.sub(re.escape(start) + r".*?" + re.escape(end), lambda _: f"{start}\n{block}\n{end}", text, flags=re.S)


path = "README.md"
text = open(path, encoding="utf-8").read()
new = text
for key, make in (("TOOLS", tools_block), ("TOYS", toys_block), ("RECENT", recent_block)):
    if f"<!-- {key}:START -->" in new:
        new = fill(new, key, make())
if new != text:
    open(path, "w", encoding="utf-8").write(new)
    print("README updated")
else:
    print("No change")
