# Render MCP Server Setup for Cursor

The Render MCP server allows you to manage Render deployments directly from Cursor.

## Step 1: Get Your Render API Key

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click on your profile → **Account Settings**
3. Scroll to **API Keys** section
4. Click **Create API Key**
5. Give it a name (e.g., "Cursor MCP")
6. Copy the API key (you'll only see it once!)

## Step 2: Configure MCP Server in Cursor

### Option A: Use Render's Hosted MCP Server (Recommended)

This is the easiest option - no local installation needed!

1. Open Cursor Settings:
   - Press `Ctrl+,` (Windows) or `Cmd+,` (Mac)
   - Or go to File → Preferences → Settings

2. Search for "MCP" or "Model Context Protocol"

3. Add the following configuration to your MCP settings:

```json
{
  "mcpServers": {
    "render": {
      "url": "https://mcp.render.com/mcp",
      "apiKey": "YOUR_RENDER_API_KEY_HERE"
    }
  }
}
```

Replace `YOUR_RENDER_API_KEY_HERE` with the API key you copied in Step 1.

### Option B: Run MCP Server Locally (Advanced)

If you prefer to run it locally, you have two options:

#### Option B1: Using Docker

1. Make sure Docker is installed and running

2. Add to Cursor MCP settings:

```json
{
  "mcpServers": {
    "render": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-p",
        "8080:8080",
        "render/mcp-server"
      ],
      "env": {
        "RENDER_API_KEY": "YOUR_RENDER_API_KEY_HERE"
      },
      "disabled": false
    }
  }
}
```

#### Option B2: Using Executable

1. **Download the executable:**
   - Visit: https://github.com/render-oss/render-mcp-server/releases
   - Download the Windows executable (`.exe` file)
   - Save it to a location like `C:\tools\render-mcp-server.exe`

2. **Add to Cursor MCP settings:**

```json
{
  "mcpServers": {
    "render": {
      "command": "C:\\tools\\render-mcp-server.exe",
      "args": [
        "--api-key",
        "YOUR_RENDER_API_KEY_HERE"
      ],
      "env": {},
      "disabled": false
    }
  }
}
```

**Note:** Update the path to match where you saved the executable.

## Step 3: Restart Cursor

After adding the configuration, restart Cursor for the changes to take effect.

## Step 4: Verify Installation

Once configured, you should be able to:
- List your Render services
- Deploy services
- View logs
- Manage environment variables
- And more!

Try asking me: "List my Render services" or "Deploy my Django backend to Render"

## Troubleshooting

**MCP server not connecting:**
- Verify your API key is correct
- Check that Cursor has been restarted
- Ensure the API key has proper permissions in Render

**Docker option not working:**
- Make sure Docker Desktop is running
- Verify Docker is accessible from command line: `docker --version`

**Executable option not working:**
- Ensure the executable path is correct
- On Windows, you may need to use `\\` instead of `\` in paths
- Check that the executable has proper permissions

## Security Note

⚠️ **Important**: Never commit your Render API key to version control!
- Keep it in Cursor's settings (which are local)
- Use environment variables if running locally
- Rotate your API key if it's ever exposed

## Additional Resources

- [Render MCP Server Documentation](https://render.com/docs/mcp-server)
- [Render API Documentation](https://render.com/docs/api)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)


