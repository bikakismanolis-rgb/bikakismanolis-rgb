import { createServer } from "node:http";
import { handleMcp } from "./http.js";

const port = Number(process.env.PORT ?? 3000);

createServer((req, res) => {
  if (req.url?.startsWith("/mcp")) return void handleMcp(req, res);
  res.writeHead(404).end();
}).listen(port, () => {
  console.log(`mail-mcp listening on http://localhost:${port}/mcp/<MCP_AUTH_TOKEN>`);
});
