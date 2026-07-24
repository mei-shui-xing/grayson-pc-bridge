import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs/promises';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport, getDefaultEnvironment } from '@modelcontextprotocol/sdk/client/stdio.js';
import { fileURLToPath } from 'url';
import { captureRemote } from '../utils/capture.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

interface McpConfig {
    command: string;
    args: string[];
    cwd?: string;
    env?: Record<string, string>;
}

export class DesktopCommanderIntegration {
    private mcpClient: Client | null = null;
    private mcpTransport: StdioClientTransport | null = null;
    private windowsUiClient: Client | null = null;
    private windowsUiTransport: StdioClientTransport | null = null;
    private windowsUiToolNames: Set<string> = new Set();
    private windowsUiCallChain: Promise<void> = Promise.resolve();
    private isReady: boolean = false;

    async initialize() {
        console.debug('[DEBUG] DesktopCommanderIntegration.initialize() called');
        const config = await this.resolveMcpConfig();

        if (!config) {
            console.debug('[DEBUG] No MCP config found');
            throw new Error('Desktop Commander MCP not found. Please install it globally via `npm install -g @wonderwhy-er/desktop-commander` or build the local project.');
        }

        console.log(` - ⏳ Connecting to Local Desktop Commander MCP using: ${config.command} ${config.args.join(' ')}`);
        console.debug('[DEBUG] MCP config:', JSON.stringify(config, null, 2));

        try {
            console.debug('[DEBUG] Creating StdioClientTransport');
            // DC_REMOTE_DEVICE tells the spawned server it is serving remote
            // services, so it suppresses local-only behavior like opening the
            // welcome page in a browser the remote user would never see.
            this.mcpTransport = new StdioClientTransport({
                ...config,
                env: { ...getDefaultEnvironment(), ...config.env, DC_REMOTE_DEVICE: 'true' }
            });

            // Create MCP client
            console.debug('[DEBUG] Creating MCP Client');
            this.mcpClient = new Client(
                {
                    name: "desktop-commander-client",
                    version: "1.0.0"
                },
                {
                    capabilities: {}
                }
            );

            // Connect to Desktop Commander
            console.debug('[DEBUG] Connecting MCP client to transport');
            await this.mcpClient.connect(this.mcpTransport);
            console.log(' - 🔌 Connected to Desktop Commander MCP');
            console.debug('[DEBUG] Desktop Commander MCP connection successful');

            await this.initializeWindowsUi();
            this.isReady = true;

        } catch (error) {
            console.error(' - ❌ Failed to connect to Desktop Commander MCP:', error);
            console.debug('[DEBUG] MCP connection error:', error);
            await captureRemote('desktop_integration_init_failed', { error });
            throw error;
        }
    }

    private resolveWindowsUiConfig(): McpConfig | null {
        const python = process.env.DC_WINDOWS_UI_PYTHON;
        const root = process.env.DC_WINDOWS_UI_ROOT;
        if (!python || !root) {
            return null;
        }

        return {
            command: python,
            args: ['-m', 'windows_ui.server'],
            cwd: root,
            env: {
                PYTHONUNBUFFERED: '1',
                WINDOWS_UI_ROOT: root,
                WINDOWS_UI_CONFIG: process.env.WINDOWS_UI_CONFIG || path.join(root, 'config', 'allowlist.json'),
                WINDOWS_UI_RUNTIME_DIR: process.env.WINDOWS_UI_RUNTIME_DIR || path.join(root, 'runtime'),
                WINDOWS_UI_LOG_DIR: process.env.WINDOWS_UI_LOG_DIR || path.join(root, 'logs')
            }
        };
    }

