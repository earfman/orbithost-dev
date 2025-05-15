# Live Updates with OrbitHost

OrbitHost provides real-time deployment updates using Server-Sent Events (SSE). This allows your application to receive instant notifications when a new deployment occurs, enabling features like automatic reloading or displaying deployment status.

## How It Works

1. OrbitHost listens for GitHub webhook events
2. When a deployment is triggered, OrbitHost sends real-time updates via SSE
3. Your client application can subscribe to these events and react accordingly

## Client-Side Integration

### Basic JavaScript Integration

Add this script to your application to receive live updates:

```javascript
class OrbitHostLiveUpdates {
  constructor(options = {}) {
    this.repository = options.repository; // Format: owner/repo
    this.baseUrl = options.baseUrl || 'https://api.orbithost.app';
    this.autoReload = options.autoReload || false;
    this.onUpdate = options.onUpdate || (() => {});
    this.onConnect = options.onConnect || (() => {});
    this.onDisconnect = options.onDisconnect || (() => {});
    this.eventSource = null;
    this.connectionAttempts = 0;
    this.maxConnectionAttempts = options.maxConnectionAttempts || 5;
    this.reconnectDelay = options.reconnectDelay || 3000;
  }

  connect() {
    if (!this.repository) {
      console.error('OrbitHost Live Updates: Repository is required');
      return;
    }

    // Close any existing connection
    this.disconnect();

    try {
      // Create a new SSE connection
      const url = `${this.baseUrl}/sse/deployments/${encodeURIComponent(this.repository)}`;
      this.eventSource = new EventSource(url);

      // Set up event handlers
      this.eventSource.addEventListener('connection_established', (event) => {
        console.log('OrbitHost Live Updates: Connected');
        this.connectionAttempts = 0;
        const data = JSON.parse(event.data);
        this.onConnect(data);
      });

      this.eventSource.addEventListener('deployment_update', (event) => {
        const data = JSON.parse(event.data);
        console.log(`OrbitHost Live Updates: Deployment status: ${data.status}`);
        
        this.onUpdate(data);
        
        // Auto-reload if enabled and deployment is successful
        if (this.autoReload && data.status === 'deployed') {
          console.log('OrbitHost Live Updates: Auto-reloading page');
          setTimeout(() => window.location.reload(), 1000);
        }
      });

      this.eventSource.addEventListener('error', (event) => {
        console.error('OrbitHost Live Updates: Connection error', event);
        this.disconnect();
        
        // Attempt to reconnect
        if (this.connectionAttempts < this.maxConnectionAttempts) {
          this.connectionAttempts++;
          console.log(`OrbitHost Live Updates: Reconnecting (attempt ${this.connectionAttempts}/${this.maxConnectionAttempts})`);
          setTimeout(() => this.connect(), this.reconnectDelay);
        } else {
          console.error('OrbitHost Live Updates: Max connection attempts reached');
          this.onDisconnect();
        }
      });
    } catch (error) {
      console.error('OrbitHost Live Updates: Failed to connect', error);
    }
  }

  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
      this.onDisconnect();
    }
  }
}
```

### Usage Example

```html
<script>
  document.addEventListener('DOMContentLoaded', () => {
    // Initialize the live updates
    const liveUpdates = new OrbitHostLiveUpdates({
      repository: 'your-username/your-repo',
      autoReload: true,
      onUpdate: (data) => {
        console.log('Deployment update:', data);
        // Update UI with deployment status
        const statusElement = document.getElementById('deployment-status');
        if (statusElement) {
          statusElement.textContent = `Deployment status: ${data.status}`;
          statusElement.className = `status-${data.status}`;
        }
      }
    });
    
    // Connect to the SSE endpoint
    liveUpdates.connect();
  });
</script>

<!-- Optional: Add this to your HTML to display deployment status -->
<div id="deployment-status" class="status-unknown">
  Deployment status: unknown
</div>

<style>
  .status-pending { color: orange; }
  .status-deployed { color: green; }
  .status-failed { color: red; }
  .status-unknown { color: gray; }
</style>
```

## React Integration

For React applications, you can use this custom hook:

