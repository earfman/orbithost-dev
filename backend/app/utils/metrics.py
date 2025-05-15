from prometheus_client import Counter, Histogram, Gauge

# Deployment metrics
deployment_count = Counter(
    "orbithost_deployments_total",
    "Total number of deployments processed",
    ["repository", "status"]
)

deployment_duration = Histogram(
    "orbithost_deployment_duration_seconds",
    "Time taken to process a deployment",
    ["repository"]
)

# Webhook metrics
webhook_duration = Histogram(
    "orbithost_webhook_duration_seconds",
    "Time taken to send a webhook"
)

webhook_failures = Counter(
    "orbithost_webhook_failures_total",
    "Total number of webhook delivery failures",
    ["repository"]
)

# Screenshot metrics
screenshot_duration = Histogram(
    "orbithost_screenshot_duration_seconds",
    "Time taken to capture a screenshot"
)

# System metrics
active_deployments = Gauge(
    "orbithost_active_deployments",
    "Number of deployments currently being processed"
)
