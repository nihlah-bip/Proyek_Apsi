import sys
import os

# Tambahkan parent directory ke sys.path agar bisa import app.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db, Member, Latihan, Pembayaran, User

def delete_all_members():
    with app.app_context():
        print("Menghapus semua data Latihan...")
        num_latihan = db.session.query(Latihan).delete()
        print(f"  - {num_latihan} data latihan dihapus.")

        print("Menghapus semua data Pembayaran...")
        num_pembayaran = db.session.query(Pembayaran).delete()
        print(f"  - {num_pembayaran} data pembayaran dihapus.")

        print("Menghapus semua data Member...")
        num_members = db.session.query(Member).delete()
        print(f"  - {num_members} data member dihapus.")

        print("Menghapus akun User dengan role 'member'...")
        num_users = db.session.query(User).filter_by(role='member').delete()
        print(f"  - {num_users} akun user member dihapus.")

        db.session.commit()
        print("Selesai! Semua data member telah dihapus.")

if __name__ == "__main__":
    delete_all_members()
