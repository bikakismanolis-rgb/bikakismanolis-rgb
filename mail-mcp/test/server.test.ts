import assert from "node:assert/strict";
import { createServer, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import { after, before, test } from "node:test";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import { parseAccounts } from "../src/config.js";
import { buildServer } from "../src/server.js";

const TOKEN = "test-token-0123456789-abcdefghij";
const ACCOUNTS = [
  { id: "g1", provider: "gmail", email: "one@gmail.com", password: "x" },
  { id: "g2", provider: "gmail", email: "two@gmail.com", password: "x" },
  { id: "y", provider: "yahoo", email: "me@yahoo.com", password: "x" },
  { id: "hot", provider: "outlook", email: "me@hotmail.com", oauth: { clientId: "c", refreshToken: "r" } },
];

let http: Server;
let base: string;

before(async () => {
  process.env.MCP_AUTH_TOKEN = TOKEN;
  process.env.MAIL_ACCOUNTS = JSON.stringify(ACCOUNTS);
  const { handleMcp } = await import("../src/http.js");
  http = createServer((req, res) => void handleMcp(req, res));
  await new Promise<void>((r) => http.listen(0, "127.0.0.1", r));
  base = `http://127.0.0.1:${(http.address() as AddressInfo).port}`;
});

after(() => http.close());

async function connect(url: string) {
  const client = new Client({ name: "test", version: "0" });
  await client.connect(new StreamableHTTPClientTransport(new URL(url)));
  return client;
}

test("rejects a missing or wrong token", async () => {
  for (const path of ["/mcp", "/mcp/wrong", "/api/mcp?token=nope"]) {
    const res = await fetch(base + path, { method: "POST", body: "{}" });
    assert.equal(res.status, 401, path);
  }
});

test("accepts the token in the path, the query and the header", async () => {
  const init = {
    jsonrpc: "2.0",
    id: 1,
    method: "initialize",
    params: { protocolVersion: "2025-03-26", capabilities: {}, clientInfo: { name: "t", version: "0" } },
  };
  const headers = { "content-type": "application/json", accept: "application/json, text/event-stream" };
  const attempts: [string, Record<string, string>][] = [
    [`/mcp/${TOKEN}`, {}],
    [`/api/mcp?token=${TOKEN}`, {}],
    ["/mcp", { authorization: `Bearer ${TOKEN}` }],
  ];
  for (const [path, extra] of attempts) {
    const res = await fetch(base + path, { method: "POST", headers: { ...headers, ...extra }, body: JSON.stringify(init) });
    assert.equal(res.status, 200, path);
    const body = (await res.json()) as { result: { serverInfo: { name: string } } };
    assert.equal(body.result.serverInfo.name, "mail-mcp");
  }
});

test("a real MCP client can list tools and accounts; passwords never leak", async () => {
  const client = await connect(`${base}/mcp/${TOKEN}`);
  const names = (await client.listTools()).tools.map((t) => t.name).sort();
  assert.deepEqual(names, [
    "create_draft", "fetch", "list_accounts", "list_folders",
    "mark_emails", "move_emails", "read_email", "search", "search_emails",
  ]);
  const res = await client.callTool({ name: "list_accounts", arguments: {} });
  const text = (res.content as { text: string }[])[0].text;
  const data = JSON.parse(text);
  assert.equal(data.sendEnabled, false);
  assert.equal(data.accounts.length, 4);
  assert.ok(!text.includes("password") && !text.includes("refreshToken"));
  await client.close();
});

test("unknown account is a tool error, not a crash", async () => {
  const client = await connect(`${base}/mcp/${TOKEN}`);
  const res = await client.callTool({ name: "list_folders", arguments: { account: "nope" } });
  assert.equal(res.isError, true);
  await client.close();
});

test("send_email only exists when sending is switched on", async () => {
  const accounts = parseAccounts(JSON.stringify(ACCOUNTS));
  const has = (allowSend: boolean) =>
    "send_email" in (buildServer({ accounts, authToken: TOKEN, allowSend }) as unknown as { _registeredTools: object })._registeredTools;
  assert.equal(has(false), false);
  assert.equal(has(true), true);
});

test("account config: presets, validation, duplicates", () => {
  const [g, , y, hot] = parseAccounts(JSON.stringify(ACCOUNTS));
  assert.equal(g.imap.host, "imap.gmail.com");
  assert.equal(y.smtp.host, "smtp.mail.yahoo.com");
  assert.equal(hot.smtp.secure, false);
  assert.match(hot.oauth!.tokenUrl, /consumers/);
  assert.throws(() => parseAccounts("not json"), /not valid JSON/);
  assert.throws(() => parseAccounts(JSON.stringify([{ id: "a", provider: "gmail", email: "a@b.co" }])), /exactly one/);
  assert.throws(() => parseAccounts(JSON.stringify([{ id: "a", provider: "custom", email: "a@b.co", password: "x" }])), /custom/);
  assert.throws(() => parseAccounts(JSON.stringify([ACCOUNTS[0], { ...ACCOUNTS[1], id: "G1" }])), /duplicate/);
});
