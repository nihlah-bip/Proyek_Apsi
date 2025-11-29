import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app


def run():
    client = app.test_client()

    # Ensure test accounts exist by calling emergency route
    client.get('/buat_akun_darurat')

    # Login as manager
    login_data = {'username': 'manager', 'password': 'admin123'}
    resp = client.post('/login?role=manager', data=login_data, follow_redirects=True)
    print('Login manager status:', resp.status_code)

    # Access admin/staff
    resp2 = client.get('/admin/staff')
    print('/admin/staff status:', resp2.status_code)
    body = resp2.get_data(as_text=True)
    snippet = body[:1000]
    print('Response snippet (first 1000 chars):\n', snippet)

if __name__ == '__main__':
    run()
