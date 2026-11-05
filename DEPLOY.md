# Deploy do Sabiá

## Estado atual (2026-11-05)

- **Produção:** <https://sabia-1gv2.onrender.com> (Render free).
- **Repo:** `nalugcs/Sabia---Caminho-1`, branch **`Estudos`** (é o default).
- **Atualizar o app:** dê push no branch `Estudos`; o Render redeploya.
- **Conta:** sempre `nalugcs` (Ana). O repo `ironidesflj/sabia-tcc` deve ser apagado.

Para publicar a identidade v0.2 ou qualquer mudança:

1. Baixe o zip atualizado do projeto.
2. Na pasta local do repo da Ana, substitua os arquivos (mantenha o `.git` e o
   `render.yaml` dela, se já estiver em plano free).
3. Commit e push no branch **`Estudos`** (GitHub Desktop ou `git push`).
4. O Render redeploya sozinho.

> O histórico local desta máquina e o do repo da Ana são independentes; **não faça
> force push**. Se a Ana autenticar o `gh` nesta máquina, eu reconcilio os históricos e
> publico sem sobrescrever.

---

**Conta correta:** Ana (`nalugcs`) · **Repositório:** <https://github.com/nalugcs/Sabia---Caminho-1>

O repositório antigo (`ironidesflj/sabia-tcc`) **não deve ser usado**; apague em
`Settings → Danger Zone → Delete this repository` (a sessão atual do `gh` não tem o
escopo `delete_repo`).


## 0. Estado do repositório da Ana

- É público e tem só um `README.md` no branch `Estudos`.
- O código do app ainda está nesta máquina, no branch `main`.
- O remote local já aponta para o repositório da Ana.

## 1. Colocar o código no GitHub da Ana

### Se a Ana estiver nesta máquina

```bash
gh auth logout
gh auth login --hostname github.com --git-protocol https --web
# escolha a conta nalugcs no navegador

cd /Users/iron/Documents/deepseek-harness/default-workspace/tcc-ana/app
git remote -v        # deve mostrar nalugcs/Sabia---Caminho-1
git push -u origin main
```

Depois, no GitHub: **Settings → Branches → Default branch → main**.
O branch `Estudos` pode ser apagado depois.

### Se a Ana estiver em outra máquina

Envie um destes arquivos (gerados na pasta `tcc-ana/`):

- `sabia-main.bundle` — histórico completo;
- `sabia-tcc.zip` — arquivos, sem `.git`.

Com o bundle:

```bash
git clone sabia-main.bundle sabia
cd sabia
git remote set-url origin https://github.com/nalugcs/Sabia---Caminho-1.git
git push -u origin main
```

Com o zip:

```bash
unzip sabia-tcc.zip -d sabia && cd sabia
git init -b main
git add . && git commit -m "Sabiá MVP"
git remote add origin https://github.com/nalugcs/Sabia---Caminho-1.git
git push -u origin main
```

## 2. Render (conta da Ana)

1. Entre em <https://dashboard.render.com> com GitHub **nalugcs**.
2. Se o repositório não aparecer, autorize o GitHub App do Render para ele
   (GitHub → Settings → Applications → Render → Configure).
3. **New → Blueprint** → escolha `Sabia---Caminho-1` → branch `main`.
4. Preencha:
   - `LLM_API_KEY`: a mesma chave que já funciona no `.env`;
   - `ADMIN_PASSWORD`: senha forte;
   - `LLM_PROVIDER=openai`;
   - `LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai`;
   - `LLM_MODEL=gemini-3.1-flash-lite` (ou o modelo que você validou).
5. Plano do web service: `starter` (~US$ 7/mês). O free hiberna e dá cold start.
6. Banco: o Blueprint cria um Postgres free que **expira em ~30 dias**.
   Para a coleta inteira, use Neon free e troque `DATABASE_URL`.
7. **Apply** e acompanhe os logs até `app iniciado`.
8. Abra `https://SEU-SERVICO.onrender.com/health` e depois `/admin`.

Link direto (só funciona depois do push e do branch `main` como default):

<https://render.com/deploy?repo=https://github.com/nalugcs/Sabia---Caminho-1>

## 3. Depois do deploy

1. Abra `/admin` e entre com a senha.
2. Cadastre um participante de teste e faça uma lição até o feedback.
3. Exporte `participantes.csv` e `turnos.csv`; confira que não há nome/sobrenome.
4. Rode o piloto de 3–5 pessoas (`docs/piloto.md`).
5. Configure backup:
   ```bash
   DATABASE_URL="postgresql://..." ./scripts/backup_db.sh
   ```
   Agende no cron ou em um job do provedor.
6. Só depois abra para ~100 pessoas.

## Variáveis de produção

| Variável | Valor |
|---|---|
| `APP_SECRET` | gerado pelo Render |
| `DATABASE_URL` | Postgres do Render ou Neon |
| `LLM_PROVIDER` | `openai` (interface compatível) |
| `LLM_BASE_URL` | Gemini ou OpenAI |
| `LLM_API_KEY` | chave |
| `LLM_MODEL` | modelo validado |
| `ADMIN_PASSWORD` | senha forte |
| `APP_COOKIE_SECURE` | `1` |
| `RATE_LIMIT_ENABLED` | `1` |

## Custos

- Web `starter`: ~US$ 7/mês.
- Postgres free do Render: expira em ~30 dias.
- Neon free: suficiente para o TCC, com backup/PITR limitado.
- OpenAI/Gemini: centavos a poucos dólares para 100 pessoas × 3 sessões.

## Checklist

- [ ] Repositório antigo apagado.
- [ ] Push no repo da Ana concluído.
- [ ] Branch default = `main`.
- [ ] Render criado e `/health` verde.
- [ ] Admin abre e senha trocada.
- [ ] Lição de teste completa.
- [ ] Export CSV pseudonimizado.
- [ ] Backup testado.
- [ ] Piloto feito.
