# Sprint 14 Plan: React Frontend Migration Phase 1

**Sprint Duration:** 2 weeks (14 days)
**Sprint Goal:** Establish modern React frontend foundation with Next.js 14, replacing Gradio UI
**Total Story Points:** 15 SP
**Theme:** Frontend Excellence - Modern React Architecture
**Status:** 🔵 PLANNED

---

## 📋 Executive Summary

Sprint 14 focuses exclusively on **frontend migration** from Gradio to a production-grade React + Next.js application. This sprint establishes the foundation for a modern, maintainable frontend architecture with authentication, streaming, and responsive design.

### Why This Sprint Exists

Sprint 13 was split into two focused sprints to avoid context switching between backend (testing/performance) and frontend (React migration) work. Sprint 14 delivers Phase 1 of the React migration with:

- **Modern Stack**: Next.js 14 (App Router), React 18, TypeScript
- **Production Features**: NextAuth.js authentication, SSE streaming, Tailwind CSS
- **Core UI**: Chat interface, document upload, responsive layout
- **API Integration**: FastAPI backend integration with streaming support

### Key Deliverables

1. ✅ **React Project Setup** - Next.js 14 with TypeScript, ESLint, Prettier
2. ✅ **Chat UI Component** - Message display, input handling, streaming indicators
3. ✅ **SSE Streaming** - Server-Sent Events for real-time LLM responses
4. ✅ **Authentication** - NextAuth.js with JWT tokens and user management
5. ✅ **Tailwind Styling** - Responsive design system with dark mode
6. ✅ **Document Upload** - Multi-file upload with progress tracking

---

## 🎯 Sprint Goals

### Primary Goals (Must-Have)

1. **Replace Gradio UI** with production-ready React frontend
2. **Implement streaming chat** with SSE for real-time responses
3. **Add authentication** with NextAuth.js and JWT integration
4. **Create responsive design** with Tailwind CSS and dark mode support
5. **Enable document upload** with multi-file support and progress indicators

### Secondary Goals (Nice-to-Have)

- Code splitting and lazy loading optimization
- React Query for server state management
- Error boundary components
- Accessibility (WCAG 2.1 AA) compliance

### Success Criteria

- ✅ Next.js application runs on port 3000
- ✅ Chat interface displays messages and handles streaming
- ✅ SSE connection established and streaming functional
- ✅ Authentication working with login/logout flow
- ✅ Document upload supports multiple files with progress
- ✅ Responsive design works on mobile/tablet/desktop
- ✅ Dark mode toggle functional
- ✅ All TypeScript types properly defined (zero `any` types)

---

## 📊 Feature Breakdown

| Feature ID | Feature Name | Story Points | Priority | Status |
|-----------|--------------|--------------|----------|--------|
| **REACT FOUNDATION** |
| 14.1 | React Project Setup (Next.js 14) | 2 SP | 🔴 CRITICAL | 🔵 Planned |
| 14.2 | Basic Chat UI Component | 3 SP | 🔴 CRITICAL | 🔵 Planned |
| **STREAMING & REAL-TIME** |
| 14.3 | Server-Sent Events Streaming | 3 SP | 🔴 CRITICAL | 🔵 Planned |
| **AUTHENTICATION** |
| 14.4 | NextAuth.js Authentication | 3 SP | 🔴 CRITICAL | 🔵 Planned |
| **UI/UX POLISH** |
| 14.5 | Tailwind CSS Styling System | 2 SP | 🟠 HIGH | 🔵 Planned |
| 14.6 | Document Upload UI | 2 SP | 🟠 HIGH | 🔵 Planned |
| **TOTAL** | **15 SP** | | |

---

## 🚀 Feature Details

### Feature 14.1: React Project Setup (Next.js 14) - 2 SP

**Priority:** 🔴 CRITICAL
**Complexity:** Medium
**Dependencies:** None
**Estimated Time:** 1 day

#### Description

Bootstrap Next.js 14 project with App Router, TypeScript, ESLint, Prettier, and project structure. Establish development environment and build pipeline.

#### Technical Requirements

1. **Project Initialization**
   ```bash
   npx create-next-app@latest aegis-rag-frontend
   # Options:
   # - TypeScript: Yes
   # - ESLint: Yes
   # - Tailwind CSS: Yes
   # - App Router: Yes
   # - src/ directory: Yes
   # - Import alias (@/*): Yes
   ```

2. **Project Structure**
   ```
   aegis-rag-frontend/
   ├── src/
   │   ├── app/
   │   │   ├── (auth)/          # Auth routes group
   │   │   │   ├── login/
   │   │   │   └── register/
   │   │   ├── (main)/          # Main app routes group
   │   │   │   ├── chat/
   │   │   │   ├── documents/
   │   │   │   └── settings/
   │   │   ├── api/             # API routes
   │   │   │   └── auth/
   │   │   ├── layout.tsx
   │   │   └── page.tsx
   │   ├── components/
   │   │   ├── ui/              # Reusable UI components
   │   │   ├── chat/            # Chat-specific components
   │   │   ├── documents/       # Document-specific components
   │   │   └── layout/          # Layout components
   │   ├── lib/
   │   │   ├── api/             # API client
   │   │   ├── hooks/           # Custom React hooks
   │   │   ├── utils/           # Utility functions
   │   │   └── types/           # TypeScript types
   │   ├── styles/
   │   │   └── globals.css
   │   └── config/
   │       └── site.ts          # Site configuration
   ├── public/
   ├── .env.local
   ├── .env.example
   ├── next.config.js
   ├── tsconfig.json
   ├── tailwind.config.ts
   ├── postcss.config.js
   ├── .eslintrc.json
   ├── .prettierrc
   └── package.json
   ```

