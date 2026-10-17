# Current Providers

This page is the canonical reference for NewsR’s implemented built-in article providers, bootstrap defaults, target catalogs, and verification status. The registry is defined in `src/newsr/providers/registry.py`.

## Catalog Synchronization

- Every startup synchronizes built-in provider records and static target catalogs into SQLite without making network requests.
- Only `bbc` is enabled on a fresh installation. Each provider’s initial selections come from `default_targets()`.
- Existing enabled states, schedules, and retained target selections are preserved, including an explicitly empty selection. Newly added targets remain unselected on existing installations.
- Catalog synchronization updates labels and destinations by stable target key. Obsolete static targets and their selections are removed; stored articles remain available.
- BBC’s additional live-discovered targets are retained during startup synchronization. The source manager can refresh an HTTP provider’s catalog and preserve selections for targets that remain available.
- Built-in article providers use `provider_type = "http"`. `[ALL]` is a synthetic aggregate scope with type `all`; watched topics use type `topic` and are managed separately.

## Verification

Last audited: **2026-10-17**. The built-in catalog contains **19 providers and 402 targets**. The audit compares first-party navigation and primary topic indexes, checks destination content and extracted candidates, and checks representative written articles. Individual product models, exhaustive tag directories, temporary promotions, and podcast-only destinations are outside the catalog. Accessible empty topic pages are identified explicitly; HTTP success alone does not establish an article-bearing listing.

The verification notes below distinguish direct HTML checks from indexed first-party evidence and blocked endpoints. Static catalogs represent this audit snapshot; BBC also supports live navigation discovery. Direct parsing produced candidates for 364 targets; 16 published coverage pages were explicitly empty and one listing contained only sponsored cards. Fifteen listing endpoints and six Deloitte search requests were blocked. Representative written articles were parsed for 18 providers; The Hacker News article parsing remains unverified.

Each catalog table records the stable target key, label, first-party destination, HTTP/content status, and extracted candidate count on **2026-10-17**. The destination column gives both the requested and final URL for the current catalog; these URLs resolved without redirects during verification. Candidate counts use the provider’s parser on the fetched listing or discovery response, before any fetch limit. An em dash means live candidate extraction could not be verified, not an empty listing. Temporary raw downloads are excluded from the repository. Bootstrap selections retain their stable keys; the additional targets are unselected by default.

For an on-demand live audit and code update, use the repository skill [`$update-provider-categories`](../.codex/skills/update-provider-categories/SKILL.md). It covers all built-in providers by default, accepts a named provider subset, and supports an audit-only report.

## Built-in Providers

### BBC News

