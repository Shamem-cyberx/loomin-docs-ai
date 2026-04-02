/**
 * Minimal Hocuspocus relay for TipTap + Yjs (in-memory; API persists HTML snapshots).
 */
import { Server } from "@hocuspocus/server";

const port = Number(process.env.PORT || 1234);

Server.configure({
  port,
  name: "loomin-docs",
  quiet: process.env.QUIET === "1",
})
  .listen()
  .then(() => {
    console.log(`[loomin-collab] listening on ${port}`);
  })
  .catch((e) => {
    console.error(e);
    process.exit(1);
  });
