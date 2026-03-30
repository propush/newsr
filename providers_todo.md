# Provider Implementation Backlog

This file is the execution backlog for expanding NewsR with additional built-in providers. Each provider card below is intended to be implementation-ready: a later agent should be able to pick one card, follow [docs/add_provider.md](/Users/pushkin/projects/newsr/docs/add_provider.md), implement the provider, run the required tests, update docs, and leave a short iteration note without reopening product decisions.

## Global Rules

- Follow [docs/add_provider.md](/Users/pushkin/projects/newsr/docs/add_provider.md) for the provider contract and architectural constraints.
- Keep all provider-specific behavior inside `src/newsr/providers/<provider_id>/`.
- Do not add provider-specific branches to the refresh pipeline, storage, or UI unless the provider exposes a real new generic requirement.
- Use `cancellable_read` in every network-facing code path.
- Preserve provider-scoped identity: `article_id = f"{provider_id}:{provider_article_id}"`.
- Derive `provider_article_id` from canonical URL structure or another stable provider-local identifier.
- Keep provider enablement and target selection in SQLite-backed state; do not add them to `newsr.yml`.
- New providers start disabled by default unless a provider card explicitly says otherwise.
- Prefer a small curated target catalog in v1. Discovery is optional and should be deferred unless it clearly improves the provider.
- Filter out non-article content aggressively in provider-local parsing: podcasts, videos, newsletters, events, sponsor pages, author hubs, and landing pages should not leak into candidate lists.
- After each provider implementation, update docs under `docs/` if the built-in catalog or provider workflow documentation changed.

## Definition Of Done

A provider iteration is done only when all of the following are true:

- provider package added under `src/newsr/providers/<provider_id>/`
- registry updated in `src/newsr/providers/registry.py`
- bootstrap defaults decided and aligned with the provider card
- listing and article fixtures added under `tests/fixtures/`
- provider-specific tests added under `tests/providers/<provider_id>/`
- stable `provider_article_id` derivation covered by tests
- targeted tests run and recorded in the iteration note
- provider-related docs updated if needed

## Progress Table

| Priority | Provider | provider_id | Domain | Strategy | Complexity | Status | Last note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | HR Dive | `hrdive` | HR/workplace | Static | Low-medium | Done | 2026-03-28: implemented with static live-topic catalog (`talent`, `compensation-benefits`, `diversity-inclusion`, `learning`, `hr-management`) and disabled bootstrap |
| 2 | MedCity News | `medcitynews` | Healthcare/medtech | Static | Low-medium | Done | 2026-03-28: implemented with static live-channel catalog (`health-tech`, `biopharma`, `medical-devices-and-diagnostics`, `consumer-employer`) and disabled bootstrap |
| 3 | Hyperallergic | `hyperallergic` | Art/culture | Static | Medium | Done | 2026-03-28: implemented with static tag-backed category catalog (`news`, `reviews`, `opinion`, `film`) and disabled bootstrap |
| 4 | EdSurge | `edsurge` | Education | Static now, discovery later | Medium | Done | 2026-03-28: implemented with live `k-12`, `higher-ed`, and `artificial-intelligence` targets and disabled bootstrap |
| 5 | Marketing Dive | `marketingdive` | Marketing/media | Static | Low-medium | Done | 2026-03-28: implemented with static topic/latest catalog (`brand-strategy`, `mobile`, `creative`, `social-media`, `video`, `agencies`, `data-analytics`, `influencer`, `marketing`, `ad-tech`, `cmo-corner`) and disabled bootstrap |
| 6 | Tom's Hardware | `tomshardware` | Hardware/PC/semiconductors | Static | Medium | Done | 2026-03-28: implemented with static section catalog (`pc-components`, `cpus`, `gpus`, `storage`, `laptops`, `desktops`, `software`, `artificial-intelligence`) and disabled bootstrap |
| 7 | Canary Media | `canarymedia` | Climate/energy | Mixed | Medium | Done | 2026-03-30: implemented with a static live-vertical catalog (`grid-edge`, `energy-storage`, `solar`, `electrification`, `transportation`), path-derived `/articles/...` article ids, and disabled bootstrap |
| 8 | Lawfare | `lawfare` | Legal/policy/tech governance | Mixed | Medium | Done | 2026-03-30: implemented with static live-topic catalog (`cybersecurity-tech`, `surveillance-privacy`, `intelligence`, `foreign-relations-international-law`), canonical `/article/<slug>` article ids, podcast/multimedia title rejection, and disabled bootstrap |
| 9 | ScienceDaily | `sciencedaily` | Science/research | Static now, discovery later | Low-medium | Done | 2026-03-30: implemented with static live-category catalog (`health_medicine`, `computers_math`, `earth_climate`, `mind_brain`, `matter_energy`), normalized `releases/YYYY/MM/<id>` article ids, and disabled bootstrap |
| 10 | InfoQ | `infoq` | Software engineering | Mixed | Medium-high | Done | 2026-03-30: implemented with static live-topic catalog (`software-architecture`, `cloud-architecture`, `devops`, `ai-ml-data-engineering`, `java`), canonical `news/...` and `articles/...` path ids, and topic-page parsing limited to written `News` and `Articles` sections so podcasts, presentations, and guides are excluded |
| 11 | Deloitte Insights | `deloitteinsights` | Consulting/research/business strategy | Mixed | Medium-high | Done | 2026-03-28: implemented with static live-topic catalog (`business-strategy-growth`, `technology-management`, `talent`, `operations`, `economy`), search-backed candidate discovery, research-hub-aware article parsing, and disabled bootstrap |
| 12 | Harvard Business Review | `hbr` | Management/leadership/business | Static | High | Done | 2026-03-28: implemented with static live-subject catalog (`leadership`, `strategy`, `innovation`, `managing-people`, `managing-yourself`), strict digital-article filtering, and disabled bootstrap |

