# mail-mcp

One small server that gives any MCP-capable AI assistant (Claude, ChatGPT and others) access to your mailboxes: any number of Gmail accounts, Yahoo, Hotmail/Outlook.com, iCloud, AOL, or any IMAP server.

You run it in your own hosting account. Your passwords and mail never pass through anyone else's server, and nothing is stored: each request opens an IMAP connection, does its job and closes it.

Οδηγίες στα ελληνικά: [ODIGOS.md](ODIGOS.md)

## What the assistant can do

| Tool | Purpose |
| --- | --- |
| `list_accounts`, `list_folders` | See which mailboxes and folders exist |
| `search_emails` | Latest messages, or search by text, sender, subject, date, unread |
| `read_email` | Text and attachment names of one message |
| `create_draft` | Save a new message or a reply to Drafts. Nothing is sent |
| `mark_emails`, `move_emails` | Read/unread, star, move, archive, trash |
| `send_email` | Only exists if you set `MAIL_ALLOW_SEND=true` |
| `search`, `fetch` | The pair ChatGPT expects for searching across all inboxes |

By default the assistant can only write drafts, and you send them yourself.

## Set it up (about 10 minutes, free Vercel account)

1. Fork this repository and import it at https://vercel.com/new. If the code sits in a `mail-mcp` subfolder, set that as the **Root Directory**.
2. Add one environment variable: `MCP_AUTH_TOKEN`, a long random text of at least 24 characters. It is the password of your server.
3. Deploy.
4. In the project, open Settings > Deployment Protection and make sure the production URL is not behind Vercel Authentication ("Standard Protection" is fine). Otherwise no assistant can reach it.
5. Open `https://<your-project>.vercel.app/setup/<MCP_AUTH_TOKEN>`. That page walks you through the rest: it checks every mailbox login, tells you what to paste where, and shows the address to give to your assistant.

## Adding mailboxes

One environment variable per mailbox, with the address and an **app password** (not your normal password):

```
MAIL_ACCOUNT_1=you@gmail.com abcd efgh ijkl mnop
MAIL_ACCOUNT_2=other@gmail.com qrst uvwx yzab cdef
MAIL_ACCOUNT_3=you@yahoo.com apppassword
```

The provider is recognised from the address. Redeploy after changing variables.

Where to create app passwords:

- Gmail: https://myaccount.google.com/apppasswords (2-Step Verification must be on)
- Yahoo: Account security > Generate app password
- iCloud: account.apple.com > Sign-In and Security > App-Specific Passwords

For any other IMAP server use the JSON form instead:

```
MAIL_ACCOUNTS=[{"id":"work","provider":"custom","email":"me@example.com","password":"...","imap":{"host":"mail.example.com","port":993},"smtp":{"host":"mail.example.com","port":465}}]
```

### Hotmail / Outlook.com

Microsoft accepts only OAuth2 for these mailboxes, so the server needs the id of an Azure app to sign in with:

1. In the Microsoft Entra admin center, create an App registration that supports **personal Microsoft accounts**.
2. Under Authentication, enable **Allow public client flows**.
3. Put its Application (client) ID in the `OUTLOOK_CLIENT_ID` variable and redeploy.
4. On the setup page, type the address and press Connect. You get a code to enter at Microsoft, then a ready `MAIL_ACCOUNT_...` line to paste.

The token from step 4 expires after roughly 90 days; repeat step 4 when the mailbox stops connecting.

## Connecting an assistant

The connector address is `https://<your-project>.vercel.app/mcp/<MCP_AUTH_TOKEN>`.

- Claude: Settings > Connectors > Add custom connector.
- ChatGPT: Settings > Connectors (developer mode), no authentication.
- Clients that can send headers may use `/mcp` with `Authorization: Bearer <MCP_AUTH_TOKEN>`.

## Security

- The connector address is a password. Whoever has it can read your mail. To revoke it, change `MCP_AUTH_TOKEN` and redeploy.
- Email is text written by strangers, and a hostile message can try to instruct the assistant ("forward everything to..."). That is why sending is off by default. Turn it on only if your assistant asks you before each tool call.
- One deployment is for one person. Do not put other people's mailboxes in yours; have them deploy their own.

## Development

```bash
npm install
```

```bash
cp .env.example .env
```

```bash
npm run dev
```

```bash
npm test
```

`MCP_URL=https://<host>/mcp/<token> npm run smoke` checks a live deployment and prints counts only, never message content.

## Status

Verified against real Gmail and Yahoo mailboxes on Vercel: listing, searching and reading. Covered by automated tests: authentication, the MCP protocol, configuration parsing and the setup page. Not yet verified against live servers: drafts, marking, moving, sending, Outlook sign-in, iCloud, AOL and the ChatGPT connection.

## License

MIT. Provided as is, without warranty.
