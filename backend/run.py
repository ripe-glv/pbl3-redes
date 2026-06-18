import os

import uvicorn

from app.config import get_settings


if __name__ == "__main__":
    settings = get_settings()
    app_module = os.getenv("APP_MODULE", "app.main:app")
    uvicorn.run(app_module, host=settings.host, port=settings.port, reload=False)
