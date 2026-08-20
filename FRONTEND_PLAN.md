# IRIS Frontend Architecture & UI Specification (Phase 5.0 & Beyond)

> **Motto:** *Boring architecture, strict contracts, excellent citation UX.*

---

## 🎨 1. Design System, Typography & Color Palette

IRIS uses a calm, enterprise-grade legal/document intelligence aesthetic with high contrast, crisp typography, and accessible interactive states.

### 1.1 Typography & Fonts
* **Primary UI & Body Font:** **Manrope**
  * **Source:** [Google Fonts (Manrope)](https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&display=swap)
  * **Weights:** `400` (Regular), `500` (Medium), `600` (SemiBold), `700` (Bold)
  * **CSS Variable:** `--default-font-family: 'Manrope', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;`
* **Display / Brand Font:** **ClashGrotesk** (or Manrope Bold fallback)
  * **Weights:** `500` (Medium), `600` (Semibold), `700` (Bold)
* **Code / Monospace:** `ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`
* **Iconography:** **Google Material Symbols Outlined** (via reusable `<MaterialIcon name="..." />` or Lucide React icons matching shadcn/ui primitives).

---

### 1.2 Theme Configuration (Radix UI / Tailwind / shadcn)

```tsx
<Theme
  accentColor="jade"           // Base fallback accent
  grayColor="olive"            // Warm gray scale with subtle olive undertone
  radius="medium"              // Clean, professional border radius (6px-8px)
  appearance="auto"            // Light / Dark mode auto system preference
  data-accent-color="emerald"  // Custom overridden emerald palette
/>
```

---

### 1.3 Exact Color Palettes (Custom Emerald Scale — Base: `#047857`)

#### **Light Mode Palette**
| Token | Hex Code | UI Purpose / Component Target |
| :--- | :--- | :--- |
| `--emerald-1` (`--accent-1`) | `#f5fefb` | Subtle tinted canvas / background / secondary panels |
| `--emerald-2` (`--accent-2`) | `#edfdf8` | Elevated card & container backgrounds |
| `--emerald-3` (`--accent-3`) | `#d4f7eb` | Hover states, selected table rows, subtle badges |
| `--emerald-4` (`--accent-4`) | `#bbf0dd` | Active / pressed button states, highlighted chips |
| `--emerald-5` (`--accent-5`) | `#9fe7cd` | Subtle borders on cards and containers |
| `--emerald-6` (`--accent-6`) | `#7edabb` | Interactive borders on inputs and controls |
| `--emerald-7` (`--accent-7`) | `#53c9a4` | High-contrast borders, focus rings |
| `--emerald-8` (`--accent-8`) | `#12b589` | Active tab indicators, primary status dots |
| `--emerald-9` (`--accent-9`) | `#047857` | **Primary solid button fill**, active badges, key CTAs |
| `--emerald-10` (`--accent-10`) | `#10674C` | Primary button hover / active pressed state |
| `--emerald-11` (`--accent-11`) | `#035e44` | High-readability accent text, icon highlights |
| `--emerald-12` (`--accent-12`) | `#0f3d2c` | High-contrast heading text, bold emphasis |
| `--page-background` | `#dcdcdc` | Neutral page backdrop (outer frame) |
| `--file-icon-fill` | `#ffffff` | Document preview icon background |

#### **Dark Mode Palette**
| Token | Hex Code | UI Purpose / Component Target |
| :--- | :--- | :--- |
| `--emerald-1` (`--accent-1`) | `#0d1512` | Deepest tinted dark canvas / base card background |
| `--emerald-2` (`--accent-2`) | `#0f1f1a` | Dark elevated container / modal background |
| `--emerald-3` (`--accent-3`) | `#0c3126` | Dark mode hover background |
| `--emerald-4` (`--accent-4`) | `#063f31` | Dark mode active / pressed background |
| `--emerald-5` (`--accent-5`) | `#084A35` | Subtle dark borders on containers |
| `--emerald-6` (`--accent-6`) | `#145c49` | Interactive borders on dark controls |
| `--emerald-7` (`--accent-7`) | `#1e6d58` | Strong dark borders |
| `--emerald-8` (`--accent-8`) | `#268169` | Dark mode focus indicators |
| `--emerald-9` (`--accent-9`) | `#047857` | Primary solid button fill (consistent brand emerald) |
| `--emerald-10` (`--accent-10`) | `#17906c` | Hover state on dark primary button |
| `--emerald-11` (`--accent-11`) | `#3dd9a0` | High-visibility light-emerald text & icons |
| `--emerald-12` (`--accent-12`) | `#EEEEEE` | High-contrast heading text in dark mode |
| `--page-background` | `#111113` | Deep dark page backdrop |
| `--file-icon-fill` | `#212225` | Dark document preview icon background |
| `--emerald-indicator` | `#3dd9a0` | Glowing status pill / progress indicator |

