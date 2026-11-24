import { z } from "zod";

/** Known providers. "custom" needs explicit imap/smtp hosts. */
const PRESETS = {
  gmail: {
    imap: { host: "imap.gmail.com", port: 993, secure: true },
    smtp: { host: "smtp.gmail.com", port: 465, secure: true },
  },
  yahoo: {
    imap: { host: "imap.mail.yahoo.com", port: 993, secure: true },
    smtp: { host: "smtp.mail.yahoo.com", port: 465, secure: true },
  },
  // Hotmail / Outlook.com / Live. Microsoft no longer accepts passwords here, only OAuth2.
  outlook: {
    imap: { host: "outlook.office365.com", port: 993, secure: true },
    smtp: { host: "smtp-mail.outlook.com", port: 587, secure: false },
  },
} as const;

const endpointSchema = z.object({
  host: z.string().min(1),
  port: z.number().int().positive(),
  secure: z.boolean().optional(),
});

const accountSchema = z
  .object({
    id: z
      .string()
      .regex(/^[a-z0-9_-]+$/i, "id may only contain letters, digits, - and _"),
    provider: z.enum(["gmail", "yahoo", "outlook", "custom"]),
    email: z.string().email(),
    name: z.string().optional(),
    /** App password (Gmail, Yahoo, most IMAP providers). */
    password: z.string().optional(),
    /** OAuth2 refresh-token login (needed for Outlook/Hotmail). */
    oauth: z
      .object({
        clientId: z.string().min(1),
        clientSecret: z.string().optional(),
        refreshToken: z.string().min(1),
        tokenUrl: z.string().url().optional(),
        scope: z.string().optional(),
      })
      .optional(),
    imap: endpointSchema.optional(),
    smtp: endpointSchema.optional(),
  })
  .refine((a) => Boolean(a.password) !== Boolean(a.oauth), {
    message: "set exactly one of `password` or `oauth`",
  })
  .refine((a) => a.provider !== "custom" || (a.imap && a.smtp), {
    message: "provider `custom` needs both `imap` and `smtp`",
  });

export type Endpoint = { host: string; port: number; secure: boolean };

export type Account = {
  id: string;
  provider: "gmail" | "yahoo" | "outlook" | "custom";
  email: string;
  name?: string;
  password?: string;
  oauth?: {
    clientId: string;
    clientSecret?: string;
    refreshToken: string;
    tokenUrl: string;
    scope: string;
  };
  imap: Endpoint;
  smtp: Endpoint;
};

export type Config = {
  accounts: Account[];
  /** Shared secret that must be present in the URL or Authorization header. */
  authToken: string;
  /** When false, send_email is not offered at all; drafts only. */
  allowSend: boolean;
};

const OUTLOOK_TOKEN_URL =
  "https://login.microsoftonline.com/consumers/oauth2/v2.0/token";
export const OUTLOOK_SCOPE =
  "https://outlook.office.com/IMAP.AccessAsUser.All https://outlook.office.com/SMTP.Send offline_access";

function withDefaults(e: z.infer<typeof endpointSchema>): Endpoint {
  return { host: e.host, port: e.port, secure: e.secure ?? (e.port === 993 || e.port === 465) };
}

export function parseAccounts(raw: string): Account[] {
  let json: unknown;
  try {
    json = JSON.parse(raw);
  } catch {
    throw new Error("MAIL_ACCOUNTS is not valid JSON");
  }
  const parsed = z.array(accountSchema).min(1).safeParse(json);
  if (!parsed.success) {
    // Zod issues carry paths and messages only, never the secret values.
    const msg = parsed.error.issues
      .map((i) => `${i.path.join(".") || "(root)"}: ${i.message}`)
      .join("; ");
    throw new Error(`MAIL_ACCOUNTS is invalid: ${msg}`);
  }
  const seen = new Set<string>();
  return parsed.data.map((a) => {
    const id = a.id.toLowerCase();
    if (seen.has(id)) throw new Error(`MAIL_ACCOUNTS has duplicate id "${id}"`);
    seen.add(id);
    const preset = a.provider === "custom" ? undefined : PRESETS[a.provider];
    return {
      id,
      provider: a.provider,
      email: a.email,
      name: a.name,
      password: a.password,
      oauth: a.oauth && {
        clientId: a.oauth.clientId,
        clientSecret: a.oauth.clientSecret,
        refreshToken: a.oauth.refreshToken,
        tokenUrl: a.oauth.tokenUrl ?? OUTLOOK_TOKEN_URL,
        scope: a.oauth.scope ?? OUTLOOK_SCOPE,
      },
      imap: withDefaults(a.imap ?? preset!.imap),
      smtp: withDefaults(a.smtp ?? preset!.smtp),
    };
  });
}

export function loadConfig(env: NodeJS.ProcessEnv = process.env): Config {
  const authToken = env.MCP_AUTH_TOKEN ?? "";
  if (authToken.length < 24) {
    throw new Error("MCP_AUTH_TOKEN must be set to a random string of at least 24 characters");
  }
  if (!env.MAIL_ACCOUNTS) throw new Error("MAIL_ACCOUNTS is not set");
  return {
    accounts: parseAccounts(env.MAIL_ACCOUNTS),
    authToken,
    allowSend: env.MAIL_ALLOW_SEND === "true",
  };
}
