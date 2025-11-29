import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app


def run():
    client = app.test_client()

    endpoints = [
        '/',
        '/admin/pegawai',
        '/manager/members',
        '/admin/accounts/members',
        '/admin/members'
    ]

    for e in endpoints:
        resp = client.get(e, follow_redirects=False)
        loc = resp.headers.get('Location')
        print(f'GET {e} -> status={resp.status_code} location={loc}')


if __name__ == '__main__':
    run()
