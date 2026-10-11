# Saved Revision Season Closure restore identity

Season Closure evidence is embedded in a Saved Revision and its Closure Marker includes
that revision's identity. A restore never moves the historical revision head directly;
it creates a new immutable restore revision so history remains linear and auditable.

Therefore a raw copy of `season_closure` is invalid. The copied marker would still name
the historical target revision while living inside a different Saved Revision.

The restore boundary now:

1. validates any current and target closure component against the revision that owns it;
2. restores the other canonical world components normally;
3. copies the historical Season Summary unchanged;
4. rebuilds the Closure Marker with the new restore revision ID;
5. stores the rebound component before calculating the new Saved Revision content hash.

The historical target is never mutated. Only the new restore revision receives the
new marker identity. The closure summary and its closing-ranking linkage remain
identical.
