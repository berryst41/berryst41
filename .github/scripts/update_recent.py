# 프로필 README의 "최근 업데이트" 칸을 공개 저장소 목록으로 새로 채워요.
import datetime, json, os, re, urllib.request

USER = "berryst41"
SKIP = {USER}  # 프로필 저장소 자신은 빼요
COUNT = 5
START, END = "<!-- RECENT:START -->", "<!-- RECENT:END -->"

req = urllib.request.Request(
    f"https://api.github.com/users/{USER}/repos?sort=pushed&per_page=20",
    headers={"Accept": "application/vnd.github+json",
             "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"},
)
repos = json.load(urllib.request.urlopen(req))

kst = datetime.timezone(datetime.timedelta(hours=9))
rows = []
for r in repos:
    if r["name"] in SKIP or r["fork"] or r["private"]:
        continue
    day = datetime.datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00")).astimezone(kst)
    desc = (r["description"] or "").replace("|", "/")
    rows.append(f"| [**{r['name']}**]({r['html_url']}) | {desc} | {day:%Y.%m.%d} |")
    if len(rows) == COUNT:
        break

table = "\n".join(["| 저장소 | 설명 | 마지막 업데이트 |", "|:---|:---|:---:|", *rows])
block = f"{START}\n{table}\n{END}"

path = "README.md"
text = open(path, encoding="utf-8").read()
new = re.sub(re.escape(START) + r".*?" + re.escape(END), block, text, flags=re.S)
if new != text:
    open(path, "w", encoding="utf-8").write(new)
    print("README updated")
else:
    print("No change")
