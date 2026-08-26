# BLUEPRINT - Academic Summary Pipeline

> **Version**: 3.0 | **Updated**: 26 August 2026

---

## 1. PROJECT OVERVIEW

This project converts **academic materials (PDF)** into **HTML summaries** in two languages (Indonesian & English), published to **GitHub Pages** for reading on any device.

### How It Works

```
You (human) → Chat with AI → AI reads PDF → AI creates HTML → Save to docs/ → Push to GitHub
```

**Important**: There is NO automation from PDF to HTML. You manually chat with AI (Freebuff/ChatGPT/Claude) to create the summaries.

---

## 2. CURRENT WORKFLOW (v3.0)

```
TAHAP 1: PREPARATION
  Place PDF in sources/{books|articles}/{title}/
        ↓
TAHAP 2: AI SUMMARY (manual - in chat AI)
  Use prompt template from templates/
  AI reads PDF → Creates 2 HTML files (IND + ENG)
  Save directly to docs/{books|articles}/{title}/
        ↓
TAHAP 3: NAVIGATION (manual)
  Create/update index.html files for navigation
  Ensure responsive.css is linked
        ↓
TAHAP 4: PUBLISH (git push)
  git add docs/ && git commit && git push
  GitHub Pages auto-deploys
        ↓
TAHAP 5: READ (on any device)
  Open https://heru2233.github.io/summary_academia/
```

---

## 3. FOLDER STRUCTURE (v3.0 - IMPLEMENTED)

```
D:\summary_msi\
│
├── sources/                          # Original PDFs (NOT in git)
│   ├── books/
│   │   └── financial-institutions-management/
│   │       └── ch1-ch7.pdf
│   └── articles/
│       ├── myers-1984/
│       ├── mcinnes-1982/
│       └── what-theory-is-not/
│
├── templates/                        # Prompt templates (NOT in git)
│   ├── PROMPT_TEMPLATE_BOOK.md
│   └── PROMPT_TEMPLATE_ARTICLE.md
│
├── scripts/                          # Python scripts
│   ├── publish.py
│   ├── config.py
│   ├── requirements.txt
│   └── .env (NOT in git)
│
├── docs/                             # GitHub Pages (IN git) ✅ LIVE
│   ├── index.html                    # Main page (English)
│   ├── css/responsive.css            # Mobile/tablet support
│   ├── books/
│   │   ├── index.html
│   │   └── financial-inst-mgmt/
│   │       ├── index.html            # ENG/IND selection
│   │       ├── chapters-eng.html
│   │       ├── chapters-ind.html
│   │       └── Ringkasan_Chapter_*.html (14 files)
│   └── articles/
│       ├── index.html
│       ├── myers-1984/
│       │   ├── index.html
│       │   └── Ringkasan_Myers_1984_*.html (2 files)
│       └── mcinnes-1982/
│           ├── index.html
│           └── Ringkasan_McInnes_1982_*.html (2 files)
│
├── .gitignore
├── BLUEPRINT.md                      # This file
└── PROJECT_LOG.md                    # Session log
```

---

## 4. NAVIGATION FLOW

```
Main Page (EN)
├── 📚 Books
│   └── Financial Institutions Management
│       ├── 🇬🇧 English → 7 Chapters
│       └── 🇮🇩 Bahasa Indonesia → 7 Bab
│
└── 📄 Journal Articles
    ├── Myers (1984) - The Capital Structure Puzzle
    │   ├── 🇬🇧 English
    │   └── 🇮🇩 Bahasa Indonesia
    └── McInnes (1982) - Financial Control
        ├── 🇬🇧 English
        └── 🇮🇩 Bahasa Indonesia
```

---

## 5. RESPONSIVE DESIGN

| Device | Breakpoint | Behavior |
|--------|------------|----------|
| Desktop | >768px | Normal layout, max-width 600px |
| Tablet | 481-768px | Reduced padding, adapted fonts |
| Mobile | <480px | Minimal padding, full-width cards, horizontal scroll tables |

**File**: `docs/css/responsive.css`

---

## 6. FILE NAMING CONVENTIONS

### HTML Files
| Type | Pattern | Example |
|------|---------|---------|
| Book chapter (IND) | `Ringkasan_Chapter_[N]_IND.html` | `Ringkasan_Chapter_1_IND.html` |
| Book chapter (ENG) | `Ringkasan_Chapter_[N]_ENG.html` | `Ringkasan_Chapter_1_ENG.html` |
| Article (IND) | `Ringkasan_[LastName]_[Year]_IND.html` | `Ringkasan_Myers_1984_IND.html` |
| Article (ENG) | `Ringkasan_[LastName]_[Year]_ENG.html` | `Ringkasan_Myers_1984_ENG.html` |

### Index Files
| Level | File | Purpose |
|-------|------|---------|
| Root | `docs/index.html` | Main page |
| Category | `docs/books/index.html` | List all books |
| Book | `docs/books/{title}/index.html` | ENG/IND selection |
| Chapters | `docs/books/{title}/chapters-{lang}.html` | Chapter list |

---

## 7. HTML FORMAT TEMPLATE

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" href="../../css/responsive.css">
  <title>Chapter Summary - Title (English)</title>
  <style>
    /* Times New Roman 12pt, A4, justify */
  </style>
  <script>
    window.MathJax = {
      tex: { inlineMath: [['\\(','\\)']], displayMath: [['\\[','\\]']] }
    };
  </script>
  <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js" async></script>
</head>
<body>
  <div class="toolbar">
    <button onclick="window.print()">Print / Save as PDF</button>
  </div>
  <h1>Summary: Title</h1>
  <p class="meta">Author, Source, Year</p>
  <!-- Content -->
  <p class="note">Note: This is a self-study summary...</p>
</body>
</html>
```

---

## 8. GITHUB PAGES

- **URL**: https://heru2233.github.io/summary_academia/
- **Repository**: https://github.com/heru2233/summary_academia
- **Source**: /docs folder on main branch
- **Deploy**: Automatic on git push

### Security
- ✅ Only HTML summaries are public (no copyrighted PDFs)
- ✅ Tokens in .env (not committed)
- ✅ sources/ and templates/ in .gitignore

---

## 9. ADDING NEW CONTENT

### Steps:
1. Place PDF in `sources/{books|articles}/{new-title}/`
2. Create folder `docs/{books|articles}/{new-title}/`
3. Chat with AI using appropriate template from `templates/`
4. AI creates `Ringkasan_*_IND.html` and `Ringkasan_*_ENG.html`
5. Create `index.html` for ENG/IND selection
6. Update parent `index.html` to include new item
7. Push to GitHub

### Book Template
Use `templates/PROMPT_TEMPLATE_BOOK.md`
- Length: 5,000-8,000 words per language
- Style: Formal academic
- Structure: Follow book section order
- Include: All formulas, tables, examples

### Article Template
Use `templates/PROMPT_TEMPLATE_ARTICLE.md`
- Length: 2,000-4,000 words per language
- Style: Flowing, readable
- Structure: Follow argument flow
- Include: Essential formulas and key tables only

---

## 10. LEGACY (v1.0 - DEPRECATED)

The old system used:
- `@1/`, `@2/`, `@3/` folders (unclear naming)
- `send_to_telegram.py` (hardcoded paths)
- Telegraph publishing (format broken)

**Status**: Deprecated. All content migrated to new structure.

---

*Blueprint maintained by Buffy (Freebuff). Updated after each major session.*
