"""MCP Hub main application."""
import argparse
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mcp_hub.models.database import Database
from mcp_hub.services.registry import ServiceRegistry
from mcp_hub.api import routes


def create_app(db_url: str = "sqlite:///./mcp_hub.db") -> FastAPI:
    """Create FastAPI application."""
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Application lifespan handler."""
        # Startup
        db = Database(db_url)
        routes.registry = ServiceRegistry(db)
        yield
        # Shutdown
        pass
    
    app = FastAPI(
        title="MCP Hub",
        description="MCP Service Registry and Discovery Platform",
        version="0.1.0",
        lifespan=lifespan,
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routes
    app.include_router(routes.router)
    
    @app.get("/")
    async def root():
        return {
            "name": "MCP Hub",
            "version": "0.1.0",
            "docs": "/docs",
        }
    
    @app.get("/health")
    async def health():
        return {"status": "healthy"}
    
    return app


def main():
    import uvicorn
    
    parser = argparse.ArgumentParser(description="MCP Hub")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    parser.add_argument("--db", default="sqlite:///./mcp_hub.db", help="Database URL")
    
    args = parser.parse_args()
    
    app = create_app(db_url=args.db)
    
    print(f"🚀 MCP Hub starting on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
