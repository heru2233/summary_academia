# PROJECT LOG - Academic Summary Pipeline

> **Last updated**: 26 August 2026
> **Current session**: Buffy (Freebuff) - Sesi 8: Auto-Start Bot

---

## PROJECT SUMMARY

This project converts academic materials (PDF books & journal articles) into **HTML summaries** in two languages (Indonesian & English), then publishes them to **GitHub Pages** for reading on any device.

### Workflow
```
PDF → PyMuPDF (fitz) → Text → AI Summarizes → HTML (IND + ENG) → GitHub Pages
```

---

## FOLDER STRUCTURE

```
D:\summary_msi\
├── sources/                          # Original PDFs (NOT in git)
│   ├── books/
│   │   └── financial-institutions-management/
│   │       └── ch1-ch7.pdf
│   └── articles/
│       ├── myers-1984/
│       │   └── Myers_1984.pdf
│       ├── mcinnes-1982/
│       │   └── McInnes_1982.pdf
│       └── what-theory-is-not/
│           └── What_theory_is_not.pdf
│
├── templates/                        # Prompt templates (NOT in git)
│   ├── PROMPT_TEMPLATE_BOOK.md
│   └── PROMPT_TEMPLATE_ARTICLE.md
│
├── scripts/                          # Python scripts
│   ├── publish.py                    # Publish script (parameterized)
│   ├── auto_summary.py               # CLI auto-summary (PyMuPDF + OpenRouter)
│   ├── telegram_bot.py               # Telegram bot (auto-detect title, lang both)
│   ├── config.py                     # Config loader (reads .env)
│   ├── requirements.txt              # Python dependencies
│   ├── logs/                         # Bot logs (NOT in git)
│   ├── .env                          # Tokens (NOT in git)
│   └── .env.example                  # Template without tokens
│
├── docs/                             # GitHub Pages (IN git)
│   ├── index.html                    # Main page (English)
│   ├── css/
│   │   └── responsive.css            # Mobile/tablet support
│   ├── books/
│   │   ├── index.html                # Book listing
│   │   └── financial-inst-mgmt/
│   │       ├── index.html            # ENG/IND selection
│   │       ├── chapters-eng.html     # English chapters
│   │       ├── chapters-ind.html     # Indonesian chapters
│   │       └── Ringkasan_Chapter_*.html (14 files)
│   └── articles/
│       ├── index.html                # Article listing
│       ├── myers-1984/
│       │   ├── index.html            # ENG/IND selection
│       │   └── Ringkasan_Myers_1984_*.html (2 files)
│       └── mcinnes-1982/
│           ├── index.html            # ENG/IND selection
│           └── Ringkasan_McInnes_1982_*.html (2 files)
│
├── .gitignore
├── BLUEPRINT.md
└── PROJECT_LOG.md                    # This file
```

---

## WORK COMPLETED

### Session 1 (26 Aug 2026) - Initial Setup
- [x] Read and understood project structure
- [x] Created PROJECT_LOG.md
- [x] Created BLUEPRINT.md

### Session 2 (26 Aug 2026) - Script + GitHub Pages
- [x] Created `scripts/publish.py` (parameterized, no hardcoded paths)
- [x] Created `scripts/config.py` (reads from .env)
- [x] Moved Telegram token from config.py to .env (security)
- [x] Created `.gitignore` (excludes .env, sources/, etc.)
- [x] Set up GitHub repository: `heru2233/summary_academia`
- [x] Enabled GitHub Pages (source: /docs)
- [x] Generated docs/ for all 18 HTML files (7 chapters x 2 lang + 2 articles x 2 lang)
- [x] Created navigation index pages

### Session 3 (26 Aug 2026) - Responsive + Migration
- [x] Created `docs/css/responsive.css` (mobile/tablet/desktop)
- [x] Updated all 28 HTML files with responsive CSS link
- [x] Reorganized navigation: Main → Books/Articles → Select Title → ENG/IND → Content
- [x] Migrated @1/@2/@3 to `sources/` with clean naming
- [x] Migrated templates to `templates/`
- [x] Updated .gitignore to exclude sources/, templates/, @1/@2/@3
- [x] Updated publish.py template for future responsive files

### Session 4 (26 Aug 2026) - Auto-Summary Script
- [x] Created `scripts/auto_summary.py` (PDF → HTML via OpenRouter API)
- [x] Integrated OpenRouter API with free models
- [x] Added OpenRouter API key to `.env`
- [x] Tested successfully with `nvidia/nemotron-3-super-120b-a12b:free`
- [x] Generated Chapter 1 English summary as test

### Session 8 (26 Aug 2026) - Auto-Start Bot
- [x] Created `start_bot.bat` - Script untuk start bot
- [x] Created `stop_bot.bat` - Script untuk stop bot
- [x] Copy ke Windows Startup folder (auto-start saat boot)
- [x] Bot jalan 24/7 seperti VPS

### Session 7 (26 Aug 2026) - List & Delete Features
- [x] `/list` - Lihat semua ringkasan tersimpan (books & articles)
- [x] `/delete [nomor]` - Hapus ringkasan berdasarkan nomor
- [x] Auto-update `articles/index.html` saat delete
- [x] Auto-push ke GitHub setelah delete
- [x] `/status` sekarang tampilkan jumlah ringkasan