    private async initializeWindowsUi() {
        const config = this.resolveWindowsUiConfig();
        const required = process.env.DC_WINDOWS_UI_REQUIRED === 'true';
        if (!config) {
            if (required) {
                throw new Error('Windows UI module configuration is missing. Set DC_WINDOWS_UI_PYTHON and DC_WINDOWS_UI_ROOT.');
            }
            console.log(' - ℹ️ Windows UI module is not configured');
            return;
        }

        console.log(` - ⏳ Connecting to Windows UI module using: ${config.command} ${config.args.join(' ')}`);
        try {
            this.windowsUiTransport = new StdioClientTransport({
                ...config,
                env: { ...getDefaultEnvironment(), ...config.env }
            });
            this.windowsUiClient = new Client(
                { name: 'grayson-windows-ui-client', version: '1.0.0' },
                { capabilities: {} }
            );
            await this.windowsUiClient.connect(this.windowsUiTransport);
            const tools = await this.windowsUiClient.listTools();
            this.windowsUiToolNames = new Set((tools.tools || []).map(tool => tool.name));
            if (this.windowsUiToolNames.size === 0) {
                throw new Error('Windows UI module returned no tools');
            }
            console.log(` - 🟢 Connected to Windows UI module (${this.windowsUiToolNames.size} tools)`);
        } catch (error) {
            console.error(' - ❌ Failed to connect to Windows UI module:', error);
            await captureRemote('windows_ui_integration_init_failed', { error });
            await this.closeWindowsUi();
            if (required) {
                throw error;
            }
        }
    }

    async resolveMcpConfig(): Promise<McpConfig | null> {
        console.debug('[DEBUG] Resolving MCP config...');
        // Option 1: Development/Local Build
        // Adjusting path resolution since we are now in src/remote-device and dist is in root/dist
        // Original: path.resolve(__dirname, '../../dist/index.js')
        const devPath = path.resolve(__dirname, '../../dist/index.js');
        console.debug('[DEBUG] Checking local dev path:', devPath);
        try {
            await fs.access(devPath);
            console.debug(' - 🔍 Found local MCP server at:', devPath);
            return {
                command: process.execPath, // Use the current node executable
                args: [devPath],
                cwd: path.dirname(devPath)
            };
        } catch {
            console.debug('[DEBUG] Local dev path not found, trying global installation');
            // Local file not found, continue...
        }

        // Option 2: Global Installation
        const commandName = 'desktop-commander';
        console.debug('[DEBUG] Checking for global command:', commandName);
        try {
            await new Promise<void>((resolve, reject) => {
                // Use platform-appropriate command to check if the command exists in PATH
                // We can't run it directly as it's an stdio MCP server that waits for input
                const whichCommand = process.platform === 'win32' ? 'where' : 'which';
                console.debug('[DEBUG] Using platform command:', whichCommand, 'on platform:', process.platform);
                const check = spawn(whichCommand, [commandName], { windowsHide: true });  // Prevent visible console windows on Windows
                check.on('error', (err) => {
                    console.debug('[DEBUG] Spawn error for', whichCommand, ':', err.message);
                    reject(err);
                });
                check.on('close', (code) => {
                    console.debug('[DEBUG]', whichCommand, 'exited with code:', code);
                    return code === 0 ? resolve() : reject(new Error('Command not found'));
                });
            });
            console.debug(' - Found global desktop-commander CLI');
            return {
                command: commandName,
                args: []
            };
        } catch (err) {
            console.debug('[DEBUG] Global command not found:', err);
            // Global command not found
        }

        console.debug('[DEBUG] No MCP config resolved');
        return null;
    }

    private enqueueWindowsUiCall<T>(operation: () => Promise<T>): Promise<T> {
        const run = this.windowsUiCallChain.then(operation, operation);
        this.windowsUiCallChain = run.then(
            () => undefined,
            () => undefined
        );
        return run;
    }

    async callClientTool(toolName: string, args: any, metadata?: any) {
        if (!this.isReady || !this.mcpClient) {
            console.debug('[DEBUG] callClientTool() failed - not ready or no client');
            throw new Error('DesktopIntegration not initialized');
        }

        // Proxy other tools to MCP server
        try {
            console.debug('[DEBUG] Calling MCP tool:', toolName, 'args:', JSON.stringify(args).substring(0, 100));
            const targetClient = this.windowsUiToolNames.has(toolName)
                ? this.windowsUiClient
                : this.mcpClient;
            if (!targetClient) {
                throw new Error(`MCP client for tool ${toolName} is not available`);
            }
            const execute = () => targetClient.callTool({
                name: toolName,
                arguments: args,
                _meta: { remote: true, ...metadata || {} }
            } as any);
            const result = this.windowsUiToolNames.has(toolName)
                ? await this.enqueueWindowsUiCall(execute)
                : await execute();
            console.debug('[DEBUG] Tool call successful:', toolName);
            return result;
        } catch (error) {
            console.error(`Error executing tool ${toolName}:`, error);
            console.debug('[DEBUG] Tool call error details:', error);
            await captureRemote('desktop_integration_tool_call_failed', { error, toolName });
            throw error;
        }
    }

