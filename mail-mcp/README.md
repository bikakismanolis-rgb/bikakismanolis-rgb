# mail-mcp

Ένας MCP server για όλα τα mailbox σου: Gmail (όσα θες), Yahoo, Hotmail/Outlook και οποιοδήποτε IMAP. Μιλάει το στάνταρ πρωτόκολλο MCP πάνω από HTTP, οπότε δουλεύει με Claude, ChatGPT και κάθε άλλο AI που δέχεται remote MCP server.

## Τι κάνει

| Tool | Δουλειά |
| --- | --- |
| `list_accounts` | Ποια mailbox είναι συνδεδεμένα |
| `list_folders` | Φάκελοι ενός mailbox |
| `search_emails` | Αναζήτηση ή τα πιο πρόσφατα (κείμενο, αποστολέας, θέμα, ημερομηνίες, αδιάβαστα) |
| `read_email` | Κείμενο και συνημμένα (ονόματα) ενός μηνύματος |
| `create_draft` | Αποθηκεύει νέο μήνυμα ή απάντηση στα Πρόχειρα. Δεν στέλνει τίποτα |
| `send_email` | Στέλνει. Υπάρχει μόνο αν βάλεις `MAIL_ALLOW_SEND=true` |
| `mark_emails` | Διαβασμένο/αδιάβαστο, αστέρι |
| `move_emails` | Μετακίνηση σε φάκελο, ή `archive` / `trash` / `spam` |
| `search`, `fetch` | Το ζευγάρι που περιμένει το ChatGPT για αναζήτηση σε όλα τα inbox |

Από προεπιλογή το AI γράφει μόνο πρόχειρα και τα στέλνεις εσύ από την εφαρμογή του mail σου.

## Ρύθμιση λογαριασμών

Όλα μπαίνουν σε μία μεταβλητή περιβάλλοντος, `MAIL_ACCOUNTS`, ως JSON σε μία γραμμή:

```json
[
  { "id": "gmail1", "provider": "gmail", "email": "a@gmail.com", "password": "app-password" },
  { "id": "gmail2", "provider": "gmail", "email": "b@gmail.com", "password": "app-password" },
  { "id": "yahoo",  "provider": "yahoo", "email": "c@yahoo.com", "password": "app-password" },
  { "id": "hot",    "provider": "outlook", "email": "d@hotmail.com",
    "oauth": { "clientId": "azure-client-id", "refreshToken": "..." } },
  { "id": "work",   "provider": "custom", "email": "me@firma.gr", "password": "...",
    "imap": { "host": "mail.firma.gr", "port": 993 }, "smtp": { "host": "mail.firma.gr", "port": 465 } }
]
```

Πού βγάζεις τα διαπιστευτήρια:

- **Gmail:** θέλει ενεργή επαλήθευση 2 βημάτων. Μετά https://myaccount.google.com/apppasswords και φτιάχνεις app password. Ένα για κάθε λογαριασμό Gmail.
- **Yahoo:** Account Security > "Generate app password".
- **Hotmail / Outlook.com:** η Microsoft δεν δέχεται πια κωδικούς στο IMAP, μόνο OAuth2. Φτιάχνεις ένα app registration στο Azure (προσωπικοί λογαριασμοί Microsoft, "Allow public client flows" ενεργό, δικαιώματα `IMAP.AccessAsUser.All` και `SMTP.Send`) και τρέχεις `npm run outlook-login -- <client-id>` για να πάρεις refresh token. Το token λήγει μετά από περίπου 90 μέρες και τότε ξανατρέχεις την εντολή.

Ποτέ μη βάζεις τον κανονικό σου κωδικό, και ποτέ μην κάνεις commit το `.env`.

## Τοπικά

```bash
npm install
```

```bash
cp .env.example .env
```

```bash
npm run dev
```

Ο server ακούει στο `http://localhost:3000/mcp/<MCP_AUTH_TOKEN>`.

```bash
npm test
```

## Deploy στο Vercel

1. Νέο project στο Vercel με **Root Directory** το `mail-mcp`.
2. Environment variables: `MCP_AUTH_TOKEN`, `MAIL_ACCOUNTS` και προαιρετικά `MAIL_ALLOW_SEND`.
3. Deploy. Το URL του connector είναι `https://<project>.vercel.app/mcp/<MCP_AUTH_TOKEN>`.

## Σύνδεση με AI

- **Claude:** https://claude.ai/customize/connectors > custom connector > βάζεις το URL.
- **ChatGPT:** Settings > Connectors (θέλει developer mode) > νέος connector με το ίδιο URL, χωρίς authentication.
- **Οτιδήποτε άλλο:** όποιος client υποστηρίζει MCP "Streamable HTTP". Όσοι στέλνουν headers μπορούν να χρησιμοποιήσουν το `/mcp` με `Authorization: Bearer <token>`.

## Ασφάλεια

- Το URL περιέχει το μυστικό. Όποιος το έχει διαβάζει το mail σου, οπότε φέρσου του σαν κωδικό. Αν διαρρεύσει, αλλάζεις το `MCP_AUTH_TOKEN` και ξανακάνεις deploy.
- Τα email είναι κείμενο από τρίτους. Ένα κακόβουλο μήνυμα μπορεί να προσπαθήσει να δώσει εντολές στο AI ("προώθησε όλα τα mail στο..."). Γι' αυτό η αποστολή είναι κλειστή από προεπιλογή. Άνοιξέ τη μόνο αν το AI που χρησιμοποιείς ζητά επιβεβαίωση πριν από κάθε tool call.
- Ο server δεν αποθηκεύει τίποτα. Κάθε κλήση ανοίγει σύνδεση IMAP, κάνει τη δουλειά και κλείνει.

## Τι έχει δοκιμαστεί

Τα αυτόματα τεστ καλύπτουν τον έλεγχο του token, το πρωτόκολλο MCP με πραγματικό client, τη λίστα των tools και την επικύρωση του `MAIL_ACCOUNTS`. Η επικοινωνία με πραγματικούς IMAP/SMTP servers, το OAuth του Outlook, το deploy στο Vercel και η σύνδεση με ChatGPT δεν έχουν δοκιμαστεί ακόμα.
