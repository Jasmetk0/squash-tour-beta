# FIFA Earth research checkpoint — 2026-10-04

Status: research checkpoint only. This file does **not** assign final 1–10 country ratings.

## Product constraints already fixed

- FIFA Earth models real-world football environments on the shared six country attributes:
  - `squash_popularity`
  - `squash_access`
  - `development_quality`
  - `competition_quality`
  - `elite_support`
  - `squash_tradition`
- Scale later: 1–10, maximum one decimal place.
- Country environment may affect participation, access, development and professional conversion, but never innate-potential rarity by nationality.
- Court Count is not a required pre-alpha attribute.
- 2026 must be treated as partial-year evidence to the real research cutoff, not a fictional complete year.
- Missing data is not zero and is not automatically the lowest rating.
- Observed evidence, derived indicators and game ratings must remain separate.
- Historical predecessor observations must not be duplicated across successor states.

## Verified global FIFA anchors

### FIFA Big Count 2006

Primary source:
https://digitalhub.fifa.com/m/55621f9fdc8ea7b4/original/mzid0qmguixkcmruvema-pdf.pdf

Research implications:
- Useful global participation/access anchor around 2006.
- Country/association rows contain substantially more than one total-player count; fields include registered-player and organisational variables.
- The survey covered essentially the FIFA association universe, but not every value should be treated as equally direct observation. FIFA supplemented missing survey responses from earlier/other sources.
- Preserve per-observation provenance/confidence rather than assigning a single confidence to the whole table.
- All-player/all-sex participation must not be silently treated as men's participation.
- Absolute player totals should later be normalised against historical population before being used as popularity/access evidence.

### FIFA Professional Football Report 2023

Primary overview:
https://inside.fifa.com/legal/news/fifa-publishes-professional-football-report-2023

Verified scope:
- all 211 FIFA Member Associations are reviewed;
- report is men's professional football;
- main domains: players, clubs, competitions/top-tier competition and transfers;
- FIFA headline: 128,694 professional male players at 3,986 clubs in 135 countries;
- 88% of associations reported some form of club-licensing regulation.

Research implications:
- strong 2023 evidence for professionalisation / elite-support / competition structure;
- only indirect evidence for mass popularity and access;
- absence of a professional league/player count is not equivalent to absence of football;
- keep the known page-identity anomaly and national-total/global-headline reconciliation issue as explicit data-quality records; do not silently “correct” raw observations.

## Verified Asia anchors

### Japan

Primary history:
https://jfa.jp/eng/about_jfa/history/

Verified timeline anchors:
- JFA founded 1921; FIFA re-entry 1950; AFC membership 1954.
- Japan Soccer League started in 1965 as the first national league.
- National Training Centre opened in 1977 for elite training.
- limited professional-player licensing introduced in 1986.
- J.League legal entity established in 1991 and competition launched in 1993.
- first men's FIFA World Cup appearance in 1998.
- J1/J2 two-division format introduced in 1999.
- 2002 World Cup co-hosting and later infrastructure/development programmes provide additional structural anchors.

Attribute use:
- league/professionalisation changes: competition_quality + elite_support;
- national training system: development_quality + elite_support;
- spread/community effects of J.League: popularity/access, supported only where contemporary evidence is available;
- results remain mainly competitive evidence.

### India

Primary sources:
https://www.the-aiff.com/history
https://www.the-aiff.com/article/foundation-day-of-governing-body-of-indian-football

Verified anchors:
- organised football predates AIFF; AIFF formed in 1937.
- FIFA affiliation in 1948 and founding AFC membership in 1954.
- national Federation Cup began in 1977.
- National Football League started in 1996.
- AIFF structure includes state associations and technical functions covering grassroots, coach education, academies, registration and leagues.

Research implication:
- India is an important test that popularity/history, access and current elite competitive quality must remain separate attributes rather than collapsing into one strength score.

## Verified Africa anchors

CAF member-association pages provide reliable creation/FIFA/CAF affiliation dates for structural anchors.

Primary examples:
- Egypt: https://www.cafonline.com/inside-caf/member-associations/egypt/
  - association created 1921; FIFA 1923; CAF 1957.
- Nigeria: https://www.cafonline.com/inside-caf/member-associations/nigeria/
  - association created 1945; FIFA 1960; CAF 1957.
- Morocco: https://www.cafonline.com/inside-caf/member-associations/morocco/
  - association created 1955; FIFA 1960; CAF 1959.
- Cameroon: https://www.cafonline.com/inside-caf/member-associations/cameroon/
  - association created 1959; FIFA 1962; CAF 1963.
- Senegal: https://www.cafonline.com/inside-caf/member-associations/senegal/
  - association created 1960; FIFA/CAF 1964.
- South Africa: https://www.cafonline.com/inside-caf/member-associations/south-africa/
  - current SAFA created 1991; FIFA/CAF affiliation 1992.

Research implications:
- creation/affiliation date is useful institutional-history evidence but cannot by itself define football tradition.
- South Africa requires an explicit discontinuity/apartheid-era association model rather than treating 1991 as “football begins”.
- decolonisation-era African associations need predecessor/local-history evidence where available.

## Historical-polity / association rules already established

The final mapping must be entity-specific rather than one generic split rule.

Required explicit cases:
- Czechoslovakia -> Czechia + Slovakia
- West Germany + East Germany -> Germany
- USSR -> successor associations
- Yugoslavia -> successor associations, including later Serbia and Montenegro / Serbia / Montenegro / Kosovo lineage
- England / Scotland / Wales / Northern Ireland vs UK geography
- Baltic and other pre-Soviet association histories where applicable
- Faroe Islands and Gibraltar as non-sovereign association cases
- colonial/territorial transitions across Africa, Asia, Caribbean and Oceania

No-double-count rules:
1. A predecessor's population observation is never copied in full to multiple successors.
2. A predecessor's player/club observation is never copied in full to multiple successors.
3. Historical competition results remain attached to the historical entity/association.
4. Successor `squash_tradition` may receive explicitly modelled inherited-history evidence where continuity is defensible.
5. Access, participation, development and elite-support require successor/local evidence or a transparent lower-confidence transition estimate.
6. FIFA/continental affiliation date is not automatically the start of local football history.

## Evidence states for future anchors

Each country-year anchor should record one of:

- `observed`: directly supported by a source for the entity/period.
- `derived`: deterministic transformation of observed inputs.
- `interpolated`: between compatible country-specific anchors.
- `carry_forward`: bounded continuation where no structural break occurred.
- `backcast`: backward estimate from later evidence plus period-specific historical evidence.
- `comparative_estimate`: transparent estimate using matched regional/structural peers.
- `structural_transition`: special handling around independence, association split/merge, regime change or professionalisation shock.

All non-observed states need confidence/provenance. Linear interpolation is prohibited across documented structural breaks unless the transition itself is explicitly modelled.

## Six attributes must remain distinct

### popularity
Primary evidence: participation intensity, cultural reach, audience/community penetration, historical prominence.
Do not substitute national-team ranking.

### access
Primary evidence: registration footprint, clubs/teams, geographic/institutional availability, grassroots/school/community pathways and material barriers.
High popularity does not guarantee high access.

### development_quality
Primary evidence: youth structures, coach education, academies/training centres, systematic player-development pathways and youth outcomes where contemporaneous.
No future leakage from later senior careers.

### competition_quality
Primary evidence: domestic competitive depth, professional/semi-professional league strength, club and national competitive evidence, player depth.
Results/rankings belong primarily here.

### elite_support
Primary evidence: professional clubs/players, federation investment, elite training systems, licensing/regulatory capacity and high-performance support.

### tradition
Primary evidence: duration and continuity of organised football, historical competition/club culture and institutional persistence.
Tradition may remain high while current competition quality declines.

## Data-quality rules

- observation year and publication year are separate fields;
- association, sovereign state and territory identifiers are separate;
- sex scope is explicit: men / women / all-sex / unknown;
- age scope is explicit where known;
- registered, active, estimated and total participation are not interchangeable;
- missing means unknown/unavailable unless the source explicitly defines zero;
- source correction never overwrites raw source evidence: preserve raw + correction/exclusion record;
- decimals in later game ratings express model resolution, not historical measurement precision.

