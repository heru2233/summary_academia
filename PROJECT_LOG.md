# PROJECT LOG - Ringkasan Akademik ke HTML → Telegraph → Telegram

> **Terakhir diperbarui**: 26 Agustus 2026  
> **Sesi terakhir**: Buffy (Freebuff) - Sesi pertama membuat log

---

## 🎯 RINGKASAN PROYEK

Proyek ini mengubah materi akademik (PDF buku & artikel jurnal) menjadi **ringkasan HTML** dalam dua bahasa (Indonesia & Inggris), lalu dipublikasikan ke **Telegraph** dan dikirim ke **Telegram** sebagai menu navigasi.

### Alur Kerja (Pipeline)
```
PDF → pdftotext → Teks → AI Merangkum → HTML (IND + ENG) → Telegraph → Telegram
```

---

## 📁 STRUKTUR FOLDER

```
D:\summary_msi\
├── summary_tele/                    # Script & config
│   ├── send_to_telegram.py         # Script utama: upload HTML ke Telegraph + kirim Telegram
│   ├── Untitled-1.txt              # Backup config (token Telegram)
│   └── venv/                       # Virtual environment Python
│
├── Template/
│   └── Talent management.docx      # Template Word (belum dipakai aktif)
│
├── @1/                              # Artikel jurnal ringkas
│   ├── What_theory_is_not.pdf      # PDF asli
│   ├── Ringkasan_What_Theory_is_Not.docx
│   └── Ringkasan_What_Theory_is_Not_v2.docx
│
├── @2/                              # Buku teks: Financial Institutions Management
│   └── Financial_Institutions_Management,_A_Risk_Management_Approach,_11e/
│       ├── ch1.pdf s/d ch7.pdf     # PDF per chapter
│       └── summary_html/           # OUTPUT ringkasan HTML
│           ├── PROMPT_TEMPLATE.md  # Template prompt untuk chapter buku
│           ├── Ringkasan_Chapter_[1-7]_IND.html  ✅ SELESAI
│           └── Ringkasan_Chapter_[1-7]_ENG.html  ✅ SELESAI
│
├── @3/                              # Artikel jurnal
│   ├── 1_Myers-FinanceTheoryFinancial-1984.pdf
│   ├── 1_McInnes-TheoryModelsImplementation-1982.pdf
│   ├── PROMPT_TEMPLATE_ARTICLE.md  # Template prompt untuk artikel jurnal
│   ├── Ringkasan_Myers_1984_IND.html    ✅ SELESAI
│   ├── Ringkasan_Myers_1984_ENG.html    ✅ SELESAI
│   ├── Ringkasan_McInnes_1982_IND.html  ✅ SELESAI
│   └── Ringkasan_McInnes_1982_ENG.html  ✅ SELESAI
│
└── @4/ (dst.)                       # Folder masa depan untuk materi baru
```

---

## ✅ STATUS PENGERJAAN

### @1 - Artikel "What Theory is Not"
| File | Status |
|------|--------|
| Ringkasan_What_Theory_is_Not.docx | ✅ Ada (dalam .docx, belum HTML) |
| Ringkasan_What_Theory_is_Not_v2.docx | ✅ Ada (v2, belum HTML) |
| **Catatan** | Perlu dikonversi ke HTML atau buat ulang dalam format HTML |

### @2 - Financial Institutions Management (Saunders & Cornett, Ed. 11)
| Chapter | File PDF | IND HTML | ENG HTML |
|---------|----------|----------|----------|
| Ch 1 - Why Are Financial Institutions Special? | ✅ ch1.pdf | ✅ | ✅ |
| Ch 2 | ✅ ch2.pdf | ✅ | ✅ |
| Ch 3 | ✅ ch3.pdf | ✅ | ✅ |
| Ch 4 | ✅ ch4.pdf | ✅ | ✅ |
| Ch 5 | ✅ ch5.pdf | ✅ | ✅ |
| Ch 6 | ✅ ch6.pdf | ✅ | ✅ |
| Ch 7 | ✅ ch7.pdf | ✅ | ✅ |
| **Total 14 file HTML** | | **7 IND** | **7 ENG** |