### Session 6 (26 Aug 2026) - Switch AI Model
- [x] Switched from `nvidia/nemotron-3-super-120b-a12b:free` to `z-ai/glm-5.2:free`
- [x] GLM 5.2 has quality score 83 (highest among free models)
- [x] Updated .env, telegram_bot.py, auto_summary.py

### Session 5 (26 Aug 2026) - Revisions & Telegram Bot Improvements
- [x] **PyMuPDF** replaces pdftotext (more reliable PDF extraction)
- [x] **Telegram bot**: Auto-detect title from PDF using AI
- [x] **Telegram bot**: Language always "both" (no selection needed)
- [x] **Telegram bot**: Full logging to `scripts/logs/`
- [x] **Telegram bot**: Auto-detect type (book vs article) from content
- [x] Updated `auto_summary.py` with PyMuPDF + logging
- [x] Updated `requirements.txt` with PyMuPDF

---

## CONTENT STATUS

### Books
| Book | Chapters | IND | ENG | GitHub Pages |
|------|----------|-----|-----|--------------|
| Financial Institutions Management (Saunders & Cornett, 11e) | 7 | 7 | 7 | https://heru2233.github.io/summary_academia/books/financial-inst-mgmt/ |

### Articles
| Article | IND | ENG | GitHub Pages |
|---------|-----|-----|--------------|
| Myers (1984) - The Capital Structure Puzzle | ✅ | ✅ | https://heru2233.github.io/summary_academia/articles/myers-1984/ |
| McInnes (1982) - Financial Control as an Aid to Management | ✅ | ✅ | https://heru2233.github.io/summary_academia/articles/mcinnes-1982/ |
| What Theory is Not | ❌ | ❌ | Not yet (only .docx draft) |

---

## CONFIGURATION

### GitHub Pages
- **URL**: https://heru2233.github.io/summary_academia/
- **Repository**: https://github.com/heru2233/summary_academia
- **Source**: /docs folder on main branch

### OpenRouter API (Auto-Summary)
- **API Key**: In `scripts/.env` (DO NOT commit)
- **Model**: `z-ai/glm-5.2:free` (free tier, quality score 83)
- **Limits**: 200 requests/day, 20 req/min

### Telegram Bot
- **Script**: `scripts/telegram_bot.py`
- **Bot Token**: In `scripts/.env` (DO NOT commit)
- **Logs**: `scripts/logs/bot_YYYYMMDD.log`
- **Flow**: Send PDF → Bot auto-detect title → Choose type → AI summarize (both languages) → Push to GitHub → Send link

---

## RULES & CONVENTIONS

### FILE NAMING
- Book chapters: `Ringkasan_Chapter_[N]_[IND/ENG].html`
- Journal articles: `Ringkasan_[LastName]_[Year]_[IND/ENG].html`

### HTML FORMAT
- Font: Times New Roman 12pt
- Math: MathJax v3 (inline `\\(...\\)`, display `\\[...\\]`)
- Responsive: Link to `css/responsive.css`

### PDF EXTRACTION
- **Primary**: PyMuPDF (`fitz`) - installed via `pip install PyMuPDF`
- **Fallback**: pdftotext (if PyMuPDF fails)
- PyMuPDF is more reliable for complex PDFs with tables/columns

### PUBLISHING
1. Generate HTML using AI with template
2. Save to `docs/{books|articles}/{title}/`
3. Push to GitHub: `git add docs/ && git commit && git push`

### TELEGRAM BOT WORKFLOW
```
1. Run: python telegram_bot.py
2. Send PDF to bot on Telegram
3. Bot auto-detects: title, type (book/article)
4. User only selects: type (book/article)
5. Bot generates: English + Indonesian summaries
6. Bot pushes to GitHub Pages
7. Bot sends link back to user
```

### AUTO-SUMMARY (CLI)
```bash
cd scripts

# With auto-detection
python auto_summary.py --pdf "../sources/books/.../ch1.pdf"

# With manual title
python auto_summary.py --pdf "../sources/books/.../ch1.pdf" --title "Chapter Title" --type book

# Dry run (extract only)
python auto_summary.py --pdf "../sources/books/.../ch1.pdf" --dry-run
```

---

## CONTINUATION PROMPT

When starting a new session, use this prompt:
```
Baca file PROJECT_LOG.md di root proyek. Saya ingin melanjutkan [SPECIFY TASK].
```

---

## TODO / NEXT STEPS

- [x] Auto-summary script with OpenRouter API
- [x] Telegram bot for PDF upload → auto-summary
- [x] PyMuPDF for reliable PDF extraction
- [x] Auto-detect title/type from PDF
- [ ] Batch process all 7 chapters (IND + ENG)
- [ ] Process articles (Myers, McInnes) with auto-summary
- [ ] Convert "What Theory is Not" from .docx to HTML
- [ ] Optional: Add search functionality to the website

---

*Log maintained by Buffy (Freebuff). Update after each session.*