## Shared Implementation Template

Apply this structure to every provider implementation:

1. Profile the source and confirm the provider card still matches the live site.
2. Add:
   - `src/newsr/providers/<provider_id>/__init__.py`
   - `src/newsr/providers/<provider_id>/provider.py`
   - `src/newsr/providers/<provider_id>/parsing.py`
   - `src/newsr/providers/<provider_id>/urls.py`
   - optional `src/newsr/providers/<provider_id>/catalog.py`
3. Register the provider in `src/newsr/providers/registry.py`.
4. Add fixtures:
   - `tests/fixtures/<provider_id>_listing_*.html`
   - `tests/fixtures/<provider_id>_article_*.html`
5. Add tests:
   - `tests/providers/<provider_id>/test_<provider_id>_provider.py`
6. Update docs if the built-in provider catalog or workflow changed.
7. Run provider-specific tests and any directly impacted tests.

Every provider test suite should cover:

- `default_targets()` returns the expected starter catalog
- default `selected=True` targets match the provider card
- `fetch_candidates()` returns only candidates for the selected target
- duplicate listing links are deduped
- obvious non-article links are rejected
- `fetch_article()` extracts title and body cleanly
- `provider_article_id` is stable and provider-scoped
- registry wiring succeeds

For mixed-format sources, add explicit negative tests for sponsor content, podcasts, videos, interactives, and landing pages.

## Provider Cards

### 1. HR Dive

- Status: `done`
- URL: `https://www.hrdive.com/`
- `provider_id`: `hrdive`
- Why: adds HR, recruiting, compensation, and workforce coverage outside the existing general tech/security mix.
- V1 scope: static `category` targets.
- Non-goals: live target discovery, podcasts, webinars, whitepapers, employer-resource hubs.
- Initial targets:
  - `talent`
  - `compensation-benefits`
  - `diversity-inclusion`
  - `learning`
  - `hr-management`
- Default selected targets:
  - `talent`
  - `compensation-benefits`
- Stable ID rule: derive `provider_article_id` from the canonical article URL path.
- Candidate extraction rules:
  - parse target listing pages only
  - accept only canonical article links
  - dedupe repeated article cards and promo repeats
- Article extraction rules:
  - extract title, body, optional author, optional published date
  - strip related links, sponsor callouts, and newsletter blocks
