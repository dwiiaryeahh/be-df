# Docker Setup untuk DF-Backpack

## Prasyarat

- Docker >= 20.10
- Docker Compose >= 2.0
- PostgreSQL Server (eksternal di LattePanda/Web Server)

> ⚠️ **Backend memerlukan PostgreSQL** - SQLite tidak lagi didukung. Backend fully PostgreSQL.

## Struktur Docker

### Layanan (Services)

1. **app** - FastAPI Application
   - Port: 8888 (default)
   - Terhubung ke database eksternal

> **CATATAN**: Database PostgreSQL tidak dijalankan di Docker. Database harus dikonfigurasi secara terpisah di LattePanda/Web Server.

## Cara Menggunakan

### 1. Setup Database Eksternal

Pastikan PostgreSQL sudah terinstall dan berjalan di LattePanda/Web Server:

```bash
# Database credentials (sesuaikan dengan setup Anda)
DB_NAME: backpack_df
DB_USER: backpack_user
DB_PASSWORD: b4cKpaCk_2026!@
DB_HOST: [IP/Hostname LattePanda]
DB_PORT: 5432
```

### 2. Setup Environment Variable

Copy file `.env.example` ke `.env` dan konfigurasi DATABASE_URL:

```bash
cp .env.example .env
```

Edit `.env` dan sesuaikan DATABASE_URL sesuai konfigurasi database eksternal Anda:

```env
# Contoh untuk database di LattePanda dengan IP 192.168.1.100
DATABASE_URL=postgresql://backpack_user:b4cKpaCk_2026!@192.168.1.100:5432/backpack_df

APP_PORT=8888
```

### 3. Verifikasi Koneksi Database

```bash
# Test koneksi ke database dari host machine
psql -h [DATABASE_HOST] -U backpack_user -d backpack_df

# Atau gunakan Docker untuk test
docker-compose exec app python -c "from app.db.database import engine; print('DB Connected!' if engine else 'Failed')"
```

### 4. Build dan Jalankan dengan Docker Compose

```bash
# Build images
docker-compose build

# Jalankan services
docker-compose up -d
```

### 5. Verifikasi Services Berjalan

```bash
# Cek status services
docker-compose ps

# Lihat logs
docker-compose logs -f app
```

### 6. Test Health Check

```bash
# API Health Check
curl http://localhost:8888/health

# Expected response:
# {
#   "status": "ok",
#   "timestamp": "2026-02-23T10:30:45.123456",
#   "database": "healthy",
#   "service": "IMSI CATCHER BACKEND"
# }
```

## Command-Command Umum

### Build ulang tanpa cache
```bash
docker-compose build --no-cache
```

### Stop services
```bash
docker-compose down
```

### Jalankan dengan environment file tertentu
```bash
docker-compose --env-file .env up -d
```

### Enter container shell
```bash
docker-compose exec app bash
```

### View logs
```bash
# Semua services
docker-compose logs

# Follow logs (real-time)
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100
```

### Rebuild dan restart
```bash
docker-compose up -d --build
```

## Konfigurasi Environment

### Variabel-variabel yang dapat dikonfigurasi (di `.env`):

| Variable | Default | Deskripsi |
|----------|---------|-----------|
| `DATABASE_URL` | sqlite:///./app.db | URL koneksi database (PostgreSQL atau SQLite) |
| `APP_PORT` | 8888 | Port FastAPI App |

**Format DATABASE_URL (PostgreSQL):**

```
# Basic PostgreSQL
postgresql://username:password@host:port/database

# PostgreSQL dengan SSL
postgresql://username:password@host:port/database?sslmode=require

# Contoh untuk LattePanda dengan IP 192.168.1.100
postgresql://backpack_user:b4cKpaCk_2026!@192.168.1.100:5432/backpack_df
```

## Database Management di Eksternal Server

### Akses PostgreSQL dari host

```bash
psql -h [DATABASE_HOST] -U backpack_user -d backpack_df
```

### Backup Database

```bash
pg_dump -h [DATABASE_HOST] -U backpack_user -d backpack_df > backup.sql
```

### Restore Database

```bash
psql -h [DATABASE_HOST] -U backpack_user -d backpack_df < backup.sql
```

## Troubleshooting

### Database Connection Error

Pastikan:
1. PostgreSQL server di LattePanda sudah berjalan
2. Database `backpack_df` sudah dibuat
3. User `backpack_user` sudah ada dengan password yang benar
4. Firewall memungkinkan koneksi ke port 5432

Test koneksi:
```bash
psql -h [DATABASE_HOST] -U backpack_user -d backpack_df -c "SELECT 1;"
```

### Port Sudah Digunakan

Jika port 8888 sudah digunakan, ubah di `.env`:
```env
APP_PORT=8889
```

### Container Crash

Lihat logs untuk error:
```bash
docker-compose logs app
```

### Rebuild Diperlukan

Jika ada perubahan di requirements.txt:
```bash
docker-compose up -d --build
```

## Volumes & Data Persistence

- **./logs**: Directory logs aplikasi
- **./app/mode**: Directory mode config
- **./app/xml_file**: Directory XML files

Data disimpan di path-path lokal ini di host machine.

## Health Checks

App memiliki health check:
- **App**: Menggunakan endpoint `/health`

## Network

App dapat terhubung ke database eksternal melalui network host atau bridge docker.

## Catatan Penting

⚠️ **Database tidak termasuk dalam Docker** - Database harus dikelola secara terpisah di LattePanda/Web Server.

✅ Hanya backend FastAPI Application yang di-Docker.

✅ Logs dan config files di-mount dari host untuk memudahkan debugging.

✅ Backup database harus dilakukan secara manual atau dengan script sendiri.