    async listClientTools() {
        if (!this.mcpClient) return { tools: [] };

        try {
            // List tools from MCP server
            const mcpTools = await this.mcpClient.listTools();

            const windowsUiTools = this.windowsUiClient
                ? (await this.windowsUiClient.listTools()).tools || []
                : [];
            const merged = new Map<string, any>();
            for (const tool of [...(mcpTools.tools || []), ...windowsUiTools]) {
                merged.set(tool.name, tool);
            }

            // Merge tools from the existing bridge and the local-only Windows UI sidecar.
            return {
                tools: [...merged.values()]
            };
        } catch (error) {
            console.error('Error fetching capabilities:', error);
            await captureRemote('desktop_integration_list_tools_failed', { error });
            // Fallback to local tools
            return {
                tools: []
            };
        }
    }

    async shutdown() {
        console.debug('[DEBUG] DesktopCommanderIntegration.shutdown() called');
        const closeWithTimeout = async (operation: () => Promise<void>, name: string, timeoutMs: number = 3000) => {
            return Promise.race([
                operation(),
                new Promise<void>((_, reject) =>
                    setTimeout(() => reject(new Error(`${name} timeout after ${timeoutMs}ms`)), timeoutMs)
                )
            ]);
        };

        await this.closeWindowsUi(closeWithTimeout);

        if (this.mcpClient) {
            try {
                console.log('  → Closing MCP client...');
                console.debug('[DEBUG] Calling mcpClient.close() with timeout');
                await closeWithTimeout(
                    () => this.mcpClient!.close(),
                    'MCP client close'
                );
                console.log('  ✓ MCP client closed');
            } catch (e: any) {
                console.warn('  ⚠️  MCP client close timeout or error:', e.message);
                console.debug('[DEBUG] MCP client close error:', e);
                await captureRemote('desktop_integration_shutdown_error', { error: e, component: 'client' });
            }
            this.mcpClient = null;
        }

        if (this.mcpTransport) {
            try {
                console.log('  → Closing MCP transport...');
                console.debug('[DEBUG] Calling mcpTransport.close() with timeout');
                await closeWithTimeout(
                    () => this.mcpTransport!.close(),
                    'MCP transport close'
                );
                console.log('  ✓ MCP transport closed');
            } catch (e: any) {
                console.warn('  ⚠️  MCP transport close timeout or error:', e.message);
                console.debug('[DEBUG] MCP transport close error:', e);
                await captureRemote('desktop_integration_shutdown_error', { error: e, component: 'transport' });
            }
            this.mcpTransport = null;
        }

        this.isReady = false;
        console.debug('[DEBUG] Desktop Commander integration shutdown complete');
    }

    private async closeWindowsUi(
        closeWithTimeout?: (operation: () => Promise<void>, name: string, timeoutMs?: number) => Promise<void>
    ) {
        const close = closeWithTimeout || (async (operation: () => Promise<void>) => operation());
        try {
            await close(() => this.windowsUiCallChain, 'Windows UI call queue drain', 3000);
        } catch (error: any) {
            console.warn('  ⚠️ Windows UI call queue did not drain before shutdown:', error.message);
        }
        if (this.windowsUiClient) {
            try {
                await close(() => this.windowsUiClient!.close(), 'Windows UI client close', 3000);
            } catch (error: any) {
                console.warn('  ⚠️ Windows UI client close error:', error.message);
            }
            this.windowsUiClient = null;
        }
        if (this.windowsUiTransport) {
            try {
                await close(() => this.windowsUiTransport!.close(), 'Windows UI transport close', 3000);
            } catch (error: any) {
                console.warn('  ⚠️ Windows UI transport close error:', error.message);
            }
            this.windowsUiTransport = null;
        }
        this.windowsUiToolNames.clear();
        this.windowsUiCallChain = Promise.resolve();
    }
}
