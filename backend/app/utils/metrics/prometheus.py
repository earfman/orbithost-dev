"""
Prometheus metrics utilities for monitoring and observability.
"""
import time
from typing import Callable, Dict, List, Optional, Union
from functools import wraps

from prometheus_client import Counter, Gauge, Histogram, Summary
from prometheus_client import generate_latest, REGISTRY
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Define default metrics
REQUEST_COUNT = Counter(
    'http_requests_total', 
    'Total HTTP Requests Count', 
    ['method', 'endpoint', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds', 
    'HTTP Request Latency', 
    ['method', 'endpoint']
)

REQUEST_IN_PROGRESS = Gauge(
    'http_requests_in_progress',
    'HTTP Requests currently in progress',
    ['method', 'endpoint']
)

DEPENDENCY_LATENCY = Histogram(
    'dependency_request_duration_seconds',
    'External Dependency Request Latency',
    ['dependency_name', 'operation']
)

ERROR_COUNT = Counter(
    'error_count_total',
    'Total Error Count',
    ['error_type', 'error_location']
)

class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware for collecting Prometheus metrics for HTTP requests.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        method = request.method
        path = request.url.path
        
        # Skip metrics endpoint to avoid infinite recursion
        if path == "/metrics":
            return await call_next(request)
        
        REQUEST_IN_PROGRESS.labels(method=method, endpoint=path).inc()
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            status_code = response.status_code
            
            # Record request metrics
            REQUEST_COUNT.labels(method=method, endpoint=path, status_code=status_code).inc()
            REQUEST_LATENCY.labels(method=method, endpoint=path).observe(time.time() - start_time)
            
            return response
        except Exception as e:
            # Record error metrics
            ERROR_COUNT.labels(error_type=type(e).__name__, error_location=f"{method}:{path}").inc()
            raise
        finally:
            REQUEST_IN_PROGRESS.labels(method=method, endpoint=path).dec()

def track_dependency_call(dependency_name: str, operation: str):
    """
    Decorator for tracking external dependency calls.
    
    Args:
        dependency_name: Name of the external dependency
        operation: Operation being performed
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                # Record error metrics
                ERROR_COUNT.labels(
                    error_type=type(e).__name__, 
                    error_location=f"{dependency_name}:{operation}"
                ).inc()
                raise
            finally:
                # Record dependency latency
                DEPENDENCY_LATENCY.labels(
                    dependency_name=dependency_name,
                    operation=operation
                ).observe(time.time() - start_time)
        
        return wrapper
    
    return decorator

def setup_metrics(app: FastAPI):
    """
    Set up Prometheus metrics for a FastAPI application.
    
    Args:
        app: FastAPI application
    """
    # Add Prometheus middleware
    app.add_middleware(PrometheusMiddleware)
    
    # Add metrics endpoint
    @app.get("/metrics")
    async def metrics():
        return Response(
            content=generate_latest(REGISTRY),
            media_type="text/plain"
        )
