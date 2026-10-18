# cos-uid-action: a ZITADEL Action that adds one claim, `cos_uid`

A small [ZITADEL](https://zitadel.com) Action (version 1, JavaScript) from the CreationOS project, written for ZITADEL v4.16. It adds one claim to the ID token and to the userinfo of a person who signs in:

```
cos_uid = "cos-" + the first 20 hex characters of sha256(lower-case, trimmed e-mail address)
```

CreationOS gives every person a Nextcloud user with that name, so Nextcloud (through its `user_oidc` app) can sign them in by this claim without a second login.

## Rules

- Only for a **human** user whose e-mail address is **verified**. For anybody else the claim is simply missing, and nobody can become somebody else's Nextcloud user by typing in an address.
- `HAND_MADE` (an empty object at the top) can map an e-mail address to a Nextcloud user name made by hand under another name.
- ZITADEL's script runtime has no crypto module, so SHA-256 is written out in the script (it hashes the UTF-8 bytes, like Node's `crypto` does).
- The Action's name in ZITADEL must be the function's name: `cosUid`.

## Install

By hand: in the ZITADEL console create an Action named `cosUid` with the content of `cos-uid-action.js`, then add it to the flow **Complement Token** on the triggers **Pre Userinfo creation** and **Pre access token creation**.

Or with the helper (it only uses ZITADEL's management API, keeps everything already on the triggers, and makes the Action "allowed to fail", so a bug in it can never stop anybody from signing in):

```sh
ZITADEL_URL=https://zitadel.example.org ZITADEL_PAT=<token> python3 cos-uid-action.py --check
ZITADEL_URL=https://zitadel.example.org ZITADEL_PAT=<token> python3 cos-uid-action.py --apply
```

The token is read from the environment only; it is never printed or kept. `--remove` takes the Action away again.

## Licence

GNU Affero General Public License, version 3 or later (`AGPL-3.0-or-later`); see `LICENSE`. Published because it runs inside ZITADEL, which is AGPL software.

This project is not made by, and not endorsed by, ZITADEL AG.