- Rejection rules:
  - audio-only items
  - sponsored resources
  - event pages
  - signup and landing pages
- Bootstrap default: disabled
- Expected files:
  - `src/newsr/providers/hrdive/__init__.py`
  - `src/newsr/providers/hrdive/provider.py`
  - `src/newsr/providers/hrdive/parsing.py`
  - `src/newsr/providers/hrdive/urls.py`
  - optional `src/newsr/providers/hrdive/catalog.py`
  - `tests/providers/hrdive/test_hrdive_provider.py`
- Fixtures:
  - one listing fixture per selected target style
  - at least one full article fixture
- Docs to update:
  - provider catalog docs if new built-ins are enumerated anywhere under `docs/`
- Complexity: low-medium
- Risks:
  - article listings may mix resource or sponsor blocks
- Acceptance checklist:
  - [x] default targets match the implemented live-topic catalog
  - [x] sponsor/resource links are rejected
  - [x] article body extraction removes promo boilerplate
  - [x] provider tests pass
- Implementation note: the live site currently exposes topic pages such as `talent`, `compensation-benefits`, `diversity-inclusion`, `learning`, and `hr-management`; the provider uses those concrete topics instead of the older backlog shorthand labels.

### 2. MedCity News

- Status: `done`
- URL: `https://medcitynews.com/`
- `provider_id`: `medcitynews`
- Why: adds healthcare innovation, medtech, biotech, and policy coverage.
- V1 scope: static `category` targets.
- Non-goals: events, podcasts, investor databases, author hubs.
- Initial targets:
  - `health-tech`
  - `biopharma`
  - `medical-devices-and-diagnostics`
  - `consumer-employer`
- Default selected targets:
  - `health-tech`
  - `medical-devices-and-diagnostics`
- Stable ID rule: canonical article URL path slug.
- Candidate extraction rules:
  - parse target/category listing pages
  - accept only canonical MedCity News article pages, including contributor/opinion articles that use the standard article format
  - dedupe repeated teaser cards
- Article extraction rules:
  - extract readable article text
  - remove embedded sponsor/video cards, related-link blocks, newsletter prompts, and promo content
- Rejection rules:
  - events
  - podcasts
  - sponsored posts
  - videos
  - contributor indexes
  - non-article landing pages
- Bootstrap default: disabled
- Expected files:
  - `src/newsr/providers/medcitynews/__init__.py`
  - `src/newsr/providers/medcitynews/provider.py`
  - `src/newsr/providers/medcitynews/parsing.py`
  - `src/newsr/providers/medcitynews/urls.py`
  - optional `src/newsr/providers/medcitynews/catalog.py`
  - `tests/providers/medcitynews/test_medcitynews_provider.py`
- Fixtures:
  - category listing fixtures
  - one representative article fixture
- Complexity: low-medium
- Risks:
  - mixed contributor and sponsored formats may need tailored filtering if site markup changes
- Acceptance checklist:
  - [x] default targets match the live-channel catalog
  - [x] sponsor/video and non-article links are rejected
  - [x] article parser handles standard news posts and contributor-format articles
  - [x] provider tests pass
- Implementation note: the live site currently exposes `Health Tech`, `BioPharma`, `Devices & Diagnostics`, and `Consumer / Employer` under `category/channel/*`; the provider uses those live channels instead of the older backlog placeholders.

### 3. Hyperallergic

- Status: `done`
- URL: `https://hyperallergic.com/`
- `provider_id`: `hyperallergic`
- Why: adds art criticism, culture coverage, and reviews.
- V1 scope: static `category` targets.
- Non-goals: opportunities, community notices, newsletters, shopping or guide pages.
- Initial targets:
  - `news`
  - `reviews`
  - `opinion`
  - `film`
- Default selected targets:
  - `news`
  - `reviews`
- Stable ID rule: canonical article path slug.
- Candidate extraction rules:
  - parse category pages
  - accept canonical article URLs only
  - dedupe repeat placements across hero and feed modules