3. **Configuration Files**

**tsconfig.json** (strict TypeScript):
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "forceConsistentCasingInFileNames": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

**next.config.js**:
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  async rewrites() {
    return [
      {
        source: '/api/backend/:path*',
        destination: 'http://localhost:8000/:path*',
      },
    ];
  },
  experimental: {
    serverActions: true,
  },
};

module.exports = nextConfig;
```

**.env.example**:
```bash
# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000

# NextAuth
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=generate-with-openssl-rand-base64-32

# Feature Flags
NEXT_PUBLIC_ENABLE_GRAPH_VIZ=true
NEXT_PUBLIC_ENABLE_MEMORY_PANEL=true
```

4. **Package Dependencies**
   ```json
   {
     "dependencies": {
       "next": "^14.1.0",
       "react": "^18.2.0",
       "react-dom": "^18.2.0",
       "next-auth": "^4.24.5",
       "axios": "^1.6.5",
       "react-query": "^3.39.3",
       "zustand": "^4.5.0",
       "zod": "^3.22.4",
       "react-hook-form": "^7.49.3",
       "lucide-react": "^0.314.0",
       "class-variance-authority": "^0.7.0",
       "clsx": "^2.1.0",
       "tailwind-merge": "^2.2.0"
     },
     "devDependencies": {
       "@types/node": "^20.11.5",
       "@types/react": "^18.2.48",
       "@types/react-dom": "^18.2.18",
       "typescript": "^5.3.3",
       "eslint": "^8.56.0",
       "eslint-config-next": "^14.1.0",
       "prettier": "^3.2.4",
       "prettier-plugin-tailwindcss": "^0.5.11",
       "autoprefixer": "^10.4.17",
       "postcss": "^8.4.33",
       "tailwindcss": "^3.4.1"
     }
   }
   ```

5. **ESLint + Prettier Configuration**

**.eslintrc.json**:
```json
{
  "extends": [
    "next/core-web-vitals",
    "prettier"
  ],
  "rules": {
    "prefer-const": "error",
    "no-console": ["warn", { "allow": ["warn", "error"] }],
    "@typescript-eslint/no-unused-vars": ["error", { "argsIgnorePattern": "^_" }],
    "@typescript-eslint/no-explicit-any": "error"
  }
}
```

**.prettierrc**:
```json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2,
  "useTabs": false,
  "plugins": ["prettier-plugin-tailwindcss"]
}
```

#### Acceptance Criteria

- ✅ `npm run dev` starts development server on port 3000
- ✅ TypeScript compilation successful with strict mode
- ✅ ESLint runs with zero errors
- ✅ Prettier formats all files correctly
- ✅ All environment variables documented in `.env.example`
- ✅ Project structure follows Next.js 14 App Router conventions
- ✅ Hot module reloading functional
- ✅ Build pipeline (`npm run build`) succeeds

#### Implementation Steps

1. Initialize Next.js project with TypeScript
2. Configure ESLint + Prettier with strict rules
3. Set up project folder structure
4. Create configuration files (next.config.js, .env.example)
5. Install core dependencies (axios, react-query, zustand)
6. Create utility functions (cn helper, API client base)
7. Verify development and build pipelines

---

### Feature 14.2: Basic Chat UI Component - 3 SP

**Priority:** 🔴 CRITICAL
**Complexity:** High
**Dependencies:** Feature 14.1
**Estimated Time:** 1.5 days

#### Description

Build core chat interface with message display, input handling, and streaming indicators. Support markdown rendering, code syntax highlighting, and message history.

#### Technical Requirements

1. **Chat Component Structure**

**src/components/chat/ChatInterface.tsx**:
```typescript
'use client';

import { useState, useRef, useEffect } from 'react';
import { Message, ChatState } from '@/lib/types/chat';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { StreamingIndicator } from './StreamingIndicator';

interface ChatInterfaceProps {
  sessionId?: string;
  initialMessages?: Message[];
}

