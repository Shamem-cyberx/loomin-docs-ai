/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_COLLAB_ENABLED?: string;
  readonly VITE_COLLAB_WS?: string;
  readonly VITE_COLLAB_PORT?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