- Article extraction rules:
  - extract title, byline, publish date, and readable body
  - remove share blocks, related links, signup prompts, and calls for support
- Rejection rules:
  - community posts
  - opportunities
  - newsletter links
  - sponsor pages
- Bootstrap default: disabled
- Expected files:
  - `src/newsr/providers/hyperallergic/__init__.py`
  - `src/newsr/providers/hyperallergic/provider.py`
  - `src/newsr/providers/hyperallergic/parsing.py`
  - `src/newsr/providers/hyperallergic/urls.py`
  - optional `src/newsr/providers/hyperallergic/catalog.py`
  - `tests/providers/hyperallergic/test_hyperallergic_provider.py`
- Fixtures:
  - one category listing fixture with mixed cards
  - one standard article fixture
- Complexity: medium
- Risks:
  - feed pages may interleave non-article editorial formats
- Acceptance checklist:
  - [x] non-article feed items are rejected
  - [x] body extraction preserves readable review/article text
  - [x] provider tests pass
- Implementation note: the live site currently exposes the selected feeds as tag pages like `/tag/news/` and `/tag/reviews/`; the provider keeps NewsR's generic `category` model and stores those live tag paths in target payloads.

### 4. EdSurge

- Status: `done`
- URL: `https://www.edsurge.com/`
- `provider_id`: `edsurge`
- Why: adds education coverage spanning K-12, higher education, and AI in learning.
- V1 scope: static `category` targets now, discovery later only if topic navigation proves stable.
- Non-goals: jobs, events, newsletters, marketplace/product pages.
- Initial targets:
  - `k12`
  - `higher-ed`
  - `artificial-intelligence`
- Default selected targets:
  - `k12`
  - `higher-ed`
- Stable ID rule: canonical `/news/<date>-<slug>` path.
- Candidate extraction rules:
  - parse topic/news listing pages
  - accept only article links under the news section
  - dedupe featured and repeated feed placements
- Article extraction rules:
  - extract readable article body
  - remove related-content blocks, newsletter prompts, and partner promos
- Rejection rules:
  - events
  - jobs
  - product or marketplace pages
  - non-news landing pages
- Bootstrap default: disabled
- Expected files:
  - `src/newsr/providers/edsurge/__init__.py`
  - `src/newsr/providers/edsurge/provider.py`
  - `src/newsr/providers/edsurge/parsing.py`
  - `src/newsr/providers/edsurge/urls.py`
  - optional `src/newsr/providers/edsurge/catalog.py`
  - `tests/providers/edsurge/test_edsurge_provider.py`
- Fixtures:
  - one K-12 or higher-ed listing fixture
  - one article fixture
- Complexity: medium
- Risks:
  - topic pages and navigation labels may drift over time
- Acceptance checklist:
  - [x] targets map to working news/topic pages
  - [x] non-news pages are rejected
  - [x] provider tests pass
- Implementation note: the live site currently uses `https://www.edsurge.com/news/k-12`, `https://www.edsurge.com/news/higher-ed`, and `https://www.edsurge.com/news/topics/artificial-intelligence`; the provider uses those live paths instead of the older `/news/topics/k-12` style.

### 5. Marketing Dive

- Status: `done`
- URL: `https://www.marketingdive.com/`
- `provider_id`: `marketingdive`
- Why: adds marketing, advertising, and media strategy coverage.
- V1 scope: static `category` targets.
- Non-goals: videos, events, sponsor content, whitepapers.
- Initial targets:
  - `brand-strategy`
  - `mobile`
  - `creative`
  - `social-media`
  - `video`
  - `agencies`
  - `data-analytics`
  - `influencer`
  - `marketing`
  - `ad-tech`
  - `cmo-corner`
- Default selected targets:
  - `social-media`
  - `brand-strategy`
- Stable ID rule: canonical article URL path.
- Candidate extraction rules:
  - parse category/topic pages
  - accept article links only
  - dedupe multi-slot repeats
- Article extraction rules:
  - strip related stories, sponsor modules, and signup prompts
- Rejection rules:
  - sponsor pages
  - events
  - webinars
  - non-article landing links