### @3 - Artikel Jurnal
| Artikel | File PDF | IND HTML | ENG HTML |
|---------|----------|----------|----------|
| Myers (1984) - Finance Theory and Financial Strategy | ✅ | ✅ | ✅ |
| McInnes & Carleton (1982) - Theory, Models and Implementation | ✅ | ✅ | ✅ |
| **Total 4 file HTML** | | **2 IND** | **2 ENG** |

### Script Publish (summary_tele)
| Komponen | Status |
|----------|--------|
| send_to_telegram.py | ✅ Aktif, sudah diuji |
| Telegraph upload | ✅ Berfungsi dengan retry & flood control |
| Telegram menu | ✅ Kirim inline keyboard per chapter |

---

## ⚙️ KONFIGURASI SCRIPT

### Telegram
- **Bot Token**: `8914264852:AAEKoG6dEcBYISvbk4Y5uGwY2_U-M4OJqmw`
- **Chat ID**: `8960371977`

### Script: `send_to_telegram.py`
- **Library**: `requests`, `beautifulsoup4`, `telegraph`
- **Fitur**:
  - Membaca semua file `.html` dari folder yang dikonfigurasi
  - Sanitasi HTML agar sesuai whitelist Telegraph
  - Upload ke Telegraph dengan retry (handle Flood Control)
  - Kirim menu inline keyboard ke Telegram (batch 50 chapter per pesan)
  - Jeda 2 detik antar request untuk hindari rate limit
- **Cara pakai**: 
  1. Edit variabel `FOLDER_HTML` dan `book_title` di script
  2. Jalankan: `python send_to_telegram.py`

---

## 📝 ATURAN & KONVENSI PROYEK

### ATURAN UTAMA

1. **Dua template berbeda** tergantung jenis materi:
   - **Chapter Buku** → pakai `@2/.../summary_html/PROMPT_TEMPLATE.md`
   - **Artikel Jurnal** → pakai `@3/PROMPT_TEMPLATE_ARTICLE.md`

2. **Selalu 2 versi bahasa**: Setiap ringkasan WAJIB punya versi IND dan ENG sebagai file HTML terpisah.

3. **Penamaan file**:
   - Chapter buku: `Ringkasan_Chapter_[N]_[IND/ENG].html`
   - Artikel jurnal: `Ringkasan_[NamaSingkat]_[Tahun]_[IND/ENG].html`

4. **Proses PDF extraction**: Gunakan `pdftotext -layout [file].pdf [output].txt`

5. **Hapus file .txt sementara** setelah selesai membuat HTML

### PERBEDAAN KRITIS: Chapter Buku vs Artikel Jurnal

| Aspek | Chapter Buku | Artikel Jurnal |
|-------|-------------|----------------|
| **Panjang** | 5.000-8.000 kata/bahasa | 2.000-4.000 kata/bahasa |
| **Gaya bahasa** | Formal akademis kaku | Mengalir, mudah dibaca |
| **Struktur** | Ikuti urutan section buku | Ikuti alur argumentasi artikel |
| **Detail** | Sangat detail, semua bagian | Fokus ide utama & kontribusi |
| **Rumus** | Semua rumus dipertahankan | Hanya rumus esensial |
| **Tabel** | Semua tabel dipertahankan | Tabel penting saja |
| **Contoh** | Semua contoh disertakan | Contoh representatif |
| **Heading** | h2 = section, h3 = sub, h4 = contoh | h2 = bagian argumen |

### FORMAT HTML WAIB (kedua template)

