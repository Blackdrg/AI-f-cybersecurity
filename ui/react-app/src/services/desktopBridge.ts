/**
 * Desktop Bridge for AI-f Enterprise
 * Handles communication with the local backend sidecar.
 */

interface DesktopConfig {
  apiUrl: string;
  isDesktop: boolean;
  version: string;
}

class DesktopBridge {
  private static instance: DesktopBridge;
  private config: DesktopConfig = {
    apiUrl: 'http://localhost:8001', // Default fallback
    isDesktop: !!(window as any).__TAURI__,
    version: '0.1.0'
  };

  private constructor() {
    this.init();
  }

  public static getInstance(): DesktopBridge {
    if (!DesktopBridge.instance) {
      DesktopBridge.instance = new DesktopBridge();
    }
    return DesktopBridge.instance;
  }

  private async init() {
    if (this.config.isDesktop) {
      console.log('Running in Desktop Mode');
      try {
        // In a real implementation, we could get the port from Tauri
        // For now, we'll assume the default or get it from an environment variable injected by Tauri
        const tauri = (window as any).__TAURI__;
        if (tauri) {
          // We can call a Tauri command to get the actual API port
          // const port = await tauri.invoke('get_api_port');
          // this.config.apiUrl = `http://localhost:${port}`;
        }
      } catch (e) {
        console.error('Failed to initialize Desktop Bridge:', e);
      }
    }
  }

  public getApiUrl(): string {
    return this.config.apiUrl;
  }

  public isDesktop(): boolean {
    return this.config.isDesktop;
  }
}

export const desktopBridge = DesktopBridge.getInstance();
export default desktopBridge;