## Known research gaps still open

Before final FIFA Earth ratings:
1. finish regional/national source collection for Africa beyond affiliation dates;
2. complete Asia beyond Japan/India, especially Korea split, China, West/Central/Southeast Asia;
3. Latin America and CONCACAF country-specific anchors;
4. Oceania and non-FIFA/sparse territories;
5. explicit polity mapping table with dates and inheritance rules;
6. country-specific anchor sets for representative strong, medium, weak, microstate and territory cases;
7. population-normalised participation indicators from Big Count;
8. complete extraction/reconciliation of Professional Football Report 2023 country rows;
9. plausibility checks before materialising 1955–2026 annual values.


## Africa research expansion — 2026-10-04

### Morocco

Primary sources:
- FRMF history: https://frmf.ma/fr/histoire-du-football-marocain
- FIFA Talent Development Scheme / Morocco: https://inside.fifa.com/advancing-football/news/talent-development-scheme-gains-new-ground-in-morocco
- FIFA Morocco development overview: https://inside.fifa.com/advancing-football/fifa-forward/news/moroccan-footballs-continuing-success

Verified anchors:
- organised Moroccan club/league history predates independence: Ligue du Maroc started in 1916.
- FRMF was established immediately after independence in 1956 and inherited the organisational space of the former Ligue du Maroc.
- FRMF history records 310 clubs at federation formation and a national championship starting in 1956.
- FIFA affiliation followed in 1960.
- modern development has a clear structural break around the Mohammed VI football development system: Academy established in 2009; FIFA describes a national/regional facilities + talent + qualified-staff strategy and a wider academy/training-centre network in the 2010s/2020s.
- later FIFA reporting explicitly attributes part of Morocco's modern player-production pipeline to this academy/network.

Attribute interpretation:
- pre-1956 evidence supports tradition and competition continuity, not modern federation capacity.
- 1956 national competition/federation consolidation supports competition_quality + elite_support.
- 2009 onward is a strong development_quality / elite_support anchor.
- do not infer mass access solely from elite academy investment.

### Egypt

Primary sources:
- EFA institutional history: https://www.efa.com.eg/ar/%D8%B9%D9%86-%D8%A7%D9%84%D8%A7%D8%AA%D8%AD%D8%A7%D8%AF/
- CAF association record: https://www.cafonline.com/inside-caf/member-associations/egypt/
- FIFA Forward technical-centre project: https://inside.fifa.com/advancing-football/fifa-forward/news/work-to-build-new-home-of-football-in-egypt-s-capital-kick-off
- FIFA 2025 technical-centre update: https://inside.fifa.com/associations/news/egypt-fa-headquarters-forward-investment-infantino-fernandes

Verified anchors:
- organised national football competition structures existed before the EFA: a national organising effort is documented from the 1910s.
- EFA founded 3 December 1921; FIFA affiliation 1923; CAF founding member in 1957.
- Egypt won the inaugural AFCON in 1957 and has long-standing continental club/national-team evidence, useful primarily for competition_quality/tradition.
- a major modern technical-centre infrastructure phase began under FIFA Forward in 2019; the EFA headquarters/technical centre was formally opened in 2021 and subsequent phases brought total FIFA Forward investment to USD 6.65m by 2025.

Attribute interpretation:
- very high historical continuity evidence for tradition.
- tournament/club success is competitive evidence, not automatic access/popularity evidence.
- 2019–2025 technical-centre investment is a modern elite_support/development_quality anchor.

### Cameroon

Primary sources:
- FECAFOOT history: https://fecafoot-officiel.com/la-fecafoot/
- CAF association record: https://www.cafonline.com/inside-caf/member-associations/cameroon/
- FIFA Forward impact: https://inside.fifa.com/en/associations/CMR/impact

Verified anchors:
- first documented teams in major Cameroonian centres followed World War I.
- a broader sports federation regulating football existed around 1947.
- local league structures were already spreading before modern FECAFOOT.
- FECAFOOT founded in 1959; FIFA affiliation 1962; CAF affiliation 1963.
- FECAFOOT history records a national first division of roughly 12–16 teams in the 1960s and Oryx Douala winning the African club championship in 1965.
- current FIFA Forward records show investment in a technical centre, pitches and competitions.

Attribute interpretation:
- tradition must predate 1959.
- federation creation and 1960s national competition are institutional/competition anchors.
- modern Forward infrastructure is development/access/elite-support evidence but should not be backcast into earlier decades.

### Nigeria

Primary sources:
- CAF association record: https://www.cafonline.com/inside-caf/member-associations/nigeria/
- CAF member-association focus: https://www.cafonline.com/news/member-association-focus-nigeria/
- FIFA Forward impact: https://inside.fifa.com/associations/NGA/impact
- FIFA Forward NFF technical-centre project: https://inside.fifa.com/advancing-football/fifa-forward/news/nigeria-football-federation-new-accommodation-pitches-fifa-forward

Verified anchors:
- Nigerian association created 1945; CAF affiliation 1957; FIFA affiliation 1960.
- Nigeria's youth competitive record provides unusually strong late-20th/early-21st-century evidence for player-development output: inaugural FIFA U-16 title in 1985 plus later U-17 and U-20 successes.
- current FIFA Forward data records USD 7.25m committed to infrastructure projects including stadiums, technical centres and pitches.
- a new NFF technical-centre project in the 2023–2026 Forward cycle includes training pitches and national-team accommodation, with FIFA funding reported at USD 4.87957m.

Attribute interpretation:
- youth results are supporting evidence for development_quality, but not a direct measurement of access or federation infrastructure.
- current infrastructure investments are strong modern elite_support/development anchors and simultaneously show that infrastructure quality should not be assumed historically from player talent alone.

### Senegal

Primary sources:
- CAF association record: https://www.cafonline.com/inside-caf/member-associations/senegal/
- FIFA youth-competition development report: https://inside.fifa.com/advancing-football/news/fifa-forward-paves-way-for-youth-competitions-in-senegal
- FIFA Forward impact: https://inside.fifa.com/fr/associations/SEN/impact
- FSF youth development seminar: https://fsfoot.sn/seminaire-projets-de-developpement-du-football-des-jeunes/

Verified anchors:
- federation created 1960; FIFA and CAF affiliation 1964.
- national youth leagues were introduced in 2020 with FIFA Forward support specifically to provide competitive pathways for young players.
- FIFA reporting identifies the previous lack of structured youth competition as a development bottleneck despite existing club/academy technical work.
- current Forward portfolio includes infrastructure, a technical centre, pitches, capacity-building and competition funding.
- FSF continued formal youth-development planning in 2025 through national/regional technical structures.

Attribute interpretation:
- 2020 is a meaningful structural-break anchor for development_quality/competition pathways.
- do not retroactively score earlier Senegal development structures at the modern level simply because later national teams became successful.

### South Africa

Primary sources:
- CAF history: https://www.cafonline.com/inside-caf/about-us/caf-history/
- CAF association record: https://www.cafonline.com/inside-caf/member-associations/south-africa/
- FIFA historical publication: https://img.fifa.com/image/upload/ghd0g4e9zyk5pbithtcg.pdf

Verified anchors:
- South Africa was one of the four countries involved in CAF's founding process in 1957.
- the apartheid regime caused exclusion from continental/international football; FIFA's historical publication records suspension in the 1960s and later expulsion.
- football itself did not disappear: FIFA's historical account describes multi-racial football structures emerging despite apartheid and the top flight becoming multi-racial by the end of the 1970s.
- modern SAFA was formed in 1991 through unification of previously divided football bodies.
- FIFA membership was restored in June 1992; CAF association records modern SAFA creation in 1991 and FIFA/CAF affiliation in 1992.
- South Africa then won AFCON in 1996.