export function ChatInterface({ sessionId, initialMessages = [] }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStreamingMessage, setCurrentStreamingMessage] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentStreamingMessage]);

  const handleSendMessage = async (content: string) => {
    // Add user message
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    // Start streaming (handled in Feature 14.3)
    setIsStreaming(true);
    // ... SSE connection logic
  };

  return (
    <div className="flex h-full flex-col">
      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4">
        <MessageList messages={messages} />

        {/* Streaming Message */}
        {isStreaming && currentStreamingMessage && (
          <div className="mb-4">
            <StreamingIndicator content={currentStreamingMessage} />
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t p-4">
        <ChatInput
          onSend={handleSendMessage}
          disabled={isStreaming}
          placeholder="Ask a question..."
        />
      </div>
    </div>
  );
}
```

2. **Message List Component**

**src/components/chat/MessageList.tsx**:
```typescript
import { Message } from '@/lib/types/chat';
import { MessageBubble } from './MessageBubble';

interface MessageListProps {
  messages: Message[];
}

export function MessageList({ messages }: MessageListProps) {
  return (
    <div className="space-y-4">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
    </div>
  );
}
```

3. **Message Bubble Component**

**src/components/chat/MessageBubble.tsx**:
```typescript
import { Message } from '@/lib/types/chat';
import { cn } from '@/lib/utils';
import { MarkdownRenderer } from './MarkdownRenderer';
import { User, Bot } from 'lucide-react';

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div
      className={cn(
        'flex items-start gap-3',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
          isUser ? 'bg-blue-500' : 'bg-gray-700'
        )}
      >
        {isUser ? (
          <User className="h-5 w-5 text-white" />
        ) : (
          <Bot className="h-5 w-5 text-white" />
        )}
      </div>

      {/* Message Content */}
      <div
        className={cn(
          'max-w-[80%] rounded-lg px-4 py-2',
          isUser
            ? 'bg-blue-500 text-white'
            : 'bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-100'
        )}
      >
        <MarkdownRenderer content={message.content} />

        {/* Timestamp */}
        <div
          className={cn(
            'mt-1 text-xs',
            isUser ? 'text-blue-100' : 'text-gray-500 dark:text-gray-400'
          )}
        >
          {new Date(message.timestamp).toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
}
```

4. **Chat Input Component**

**src/components/chat/ChatInput.tsx**:
```typescript
'use client';

import { useState, KeyboardEvent } from 'react';
import { Send } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({ onSend, disabled, placeholder }: ChatInputProps) {
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (input.trim() && !disabled) {
      onSend(input.trim());
      setInput('');
    }
  };

  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex items-end gap-2">
      <textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyPress={handleKeyPress}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
        className="flex-1 resize-none rounded-lg border border-gray-300 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800"
      />
      <Button
        onClick={handleSend}
        disabled={disabled || !input.trim()}
        className="h-10 w-10 shrink-0"
      >
        <Send className="h-5 w-5" />
      </Button>
    </div>
  );
}
```

5. **Markdown Renderer**

**src/components/chat/MarkdownRenderer.tsx**:
```typescript
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface MarkdownRendererProps {
  content: string;
}

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <ReactMarkdown
      components={{
        code({ node, inline, className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || '');
          return !inline && match ? (
            <SyntaxHighlighter
              style={vscDarkPlus}
              language={match[1]}
              PreTag="div"
              {...props}
            >
              {String(children).replace(/\n$/, '')}
            </SyntaxHighlighter>
          ) : (
            <code className="rounded bg-gray-200 px-1 dark:bg-gray-700" {...props}>
              {children}
            </code>
          );
        },
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
```

6. **Type Definitions**

**src/lib/types/chat.ts**:
```typescript
export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  metadata?: {
    sources?: string[];
    tokens?: number;
    model?: string;
  };
}

export interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  currentStreamingMessage: string;
  sessionId: string | null;
  error: string | null;
}
```

#### Acceptance Criteria

- ✅ Chat interface displays user and assistant messages
- ✅ Message input supports multiline text (Shift+Enter)
- ✅ Enter key sends message (without Shift)
- ✅ Markdown rendering works (bold, italic, code blocks)
- ✅ Code syntax highlighting functional
- ✅ Auto-scroll to latest message
- ✅ Message timestamps displayed
- ✅ Responsive design (mobile/tablet/desktop)
- ✅ Dark mode support

---

### Feature 14.3: Server-Sent Events Streaming - 3 SP

**Priority:** 🔴 CRITICAL
**Complexity:** High
**Dependencies:** Feature 14.2
**Estimated Time:** 1.5 days

#### Description

Implement SSE connection to FastAPI backend for real-time streaming of LLM responses. Handle connection errors, reconnection, and streaming state management.

#### Technical Requirements

1. **SSE Client Hook**

**src/lib/hooks/useSSE.ts**:
```typescript
import { useEffect, useRef, useState } from 'react';

interface UseSSEOptions {
  url: string;
  onMessage: (data: string) => void;
  onError?: (error: Event) => void;
  onComplete?: () => void;
}

