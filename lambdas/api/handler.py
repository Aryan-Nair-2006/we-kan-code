from mangum import Mangum

from backend.app.main import app

# Wraps the same FastAPI app used for local development (`uvicorn backend.app.main:app`)
# so every route (/documents, /query, /flags, /reviews, /analytics, /health) is available
# once this Lambda is deployed behind API Gateway - no separate logic to keep in sync.
handler = Mangum(app)