Mandatory modelling rule:
- never model 1955–1991 as "no South African football".
- introduce an apartheid-era institutional discontinuity affecting international competition access, governance unity and development pathways.
- tradition/popularity/local competition may remain substantial during isolation, while international competition_quality evidence and institutional elite-support continuity are explicitly constrained.
- 1991–1992 is a major structural_transition, not a normal interpolated year.

## Africa-specific research conclusions

Africa cannot be modelled as a simple late-start region based on FIFA/CAF affiliation dates.

At least four distinct historical patterns are already evident:

1. **Long institutional/competition continuity** — Egypt.
2. **Colonial/pre-independence league continuity followed by federation consolidation** — Morocco.
3. **Strong local football before post-independence federation formalisation** — Cameroon and many likely peers.
4. **Political exclusion / fragmented governance despite substantial domestic football** — South Africa.

Modern development also differs materially:
- Morocco: integrated academy/facilities/personnel system.
- Senegal: competition-pathway expansion, especially youth leagues from 2020.
- Nigeria: exceptional player-development outcomes combined with continuing major infrastructure investment.
- Egypt: federation/technical-centre capacity investment.
- Cameroon: technical-centre/pitch/competition investment.

These patterns must be preserved as country-specific anchors rather than collapsed into one CAF-era curve.

## Additional Africa research still required

Before Africa is ready for annual materialisation:
- Ghana, Côte d'Ivoire and Algeria need full dossiers because they provide key comparison cases.
- Ethiopia/Sudan require early-CAF and political-history handling.
- DR Congo/Congo, Tanzania, Kenya, Uganda, Zambia and Zimbabwe require colonial/independence transition anchors.
- Eritrea/Ethiopia and Sudan/South Sudan need explicit predecessor-successor rules.
- small/island and sparse-data associations need comparative models: Cabo Verde, Comoros, São Tomé and Príncipe, Seychelles, Mauritius, Djibouti, Lesotho, Eswatini and others.
- historical professional-league dates and registration/club-count anchors remain incomplete across most countries.
- Big Count 2006 country observations should later be cross-joined with population before popularity/access inference.


## Asia research expansion — 2026-10-04

### Korea Republic

Primary sources:
- KFA summary: https://www.kfa.or.kr/kfa/
- KFA history: https://www.kfa.or.kr/kfa/?act=history
- FIFA Korea association / development: https://inside.fifa.com/en/about-fifa/associations/kor
- FIFA Korea Football Park 2026: https://inside.fifa.com/associations/news/korea-republic-opens-new-national-training-center-fifa-forward

Verified anchors:
- predecessor Korean football association founded 19 September 1933.
- FIFA membership 21 May 1948.
- renamed Korea Football Association 4 September 1948.
- AFC membership 8 May 1954.
- the first nationwide football competition is recorded by KFA in 1921, so organised tradition clearly predates the modern Republic-era association.
- KFA documents Asian Cup titles in 1956 and 1960.
- a professional league launched in 1983.
- modern development infrastructure received another major anchor in 2026 with the opening of Korea Football Park, designed for elite training, youth development, coaches/referees and club/public access; FIFA Forward funded five pitches.

Attribute interpretation:
- 1955 starts from an already mature organised-football ecosystem; do not treat 1955 as a build-from-zero date.
- 1983 is a strong competition_quality / elite_support professionalisation anchor.
- 2026 Korea Football Park supports modern development_quality + elite_support + some access evidence.

### Korea split / DPR Korea

Primary sources:
- FIFA DPR Korea association: https://inside.fifa.com/en/about-fifa/associations/PRK
- AFC DPRK member association: https://www.the-afc.com/en/east/dpr_korea.html

Verified evidence:
- Korea Republic and DPR Korea are separate football associations/entities in the post-war period.
- DPR Korea's men's side reached the 1966 FIFA World Cup quarter-finals, a strong mid-1960s competition-quality anchor.
- available official public-source detail for historical participation/access/development is much thinner than for Korea Republic.

Mandatory modelling rule:
- pre-division Korean football history must not be copied in full into both post-division entities.
- Korea Republic can inherit explicit institutional continuity from the 1933 association only where source lineage supports it.
- DPR Korea requires separate post-division evidence for access/development/elite support.
- broader pre-1945 Korean football may support carefully tagged shared cultural/tradition context, but must not become duplicated player/club/competition observations.
- confidence should be lower for DPR Korea non-results dimensions because current public evidence is sparse.

### China PR

Primary sources:
- FIFA Forward China U-19 youth competition: https://inside.fifa.com/advancing-football/fifa-forward/news/youth-development-in-china-moving-forward-with-newly-structured-u-19-national-yo
- FIFA China Forward impact: https://inside.fifa.com/en/associations/CHN/impact
- CFA statutes via AFC: https://assets.the-afc.com/migration/c/f/cfa-statutes-2019-edition

Verified anchors:
- FIFA-supported restructuring of the U-19 National Youth Super League provides a concrete 2019 development/competition anchor.
- FIFA reports participating players in that competition rising from 1,066 to 1,649 after restructuring.
- current Forward portfolio is heavily competition-oriented rather than infrastructure-oriented.

Attribute interpretation:
- use the 2019 youth-league intervention as development_quality + youth competition pathway evidence.
- do not infer overall football popularity from this programme alone.
- China requires further historical research for the 1955–1990s association/league pathway before annual materialisation.

### Iran

Primary source:
- Iran AFC Asian Cup 2027 bid documentation: https://assets.the-afc.com/downloads/asian-cup/AC-2027-BID-BOOK-IR-IRAN.pdf

Verified anchors:
- modern-style football is documented in Iran from the early 20th century, with school/institutional spread.
- national football federation established in 1946.
- FIFA membership dated 20 February 1948.
- therefore Iran enters the 1955 simulation period with an existing national governing structure and established football culture.

Attribute interpretation:
- 1955 tradition/institutional-support baselines must reflect pre-existing organised football, not a new association.
- further national-league/professionalisation and youth-development anchors are still required.

### Saudi Arabia

Primary source:
- SAFF statutes via AFC: https://assets.the-afc.com/migration/s/a/saff-statutes

Verified anchor:
- Saudi Arabian Football Federation formally established 6 September 1956.

Attribute interpretation:
- 1956 is an institutional anchor, not necessarily the first year football was played locally.
- historical domestic competition and later professionalisation still need separate source-backed anchors.
- recent state investment must never be backcast across the full historical period.

### Uzbekistan / post-Soviet Central Asia

Primary sources:
- FIFA Central Asian development / CAFA Nations Cup: https://inside.fifa.com/news/cafa-nations-cup-uzbekistan-tajikistan-gianni-infantino
- FIFA Uzbekistan association: https://inside.fifa.com/about-fifa/associations/UZB
- UFA statutes via AFC: https://assets.the-afc.com/migration/u/f/ufa-statutes

Verified anchors:
- Uzbekistan, Kyrgyz Republic, Tajikistan and Turkmenistan joined FIFA in 1994, shortly after independence.
- FIFA explicitly describes these Central Asian football nations as institutionally young while also noting that football is popular across the region.
- Uzbekistan qualified for its first men's FIFA World Cup in 2025 for the 2026 tournament.
- post-independence technical/physical infrastructure growth is a distinct modern phase.

Mandatory modelling rule:
- pre-1991 Uzbek football activity belongs to the Soviet sporting system and must not be treated as "no football".
- Soviet-era local clubs/player-development evidence may inform Uzbekistan-specific tradition/development only where geographically attributable.
- USSR national-team/player/association observations are not copied wholesale into Uzbekistan.
- 1991–1994 should be a structural_transition period from Soviet-system local football into an independent association/international ecosystem.
- same principle applies, with country-specific evidence, to Kyrgyzstan, Tajikistan and Turkmenistan.

## Asia-specific research conclusions

Asia already shows several materially different historical trajectories:

1. **Long pre-1955 institutional continuity** — Korea Republic, Iran, Japan.
2. **Post-war political split requiring non-duplicated shared-history handling** — Koreas.
3. **Large-system reform without simple strength continuity** — China.
4. **Mid-1950s federation formalisation followed by later professionalisation/investment** — Saudi Arabia.
5. **Strong local football inside a predecessor state followed by independent-association creation** — Uzbekistan and other post-Soviet Central Asian states.
6. **Established football tradition but later national-league formalisation** — India.