```jsx
import { useState, useEffect } from 'react';

function useOrbitHostLiveUpdates(options) {
  const [deploymentStatus, setDeploymentStatus] = useState('unknown');
  const [deploymentData, setDeploymentData] = useState(null);
  const [connected, setConnected] = useState(false);
  
  useEffect(() => {
    if (!options.repository) {
      console.error('Repository is required');
      return;
    }
    
    const baseUrl = options.baseUrl || 'https://api.orbithost.app';
    const url = `${baseUrl}/sse/deployments/${encodeURIComponent(options.repository)}`;
    let eventSource = null;
    let connectionAttempts = 0;
    const maxConnectionAttempts = options.maxConnectionAttempts || 5;
    const reconnectDelay = options.reconnectDelay || 3000;
    
    function connect() {
      try {
        eventSource = new EventSource(url);
        
        eventSource.addEventListener('connection_established', (event) => {
          console.log('OrbitHost: Connected');
          setConnected(true);
          connectionAttempts = 0;
        });
        
        eventSource.addEventListener('deployment_update', (event) => {
          const data = JSON.parse(event.data);
          console.log(`OrbitHost: Deployment status: ${data.status}`);
          setDeploymentStatus(data.status);
          setDeploymentData(data);
          
          if (options.onUpdate) {
            options.onUpdate(data);
          }
          
          if (options.autoReload && data.status === 'deployed') {
            console.log('OrbitHost: Auto-reloading page');
            setTimeout(() => window.location.reload(), 1000);
          }
        });
        
        eventSource.addEventListener('error', () => {
          console.error('OrbitHost: Connection error');
          setConnected(false);
          
          if (eventSource) {
            eventSource.close();
            eventSource = null;
          }
          
          if (connectionAttempts < maxConnectionAttempts) {
            connectionAttempts++;
            console.log(`OrbitHost: Reconnecting (attempt ${connectionAttempts}/${maxConnectionAttempts})`);
            setTimeout(connect, reconnectDelay);
          } else {
            console.error('OrbitHost: Max connection attempts reached');
          }
        });
      } catch (error) {
        console.error('OrbitHost: Failed to connect', error);
        setConnected(false);
      }
    }
    
    connect();
    
    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [options.repository]);
  
  return { deploymentStatus, deploymentData, connected };
}

// Usage example
function DeploymentStatus() {
  const { deploymentStatus, deploymentData, connected } = useOrbitHostLiveUpdates({
    repository: 'your-username/your-repo',
    autoReload: false
  });
  
  return (
    <div className={`deployment-status status-${deploymentStatus}`}>
      <div>Connection status: {connected ? 'Connected' : 'Disconnected'}</div>
      <div>Deployment status: {deploymentStatus}</div>
      {deploymentData && (
        <div>
          <div>Latest commit: {deploymentData.commit_message}</div>
          <div>Author: {deploymentData.author}</div>
          <div>Timestamp: {new Date(deploymentData.timestamp).toLocaleString()}</div>
        </div>
      )}
    </div>
  );
}
```

## Vue.js Integration

For Vue.js applications, you can create a composable:

```javascript
// useOrbitHostLiveUpdates.js
import { ref, onMounted, onUnmounted } from 'vue';

export function useOrbitHostLiveUpdates(options) {
  const deploymentStatus = ref('unknown');
  const deploymentData = ref(null);
  const connected = ref(false);
  let eventSource = null;
  
  function connect() {
    if (!options.repository) {
      console.error('Repository is required');
      return;
    }
    
    const baseUrl = options.baseUrl || 'https://api.orbithost.app';
    const url = `${baseUrl}/sse/deployments/${encodeURIComponent(options.repository)}`;
    
    try {
      eventSource = new EventSource(url);
      
      eventSource.addEventListener('connection_established', (event) => {
        console.log('OrbitHost: Connected');
        connected.value = true;
      });
      
      eventSource.addEventListener('deployment_update', (event) => {
        const data = JSON.parse(event.data);
        console.log(`OrbitHost: Deployment status: ${data.status}`);
        deploymentStatus.value = data.status;
        deploymentData.value = data;
        
        if (options.onUpdate) {
          options.onUpdate(data);
        }
        
        if (options.autoReload && data.status === 'deployed') {
          console.log('OrbitHost: Auto-reloading page');
          setTimeout(() => window.location.reload(), 1000);
        }
      });
      
      eventSource.addEventListener('error', () => {
        console.error('OrbitHost: Connection error');
        connected.value = false;
        disconnect();
      });
    } catch (error) {
      console.error('OrbitHost: Failed to connect', error);
      connected.value = false;
    }
  }
  
  function disconnect() {
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
  }
  
  onMounted(() => {
    connect();
  });
  
  onUnmounted(() => {
    disconnect();
  });
  
  return { deploymentStatus, deploymentData, connected };
}
```

## Advanced Configuration

The OrbitHost Live Updates client supports several configuration options:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `repository` | String | Required | The repository to subscribe to (format: owner/repo) |
| `baseUrl` | String | 'https://api.orbithost.app' | The base URL of the OrbitHost API |
| `autoReload` | Boolean | false | Whether to automatically reload the page when a deployment is successful |
| `onUpdate` | Function | () => {} | Callback function called when a deployment update is received |
| `onConnect` | Function | () => {} | Callback function called when the connection is established |
| `onDisconnect` | Function | () => {} | Callback function called when the connection is closed |
| `maxConnectionAttempts` | Number | 5 | Maximum number of connection attempts |
| `reconnectDelay` | Number | 3000 | Delay between reconnection attempts (in milliseconds) |

## Security Considerations

The SSE endpoint is public and does not require authentication. This means that anyone can subscribe to deployment updates for your repository. If you need to restrict access to deployment updates, you should implement authentication in your client application.