export function useSSE({ url, onMessage, onError, onComplete }: UseSSEOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setIsConnected(true);
    };

    eventSource.onmessage = (event) => {
      const data = event.data;

      // Check for completion signal
      if (data === '[DONE]') {
        onComplete?.();
        eventSource.close();
        setIsConnected(false);
        return;
      }

      onMessage(data);
    };

    eventSource.onerror = (error) => {
      onError?.(error);
      eventSource.close();
      setIsConnected(false);
    };

    return () => {
      eventSource.close();
      setIsConnected(false);
    };
  }, [url, onMessage, onError, onComplete]);

  const close = () => {
    eventSourceRef.current?.close();
    setIsConnected(false);
  };

  return { isConnected, close };
}
```

2. **Chat API Client**

**src/lib/api/chat.ts**:
```typescript
import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface ChatRequest {
  query: string;
  session_id?: string;
  rag_mode?: 'lightrag' | 'graphiti' | 'hybrid';
  stream?: boolean;
}

export interface ChatResponse {
  answer: string;
  sources: string[];
  session_id: string;
  metadata: {
    tokens: number;
    model: string;
    duration_ms: number;
  };
}

export const chatAPI = {
  /**
   * Send a chat message with streaming support
   */
  sendMessage: async (request: ChatRequest): Promise<ChatResponse> => {
    const response = await axios.post<ChatResponse>(`${API_URL}/api/v1/chat`, request);
    return response.data;
  },

  /**
   * Get SSE streaming URL for a chat message
   */
  getStreamingURL: (request: ChatRequest): string => {
    const params = new URLSearchParams({
      query: request.query,
      stream: 'true',
      ...(request.session_id && { session_id: request.session_id }),
      ...(request.rag_mode && { rag_mode: request.rag_mode }),
    });
    return `${API_URL}/api/v1/chat/stream?${params.toString()}`;
  },
};
```

3. **Updated Chat Interface with SSE**

**src/components/chat/ChatInterface.tsx** (updated):
```typescript
'use client';

import { useState, useRef, useEffect } from 'react';
import { Message } from '@/lib/types/chat';
import { chatAPI } from '@/lib/api/chat';
import { useSSE } from '@/lib/hooks/useSSE';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { StreamingIndicator } from './StreamingIndicator';

export function ChatInterface({ sessionId: initialSessionId }: { sessionId?: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStreamingMessage, setCurrentStreamingMessage] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(initialSessionId || null);
  const [streamingURL, setStreamingURL] = useState<string | null>(null);

  // SSE hook
  useSSE({
    url: streamingURL || '',
    onMessage: (data) => {
      setCurrentStreamingMessage((prev) => prev + data);
    },
    onComplete: () => {
      // Add completed assistant message
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: currentStreamingMessage,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);

      // Reset streaming state
      setIsStreaming(false);
      setCurrentStreamingMessage('');
      setStreamingURL(null);
    },
    onError: (error) => {
      console.error('SSE error:', error);
      setIsStreaming(false);
      setStreamingURL(null);
    },
  });

  const handleSendMessage = async (content: string) => {
    // Add user message
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    // Start streaming
    setIsStreaming(true);
    setCurrentStreamingMessage('');

    const url = chatAPI.getStreamingURL({
      query: content,
      session_id: sessionId || undefined,
      rag_mode: 'hybrid',
      stream: true,
    });

    setStreamingURL(url);
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto p-4">
        <MessageList messages={messages} />

        {isStreaming && currentStreamingMessage && (
          <div className="mb-4">
            <StreamingIndicator content={currentStreamingMessage} />
          </div>
        )}
      </div>

      <div className="border-t p-4">
        <ChatInput
          onSend={handleSendMessage}
          disabled={isStreaming}
          placeholder="Ask a question..."
        />
      </div>
    </div>
  );
}
```

4. **Streaming Indicator Component**

**src/components/chat/StreamingIndicator.tsx**:
```typescript
import { MarkdownRenderer } from './MarkdownRenderer';
import { Loader2 } from 'lucide-react';

interface StreamingIndicatorProps {
  content: string;
}

export function StreamingIndicator({ content }: StreamingIndicatorProps) {
  return (
    <div className="flex items-start gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-700">
        <Loader2 className="h-5 w-5 animate-spin text-white" />
      </div>

      <div className="max-w-[80%] rounded-lg bg-gray-100 px-4 py-2 dark:bg-gray-800">
        <MarkdownRenderer content={content} />
        <div className="mt-1 text-xs text-gray-500">Streaming...</div>
      </div>
    </div>
  );
}
```

#### Backend API Endpoint (Reference)

**src/api/routes/chat.py** (already exists in backend):
```python
@router.get("/chat/stream")
async def chat_stream(
    query: str,
    session_id: Optional[str] = None,
    rag_mode: RAGMode = RAGMode.HYBRID,
):
    """Stream chat responses via Server-Sent Events."""

    async def event_generator():
        try:
            # Initialize RAG pipeline
            pipeline = get_rag_pipeline(rag_mode)

            # Stream response
            async for chunk in pipeline.stream(query, session_id):
                yield f"data: {chunk}\n\n"

            # Signal completion
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

#### Acceptance Criteria

- ✅ SSE connection established to FastAPI backend
- ✅ Streaming responses displayed in real-time
- ✅ Streaming indicator shows during generation
- ✅ Connection errors handled gracefully
- ✅ Completion signal (`[DONE]`) processed correctly
- ✅ Multiple streaming sessions don't interfere
- ✅ Connection closed on component unmount
- ✅ Retry logic for failed connections

