"""
Main module for integrating all monitoring and observability components.
"""
import os
from typing import Dict, List, Optional

from fastapi import FastAPI

from app.utils.logging.zap_logger import get_logger
from app.utils.metrics.prometheus import setup_metrics
from app.utils.tracing.tracer import setup_tracing

logger = get_logger(service_name="observability")

def setup_observability(
    app: FastAPI,
    service_name: str = None,
    enable_metrics: bool = True,
    enable_tracing: bool = True,
):
    """
    Set up all observability components for a FastAPI application.
    
    Args:
        app: FastAPI application
        service_name: Name of the service
        enable_metrics: Whether to enable metrics
        enable_tracing: Whether to enable tracing
    """
    # Get service name from environment variable if not provided
    if service_name is None:
        service_name = os.getenv("SERVICE_NAME", "orbithost")
    
    logger.info(f"Setting up observability for service: {service_name}")
    
    # Set up metrics
    if enable_metrics:
        logger.info("Setting up Prometheus metrics")
        setup_metrics(app)
    
    # Set up tracing
    if enable_tracing:
        logger.info("Setting up distributed tracing")
        setup_tracing(app, service_name)
    
    logger.info("Observability setup complete")
    
    return {
        "service_name": service_name,
        "metrics_enabled": enable_metrics,
        "tracing_enabled": enable_tracing,
    }