- Bootstrap default: disabled
- Expected files:
  - `src/newsr/providers/marketingdive/__init__.py`
  - `src/newsr/providers/marketingdive/provider.py`
  - `src/newsr/providers/marketingdive/parsing.py`
  - `src/newsr/providers/marketingdive/urls.py`
  - optional `src/newsr/providers/marketingdive/catalog.py`
  - `tests/providers/marketingdive/test_marketingdive_provider.py`
- Fixtures:
  - category listing fixture
  - standard article fixture
- Complexity: low-medium
- Risks:
  - video and sponsor modules may resemble article cards
- Acceptance checklist:
  - [x] non-article tiles are rejected
  - [x] article content parses cleanly
  - [x] provider tests pass
- Implementation note: the provider uses a static topic/latest catalog backed by `/topic/brand-strategy/`, `/topic/mobile-marketing/`, `/topic/creative/`, `/topic/social-media/`, `/topic/video/`, `/topic/agencies/`, `/topic/analytics/`, `/topic/influencer-marketing/`, `/`, `/topic/marketing-tech/`, and `/topic/cmo-corner/`; `data-analytics`, `influencer`, and `ad-tech` keep concise target keys while mapping to the live `analytics`, `influencer-marketing`, and `marketing-tech` paths, and `marketing` maps to the site root because there is no dedicated live topic page for it.

### 6. Tom's Hardware

- Status: `done`
- URL: `https://www.tomshardware.com/`
- `provider_id`: `tomshardware`
- Why: adds hardware, GPUs, CPUs, storage, and semiconductor-adjacent coverage.
- V1 scope: static `category` targets.
- Non-goals: deals pages, shopping guides, benchmark tools, galleries.
- Initial targets:
  - `pc-components`
  - `cpus`
  - `gpus`
  - `storage`
  - `laptops`
  - `desktops`
  - `software`
  - `artificial-intelligence`
- Default selected targets:
  - `pc-components`
  - `cpus`
  - `gpus`
- Stable ID rule: canonical article path slug.
- Candidate extraction rules:
  - parse section/category pages
  - accept article links only
  - dedupe hero and feed placements
- Article extraction rules:
  - extract readable review/news body
  - strip affiliate-style modules, galleries, related links, and newsletter prompts
- Rejection rules:
  - deals pages
  - shopping guides
  - galleries
  - benchmark landing pages
- Bootstrap default: disabled
- Expected files:
  - `src/newsr/providers/tomshardware/__init__.py`
  - `src/newsr/providers/tomshardware/provider.py`
  - `src/newsr/providers/tomshardware/parsing.py`
  - `src/newsr/providers/tomshardware/urls.py`
  - optional `src/newsr/providers/tomshardware/catalog.py`
  - `tests/providers/tomshardware/test_tomshardware_provider.py`
- Fixtures:
  - one section listing fixture
  - one article fixture
- Complexity: medium
- Risks:
  - commerce and review formatting may require strong content filtering
- Acceptance checklist:
  - [x] commerce/deals pages are rejected
  - [x] article body excludes affiliate clutter
  - [x] provider tests pass
- Implementation note: the provider uses static sections rooted at `/pc-components`, `/pc-components/cpus`, `/pc-components/gpus`, `/pc-components/storage`, `/laptops/news`, `/desktops`, `/software`, and `/tech-industry/artificial-intelligence`, while filtering out best-pick, deals, and other commerce-heavy listing entries.

### 7. Canary Media

- Status: `done`
- URL: `https://www.canarymedia.com/`
- `provider_id`: `canarymedia`
- Why: adds climate, electrification, utilities, and clean-energy coverage.
- V1 scope: curated mixed model.
- Non-goals: full live discovery of every vertical, podcasts, events, and static research hubs.
- Initial targets:
  - `grid-edge`
  - `energy-storage`
  - `solar`
  - `electrification`
  - `transportation`
- Default selected targets:
  - `grid-edge`
  - `solar`
- Stable ID rule: canonical article path under `/articles/...`.
- Candidate extraction rules:
  - parse article vertical pages
  - accept article links only
  - preserve target context in candidate category
