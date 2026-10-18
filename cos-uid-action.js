// SPDX-FileCopyrightText: 2026 CreationOS
// SPDX-License-Identifier: AGPL-3.0-or-later
// ZITADEL Action (v1, JavaScript) for the trigger "Complement token: pre userinfo creation" (and "pre access token creation").
// It adds ONE claim to the ID token / userinfo: cos_uid = "cos-" + the first 20 hex characters of sha256(lower-case, trimmed e-mail address)
// = exactly what files-service/src/provisioner.js (ncUserFor) calls the person's Nextcloud user name.
// Rules: only for a human whose e-mail address is VERIFIED (an unverified address could be somebody else's: nobody may become that person's Nextcloud user by typing it in).
// The action's NAME in ZITADEL must be the function's name: cosUid. ZITADEL's runtime is ES5-style JavaScript with no crypto module (its docs list http, log, uuid only), so SHA-256 is written out here.
// People whose Nextcloud account was made BY HAND under another name (not "cos-" + hash): lower-case verified e-mail -> that Nextcloud user. Empty is fine. The login bridge has the same list (CLOUD_USER_MAP): keep them equal.
var HAND_MADE = {};
function sha256hex(ascii) {
  function rr(v, a) { return (v >>> a) | (v << (32 - a)); }
  var maxWord = Math.pow(2, 32);
  var i, j, result = '';
  var words = [];
  var bitLength = ascii.length * 8;
  var hash = [], k = [], primeCounter = 0, isComposite = {};
  for (var candidate = 2; primeCounter < 64; candidate++) {
    if (!isComposite[candidate]) {
      for (i = 0; i < 313; i += candidate) { isComposite[i] = candidate; }
      hash[primeCounter] = (Math.pow(candidate, 0.5) * maxWord) | 0;
      k[primeCounter++] = (Math.pow(candidate, 1 / 3) * maxWord) | 0;
    }
  }
  hash = hash.slice(0, 8);
  ascii += '\x80';
  while (ascii.length % 64 - 56) { ascii += '\x00'; }
  for (i = 0; i < ascii.length; i++) {
    j = ascii.charCodeAt(i);
    words[i >> 2] |= j << ((3 - i) % 4) * 8;
  }
  words[words.length] = (bitLength / maxWord) | 0;
  words[words.length] = bitLength;
  for (j = 0; j < words.length;) {
    var w = words.slice(j, j += 16);
    var old = hash;
    hash = hash.slice(0, 8);
    for (i = 0; i < 64; i++) {
      var w15 = w[i - 15], w2 = w[i - 2];
      var a = hash[0], e = hash[4];
      var t1 = hash[7] + (rr(e, 6) ^ rr(e, 11) ^ rr(e, 25)) + ((e & hash[5]) ^ ((~e) & hash[6])) + k[i] +
        (w[i] = (i < 16) ? w[i] : (w[i - 16] + (rr(w15, 7) ^ rr(w15, 18) ^ (w15 >>> 3)) + w[i - 7] + (rr(w2, 17) ^ rr(w2, 19) ^ (w2 >>> 10))) | 0);
      var t2 = (rr(a, 2) ^ rr(a, 13) ^ rr(a, 22)) + ((a & hash[1]) ^ (a & hash[2]) ^ (hash[1] & hash[2]));
      hash = [(t1 + t2) | 0].concat(hash);
      hash[4] = (hash[4] + t1) | 0;
    }
    for (i = 0; i < 8; i++) { hash[i] = (hash[i] + old[i]) | 0; }
  }
  for (i = 0; i < 8; i++) {
    for (j = 3; j + 1; j--) {
      var b = (hash[i] >> (j * 8)) & 255;
      result += (b < 16 ? '0' : '') + b.toString(16);
    }
  }
  return result;
}

function cosUid(ctx, api) {
  var user = ctx.v1.getUser();
  var human = user && user.human;
  if (!human) { return; } // a machine user: no storage
  // found on ZITADEL v4.16.0: human.email is a Go string that the script runtime shows as typeof "object" (JSON.stringify gives the plain text): always coerce it with String()
  var raw = human.email;
  var email = raw && raw.email ? String(raw.email) : (raw ? String(raw) : '');
  var verified = (human.isEmailVerified !== undefined) ? !!human.isEmailVerified : !!(raw && raw.isEmailVerified);
  if (!email || !verified) { return; }
  var key = String(email).replace(/^\s+|\s+$/g, '').toLowerCase();
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(key) || key.length > 254) { return; }
  var utf8 = unescape(encodeURIComponent(key)); // sha256 of the UTF-8 bytes, like Node's crypto does
  api.v1.claims.setClaim('cos_uid', Object.prototype.hasOwnProperty.call(HAND_MADE, key) ? String(HAND_MADE[key]) : 'cos-' + sha256hex(utf8).slice(0, 20));
}
