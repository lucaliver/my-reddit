# my-reddit 📰

Feed Reddit personalizzato con digest giornaliero su Telegram.

Definisci i subreddit che ti interessano, il sistema li scarica via RSS, filtra via i post troppo recenti/vecchi o con keyword indesiderate, raggruppa per subreddit e ti manda tutto su Telegram ogni mattina.

**Nessun API key Reddit necessaria** — usa i feed RSS pubblici.

## Come funziona

Il progetto è una **pipeline a 4 step** che trasforma un feed RSS grezzo in un messaggio Telegram pulito. Ogni step ha il suo modulo dedicato e fa una cosa sola.

### Il flusso completo

```
┌─────────────────────────────────────────────────────────────────┐
│  GitHub Actions (ogni giorno alle 18:00 CEST)                   │
│  oppure: python3 main.py (lancio manuale)                       │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
          ┌────────────────────────┐
          │  1. FETCH (RSS)        │  reddit_client.py
          │                        │
          │  Costruisce un URL     │  r/python+webdev+programming/top.rss
          │  multi-subreddit e     │
          │  scarica TUTTI i post  │  → 1 sola richiesta HTTP
          │  in una sola chiamata. │
          │                        │  Parsa l'XML Atom e normalizza
          │  Output: lista di      │  ogni <entry> in un dict Python
          │  100 post grezzi       │  con: titolo, link, data, subreddit
          └───────────┬────────────┘
                      │
                      ▼
          ┌────────────────────────┐
          │  2. FILTER             │  filter.py
          │                        │
          │  Applica filtri in     │  1) Età: tiene solo post tra
          │  sequenza, scartando   │     24h e 48h (configurabile)
          │  ciò che non passa.    │  2) Keyword: scarta titoli che
          │                        │     contengono parole bloccate
          │  Output: ~10-20 post   │
          │  che soddisfano i      │  Ogni filtro logga quanti post
          │  criteri               │  ha rimosso, utile per il tuning
          └───────────┬────────────┘
                      │
                      ▼
          ┌────────────────────────┐
          │  3. GROUP              │  grouper.py
          │                        │
          │  Raggruppa i post per  │  I subreddit possono essere
          │  subreddit o per       │  aggregati in gruppi custom:
          │  gruppo personalizzato │  es. "Tech" = python+webdev
          │                        │
          │  Dentro ogni gruppo    │  Ordina i gruppi per score
          │  taglia a max 5 post   │  medio (decrescente)
          └───────────┬────────────┘
                      │
                      ▼
          ┌────────────────────────┐
          │  4. SEND               │  telegram_sender.py
          │                        │
          │  Formatta in HTML per  │  Titoli come link cliccabili,
          │  Telegram, con header  │  separatori tra gruppi
          │  e separatori.         │
          │                        │  Se il messaggio supera 4096
          │  Chiama l'API Telegram │  char (limite Telegram) lo
          │  via HTTP POST.        │  spezza automaticamente
          └────────────────────────┘
```

### Perché RSS e non le API Reddit?

Reddit ha chiuso l'accesso self-service alle API nel 2025 (Responsible Builder Policy). Per creare un'app API serve ora un processo di approvazione manuale che può richiedere settimane e spesso viene negato per script personali.

I feed RSS pubblici (`reddit.com/r/.../top.rss`) funzionano ancora senza autenticazione. Il trade-off:

| | API (PRAW) | RSS |
|---|---|---|
| **Autenticazione** | Richiede approvazione | Nessuna |
| **Score/upvote** | ✅ Disponibile | ❌ Non esposto |
| **Commenti count** | ✅ Disponibile | ❌ Non esposto |
| **Feed personalizzato** | ✅ La tua home | ❌ Devi elencare i subreddit |
| **Rate limiting** | 100 req/min | Aggressivo ma ok per 1 req/giorno |

Per compensare l'assenza dello score, usiamo il sort `top` — Reddit ordina i post per score internamente, quindi quelli in cima hanno già centinaia/migliaia di upvote.

### I moduli nel dettaglio