- Article extraction rules:
  - strip support/signup prompts, inline promos, and related-content modules
- Rejection rules:
  - podcasts
  - event pages
  - landing pages without article bodies
- Bootstrap default: disabled
- Expected files:
  - `src/newsr/providers/canarymedia/__init__.py`
  - `src/newsr/providers/canarymedia/provider.py`
  - `src/newsr/providers/canarymedia/parsing.py`
  - `src/newsr/providers/canarymedia/urls.py`
  - optional `src/newsr/providers/canarymedia/catalog.py`
  - `tests/providers/canarymedia/test_canarymedia_provider.py`
- Fixtures:
  - one vertical listing fixture
  - one article fixture
- Complexity: medium
- Risks:
  - vertical taxonomy may need later refinement if the site navigation changes
- Acceptance checklist:
  - [x] curated targets map to article-bearing pages
  - [x] non-article pages are rejected
  - [x] provider tests pass
- Implementation note: the provider uses static live article verticals rooted at `/articles/grid-edge`, `/articles/energy-storage`, `/articles/solar`, `/articles/electrification`, and `/articles/transportation`, while deriving stable ids from canonical `/articles/<topic>/<slug>` paths.

### 8. Lawfare

- Status: `done`
- URL: `https://www.lawfaremedia.org/`
- `provider_id`: `lawfare`
- Why: adds law, national security, cyber policy, and surveillance/privacy coverage.
- V1 scope: mixed `topic` targets.
- Non-goals: podcasts, videos, webinars, and broad topic discovery.
- Initial targets:
  - `cybersecurity-tech`
  - `surveillance-privacy`
  - `intelligence`
  - `foreign-relations-international-law`
- Default selected targets:
  - `cybersecurity-tech`
  - `surveillance-privacy`
- Stable ID rule: canonical article path slug.
- Candidate extraction rules:
  - parse topic pages
  - accept written article links only
  - dedupe hero and repeat placements
- Article extraction rules:
  - strip related reading, subscription prompts, share blocks, and podcast embeds
- Rejection rules:
  - podcasts
  - multimedia
  - topic landing pages without article bodies
- Bootstrap default: disabled
- Expected files:
  - `src/newsr/providers/lawfare/__init__.py`
  - `src/newsr/providers/lawfare/provider.py`
  - `src/newsr/providers/lawfare/parsing.py`
  - `src/newsr/providers/lawfare/urls.py`
  - optional `src/newsr/providers/lawfare/catalog.py`
  - `tests/providers/lawfare/test_lawfare_provider.py`
- Fixtures:
  - one topic listing fixture
  - one standard article fixture
- Complexity: medium
- Risks:
  - topic pages may mix podcasts and essays heavily
- Acceptance checklist:
  - [x] podcasts are excluded from candidate extraction
  - [x] standard written articles parse cleanly
  - [x] provider tests pass
- Implementation note: the provider uses the live `/topics/cybersecurity-tech`, `/topics/surveillance-privacy`, `/topics/intelligence`, and `/topics/foreign-relations-international-law` paths, derives stable article ids from canonical `/article/<slug>` URLs, and rejects Lawfare podcast and multimedia entries by title pattern during candidate extraction.

### 9. ScienceDaily

- Status: `done`
- URL: `https://www.sciencedaily.com/`
- `provider_id`: `sciencedaily`
- Why: adds science and research summaries across health, technology, environment, and neuroscience.
- V1 scope: static `category` targets now, discovery later only if the category tree proves worth maintaining.
- Non-goals: external off-site links, full category discovery, topic archive navigation.
- Initial targets:
  - `health`
  - `technology`
  - `environment`
  - `mind-brain`
  - `matter-energy`
- Default selected targets:
  - `health`
  - `technology`
- Stable ID rule: canonical release/article path.
- Candidate extraction rules:
  - parse category pages
  - accept internal article links only
  - reject index/archive and external-source links
- Article extraction rules:
  - extract title, source summary, and main body
  - strip related-topic, subscription, and navigation clutter
- Rejection rules:
  - external handoff links
  - archives
  - index pages
  - pages without usable body text
