# BLUEPRINT PROYEK: Academic Summary Pipeline

> **Versi**: 2.0 | **Diperbarui**: 26 Agustus 2026

---

## 1. APA PROYEK INI?

Proyek ini mengubah **materi akademik (PDF)** menjadi **ringkasan HTML** yang rapi, lalu dipublikasikan agar bisa dibaca kapan saja di gadget.

### Jawaban atas pertanyaan umum

**Q: AI apa yang merangkumnya?**
A: **Anda** (manusia) yang memberikan instruksi ke AI (seperti Freebuff/ChatGPT/Claude). AI membaca PDF lalu membuat file HTML. **Tidak ada otomasi** dari PDF → HTML. Ini proses manual di chat AI.

**Q: Apakah summary AI dan send to Telegram itu 2 hal berbeda?**
A: **YA, terpisah total:**
```
TAHAP 1: AI Summary (Manual - di chat AI)
  Anda chat ke AI → AI baca PDF → AI buat file HTML
  
TAHAP 2: Publish (Semi-otomatis - di terminal)
  Python script baca file HTML → upload Telegraph → kirim link ke Telegram
```

---

## 2. ALUR KERJA SAAT INI (v1.0) — BANYAK MASALAH

```
PDF ──[MANUAL]──→ AI merangkum ──→ HTML disimpan
                                        │
                                   [MANUAL]
                                   Edit script.py
                                   (ubah FOLDER_HTML)
                                        │
                                        ▼
                              send_to_telegram.py
                                        │
                                   upload Telegraph
                                   (format rusak ❌)
                                        │
                                   kirim ke Telegram
                                   (link telegra.ph ❌)
```

### Masalah:
1. ❌ **Folder @1, @2, @3** → tidak jelas isinya apa
2. ❌ **Hardcoded path** di script → harus edit manual tiap pindah folder
3. ❌ **Telegraph merusak format** → tabel, rumus, heading hilang
4. ❌ **Tidak ada otomasi** dari PDF → HTML (semua manual di chat AI)
5. ❌ **Tidak ada standarisasi** penamaan file antar folder

---

## 3. ALUR KERJA YANG DISARANKAN (v2.0)

```
TAHAP 1: PERSIAPAN
  Siapkan PDF di folder sumber
        ↓
TAHAP 2: AI SUMMARY (di chat AI)
  Copy-paste prompt template yang sesuai (buku/artikel)
  AI baca PDF → AI buat 2 file HTML (IND + ENG)
  Simpan langsung di folder yang benar
        ↓
TAHAP 3: PUBLISH (otomatis via script)
  Jalankan: python publish.py --folder @2/buku --title "Judul Buku"
  Script otomatis:
    a) Baca semua HTML di folder
    b) Upload ke Telegraph
    c) Kirim menu ke Telegram
        ↓
TAHAP 4: BACA (di gadget)
  Buka Telegram → klik tombol → baca ringkasan
```

---

## 4. STRUKTUR FOLDER YANG DISARANKAN

```
D:\summary_msi\                          ← ROOT PROYEK
│
├── BLUEPRINT.md                         ← File ini
├── PROJECT_LOG.md                       ← Log status proyek
│
├── sources/                             ← 📁 PDF sumber (jangan diubah)
│   ├── buku-01-financial-inst-mgmt/     ← Folder per judul buku
│   │   ├── ch1.pdf ... ch7.pdf
│   │   └── README.md                    ← Info: judul, penulis, edisi
│   │
│   ├── artikel-01-myers-1984/
│   │   ├── paper.pdf
│   │   └── README.md
│   │
│   └── artikel-02-mcinnes-1982/
│       ├── paper.pdf
│       └── README.md
│
├── summaries/                           ← 📁 Output HTML ringkasan
│   ├── buku-01-financial-inst-mgmt/     ← 1 per sumber
│   │   ├── Ringkasan_Chapter_1_IND.html
│   │   ├── Ringkasan_Chapter_1_ENG.html
│   │   ├── ...
│   │   └── Ringkasan_Chapter_7_ENG.html
│   │
│   ├── artikel-01-myers-1984/
│   │   ├── Ringkasan_Myers_1984_IND.html
│   │   └── Ringkasan_Myers_1984_ENG.html
│   │
│   └── artikel-02-mcinnes-1982/
│       ├── Ringkasan_McInnes_1982_IND.html
│       └── Ringkasan_McInnes_1982_ENG.html
│
├── templates/                           ← 📁 Prompt template
│   ├── PROMPT_TEMPLATE_BOOK.md          ← Untuk chapter buku
│   ├── PROMPT_TEMPLATE_ARTICLE.md       ← Untuk artikel jurnal
│   └── Template.docx                    ← Template Word (opsional)
│
└── scripts/                             ← 📁 Script Python
    ├── publish.py                       ← Script utama (upload + kirim)
    ├── requirements.txt                 ← Dependensi Python
    └── config.py                        ← Token & konfigurasi
```

