import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_upload_invalid_file_type():
    files = {'file': ('test.png', b'fake image data', 'image/png')}
    data = {
        'owner': 'Test',
        'category': 'Test',
        'access_level': 'public',
        'version': '1.0'
    }
    response = client.post("/documents/upload", files=files, data=data)
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()['detail']