- Bootstrap default: disabled
- Expected files:
  - `src/newsr/providers/sciencedaily/__init__.py`
  - `src/newsr/providers/sciencedaily/provider.py`
  - `src/newsr/providers/sciencedaily/parsing.py`
  - `src/newsr/providers/sciencedaily/urls.py`
  - optional `src/newsr/providers/sciencedaily/catalog.py`
  - `tests/providers/sciencedaily/test_sciencedaily_provider.py`
- Fixtures:
  - category listing fixture
  - one article fixture
- Complexity: low-medium
- Risks:
  - some content may be shorter source summaries than standard news articles
- Acceptance checklist:
  - [x] external links are rejected
  - [x] body extraction yields readable text
  - [x] provider tests pass
- Implementation note: the live site labels and paths are used directly in v1, so the provider targets are `Health & Medicine`, `Computers & Math`, `Earth & Climate`, `Mind & Brain`, and `Matter & Energy` backed by `/news/<slug>/` pages.

### 10. InfoQ

- Status: `done`
- URL: `https://www.infoq.com/`
- `provider_id`: `infoq`
- Why: adds software architecture, DevOps, cloud, and engineering-practice coverage.
- V1 scope: mixed `topic` targets.
- Non-goals: feeds, conference pages, videos, talk pages, and full discovery.
- Initial targets:
  - `software-architecture`
  - `cloud-architecture`
  - `devops`
  - `ai-ml-data-engineering`
  - `java`
- Default selected targets:
  - `software-architecture`
  - `cloud-architecture`
- Stable ID rule: canonical article path slug.
- Candidate extraction rules:
  - parse topic pages or equivalent article-bearing sections
  - accept written article links only
  - reject talks, presentations, and video content
- Article extraction rules:
  - strip registration prompts, event promos, and related-content modules
- Rejection rules:
  - conference pages
  - video pages
  - podcast/media items
  - non-article talk pages
- Bootstrap default: disabled
- Expected files:
  - `src/newsr/providers/infoq/__init__.py`
  - `src/newsr/providers/infoq/provider.py`
  - `src/newsr/providers/infoq/parsing.py`
  - `src/newsr/providers/infoq/urls.py`
  - optional `src/newsr/providers/infoq/catalog.py`
  - `tests/providers/infoq/test_infoq_provider.py`
- Fixtures:
  - topic listing fixture with mixed cards
  - one standard article fixture
- Complexity: medium-high
- Risks:
  - topic pages may mix articles, presentations, and event material
- Acceptance checklist:
  - [x] non-article content is rejected
  - [x] topic context is preserved on candidates
  - [x] provider tests pass
- Implementation note: the live site currently exposes the curated targets as topic pages rooted at `/architecture/`, `/cloud-architecture/`, `/devops/`, `/ai-ml-data-eng/`, and `/java/`; the provider treats those pages as static topic feeds and only ingests entries from their written `News` and `Articles` sections.

### 11. Deloitte Insights

- Status: `done`
- URL: `https://www.deloitte.com/us/en/insights.html?icid=top_insights`
- `provider_id`: `deloitteinsights`
- Why: adds consulting, economic, operations, workforce, and strategy research coverage.
- V1 scope: mixed `topic` targets.
- Non-goals: interactives, dashboards, videos, podcasts, webcasts, and industry hub discovery.
- Initial targets:
  - `strategy`
  - `technology`
  - `workforce`
  - `operations`
  - `economics`
- Default selected targets:
  - `strategy`
  - `technology`
- Stable ID rule: canonical article path slug.
- Candidate extraction rules:
  - parse topic or article index pages only
  - accept long-form article pages with readable body text
  - reject non-article research assets
- Article extraction rules:
  - strip signup prompts, navigation, inline promos, and download-callout clutter
- Rejection rules:
  - interactives
  - dashboards
  - videos
  - webcasts
  - research-center landing pages
