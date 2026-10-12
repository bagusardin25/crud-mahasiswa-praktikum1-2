"""CRUD Mahasiswa — Flask + PostgreSQL.

Aplikasi kecil untuk praktikum Komputasi Awan. Jenkins membangunnya menjadi
Docker image, lalu menjalankannya bersama container PostgreSQL lewat
docker compose.
"""
import os
import re
import time
from datetime import datetime

import psycopg
from psycopg.rows import dict_row
from flask import (
    Flask, abort, flash, jsonify, redirect, render_template, request, url_for,
)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "ganti-secret-key-ini")

# Semua konfigurasi database diambil dari environment variable supaya
# image yang sama bisa dipakai di laptop, di Jenkins, maupun di cloud.
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "mahasiswa_db"),
    "user": os.getenv("DB_USER", "mahasiswa"),
    "password": os.getenv("DB_PASSWORD", "mahasiswa123"),
}

# Diisi nomor build Jenkins lewat docker compose, jadi terlihat di halaman
# build mana yang sedang berjalan.
APP_VERSION = os.getenv("APP_VERSION", "dev")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

SEED_DATA = [
    ("1202230001", "Andi Pratama", "Sistem Informasi", 2023, "andi@example.com"),
    ("1202230002", "Siti Rahmawati", "Sistem Informasi", 2023, "siti@example.com"),
    ("1301240015", "Budi Santoso", "Informatika", 2024, None),
]


def get_conn():
    return psycopg.connect(**DB_CONFIG, row_factory=dict_row, connect_timeout=5)


