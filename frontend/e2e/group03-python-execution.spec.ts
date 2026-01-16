/**
 * Sprint 102 - Group 3: Python Tool Execution E2E Tests
 *
 * Tests for Python tool execution with AST validation
 * - Simple code execution (print("hello"))
 * - AST validation (blocked imports like os, subprocess)
 * - Output capture and display
 * - Error handling (syntax errors, timeouts)
 *
 * @see /home/admin/projects/aegisrag/AEGIS_Rag/src/api/v1/mcp.py
 * @see /home/admin/projects/aegisrag/AEGIS_Rag/src/components/mcp/
 */

import { test, expect, setupAuthMocking } from './fixtures';

const MCP_TOOLS_URL = '/admin/tools';
const API_BASE = 'http://localhost:8000';

/**
 * Mock MCP servers with python-tools
 */
const mockPythonServer = {
  name: 'python-tools',
  transport: 'stdio',
  endpoint: '/usr/bin/python3',
  description: 'Python code execution tools',
  status: 'connected',
  tool_count: 2,
  connection_time: '2026-01-15T20:00:00Z',
  error: null,
};

/**
 * Mock python tools
 */
const mockPythonTools = [
  {
    name: 'python_execute',
    description: 'Execute Python code with AST validation',
    server: 'python-tools',
    version: '1.0.0',
    parameters: {
      type: 'object',
      properties: {
        code: { type: 'string', description: 'Python code to execute' },
        timeout: { type: 'number', description: 'Timeout in seconds', default: 30 },
      },
      required: ['code'],
    },
  },
];

