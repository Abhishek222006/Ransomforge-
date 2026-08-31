from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict[str, object]:
    websocket_manager = request.app.state.websocket_manager
    file_monitor = request.app.state.file_monitor

    return {
        "status": "ok",
        "service": "RansomForge",
        "active_connections": websocket_manager.connection_count,
        "monitor_path": str(file_monitor.watch_path),
    }