### Penamaan Folder
| Pola | Keterangan | Contoh |
|------|-----------|--------|
| `buku-NN-nama-pendek` | Buku, nomor urut + nama | `buku-01-financial-inst-mgmt` |
| `artikel-NN-nama-penulis-tahun` | Artikel jurnal | `artikel-01-myers-1984` |

### Penamaan File HTML
| Jenis | Pola | Contoh |
|-------|------|--------|
| Chapter buku (IND) | `Ringkasan_Chapter_[N]_IND.html` | `Ringkasan_Chapter_1_IND.html` |
| Chapter buku (ENG) | `Ringkasan_Chapter_[N]_ENG.html` | `Ringkasan_Chapter_1_ENG.html` |
| Artikel (IND) | `Ringkasan_[Nama]_[Tahun]_IND.html` | `Ringkasan_Myers_1984_IND.html` |
| Artikel (ENG) | `Ringkasan_[Nama]_[Tahun]_ENG.html` | `Ringkasan_Myers_1984_ENG.html` |

---

## 5. REKOMENDASI: GITHUB PAGES

**Kenapa GitHub Pages?**
- ✅ **GRATIS** selamanya
- ✅ HTML tampil **SEMPURNA** (tabel, rumus, styling semua jalan)
- ✅ Akses dari **gadget** via browser
- ✅ Punya **version history** (git)
- ✅ Bisa di-share ke orang lain

### Cara Kerja:
```
Push HTML ke GitHub repo
        ↓
GitHub Pages aktif (gratis)
        ↓
Dapat URL: https://username.github.io/summaries/
        ↓
Buka di browser gadget → format sempurna ✅
```

### Tampilan di Telegram:
```
📚 RINGKASAN BUKU
Financial Institutions Management

Klik untuk membaca:
📖 Ch 1 - https://username.github.io/summaries/buku-01/ch1-ind.html
📖 Ch 2 - https://username.github.io/summaries/buku-01/ch2-ind.html
...
```

---

## 6. REVISI SCRIPT: publish.py

Script baru harus:
1. **Parameterisasi** — tidak hardcode path
2. **Otomatis deteksi** — baca semua HTML di folder
3. **Pilihan publish** — Telegraph ATAU GitHub (atau keduanya)
4. **Lebih robust** — error handling lebih baik

### Design Script Baru:

```python
# publish.py — Versi baru (blueprint)

# Fitur:
# 1. Baca folder HTML dari argumen command line
# 2. Upload ke Telegraph (opsional)
# 3. Generate file index.html untuk GitHub Pages
# 4. Kirim menu ke Telegram

# Contoh penggunaan:
# python publish.py --source summaries/buku-01 --title "Financial Institutions Management" --mode github
# python publish.py --source summaries/buku-01 --title "Financial Institutions Management" --mode telegraph
```

---

## 7. PROMPT TEMPLATE — PERUBAHAN

### Untuk Chapter Buku:
Saat ini sudah bagus. Tidak perlu banyak perubahan. Cuma:
- Lokasi file di prompt harus sesuai struktur baru (`sources/` dan `summaries/`)

### Untuk Artikel Jurnal:
Sama, cuma update path di prompt.

---

## 8. CHECKLIST MIGRASI

Migrasi dari v1.0 → v2.0:

- [ ] Buat folder `sources/` dan pindahkan PDF
- [ ] Buat folder `summaries/` dan pindahkan HTML
- [ ] Buat folder `templates/` dan pindahkan prompt template
- [ ] Buat folder `scripts/` dan tulis script baru
- [ ] Update `PROJECT_LOG.md`
- [ ] Setup GitHub Pages
- [ ] Publish pertama kali
- [ ] Kirim link ke Telegram

---

## 9. NAMA PROYEK YANG DISARANKAN

| Sekarang | Disarankan | Alasan |
|----------|-----------|--------|
| `summary_msi` | `akademia-ringkas` | Lebih deskriptif, mudah diingat |
| `@1`, `@2`, `@3` | `buku-01-*`, `artikel-01-*` | Jelas isinya |
| `send_to_telegram.py` | `publish.py` | Lebih umum, bisa multi-target |
| `summary_tele/` | `scripts/` | Standar proyek Python |

---

*Blueprint ini dibuat oleh Buffy (Freebuff) — 26 Agustus 2026*