These trajectories require different anchor-generation rules. A single AFC-era interpolation curve would be historically wrong.

## Additional Asia research still required

Before Asia is ready for annual materialisation:
- China: federation/league continuity and professionalisation from 1955 through the 1990s.
- DPR Korea: domestic league, development and participation evidence beyond international results.
- Iran: national league/professionalisation, youth/coaching and elite-support milestones.
- Saudi Arabia: domestic league and professionalisation chronology plus recent investment breakpoints.
- Gulf states including Qatar/UAE: separate late-20th/21st-century infrastructure and elite-support models.
- Iraq, Syria, Jordan, Lebanon and Palestine: institutional history and conflict-disruption anchors.
- Southeast Asia: Thailand, Indonesia, Malaysia, Vietnam, Philippines, Singapore plus colonial/state-transition handling.
- South Asia beyond India: Pakistan, Bangladesh, Sri Lanka, Nepal, Bhutan.
- post-Soviet Central Asia: explicit predecessor mapping for Kazakhstan, Kyrgyzstan, Tajikistan, Turkmenistan, Uzbekistan.
- Hong Kong and Macau: non-sovereign association treatment and political-sovereignty transition without rewriting association history.
- Vietnam and Korea political splits require dedicated no-double-count rules.


## Americas research expansion — 2026-10-04

### Argentina

Primary sources:
- AFA history: https://www.afa.com.ar/11461/pages/historia
- AFA professionalisation milestone: https://www.afa.com.ar/clubes/posts/a-90-anos-de-la-fundacion-de-la-liga-argentina-de-football

Verified anchors:
- AFA traces organised national association history to 21 February 1893.
- Argentina became the first South American association affiliated to FIFA in 1912.
- professional football was formally organised through the Liga Argentina de Football in 1931.
- therefore Argentina enters the 1955 simulation horizon with decades of organised competition and more than two decades of formal professionalisation already established.

Attribute interpretation:
- tradition and competition_quality must start very high relative to countries only institutionalising football after 1955.
- professionalisation evidence supports elite_support/competition_quality but does not by itself measure access or mass participation.
- later national-team titles are competitive evidence, not a substitute for development/access observations.

### Brazil

Primary source:
- CBF national-team history: https://www.cbf.com.br/selecao-brasileira/noticias/noticias-selecao-masculina/a/111-anos-da-selecao-brasileira

Verified anchor:
- Brazil's national team first played in 1914.
- by the 1955 start year Brazil already had long-running organised football and national representation.
- later competitive dominance can inform competition_quality/tradition but should not be used to infer all six attributes.

Research gap:
- still requires authoritative CBF/FIFA sources for federation lineage, domestic professionalisation, youth-development system and participation/access anchors.
- Brazil should not receive final annual anchors from results history alone.

### Mexico

Primary source:
- FMF history: https://fmf.mx/historia

Verified anchors:
- predecessor Federation de Football Asociación existed by 1922.
- Federación Mexicana de Fútbol founded 23 August 1927.
- first championship under the federation was 1927–28 with eight teams.
- FMF history dates FIFA-regulated Mexican football from 1929.
- hosting FIFA World Cups in 1970 and 1986 provides infrastructure/elite-support event anchors, but hosting itself is not a direct popularity/access measure.

Attribute interpretation:
- Mexico is another country entering 1955 with mature federation/competition tradition.
- tournament hosting is a bounded elite-support/infrastructure signal around the event period, not a permanent maximum.
- later club/national results remain competition evidence.

### United States

Primary sources:
- U.S. Soccer historical timeline: https://www.ussoccer.com/history/timeline
- U.S. Soccer National Training Center / current strategy: https://www.ussoccer.com/stories/2024/04/us-soccer-breaks-ground-on-the-arthur-m-blank-us-soccer-national-training-center
- FIFA Forward impact: https://inside.fifa.com/en/associations/USA/impact

Verified anchors:
- U.S. Soccer predecessor federation founded 5 April 1913.
- provisional FIFA membership followed in 1913 and full membership in 1914.
- National Challenge Cup began in 1914.
- an early professional American Soccer League began in 1921.
- therefore organised/professional football history long predates 1955, even though football's relative national popularity and league continuity differed greatly from Latin America/Europe.
- current U.S. Soccer strategy explicitly separates participation/access, playing environments/coaching, development pathways/pro leagues and commercial/fandom growth.
- current FIFA Forward funding includes capacity-building, national-team support and competition investment.
- a new national training centre broke ground in 2024, providing a modern elite-support/development anchor.

Attribute interpretation:
- the USA is a crucial test case for keeping tradition, access, popularity, competition quality and elite support separate.
- long institutional tradition does not imply football was historically a dominant spectator sport.
- large youth participation in later decades must not be converted directly into elite competition strength.

### CONCACAF / territory handling

Useful official evidence:
- FIFA Forward country impact pages expose project allocations for small/non-sovereign associations such as Puerto Rico and the U.S. Virgin Islands.
- examples:
  - Puerto Rico: https://inside.fifa.com/associations/PUR/impact
  - U.S. Virgin Islands: https://inside.fifa.com/associations/VIR/impact

Research implications:
- non-sovereign FIFA members require association-level football observations distinct from sovereign-state political geography.
- modern Forward projects can provide development/access/elite-support anchors even for sparse associations, but they must not be backcast before the project period.
- absolute funding values should not become direct 1–10 ratings; they need context such as population, existing facilities and project type.

## Americas-specific research conclusions

The Americas already provide several useful contrasting archetypes:

1. **Very old association + early professionalisation + elite competitive tradition** — Argentina.
2. **Very old football culture + exceptional competitive output requiring deeper structural evidence** — Brazil.
3. **Long federation/league continuity + major event-hosting infrastructure** — Mexico.
4. **Long institutional history but highly variable national popularity/pro-league continuity** — United States.
5. **Small/non-sovereign associations where modern FIFA investment is observable but historical evidence is sparse** — Puerto Rico, U.S. Virgin Islands and similar territories.

This reinforces the six-attribute model: neither early federation date, absolute participation, hosting events nor national-team results can stand in for the whole environment.

## Additional Americas research still required

Before Americas annual materialisation:
- Brazil: federation lineage, professionalisation, youth/club development and participation data.
- Argentina: modern youth/development and participation/access anchors beyond competition history.
- Uruguay: essential early-professional/tradition comparator.
- Chile, Colombia, Peru, Paraguay and Ecuador: association/professional league/development timelines.
- Mexico: professional-league chronology and youth/development structures beyond federation history.
- USA: major structural breaks in professional leagues (NASL collapse, MLS launch), youth registration/access and development-system reforms.
- Canada: separate federation/professional-pathway history.
- Caribbean and Central America: country-specific histories plus sparse-data comparative groups.
- political/association mapping for Puerto Rico, USVI, Bermuda, Cayman Islands and other non-sovereign members.


## Oceania and small-association research expansion — 2026-10-04

### Australia

Primary sources:
- Football Australia history: https://footballaustralia.com.au/history
- Football Australia governance: https://footballaustralia.com.au/about/football-australia-governance
- Whole of Football Plan: https://footballaustralia.com.au/sites/ffa/files/2019-05/Whole_of_Football_Plan.pdf

Verified anchors:
- a national governing body existed before the current federation lineage, but governance was unstable and fragmented.
- the Australian Soccer Federation was formed in 1961 after an earlier body had been suspended from FIFA; FIFA readmission followed in 1963.
- Australia, New Zealand, Fiji and Papua New Guinea were founding members of OFC in 1966.
- the National Soccer League operated as the national competition before being discontinued after 2003-04.
- the A-League launched in 2005 as Australia's first fully professional national league.
- Australia formally moved from OFC to AFC on 1 January 2006.
- league governance was later separated from Football Australia in 2020.