---

### Feature 14.4: NextAuth.js Authentication - 3 SP

**Priority:** 🔴 CRITICAL
**Complexity:** High
**Dependencies:** Feature 14.1
**Estimated Time:** 1.5 days

#### Description

Implement authentication with NextAuth.js, JWT tokens, and integration with FastAPI backend. Support login, logout, and protected routes.

#### Technical Requirements

1. **NextAuth Configuration**

**src/app/api/auth/[...nextauth]/route.ts**:
```typescript
import NextAuth, { NextAuthOptions } from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';
import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: 'Credentials',
      credentials: {
        username: { label: 'Username', type: 'text' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        if (!credentials?.username || !credentials?.password) {
          return null;
        }

        try {
          // Authenticate with FastAPI backend
          const response = await axios.post(`${API_URL}/api/v1/auth/login`, {
            username: credentials.username,
            password: credentials.password,
          });

          const { access_token, user } = response.data;

          if (access_token && user) {
            return {
              id: user.id,
              name: user.username,
              email: user.email,
              accessToken: access_token,
            };
          }

          return null;
        } catch (error) {
          console.error('Authentication error:', error);
          return null;
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.accessToken = user.accessToken;
        token.id = user.id;
      }
      return token;
    },
    async session({ session, token }) {
      session.user.id = token.id as string;
      session.accessToken = token.accessToken as string;
      return session;
    },
  },
  pages: {
    signIn: '/login',
    error: '/login',
  },
  session: {
    strategy: 'jwt',
    maxAge: 24 * 60 * 60, // 24 hours
  },
  secret: process.env.NEXTAUTH_SECRET,
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
```

2. **Session Provider**

**src/app/providers.tsx**:
```typescript
'use client';

import { SessionProvider } from 'next-auth/react';
import { ReactNode } from 'react';

export function Providers({ children }: { children: ReactNode }) {
  return <SessionProvider>{children}</SessionProvider>;
}
```

**src/app/layout.tsx** (updated):
```typescript
import { Providers } from './providers';

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

3. **Login Page**

**src/app/(auth)/login/page.tsx**:
```typescript
'use client';

import { signIn } from 'next-auth/react';
import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    const result = await signIn('credentials', {
      username,
      password,
      redirect: false,
    });

    if (result?.error) {
      setError('Invalid username or password');
      setIsLoading(false);
    } else {
      router.push('/chat');
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-100 dark:bg-gray-900">
      <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-lg dark:bg-gray-800">
        <h1 className="mb-6 text-2xl font-bold">AEGIS RAG Login</h1>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="mt-1 w-full rounded-lg border px-4 py-2"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-lg border px-4 py-2"
              required
            />
          </div>

          {error && (
            <div className="rounded-lg bg-red-100 p-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <Button type="submit" disabled={isLoading} className="w-full">
            {isLoading ? 'Logging in...' : 'Login'}
          </Button>
        </form>
      </div>
    </div>
  );
}
```

4. **Protected Route Middleware**

**src/middleware.ts**:
```typescript
import { withAuth } from 'next-auth/middleware';

export default withAuth({
  callbacks: {
    authorized: ({ token }) => !!token,
  },
  pages: {
    signIn: '/login',
  },
});

export const config = {
  matcher: ['/chat/:path*', '/documents/:path*', '/settings/:path*'],
};
```

5. **Authenticated API Client**

**src/lib/api/client.ts**:
```typescript
import axios from 'axios';
import { getSession } from 'next-auth/react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_URL,
});

// Add auth token to all requests
apiClient.interceptors.request.use(async (config) => {
  const session = await getSession();
  if (session?.accessToken) {
    config.headers.Authorization = `Bearer ${session.accessToken}`;
  }
  return config;
});

// Handle 401 errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

#### Acceptance Criteria

- ✅ Login page functional with username/password
- ✅ Successful login redirects to /chat
- ✅ Failed login shows error message
- ✅ JWT token stored in session
- ✅ Protected routes require authentication
- ✅ Unauthenticated users redirected to /login
- ✅ API requests include Bearer token
- ✅ Logout functionality works
- ✅ Session expires after 24 hours

---

### Feature 14.5: Tailwind CSS Styling System - 2 SP

**Priority:** 🟠 HIGH
**Complexity:** Medium
**Dependencies:** Feature 14.1, 14.2
**Estimated Time:** 1 day

#### Description

Implement comprehensive Tailwind CSS design system with dark mode support, responsive layouts, and reusable UI components.

#### Technical Requirements

1. **Tailwind Configuration**

**tailwind.config.ts**:
```typescript
import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: ['class'],
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
};

export default config;
```

2. **Global Styles**

