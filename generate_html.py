#!/usr/bin/env python3
"""
Academic Hub 2026 — Notion API Sync Script
Busca dados do DATABASE Hub 2026 e gera index.html atualizado.
"""
import os, json, re, urllib.request, urllib.parse
from collections import defaultdict
from datetime import datetime

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
HUB_DB_ID = "73f660e1-e881-4e4f-b402-ce731b8a8a54"
PASSWORD_HASH = os.environ.get("HUB_PASSWORD", "Prof2026")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def notion_request(method, path, body=None):
    url = f"https://api.notion.com/v1{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def fetch_all_hub_entries():
    entries, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        result = notion_request("POST", f"/databases/{HUB_DB_ID}/query", body)
        for page in result.get("results", []):
            props = page["properties"]
            def txt(p):
                v = props.get(p, {})
                t = v.get("type", "")
                if t == "title":   return "".join(r["plain_text"] for r in v.get("title", []))
                if t == "select":  return (v.get("select") or {}).get("name", "")
                return ""
            entries.append({
                "id":       page["id"],
                "aluno":    txt("Aluno"),
                "turma":    txt("Turma"),
                "disc":     txt("Disciplina"),
                "situacao": txt("Situação"),
            })
        if not result.get("has_more"):
            break
        cursor = result["next_cursor"]
    return entries

def build_html(entries):
    # Agrupar dados
    turmas = defaultdict(lambda: defaultdict(list))
    for e in entries:
        if e["aluno"]:
            turmas[e["turma"]][e["disc"]].append(e)

    # Contar por situação
    situacao_count = defaultdict(lambda: defaultdict(int))
    for e in entries:
        situacao_count[e["turma"]][e["situacao"]] += 1

    total = len(entries)
    updated = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Gerar JS com dados reais
    disciplines_js = []
    disc_config = [
        ("ADM-7N-MC", "Gest. Estratégica",           "ge",     "#8b5cf6", "disc-ge",     "#ede9fe", "#4c1d95", "GE",  "NOTURNO",  "Montes Claros"),
        ("ADM-6N",    "Gestão p/ MPE",               "mpe6",   "#f97316", "disc-mpe6",   "#ffedd5", "#9a3412", "MPE", "NOTURNO",  "Montes Claros"),
        ("ADM-8N-MC", "Gestão p/ MPE",               "mpe8mc", "#eab308", "disc-mpe8mc", "#fefce8", "#713f12", "MPE", "NOTURNO",  "Montes Claros"),
        ("ADM-8N-BM", "Gestão p/ MPE",               "mpe8bm", "#3b82f6", "disc-mpe8bm", "#dbeafe", "#1e3a8a", "MPE", "NOTURNO",  "Brasília de Minas"),
        ("ADM-8N-BM", "Consultoria",                 "con",    "#6b7280", "disc-con",    "#f1f5f9", "#374151", "CON", "NOTURNO",  "Brasília de Minas"),
    ]
    disc_label = {
        "Gest. Estratégica": "GE",
        "Gestão p/ MPE":     "MPE",
        "Consultoria":       "CON",
    }
    for (turma, disc_full, did, color, cls, bg, fg, code, turno, local) in disc_config:
        alunos = turmas.get(turma, {}).get(disc_full, [])
        disc_str = f"{turma} — {disc_label.get(disc_full, code)}"
        disciplines_js.append(
            f"  {{ id:'{did}', code:'{code}', turma:'{turma}', disc:'{disc_str}', "
            f"full:'{disc_full}', turno:'{turno}', local:'{local}', "
            f"totalAlunos:{len(alunos)}, color:'{color}', cls:'{cls}', bg:'{bg}', fg:'{fg}' }}"
        )

    students_js = []
    counter = 1
    for (turma, disc_full, did, *_) in disc_config:
        alunos = sorted(turmas.get(turma, {}).get(disc_full, []), key=lambda x: x["aluno"])
        disc_str = f"{turma} — {disc_label.get(disc_full, did.upper())}"
        for e in alunos:
            name = e["aluno"].title()
            sit  = e["situacao"] or "Regular"
            students_js.append(
                f"  {{id:'s{counter:03d}', name:'{name}', turma:'{turma}', "
                f"disc:'{disc_str}', situacao:'{sit}', notionId:'{e['id']}'}}"
            )
            counter += 1

    disciplines_block = "const DISCIPLINES = [\\n" + ",\\n".join(disciplines_js) + "\\n];"
    students_block    = "const STUDENTS = [\\n" + ",\\n".join(students_js) + "\\n];"
    meta_block = f"const LAST_UPDATED = '{updated}'; const TOTAL_ALUNOS = {total};"

    return disciplines_block, students_block, meta_block

def inject_into_template(template_path, disciplines_block, students_block, meta_block, output_path):
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    content = re.sub(r'const DISCIPLINES = \\[.*?\\];', disciplines_block, content, flags=re.DOTALL)
    content = re.sub(r'const STUDENTS = \\[.*?\\];',    students_block,    content, flags=re.DOTALL)

    # Inserir / atualizar bloco de metadados
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
    ta_match = re.search(r'TOTAL_ALUNOS = (\\d+)', meta_block)
    ta_val = int(ta_match.group(1)) if ta_match else 0
    if "const LAST_UPDATED" in content:
        content = re.sub(r'const LAST_UPDATED = .*?;', f"const LAST_UPDATED = '{now_str}';", content)
        content = re.sub(r'const TOTAL_ALUNOS = .*?;', f"const TOTAL_ALUNOS = {ta_val};", content)
    else:
        content = content.replace("const DISCIPLINES", meta_block + "\\nconst DISCIPLINES", 1)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ index.html gerado — {datetime.now().strftime('%d/%m/%Y %H:%M')} — {ta_val} entradas")

if __name__ == "__main__":
    print("🔄 Buscando dados do Notion...")
    entries = fetch_all_hub_entries()
    print(f"   {len(entries)} entradas encontradas")
    d, s, m = build_html(entries)
    inject_into_template("template.html", d, s, m, "index.html")