Attribute interpretation:
- 1960-63 is an institutional disruption and must not be treated as "no football".
- 2005 is a major competition_quality / elite_support professionalisation anchor.
- 2006 confederation transfer changes competitive environment and travel/opposition context but should not automatically change popularity/access.
- governance instability before 2003 is relevant to elite_support/institutional continuity.
- long local football history and league participation should remain distinct from football's relative popularity within a rugby/cricket-dominant sporting culture.

### New Zealand

Primary sources:
- OFC member-association record: https://www.oceaniafootball.com/new-zealand/
- OFC grassroots/finance history: https://www.oceaniafootball.com/archives-12647/
- OFC financial/development article: https://www.oceaniafootball.com/archives-11739/

Verified anchors:
- New Zealand Football founded in 1891.
- FIFA affiliation in 1948.
- New Zealand was one of OFC's founding members in 1966.
- post-2010 World Cup revenue was explicitly reinvested into grassroots, coaching, facilities and talent development through the New Zealand Football Foundation.
- NZF also rebuilt financial reserves after a late-2000s working-capital shortage, a useful example of institutional-capacity variation over time.
- football growth since the turn of the century is acknowledged by OFC, but New Zealand remains historically a rugby-dominant sporting environment.

Attribute interpretation:
- 1955 tradition and institutional continuity are already mature.
- popularity must remain lower than a simplistic federation-age score would imply.
- 2010-11 is a useful modern access/development/elite-support investment anchor.
- financial/institutional capacity can vary without erasing tradition.

### Fiji

Primary sources:
- OFC member-association record: https://www.oceaniafootball.com/fiji/
- FIFA Forward impact: https://inside.fifa.com/en/associations/FIJ/impact
- OFC refereeing history: https://www.oceaniafootball.com/archives-12245/

Verified anchors:
- Fiji Football Association founded in 1938.
- FIFA affiliation in 1963.
- Fiji was one of the founding members of OFC in 1966.
- a dedicated referees association was established in 1954, showing organised technical structures before FIFA affiliation.
- OFC describes football as having a large following while competing with rugby and rugby league.
- current FIFA Forward funding is heavily infrastructure-weighted, with investment in headquarters, technical centre, pitches and futsal facilities.

Attribute interpretation:
- football tradition predates international affiliation substantially.
- 1950s technical organisation is supporting evidence for competition/institutional maturity.
- current infrastructure investment is a modern access/development/elite-support anchor only, not a historical backcast.
- Fiji is a useful case where small population does not imply negligible football culture.

### Papua New Guinea

Primary source:
- OFC member-association record: https://www.oceaniafootball.com/papua-new-guinea/

Verified anchors:
- PNGFA founded in 1962 and affiliated to FIFA in 1963.
- OFC describes roughly 200,000 participants in a population above seven million in the source's reference period.
- OFC explicitly identifies geography and developing-country conditions as obstacles to football development.
- PNGFA's national approach is described as a response to earlier regional fragmentation.

Attribute interpretation:
- participant totals support popularity/access only after population normalisation and source-date handling.
- difficult geography is direct access/development context and should not be inferred from competitive results.
- 1962-63 is a federation/international anchor, while pre-federation local football needs additional historical research.

### Solomon Islands

Primary sources:
- OFC member-association record: https://www.oceaniafootball.com/solomon-islands/
- OFC Honiara history: https://www.oceaniafootball.com/archives-15569/

Verified anchors:
- SIFF founded in 1978; FIFA membership in 1988.
- football is described by OFC as the national sport.
- Honiara Football Association existed from 1956 and organised major domestic competitions before SIFF took over that role.
- domestic/regional matches have drawn very large crowds relative to population.
- FIFA Goal-era infrastructure improved the principal international playing field.

Attribute interpretation:
- tradition/popularity clearly predate SIFF's 1978 foundation.
- the 1956 Honiara structure is a strong local competition/tradition anchor.
- SIFF foundation/FIFA membership are governance/international-access anchors rather than football-start dates.

### Cook Islands

Primary source:
- OFC member-association record: https://www.oceaniafootball.com/cook-islands/

Verified anchors:
- CIFA founded in 1971 and became a FIFA member in 1994.
- the association includes Rarotonga clubs plus Outer Island Associations.

Attribute interpretation:
- archipelagic structure is directly relevant to access/logistics.
- sparse population and late FIFA membership do not justify a universal minimum rating.
- association/network structure can support a transparent low-confidence access/competition model where earlier quantitative data is absent.

### American Samoa

Primary sources:
- OFC member-association record: https://www.oceaniafootball.com/american-samoa/
- OFC normalisation / youth-facility account: https://www.oceaniafootball.com/archives-6255/

Verified anchors:
- predecessor association founded in 1984; FIFA affiliation in 1998.
- FIFA normalisation occurred in 2006-08 and the current FFAS emerged after dissolution of the previous association.
- OFC reports a strong school/youth competition focus and unusually high youth uptake relative to other local sports in the source period.

Mandatory modelling rule:
- 2006-08 is a governance structural_transition, not a smooth interpolation.
- modern youth participation can support access/popularity/development evidence, but must not be backcast to 1984.
- territory status is handled at association level; political-sovereignty fields remain separate.

### Tahiti

Primary sources:
- FIFA Forward impact: https://inside.fifa.com/associations/TAH/impact
- FIFA Talent Academy / development update: https://inside.fifa.com/advancing-football/fifa-forward/news/tahiti-football-development-thierry-ariiotima-infantino

Verified anchors:
- Tahiti is a non-sovereign association whose football evidence must remain separate from France.
- modern FIFA Forward investment covers infrastructure, competitions and national-team support.
- the first FIFA Talent Academy in Oceania was launched in Tahiti in November 2025.
- FIFA explicitly notes geography/topography as development challenges and significant recent investment in facilities.

Attribute interpretation:
- 2025 is a strong modern development_quality / elite_support anchor.
- geography supports access/logistics context.
- France-level football observations must never be copied into Tahiti.

### New Caledonia

Primary source:
- FIFA Forward impact: https://inside.fifa.com/en/associations/NCL/impact

Verified anchors:
- New Caledonia is a distinct FIFA/OFC football association despite non-sovereign political status.
- current Forward allocations include competitions, national-team support, infrastructure and a technical centre.

Attribute interpretation:
- country/territory identity in the game model must be association-aware.
- metropolitan France data cannot substitute for New Caledonia-specific participation/development evidence.
- current project data is modern evidence only.

## Oceania confederation structure

Primary sources:
- OFC history: https://www.oceaniafootball.com/history/
- OFC current member list/statutes:
  https://www.oceaniafootball.com/member-associations/
  https://www.oceaniafootball.com/cms/wp-content/uploads/2024/06/OFC-Statutes-May-2024-signed.pdf

Verified anchors:
- OFC was formally approved in 1966.
- founding members: Australia, New Zealand, Fiji and Papua New Guinea; New Caledonia was provisionally involved because it lacked sporting autonomy at the time.
- OFC currently has 11 ordinary Member Associations plus associate members.
- OFC statutes explicitly allow football associations representing a country or territory, including non-independent regions with required authorisation.

Model implications:
- sovereign-country mapping and football-association mapping must be separate layers.
- non-sovereign members such as Tahiti/New Caledonia must have independent football observations and annual ratings where they exist in the Earth catalog.
- affiliation date is not the same as first organised football.
- territory football observations must never be merged into or duplicated from the governing sovereign state by default.

## Oceania-specific research conclusions

Oceania is especially useful for validating sparse-country methodology because it contains:
1. very old association history but football as a secondary national sport — New Zealand;
2. long football tradition in small populations — Fiji;
3. large participation with severe geographic/access constraints — Papua New Guinea;
4. football as a national sport despite a small and geographically fragmented population — Solomon Islands;
5. late-formalised archipelagic associations — Cook Islands;
6. governance discontinuity with strong youth structure — American Samoa;
7. non-sovereign football identities — Tahiti and New Caledonia;
8. a major confederation transition and professionalisation shock — Australia.

This means sparse data must be solved with country-specific structural evidence, not one low-rating default.

## Additional Oceania research still required

