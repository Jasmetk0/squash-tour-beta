# Frozen match replay after native birth

## Regression and authority boundary

The continuation replay API previously sent a live v11 checkpoint to the generic
checkpoint verifier without its native inputs. After a valid birthday it therefore
refused to replay an already confirmed pre-birth final. Calling the mutation
context instead would incorrectly make historical replay depend on today's
medical readiness and Working Draft status.

This bounded adapter handles exactly v11's **unchanged historical root**. It
authenticates the actual Run/Branch Saved lineage, decodes that authenticated
HEAD and requires the live root to equal its real Signed counterpart. A first
unsaved birthday may use its actual Saved base root; later native heads must
retain that same root. Rehashing a different live root is not authority.

Only then does the existing verifier check actual live World/opening evidence,
reusing the just-authenticated exact prefix. The existing MatchEngine replays the
selected old match with its original input context, injected seed, log anchor and
effective Health, and compares the entire result/log as before. Today's live
Health/lifecycle/source-generation readiness is not substituted for those facts.

Responses for this bounded native case additionally identify
`historical_owner_scope: pre_native_birth_checkpoint`, the historical root hash
and the match's original source-checkpoint hash. Old checkpoint responses remain
unchanged. No new match, post-birth Entry, future result, write, Save or automatic
repair is permitted. New checkpoint kinds require their own explicit adapter.

## Evidence and limits

- Eight focused boundary tests cover actual source-selection rules with the
  Signed-lineage authorization boundary mocked; they are not whole-Run integration.
- The genuine HTTP/SQLite configured Edition scenario uses production Entry,
  MatchEngine, confirmed result, birthday and manual Save. It verifies replay
  before/after birth Save, after another natural week, and after closing/reopening
  the API/database.
- A corrupt current live Health row does not alter frozen historical replay but
  still blocks current Tour inspection. Rehashed live historical-root divergence
  is rejected against the actual Signed owner. Full database dumps show reads
  do not mutate or repair either case.

Native post-birth competition, source epochs, protected fork re-signing and full
pre-alpha release/50×61 acceptance remain separate unfinished work. Final-head
native API/season/browser gates are mandatory before this slice is merge-ready.
