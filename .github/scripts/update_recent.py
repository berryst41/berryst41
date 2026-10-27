# 프로필 README의 자동 칸들을 다른 저장소 내용으로 새로 채워요.
#   TOOLS  : school 저장소 README의 "한눈에 보기" 표를 그대로 가져와요.
#   TOYS   : toy-store 안의 장난감 폴더마다 README 첫 소개 줄을 가져와요.
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
    m = re.search(r"## ✨ 한눈에 보기\s*\n(.*?)\n\s*\n", md, re.S)
    rows = [l for l in (m.group(1).splitlines() if m else []) if l.startswith("|")][2:]
    out = ["| | 도구 | 이럴 때 써요 | 바로가기 |", "|:---:|:---|:---|:---:|"]
    for row in rows:
        cells = row.strip("|").split("|")
        if len(cells) < 4:
            continue
        cells = [c.strip() for c in cells]
        cells[1] = re.sub(r"\]\(#", f"](https://github.com/{USER}/school#", cells[1])
        name = re.sub(r"[*\[\]]|\(.*?\)", "", cells[1]).strip()
        cells[2] = OVERRIDES.get(name, cells[2])
        out.append(cells[:4])
    if out[2:]:
        out[-1][1] += NEW  # school 표는 새 도구를 맨 아래에 추가해요
    return "\n".join(r if isinstance(r, str) else "| " + " | ".join(r) + " |" for r in out)


def toys_block():
    items = get(f"/repos/{USER}/toy-store/contents/") or []
    out = ["| 장난감 | 어떤 거예요? |", "|:---|:---|"]
    toys = []
    for it in (i for i in items if i["type"] == "dir" and not i["name"].startswith(".")):
        commits = get(f"/repos/{USER}/toy-store/commits?path={it['path']}&per_page=100") or []
        born = commits[-1]["commit"]["committer"]["date"] if commits else ""
        desc = summary(get(f"/repos/{USER}/toy-store/contents/{it['path']}/README.md", raw=True))
        toys.append((born, it, desc))
    toys.sort(key=lambda t: t[0], reverse=True)  # 최근에 만든 장난감이 위로
    for n, (born, it, desc) in enumerate(toys):
        out.append(f"| [**{it['name']}**]({it['html_url']}){NEW if n == 0 else ''} | {desc} |")
    if len(out) == 2:
        out.append("| 📦 *곧 첫 장난감이 들어와요!* | |")
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