```
my-reddit/
├── main.py                    # Entry point — orchestra i 4 step
├── config.py                  # Legge tutte le config da env/`.env`
│
├── src/
│   ├── reddit_client.py       # Step 1: HTTP GET → XML parsing
│   ├── filter.py              # Step 2: filtra per età e keyword
│   ├── grouper.py             # Step 3: raggruppa e ordina
│   └── telegram_sender.py     # Step 4: formatta HTML e invia
│
├── .github/workflows/
│   └── daily_feed.yml         # Cron GitHub Actions
│
├── .env.example               # Template per le config locali
├── .env                       # Le TUE config (non committato)
├── requirements.txt           # requests + python-dotenv
└── .gitignore                 # Protegge .env e __pycache__
```

**`main.py`** — 40 righe. Chiama i 4 moduli in sequenza e gestisce gli errori. Se un qualsiasi step non produce dati (es. zero post dopo il filtraggio), si ferma con un warning invece di inviare un messaggio vuoto.

**`config.py`** — Legge tutte le impostazioni da variabili d'ambiente (che vengono dal file `.env` in locale, o dai GitHub Secrets/Variables in CI). Ogni parametro ha un default sensato, quindi funziona anche senza configurare nulla tranne Telegram e i subreddit.

**`reddit_client.py`** — Concatena tutti i subreddit con `+` e fa un'unica richiesta a `r/a+b+c/top.rss`. L'XML viene parsato con la libreria standard `xml.etree`. Se Reddit risponde 429 (rate limit), ritenta con backoff esponenziale (10s → 20s → 40s). Se hai più di 50 subreddit, li spezza in batch.

**`filter.py`** — Due filtri in cascata. Prima scarta per età (troppo freschi o troppo vecchi), poi per keyword. L'ordine conta: l'età è il filtro più veloce e scarta di più, quindi va per primo.

**`grouper.py`** — Legge la mappa `SUBREDDIT_GROUPS` e assegna ogni post al suo gruppo. I subreddit non mappati diventano un gruppo a sé. Dentro ogni gruppo, i post sono ordinati per la posizione che Reddit gli ha dato (il sort `top` fa già il ranking). I gruppi sono ordinati per "importanza" (score medio).

**`telegram_sender.py`** — Formatta in HTML (non Markdown, perché i titoli Reddit sono pieni di caratteri speciali che rompono MarkdownV2). Ogni titolo è un `<a href="...">` cliccabile. Se il testo supera i 4096 caratteri, lo spezza sui separatori tra gruppi per non tagliare un gruppo a metà.

### GitHub Actions

Il file `daily_feed.yml` configura un cron che gira ogni giorno alle 16:00 UTC (18:00 ora italiana). Puoi anche triggerarlo manualmente da **Actions → Run workflow** per testare. I secrets (token Telegram) sono separati dalle variables (lista subreddit, keyword bloccate), perché GitHub li gestisce diversamente per sicurezza.

> ⚠️ GitHub disattiva automaticamente i workflow schedulati se il repo non riceve commit per 60 giorni. Basta un commit vuoto (`git commit --allow-empty -m "keep alive"`) per riattivarlo.

---

## Setup rapido

### 1. Bot Telegram

Cerca **@BotFather** su Telegram → `/newbot` → annota il **token**.
Manda `/start` al bot, poi visita `https://api.telegram.org/bot<TOKEN>/getUpdates` per trovare il tuo **chat ID**.

### 2. Configurazione

```bash
cp .env.example .env
```

Compila nel `.env`:

```bash
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=987654321
SUBREDDITS=["python","webdev","gaming"]
```

### 3. Test locale

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

### 4. Deploy su GitHub

Pusha il repo, poi in **Settings → Secrets and variables → Actions** aggiungi:

- **Secrets**: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- **Variables**: `SUBREDDITS`, `SUBREDDIT_GROUPS` (opzionale), `BLOCKED_KEYWORDS` (opzionale)

Il workflow parte ogni giorno alle 18:00 CEST, oppure manualmente da **Actions → Run workflow**.
