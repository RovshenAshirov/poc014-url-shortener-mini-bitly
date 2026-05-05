from fastapi import APIRouter
from prometheus_client import REGISTRY

router = APIRouter()


@router.get("/metrics/summary")
async def metrics_summary():
    metrics = {}
    for metric in REGISTRY.collect():
        for sample in metric.samples:
            metrics[sample.name] = sample.value

    return {
        "memory_mb": round(metrics.get("process_resident_memory_bytes", 0) / 1024 / 1024, 2),
        "cpu_seconds": round(metrics.get("process_cpu_seconds_total", 0), 2),
        "total_requests": metrics.get("http_requests_total", 0),
        "open_files": metrics.get("process_open_fds", 0),
    }