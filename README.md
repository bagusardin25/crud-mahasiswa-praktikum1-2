# CRUD Mahasiswa — Flask + PostgreSQL + Docker + Jenkins

Aplikasi CRUD data mahasiswa sederhana untuk Praktikum Komputasi Awan. Setiap
push ke GitHub memicu Jenkins untuk membangun Docker image, mendorongnya ke
Docker Hub, lalu menjalankan aplikasi bersama database PostgreSQL.

```
push ke GitHub ──webhook (ngrok)──▶ Jenkins
   1. Checkout            ambil kode dari GitHub
   2. Build Docker Image  docker build
   3. Push ke Docker Hub  docker push (tag nomor build + latest)
   4. Deploy              docker compose up → container app + container PostgreSQL
   5. Verifikasi          GET /health → memastikan app terhubung ke database
```

## Struktur

```
crud-mahasiswa/
├── app.py               # Flask: CRUD, /api/mahasiswa, /health
├── templates/           # Halaman daftar & form
├── requirements.txt
├── Dockerfile
├── docker-compose.yml   # service app + db (PostgreSQL 16)
└── Jenkinsfile          # pipeline untuk Jenkins di Windows
```

| Fitur | URL |
|---|---|
| Daftar + cari mahasiswa | `GET /` |
| Tambah | `GET/POST /tambah` |
| Edit | `GET/POST /edit/<id>` |
| Hapus | `POST /hapus/<id>` |
| Data JSON | `GET /api/mahasiswa` |
| Health check (app + database) | `GET /health` |

Tabel `mahasiswa` dibuat otomatis saat aplikasi pertama kali jalan, lengkap
dengan 3 data contoh.

## 1. Coba jalankan di laptop dulu (tanpa Jenkins)

Pastikan Docker Desktop sudah Running, lalu di folder project:

```bash
docker compose up -d --build
```

Buka http://localhost:5000. Untuk mematikan: `docker compose down`
(tambahkan `-v` kalau ingin menghapus isi database juga).

## 2. Push ke GitHub

```bash
git init
git add .
git commit -m "CRUD mahasiswa + pipeline Jenkins"
git branch -M main
git remote add origin https://github.com/USERNAME/crud-mahasiswa.git
git push -u origin main
```

## 3. Siapkan credential Docker Hub di Jenkins

1. Docker Hub → Account settings → Personal access tokens → **Generate new token**
   dengan permission **Read, Write, Delete**.
2. Jenkins → Manage Jenkins → Credentials → (global) → **Add Credentials**
   - Kind: **Username with password**
   - Username: **username Docker Hub** (bukan email)
   - Password: token dari langkah 1
   - ID: `dockerhub-credentials`

Nama image di Docker Hub otomatis memakai username dari credential ini, jadi
tidak ada yang perlu diubah di Jenkinsfile.

## 4. Buat Pipeline job

1. New Item → nama **tanpa spasi**, misalnya `crud-mahasiswa` → **Pipeline** → OK
2. Build Triggers: centang **GitHub hook trigger for GITScm polling**
3. Pipeline → Definition: **Pipeline script from SCM**
   - SCM: Git
   - Repository URL: `https://github.com/USERNAME/crud-mahasiswa.git`
   - Branch Specifier: **`*/main`** (default Jenkins `*/master`, ganti!)
   - Script Path: `Jenkinsfile`
4. Save → **Build Now**

Untuk build otomatis saat push, pasang webhook di GitHub:
`https://<url-ngrok>/github-webhook/` (Content type: `application/json`).

## 5. Bukti untuk laporan

- Stage View Jenkins dengan kelima stage hijau
- Console Output bagian `docker push` dan respons `/health`
- Halaman Tags repo `crud-mahasiswa` di Docker Hub
- Halaman aplikasi di http://localhost:5000; badge **Build #N** di pojok kanan
  atas menunjukkan nomor build Jenkins yang sedang berjalan
- Tambah/edit data, lalu jalankan build lagi: datanya tetap ada karena
  tersimpan di volume database

## Troubleshooting

| Masalah | Solusi |
|---|---|
| `docker` tidak dikenali / error named pipe | Jenkins service harus jalan dengan akun Windows yang sama dengan Docker Desktop (Services → Jenkins → Log On) |
| Push gagal `unauthorized` / `denied` | Cek username credential (harus username, bukan email) dan permission token Read, Write, Delete |
| Port 5000 sudah dipakai | Ganti `APP_PORT` di Jenkinsfile, misalnya `'5050'` |
| Stage Verifikasi gagal | Lihat log container di bagian akhir Console Output; biasanya database belum siap atau password berubah |
| Password DB diganti tapi app gagal konek | Volume lama masih memakai password lama: `docker compose down -v` lalu build ulang |

### Jenkins di Linux / container

Ganti setiap `bat '...'` menjadi `sh '...'` dan `%VAR%` menjadi `$VAR`, misalnya
`sh 'docker build -t $APP_NAME:$IMAGE_TAG .'`. Untuk login gunakan
`sh 'echo $DH_TOKEN | docker login -u $DH_USER --password-stdin'`.
Kalau Jenkins sendiri berjalan di dalam container, `localhost` di stage
Verifikasi merujuk ke container Jenkins, bukan ke host.
