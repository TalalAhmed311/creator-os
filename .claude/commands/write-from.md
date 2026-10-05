---
description: Write our own version of a post that worked — download/read it, break down why, then draft for one of our accounts
argument-hint: <post-url> [account] [angle]
---
Arguments: `$ARGUMENTS`

Load `content-research` and `platform-writing`.

1. **Study the reference.** Video: `./studio research post add <url> --analyze` → read `analysis.md`, LOOK at `hook.jpg` /
   `contact.jpg`, write the breakdown (`./studio research analysis set <post-id> --hook-type … --structure … --why …`).
   Text post (LinkedIn/X): fetch the text through a connector, `./studio research post add <url> --text-file <f> --handle <h>
   --views/--likes … --source <connector>`. Tell the owner in 3 lines: hook type, structure, why it worked, × normal if known.
2. **Account.** From the arguments, else ask once (default: the account on the same platform as the reference).
3. Run the `/write` flow from step 2 with `--ref-url <url>`: same mechanism, our topic and voice, our material. Never their words,
   footage or images.