Before annual materialisation:
- verify historical federation/league anchors for Tahiti, New Caledonia, Samoa, Tonga and Vanuatu.
- add explicit associate-member / non-FIFA handling for Kiribati, Tuvalu and other Earth-catalog Pacific entities where applicable.
- retrieve source-dated participation counts where available rather than relying on undated profile text.
- Australia requires explicit NSL start (1977), Crawford-era governance transition (2003) and A-League professionalisation anchors in the structured dataset.
- New Zealand requires domestic league/professional pathway anchors to complement federation history.
- separate 11-a-side, futsal and beach-soccer evidence when source material mixes them.


## Historical entity and association mapping — first explicit ruleset

The following mappings are now sufficiently evidenced to freeze as research rules. These are not ratings; they govern ownership/inheritance of observations.

### Czechoslovakia -> Czechia + Slovakia

Primary evidence:
- UEFA Czechia history: https://www.uefa.com/news-media/news/0282-1830fd7e681b-d29c43b082a6-1000--developing-football-in-czechia/
- UEFA Slovakia history: https://www.uefa.com/nationalassociations/svk/
- UEFA split-history note: https://www.uefa.com/news-media/news/025f-0fda3a4bb12d-e23ea8111c7f-1000--slovakia-mourns-former-fa-president-milan-sluzanic/

Verified anchors:
- Czechoslovakia ceased to exist on 1 January 1993.
- Czech and Slovak modern national associations became separate thereafter.
- Slovak football also has an earlier distinct association/league period in 1938-45.
- Czech association roots predate Czechoslovakia.

Rules:
- 1955-1992 Czechoslovakia population/player/club observations belong to the predecessor entity and are never copied in full to both successors.
- Czechia/Slovakia may inherit tradition evidence only through explicitly localisable club, player, regional or institutional history.
- where predecessor evidence is not geographically separable, use a structural_transition estimate in 1993 rather than duplicate the predecessor observation.
- direct Czechoslovak competition results remain predecessor results; they can support successor tradition only with reduced/inherited confidence, not successor competition-quality observations for the same year.

### East Germany + West Germany -> Germany

Primary evidence:
- DFB history: https://www.dfb.de/historie

Verified anchor:
- the East German DFV was dissolved on 20 November 1990; the NOFV was created as successor and joined the DFB.

Rules:
- before unification, FRG/DFB and GDR/DFV observations are separate.
- do not sum or copy either state's historical rating directly into unified Germany.
- 1990-91 is a structural_transition year/period.
- unified Germany may inherit tradition from both structures, but contemporary access/development/competition/elite-support must be recomputed from post-unification evidence or explicit aggregation of non-overlapping source observations.
- population and player counts may only be aggregated when source definitions and observation dates are compatible.

### USSR -> successor states

Primary evidence:
- UEFA Russia history: https://www.uefa.com/nationalassociations/RUS/
- UEFA Ukraine history: https://www.uefa.com/nationalassociations/UKR/
- UEFA Estonia history: https://www.uefa.com/nationalassociations/EST/
- UEFA Lithuania history: https://www.uefa.com/nationalassociations/ltu/
- UEFA Latvia history: https://www.uefa.com/nationalassociations/LVA/
- UEFA Georgia history: https://www.uefa.com/nationalassociations/GEO/
- UEFA Armenia history: https://www.uefa.com/nationalassociations/ARM/

Verified anchors:
- USSR national football operated as a single international entity during the Soviet period.
- republican/local club systems and football organisations existed inside the USSR and are geographically attributable in many cases.
- Russia formed its post-Soviet union in February 1992 and assumed duties/functions of the former FFUSSR.
- Ukraine became self-governing in football in 1991 and launched its own competitions in 1992.
- Baltic associations have pre-Soviet independent histories; Soviet-era domestic football continued locally.
- Georgia had its own football federation operating under the Soviet system and launched an independent federation/league in 1990.
- Armenia's independent federation was founded in 1992 after substantial Soviet-era club history.

Rules:
- USSR national-team results and USSR-wide player/registration counts are never duplicated across successors.
- geographically attributable Soviet-era club, league, academy or participation evidence may support the relevant successor's local tradition/development history.
- republic-specific pre-Soviet history remains local to that successor where documented.
- Russia's institutional succession from FFUSSR does not entitle Russia to inherit every USSR-wide observation as a Russian country observation.
- 1990-94 should be modelled country-by-country as structural_transition, not one common linear split.
- Baltic states require restoration logic; Central Asian/Caucasus states require transition from Soviet-system local football to independent association structures.

### Yugoslavia -> successors

Primary evidence:
- UEFA Serbia history: https://www.uefa.com/nationalassociations/SRB/
- UEFA Croatia history: https://www.uefa.com/nationalassociations/CRO/
- UEFA Bosnia and Herzegovina history: https://www.uefa.com/nationalassociations/BIH/
- UEFA North Macedonia history: https://www.uefa.com/nationalassociations/MKD/
- UEFA Montenegro history: https://www.uefa.com/nationalassociations/mne/
- UEFA Kosovo history: https://www.uefa.com/nationalassociations/KOS/

Verified anchors:
- Serbia's association lineage traces to the Yugoslav Football Association founded in 1919.
- Croatia had distinct association structures before and during Yugoslav periods.
- Bosnia and Herzegovina had a football federation under the Yugoslav system from 1945.
- North Macedonia had a football association inside Yugoslavia from 1948 and independent FFM after 1991.
- Montenegro's association existed within Yugoslav/Serbia-Montenegro structures before independence; independent league began 2006/07 and UEFA/FIFA membership followed in 2007.
- Kosovo had its own football federation from 1946 within Yugoslav structures, reorganised after the 1999 war, and joined UEFA/FIFA in 2016.

Rules:
- Yugoslavia national-team observations remain predecessor observations.
- republic-local league/club/player/federation observations may remain attached to the geographic successor when sourceable.
- Serbia may inherit institutional lineage from the 1919 association where that specific legal/institutional continuity is relevant, but may not absorb all Yugoslav participation/results as Serbian observations.
- Croatia/Bosnia/North Macedonia/Montenegro/Kosovo do not receive duplicated Yugoslavia totals.
- Kosovo's tradition and local-competition evidence clearly predates 2016 international recognition; UEFA/FIFA membership must not be treated as the beginning of football.
- 1991-2007 transition rules vary by successor and must be explicit.

### Faroe Islands

Primary evidence:
- UEFA Faroe Islands history: https://www.uefa.com/nationalassociations/fro/

Verified anchors:
- first club 1892;
- first official national championship 1942;
- first cup 1955;
- independent football association 1979;
- FIFA membership 1988; UEFA 1990;
- artificial-turf introduction in 1986 materially changed participation conditions.

Rules:
- football tradition and domestic competition begin long before FIFA/UEFA membership.
- 1986 is a specific access/development infrastructure anchor.
- Faroe football observations are separate from Denmark despite political sovereignty links.

### Gibraltar

Primary evidence:
- UEFA Gibraltar history: https://www.uefa.com/nationalassociations/gib/
- UEFA membership anniversary: https://www.uefa.com/news-media/news/0284-18b391779f7f-d7e1097a7b9d-1000--gibraltar-celebrating-ten-years-of-uefa-membership/

Verified anchors:
- civilian football association formed in 1895.
- football competitions existed before UEFA/FIFA recognition.
- UEFA membership came in May 2013 after a long legal/accession process.

Rules:
- tradition/popularity/local competition must not start in 2013.
- Gibraltar observations remain separate from UK/England observations.
- delayed international recognition primarily constrains international competition access, not historical domestic tradition.

### Korea split

Rules already established from Korea Republic / DPR Korea research:
- pre-division Korean football history cannot be copied in full to both successors.
- Korea Republic may inherit documented institutional continuity from predecessor Korean association structures where source lineage supports it.
- DPR Korea requires separate post-division evidence.
- shared pre-division cultural/tradition context can be tagged as inherited_context, never duplicated quantitative observation.

### Non-sovereign associations

Applies to at least:
- England, Scotland, Wales, Northern Ireland vs UK geography;
- Faroe Islands vs Denmark;
- Gibraltar vs UK;
- Tahiti / New Caledonia vs France;
- Puerto Rico / US Virgin Islands vs USA;
- Cook Islands and other associated territories where applicable.

