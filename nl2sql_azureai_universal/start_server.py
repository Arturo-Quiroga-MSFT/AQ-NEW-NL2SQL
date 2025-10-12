"""start_server.py - aiohttp Web Server for Teams NL2SQL Bot
===========================================================

Adds a lightweight /healthz endpoint (GET) for container platform health checks
separate from the Bot Framework /api/messages POST endpoint. This avoids false
health check failures due to BF authentication or payload requirements.

If ENV IMAGE_TAG is set (in Dockerfile) it's surfaced in /healthz for quick
revision identification.
"""

from os import environ
from datetime import datetime
from microsoft_agents.hosting.core import AgentApplication, AgentAuthConfiguration
from microsoft_agents.hosting.aiohttp import (
    start_agent_process,
    jwt_authorization_middleware,
    CloudAdapter,
)
from aiohttp.web import Request, Response, Application, run_app
from aiohttp import web

# Import our Teams NL2SQL agent
from teams_nl2sql_agent import AGENT_APP, CONNECTION_MANAGER


def start_server(
    agent_application: AgentApplication, 
    auth_configuration: AgentAuthConfiguration
):
    """
    Start the aiohttp web server with the Teams bot endpoint.
    
    Args:
        agent_application: The configured AgentApplication instance
        auth_configuration: Authentication configuration from MsalConnectionManager
    """
    
    async def entry_point(req: Request) -> Response:
        """
        Entry point for /api/messages endpoint.
        Routes incoming Bot Framework activities to the agent application.
        """
        agent: AgentApplication = req.app["agent_app"]
        adapter: CloudAdapter = req.app["adapter"]
        return await start_agent_process(
            req,
            agent,
            adapter,
        )

    # Create aiohttp application with JWT authorization middleware.
    # We add a preceding middleware to bypass auth for /healthz so external health checks don't get 401.

    @web.middleware  # pragma: no cover - simple routing bypass
    async def healthz_bypass_middleware(request: Request, handler):
        if request.path == "/healthz":
            return web.json_response(
                {
                    "status": "ok",
                    "service": "nl2sql-teams-bot",
                    "time_utc": datetime.utcnow().isoformat() + "Z",
                    "image_tag": environ.get("IMAGE_TAG", "unknown"),
                }
            )
        return await handler(request)

    APP = Application(middlewares=[healthz_bypass_middleware, jwt_authorization_middleware])
    
    # Register the /api/messages endpoint (Bot Framework)
    APP.router.add_post("/api/messages", entry_point)

    # We intentionally DO NOT register /healthz as a regular route (middleware handles it pre-auth)
    
    # Store configuration in app context
    APP["agent_configuration"] = auth_configuration
    APP["agent_app"] = agent_application
    APP["adapter"] = agent_application.adapter

    # Get port from environment or default to 3978 (standard bot port)
    # Azure App Service uses PORT environment variable
    port = int(environ.get("PORT", 3978))
    # Use 0.0.0.0 for Azure, localhost for local development
    host = environ.get("HOST", "0.0.0.0" if environ.get("WEBSITE_SITE_NAME") else "localhost")

    print(f"\n{'='*60}")
    print(f"🤖 NL2SQL Teams Bot Server Starting...")
    print(f"{'='*60}")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Endpoint: http://{host}:{port}/api/messages")
    print(f"Health:   http://{host}:{port}/healthz")
    if environ.get("IMAGE_TAG"):
        print(f"Image Tag: {environ.get('IMAGE_TAG')}")
    print(f"{'='*60}\n")

    try:
        run_app(APP, host=host, port=port)
    except Exception as error:
        print(f"[ERROR] Failed to start server: {error}")
        raise error


if __name__ == "__main__":
    # Enable logging for debugging
    import logging
    ms_agents_logger = logging.getLogger("microsoft_agents")
    ms_agents_logger.addHandler(logging.StreamHandler())
    ms_agents_logger.setLevel(logging.INFO)
    
    print("Starting NL2SQL Teams Bot...")
    
    # Start the server with our agent application
    start_server(
        agent_application=AGENT_APP,
        auth_configuration=CONNECTION_MANAGER.get_default_connection_configuration(),
    )