**src/styles/globals.css**:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;

    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;

    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;

    --primary: 222.2 47.4% 11.2%;
    --primary-foreground: 210 40% 98%;

    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;

    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;

    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;

    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;

    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 222.2 84% 4.9%;

    --radius: 0.5rem;
  }

  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;

    --card: 222.2 84% 4.9%;
    --card-foreground: 210 40% 98%;

    --popover: 222.2 84% 4.9%;
    --popover-foreground: 210 40% 98%;

    --primary: 210 40% 98%;
    --primary-foreground: 222.2 47.4% 11.2%;

    --secondary: 217.2 32.6% 17.5%;
    --secondary-foreground: 210 40% 98%;

    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 65.1%;

    --accent: 217.2 32.6% 17.5%;
    --accent-foreground: 210 40% 98%;

    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 210 40% 98%;

    --border: 217.2 32.6% 17.5%;
    --input: 217.2 32.6% 17.5%;
    --ring: 212.7 26.8% 83.9%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

3. **Dark Mode Toggle**

**src/components/ui/theme-toggle.tsx**:
```typescript
'use client';

import { Moon, Sun } from 'lucide-react';
import { useTheme } from 'next-themes';
import { Button } from './button';

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
    >
      <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
      <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
      <span className="sr-only">Toggle theme</span>
    </Button>
  );
}
```

4. **Button Component** (shadcn/ui style)

**src/components/ui/button.tsx**:
```typescript
import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
        secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        link: 'text-primary underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 rounded-md px-3',
        lg: 'h-11 rounded-md px-8',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = 'Button';

export { Button, buttonVariants };
```

#### Acceptance Criteria

- ✅ Dark mode toggle functional
- ✅ Theme persists across page reloads
- ✅ All components support dark mode
- ✅ Responsive design works on all screen sizes
- ✅ Color system consistent across app
- ✅ Accessibility (WCAG 2.1 AA) compliance
- ✅ Smooth transitions between themes

---

### Feature 14.6: Document Upload UI - 2 SP

**Priority:** 🟠 HIGH
**Complexity:** Medium
**Dependencies:** Feature 14.1, 14.4
**Estimated Time:** 1 day

#### Description

Build document upload interface with drag-and-drop, multi-file support, progress tracking, and error handling.

#### Technical Requirements

1. **Document Upload Component**

**src/components/documents/DocumentUpload.tsx**:
```typescript
'use client';

import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, File, X, CheckCircle, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { documentAPI } from '@/lib/api/documents';

interface UploadedFile {
  file: File;
  status: 'pending' | 'uploading' | 'success' | 'error';
  progress: number;
  error?: string;
}

export function DocumentUpload() {
  const [files, setFiles] = useState<UploadedFile[]>([]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.map((file) => ({
      file,
      status: 'pending' as const,
      progress: 0,
    }));
    setFiles((prev) => [...prev, ...newFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    multiple: true,
  });

  const handleUpload = async () => {
    const pendingFiles = files.filter((f) => f.status === 'pending');

    for (const uploadFile of pendingFiles) {
      try {
        // Update status to uploading
        setFiles((prev) =>
          prev.map((f) =>
            f.file === uploadFile.file
              ? { ...f, status: 'uploading' }
              : f
          )
        );

        // Upload with progress tracking
        await documentAPI.uploadDocument(uploadFile.file, (progress) => {
          setFiles((prev) =>
            prev.map((f) =>
              f.file === uploadFile.file ? { ...f, progress } : f
            )
          );
        });

        // Mark as success
        setFiles((prev) =>
          prev.map((f) =>
            f.file === uploadFile.file
              ? { ...f, status: 'success', progress: 100 }
              : f
          )
        );
      } catch (error) {
        // Mark as error
        setFiles((prev) =>
          prev.map((f) =>
            f.file === uploadFile.file
              ? {
                  ...f,
                  status: 'error',
                  error: error instanceof Error ? error.message : 'Upload failed',
                }
              : f
          )
        );
      }
    }
  };

  const removeFile = (fileToRemove: File) => {
    setFiles((prev) => prev.filter((f) => f.file !== fileToRemove));
  };

  return (
    <div className="space-y-4">
      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`rounded-lg border-2 border-dashed p-12 text-center transition-colors ${
          isDragActive
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-950'
            : 'border-gray-300 hover:border-gray-400 dark:border-gray-600'
        }`}
      >
        <input {...getInputProps()} />
        <Upload className="mx-auto h-12 w-12 text-gray-400" />
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          {isDragActive
            ? 'Drop files here...'
            : 'Drag & drop files here, or click to select'}
        </p>
        <p className="mt-1 text-xs text-gray-500">
          Supported: PDF, TXT, DOCX (max 10MB)
        </p>
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((uploadFile) => (
            <FileItem
              key={uploadFile.file.name}
              uploadFile={uploadFile}
              onRemove={() => removeFile(uploadFile.file)}
            />
          ))}
        </div>
      )}

      {/* Upload Button */}
      {files.some((f) => f.status === 'pending') && (
        <Button onClick={handleUpload} className="w-full">
          Upload {files.filter((f) => f.status === 'pending').length} file(s)
        </Button>
      )}
    </div>
  );
}

function FileItem({
  uploadFile,
  onRemove,
}: {
  uploadFile: UploadedFile;
  onRemove: () => void;
}) {
  const { file, status, progress, error } = uploadFile;

  return (
    <div className="flex items-center gap-3 rounded-lg border p-3">
      <File className="h-5 w-5 text-gray-400" />

      <div className="flex-1">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">{file.name}</span>
          <span className="text-xs text-gray-500">
            {(file.size / 1024 / 1024).toFixed(2)} MB
          </span>
        </div>

        {/* Progress Bar */}
        {status === 'uploading' && (
          <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-gray-200">
            <div
              className="h-full bg-blue-500 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}

        {/* Error Message */}
        {status === 'error' && (
          <p className="mt-1 text-xs text-red-600">{error}</p>
        )}
      </div>

      {/* Status Icon */}
      {status === 'success' && (
        <CheckCircle className="h-5 w-5 text-green-500" />
      )}
      {status === 'error' && (
        <AlertCircle className="h-5 w-5 text-red-500" />
      )}
      {status === 'pending' && (
        <button onClick={onRemove}>
          <X className="h-5 w-5 text-gray-400 hover:text-gray-600" />
        </button>
      )}
    </div>
  );
}
```

