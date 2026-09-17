import re
import requests

sid = "1M6hc3vmk1bNchMvEwXsIyyO5iq3mAzP877HTXzhzg38"
r = requests.get(
    f"https://docs.google.com/spreadsheets/d/{sid}/edit",
    timeout=30,
    headers={"User-Agent": "Mozilla/5.0"},
)
text = r.text
# sheetId often near sheet title in JSON blobs
for m in re.finditer(r"General single and bulk v2", text):
    start = max(0, m.start() - 200)
    snippet = text[start : m.start() + 80]
    print("---")
    print(snippet.replace("\\n", " ")[:300])

ids = re.findall(r'"sheetId"\s*:\s*(\d+)', text)
print("sheetIds", ids)
names = re.findall(r',"([^"]{5,60})",', text)
for n in names:
    if "general" in n.lower() or "TMT" in n or "bulk" in n.lower():
        print("name:", n)
