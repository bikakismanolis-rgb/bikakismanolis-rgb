# mail-mcp: οδηγός στα ελληνικά

Ένας μικρός server που δίνει στο AI σου (Claude, ChatGPT και άλλα) πρόσβαση στα mailbox σου: όσα Gmail θες, Yahoo, Hotmail/Outlook, iCloud ή οποιοδήποτε IMAP.

Τον τρέχεις στον δικό σου λογαριασμό. Οι κωδικοί και τα email σου δεν περνάνε από server κανενός άλλου, και δεν αποθηκεύεται τίποτα.

## Εγκατάσταση (περίπου 10 λεπτά, δωρεάν λογαριασμός Vercel)

1. Κάνε fork το repository και εισαγωγή στο https://vercel.com/new. Αν ο κώδικας είναι σε υποφάκελο `mail-mcp`, όρισέ τον ως **Root Directory**.
2. Πρόσθεσε μία μεταβλητή περιβάλλοντος: `MCP_AUTH_TOKEN`, ένα μεγάλο τυχαίο κείμενο με τουλάχιστον 24 χαρακτήρες. Είναι ο κωδικός του server σου.
3. Πάτα Deploy.
4. Στο project, πήγαινε Settings > Deployment Protection και βεβαιώσου ότι το κύριο URL δεν είναι κλειδωμένο πίσω από Vercel Authentication (το "Standard Protection" είναι εντάξει). Αλλιώς κανένα AI δεν μπορεί να συνδεθεί.
5. Άνοιξε το `https://<το-project-σου>.vercel.app/setup/<MCP_AUTH_TOKEN>`. Η σελίδα αυτή σε οδηγεί στα υπόλοιπα: ελέγχει αν συνδέεται κάθε mailbox, σου λέει τι να επικολλήσεις πού, και σου δείχνει τη διεύθυνση που δίνεις στο AI.

## Προσθήκη mailbox

Μία μεταβλητή ανά mailbox, με τη διεύθυνση και έναν **κωδικό εφαρμογής** (όχι τον κανονικό σου κωδικό):

```
MAIL_ACCOUNT_1=esy@gmail.com abcd efgh ijkl mnop
MAIL_ACCOUNT_2=allo@gmail.com qrst uvwx yzab cdef
MAIL_ACCOUNT_3=esy@yahoo.com kodikosefarmogis
```

Ο πάροχος αναγνωρίζεται από τη διεύθυνση. Μετά από κάθε αλλαγή κάνεις Redeploy.

Πού βγάζεις κωδικό εφαρμογής:

- Gmail: https://myaccount.google.com/apppasswords (θέλει ενεργή επαλήθευση 2 βημάτων)
- Yahoo: Account security > Generate app password
- iCloud: account.apple.com > Σύνδεση και ασφάλεια > Κωδικοί για συγκεκριμένες εφαρμογές

### Hotmail / Outlook.com

Η Microsoft δέχεται μόνο OAuth2, οπότε ο server χρειάζεται το id μιας εφαρμογής Azure:

1. Στο Microsoft Entra admin center φτιάξε App registration που υποστηρίζει **προσωπικούς λογαριασμούς Microsoft**.
2. Στο Authentication ενεργοποίησε το **Allow public client flows**.
3. Βάλε το Application (client) ID στη μεταβλητή `OUTLOOK_CLIENT_ID` και κάνε Redeploy.
4. Στη σελίδα ρύθμισης γράψε τη διεύθυνση και πάτα Σύνδεση. Παίρνεις έναν κωδικό που γράφεις στη Microsoft, και μετά μια έτοιμη γραμμή `MAIL_ACCOUNT_...` για επικόλληση.

Το token λήγει σε περίπου 90 μέρες. Όταν το mailbox σταματήσει να συνδέεται, επαναλαμβάνεις το βήμα 4.

## Σύνδεση με το AI

Η διεύθυνση του connector είναι `https://<το-project-σου>.vercel.app/mcp/<MCP_AUTH_TOKEN>`.

- Claude: Settings > Connectors > Add custom connector.
- ChatGPT: Settings > Connectors (developer mode), χωρίς authentication.

## Ασφάλεια

- Η διεύθυνση του connector είναι κωδικός. Όποιος την έχει διαβάζει το mail σου. Για να την ακυρώσεις, άλλαξε το `MCP_AUTH_TOKEN` και κάνε Redeploy.
- Τα email τα γράφουν ξένοι, και ένα κακόβουλο μήνυμα μπορεί να προσπαθήσει να δώσει εντολές στο AI. Γι' αυτό η αποστολή είναι κλειστή από προεπιλογή: το AI γράφει πρόχειρα και τα στέλνεις εσύ. Ανοίγει με `MAIL_ALLOW_SEND=true`.
- Μία εγκατάσταση είναι για έναν άνθρωπο. Μη βάζεις mailbox άλλων στη δική σου· ο καθένας στήνει τη δική του.
