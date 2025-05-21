"""
Simplified tracing implementation for distributed tracing.
"""
import asyncio
import functools
import inspect
import os
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Callable, Dict, List, Optional, Union

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.utils.logging.zap_logger import get_logger

logger = get_logger(service_name="tracing")

class Span:
    """
    Represents a span in a trace.
    """
    
    def __init__(
        self,
        name: str,
        trace_id: str = None,
        parent_span_id: str = None,
        tags: Dict[str, str] = None,
        start_time: float = None,
    ):
        """
        Initialize a span.
        
        Args:
            name: Name of the span
            trace_id: ID of the trace this span belongs to
            parent_span_id: ID of the parent span
            tags: Tags to associate with the span
            start_time: Start time of the span
        """
        self.name = name
        self.span_id = str(uuid.uuid4())
        self.trace_id = trace_id or str(uuid.uuid4())
        self.parent_span_id = parent_span_id
        self.tags = tags or {}
        self.start_time = start_time or time.time()
        self.end_time = None
        self.events = []
    
    def finish(self):
        """Finish the span."""
        self.end_time = time.time()
        
        # Log span information
        span_data = {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "duration_ms": round((self.end_time - self.start_time) * 1000, 2),
            "tags": self.tags,
            "events": self.events,
        }
        
        logger.info("Span completed", span=span_data)
        
        return span_data
    
    def add_event(self, name: str, attributes: Dict[str, Any] = None):
        """
        Add an event to the span.
        
        Args:
            name: Name of the event
            attributes: Attributes to associate with the event
        """
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {},
        })
    
    def add_tag(self, key: str, value: str):
        """
        Add a tag to the span.
        
        Args:
            key: Tag key
            value: Tag value
        """
        self.tags[key] = value

class Tracer:
    """
    Simple tracer for distributed tracing.
    """
    
    def __init__(self, service_name: str):
        """
        Initialize the tracer.
        
        Args:
            service_name: Name of the service
        """
        self.service_name = service_name
        self._current_spans = {}  # task_id -> span
    
    def _get_current_span(self) -> Optional[Span]:
        """
        Get the current span for the current task.
        
        Returns:
            Current span or None if no span exists
        """
        task = asyncio.current_task() if hasattr(asyncio, "current_task") else asyncio.Task.current_task()
        if task is None:
            return None
        
        return self._current_spans.get(id(task))
    
    def _set_current_span(self, span: Span):
        """
        Set the current span for the current task.
        
        Args:
            span: Span to set as current
        """
        task = asyncio.current_task() if hasattr(asyncio, "current_task") else asyncio.Task.current_task()
        if task is not None:
            self._current_spans[id(task)] = span
    
    def _clear_current_span(self):
        """Clear the current span for the current task."""
        task = asyncio.current_task() if hasattr(asyncio, "current_task") else asyncio.Task.current_task()
        if task is not None and id(task) in self._current_spans:
            del self._current_spans[id(task)]
    
    @contextmanager
    def start_span(
        self,
        name: str,
        trace_id: str = None,
        parent_span_id: str = None,
        tags: Dict[str, str] = None,
    ):
        """
        Start a new span.
        
        Args:
            name: Name of the span
            trace_id: ID of the trace this span belongs to
            parent_span_id: ID of the parent span
            tags: Tags to associate with the span
            
        Yields:
            The created span
        """
        current_span = self._get_current_span()
        
        # Use current span's trace_id and span_id as parent if available
        if current_span and not trace_id:
            trace_id = current_span.trace_id
        
        if current_span and not parent_span_id:
            parent_span_id = current_span.span_id
        
        # Create new span
        span = Span(
            name=name,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            tags=tags,
        )
        
        # Add service name tag
        span.add_tag("service.name", self.service_name)
        
        # Set as current span
        self._set_current_span(span)
        
        try:
            yield span
        finally:
            # Finish span
            span.finish()
            
            # Restore parent span as current
            if current_span:
                self._set_current_span(current_span)
            else:
                self._clear_current_span()
    
    @asynccontextmanager
    async def start_async_span(
        self,
        name: str,
        trace_id: str = None,
        parent_span_id: str = None,
        tags: Dict[str, str] = None,
    ):
        """
        Start a new async span.
        
        Args:
            name: Name of the span
            trace_id: ID of the trace this span belongs to
            parent_span_id: ID of the parent span
            tags: Tags to associate with the span
            
        Yields:
            The created span
        """
        with self.start_span(name, trace_id, parent_span_id, tags) as span:
            yield span
    
    def trace(self, name: str = None, tags: Dict[str, str] = None):
        """
        Decorator for tracing a function.
        
        Args:
            name: Name of the span (defaults to function name)
            tags: Tags to associate with the span
            
        Returns:
            Decorated function
        """
        def decorator(func):
            # Get function name if not provided
            span_name = name or func.__qualname__
            
            # Check if function is async
            is_async = inspect.iscoroutinefunction(func)
            
            if is_async:
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    async with self.start_async_span(span_name, tags=tags) as span:
                        return await func(*args, **kwargs)
                
                return async_wrapper
            else:
                @functools.wraps(func)
                def sync_wrapper(*args, **kwargs):
                    with self.start_span(span_name, tags=tags) as span:
                        return func(*args, **kwargs)
                
                return sync_wrapper
            
        return decorator

class TracingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for tracing HTTP requests.
    """
    
    def __init__(self, app: ASGIApp, tracer: Tracer):
        """
        Initialize the tracing middleware.
        
        Args:
            app: ASGI application
            tracer: Tracer instance
        """
        super().__init__(app)
        self.tracer = tracer
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process an incoming request.
        
        Args:
            request: Incoming request
            call_next: Function to call next middleware
            
        Returns:
            Response
        """
        # Extract trace context from headers
        trace_id = request.headers.get("X-Trace-ID")
        parent_span_id = request.headers.get("X-Span-ID")
        
        # Create span for request
        span_name = f"{request.method} {request.url.path}"
        
        # Add tags
        tags = {
            "http.method": request.method,
            "http.url": str(request.url),
            "http.host": request.headers.get("host", ""),
            "http.user_agent": request.headers.get("user-agent", ""),
        }
        
        # Process request with span
        async with self.tracer.start_async_span(
            name=span_name,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            tags=tags,
        ) as span:
            try:
                # Call next middleware
                response = await call_next(request)
                
                # Add response tags
                span.add_tag("http.status_code", str(response.status_code))
                
                # Add trace headers to response
                response.headers["X-Trace-ID"] = span.trace_id
                response.headers["X-Span-ID"] = span.span_id
                
                return response
            except Exception as e:
                # Add error tags
                span.add_tag("error", "true")
                span.add_tag("error.type", type(e).__name__)
                span.add_tag("error.message", str(e))
                
                # Add error event
                span.add_event("exception", {
                    "exception.type": type(e).__name__,
                    "exception.message": str(e),
                })
                
                raise

def get_tracer(service_name: str = None) -> Tracer:
    """
    Get a configured tracer instance.
    
    Args:
        service_name: Name of the service
        
    Returns:
        Configured tracer instance
    """
    # Get service name from environment variable if not provided
    if service_name is None:
        service_name = os.getenv("SERVICE_NAME", "orbithost")
    
    return Tracer(service_name=service_name)

def setup_tracing(app: FastAPI, service_name: str = None):
    """
    Set up tracing for a FastAPI application.
    
    Args:
        app: FastAPI application
        service_name: Name of the service
    """
    # Get tracer
    tracer = get_tracer(service_name)
    
    # Add tracing middleware
    app.add_middleware(TracingMiddleware, tracer=tracer)
    
    return tracer