---

### 1.4 Mode-Specific Modality Palettes

For multi-modal queries and visual distinctions:

| Search / Query Mode | Radix Palette Tokens | Purpose / Accent Usage |
| :--- | :--- | :--- |
| **Document Search Mode** | Emerald (`--emerald-9`, `--emerald-11`, `--emerald-3`) | Standard document RAG & legal search |
| **Chat Mode** | Iris / Purple (`--iris-9`, `--iris-11`, `--iris-a3`) | Conversational turns & synthesis answers |
| **Web Search Mode** | Orange (`--orange-9`, `--orange-11`, `--orange-a4`) | External / live web search citations |
| **Vision / Image Mode** | Blue (`--blue-9`, `--blue-11`, `--blue-3`) | VLM figure analysis & diagram bounding boxes |

---

## 🏛️ 2. Core Architecture & Folder Structure

IRIS Phase 5.0 utilizes **Page-Level Resource Co-Location** in Next.js (App Router).

```text
frontend/
├── app/
│   ├── (auth)/
│   │   └── sign-in/
│   │       ├── page.tsx
│   │       ├── auth-form.tsx
│   │       └── auth.schemas.ts
│   ├── (app)/
│   │   ├── layout.tsx                # App sidebar, navigation, theme provider
│   │   ├── chat/                     # Main Product Surface
│   │   │   ├── page.tsx              # URL query-param parser & main layout mount
│   │   │   ├── api.ts                # Calls /query, /search, /sessions
│   │   │   ├── schemas.ts            # Zod schemas for query/chat
│   │   │   ├── store.ts              # Zustand store for local UI state
│   │   │   └── components/
│   │   │       ├── ChatPanel.tsx     # Message list + chat input
│   │   │       ├── MessageBubble.tsx # Answer renderer + citation pills
│   │   │       ├── PdfPanel.tsx      # PDF.js canvas + navigation controls
│   │   │       ├── BboxOverlay.tsx   # Normalized coordinate highlight layer
│   │   │       ├── CitationList.tsx  # Drawer / bottom list of cited chunks
│   │   │       └── ResizableSplit.tsx# Drag-to-resize split view
│   │   └── documents/
│   │       ├── page.tsx              # Uploads & document status list
│   │       ├── api.ts                # Upload triggers & status polling
│   │       ├── schemas.ts            # Document schemas
│   │       └── components/
│   │           ├── UploadDropzone.tsx
│   │           └── DocStatusTable.tsx
├── components/
│   ├── ui/                           # Reusable shadcn/ui + Radix primitives (Button, Dialog, etc.)
│   └── layout/                       # Header, Sidebar, UserMenu
├── lib/
│   ├── api/
│   │   ├── client.ts                 # Axios / Fetch client with X-Firebase-Token injection
│   │   ├── errors.ts                 # Normalized ApiError mapping
│   │   └── urls.ts                   # Signed URL resolver & caching
│   ├── auth/
│   │   ├── firebase.ts               # Firebase Client SDK init
│   │   └── token.ts                  # ID token getter & silent refresh
│   └── validation/
│       └── ids.ts                    # Regex validators (doc_id, session_id)
```

---

## 🧭 3. URL State vs. Security State (Query Params Pattern)

### 3.1 Flat Routing with Query Parameters
Instead of deeply nested routes (e.g. `/chat/[sessionId]/doc/[docId]`), the entire split-screen state is stored in query parameters:

```text
/chat?sessionId=s_123&docId=doc_456&page=14&citationId=c_789
```

#### **Why this works:**
* **Instant State Restoration:** Refreshing the browser or sharing a URL immediately re-opens the exact session, displays the right document, navigates PDF.js to page 14, and highlights citation `c_789`.
* **Zero Route Hydration Bugs:** Prevents broken breadcrumbs and layout tearing.

### 3.2 Strict Anti-IDOR Rule (Security Boundary)
* **Allowed in Query Params (UI State only):** `sessionId`, `docId`, `page`, `citationId`, `panelWidth`.
* **FORBIDDEN in Query Params (Security State):** `tenantId`, `userId`, `role`, `gcsPath`.
* The frontend **never** sends `tenantId`. The backend extracts tenant identity exclusively from the verified Firebase JWT.

---

## 🗄️ 4. State Management Separation

| State Category | Tool | Scope & Responsibilities |
| :--- | :--- | :--- |
| **Server State** | **TanStack Query** (`@tanstack/react-query`) | • Fetching and caching session lists (`/sessions`)<br>• Polling document processing status (`/doc-status/{id}`)<br>• Fetching Signed GCS URLs (`/documents/{id}/view-url`)<br>• Triggering `/query` mutations |
| **UI State** | **Zustand** (`zustand`) | • Currently active/clicked citation<br>• PDF zoom level and active page<br>• Split-screen panel width (resizable slider)<br>• Draft message buffer in chat input |