2. **Document API Client**

**src/lib/api/documents.ts**:
```typescript
import { apiClient } from './client';

export interface UploadResponse {
  filename: string;
  chunks_created: number;
  status: string;
}

export const documentAPI = {
  /**
   * Upload a document with progress tracking
   */
  uploadDocument: async (
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<UploadResponse>(
      '/api/v1/documents/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const progress = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            onProgress?.(progress);
          }
        },
      }
    );

    return response.data;
  },

  /**
   * Get list of uploaded documents
   */
  listDocuments: async (): Promise<string[]> => {
    const response = await apiClient.get<string[]>('/api/v1/documents');
    return response.data;
  },
};
```

#### Acceptance Criteria

- ✅ Drag-and-drop file upload functional
- ✅ Click to select files works
- ✅ Multiple files can be uploaded simultaneously
- ✅ Progress bars update during upload
- ✅ Success/error states displayed correctly
- ✅ File type validation (PDF, TXT, DOCX only)
- ✅ File size validation (max 10MB)
- ✅ Files can be removed before upload
- ✅ Responsive design on all screen sizes

---

## 📅 Sprint Timeline

### Week 1: React Foundation & Streaming (9 SP)

**Days 1-2**: Feature 14.1 - React Project Setup (2 SP)
- Initialize Next.js 14 project
- Configure TypeScript, ESLint, Prettier
- Set up project structure and dependencies

**Days 3-4**: Feature 14.2 - Basic Chat UI (3 SP)
- Build chat interface components
- Implement message display and input
- Add markdown rendering

**Days 5-6**: Feature 14.3 - SSE Streaming (3 SP)
- Implement SSE client hook
- Connect to FastAPI backend
- Test streaming functionality

**Day 7**: Feature 14.4 - Authentication (1 SP - start)
- Set up NextAuth.js configuration

### Week 2: Authentication & UI Polish (6 SP)

**Days 8-9**: Feature 14.4 - Authentication (2 SP - complete)
- Build login page
- Implement protected routes
- Test authentication flow

**Days 10-11**: Feature 14.5 - Tailwind Styling (2 SP)
- Configure Tailwind design system
- Implement dark mode
- Style all components

**Days 12-13**: Feature 14.6 - Document Upload (2 SP)
- Build upload interface
- Implement drag-and-drop
- Add progress tracking

**Day 14**: Testing & Deployment
- Integration testing
- Bug fixes
- Sprint review preparation

---

## 🧪 Testing Strategy

### Component Testing (Jest + React Testing Library)

**Test Coverage Requirements:**
- All components: 80%+ coverage
- Critical paths: 100% coverage
- Edge cases: Error states, loading states, empty states

**Example Test**:
```typescript
// src/components/chat/__tests__/ChatInterface.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatInterface } from '../ChatInterface';

describe('ChatInterface', () => {
  it('sends a message when Enter is pressed', async () => {
    render(<ChatInterface />);

    const input = screen.getByPlaceholderText('Ask a question...');
    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.keyPress(input, { key: 'Enter', code: 13, charCode: 13 });

    await waitFor(() => {
      expect(screen.getByText('Hello')).toBeInTheDocument();
    });
  });

  it('displays streaming indicator during response', async () => {
    render(<ChatInterface />);

    // Trigger message send
    const input = screen.getByPlaceholderText('Ask a question...');
    fireEvent.change(input, { target: { value: 'Test' } });
    fireEvent.keyPress(input, { key: 'Enter', code: 13, charCode: 13 });

    await waitFor(() => {
      expect(screen.getByText('Streaming...')).toBeInTheDocument();
    });
  });
});
```

### E2E Testing (Playwright)

**Test Scenarios:**
1. Complete chat flow (login → send message → receive response)
2. Document upload flow (login → upload → verify ingestion)
3. Authentication flow (login → protected route → logout)
4. Dark mode toggle
5. Responsive design (mobile/tablet/desktop)

