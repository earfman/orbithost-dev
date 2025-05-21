# OrbitContext & OrbitBridge

OrbitContext is a unified protocol for managing context across AI agents, developer tools, and runtime environments. It provides a structured format for capturing, storing, and sharing runtime data, errors, user interactions, and development history.

## OrbitContext Protocol

OrbitContext solves the context gap in AI-native development by providing:

1. **Unified Schema**: A standardized format for representing all types of development and runtime context
2. **Persistent Store**: An event-sourced database that maintains the full history of context
3. **Relationship Mapping**: Explicit connections between related context entries
4. **Multi-Agent Support**: Shared memory layer accessible by multiple AI tools
5. **MCP Compatibility**: Integration with the Model Context Protocol for seamless AI tool connectivity

## MCP Architecture

OrbitHost implements a federated Model Context Protocol (MCP) architecture where it serves as a central hub for AI capabilities:

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Applications                     │
│  (IDEs, Browsers, Command-line tools, Custom integrations)  │
└───────────────────────────────┬─────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                   Universal MCP Client Layer                 │
│      (Discovers and connects to available MCP servers)       │
└───────────┬─────────────────────────────────────┬───────────┘
            │                                     │
            ▼                                     ▼
┌───────────────────────────┐       ┌───────────────────────────┐
│    Local MCP Servers      │       │   OrbitHost MCP Servers   │
│  (Windsurf, Claude, etc.) │◄─────►│  (Our hosted AI services) │
└───────────────────────────┘       └───────────────────────────┘
```

### Key Benefits

- **Independence**: Users don't need third-party AI tools for AI-powered analysis
- **Consistency**: All users get the same high-quality AI capabilities
- **Fallback Support**: Uses local AI tools when available, hosted services when needed
- **Enterprise Ready**: Compatible with strict security policies
- **Specialized AI**: Tailored for deployment analysis, error debugging, and performance optimization

## Components

### 1. OrbitContext

The core data model for representing context across the system. Includes:

- Deployment information
- Error data
- Metrics
- User interactions
- Code artifacts

### 2. Universal MCP Client

A client that can connect to any MCP-compatible server, including:

- Auto-discovery of MCP endpoints
- Support for multiple transport protocols (SSE, WebSocket, STDIO)
- Dynamic tool discovery
- Resource management

### 3. MCP Server

A hosted Model Context Protocol server that provides:

- AI-powered deployment analysis
- Error debugging assistance
- Performance recommendations
- Multi-modal context understanding

### 4. AI Feedback Service

A service that leverages the MCP architecture to provide:

- Automated deployment feedback
- Error root cause analysis
- Performance optimization suggestions
- Security vulnerability detection

## Usage

```python
# Create an MCP client
from app.services.orbitbridge.mcp_client import MCPClient

# Auto-discovers endpoints if set to "auto"
client = MCPClient(mcp_url="auto")

# Or connect to a specific MCP server
client = MCPClient(mcp_url="http://localhost:8000/mcp")

# Send context to an MCP server
response = await client.send_context(context)

# Discover available tools
tools = await client.discover_tools()

# Invoke a tool
result = await client.invoke_tool("analyze_deployment", {"deployment_id": "deploy-123"})
```

## Integration with AI Tools

The OrbitBridge architecture enables seamless integration with:

1. **Windsurf**: For IDE integration and code analysis
2. **Claude**: For natural language understanding and code generation
3. **Cursor**: For AI-assisted coding
4. **Custom AI Tools**: Through the MCP standard

For more detailed information, see the [OrbitContext Whitepaper](../../../docs/OrbitContext_Whitepaper.md).
