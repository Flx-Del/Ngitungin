# Ngitungin

Aplikasi pembukuan dan kalkulator HPP untuk UMKM. UI dan pesan validasi menggunakan Bahasa Indonesia.

## Status pengerjaan

- Tahap 1: analisis kebutuhan dan arsitektur — [`docs/01-analisis-arsitektur.md`](docs/01-analisis-arsitektur.md)
- Tahap 2: rancangan database dan ERD — [`docs/02-skema-database.md`](docs/02-skema-database.md)
- Tahap 3–9: implementasi MVP dasar tersedia di `backend/` dan `frontend/`.
- Tahap 10: tujuh pemeriksaan unit perhitungan/satuan lulus; build aplikasi menunggu dependensi frontend/backend dipasang.

## Fitur yang tersedia

- Daftar dan masuk akun dengan hash kata sandi; semua endpoint usaha memeriksa kepemilikan data.
- Produk, harga jual, HPP, stok awal, status aktif, penyesuaian stok, dan jejak pergerakan stok.
- Penjualan dengan banyak item, snapshot harga/HPP, pemeriksaan stok, pengurangan stok atomik, pengeditan dan pembatalan dengan penyesuaian stok.
- Pemasukan lain serta pencatatan, pengeditan, dan pembatalan pengeluaran.
- Data bahan baku dan kalkulasi HPP dari harga beli, pemakaian bahan, upah, overhead, serta hasil produksi per batch.
- Rekomendasi harga berdasarkan margin, simulasi keuntungan dari HPP produk yang tersimpan, dashboard periode, laporan laba rugi dan HPP produk, serta ekspor transaksi/pengeluaran/HPP ke CSV.
- Dashboard web responsif, daftar produk, formulir penjualan/pengeluaran, kalkulator, dan laporan.

Tujuh tes unit untuk konversi satuan, contoh HPP, harga berdasarkan margin, dan simulasi laba lulus. `npm install` belum berhasil pada lingkungan ini karena akses ke `registry.npmjs.org` ditolak (`EACCES`); paket backend juga belum tersedia untuk uji API.

## Menjalankan secara lokal

Prasyarat: Python 3.12+, Node.js 20+, dan npm. Docker tidak diperlukan untuk mode lokal; SQLite dipakai sebagai database pengembangan. PostgreSQL disarankan untuk penggunaan bersama/produksi.

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Ganti `APP_SECRET_KEY` pada `backend/.env` dengan rahasia acak minimal 32 karakter. Salah satu cara membuatnya:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Lalu jalankan API:

```powershell
uvicorn app.main:app --reload
```

API berjalan di `http://localhost:8000`; dokumentasi interaktif tersedia di `/docs`. Database SQLite dibuat sebagai `backend/ngitungin.db` saat aplikasi mulai.

### Frontend

Buka terminal kedua:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Buka alamat Vite yang ditampilkan, biasanya `http://localhost:5173`.

## PostgreSQL

`backend/schema.sql` mendeskripsikan tabel inti lengkap untuk PostgreSQL. Untuk menjalankannya pada database kosong, pasang PostgreSQL lalu jalankan:

```powershell
psql "$env:DATABASE_URL" -f backend/schema.sql
```

Backend ORM saat ini dapat diarahkan ke URL PostgreSQL melalui `DATABASE_URL`. Migrasi Alembic dan pemetaan semua tabel skema penuh masih perlu dirapikan sebelum peningkatan skema produksi; jangan menerapkan perubahan skema langsung pada data penting.

## Batas implementasi saat ini

- Akun MVP otomatis terhubung ke usaha pertama yang dibuat. Alur multi-usaha/cabang belum ada.
- Penjualan dan pengeluaran dapat diedit atau dibatalkan. Pembelian stok dan ekspor Excel/PDF belum tersedia.
- Kategori pengeluaran awal dibuat otomatis. Pengelolaan kategori melalui halaman pengaturan belum tersedia.
- CSV tersedia untuk transaksi, pengeluaran, dan laporan HPP. Laporan dashboard/laba rugi membaca catatan yang tersimpan.
- HPP yang disimpan pada produk menjadi snapshot yang digunakan penjualan dan simulasi. Perubahan material memerlukan penyimpanan ulang kalkulasi HPP.
- Penyimpanan token berada di `sessionStorage`, sehingga sesi berakhir saat tab/browser ditutup. Untuk deployment, gunakan HTTPS, kebijakan token yang sesuai, secret kuat, database PostgreSQL, backup, dan migrasi terkelola.