- provider id: `bbc`
- bootstrap state: enabled by default
- default selected targets: `World`, `Technology`, `Business`, `Entertainment & Arts`
- catalog behavior: Live discovery merges navigation categories with the built-in catalog. Regional `/news/world/*` pages and top-level editorial sections are supported. Candidate extraction is scoped to the main listing, excluding global navigation and footer promotions. Candidates include native news reports and written BBC features; live coverage, video pages, external links, and topic indexes are excluded.
- verification: **2026-10-17**. All 27 destinations produced native written-article candidates within the main listing. Representative news and Culture feature articles supplied readable bodies, author names, and publication dates. Article metadata supports structured ReportageNewsArticle, NewsArticle, and Article records; publication dates use datePublished.
- first-party catalog reference: [publisher navigation or topic index](https://www.bbc.com/news)
- article verification samples: [Written article](https://www.bbc.com/news/articles/cr20wlp09gn3o), [Culture](https://www.bbc.com/culture/article/20261015-hollywood-stars-on-the-films-that-mean-most-to-them)

| Key | Target | Destination | HTTP/content | Candidates |
| --- | --- | --- | --- | --- |
| `world` | World | [/news/world](https://www.bbc.com/news/world) | 200 listing | 17 |
| `technology` | Technology | [/technology](https://www.bbc.com/technology) | 200 listing | 25 |
| `business` | Business | [/business](https://www.bbc.com/business) | 200 listing | 31 |
| `entertainment_and_arts` | Entertainment & Arts | [/culture/entertainment-news](https://www.bbc.com/culture/entertainment-news) | 200 listing | 20 |
| `bbcindepth` | BBC InDepth | [/news/bbcindepth](https://www.bbc.com/news/bbcindepth) | 200 listing | 12 |
| `science-environment` | Science & Environment | [/news/science_and_environment](https://www.bbc.com/news/science_and_environment) | 200 listing | 9 |
| `health` | Health | [/health](https://www.bbc.com/health) | 200 listing | 41 |
| `newsbeat` | Newsbeat | [/news/newsbeat](https://www.bbc.com/news/newsbeat) | 200 listing | 12 |
| `latest` | Latest | [/news](https://www.bbc.com/news) | 200 listing | 23 |
| `us-canada` | US & Canada | [/news/us-canada](https://www.bbc.com/news/us-canada) | 200 listing | 20 |
| `uk` | UK | [/news/uk](https://www.bbc.com/news/uk) | 200 listing | 25 |
| `world/africa` | Africa | [/news/world/africa](https://www.bbc.com/news/world/africa) | 200 listing | 15 |
| `world/asia` | Asia | [/news/world/asia](https://www.bbc.com/news/world/asia) | 200 listing | 14 |
| `world/australia` | Australia | [/news/world/australia](https://www.bbc.com/news/world/australia) | 200 listing | 11 |
| `world/europe` | Europe | [/news/world/europe](https://www.bbc.com/news/world/europe) | 200 listing | 18 |
| `world/latin_america` | Latin America | [/news/world/latin_america](https://www.bbc.com/news/world/latin_america) | 200 listing | 15 |
| `world/middle_east` | Middle East | [/news/world/middle_east](https://www.bbc.com/news/world/middle_east) | 200 listing | 19 |
| `bbcverify` | BBC Verify | [/news/bbcverify](https://www.bbc.com/news/bbcverify) | 200 listing | 16 |
| `politics` | UK Politics | [/news/politics](https://www.bbc.com/news/politics) | 200 listing | 24 |
| `england` | England | [/news/england](https://www.bbc.com/news/england) | 200 listing | 26 |
| `northern_ireland` | Northern Ireland | [/news/northern_ireland](https://www.bbc.com/news/northern_ireland) | 200 listing | 27 |
| `scotland` | Scotland | [/news/scotland](https://www.bbc.com/news/scotland) | 200 listing | 21 |
| `wales` | Wales | [/news/wales](https://www.bbc.com/news/wales) | 200 listing | 16 |
| `culture` | Culture | [/culture](https://www.bbc.com/culture) | 200 listing | 34 |
| `arts` | Arts | [/arts](https://www.bbc.com/arts) | 200 listing | 27 |
| `travel` | Travel | [/travel](https://www.bbc.com/travel) | 200 listing | 43 |
| `earth` | Earth | [/future-planet](https://www.bbc.com/future-planet) | 200 listing | 24 |


### 9to5Mac

- provider id: `9to5mac`
- bootstrap state: disabled by default
- default selected targets: `Latest`, `iPhone`, `Mac`, `iPad`, `Apple Watch`
- catalog behavior: Static guide-backed catalog with the site root as Latest. Candidate extraction accepts native written articles and excludes podcast cards.
- verification: **2026-10-17**. All 30 destinations produced written-article candidates, including HomePod. Representative Apple Watch and HomePod articles supplied readable bodies, authors, and publication dates.
- first-party catalog reference: [publisher navigation or topic index](https://9to5mac.com/)
- article verification samples: [Written article](https://9to5mac.com/2026/10/07/watchos-27-adds-three-new-apps-to-your-apple-watch/), [HomePod](https://9to5mac.com/2026/10/16/homepod-is-about-to-get-free-upgrade-with-these-new-features/)

| Key | Target | Destination | HTTP/content | Candidates |
| --- | --- | --- | --- | --- |
| `latest` | Latest | [/](https://9to5mac.com/) | 200 listing | 26 |
| `iphone` | iPhone | [/guides/iphone/](https://9to5mac.com/guides/iphone/) | 200 listing | 22 |
| `mac` | Mac | [/guides/mac/](https://9to5mac.com/guides/mac/) | 200 listing | 24 |
| `ipad` | iPad | [/guides/ipad/](https://9to5mac.com/guides/ipad/) | 200 listing | 22 |
| `apple-watch` | Apple Watch | [/guides/apple-watch/](https://9to5mac.com/guides/apple-watch/) | 200 listing | 24 |
| `vision-pro` | Vision Pro | [/guides/vision-pro/](https://9to5mac.com/guides/vision-pro/) | 200 listing | 24 |
| `apple-tv` | Apple TV | [/guides/apple-tv/](https://9to5mac.com/guides/apple-tv/) | 200 listing | 22 |
| `airpods` | AirPods | [/guides/airpods/](https://9to5mac.com/guides/airpods/) | 200 listing | 24 |
| `homekit` | HomeKit | [/guides/homekit/](https://9to5mac.com/guides/homekit/) | 200 listing | 24 |
| `reviews` | Reviews | [/guides/review/](https://9to5mac.com/guides/review/) | 200 listing | 23 |
| `how-to` | How Tos | [/guides/how-to/](https://9to5mac.com/guides/how-to/) | 200 listing | 6 |
| `app-store` | App Store | [/guides/app-store/](https://9to5mac.com/guides/app-store/) | 200 listing | 24 |
| `apple-music` | Apple Music | [/guides/apple-music/](https://9to5mac.com/guides/apple-music/) | 200 listing | 24 |
| `carplay` | CarPlay | [/guides/carplay/](https://9to5mac.com/guides/carplay/) | 200 listing | 21 |
| `siri` | Siri | [/guides/siri/](https://9to5mac.com/guides/siri/) | 200 listing | 24 |
| `apple-silicon` | Apple Silicon | [/guides/apple-silicon/](https://9to5mac.com/guides/apple-silicon/) | 200 listing | 23 |
| `apple-arcade` | Apple Arcade | [/guides/apple-arcade/](https://9to5mac.com/guides/apple-arcade/) | 200 listing | 24 |
| `aapl` | AAPL | [/guides/aapl/](https://9to5mac.com/guides/aapl/) | 200 listing | 24 |
| `ios` | iOS | [/guides/ios/](https://9to5mac.com/guides/ios/) | 200 listing | 23 |
| `ipados` | iPadOS | [/guides/ipados/](https://9to5mac.com/guides/ipados/) | 200 listing | 23 |
| `macos` | macOS | [/guides/macos/](https://9to5mac.com/guides/macos/) | 200 listing | 24 |
| `watchos` | watchOS | [/guides/watchos/](https://9to5mac.com/guides/watchos/) | 200 listing | 24 |
| `visionos` | visionOS | [/guides/visionos/](https://9to5mac.com/guides/visionos/) | 200 listing | 24 |
| `apple-health` | Apple Health | [/guides/apple-health/](https://9to5mac.com/guides/apple-health/) | 200 listing | 23 |
| `apple-store` | Apple Store | [/guides/apple-store/](https://9to5mac.com/guides/apple-store/) | 200 listing | 24 |
| `apple-card` | Apple Card | [/guides/apple-card/](https://9to5mac.com/guides/apple-card/) | 200 listing | 24 |
| `apple-one` | Apple One | [/guides/apple-one/](https://9to5mac.com/guides/apple-one/) | 200 listing | 24 |
| `apple-fitness` | Apple Fitness+ | [/guides/apple-fitness/](https://9to5mac.com/guides/apple-fitness/) | 200 listing | 24 |
| `ai` | AI | [/guides/ai/](https://9to5mac.com/guides/ai/) | 200 listing | 24 |
| `homepod` | HomePod | [/guides/homepod/](https://9to5mac.com/guides/homepod/) | 200 listing | 24 |


### 9to5Google

- provider id: `ninetofivegoogle`
- bootstrap state: disabled by default
- default selected targets: `Latest`, `Pixel`, `Android`, `Chrome`, `TV`, `Workspace`
- catalog behavior: Static guide-backed catalog covering product families, Android manufacturers, and Workspace services with the site root as Latest and feature-backed Reviews and Exclusives. Taxonomy classes for YouTube topics are supported while embedded video and podcast cards are excluded.
- verification: **2026-10-17**. All 35 destinations produced written-article candidates. Representative Android, Gmail, and Pixel Watch articles supplied readable bodies, authors, and publication dates. Cars and some guide pages contain older archive material.
- first-party catalog reference: [publisher navigation or topic index](https://9to5google.com/)
- article verification samples: [Written article](https://9to5google.com/2026/10/16/iphone-duo-pre-order-delay-android-foldable-alternatives/), [Gmail](https://9to5google.com/2026/09/19/gmail-copy-code/), [Pixel Watch](https://9to5google.com/2026/10/08/google-ending-safety-signal-support-pixel-watch/)

| Key | Target | Destination | HTTP/content | Candidates |
| --- | --- | --- | --- | --- |
| `latest` | Latest | [/](https://9to5google.com/) | 200 listing | 23 |
| `pixel` | Pixel | [/guides/google-pixel/](https://9to5google.com/guides/google-pixel/) | 200 listing | 24 |
| `android` | Android | [/guides/android/](https://9to5google.com/guides/android/) | 200 listing | 24 |
| `chrome` | Chrome | [/guides/google-chrome/](https://9to5google.com/guides/google-chrome/) | 200 listing | 24 |
| `tv` | TV | [/guides/google-tv/](https://9to5google.com/guides/google-tv/) | 200 listing | 23 |
| `workspace` | Workspace | [/guides/google-workspace/](https://9to5google.com/guides/google-workspace/) | 200 listing | 24 |
| `assistant` | Assistant | [/guides/google-assistant/](https://9to5google.com/guides/google-assistant/) | 200 listing | 24 |
| `smart-home` | Smart Home | [/guides/smart-home/](https://9to5google.com/guides/smart-home/) | 200 listing | 23 |
| `cars` | Cars | [/guides/cars/](https://9to5google.com/guides/cars/) | 200 listing | 6 |
| `reviews` | Reviews | [/feature/review/](https://9to5google.com/feature/review/) | 200 listing | 24 |
| `how-to` | How Tos | [/guides/how-to/](https://9to5google.com/guides/how-to/) | 200 listing | 14 |
| `deals` | Deals | [/guides/deals/](https://9to5google.com/guides/deals/) | 200 listing | 24 |
| `gemini` | Gemini | [/guides/gemini/](https://9to5google.com/guides/gemini/) | 200 listing | 24 |
| `nest` | Nest | [/guides/google-nest/](https://9to5google.com/guides/google-nest/) | 200 listing | 24 |
| `chromeos` | ChromeOS | [/guides/chrome-os/](https://9to5google.com/guides/chrome-os/) | 200 listing | 24 |
| `android-auto` | Android Auto | [/guides/android-auto/](https://9to5google.com/guides/android-auto/) | 200 listing | 24 |
| `wear-os` | Wear OS | [/guides/wear-os/](https://9to5google.com/guides/wear-os/) | 200 listing | 24 |
| `youtube` | YouTube | [/guides/youtube/](https://9to5google.com/guides/youtube/) | 200 listing | 24 |
| `youtube-music` | YouTube Music | [/guides/youtube-music/](https://9to5google.com/guides/youtube-music/) | 200 listing | 24 |
| `youtube-tv` | YouTube TV | [/guides/youtube-tv/](https://9to5google.com/guides/youtube-tv/) | 200 listing | 24 |
| `exclusives` | Exclusives | [/feature/exclusives/](https://9to5google.com/feature/exclusives/) | 200 listing | 24 |
| `pixel-watch` | Pixel Watch | [/guides/google-pixel-watch/](https://9to5google.com/guides/google-pixel-watch/) | 200 listing | 23 |
| `samsung` | Samsung | [/guides/samsung/](https://9to5google.com/guides/samsung/) | 200 listing | 24 |
| `oneplus` | OnePlus | [/guides/oneplus/](https://9to5google.com/guides/oneplus/) | 200 listing | 24 |
| `oppo` | Oppo | [/guides/oppo/](https://9to5google.com/guides/oppo/) | 200 listing | 24 |
| `xiaomi` | Xiaomi | [/guides/xiaomi/](https://9to5google.com/guides/xiaomi/) | 200 listing | 24 |
| `android-tv` | Android TV | [/guides/android-tv/](https://9to5google.com/guides/android-tv/) | 200 listing | 24 |
| `chromecast` | Chromecast | [/guides/chromecast/](https://9to5google.com/guides/chromecast/) | 200 listing | 24 |
| `gmail` | Gmail | [/guides/gmail/](https://9to5google.com/guides/gmail/) | 200 listing | 23 |
| `google-meet` | Google Meet | [/guides/google-meet/](https://9to5google.com/guides/google-meet/) | 200 listing | 24 |
| `google-chat` | Google Chat | [/guides/google-chat/](https://9to5google.com/guides/google-chat/) | 200 listing | 24 |
| `google-calendar` | Google Calendar | [/guides/google-calendar/](https://9to5google.com/guides/google-calendar/) | 200 listing | 24 |
| `google-keep` | Google Keep | [/guides/google-keep/](https://9to5google.com/guides/google-keep/) | 200 listing | 24 |
| `google-drive` | Google Drive | [/guides/google-drive/](https://9to5google.com/guides/google-drive/) | 200 listing | 24 |
| `google-docs` | Google Docs | [/guides/google-docs/](https://9to5google.com/guides/google-docs/) | 200 listing | 24 |


### TechCrunch

- provider id: `techcrunch`
- bootstrap state: disabled by default
- default selected targets: `Latest`, `Startups`, `Venture`, `AI`, `Security`
- catalog behavior: Static catalog covering the editorial Topics menu, including its featured company topics. Latest uses `/latest/`; AI uses the artificial-intelligence category.
- verification: **2026-10-17**. All 33 destinations produced written-article candidates; a representative article supplied a readable body, author, and publication date.
- first-party catalog reference: [publisher navigation or topic index](https://techcrunch.com/)
- article verification samples: [Written article](https://techcrunch.com/2026/10/16/replit-is-no-longer-working-with-anthropic-ceo-says/)

| Key | Target | Destination | HTTP/content | Candidates |
| --- | --- | --- | --- | --- |
| `latest` | Latest | [/latest/](https://techcrunch.com/latest/) | 200 listing | 20 |
| `startups` | Startups | [/category/startups/](https://techcrunch.com/category/startups/) | 200 listing | 29 |
| `venture` | Venture | [/category/venture/](https://techcrunch.com/category/venture/) | 200 listing | 28 |
| `ai` | AI | [/category/artificial-intelligence/](https://techcrunch.com/category/artificial-intelligence/) | 200 listing | 28 |
| `security` | Security | [/category/security/](https://techcrunch.com/category/security/) | 200 listing | 30 |
| `apps` | Apps | [/category/apps/](https://techcrunch.com/category/apps/) | 200 listing | 30 |
| `fintech` | Fintech | [/category/fintech/](https://techcrunch.com/category/fintech/) | 200 listing | 30 |
| `enterprise` | Enterprise | [/category/enterprise/](https://techcrunch.com/category/enterprise/) | 200 listing | 30 |
| `climate` | Climate | [/category/climate/](https://techcrunch.com/category/climate/) | 200 listing | 30 |
| `robotics` | Robotics | [/category/robotics/](https://techcrunch.com/category/robotics/) | 200 listing | 28 |
| `government-policy` | Government & Policy | [/category/government-policy/](https://techcrunch.com/category/government-policy/) | 200 listing | 29 |
| `apple` | Apple | [/tag/apple/](https://techcrunch.com/tag/apple/) | 200 listing | 29 |
| `amazon` | Amazon | [/tag/amazon/](https://techcrunch.com/tag/amazon/) | 200 listing | 27 |
| `biotech-health` | Biotech & Health | [/category/biotech-health/](https://techcrunch.com/category/biotech-health/) | 200 listing | 29 |
| `cloud-computing` | Cloud Computing | [/tag/cloud-computing/](https://techcrunch.com/tag/cloud-computing/) | 200 listing | 29 |
| `commerce` | Commerce | [/category/commerce/](https://techcrunch.com/category/commerce/) | 200 listing | 30 |
| `cryptocurrency` | Crypto | [/category/cryptocurrency/](https://techcrunch.com/category/cryptocurrency/) | 200 listing | 30 |
| `evs` | EVs | [/tag/evs/](https://techcrunch.com/tag/evs/) | 200 listing | 30 |
| `fundraising` | Fundraising | [/category/fundraising/](https://techcrunch.com/category/fundraising/) | 200 listing | 30 |
| `gadgets` | Gadgets | [/category/gadgets/](https://techcrunch.com/category/gadgets/) | 200 listing | 30 |
| `gaming` | Gaming | [/category/gaming/](https://techcrunch.com/category/gaming/) | 200 listing | 30 |
| `google` | Google | [/tag/google/](https://techcrunch.com/tag/google/) | 200 listing | 30 |
| `hardware` | Hardware | [/category/hardware/](https://techcrunch.com/category/hardware/) | 200 listing | 30 |
| `instagram` | Instagram | [/tag/instagram/](https://techcrunch.com/tag/instagram/) | 200 listing | 30 |
| `layoffs` | Layoffs | [/tag/layoffs/](https://techcrunch.com/tag/layoffs/) | 200 listing | 28 |
| `media-entertainment` | Media & Entertainment | [/category/media-entertainment/](https://techcrunch.com/category/media-entertainment/) | 200 listing | 30 |
| `meta` | Meta | [/tag/meta/](https://techcrunch.com/tag/meta/) | 200 listing | 28 |
| `microsoft` | Microsoft | [/tag/microsoft/](https://techcrunch.com/tag/microsoft/) | 200 listing | 30 |
| `privacy` | Privacy | [/category/privacy/](https://techcrunch.com/category/privacy/) | 200 listing | 30 |
| `social` | Social | [/category/social/](https://techcrunch.com/category/social/) | 200 listing | 30 |
| `space` | Space | [/category/space/](https://techcrunch.com/category/space/) | 200 listing | 30 |
| `tiktok` | TikTok | [/tag/tiktok/](https://techcrunch.com/tag/tiktok/) | 200 listing | 30 |
| `transportation` | Transportation | [/category/transportation/](https://techcrunch.com/category/transportation/) | 200 listing | 30 |


### The Hacker News

- provider id: `thehackernews`
- bootstrap state: disabled by default
- default selected targets: `Threat Intelligence`, `Cyber Attacks`, `Vulnerabilities`, `Expert Insights`
- catalog behavior: Static catalog of the four written-news sections in site navigation.
- verification: **2026-10-17**. Indexed first-party navigation confirms the four sections. Direct requests to the homepage and all four destinations returned HTTP 403 challenge pages, including a repeated Threat Intelligence check. Current raw listing and article extraction remain unverified; no targets are retired on this evidence.
- first-party catalog references: [publisher homepage](https://thehackernews.com/), [indexed first-party navigation](https://thehackernews.com/search?by-date=false&max-results=20&q=vulnerabilities&start=1807&updated-max=2017-09-29T10%3A57%3A00-07%3A00)

| Key | Target | Destination | HTTP/content | Candidates |
| --- | --- | --- | --- | --- |
| `threat-intelligence` | Threat Intelligence | [/search/label/Threat%20Intelligence](https://thehackernews.com/search/label/Threat%20Intelligence) | 403 challenge | — |
| `cyber-attacks` | Cyber Attacks | [/search/label/Cyber%20Attack](https://thehackernews.com/search/label/Cyber%20Attack) | 403 challenge | — |
| `vulnerabilities` | Vulnerabilities | [/search/label/Vulnerable](https://thehackernews.com/search/label/Vulnerable) | 403 challenge | — |
| `expert-insights` | Expert Insights | [/expert-insights/](https://thehackernews.com/expert-insights/) | 403 challenge | — |


### Ars Technica

- provider id: `arstechnica`
- bootstrap state: disabled by default
- default selected targets: `Latest`, `Tech`, `Science`, `Security`
- catalog behavior: Static mixed catalog with a catch-all Latest feed and editorial sections.
- verification: **2026-10-17**. All 12 destinations produced written-article candidates. The navigation and section headings identify Tech and Policy; their stable keys are gadgets and tech-policy. A representative article supplied a readable body, author, and publication date.
- first-party catalog reference: [publisher navigation or topic index](https://arstechnica.com/)
- article verification samples: [Written article](https://arstechnica.com/gadgets/2026/10/ray-ban-meta-smart-glasses-found-recording-audio-without-wearers-consent/)

| Key | Target | Destination | HTTP/content | Candidates |
| --- | --- | --- | --- | --- |
| `latest` | Latest | [/](https://arstechnica.com/) | 200 listing | 36 |
| `gadgets` | Tech | [/gadgets/](https://arstechnica.com/gadgets/) | 200 listing | 36 |
| `science` | Science | [/science/](https://arstechnica.com/science/) | 200 listing | 36 |
| `security` | Security | [/security/](https://arstechnica.com/security/) | 200 listing | 36 |
| `tech-policy` | Policy | [/tech-policy/](https://arstechnica.com/tech-policy/) | 200 listing | 36 |
| `space` | Space | [/space/](https://arstechnica.com/space/) | 200 listing | 36 |
| `ai` | AI | [/ai/](https://arstechnica.com/ai/) | 200 listing | 36 |
| `gaming` | Gaming | [/gaming/](https://arstechnica.com/gaming/) | 200 listing | 36 |
| `cars` | Cars | [/cars/](https://arstechnica.com/cars/) | 200 listing | 36 |
| `information-technology` | Biz & IT | [/information-technology/](https://arstechnica.com/information-technology/) | 200 listing | 36 |
| `health` | Health | [/health/](https://arstechnica.com/health/) | 200 listing | 36 |
| `culture` | Culture | [/culture/](https://arstechnica.com/culture/) | 200 listing | 36 |


### HR Dive

- provider id: `hrdive`
- bootstrap state: disabled by default
- default selected targets: `Talent`, `Comp & Benefits`
- catalog behavior: Static catalog covering the navigation topic menu.
- verification: **2026-10-17**. All eight destinations produced written-article candidates; a representative article supplied a readable body, author, and publication date through sailthru.date metadata.
- first-party catalog reference: [publisher navigation or topic index](https://www.hrdive.com/)
- article verification samples: [Written article](https://www.hrdive.com/news/benefits-outlook-2026-wtw/833170/)

| Key | Target | Destination | HTTP/content | Candidates |
| --- | --- | --- | --- | --- |
| `talent` | Talent | [/topic/talent/](https://www.hrdive.com/topic/talent/) | 200 listing | 24 |
| `compensation-benefits` | Comp & Benefits | [/topic/compensation-benefits/](https://www.hrdive.com/topic/compensation-benefits/) | 200 listing | 20 |
| `diversity-inclusion` | Diversity & Inclusion | [/topic/diversity-inclusion/](https://www.hrdive.com/topic/diversity-inclusion/) | 200 listing | 24 |
| `learning` | Learning | [/topic/learning/](https://www.hrdive.com/topic/learning/) | 200 listing | 24 |
| `hr-management` | HR Management | [/topic/hr-management/](https://www.hrdive.com/topic/hr-management/) | 200 listing | 17 |
| `compliance` | Compliance | [/topic/legal/](https://www.hrdive.com/topic/legal/) | 200 listing | 24 |
| `hr-technology-analytics` | Tech & Analytics | [/topic/hr-technology-analytics/](https://www.hrdive.com/topic/hr-technology-analytics/) | 200 listing | 21 |
| `state-local-laws` | State & Local Laws | [/topic/state-local-laws/](https://www.hrdive.com/topic/state-local-laws/) | 200 listing | 5 |


### MedCity News

- provider id: `medcitynews`
- bootstrap state: disabled by default
- default selected targets: `Health Tech`, `Devices & Diagnostics`
- catalog behavior: Static catalog of written news, channels, and contributor articles. Sponsored and webinar destinations are excluded.
- verification: **2026-10-17**. All 11 destinations produced written-article candidates; a representative article supplied a readable body, author, and publication date.
- first-party catalog reference: [publisher navigation or topic index](https://medcitynews.com/)
- article verification samples: [Written article](https://medcitynews.com/2026/10/why-epic-is-launching-a-prescription-price-comparison-tool/)

| Key | Target | Destination | HTTP/content | Candidates |
| --- | --- | --- | --- | --- |
| `health-tech` | Health Tech | [/category/channel/health-tech/](https://medcitynews.com/category/channel/health-tech/) | 200 listing | 13 |
| `biopharma` | BioPharma | [/category/channel/biopharma/](https://medcitynews.com/category/channel/biopharma/) | 200 listing | 15 |
| `medical-devices-and-diagnostics` | Devices & Diagnostics | [/category/channel/medical-devices-and-diagnostics/](https://medcitynews.com/category/channel/medical-devices-and-diagnostics/) | 200 listing | 14 |
| `consumer-employer` | Consumer / Employer | [/category/channel/consumer-employer/](https://medcitynews.com/category/channel/consumer-employer/) | 200 listing | 14 |
| `news` | News | [/category/news/](https://medcitynews.com/category/news/) | 200 listing | 13 |
| `contributors` | Contributors | [/category/medcity-influencers/](https://medcitynews.com/category/medcity-influencers/) | 200 listing | 15 |
| `artificial-intelligence` | Artificial Intelligence | [/category/channel/artificial-intelligence/](https://medcitynews.com/category/channel/artificial-intelligence/) | 200 listing | 13 |
| `startups` | Startups | [/category/channel/startup-channel/](https://medcitynews.com/category/channel/startup-channel/) | 200 listing | 15 |
| `payers` | Payers | [/category/channel/payers/](https://medcitynews.com/category/channel/payers/) | 200 listing | 12 |
| `providers` | Providers | [/category/channel/providers/](https://medcitynews.com/category/channel/providers/) | 200 listing | 14 |
| `policy` | Policy | [/category/channel/politics-channel/](https://medcitynews.com/category/channel/politics-channel/) | 200 listing | 15 |


### Hyperallergic

- provider id: `hyperallergic`
- bootstrap state: disabled by default
- default selected targets: `News`, `Reviews`
- catalog behavior: Static tag-backed editorial catalog. Reviews, Features, Interviews, Guides, and Announcements use singular tag paths. Explicit Community, Opportunities, and Announcements targets accept editorial posts in those sections; sponsored cards remain excluded.
- verification: **2026-10-17**. Eleven destinations produced eligible written-article candidates; a representative article supplied a readable body, author, and publication date. Announcements returned HTTP 200 with only sponsored cards and zero eligible candidates. It remains a valid published listing; sponsored cards are excluded for every target.
- first-party catalog reference: [publisher navigation or topic index](https://hyperallergic.com/)
- article verification samples: [Written article](https://hyperallergic.com/this-ron-desantis-statue-cant-take-the-heat/)

| Key | Target | Destination | HTTP/content | Candidates |
| --- | --- | --- | --- | --- |
| `news` | News | [/tag/news/](https://hyperallergic.com/tag/news/) | 200 listing | 12 |
| `reviews` | Reviews | [/tag/review/](https://hyperallergic.com/tag/review/) | 200 listing | 12 |
| `opinion` | Opinion | [/tag/opinion/](https://hyperallergic.com/tag/opinion/) | 200 listing | 12 |
| `film` | Film | [/tag/film/](https://hyperallergic.com/tag/film/) | 200 listing | 12 |
| `features` | Features | [/tag/feature/](https://hyperallergic.com/tag/feature/) | 200 listing | 12 |
| `interviews` | Interviews | [/tag/interview/](https://hyperallergic.com/tag/interview/) | 200 listing | 12 |
| `community` | Community | [/tag/community/](https://hyperallergic.com/tag/community/) | 200 listing | 12 |
| `guides` | Guides | [/tag/guide/](https://hyperallergic.com/tag/guide/) | 200 listing | 12 |
| `opportunities` | Opportunities | [/tag/opportunities/](https://hyperallergic.com/tag/opportunities/) | 200 listing | 6 |
| `announcements` | Announcements | [/tag/announcement/](https://hyperallergic.com/tag/announcement/) | 200 sponsored only | 0 |
| `books` | Books | [/tag/books/](https://hyperallergic.com/tag/books/) | 200 listing | 12 |
| `comics` | Comics | [/tag/comics/](https://hyperallergic.com/tag/comics/) | 200 listing | 12 |


### EdSurge

- provider id: `edsurge`
- bootstrap state: disabled by default
- default selected targets: `Latest`, `Higher Education`
- catalog behavior: Static catalog using the homepage for Latest and `/coverage-areas/*` for the published coverage-area catalog. Written article URLs support both undated slugs and dated archive slugs. Podcast cards are excluded.
- verification: **2026-10-17**. The homepage produced written candidates; a representative article supplied a readable body, author, and date. All 16 coverage-area pages returned HTTP 200 with “No Articles Available under this topic” and zero candidates. Education Workforce uses /coverage-areas/education-workforce; the trailing-hyphen navigation link returns HTTP 404. Empty topics have no cross-category fallback.
- first-party catalog reference: [publisher navigation or topic index](https://www.edsurge.com/)
- article verification samples: [Written article](https://www.edsurge.com/news/can-high-impact-tutoring-survive-post-pandemic-funding-loss)

| Key | Target | Destination | HTTP/content | Candidates |
| --- | --- | --- | --- | --- |
| `latest` | Latest | [/](https://www.edsurge.com/) | 200 listing | 10 |
| `higher-ed` | Higher Education | [/coverage-areas/higher-education](https://www.edsurge.com/coverage-areas/higher-education) | 200 explicit empty | 0 |
| `artificial-intelligence` | Artificial Intelligence | [/coverage-areas/artificial-intelligence](https://www.edsurge.com/coverage-areas/artificial-intelligence) | 200 explicit empty | 0 |
| `career-readiness` | Career Readiness | [/coverage-areas/career-readiness](https://www.edsurge.com/coverage-areas/career-readiness) | 200 explicit empty | 0 |
| `access-and-inclusion` | Access and Inclusion | [/coverage-areas/access-and-inclusion](https://www.edsurge.com/coverage-areas/access-and-inclusion) | 200 explicit empty | 0 |
| `early-learning` | Early Learning | [/coverage-areas/early-learning](https://www.edsurge.com/coverage-areas/early-learning) | 200 explicit empty | 0 |
| `education-workforce` | Education Workforce | [/coverage-areas/education-workforce](https://www.edsurge.com/coverage-areas/education-workforce) | 200 explicit empty | 0 |
| `teaching-and-learning` | Teaching and Learning | [/coverage-areas/teaching-and-learning](https://www.edsurge.com/coverage-areas/teaching-and-learning) | 200 explicit empty | 0 |
| `policy-and-government` | Policy and Government | [/coverage-areas/policy-and-government](https://www.edsurge.com/coverage-areas/policy-and-government) | 200 explicit empty | 0 |
| `edtech-business` | Edtech Business | [/coverage-areas/edtech-business](https://www.edsurge.com/coverage-areas/edtech-business) | 200 explicit empty | 0 |
| `assessments` | Assessments | [/coverage-areas/assessments](https://www.edsurge.com/coverage-areas/assessments) | 200 explicit empty | 0 |
| `digital-skills` | Digital Skills | [/coverage-areas/digital-skills](https://www.edsurge.com/coverage-areas/digital-skills) | 200 explicit empty | 0 |
| `media-literacy` | Media Literacy | [/coverage-areas/media-literacy](https://www.edsurge.com/coverage-areas/media-literacy) | 200 explicit empty | 0 |
| `social-emotional-learning` | Social-Emotional Learning | [/coverage-areas/social-emotional-learning](https://www.edsurge.com/coverage-areas/social-emotional-learning) | 200 explicit empty | 0 |
| `digital-access` | Digital Access | [/coverage-areas/digital-access](https://www.edsurge.com/coverage-areas/digital-access) | 200 explicit empty | 0 |
| `instructional-trends` | Instructional Trends | [/coverage-areas/instructional-trends](https://www.edsurge.com/coverage-areas/instructional-trends) | 200 explicit empty | 0 |
| `data-privacy` | Data Privacy | [/coverage-areas/data-privacy](https://www.edsurge.com/coverage-areas/data-privacy) | 200 explicit empty | 0 |


### Marketing Dive

- provider id: `marketingdive`
- bootstrap state: disabled by default
- default selected targets: `Brand Strategy`, `Social Media`
- catalog behavior: Static topic catalog with Marketing mapped to the homepage. Topic paths preserve the publisher’s capitalization, including Social Media and Video.
- verification: **2026-10-17**. All 11 destinations produced written-article candidates; a representative article supplied a readable body, author, and publication date through sailthru.date metadata. Social Media and Video paths retain publisher capitalization.
- first-party catalog reference: [publisher navigation or topic index](https://www.marketingdive.com/)
- article verification samples: [Written article](https://www.marketingdive.com/news/wendys-signs-on-as-first-sponsor-for-in-app-bravo-fan-experience/833067/)

| Key | Target | Destination | HTTP/content | Candidates |
| --- | --- | --- | --- | --- |
| `brand-strategy` | Brand Strategy | [/topic/brand-strategy/](https://www.marketingdive.com/topic/brand-strategy/) | 200 listing | 25 |
| `mobile` | Mobile | [/topic/mobile-marketing/](https://www.marketingdive.com/topic/mobile-marketing/) | 200 listing | 25 |
| `creative` | Creative | [/topic/creative/](https://www.marketingdive.com/topic/creative/) | 200 listing | 25 |
| `social-media` | Social Media | [/topic/Social-media-marketing/](https://www.marketingdive.com/topic/Social-media-marketing/) | 200 listing | 24 |
| `video` | Video | [/topic/Video-marketing/](https://www.marketingdive.com/topic/Video-marketing/) | 200 listing | 22 |
| `agencies` | Agencies | [/topic/agencies/](https://www.marketingdive.com/topic/agencies/) | 200 listing | 23 |
| `data-analytics` | Data/Analytics | [/topic/analytics/](https://www.marketingdive.com/topic/analytics/) | 200 listing | 19 |
| `influencer` | Influencer Marketing | [/topic/influencer-marketing/](https://www.marketingdive.com/topic/influencer-marketing/) | 200 listing | 24 |
| `marketing` | Marketing | [/](https://www.marketingdive.com/) | 200 listing | 24 |
| `ad-tech` | Ad Tech | [/topic/marketing-tech/](https://www.marketingdive.com/topic/marketing-tech/) | 200 listing | 24 |
| `cmo-corner` | CMO Corner | [/topic/cmo-corner/](https://www.marketingdive.com/topic/cmo-corner/) | 200 listing | 24 |


### Payments Dive

- provider id: `paymentsdive`
- bootstrap state: disabled by default
- default selected targets: `Technology`, `Fraud`
- catalog behavior: Static catalog using the homepage for Latest and the navigation topic destinations. Candidate extraction accepts written articles and filters sponsored cards and trendlines.
- verification: **2026-10-17**. All nine destinations produced written-article candidates; a representative article supplied a readable body, author, and publication date.
- first-party catalog reference: [publisher navigation or topic index](https://www.paymentsdive.com/)
- article verification samples: [Written article](https://www.paymentsdive.com/news/treasury-taps-data-to-fend-off-payments-fraud/832511/)

| Key | Target | Destination | HTTP/content | Candidates |
| --- | --- | --- | --- | --- |
| `latest` | Latest | [/](https://www.paymentsdive.com/) | 200 listing | 31 |
| `retail` | Retail | [/topic/retail/](https://www.paymentsdive.com/topic/retail/) | 200 listing | 24 |
| `banking` | Banking | [/topic/banking/](https://www.paymentsdive.com/topic/banking/) | 200 listing | 25 |
| `restaurants` | Restaurants | [/topic/restaurants/](https://www.paymentsdive.com/topic/restaurants/) | 200 listing | 25 |
| `regulations_and_policy` | Regulations & Policy | [/topic/regulations_and_policy/](https://www.paymentsdive.com/topic/regulations_and_policy/) | 200 listing | 25 |
| `risk` | Consumer Risk | [/topic/risk/](https://www.paymentsdive.com/topic/risk/) | 200 listing | 24 |
| `technology` | Technology | [/topic/technology/](https://www.paymentsdive.com/topic/technology/) | 200 listing | 21 |
| `b2b` | B2B | [/topic/b2b/](https://www.paymentsdive.com/topic/b2b/) | 200 listing | 25 |
| `fraud` | Fraud | [/topic/fraud/](https://www.paymentsdive.com/topic/fraud/) | 200 listing | 24 |


### Tom's Hardware

- provider id: `tomshardware`
- bootstrap state: disabled by default
- default selected targets: `PC Components`, `CPUs`, `GPUs`
- catalog behavior: Static hardware, software, and technology catalog using server-rendered `/news` indexes. Candidates include written news and reviews, including legacy `/news/*.html` URLs; buying guides, deals, sponsored cards, and category indexes are excluded.
- verification: **2026-10-17**. All 36 /news destinations produced eligible candidates, including the navigation sections for routers, PC building, laptop and desktop types, monitors, keyboards, mice, and headphones. Representative CPU, headphone, and ultrabook articles supplied readable bodies, authors, and publication dates. Headphones and Ultrabooks listings have no h1 heading, but contain relevant native written-article cards. Some sections contain older archive material.
- first-party catalog reference: [publisher navigation or topic index](https://www.tomshardware.com/)
- article verification samples: [Written article](https://www.tomshardware.com/pc-components/cpus/qualcomm-wins-architecture-breach-verdict-against-arm-but-gets-just-usd2-judge-could-still-suspend-royalty-fees-for-five-years), [Headphones](https://www.tomshardware.com/peripherals/gaming-headsets/corsair-launches-lightweight-budget-friendly-hs35-v3-gaming-headsets), [Ultrabooks](https://www.tomshardware.com/laptops/ultrabooks-ultraportables/intels-googlebooks-might-not-run-some-android-apps-as-well-as-qualcomms-google-says-this-is-because-android-apps-were-designed-for-arm-chips)

| Key | Target | Destination | HTTP/content | Candidates |
| --- | --- | --- | --- | --- |
| `pc-components` | PC Components | [/pc-components/news](https://www.tomshardware.com/pc-components/news) | 200 listing | 10 |
| `cpus` | CPUs | [/pc-components/cpus/news](https://www.tomshardware.com/pc-components/cpus/news) | 200 listing | 9 |
| `gpus` | GPUs | [/pc-components/gpus/news](https://www.tomshardware.com/pc-components/gpus/news) | 200 listing | 10 |
| `storage` | Storage | [/pc-components/storage/news](https://www.tomshardware.com/pc-components/storage/news) | 200 listing | 10 |
| `laptops` | Laptops | [/laptops/news](https://www.tomshardware.com/laptops/news) | 200 listing | 10 |
| `desktops` | Desktops | [/desktops/news](https://www.tomshardware.com/desktops/news) | 200 listing | 10 |
| `software` | Software | [/software/news](https://www.tomshardware.com/software/news) | 200 listing | 10 |
| `artificial-intelligence` | Artificial Intelligence | [/tech-industry/artificial-intelligence/news](https://www.tomshardware.com/tech-industry/artificial-intelligence/news) | 200 listing | 10 |
| `latest` | Latest | [/news](https://www.tomshardware.com/news) | 200 listing | 7 |
| `ram` | RAM | [/pc-components/ram/news](https://www.tomshardware.com/pc-components/ram/news) | 200 listing | 10 |
| `cooling` | Cooling | [/pc-components/cooling/news](https://www.tomshardware.com/pc-components/cooling/news) | 200 listing | 10 |
| `motherboards` | Motherboards | [/pc-components/motherboards/news](https://www.tomshardware.com/pc-components/motherboards/news) | 200 listing | 10 |
| `overclocking` | Overclocking | [/pc-components/overclocking/news](https://www.tomshardware.com/pc-components/overclocking/news) | 200 listing | 10 |
| `pc-cases` | PC Cases | [/pc-components/pc-cases/news](https://www.tomshardware.com/pc-components/pc-cases/news) | 200 listing | 10 |
| `power-supplies` | Power Supplies | [/pc-components/power-supplies/news](https://www.tomshardware.com/pc-components/power-supplies/news) | 200 listing | 10 |
| `networking` | Networking | [/networking/news](https://www.tomshardware.com/networking/news) | 200 listing | 10 |
| `monitors` | Monitors | [/monitors/news](https://www.tomshardware.com/monitors/news) | 200 listing | 10 |
| `peripherals` | Peripherals | [/peripherals/news](https://www.tomshardware.com/peripherals/news) | 200 listing | 10 |
| `3d-printing` | 3D Printers | [/3d-printing/news](https://www.tomshardware.com/3d-printing/news) | 200 listing | 10 |
| `tech-industry` | Tech Industry | [/tech-industry/news](https://www.tomshardware.com/tech-industry/news) | 200 listing | 10 |
| `cyber-security` | Cybersecurity | [/tech-industry/cyber-security/news](https://www.tomshardware.com/tech-industry/cyber-security/news) | 200 listing | 10 |
| `supercomputers` | Supercomputers | [/tech-industry/supercomputers/news](https://www.tomshardware.com/tech-industry/supercomputers/news) | 200 listing | 10 |
| `quantum-computing` | Quantum Computing | [/tech-industry/quantum-computing/news](https://www.tomshardware.com/tech-industry/quantum-computing/news) | 200 listing | 10 |
| `operating-systems` | Operating Systems | [/software/operating-systems/news](https://www.tomshardware.com/software/operating-systems/news) | 200 listing | 10 |
| `programming` | Programming | [/software/programming/news](https://www.tomshardware.com/software/programming/news) | 200 listing | 10 |
| `applications` | Applications | [/software/applications/news](https://www.tomshardware.com/software/applications/news) | 200 listing | 10 |
| `browsers` | Web Browsers | [/software/browsers/news](https://www.tomshardware.com/software/browsers/news) | 200 listing | 10 |
| `routers` | Routers | [/networking/routers/news](https://www.tomshardware.com/networking/routers/news) | 200 listing | 10 |
| `pc-building` | PC Building | [/desktops/pc-building/news](https://www.tomshardware.com/desktops/pc-building/news) | 200 listing | 10 |
| `gaming-laptops` | Gaming Laptops | [/laptops/gaming-laptops/news](https://www.tomshardware.com/laptops/gaming-laptops/news) | 200 listing | 10 |
| `ultrabooks` | Ultrabooks | [/laptops/ultrabooks-ultraportables/news](https://www.tomshardware.com/laptops/ultrabooks-ultraportables/news) | 200 listing | 10 |
| `gaming-pcs` | Gaming PCs | [/desktops/gaming-pcs/news](https://www.tomshardware.com/desktops/gaming-pcs/news) | 200 listing | 10 |
| `gaming-monitors` | Gaming Monitors | [/monitors/gaming-monitors/news](https://www.tomshardware.com/monitors/gaming-monitors/news) | 200 listing | 10 |
| `keyboards` | Keyboards | [/peripherals/keyboards/news](https://www.tomshardware.com/peripherals/keyboards/news) | 200 listing | 10 |
| `mice` | Mice | [/peripherals/mice/news](https://www.tomshardware.com/peripherals/mice/news) | 200 listing | 10 |
| `headphones` | Headphones | [/peripherals/headphones-headsets/news](https://www.tomshardware.com/peripherals/headphones-headsets/news) | 200 listing | 7 |


### Canary Media

- provider id: `canarymedia`
- bootstrap state: disabled by default
- default selected targets: `Grid Edge`, `Solar`
- catalog behavior: Static catalog covering the published View All Topics index through `/articles/<topic>` destinations. The Sponsored topic is excluded.
- verification: **2026-10-17**. All 61 destinations in the primary topic index produced candidates; a representative article supplied a readable body, author, and publication date. The sponsored topic is outside the editorial catalog.
- first-party catalog reference: [publisher navigation or topic index](https://www.canarymedia.com/articles/categories)
- article verification samples: [Written article](https://www.canarymedia.com/articles/transmission/advanced-grid-tech-doe-boost)

| Key | Target | Destination | HTTP/content | Candidates |
| --- | --- | --- | --- | --- |
| `grid-edge` | Grid Edge | [/articles/grid-edge](https://www.canarymedia.com/articles/grid-edge) | 200 listing | 11 |
| `energy-storage` | Energy Storage | [/articles/energy-storage](https://www.canarymedia.com/articles/energy-storage) | 200 listing | 11 |
| `solar` | Solar | [/articles/solar](https://www.canarymedia.com/articles/solar) | 200 listing | 11 |
| `electrification` | Electrification | [/articles/electrification](https://www.canarymedia.com/articles/electrification) | 200 listing | 11 |
| `transportation` | Transportation | [/articles/transportation](https://www.canarymedia.com/articles/transportation) | 200 listing | 11 |
| `wind` | Wind | [/articles/wind](https://www.canarymedia.com/articles/wind) | 200 listing | 11 |
| `batteries` | Batteries | [/articles/batteries](https://www.canarymedia.com/articles/batteries) | 200 listing | 11 |
| `affordability` | Affordability | [/articles/affordability](https://www.canarymedia.com/articles/affordability) | 200 listing | 11 |
| `air-travel` | Air travel | [/articles/air-travel](https://www.canarymedia.com/articles/air-travel) | 200 listing | 11 |
| `balcony-solar` | Balcony solar | [/articles/balcony-solar](https://www.canarymedia.com/articles/balcony-solar) | 200 listing | 11 |
| `canary-media` | Canary Media | [/articles/canary-media](https://www.canarymedia.com/articles/canary-media) | 200 listing | 8 |
| `carbon-capture` | Carbon capture | [/articles/carbon-capture](https://www.canarymedia.com/articles/carbon-capture) | 200 listing | 11 |
| `carbon-removal` | Carbon removal | [/articles/carbon-removal](https://www.canarymedia.com/articles/carbon-removal) | 200 listing | 11 |
| `carbon-free-buildings` | Carbon-free buildings | [/articles/carbon-free-buildings](https://www.canarymedia.com/articles/carbon-free-buildings) | 200 listing | 11 |
| `clean-aluminum` | Clean aluminum | [/articles/clean-aluminum](https://www.canarymedia.com/articles/clean-aluminum) | 200 listing | 11 |
| `clean-energy` | Clean energy | [/articles/clean-energy](https://www.canarymedia.com/articles/clean-energy) | 200 listing | 11 |
| `clean-energy-jobs` | Clean energy jobs | [/articles/clean-energy-jobs](https://www.canarymedia.com/articles/clean-energy-jobs) | 200 listing | 11 |
| `clean-energy-manufacturing` | Clean energy manufacturing | [/articles/clean-energy-manufacturing](https://www.canarymedia.com/articles/clean-energy-manufacturing) | 200 listing | 11 |
| `clean-energy-supply-chain` | Clean energy supply chain | [/articles/clean-energy-supply-chain](https://www.canarymedia.com/articles/clean-energy-supply-chain) | 200 listing | 11 |
| `clean-fleets` | Clean fleets | [/articles/clean-fleets](https://www.canarymedia.com/articles/clean-fleets) | 200 listing | 11 |
| `clean-industry` | Clean industry | [/articles/clean-industry](https://www.canarymedia.com/articles/clean-industry) | 200 listing | 11 |
| `climate-crisis` | Climate crisis | [/articles/climate-crisis](https://www.canarymedia.com/articles/climate-crisis) | 200 listing | 11 |
| `climate-justice` | Climate justice | [/articles/climate-justice](https://www.canarymedia.com/articles/climate-justice) | 200 listing | 11 |
| `climatetech-finance` | Climatetech finance | [/articles/climatetech-finance](https://www.canarymedia.com/articles/climatetech-finance) | 200 listing | 11 |
| `corporate-procurement` | Corporate procurement | [/articles/corporate-procurement](https://www.canarymedia.com/articles/corporate-procurement) | 200 listing | 11 |
| `culture` | Culture | [/articles/culture](https://www.canarymedia.com/articles/culture) | 200 listing | 11 |
| `data-centers` | Data centers | [/articles/data-centers](https://www.canarymedia.com/articles/data-centers) | 200 listing | 11 |
| `distributed-energy-resources` | Distributed energy resources | [/articles/distributed-energy-resources](https://www.canarymedia.com/articles/distributed-energy-resources) | 200 listing | 11 |
| `electric-vehicles` | Electric vehicles | [/articles/electric-vehicles](https://www.canarymedia.com/articles/electric-vehicles) | 200 listing | 11 |
| `emissions-reduction` | Emissions reduction | [/articles/emissions-reduction](https://www.canarymedia.com/articles/emissions-reduction) | 200 listing | 11 |
| `energy-efficiency` | Energy efficiency | [/articles/energy-efficiency](https://www.canarymedia.com/articles/energy-efficiency) | 200 listing | 11 |
| `energy-equity` | Energy equity | [/articles/energy-equity](https://www.canarymedia.com/articles/energy-equity) | 200 listing | 11 |
| `energy-markets` | Energy markets | [/articles/energy-markets](https://www.canarymedia.com/articles/energy-markets) | 200 listing | 11 |
| `enn` | ENN | [/articles/enn](https://www.canarymedia.com/articles/enn) | 200 listing | 11 |
| `ev-charging` | EV charging | [/articles/ev-charging](https://www.canarymedia.com/articles/ev-charging) | 200 listing | 11 |
| `food-and-farms` | Food and farms | [/articles/food-and-farms](https://www.canarymedia.com/articles/food-and-farms) | 200 listing | 11 |
| `fossil-fuels` | Fossil fuels | [/articles/fossil-fuels](https://www.canarymedia.com/articles/fossil-fuels) | 200 listing | 11 |
| `fun-stuff` | Fun stuff | [/articles/fun-stuff](https://www.canarymedia.com/articles/fun-stuff) | 200 listing | 7 |
| `geothermal` | Geothermal | [/articles/geothermal](https://www.canarymedia.com/articles/geothermal) | 200 listing | 11 |
| `green-steel` | Green steel | [/articles/green-steel](https://www.canarymedia.com/articles/green-steel) | 200 listing | 11 |
| `guides-and-how-tos` | Guides and how-tos | [/articles/guides-and-how-tos](https://www.canarymedia.com/articles/guides-and-how-tos) | 200 listing | 11 |
| `heat-pumps` | Heat pumps | [/articles/heat-pumps](https://www.canarymedia.com/articles/heat-pumps) | 200 listing | 11 |
| `hydrogen` | Hydrogen | [/articles/hydrogen](https://www.canarymedia.com/articles/hydrogen) | 200 listing | 11 |
| `hydropower` | Hydropower | [/articles/hydropower](https://www.canarymedia.com/articles/hydropower) | 200 listing | 11 |
| `just-transition` | Just transition | [/articles/just-transition](https://www.canarymedia.com/articles/just-transition) | 200 listing | 11 |
| `land-use` | Land use | [/articles/land-use](https://www.canarymedia.com/articles/land-use) | 200 listing | 11 |
| `liquefied-natural-gas` | Liquefied natural gas | [/articles/liquefied-natural-gas](https://www.canarymedia.com/articles/liquefied-natural-gas) | 200 listing | 11 |
| `long-duration-energy-storage` | Long-duration energy storage | [/articles/long-duration-energy-storage](https://www.canarymedia.com/articles/long-duration-energy-storage) | 200 listing | 11 |
| `sea-transport` | Marine transport | [/articles/sea-transport](https://www.canarymedia.com/articles/sea-transport) | 200 listing | 11 |
| `methane` | Methane | [/articles/methane](https://www.canarymedia.com/articles/methane) | 200 listing | 11 |
| `nuclear` | Nuclear | [/articles/nuclear](https://www.canarymedia.com/articles/nuclear) | 200 listing | 11 |
| `ocean-energy` | Ocean energy | [/articles/ocean-energy](https://www.canarymedia.com/articles/ocean-energy) | 200 listing | 4 |
| `offshore-wind` | Offshore wind | [/articles/offshore-wind](https://www.canarymedia.com/articles/offshore-wind) | 200 listing | 11 |
| `policy-regulation` | Policy & regulation | [/articles/policy-regulation](https://www.canarymedia.com/articles/policy-regulation) | 200 listing | 11 |
| `politics` | Politics | [/articles/politics](https://www.canarymedia.com/articles/politics) | 200 listing | 11 |
| `public-transit` | Public transit | [/articles/public-transit](https://www.canarymedia.com/articles/public-transit) | 200 listing | 11 |
| `recycling-renewables` | Recycling renewables | [/articles/recycling-renewables](https://www.canarymedia.com/articles/recycling-renewables) | 200 listing | 11 |
| `transmission` | Transmission | [/articles/transmission](https://www.canarymedia.com/articles/transmission) | 200 listing | 11 |
| `utilities` | Utilities | [/articles/utilities](https://www.canarymedia.com/articles/utilities) | 200 listing | 11 |
| `virtual-power-plants` | Virtual power plants | [/articles/virtual-power-plants](https://www.canarymedia.com/articles/virtual-power-plants) | 200 listing | 10 |
| `workforce-diversity` | Workforce diversity | [/articles/workforce-diversity](https://www.canarymedia.com/articles/workforce-diversity) | 200 listing | 11 |


### Lawfare

- provider id: `lawfare`
- bootstrap state: disabled by default
- default selected targets: `Cybersecurity & Tech`, `Surveillance & Privacy`
- catalog behavior: Static catalog covering all twelve Topics navigation entries. Listing extraction accepts written article titles and excludes podcast and multimedia entries.
- verification: **2026-10-17**. The Topics navigation is present in accessible Cybersecurity & Tech HTML and indexed first-party pages. Cybersecurity & Tech produced written candidates and a representative article supplied a readable body, author, and publication date. The homepage and the other eleven destinations returned HTTP 403 challenge pages; a repeated Congress request was also blocked. Their raw listing extraction remains unverified.
- first-party catalog references: [publisher homepage](https://www.lawfaremedia.org/), [accessible Topics navigation](https://www.lawfaremedia.org/topics/cybersecurity-tech)
- article verification samples: [Written article](https://www.lawfaremedia.org/article/russia's-digital-detox-boomerang)

| Key | Target | Destination | HTTP/content | Candidates |
| --- | --- | --- | --- | --- |
| `cybersecurity-tech` | Cybersecurity & Tech | [/topics/cybersecurity-tech](https://www.lawfaremedia.org/topics/cybersecurity-tech) | 200 listing | 10 |
| `surveillance-privacy` | Surveillance & Privacy | [/topics/surveillance-privacy](https://www.lawfaremedia.org/topics/surveillance-privacy) | 403 challenge | — |
| `intelligence` | Intelligence | [/topics/intelligence](https://www.lawfaremedia.org/topics/intelligence) | 403 challenge | — |
| `foreign-relations-international-law` | Foreign Relations & International Law | [/topics/foreign-relations-international-law](https://www.lawfaremedia.org/topics/foreign-relations-international-law) | 403 challenge | — |
| `armed-conflict` | Armed Conflict | [/topics/armed-conflict](https://www.lawfaremedia.org/topics/armed-conflict) | 403 challenge | — |
| `congress` | Congress | [/topics/congress](https://www.lawfaremedia.org/topics/congress) | 403 challenge | — |
| `courts-litigation` | Courts & Litigation | [/topics/courts-litigation](https://www.lawfaremedia.org/topics/courts-litigation) | 403 challenge | — |
| `criminal-justice-rule-of-law` | Criminal Justice & Rule of Law | [/topics/criminal-justice-rule-of-law](https://www.lawfaremedia.org/topics/criminal-justice-rule-of-law) | 403 challenge | — |
| `democracy-elections` | Democracy & Elections | [/topics/democracy-elections](https://www.lawfaremedia.org/topics/democracy-elections) | 403 challenge | — |
| `executive-branch` | Executive Branch | [/topics/executive-branch](https://www.lawfaremedia.org/topics/executive-branch) | 403 challenge | — |
| `states-localities` | States & Localities | [/topics/states-localities](https://www.lawfaremedia.org/topics/states-localities) | 403 challenge | — |
| `terrorism-extremism` | Terrorism & Extremism | [/topics/terrorism-extremism](https://www.lawfaremedia.org/topics/terrorism-extremism) | 403 challenge | — |


### InfoQ

- provider id: `infoq`
- bootstrap state: disabled by default
- default selected targets: `Software Architecture`, `Cloud Architecture`
- catalog behavior: Static catalog covering the technical navigation topics and Cloud Architecture. Candidate extraction is restricted to each page’s News and Articles modules, excluding podcasts, presentations, and guides.
- verification: **2026-10-17**. All 46 destinations produced written-article candidates; a representative article supplied a readable body, author, and publication date. Case Studies, Patterns, and Security use the canonical /case_study/, /designpattern/, and /security/ destinations.
- first-party catalog reference: [publisher navigation or topic index](https://www.infoq.com/)
- article verification samples: [Written article](https://www.infoq.com/news/2026/10/aws-enhanced-eventbridge-buses/)

| Key | Target | Destination | HTTP/content | Candidates |
| --- | --- | --- | --- | --- |
| `software-architecture` | Software Architecture | [/architecture/](https://www.infoq.com/architecture/) | 200 listing | 15 |
| `cloud-architecture` | Cloud Architecture | [/cloud-architecture/](https://www.infoq.com/cloud-architecture/) | 200 listing | 23 |
| `devops` | DevOps | [/devops/](https://www.infoq.com/devops/) | 200 listing | 15 |
| `ai-ml-data-engineering` | AI, ML & Data Engineering | [/ai-ml-data-eng/](https://www.infoq.com/ai-ml-data-eng/) | 200 listing | 15 |
| `java` | Java | [/java/](https://www.infoq.com/java/) | 200 listing | 15 |
| `development` | Development | [/development/](https://www.infoq.com/development/) | 200 listing | 15 |
| `kotlin` | Kotlin | [/kotlin/](https://www.infoq.com/kotlin/) | 200 listing | 23 |
| `dotnet` | .NET | [/dotnet/](https://www.infoq.com/dotnet/) | 200 listing | 15 |
| `c-sharp` | C# | [/c_sharp/](https://www.infoq.com/c_sharp/) | 200 listing | 20 |
| `swift` | Swift | [/swift/](https://www.infoq.com/swift/) | 200 listing | 27 |
| `golang` | Go | [/golang/](https://www.infoq.com/golang/) | 200 listing | 20 |
| `rust` | Rust | [/rust/](https://www.infoq.com/rust/) | 200 listing | 20 |
| `javascript` | JavaScript | [/javascript/](https://www.infoq.com/javascript/) | 200 listing | 15 |
| `architecture-design` | Architecture & Design | [/architecture-design/](https://www.infoq.com/architecture-design/) | 200 listing | 15 |
| `enterprise-architecture` | Enterprise Architecture | [/enterprise-architecture/](https://www.infoq.com/enterprise-architecture/) | 200 listing | 15 |
| `performance-scalability` | Scalability/Performance | [/performance-scalability/](https://www.infoq.com/performance-scalability/) | 200 listing | 22 |
| `design` | Design | [/design/](https://www.infoq.com/design/) | 200 listing | 15 |
| `case-study` | Case Studies | [/case_study/](https://www.infoq.com/case_study/) | 200 listing | 24 |
| `microservices` | Microservices | [/microservices/](https://www.infoq.com/microservices/) | 200 listing | 15 |
| `servicemesh` | Service Mesh | [/servicemesh/](https://www.infoq.com/servicemesh/) | 200 listing | 16 |
| `designpattern` | Patterns | [/designpattern/](https://www.infoq.com/designpattern/) | 200 listing | 19 |
| `security` | Security | [/security/](https://www.infoq.com/security/) | 200 listing | 15 |
| `bigdata` | Big Data | [/bigdata/](https://www.infoq.com/bigdata/) | 200 listing | 15 |
| `machinelearning` | Machine Learning | [/machinelearning/](https://www.infoq.com/machinelearning/) | 200 listing | 15 |
| `nosql` | NoSQL | [/nosql/](https://www.infoq.com/nosql/) | 200 listing | 18 |
| `database` | Database | [/database/](https://www.infoq.com/database/) | 200 listing | 15 |
| `data-analytics` | Data Analytics | [/data-analytics/](https://www.infoq.com/data-analytics/) | 200 listing | 22 |
| `streaming` | Streaming | [/streaming/](https://www.infoq.com/streaming/) | 200 listing | 20 |
| `culture-methods` | Culture & Methods | [/culture-methods/](https://www.infoq.com/culture-methods/) | 200 listing | 15 |
| `agile` | Agile | [/agile/](https://www.infoq.com/agile/) | 200 listing | 15 |
| `diversity` | Diversity | [/diversity/](https://www.infoq.com/diversity/) | 200 listing | 18 |
| `leadership` | Leadership | [/leadership/](https://www.infoq.com/leadership/) | 200 listing | 15 |
| `lean` | Lean/Kanban | [/lean/](https://www.infoq.com/lean/) | 200 listing | 16 |
| `personal-growth` | Personal Growth | [/personal-growth/](https://www.infoq.com/personal-growth/) | 200 listing | 19 |
| `scrum` | Scrum | [/scrum/](https://www.infoq.com/scrum/) | 200 listing | 15 |
| `sociocracy` | Sociocracy | [/sociocracy/](https://www.infoq.com/sociocracy/) | 200 listing | 15 |
| `software-craftsmanship` | Software Craftsmanship | [/software_craftsmanship/](https://www.infoq.com/software_craftsmanship/) | 200 listing | 16 |
| `team-collaboration` | Team Collaboration | [/team-collaboration/](https://www.infoq.com/team-collaboration/) | 200 listing | 16 |
| `testing` | Testing | [/testing/](https://www.infoq.com/testing/) | 200 listing | 16 |
| `ux` | UX | [/ux/](https://www.infoq.com/ux/) | 200 listing | 20 |
| `infrastructure` | Infrastructure | [/infrastructure/](https://www.infoq.com/infrastructure/) | 200 listing | 15 |
| `continuous-delivery` | Continuous Delivery | [/continuous_delivery/](https://www.infoq.com/continuous_delivery/) | 200 listing | 15 |
| `automation` | Automation | [/automation/](https://www.infoq.com/automation/) | 200 listing | 18 |
| `containers` | Containers | [/containers/](https://www.infoq.com/containers/) | 200 listing | 16 |
| `cloud-computing` | Cloud | [/cloud-computing/](https://www.infoq.com/cloud-computing/) | 200 listing | 15 |
| `observability` | Observability | [/observability/](https://www.infoq.com/observability/) | 200 listing | 16 |


### Deloitte Insights

- provider id: `deloitteinsights`
- bootstrap state: disabled by default
- default selected targets: `Strategy`, `Technology`
- catalog behavior: Static catalog covering the editorial Topics menu. Candidate discovery uses the first-party search endpoint and each target’s search tag. Economics uses the research-center hub. Article parsing supports insights articles and readable research-center hubs.
- verification: **2026-10-17**. All six destination pages were accessible. The search endpoint returned HTTP 403 for each target’s discovery request, so candidate discovery remains unverified. A representative Tech Trends article supplied a readable body, author, and publication date. Economics uses the research-center hub; /us/en/insights/topics/economy.html resolves to that hub. Leadership appears in suggested topics and is outside the six-item editorial Topics menu.
- first-party catalog reference: [publisher navigation or topic index](https://www.deloitte.com/us/en/insights.html)
- article verification samples: [Technology](https://www.deloitte.com/us/en/insights/topics/technology-management/tech-trends.html)

| Key | Target | Destination | HTTP/content | Candidates |
| --- | --- | --- | --- | --- |
| `business-strategy-growth` | Strategy | [/us/en/insights/topics/business-strategy-growth.html](https://www.deloitte.com/us/en/insights/topics/business-strategy-growth.html) | 200 hub; discovery 403 | — |
| `technology-management` | Technology | [/us/en/insights/topics/technology-management.html](https://www.deloitte.com/us/en/insights/topics/technology-management.html) | 200 hub; discovery 403 | — |
| `talent` | Workforce | [/us/en/insights/topics/talent.html](https://www.deloitte.com/us/en/insights/topics/talent.html) | 200 hub; discovery 403 | — |
| `operations` | Operations | [/us/en/insights/topics/operations.html](https://www.deloitte.com/us/en/insights/topics/operations.html) | 200 hub; discovery 403 | — |
| `economy` | Economics | [/us/en/insights/research-centers/economics.html](https://www.deloitte.com/us/en/insights/research-centers/economics.html) | 200 hub; discovery 403 | — |
| `sustainability` | Sustainability | [/us/en/insights/topics/sustainability.html](https://www.deloitte.com/us/en/insights/topics/sustainability.html) | 200 hub; discovery 403 | — |


### Harvard Business Review

- provider id: `hbr`
- bootstrap state: disabled by default
- default selected targets: `Leadership`, `Strategy`
- catalog behavior: Static catalog covering the featured subjects on the Topics index. Candidate extraction reads Digital Article records from server-rendered Next.js result state and supports stream-item cards. Magazine articles, podcasts, store items, and external URLs are excluded. The exhaustive alphabetical subject, industry, and geography directories are outside this catalog.
- verification: **2026-10-17**. All 17 destinations produced digital-article candidates; a representative article supplied a readable body, author, and publication date. Work-life Balance uses the canonical /topic/subject/work_life-balance destination with the stable key work-life-balance. The navigation label Managing Teams links to Managing People; the catalog uses the topic-page label.
- first-party catalog reference: [publisher navigation or topic index](https://hbr.org/topics)
- article verification samples: [Written article](https://hbr.org/2026/10/the-most-consequential-move-a-new-ceo-can-make)

| Key | Target | Destination | HTTP/content | Candidates |
| --- | --- | --- | --- | --- |
| `leadership` | Leadership | [/topic/subject/leadership](https://hbr.org/topic/subject/leadership) | 200 listing | 3 |
| `strategy` | Strategy | [/topic/subject/strategy](https://hbr.org/topic/subject/strategy) | 200 listing | 3 |
| `innovation` | Innovation | [/topic/subject/innovation](https://hbr.org/topic/subject/innovation) | 200 listing | 3 |
| `managing-people` | Managing People | [/topic/subject/managing-people](https://hbr.org/topic/subject/managing-people) | 200 listing | 7 |
| `managing-yourself` | Managing Yourself | [/topic/subject/managing-yourself](https://hbr.org/topic/subject/managing-yourself) | 200 listing | 4 |
| `gender` | Gender | [/topic/subject/gender](https://hbr.org/topic/subject/gender) | 200 listing | 3 |
| `work-life-balance` | Work-life Balance | [/topic/subject/work_life-balance](https://hbr.org/topic/subject/work_life-balance) | 200 listing | 1 |
| `technology-and-analytics` | Technology and Analytics | [/topic/subject/technology-and-analytics](https://hbr.org/topic/subject/technology-and-analytics) | 200 listing | 7 |
| `organizational-culture` | Organizational Culture | [/topic/subject/organizational-culture](https://hbr.org/topic/subject/organizational-culture) | 200 listing | 3 |
| `marketing` | Marketing | [/topic/subject/marketing](https://hbr.org/topic/subject/marketing) | 200 listing | 2 |
| `business-communication` | Business Communication | [/topic/subject/business-communication](https://hbr.org/topic/subject/business-communication) | 200 listing | 4 |
| `economics` | Economics | [/topic/subject/economics](https://hbr.org/topic/subject/economics) | 200 listing | 4 |
| `decision-making-and-problem-solving` | Decision Making and Problem Solving | [/topic/subject/decision-making-and-problem-solving](https://hbr.org/topic/subject/decision-making-and-problem-solving) | 200 listing | 3 |
| `competitive-strategy` | Competitive Strategy | [/topic/subject/competitive-strategy](https://hbr.org/topic/subject/competitive-strategy) | 200 listing | 5 |
| `customer-experience` | Customer Experience | [/topic/subject/customer-experience](https://hbr.org/topic/subject/customer-experience) | 200 listing | 4 |
| `international-business` | International Business | [/topic/subject/international-business](https://hbr.org/topic/subject/international-business) | 200 listing | 4 |
| `career-planning` | Career Planning | [/topic/subject/career-planning](https://hbr.org/topic/subject/career-planning) | 200 listing | 6 |


### ScienceDaily

- provider id: `sciencedaily`
- bootstrap state: disabled by default
- default selected targets: `Health & Medicine`, `Computers & Math`
- catalog behavior: Static catalog covering the primary science sections, Latest, and Top Science News. Candidate extraction is scoped to the category-page headline modules, and article URLs are restricted to internal `/releases/*` pages. Deeper subtopic directories are outside this catalog.
- verification: **2026-10-17**. All 15 destinations produced native release candidates, including Latest and Top Science News. Representative release articles supplied readable bodies, institutional sources, and dates. Strange & Offbeat identifies the /news/strange_offbeat/ section. Deeper science subtopics remain outside this catalog.
- first-party catalog reference: [publisher navigation or topic index](https://www.sciencedaily.com/)
- article verification samples: [Written article](https://www.sciencedaily.com/releases/2026/10/261014072018.htm), [Latest](https://www.sciencedaily.com/releases/2026/10/261015003803.htm)

| Key | Target | Destination | HTTP/content | Candidates |
| --- | --- | --- | --- | --- |
| `health_medicine` | Health & Medicine | [/news/health_medicine/](https://www.sciencedaily.com/news/health_medicine/) | 200 listing | 122 |
| `computers_math` | Computers & Math | [/news/computers_math/](https://www.sciencedaily.com/news/computers_math/) | 200 listing | 122 |
| `earth_climate` | Earth & Climate | [/news/earth_climate/](https://www.sciencedaily.com/news/earth_climate/) | 200 listing | 122 |
| `mind_brain` | Mind & Brain | [/news/mind_brain/](https://www.sciencedaily.com/news/mind_brain/) | 200 listing | 122 |
| `matter_energy` | Matter & Energy | [/news/matter_energy/](https://www.sciencedaily.com/news/matter_energy/) | 200 listing | 122 |
| `living_well` | Living Well | [/news/living_well/](https://www.sciencedaily.com/news/living_well/) | 200 listing | 122 |
| `space_time` | Space & Time | [/news/space_time/](https://www.sciencedaily.com/news/space_time/) | 200 listing | 122 |
| `plants_animals` | Plants & Animals | [/news/plants_animals/](https://www.sciencedaily.com/news/plants_animals/) | 200 listing | 122 |
| `fossils_ruins` | Fossils & Ruins | [/news/fossils_ruins/](https://www.sciencedaily.com/news/fossils_ruins/) | 200 listing | 122 |
| `science_society` | Science & Society | [/news/science_society/](https://www.sciencedaily.com/news/science_society/) | 200 listing | 122 |
| `business_industry` | Business & Industry | [/news/business_industry/](https://www.sciencedaily.com/news/business_industry/) | 200 listing | 122 |
| `education_learning` | Education & Learning | [/news/education_learning/](https://www.sciencedaily.com/news/education_learning/) | 200 listing | 122 |
| `strange_offbeat` | Strange & Offbeat | [/news/strange_offbeat/](https://www.sciencedaily.com/news/strange_offbeat/) | 200 listing | 122 |
| `latest` | Latest | [/news/](https://www.sciencedaily.com/news/) | 200 listing | 122 |
| `top-science` | Top Science News | [/news/top/science/](https://www.sciencedaily.com/news/top/science/) | 200 listing | 122 |
