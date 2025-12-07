import json
with open("data/finma.txt", "r") as f:
    contents = f.read()
contents = contents.split("\n")

sentences = []
for line in contents:
    if len(line) == 0:
        continue
    line = json.loads(line)
    line = f"{line['title']} {line['link']} {line['pubDate']} {line['description']}"
    sentences.append(line)