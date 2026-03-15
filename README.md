# 🎓 Academic Hub 2026 — Prof. Dr. Marcelo Caetano

Dashboard acadêmico sincronizado automaticamente com o Notion.

## Como funciona
- GitHub Actions roda a cada **2 horas** e busca dados do Notion
- Gera `index.html` atualizado e publica no GitHub Pages
- Acesse via Notion (embed) ou diretamente pelo link do GitHub Pages

## Atualização manual
Na aba **Actions** do repositório → clique em **"Sync Notion → GitHub Pages"** → **"Run workflow"**

## Senha de acesso
Configurada via secret `HUB_PASSWORD` no GitHub (Settings → Secrets → Actions).
Senha padrão: `Prof2026`