Rules:
- football association identity and political-sovereign identity are separate dimensions.
- population source must use the correct geographic territory.
- football observations belong to the association territory, not automatically to the sovereign state.
- sovereign-state football totals are never duplicated into constituent/territorial associations.
- where a political-geography package contains both sovereign and constituent entities, aggregation must be explicit and non-overlapping.

## Canonical transition record shape

Each non-trivial entity transition should eventually be encoded like:

```json
{
  "transition_id": "ussr_to_successors_1991",
  "effective_period": {"start": 1990, "end": 1994},
  "predecessor_entities": ["USSR"],
  "successor_entities": ["RUS", "UKR", "..."],
  "transition_type": "dissolution",
  "observation_rules": {
    "population": "no_duplicate; use territory-specific population series",
    "participation": "use republic-specific observations where available; otherwise comparative transition estimate",
    "results": "predecessor-only",
    "club_history": "geographically attributable",
    "tradition": "partial inherited context allowed",
    "development": "local evidence only or lower-confidence transition estimate",
    "elite_support": "local evidence only or lower-confidence transition estimate"
  },
  "interpolation_allowed": false,
  "confidence": "high",
  "source_ids": []
}
```

## New hard invariants for materialisation

1. No quantitative predecessor observation may be copied unchanged into more than one successor.
2. Results belong to the team/entity that achieved them; successor use is tradition-context only unless the competition itself legally/statistically treats continuity otherwise.
3. Club-local observations may follow geography when the club remained in that territory.
4. International-affiliation dates change international access, not necessarily domestic tradition.
5. Independence/split/merge periods block ordinary linear interpolation.
6. Successor ratings immediately after a split must be rebuilt from local evidence + explicit transition logic.
7. Legal/institutional succession does not automatically imply quantitative succession of the whole predecessor ecosystem.
8. Political sovereignty and football-association identity must remain separate.


## Prototype country set before numeric ratings

Before assigning any 1–10 values, FIFA Earth should be tested on a deliberately diverse prototype set. The purpose is to validate the temporal model and attribute separation, not to optimise ratings for famous countries.

### Prototype A — Japan

Required anchors:
- 1955 baseline: established federation/AFC membership, pre-professional domestic structure.
- 1965: Japan Soccer League launch.
- 1977: National Training Centre.
- 1986: limited professional-player licensing.
- 1991-93: J.League institutional/professional break.
- 1998: first men's FIFA World Cup appearance.
- 2002: World Cup co-hosting infrastructure/event environment.
- 2010s-2020s: academy/training-network evidence.
- 2026: partial-year evidence only.

Expected behaviour:
- tradition changes slowly.
- competition_quality and elite_support step materially around professionalisation.
- development_quality rises around training/pro pathway reforms.
- popularity/access may rise after J.League but require participation evidence rather than assuming the same step size.

### Prototype B — India

Required anchors:
- 1955 baseline: established AIFF/FIFA/AFC structure.
- 1977: Federation Cup.
- 1996: National Football League.
- modern period: I-League/ISL and grassroots/coaching evidence to be sourced before final values.

Expected behaviour:
- tradition and popularity can remain materially above elite competition quality.
- national-league formalisation should raise competition_quality/elite_support more than tradition.
- no result-based shortcut from national-team strength to popularity/access.

### Prototype C — Morocco

Required anchors:
- 1955: pre-independence league structure still active.
- 1956: FRMF/national championship consolidation.
- 1960: FIFA affiliation.
- 2009: Mohammed VI Academy.
- 2010s-2020s: expanding national/regional academy and infrastructure system.
- 2022-26: recent elite competitive evidence, used primarily as validation rather than retroactive input.

Expected behaviour:
- high tradition predates 1956.
- 2009+ development_quality/elite_support should show a structural rise.
- recent senior results must not be used to inflate 2009 retrospectively.

### Prototype D — Senegal

Required anchors:
- 1960 federation creation.
- 1964 FIFA/CAF affiliation.
- pre-2020 youth pathway evidence.
- 2020: national youth leagues introduced with FIFA Forward support.
- 2020s: continued youth/development and infrastructure programmes.

Expected behaviour:
- 2020 is an explicit development/competition-pathway break.
- later success may validate but cannot cause earlier ratings.
- tradition increases gradually; development_quality can change faster.

### Prototype E — South Africa

Required anchors:
- 1955-57: substantial domestic football / early CAF context.
- apartheid-era suspension/exclusion period.
- late 1970s: evidence of multiracial top-flight change.
- 1991: unified SAFA.
- 1992: restored FIFA/CAF international membership.
- 1996: AFCON win as post-transition competition evidence.

Expected behaviour:
- popularity/tradition must not collapse during international isolation.
- international competition access and governance/elite-support are disrupted.
- 1991-92 is non-interpolable structural_transition.
- competitive recovery after readmission is handled separately from local tradition.

### Prototype F — Argentina

Required anchors:
- 1955 baseline already reflects federation dating to 1893 and professionalisation since 1931.
- later anchor years should rely on domestic-league structure, player-development and participation evidence rather than only World Cup results.
- 2026 partial-year cutoff.

Expected behaviour:
- tradition is already near its mature historical regime by 1955 and moves slowly.
- competition_quality can fluctuate.
- elite_support/development may evolve without needing tradition to track them.

### Prototype G — United States

Required anchors:
- 1955 baseline: old federation and prior professional-league history but football not a dominant national spectator sport.
- later professional-league discontinuities must be explicitly represented.
- modern participation/youth, professional-league and national-training evidence require dedicated anchors.
- 2024+ national training-centre development is a modern elite/development anchor.

Expected behaviour:
- long tradition does not imply maximum popularity.
- access/participation can become strong while elite competition quality follows a different path.
- league collapse/relaunch periods must block naïve interpolation.

### Prototype H — Australia

Required anchors:
- 1955 pre-current-federation structure.
- 1960-63 governance/FIFA disruption.
- 1966 OFC founding.
- 1977 National Soccer League start.
- 2003 governance reset/Crawford-era transition.
- 2005 A-League launch.
- 2006 AFC transfer.
- 2020 league-governance separation.

Expected behaviour:
- 2005 professionalisation raises competition_quality/elite_support.
- 2006 confederation move changes competition context, not automatically popularity.
- governance disruptions affect elite-support/institutional confidence without erasing local football.

### Prototype I — New Zealand

Required anchors:
- 1955 baseline: federation dating to 1891, FIFA since 1948.
- 1966 OFC founding.
- late-2000s financial stress.
- 2010-11 World Cup-driven reinvestment into grassroots/development.
- 2026 OFC Pro League context, if used, must remain partial/current evidence.

Expected behaviour:
- high tradition relative to small population.
- popularity remains bounded by multi-sport/rugby-dominant context.
- institutional/elite-support capacity may fluctuate independently of tradition.

### Prototype J — Faroe Islands

Required anchors:
- 1955: official national championship already exists; inaugural cup in 1955.
- 1979: independent football association.
- 1986: artificial-turf intervention.
- 1988/1990: FIFA/UEFA accession.
- 1999: national stadium.
- later grassroots/competition evidence.

Expected behaviour:
- 1986 can materially improve access/development despite no sovereignty change.
- international recognition raises competition access but must not create tradition from zero.
- small population must not force minimum popularity per capita.

### Prototype K — Czechoslovakia -> Czechia / Slovakia

Required anchors:
- predecessor annual series 1955-1992.
- 1993 explicit split.
- Czech and Slovak successor series rebuilt from local evidence.
- Slovak 1938-45 historical association context allowed only as tradition context.

Expected behaviour:
- no duplicated 1992 predecessor values in both 1993 successors.
- competition/development/access may diverge quickly after independence.
- inherited tradition can be partial and evidence-based.

### Prototype L — USSR -> Russia / Ukraine / one Baltic / one Caucasus successor

Required anchors:
- predecessor series through dissolution.
- local Soviet-era club/federation evidence for each chosen successor.
- 1990-94 structural transitions.
- independent leagues/federations after transition.