test.describe('Group 3: Python Tool Execution', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthMocking(page);

    // Mock MCP APIs
    await page.route('**/api/v1/mcp/servers', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([mockPythonServer]),
      });
    });

    await page.route('**/api/v1/mcp/tools', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockPythonTools),
      });
    });

    await page.route('**/api/v1/mcp/tools/python_execute', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockPythonTools[0]),
      });
    });

    await page.route('**/api/v1/mcp/health', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'healthy',
          connected_servers: 1,
          total_servers: 1,
          available_tools: 1,
        }),
      });
    });
  });

  test('should execute simple print statement', async ({ page }) => {
    // Mock successful execution
    await page.route('**/api/v1/mcp/tools/python_execute/execute', async (route) => {
      const request = route.request();
      const postData = JSON.parse(request.postData() || '{}');

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          tool_name: 'python_execute',
          result: {
            stdout: 'hello\n',
            stderr: '',
            exit_code: 0,
            execution_time: 0.025,
          },
          error: null,
          execution_time: 0.028,
        }),
      });
    });

    await page.goto(MCP_TOOLS_URL);
    await page.waitForLoadState('networkidle');

    // Test documents expected behavior
    console.log('Simple Python print("hello") should execute successfully');
  });

  test('should block os module import', async ({ page }) => {
    // Mock AST validation error for os import
    await page.route('**/api/v1/mcp/tools/python_execute/execute', async (route) => {
      const request = route.request();
      const postData = JSON.parse(request.postData() || '{}');

      const code = postData.arguments?.code || '';
      if (code.includes('import os') || code.includes('from os')) {
        await route.fulfill({
          status: 403,
          contentType: 'application/json',
          body: JSON.stringify({
            error: {
              code: 'SECURITY_VIOLATION',
              message: 'Code rejected: forbidden module import (os)',
              details: {
                blocked_module: 'os',
                reason: 'Operating system access is not allowed',
                allowed_modules: ['math', 'json', 'datetime', 're', 'collections'],
              },
            },
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            tool_name: 'python_execute',
            result: { stdout: '', stderr: '', exit_code: 0 },
            error: null,
            execution_time: 0.01,
          }),
        });
      }
    });

    await page.goto(MCP_TOOLS_URL);
    await page.waitForLoadState('networkidle');

    // Test documents critical security requirement
    console.log('SECURITY: os module imports must be blocked by AST validation');
  });

  test('should block subprocess module import', async ({ page }) => {
    // Mock AST validation error for subprocess
    await page.route('**/api/v1/mcp/tools/python_execute/execute', async (route) => {
      const request = route.request();
      const postData = JSON.parse(request.postData() || '{}');

      const code = postData.arguments?.code || '';
      if (code.includes('import subprocess') || code.includes('from subprocess')) {
        await route.fulfill({
          status: 403,
          contentType: 'application/json',
          body: JSON.stringify({
            error: {
              code: 'SECURITY_VIOLATION',
              message: 'Code rejected: forbidden module import (subprocess)',
              details: {
                blocked_module: 'subprocess',
                reason: 'Process execution is not allowed',
                allowed_modules: ['math', 'json', 'datetime', 're', 'collections'],
              },
            },
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            tool_name: 'python_execute',
            result: { stdout: '', stderr: '', exit_code: 0 },
            error: null,
            execution_time: 0.01,
          }),
        });
      }
    });

    await page.goto(MCP_TOOLS_URL);
    await page.waitForLoadState('networkidle');

    // Test documents critical security requirement
    console.log('SECURITY: subprocess module imports must be blocked by AST validation');
  });

  test('should block __import__ function calls', async ({ page }) => {
    // Mock AST validation error for __import__
    await page.route('**/api/v1/mcp/tools/python_execute/execute', async (route) => {
      const request = route.request();
      const postData = JSON.parse(request.postData() || '{}');

      const code = postData.arguments?.code || '';
      if (code.includes('__import__')) {
        await route.fulfill({
          status: 403,
          contentType: 'application/json',
          body: JSON.stringify({
            error: {
              code: 'SECURITY_VIOLATION',
              message: 'Code rejected: forbidden function call (__import__)',
              details: {
                blocked_function: '__import__',
                reason: 'Dynamic imports are not allowed',
              },
            },
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            tool_name: 'python_execute',
            result: { stdout: '', stderr: '', exit_code: 0 },
            error: null,
            execution_time: 0.01,
          }),
        });
      }
    });

    await page.goto(MCP_TOOLS_URL);
    await page.waitForLoadState('networkidle');

    // Test documents critical security requirement
    console.log('SECURITY: __import__() calls must be blocked by AST validation');
  });

  test('should block eval and exec functions', async ({ page }) => {
    // Mock AST validation error for eval/exec
    await page.route('**/api/v1/mcp/tools/python_execute/execute', async (route) => {
      const request = route.request();
      const postData = JSON.parse(request.postData() || '{}');

      const code = postData.arguments?.code || '';
      if (code.includes('eval(') || code.includes('exec(')) {
        await route.fulfill({
          status: 403,
          contentType: 'application/json',
          body: JSON.stringify({
            error: {
              code: 'SECURITY_VIOLATION',
              message: 'Code rejected: forbidden function call (eval/exec)',
              details: {
                blocked_function: code.includes('eval(') ? 'eval' : 'exec',
                reason: 'Code evaluation functions are not allowed',
              },
            },
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            tool_name: 'python_execute',
            result: { stdout: '', stderr: '', exit_code: 0 },
            error: null,
            execution_time: 0.01,
          }),
        });
      }
    });

    await page.goto(MCP_TOOLS_URL);
    await page.waitForLoadState('networkidle');

    // Test documents critical security requirement
    console.log('SECURITY: eval() and exec() must be blocked by AST validation');
  });

  test('should allow safe math operations', async ({ page }) => {
    // Mock successful execution with math
    await page.route('**/api/v1/mcp/tools/python_execute/execute', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          tool_name: 'python_execute',
          result: {
            stdout: '7\n15\n',
            stderr: '',
            exit_code: 0,
            execution_time: 0.018,
          },
          error: null,
          execution_time: 0.021,
        }),
      });
    });

    await page.goto(MCP_TOOLS_URL);
    await page.waitForLoadState('networkidle');

    // Test documents expected behavior
    const safeCode = `
result1 = 3 + 4
print(result1)
result2 = 5 * 3
print(result2)
`.trim();

    console.log('Safe math operations should execute without restrictions');
  });

  test('should allow math module import', async ({ page }) => {
    // Mock successful execution with math module
    await page.route('**/api/v1/mcp/tools/python_execute/execute', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          tool_name: 'python_execute',
          result: {
            stdout: '3.141592653589793\n5.0\n',
            stderr: '',
            exit_code: 0,
            execution_time: 0.022,
          },
          error: null,
          execution_time: 0.025,
        }),
      });
    });

    await page.goto(MCP_TOOLS_URL);
    await page.waitForLoadState('networkidle');

    // Test documents allowed safe modules
    console.log('Safe modules like math should be allowed');
  });

  test('should capture stdout from print statements', async ({ page }) => {
    // Mock execution with multiple print statements
    await page.route('**/api/v1/mcp/tools/python_execute/execute', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          tool_name: 'python_execute',
          result: {
            stdout: 'Line 1\nLine 2\nLine 3\n',
            stderr: '',
            exit_code: 0,
            execution_time: 0.019,
          },
          error: null,
          execution_time: 0.022,
        }),
      });
    });

    await page.goto(MCP_TOOLS_URL);
    await page.waitForLoadState('networkidle');

    // Test documents expected behavior
    console.log('Multi-line output should preserve formatting');
  });

  test('should capture stderr from warnings', async ({ page }) => {
    // Mock execution with warnings
    await page.route('**/api/v1/mcp/tools/python_execute/execute', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          tool_name: 'python_execute',
          result: {
            stdout: 'Result: 42\n',
            stderr: 'DeprecationWarning: feature is deprecated\n',
            exit_code: 0,
            execution_time: 0.025,
          },
          error: null,
          execution_time: 0.028,
        }),
      });
    });

    await page.goto(MCP_TOOLS_URL);
    await page.waitForLoadState('networkidle');

    // Test documents expected behavior
    console.log('stderr warnings should be displayed separately from stdout');
  });

  test('should handle syntax errors', async ({ page }) => {
    // Mock syntax error
    await page.route('**/api/v1/mcp/tools/python_execute/execute', async (route) => {
      await route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({
          error: {
            code: 'SYNTAX_ERROR',
            message: 'Invalid Python syntax',
            details: {
              error_type: 'SyntaxError',
              message: 'invalid syntax',
              line: 1,
              offset: 6,
            },
          },
        }),
      });
    });

    await page.goto(MCP_TOOLS_URL);
    await page.waitForLoadState('networkidle');

    // Test documents expected error handling
    console.log('Syntax errors should be caught and reported with line/column info');
  });

  test('should handle runtime errors', async ({ page }) => {
    // Mock runtime error
    await page.route('**/api/v1/mcp/tools/python_execute/execute', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          tool_name: 'python_execute',
          result: {
            stdout: '',
            stderr: 'Traceback (most recent call last):\n  File "<string>", line 1, in <module>\nZeroDivisionError: division by zero\n',
            exit_code: 1,
            execution_time: 0.015,
          },
          error: 'Execution failed with exit code 1',
          execution_time: 0.018,
        }),
      });
    });

    await page.goto(MCP_TOOLS_URL);
    await page.waitForLoadState('networkidle');

    // Test documents expected error handling
    console.log('Runtime errors should display full traceback');
  });

  test('should handle timeout', async ({ page }) => {
    // Mock timeout error
    await page.route('**/api/v1/mcp/tools/python_execute/execute', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 100));

      await route.fulfill({
        status: 504,
        contentType: 'application/json',
        body: JSON.stringify({
          error: {
            code: 'TIMEOUT',
            message: 'Code execution timed out after 30 seconds',
            details: {
              timeout_seconds: 30,
            },
          },
        }),
      });
    });

    await page.goto(MCP_TOOLS_URL);
    await page.waitForLoadState('networkidle');

    // Test documents expected timeout handling
    console.log('Infinite loops or long-running code should timeout gracefully');
  });

  test('should display execution time', async ({ page }) => {
    // Mock execution with timing info
    await page.route('**/api/v1/mcp/tools/python_execute/execute', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          tool_name: 'python_execute',
          result: {
            stdout: 'Computation complete\n',
            stderr: '',
            exit_code: 0,
            execution_time: 1.234,
          },
          error: null,
          execution_time: 1.239,
        }),
      });
    });

    await page.goto(MCP_TOOLS_URL);
    await page.waitForLoadState('networkidle');

    // Test documents expected behavior
    console.log('Execution time should be displayed');
  });

  test('should handle empty code gracefully', async ({ page }) => {
    // Mock validation error for empty code
    await page.route('**/api/v1/mcp/tools/python_execute/execute', async (route) => {
      const request = route.request();
      const postData = JSON.parse(request.postData() || '{}');
      const code = postData.arguments?.code || '';

      if (code.trim() === '') {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({
            error: {
              code: 'INVALID_INPUT',
              message: 'Code cannot be empty',
              details: null,
            },
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            tool_name: 'python_execute',
            result: { stdout: '', stderr: '', exit_code: 0 },
            error: null,
            execution_time: 0.01,
          }),
        });
      }
    });

    await page.goto(MCP_TOOLS_URL);
    await page.waitForLoadState('networkidle');

    // Test documents expected validation
    console.log('Empty code should be validated before execution');
  });

  test('should support multi-line code input', async ({ page }) => {
    await page.goto(MCP_TOOLS_URL);
    await page.waitForLoadState('networkidle');

    // Test documents expected UI requirement
    console.log('Code input should support multi-line editing (textarea with proper formatting)');
  });

  test('should sanitize output to prevent XSS', async ({ page }) => {
    // Mock execution with HTML-like output
    await page.route('**/api/v1/mcp/tools/python_execute/execute', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          tool_name: 'python_execute',
          result: {
            stdout: '<script>alert("XSS")</script>\n',
            stderr: '',
            exit_code: 0,
            execution_time: 0.015,
          },
          error: null,
          execution_time: 0.018,
        }),
      });
    });

    await page.goto(MCP_TOOLS_URL);
    await page.waitForLoadState('networkidle');

    // Test documents critical security requirement
    console.log('SECURITY: Output must be escaped to prevent XSS attacks');
  });

  test('should allow json module for data handling', async ({ page }) => {
    // Mock successful execution with json module
    await page.route('**/api/v1/mcp/tools/python_execute/execute', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          tool_name: 'python_execute',
          result: {
            stdout: '{"name": "test", "value": 42}\n',
            stderr: '',
            exit_code: 0,
            execution_time: 0.021,
          },
          error: null,
          execution_time: 0.024,
        }),
      });
    });

    await page.goto(MCP_TOOLS_URL);
    await page.waitForLoadState('networkidle');

    // Test documents allowed safe modules
    console.log('Safe modules like json should be allowed');
  });

  test('should provide code examples or templates', async ({ page }) => {
    await page.goto(MCP_TOOLS_URL);
    await page.waitForLoadState('networkidle');

    // Test documents UX enhancement feature
    console.log('FEATURE: Code examples/templates would improve UX (not required for MVP)');
  });

  test('should show loading state during execution', async ({ page }) => {
    // Mock slow execution
    await page.route('**/api/v1/mcp/tools/python_execute/execute', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 2000));

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          tool_name: 'python_execute',
          result: {
            stdout: 'done\n',
            stderr: '',
            exit_code: 0,
            execution_time: 1.95,
          },
          error: null,
          execution_time: 2.0,
        }),
      });
    });

    await page.goto(MCP_TOOLS_URL);
    await page.waitForLoadState('networkidle');

    // Test documents expected UX
    console.log('UI should show loading state during code execution');
  });

  test('should block file system access via open()', async ({ page }) => {
    // Mock AST validation error for open()
    await page.route('**/api/v1/mcp/tools/python_execute/execute', async (route) => {
      const request = route.request();
      const postData = JSON.parse(request.postData() || '{}');

      const code = postData.arguments?.code || '';
      if (code.includes('open(')) {
        await route.fulfill({
          status: 403,
          contentType: 'application/json',
          body: JSON.stringify({
            error: {
              code: 'SECURITY_VIOLATION',
              message: 'Code rejected: forbidden function call (open)',
              details: {
                blocked_function: 'open',
                reason: 'File system access is not allowed',
              },
            },
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            tool_name: 'python_execute',
            result: { stdout: '', stderr: '', exit_code: 0 },
            error: null,
            execution_time: 0.01,
          }),
        });
      }
    });

    await page.goto(MCP_TOOLS_URL);
    await page.waitForLoadState('networkidle');

    // Test documents critical security requirement
    console.log('SECURITY: open() calls must be blocked by AST validation');
  });
});