---

## 🛡️ 5. Runtime Validation Contracts (Zod)

Zod acts as the runtime barrier, guaranteeing that unexpected backend data never crashes the React UI.

### 5.1 Core Zod Schemas (`lib/api/schemas.ts`)

```typescript
import { z } from "zod";

// Citation Schema with strict bounding box tuple
export const CitationSchema = z.object({
  chunk_id: z.string().min(1),
  doc_id: z.string().regex(/^[a-zA-Z0-9_-]{1,128}$/),
  page_number: z.number().int().positive(),
  bbox: z.array(z.number()).length(4), // [left, top, right, bottom] in 0-1 coords
  text_snippet: z.string(),
});

export type Citation = z.infer<typeof CitationSchema>;

// Query Response Contract
export const QueryResponseSchema = z.object({
  answer: z.string(),
  citations: z.array(CitationSchema),
  mode: z.enum(["standard", "deep"]),
  latency_ms: z.number().nonnegative(),
  chunks_used: z.number().int().nonnegative(),
});

export type QueryResponse = z.infer<typeof QueryResponseSchema>;

// Signed URL Response
export const SignedUrlResponseSchema = z.object({
  url: z.string().url(),
  expires_in_seconds: z.number().default(900), // 15-minute TTL
});

export type SignedUrlResponse = z.infer<typeof SignedUrlResponseSchema>;

// Chat Input Form Schema
export const ChatInputSchema = z.object({
  query: z.string().trim().min(1, "Question cannot be empty").max(4000, "Max 4,000 characters"),
  mode: z.enum(["standard", "deep"]).default("standard"),
});
```

---

## 📄 6. PDF.js & Bounding-Box (`BboxOverlay.tsx`) UX Flow

```
[User clicks Citation Pill "[1]"]
               │
               ▼
1. Extract doc_id, page_number, and bbox from Citation object
               │
               ▼
2. Fetch Signed URL via TanStack Query (`GET /documents/{doc_id}/view-url`)
   * Note: Never store URL permanently; refresh if 15-min TTL expires (HTTP 403)
               │
               ▼
3. PDF.js canvas renders target page
               │
               ▼
4. BboxOverlay converts normalized [left, top, right, bottom] to canvas pixel rect:
   pixel_left   = bbox[0] * canvas_width
   pixel_top    = bbox[1] * canvas_height
   pixel_width  = (bbox[2] - bbox[0]) * canvas_width
   pixel_height = (bbox[3] - bbox[1]) * canvas_height
               │
               ▼
5. Render smooth animated highlight box + auto-scroll viewport into view
   * Fallback: If bbox is null/empty, execute in-page PDF text search for snippet
```

---

## 🚀 7. Roadmap & Phased Implementation

### Phase 5.0 (MVP Target — Launch Essential)
* [x] Next.js (TypeScript) + `shadcn/ui` + Radix UI Themes (Emerald Palette).
* [x] Firebase Client SDK Auth (`X-Firebase-Token` header injection).
* [x] Split-Screen View: Chat Panel on Left, PDF.js + `BboxOverlay.tsx` on Right.
* [x] Standard `POST /query` integration (with loading skeleton and latency telemetry).
* [x] Direct-to-GCS 15-minute Signed URL viewing with automatic refresh.
* [x] Runtime validation with Zod on all API endpoints and forms.
* [x] Playwright E2E test verifying: Login $\rightarrow$ Ask $\rightarrow$ Click Citation $\rightarrow$ PDF navigates and highlights bbox.

### Phase 5.5 / 6.0 (Post-MVP Fast Follows)
* [ ] **SSE Token Streaming:** Add Server-Sent Events (`POST /query/stream`) to stream LLM tokens in real time, delivering citations in a final metadata event chunk.
* [ ] **Automated OpenAPI Client Generation:** Generate TypeScript types and Zod schemas directly from FastAPI OpenAPI specs using `openapi-zod-client` or `Orval`.

### Phase 7.0+ (Deferred Enterprise Studio Features)
* [ ] **No-Code Agent Studio (`/agents`):** Custom agent builder.
* [ ] **Third-Party Connectors (`/connectors`):** Slack, Google Drive, Jira OAuth connectors.
* [ ] **Team RBAC (`/users`, `/groups`):** Team permissions management.
* [ ] **Developer Settings (`/account`):** Personal Access Token (PAT) minting for MCP tools.
* [ ] **Real-Time Alert Center (`/notifications`):** WebSocket sync progress.