Expected behaviour:
- USSR national-team results stay with USSR.
- local club/development history may follow geography.
- Russia's legal succession does not absorb every USSR-wide participation observation.
- Baltic restoration history differs from Ukraine/Russia and from Caucasus/Central Asia.

### Prototype M — Fiji / Papua New Guinea / Solomon Islands

Purpose:
- validate sparse/small-country comparative logic without flattening them.

Expected contrasts:
- Fiji: old federation and meaningful football culture despite small population.
- PNG: large participation but severe geographic/access constraints.
- Solomon Islands: football as national sport, local competition history predating SIFF, high relative popularity despite small scale.

## Prototype pass/fail checks

A prototype series fails before numeric rollout if any of the following occurs:

1. all six attributes move together through most anchor events;
2. a FIFA/UEFA/CAF/OFC affiliation date causes tradition to jump from near-zero despite older domestic history;
3. a later World Cup result materially raises an earlier year's development rating;
4. a successor receives the predecessor's full quantitative state without local evidence;
5. a small country is forced low purely due to absolute population;
6. a large country is forced high purely due to absolute player totals;
7. elite academy/infrastructure investment automatically creates high mass access;
8. professional-league creation instantly creates deep football tradition;
9. political independence alone resets local club/history evidence;
10. 2026 behaves as a full-year observation rather than a partial cutoff.

## Interpolation policy to test on prototypes

Allowed:
- gradual interpolation between compatible observed/derived anchors for the same entity and measurement regime;
- bounded carry-forward when source evidence indicates institutional continuity and no structural break;
- slow-moving tradition interpolation over long stable periods.

Not allowed:
- interpolation across independence/split/merge without a structural_transition node;
- interpolation across league collapse/relaunch or governance normalisation where the affected attribute changes regime;
- interpolation that uses later competitive results to infer earlier development;
- cross-country interpolation used as if it were observed history.

Comparative estimates:
- permitted only for missing dimensions/periods;
- require explicit peer set and rationale;
- confidence below directly observed/derived anchors;
- should use structural similarity (region, population/logistics, association age, league structure, economic/infrastructure context) rather than a single continental average.

## Claims explicitly rejected

Do not re-use illustrative or weakly sourced historical claims as facts. In particular, previous draft/research examples that are demonstrably incorrect or unverified must not enter source observations, anchors or ratings.

## Next research blocks

Recommended sequence from this checkpoint:
1. Africa country-specific institutional/development/professional anchors.
2. Asia structural cases and country dossiers.
3. South America + CONCACAF.
4. Oceania + territories/microstates.
5. final polity/association mapping table.
6. representative-country annual prototype.
7. realism audit.
8. only then full FIFA Earth materialisation.


## FIFA Big Count 2006 identity reconciliation

The FIFA Big Count source is association-level, while the Earth catalogue is a 250-entry geography catalogue. Source labels therefore must not be fuzzy-joined or silently coerced into current Earth entities.

Implemented research tooling:
- `config/earth_research/mappings/fifa_big_count_2006_identity_overrides.json`
- `scripts/reconcile_fifa_big_count_identities.py`
- `tests/application/test_fifa_big_count_identity_reconciliation.py`

### Resolution policy

Each source row must end in exactly one explicit state:

1. **unique normalized Earth name** — safe only when one Earth country name matches;
2. **explicit direct mapping** — for known naming differences such as China PR → CHN, Czech Republic → CZE, Chinese Taipei → TWN, Tahiti → PYF and Puerto Rico → PRI;
3. **declared aggregate member** — used when multiple non-overlapping FIFA associations map into one Earth geography;
4. **manual review** — used when the source-year geography cannot safely be attached to the modern Earth entity;
5. **unresolved** — a hard failure in strict reconciliation and not accepted for calibration.

No fuzzy matching is permitted.

### United Kingdom / home associations

Big Count 2006 reports England, Scotland, Wales and Northern Ireland separately, while the Earth catalogue contains `GBR` rather than four home-nation entities.

For participation-style quantities only:
- all players;
- registered players;
- unregistered players;
- clubs;
- officials;

the four non-overlapping association rows are explicitly aggregated into `GBR`.

This aggregation rule does **not** apply to national-team results, ranking history, association governance or other competition evidence. Those remain association-specific evidence and require a different modelling layer if used.

### Manual-review rows currently blocked

The following 2006 rows are intentionally not auto-joined:

- **Netherlands Antilles** — observation predates the political dissolution; current successor allocation is not safely derivable from the aggregate row.
- **Curacao** — extracted Big Count counts duplicate the Netherlands Antilles row exactly; do not double-count or attach automatically to `CUW`.
- **Serbia** — source year overlaps the Serbia and Montenegro dissolution; exact observation timing/territorial denominator must be reconciled before using a current `SRB` population denominator.
- **Sudan** — observation predates South Sudan independence; current `SDN` geography is not automatically compatible with the historical association total.

These are deliberate data-quality blocks, not missing-data zeros.

### Calibration implication

A Big Count row is usable for population-normalised calibration only after identity reconciliation. The pipeline must never divide an unresolved historical-association total by the population of a modern successor entity.

The identity report is deterministic and fails strict mode on unresolved rows or duplicate direct targets. This makes association/geography reconciliation a prerequisite for scaling the 2006 cross-country benchmark beyond the nine-country prototype.


## Global calibration checkpoints now implemented

Two source-specific Earth reconciliation + benchmark pipelines are now available for FIFA Earth research. They are research inputs, **not** direct rating generators.

### FIFA Big Count 2006

Implemented:
- explicit association → Earth identity reconciliation;
- no fuzzy joins;
- United Kingdom home associations aggregated into `GBR` only for additive participation-style counts;
- four historically unsafe rows blocked for manual review: Netherlands Antilles, Curacao, Serbia and Sudan;
- population-normalised 2006 benchmark using Earth population;
- PR-critical tests covering identity safety, GBR aggregation and selected per-capita checks.

Current result:
- 208 source rows;
- 201 safely benchmarked Earth entities;
- 49 Earth entities not represented by a safe benchmark row;
- manual-review historical rows are excluded rather than divided by modern successor populations.

Use:
- strongest as comparative evidence for `squash_popularity` and `squash_access`;
- not a direct measure of development, competition quality or elite support;
- all-player scope must remain explicit.

### FIFA Professional Football Report 2023

Implemented:
- page-aware identity reconciliation for 211 national pages/observations;
- explicit preservation of the page-38 identity conflict: source label `KUWAIT`, Kyrgyzstan flag/emblem;
- page 37 remains the safe Kuwait observation; page 38 is not auto-joined to either `KWT` or `KGZ`;
- four UK home associations aggregate into `GBR`, but any missing member value keeps the Earth-level aggregate `null`;
- known partial sums are retained separately and never promoted to complete totals;
- population-normalised 2023 benchmark for safely reconciled Earth entities;
- published global totals and extracted national-page sums remain separate because they disagree.

Current result:
- 211 source observations, 210 unique association labels;
- 207 safely reconciled Earth entities;
- 43 Earth entities without a safe 2023 professional benchmark entity;
- one explicitly blocked identity-conflict page;
- missing professional-player/club values remain `null`, never zero.

Use:
- comparative evidence mainly for professional ecosystem depth, `competition_quality` and `elite_support`;
- men's professional scope must remain explicit;
- 2023 Earth population is only a normalising denominator and does not imply one exact common observation date for every association.

### Combined interpretation

The two checkpoints intentionally measure different things:
- **2006 Big Count**: broad participation / organised-access footprint;
- **2023 Professional Report**: professional ecosystem / elite structure.

They must not be collapsed into one generic football-strength score. The six FIFA Earth attributes remain independently reasoned from multiple evidence streams.

The nine-country prototype can now be audited against global comparative distributions instead of only pairwise intuition. The next research step is to derive robust percentile/band diagnostics from these benchmarks and use them as calibration evidence, while keeping historical anchors, structural breaks and country-specific sources authoritative for the 1955–2026 trajectories.
