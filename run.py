import uvicorn
import os
import sys

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    
    print("=" * 65)
    print("  Bengaluru Local Delivery Route Planner - Startup")
    print(f"  Web Interface:    http://{host}:{port}")
    print(f"  Swagger API Docs: http://{host}:{port}/docs")
    print("=" * 65)
    
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