```html
<!-- Head essentials -->
<meta charset="UTF-8">
<style>/* Times New Roman 12pt, A4, justify */</style>
<script>window.MathJax = { tex: { inlineMath: [['\\(','\\)']], displayMath: [['\\[','\\]']] } };</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js" async></script>

<!-- Body structure -->
<div class="toolbar"><button onclick="window.print()">Cetak / Simpan sebagai PDF</button></div>
<h1>Ringkasan: [Judul]</h1>
<p class="meta">Penulis, Sumber, Tahun</p>
<!-- Isi ringkasan -->
<p class="note">Catatan: Dokumen ini adalah ringkasan belajar mandiri...</p>
```

### ATURAN PENULISAN

1. **Istilah asing**: Dimiringkan `<i>...</i>` saat pertama kali muncul
2. **Rumus**: MathJax format `\\[ ... \\]` display, `\\( ... \\)` inline
3. **Tabel**: Format `<table>` dengan `<th>` background `#eee`
4. **Equation class**: Gunakan `<div class="eq">` untuk display equation
5. **Em-dash/en-dash**: JANGAN gunakan karakter `—` atau `–`
6. **Referensi**: Sertakan sumber di bagian atas dan catatan di bawah

### ATURAN PUBLISH

1. **Edit `FOLDER_HTML`** di `send_to_telegram.py` sebelum menjalankan
2. **Edit `book_title`** sesuai judul buku/artikel
3. **Jalankan script** dari folder `summary_tele/` dengan virtual environment aktif
4. **Telegram limit**: Maksimal 50 tombol inline per pesan (otomatis di-batch)
5. **Telegraph limit**: Script otomatis handle flood control dengan retry

---

## 🚀 CATATAN UNTUK SESI MENDATANG

### Yang Sudah Selesai
- [x] Ringkasan Chapter 1-7 buku Financial Institutions Management (IND+ENG)
- [x] Ringkasan Artikel Myers 1984 & McInnes 1982 (IND+ENG)
- [x] Script publish ke Telegraph + Telegram

### Yang Belum / Potensi Lanjutan
- [ ] Konversi ringkasan @1 (What Theory is Not) dari .docx ke HTML
- [ ] Publish @3 (Myers & McInnes) ke Telegraph + Telegram (jika belum)
- [ ] Publish @1 ke Telegraph + Telegram
- [ ] Tambah materi baru ke folder @4, @5, dst.
- [ ] Buat script otomatis pipeline: PDF → HTML (mungkin pakai AI API)
- [ ] Backup / arsipkan Telegraph URLs yang sudah di-publish

### Prompt untuk Melanjutkan Sesi
Ketika memulai sesi baru, gunakan prompt ini:
```
Baca file PROJECT_LOG.md di root proyek. Saya ingin melanjutkan proyek ringkasan akademik.
[SPEKSIKASI YANG INGIN DILANJUTKAN]
```

---

## 🔧 TROUBLESHOOTING

| Masalah | Solusi |
|---------|--------|
| `pdftotext` tidak ditemukan | Install: `choco install poppler` atau download dari https://github.com/oschwartz10612/poppler-windows |
| Telegraph Flood Control | Script otomatis retry, tunggu sesuai pesan error |
| HTML tidak tampil rumus | Pastikan MathJax CDN bisa diakses (butuh internet) |
| Telegram tidak terkirim | Cek token & chat ID di `send_to_telegram.py` |
| Folder salah | Edit variabel `FOLDER_HTML` di script sesuai path folder target |
| Virtual environment error | Aktifkan: `summary_tele/venv/Scripts/activate` |

---

## 📚 REFERENSI CEPAT

| File | Fungsi |
|------|--------|
| `@2/.../summary_html/PROMPT_TEMPLATE.md` | Template prompt untuk merangkum chapter buku |
| `@3/PROMPT_TEMPLATE_ARTICLE.md` | Template prompt untuk merangkum artikel jurnal |
| `summary_tele/send_to_telegram.py` | Script publish HTML → Telegraph → Telegram |
| `Template/Talent management.docx` | Template Word (belum aktif dipakai) |

---

*Log ini dibuat oleh Buffy (Freebuff) pada sesi 26 Agustus 2026. Perbarui bagian status setiap kali ada pengerjaan baru.*