def init_db(retries=10, delay=3):
    """Buat tabel kalau belum ada, lalu isi data contoh bila tabel masih kosong.

    Dicoba berulang karena container PostgreSQL bisa butuh beberapa detik
    sampai siap menerima koneksi.
    """
    for attempt in range(1, retries + 1):
        try:
            with get_conn() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS mahasiswa (
                        id         SERIAL PRIMARY KEY,
                        nim        VARCHAR(20)  NOT NULL UNIQUE,
                        nama       VARCHAR(100) NOT NULL,
                        prodi      VARCHAR(100) NOT NULL,
                        angkatan   SMALLINT     NOT NULL,
                        email      VARCHAR(120),
                        created_at TIMESTAMP    NOT NULL DEFAULT NOW()
                    )
                    """
                )
                jumlah = conn.execute("SELECT COUNT(*) AS n FROM mahasiswa").fetchone()["n"]
                if jumlah == 0:
                    with conn.cursor() as cur:
                        cur.executemany(
                            "INSERT INTO mahasiswa (nim, nama, prodi, angkatan, email) "
                            "VALUES (%s, %s, %s, %s, %s)",
                            SEED_DATA,
                        )
            print("Database siap.", flush=True)
            return
        except psycopg.OperationalError as exc:
            print(f"[{attempt}/{retries}] Database belum siap: {exc}", flush=True)
            time.sleep(delay)
    raise RuntimeError("Tidak bisa terhubung ke database setelah beberapa percobaan.")


def validate(form):
    """Rapikan dan periksa input form. Mengembalikan (data, daftar_error)."""
    data = {
        "nim": form.get("nim", "").strip(),
        "nama": form.get("nama", "").strip(),
        "prodi": form.get("prodi", "").strip(),
        "angkatan": form.get("angkatan", "").strip(),
        "email": form.get("email", "").strip(),
    }
    errors = []

    if not (data["nim"].isdigit() and 5 <= len(data["nim"]) <= 20):
        errors.append("NIM wajib diisi, berupa 5–20 digit angka.")
    if not data["nama"]:
        errors.append("Nama wajib diisi.")
    elif len(data["nama"]) > 100:
        errors.append("Nama maksimal 100 karakter.")
    if not data["prodi"]:
        errors.append("Program studi wajib diisi.")
    elif len(data["prodi"]) > 100:
        errors.append("Program studi maksimal 100 karakter.")

    tahun_maks = datetime.now().year + 1
    try:
        angkatan = int(data["angkatan"])
        if not 1990 <= angkatan <= tahun_maks:
            raise ValueError
        data["angkatan"] = angkatan
    except ValueError:
        errors.append(f"Angkatan harus berupa tahun antara 1990 dan {tahun_maks}.")

    if data["email"] and (len(data["email"]) > 120 or not EMAIL_RE.match(data["email"])):
        errors.append("Format email tidak valid.")
    data["email"] = data["email"] or None

    return data, errors


@app.context_processor
def inject_version():
    return {"app_version": APP_VERSION}


# ---------------------------------------------------------------- READ
@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    with get_conn() as conn:
        if q:
            pola = f"%{q}%"
            rows = conn.execute(
                "SELECT * FROM mahasiswa WHERE nama ILIKE %s OR nim ILIKE %s ORDER BY nim",
                (pola, pola),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM mahasiswa ORDER BY nim").fetchall()
        total = conn.execute("SELECT COUNT(*) AS n FROM mahasiswa").fetchone()["n"]
    return render_template("index.html", mahasiswa=rows, q=q, total=total)


# -------------------------------------------------------------- CREATE
@app.route("/tambah", methods=["GET", "POST"])
def tambah():
    if request.method == "POST":
        data, errors = validate(request.form)
        if not errors:
            try:
                with get_conn() as conn:
                    conn.execute(
                        "INSERT INTO mahasiswa (nim, nama, prodi, angkatan, email) "
                        "VALUES (%s, %s, %s, %s, %s)",
                        (data["nim"], data["nama"], data["prodi"], data["angkatan"], data["email"]),
                    )
                flash(f"Mahasiswa {data['nama']} berhasil ditambahkan.", "success")
                return redirect(url_for("index"))
            except psycopg.errors.UniqueViolation:
                errors.append(f"NIM {data['nim']} sudah terdaftar.")
        for e in errors:
            flash(e, "error")
        return render_template(
            "form.html", mhs=request.form, judul="Tambah Mahasiswa",
            action=url_for("tambah"),
        ), 400

    return render_template(
        "form.html", mhs={}, judul="Tambah Mahasiswa", action=url_for("tambah"),
    )


# -------------------------------------------------------------- UPDATE
@app.route("/edit/<int:mhs_id>", methods=["GET", "POST"])
def edit(mhs_id):
    with get_conn() as conn:
        mhs = conn.execute("SELECT * FROM mahasiswa WHERE id = %s", (mhs_id,)).fetchone()
    if mhs is None:
        abort(404)

    if request.method == "POST":
        data, errors = validate(request.form)
        if not errors:
            try:
                with get_conn() as conn:
                    conn.execute(
                        "UPDATE mahasiswa SET nim = %s, nama = %s, prodi = %s, "
                        "angkatan = %s, email = %s WHERE id = %s",
                        (data["nim"], data["nama"], data["prodi"], data["angkatan"],
                         data["email"], mhs_id),
                    )
                flash(f"Data {data['nama']} berhasil diperbarui.", "success")
                return redirect(url_for("index"))
            except psycopg.errors.UniqueViolation:
                errors.append(f"NIM {data['nim']} sudah dipakai mahasiswa lain.")
        for e in errors:
            flash(e, "error")
        return render_template(
            "form.html", mhs=request.form, judul="Edit Mahasiswa",
            action=url_for("edit", mhs_id=mhs_id),
        ), 400

    return render_template(
        "form.html", mhs=mhs, judul="Edit Mahasiswa",
        action=url_for("edit", mhs_id=mhs_id),
    )


# -------------------------------------------------------------- DELETE
@app.route("/hapus/<int:mhs_id>", methods=["POST"])
def hapus(mhs_id):
    with get_conn() as conn:
        row = conn.execute(
            "DELETE FROM mahasiswa WHERE id = %s RETURNING nama", (mhs_id,)
        ).fetchone()
    if row is None:
        flash("Data tidak ditemukan.", "error")
    else:
        flash(f"Data {row['nama']} berhasil dihapus.", "success")
    return redirect(url_for("index"))


# ------------------------------------------------------- API & HEALTH
@app.route("/api/mahasiswa")
def api_mahasiswa():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, nim, nama, prodi, angkatan, email FROM mahasiswa ORDER BY nim"
        ).fetchall()
    return jsonify(rows)


@app.route("/health")
def health():
    """Dipakai stage Verifikasi di Jenkins untuk memastikan app + database hidup."""
    try:
        with get_conn() as conn:
            jumlah = conn.execute("SELECT COUNT(*) AS n FROM mahasiswa").fetchone()["n"]
        return jsonify(
            status="ok", database="connected", version=APP_VERSION,
            jumlah_mahasiswa=jumlah,
        )
    except Exception as exc:  # noqa: BLE001 — health check harus selalu menjawab
        return jsonify(status="error", database="disconnected", detail=str(exc)), 503


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