**Example E2E Test**:
```typescript
// e2e/chat.spec.ts
import { test, expect } from '@playwright/test';

test('complete chat flow', async ({ page }) => {
  // Login
  await page.goto('http://localhost:3000/login');
  await page.fill('input[type="text"]', 'testuser');
  await page.fill('input[type="password"]', 'password123');
  await page.click('button[type="submit"]');

  // Wait for redirect to chat
  await expect(page).toHaveURL('http://localhost:3000/chat');

  // Send message
  await page.fill('textarea', 'What is AEGIS RAG?');
  await page.press('textarea', 'Enter');

  // Verify message sent
  await expect(page.locator('text=What is AEGIS RAG?')).toBeVisible();

  // Wait for streaming response
  await expect(page.locator('text=Streaming...')).toBeVisible();

  // Verify response received
  await expect(page.locator('text=AEGIS RAG is')).toBeVisible({ timeout: 10000 });
});
```

---

## 📊 Success Metrics

### Performance Targets

- **Time to Interactive (TTI)**: < 2s
- **First Contentful Paint (FCP)**: < 1s
- **Largest Contentful Paint (LCP)**: < 2.5s
- **Cumulative Layout Shift (CLS)**: < 0.1
- **SSE Latency**: < 100ms (first chunk)

### Quality Metrics

- **TypeScript Coverage**: 100% (zero `any` types)
- **Test Coverage**: 80%+ (components), 70%+ (overall)
- **Accessibility Score**: 95+ (Lighthouse)
- **ESLint Errors**: 0
- **Bundle Size**: < 500KB (main bundle)

### User Experience

- ✅ Chat interface responds in < 200ms
- ✅ Streaming updates appear in real-time (< 100ms latency)
- ✅ Dark mode toggle instant (no flash)
- ✅ File upload progress updates smoothly
- ✅ Mobile-responsive (works on 320px+ screens)

---

## 🔄 Integration with Backend

### API Endpoints Required (Already Implemented)

1. **POST /api/v1/auth/login** - User authentication
2. **GET /api/v1/chat/stream** - SSE streaming chat
3. **POST /api/v1/documents/upload** - Document upload
4. **GET /api/v1/documents** - List documents

### Environment Variables

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=<generate-with-openssl>
```

---

## 🚧 Known Limitations & Future Work

### Sprint 14 Limitations

1. **No Graph Visualization** - Deferred to Sprint 15
2. **No Memory Panel** - Deferred to Sprint 15
3. **No Advanced Settings** - Deferred to Sprint 15
4. **Basic Authentication** - No OAuth/SSO yet
5. **No Offline Support** - PWA features deferred

### Planned for Sprint 15 (React Migration Phase 2)

- Feature 15.1: Graph Visualization (vis.js integration)
- Feature 15.2: Memory Panel (3-layer display)
- Feature 15.3: Advanced Settings (RAG mode, LLM selection)
- Feature 15.4: Session History (past conversations)
- Feature 15.5: Export Functionality (PDF, JSON)

---

## 📝 Definition of Done

### Feature-Level DoD

- ✅ Code implemented and passes TypeScript compilation
- ✅ Unit tests written and passing (80%+ coverage)
- ✅ E2E tests written and passing
- ✅ ESLint/Prettier errors resolved
- ✅ Component documented (JSDoc comments)
- ✅ Responsive design verified (mobile/tablet/desktop)
- ✅ Dark mode support verified
- ✅ Accessibility checked (keyboard navigation, ARIA labels)
- ✅ Code reviewed and approved

### Sprint-Level DoD

- ✅ All 6 features completed
- ✅ 15 SP delivered
- ✅ Integration tests passing
- ✅ Performance targets met (TTI < 2s, FCP < 1s)
- ✅ No critical bugs
- ✅ Documentation updated (README, deployment guide)
- ✅ Sprint review presentation prepared
- ✅ Deployment to staging environment successful

---

## 🎯 Sprint Goals Recap

By the end of Sprint 14, we will have:

1. ✅ **Modern React Frontend** - Next.js 14 application replacing Gradio UI
2. ✅ **Real-Time Streaming** - SSE-powered chat with LLM responses
3. ✅ **User Authentication** - NextAuth.js with JWT tokens
4. ✅ **Professional UI/UX** - Tailwind CSS design system with dark mode
5. ✅ **Document Upload** - Multi-file upload with progress tracking
6. ✅ **Production-Ready** - TypeScript, ESLint, testing, responsive design

**Next Sprint Preview**: Sprint 15 will focus on Phase 2 features (graph visualization, memory panel, advanced settings) and performance optimization.

---

## 📞 Support & Resources

- **Next.js 14 Docs**: https://nextjs.org/docs
- **NextAuth.js Docs**: https://next-auth.js.org
- **Tailwind CSS Docs**: https://tailwindcss.com/docs
- **React Query Docs**: https://tanstack.com/query/latest
- **Playwright Docs**: https://playwright.dev

---

**Status**: 🔵 PLANNED
**Created**: 2025-10-22
**Sprint Start**: TBD (after Sprint 13 completion)
**Sprint End**: TBD (2 weeks after start)
