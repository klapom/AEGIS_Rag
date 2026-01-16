/**
 * MCP Type Definitions
 * Sprint 107: Shared types for MCP components
 */

export interface MCPServerDefinition {
  id: string;
  name: string;
  description: string;
  transport: string;
  command?: string;
  args?: string[];
  url?: string;
  dependencies?: {
    npm?: string[];
    pip?: string[];
    env?: string[];
  };
  repository?: string;
  homepage?: string;
  version: string;
  stars: number;
  downloads: number;
  tags: string[];
}