- Bootstrap default: disabled
- Expected files:
  - `src/newsr/providers/deloitteinsights/__init__.py`
  - `src/newsr/providers/deloitteinsights/provider.py`
  - `src/newsr/providers/deloitteinsights/parsing.py`
  - `src/newsr/providers/deloitteinsights/urls.py`
  - optional `src/newsr/providers/deloitteinsights/catalog.py`
  - `tests/providers/deloitteinsights/test_deloitteinsights_provider.py`
- Fixtures:
  - topic listing fixture with mixed asset types
  - one standard article fixture
- Complexity: medium-high
- Risks:
  - site mixes many non-article formats into the same navigation surfaces
- Acceptance checklist:
  - [x] non-article assets are rejected
  - [x] article body extraction remains readable
  - [x] provider tests pass
- Implementation note: the live Deloitte topic pages currently map cleanly to `business-strategy-growth`, `technology-management`, `talent`, `operations`, and `economy`; the provider keeps those stable topic slugs in storage, uses human-readable labels in the UI, and fetches candidate cards from Deloitte's first-party search endpoint because the topic pages render their article grids client-side.

### 12. Harvard Business Review

- Status: `done`
- URL: `https://hbr.org/`
- `provider_id`: `hbr`
- Why: adds management, leadership, strategy, and workplace advice content.
- V1 scope: static `topic` targets.
- Non-goals: podcasts, videos, magazines, sponsor content, reading lists, archive pages, and subscriber-only pages without usable body text.
- Initial targets:
  - `leadership`
  - `strategy`
  - `innovation`
  - `managing-teams`
  - `managing-yourself`
- Default selected targets:
  - `leadership`
  - `strategy`
- Stable ID rule: canonical article path slug.
- Candidate extraction rules:
  - parse topic pages only
  - accept written article links that produce usable article bodies
  - reject mixed-format cards aggressively
- Article extraction rules:
  - extract title, body, optional author, optional published date
  - remove subscription prompts, share blocks, and related-content modules
- Rejection rules:
  - podcasts
  - videos
  - archive/magazine pages
  - reading lists
  - sponsor content
  - unusable subscriber-only pages
- Bootstrap default: disabled
- Expected files:
  - `src/newsr/providers/hbr/__init__.py`
  - `src/newsr/providers/hbr/provider.py`
  - `src/newsr/providers/hbr/parsing.py`
  - `src/newsr/providers/hbr/urls.py`
  - optional `src/newsr/providers/hbr/catalog.py`
  - `tests/providers/hbr/test_hbr_provider.py`
- Fixtures:
  - topic listing fixture with mixed card types
  - one free article fixture
  - one negative fixture for a gated or unusable page shape if needed
- Complexity: high
- Risks:
  - paywall and mixed-format content may require stronger rejection logic than any current built-in provider
- Acceptance checklist:
  - [x] gated or unusable pages are rejected safely
  - [x] mixed-format topic cards do not leak into candidates
  - [x] provider tests pass
- Implementation note: the live HBR topic pages currently use `topic/subject/*` URLs, and the older backlog label `managing-teams` maps to the live `managing-people` subject slug.

## Decision Log

- Chosen: diversity-first provider set across education, art, HR, software, hardware, healthcare, energy, marketing, law/policy, science, consulting, and management.
- Chosen: mixed implementation strategy.
  Static catalogs where possible; discovery only when it is clearly useful and stable.
- Chosen: all new providers disabled by default at bootstrap.
- Chosen: `hbr` and `deloitteinsights` remain in scope despite higher parsing risk because they broaden the catalog meaningfully and still appear implementable with strong rejection logic.

## Cross-Provider Risks

- Many modern media sites mix article cards with podcasts, events, webinars, sponsor content, and signup modules.
- Some providers may expose topic navigation that is useful for curation but too unstable for live discovery in v1.
- Several providers may require more aggressive article-body cleanup than the current built-ins.
- `hbr` and `deloitteinsights` are the highest-risk candidates because of mixed format and partial gating.

## Iteration Note Template

Use this note after each provider implementation:

```md
### Iteration Note: <provider_id>

- Date:
- Implementer:
- Files changed:
- Tests run:
- Docs updated:
- Result:
- Follow-ups:
```
