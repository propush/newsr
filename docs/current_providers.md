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

Last audited: **2026-10-10**. The built-in catalog contains **19 providers and 376 targets**. The audit compares first-party navigation and primary topic indexes, checks destination content and extracted candidates, and checks representative written articles. Individual product models, exhaustive tag directories, temporary promotions, and podcast-only destinations are outside the catalog. Accessible empty topic pages are identified explicitly; HTTP success alone does not establish an article-bearing listing.

The verification notes below distinguish direct HTML checks from indexed first-party evidence and blocked endpoints. Static catalogs represent this audit snapshot; BBC also supports live navigation discovery.

## Built-in Providers

### BBC News

- provider id: `bbc`
- bootstrap state: enabled by default
- default selected targets: `World`, `Technology`, `Business`, `Entertainment & Arts`
- catalog behavior: Live discovery merges navigation categories with the built-in catalog. Regional `/news/world/*` pages and top-level editorial sections are supported. Candidates include native news reports and written BBC features; live coverage, video pages, external links, and topic indexes are excluded.
- verification: All built-in destinations produced written-article candidates. Representative news and Culture feature articles were parsed.
- first-party catalog reference: [publisher navigation or topic index](https://www.bbc.com/news)

| Target | Destination |
| --- | --- |
| World | [/news/world](https://www.bbc.com/news/world) |
| Technology | [/technology](https://www.bbc.com/technology) |
| Business | [/business](https://www.bbc.com/business) |
| Entertainment & Arts | [/culture/entertainment-news](https://www.bbc.com/culture/entertainment-news) |
| BBC InDepth | [/news/bbcindepth](https://www.bbc.com/news/bbcindepth) |
| Science & Environment | [/news/science_and_environment](https://www.bbc.com/news/science_and_environment) |
| Health | [/health](https://www.bbc.com/health) |
| Newsbeat | [/news/newsbeat](https://www.bbc.com/news/newsbeat) |
| Latest | [/news](https://www.bbc.com/news) |
| US & Canada | [/news/us-canada](https://www.bbc.com/news/us-canada) |
| UK | [/news/uk](https://www.bbc.com/news/uk) |
| Africa | [/news/world/africa](https://www.bbc.com/news/world/africa) |
| Asia | [/news/world/asia](https://www.bbc.com/news/world/asia) |
| Australia | [/news/world/australia](https://www.bbc.com/news/world/australia) |
| Europe | [/news/world/europe](https://www.bbc.com/news/world/europe) |
| Latin America | [/news/world/latin_america](https://www.bbc.com/news/world/latin_america) |
| Middle East | [/news/world/middle_east](https://www.bbc.com/news/world/middle_east) |
| BBC Verify | [/news/bbcverify](https://www.bbc.com/news/bbcverify) |
| UK Politics | [/news/politics](https://www.bbc.com/news/politics) |
| England | [/news/england](https://www.bbc.com/news/england) |
| Northern Ireland | [/news/northern_ireland](https://www.bbc.com/news/northern_ireland) |
| Scotland | [/news/scotland](https://www.bbc.com/news/scotland) |
| Wales | [/news/wales](https://www.bbc.com/news/wales) |
| Culture | [/culture](https://www.bbc.com/culture) |
| Arts | [/arts](https://www.bbc.com/arts) |
| Travel | [/travel](https://www.bbc.com/travel) |
| Earth | [/future-planet](https://www.bbc.com/future-planet) |

### 9to5Mac

- provider id: `9to5mac`
- bootstrap state: disabled by default
- default selected targets: `Latest`, `iPhone`, `Mac`, `iPad`, `Apple Watch`
- catalog behavior: Static guide-backed catalog with the site root as Latest. Candidate extraction accepts native written articles and excludes podcast cards.
- verification: All destinations produced candidates; a representative article was parsed.
- first-party catalog reference: [publisher navigation or topic index](https://9to5mac.com/)

| Target | Destination |
| --- | --- |
| Latest | [/](https://9to5mac.com/) |
| iPhone | [/guides/iphone/](https://9to5mac.com/guides/iphone/) |
| Mac | [/guides/mac/](https://9to5mac.com/guides/mac/) |
| iPad | [/guides/ipad/](https://9to5mac.com/guides/ipad/) |
| Apple Watch | [/guides/apple-watch/](https://9to5mac.com/guides/apple-watch/) |
| Vision Pro | [/guides/vision-pro/](https://9to5mac.com/guides/vision-pro/) |
| Apple TV | [/guides/apple-tv/](https://9to5mac.com/guides/apple-tv/) |
| AirPods | [/guides/airpods/](https://9to5mac.com/guides/airpods/) |
| HomeKit | [/guides/homekit/](https://9to5mac.com/guides/homekit/) |
| Reviews | [/guides/review/](https://9to5mac.com/guides/review/) |
| How Tos | [/guides/how-to/](https://9to5mac.com/guides/how-to/) |
| App Store | [/guides/app-store/](https://9to5mac.com/guides/app-store/) |
| Apple Music | [/guides/apple-music/](https://9to5mac.com/guides/apple-music/) |
| CarPlay | [/guides/carplay/](https://9to5mac.com/guides/carplay/) |
| Siri | [/guides/siri/](https://9to5mac.com/guides/siri/) |
| Apple Silicon | [/guides/apple-silicon/](https://9to5mac.com/guides/apple-silicon/) |
| Apple Arcade | [/guides/apple-arcade/](https://9to5mac.com/guides/apple-arcade/) |
| AAPL | [/guides/aapl/](https://9to5mac.com/guides/aapl/) |
| iOS | [/guides/ios/](https://9to5mac.com/guides/ios/) |
| iPadOS | [/guides/ipados/](https://9to5mac.com/guides/ipados/) |
| macOS | [/guides/macos/](https://9to5mac.com/guides/macos/) |
| watchOS | [/guides/watchos/](https://9to5mac.com/guides/watchos/) |
| visionOS | [/guides/visionos/](https://9to5mac.com/guides/visionos/) |
| Apple Health | [/guides/apple-health/](https://9to5mac.com/guides/apple-health/) |
| Apple Store | [/guides/apple-store/](https://9to5mac.com/guides/apple-store/) |
| Apple Card | [/guides/apple-card/](https://9to5mac.com/guides/apple-card/) |
| Apple One | [/guides/apple-one/](https://9to5mac.com/guides/apple-one/) |
| Apple Fitness+ | [/guides/apple-fitness/](https://9to5mac.com/guides/apple-fitness/) |
| AI | [/guides/ai/](https://9to5mac.com/guides/ai/) |

### 9to5Google

- provider id: `ninetofivegoogle`
- bootstrap state: disabled by default
- default selected targets: `Latest`, `Pixel`, `Android`, `Chrome`, `TV`, `Workspace`
- catalog behavior: Static guide-backed catalog with the site root as Latest and feature-backed Reviews and Exclusives. Taxonomy classes for YouTube topics are supported while embedded video and podcast cards are excluded.
- verification: All destinations produced candidates; a representative article was parsed. Cars and some guide pages contain older archive material.
- first-party catalog reference: [publisher navigation or topic index](https://9to5google.com/)

| Target | Destination |
| --- | --- |
| Latest | [/](https://9to5google.com/) |
| Pixel | [/guides/google-pixel/](https://9to5google.com/guides/google-pixel/) |
| Android | [/guides/android/](https://9to5google.com/guides/android/) |
| Chrome | [/guides/google-chrome/](https://9to5google.com/guides/google-chrome/) |
| TV | [/guides/google-tv/](https://9to5google.com/guides/google-tv/) |
| Workspace | [/guides/google-workspace/](https://9to5google.com/guides/google-workspace/) |
| Assistant | [/guides/google-assistant/](https://9to5google.com/guides/google-assistant/) |
| Smart Home | [/guides/smart-home/](https://9to5google.com/guides/smart-home/) |
| Cars | [/guides/cars/](https://9to5google.com/guides/cars/) |
| Reviews | [/feature/review/](https://9to5google.com/feature/review/) |
| How Tos | [/guides/how-to/](https://9to5google.com/guides/how-to/) |
| Deals | [/guides/deals/](https://9to5google.com/guides/deals/) |
| Gemini | [/guides/gemini/](https://9to5google.com/guides/gemini/) |
| Nest | [/guides/google-nest/](https://9to5google.com/guides/google-nest/) |
| ChromeOS | [/guides/chrome-os/](https://9to5google.com/guides/chrome-os/) |
| Android Auto | [/guides/android-auto/](https://9to5google.com/guides/android-auto/) |
| Wear OS | [/guides/wear-os/](https://9to5google.com/guides/wear-os/) |
| YouTube | [/guides/youtube/](https://9to5google.com/guides/youtube/) |
| YouTube Music | [/guides/youtube-music/](https://9to5google.com/guides/youtube-music/) |
| YouTube TV | [/guides/youtube-tv/](https://9to5google.com/guides/youtube-tv/) |
| Exclusives | [/feature/exclusives/](https://9to5google.com/feature/exclusives/) |

### TechCrunch

- provider id: `techcrunch`
- bootstrap state: disabled by default
- default selected targets: `Latest`, `Startups`, `Venture`, `AI`, `Security`
- catalog behavior: Static catalog covering the editorial Topics menu, including its featured company topics. Latest uses `/latest/`; AI uses the artificial-intelligence category.
- verification: All destinations produced candidates; a representative article was parsed.
- first-party catalog reference: [publisher navigation or topic index](https://techcrunch.com/)

| Target | Destination |
| --- | --- |
| Latest | [/latest/](https://techcrunch.com/latest/) |
| Startups | [/category/startups/](https://techcrunch.com/category/startups/) |
| Venture | [/category/venture/](https://techcrunch.com/category/venture/) |
| AI | [/category/artificial-intelligence/](https://techcrunch.com/category/artificial-intelligence/) |
| Security | [/category/security/](https://techcrunch.com/category/security/) |
| Apps | [/category/apps/](https://techcrunch.com/category/apps/) |
| Fintech | [/category/fintech/](https://techcrunch.com/category/fintech/) |
| Enterprise | [/category/enterprise/](https://techcrunch.com/category/enterprise/) |
| Climate | [/category/climate/](https://techcrunch.com/category/climate/) |
| Robotics | [/category/robotics/](https://techcrunch.com/category/robotics/) |
| Government & Policy | [/category/government-policy/](https://techcrunch.com/category/government-policy/) |
| Apple | [/tag/apple/](https://techcrunch.com/tag/apple/) |
| Amazon | [/tag/amazon/](https://techcrunch.com/tag/amazon/) |
| Biotech & Health | [/category/biotech-health/](https://techcrunch.com/category/biotech-health/) |
| Cloud Computing | [/tag/cloud-computing/](https://techcrunch.com/tag/cloud-computing/) |
| Commerce | [/category/commerce/](https://techcrunch.com/category/commerce/) |
| Crypto | [/category/cryptocurrency/](https://techcrunch.com/category/cryptocurrency/) |
| EVs | [/tag/evs/](https://techcrunch.com/tag/evs/) |
| Fundraising | [/category/fundraising/](https://techcrunch.com/category/fundraising/) |
| Gadgets | [/category/gadgets/](https://techcrunch.com/category/gadgets/) |
| Gaming | [/category/gaming/](https://techcrunch.com/category/gaming/) |
| Google | [/tag/google/](https://techcrunch.com/tag/google/) |
| Hardware | [/category/hardware/](https://techcrunch.com/category/hardware/) |
| Instagram | [/tag/instagram/](https://techcrunch.com/tag/instagram/) |
| Layoffs | [/tag/layoffs/](https://techcrunch.com/tag/layoffs/) |
| Media & Entertainment | [/category/media-entertainment/](https://techcrunch.com/category/media-entertainment/) |
| Meta | [/tag/meta/](https://techcrunch.com/tag/meta/) |
| Microsoft | [/tag/microsoft/](https://techcrunch.com/tag/microsoft/) |
| Privacy | [/category/privacy/](https://techcrunch.com/category/privacy/) |
| Social | [/category/social/](https://techcrunch.com/category/social/) |
| Space | [/category/space/](https://techcrunch.com/category/space/) |
| TikTok | [/tag/tiktok/](https://techcrunch.com/tag/tiktok/) |
| Transportation | [/category/transportation/](https://techcrunch.com/category/transportation/) |

### The Hacker News

- provider id: `thehackernews`
- bootstrap state: disabled by default
- default selected targets: `Threat Intelligence`, `Cyber Attacks`, `Vulnerabilities`, `Expert Insights`
- catalog behavior: Static catalog of the four written-news sections in site navigation.
- verification: Navigation was confirmed through indexed first-party content. Direct HTTP requests to the homepage and all four sections returned 403; current raw listing and article extraction remain unverified.
- first-party catalog reference: [publisher navigation or topic index](https://thehackernews.com/)

| Target | Destination |
| --- | --- |
| Threat Intelligence | [/search/label/Threat%20Intelligence](https://thehackernews.com/search/label/Threat%20Intelligence) |
| Cyber Attacks | [/search/label/Cyber%20Attack](https://thehackernews.com/search/label/Cyber%20Attack) |
| Vulnerabilities | [/search/label/Vulnerable](https://thehackernews.com/search/label/Vulnerable) |
| Expert Insights | [/expert-insights/](https://thehackernews.com/expert-insights/) |

### Ars Technica

- provider id: `arstechnica`
- bootstrap state: disabled by default
- default selected targets: `Latest`, `Gadgets`, `Science`, `Security`
- catalog behavior: Static mixed catalog with a catch-all Latest feed and editorial sections.
- verification: First-party indexed category pages confirm the sections, including Gaming, Cars, Biz & IT, Health, and Culture. Direct requests returned 403; current raw listing and article extraction remain unverified.
- first-party catalog reference: [publisher navigation or topic index](https://arstechnica.com/)

| Target | Destination |
| --- | --- |
| Latest | [/](https://arstechnica.com/) |
| Gadgets | [/gadgets/](https://arstechnica.com/gadgets/) |
| Science | [/science/](https://arstechnica.com/science/) |
| Security | [/security/](https://arstechnica.com/security/) |
| Tech Policy | [/tech-policy/](https://arstechnica.com/tech-policy/) |
| Space | [/space/](https://arstechnica.com/space/) |
| AI | [/ai/](https://arstechnica.com/ai/) |
| Gaming | [/gaming/](https://arstechnica.com/gaming/) |
| Cars | [/cars/](https://arstechnica.com/cars/) |
| Biz & IT | [/information-technology/](https://arstechnica.com/information-technology/) |
| Health | [/health/](https://arstechnica.com/health/) |
| Culture | [/culture/](https://arstechnica.com/culture/) |

### HR Dive

- provider id: `hrdive`
- bootstrap state: disabled by default
- default selected targets: `Talent`, `Comp & Benefits`
- catalog behavior: Static catalog covering the navigation topic menu.
- verification: All destinations produced candidates; a representative article was parsed.
- first-party catalog reference: [publisher navigation or topic index](https://www.hrdive.com/)

| Target | Destination |
| --- | --- |
| Talent | [/topic/talent/](https://www.hrdive.com/topic/talent/) |
| Comp & Benefits | [/topic/compensation-benefits/](https://www.hrdive.com/topic/compensation-benefits/) |
| Diversity & Inclusion | [/topic/diversity-inclusion/](https://www.hrdive.com/topic/diversity-inclusion/) |
| Learning | [/topic/learning/](https://www.hrdive.com/topic/learning/) |
| HR Management | [/topic/hr-management/](https://www.hrdive.com/topic/hr-management/) |
| Compliance | [/topic/legal/](https://www.hrdive.com/topic/legal/) |
| Tech & Analytics | [/topic/hr-technology-analytics/](https://www.hrdive.com/topic/hr-technology-analytics/) |
| State & Local Laws | [/topic/state-local-laws/](https://www.hrdive.com/topic/state-local-laws/) |

### MedCity News

- provider id: `medcitynews`
- bootstrap state: disabled by default
- default selected targets: `Health Tech`, `Devices & Diagnostics`
- catalog behavior: Static catalog of written news, channels, and contributor articles. Sponsored and webinar destinations are excluded.
- verification: All destinations produced candidates; a representative article was parsed.
- first-party catalog reference: [publisher navigation or topic index](https://medcitynews.com/)

| Target | Destination |
| --- | --- |
| Health Tech | [/category/channel/health-tech/](https://medcitynews.com/category/channel/health-tech/) |
| BioPharma | [/category/channel/biopharma/](https://medcitynews.com/category/channel/biopharma/) |
| Devices & Diagnostics | [/category/channel/medical-devices-and-diagnostics/](https://medcitynews.com/category/channel/medical-devices-and-diagnostics/) |
| Consumer / Employer | [/category/channel/consumer-employer/](https://medcitynews.com/category/channel/consumer-employer/) |
| News | [/category/news/](https://medcitynews.com/category/news/) |
| Contributors | [/category/medcity-influencers/](https://medcitynews.com/category/medcity-influencers/) |
| Artificial Intelligence | [/category/channel/artificial-intelligence/](https://medcitynews.com/category/channel/artificial-intelligence/) |
| Startups | [/category/channel/startup-channel/](https://medcitynews.com/category/channel/startup-channel/) |
| Payers | [/category/channel/payers/](https://medcitynews.com/category/channel/payers/) |
| Providers | [/category/channel/providers/](https://medcitynews.com/category/channel/providers/) |
| Policy | [/category/channel/politics-channel/](https://medcitynews.com/category/channel/politics-channel/) |

### Hyperallergic

- provider id: `hyperallergic`
- bootstrap state: disabled by default
- default selected targets: `News`, `Reviews`
- catalog behavior: Static tag-backed editorial catalog. Reviews, Features, Interviews, Guides, and Announcements use singular tag paths. Explicit Community, Opportunities, and Announcements targets accept editorial posts in those sections; sponsored cards remain excluded.
- verification: All destinations produced eligible candidates; a representative article was parsed.
- first-party catalog reference: [publisher navigation or topic index](https://hyperallergic.com/)

| Target | Destination |
| --- | --- |
| News | [/tag/news/](https://hyperallergic.com/tag/news/) |
| Reviews | [/tag/review/](https://hyperallergic.com/tag/review/) |
| Opinion | [/tag/opinion/](https://hyperallergic.com/tag/opinion/) |
| Film | [/tag/film/](https://hyperallergic.com/tag/film/) |
| Features | [/tag/feature/](https://hyperallergic.com/tag/feature/) |
| Interviews | [/tag/interview/](https://hyperallergic.com/tag/interview/) |
| Community | [/tag/community/](https://hyperallergic.com/tag/community/) |
| Guides | [/tag/guide/](https://hyperallergic.com/tag/guide/) |
| Opportunities | [/tag/opportunities/](https://hyperallergic.com/tag/opportunities/) |
| Announcements | [/tag/announcement/](https://hyperallergic.com/tag/announcement/) |
| Books | [/tag/books/](https://hyperallergic.com/tag/books/) |
| Comics | [/tag/comics/](https://hyperallergic.com/tag/comics/) |

### EdSurge

- provider id: `edsurge`
- bootstrap state: disabled by default
- default selected targets: `Latest`, `Higher Education`
- catalog behavior: Static catalog using the homepage for Latest and `/coverage-areas/*` for the published coverage-area catalog. Written article URLs support both undated slugs and dated archive slugs. Podcast cards are excluded.
- verification: The homepage produced written candidates and a representative article body, author, and date were parsed. All 16 coverage-area pages exist but currently render “No Articles Available under this topic”; these targets can return an empty result. No cross-category fallback is used.
- first-party catalog reference: [publisher navigation or topic index](https://www.edsurge.com/)

| Target | Destination |
| --- | --- |
| Latest | [/](https://www.edsurge.com/) |
| Higher Education | [/coverage-areas/higher-education](https://www.edsurge.com/coverage-areas/higher-education) |
| Artificial Intelligence | [/coverage-areas/artificial-intelligence](https://www.edsurge.com/coverage-areas/artificial-intelligence) |
| Career Readiness | [/coverage-areas/career-readiness](https://www.edsurge.com/coverage-areas/career-readiness) |
| Access and Inclusion | [/coverage-areas/access-and-inclusion](https://www.edsurge.com/coverage-areas/access-and-inclusion) |
| Early Learning | [/coverage-areas/early-learning](https://www.edsurge.com/coverage-areas/early-learning) |
| Education Workforce | [/coverage-areas/education-workforce](https://www.edsurge.com/coverage-areas/education-workforce) |
| Teaching and Learning | [/coverage-areas/teaching-and-learning](https://www.edsurge.com/coverage-areas/teaching-and-learning) |
| Policy and Government | [/coverage-areas/policy-and-government](https://www.edsurge.com/coverage-areas/policy-and-government) |
| Edtech Business | [/coverage-areas/edtech-business](https://www.edsurge.com/coverage-areas/edtech-business) |
| Assessments | [/coverage-areas/assessments](https://www.edsurge.com/coverage-areas/assessments) |
| Digital Skills | [/coverage-areas/digital-skills](https://www.edsurge.com/coverage-areas/digital-skills) |
| Media Literacy | [/coverage-areas/media-literacy](https://www.edsurge.com/coverage-areas/media-literacy) |
| Social-Emotional Learning | [/coverage-areas/social-emotional-learning](https://www.edsurge.com/coverage-areas/social-emotional-learning) |
| Digital Access | [/coverage-areas/digital-access](https://www.edsurge.com/coverage-areas/digital-access) |
| Instructional Trends | [/coverage-areas/instructional-trends](https://www.edsurge.com/coverage-areas/instructional-trends) |
| Data Privacy | [/coverage-areas/data-privacy](https://www.edsurge.com/coverage-areas/data-privacy) |

### Marketing Dive

- provider id: `marketingdive`
- bootstrap state: disabled by default
- default selected targets: `Brand Strategy`, `Social Media`
- catalog behavior: Static topic catalog with Marketing mapped to the homepage. Topic paths preserve the publisher’s capitalization, including Social Media and Video.
- verification: All destinations produced candidates; a representative article was parsed.
- first-party catalog reference: [publisher navigation or topic index](https://www.marketingdive.com/)

| Target | Destination |
| --- | --- |
| Brand Strategy | [/topic/brand-strategy/](https://www.marketingdive.com/topic/brand-strategy/) |
| Mobile | [/topic/mobile-marketing/](https://www.marketingdive.com/topic/mobile-marketing/) |
| Creative | [/topic/creative/](https://www.marketingdive.com/topic/creative/) |
| Social Media | [/topic/Social-media-marketing/](https://www.marketingdive.com/topic/Social-media-marketing/) |
| Video | [/topic/Video-marketing/](https://www.marketingdive.com/topic/Video-marketing/) |
| Agencies | [/topic/agencies/](https://www.marketingdive.com/topic/agencies/) |
| Data/Analytics | [/topic/analytics/](https://www.marketingdive.com/topic/analytics/) |
| Influencer Marketing | [/topic/influencer-marketing/](https://www.marketingdive.com/topic/influencer-marketing/) |
| Marketing | [/](https://www.marketingdive.com/) |
| Ad Tech | [/topic/marketing-tech/](https://www.marketingdive.com/topic/marketing-tech/) |
| CMO Corner | [/topic/cmo-corner/](https://www.marketingdive.com/topic/cmo-corner/) |

### Payments Dive

- provider id: `paymentsdive`
- bootstrap state: disabled by default
- default selected targets: `Technology`, `Fraud`
- catalog behavior: Static catalog using the homepage for Latest and the navigation topic destinations. Candidate extraction accepts written articles and filters sponsored cards and trendlines.
- verification: All destinations produced candidates; a representative article was parsed.
- first-party catalog reference: [publisher navigation or topic index](https://www.paymentsdive.com/)

| Target | Destination |
| --- | --- |
| Latest | [/](https://www.paymentsdive.com/) |
| Retail | [/topic/retail/](https://www.paymentsdive.com/topic/retail/) |
| Banking | [/topic/banking/](https://www.paymentsdive.com/topic/banking/) |
| Restaurants | [/topic/restaurants/](https://www.paymentsdive.com/topic/restaurants/) |
| Regulations & Policy | [/topic/regulations_and_policy/](https://www.paymentsdive.com/topic/regulations_and_policy/) |
| Consumer Risk | [/topic/risk/](https://www.paymentsdive.com/topic/risk/) |
| Technology | [/topic/technology/](https://www.paymentsdive.com/topic/technology/) |
| B2B | [/topic/b2b/](https://www.paymentsdive.com/topic/b2b/) |
| Fraud | [/topic/fraud/](https://www.paymentsdive.com/topic/fraud/) |

### Tom's Hardware

- provider id: `tomshardware`
- bootstrap state: disabled by default
- default selected targets: `PC Components`, `CPUs`, `GPUs`
- catalog behavior: Static hardware, software, and technology catalog using server-rendered `/news` indexes. Candidates include written news and reviews, including legacy `/news/*.html` URLs; buying guides, deals, sponsored cards, and category indexes are excluded.
- verification: All destinations produced candidates; a representative article was parsed.
- first-party catalog reference: [publisher navigation or topic index](https://www.tomshardware.com/)

| Target | Destination |
| --- | --- |
| PC Components | [/pc-components/news](https://www.tomshardware.com/pc-components/news) |
| CPUs | [/pc-components/cpus/news](https://www.tomshardware.com/pc-components/cpus/news) |
| GPUs | [/pc-components/gpus/news](https://www.tomshardware.com/pc-components/gpus/news) |
| Storage | [/pc-components/storage/news](https://www.tomshardware.com/pc-components/storage/news) |
| Laptops | [/laptops/news](https://www.tomshardware.com/laptops/news) |
| Desktops | [/desktops/news](https://www.tomshardware.com/desktops/news) |
| Software | [/software/news](https://www.tomshardware.com/software/news) |
| Artificial Intelligence | [/tech-industry/artificial-intelligence/news](https://www.tomshardware.com/tech-industry/artificial-intelligence/news) |
| Latest | [/news](https://www.tomshardware.com/news) |
| RAM | [/pc-components/ram/news](https://www.tomshardware.com/pc-components/ram/news) |
| Cooling | [/pc-components/cooling/news](https://www.tomshardware.com/pc-components/cooling/news) |
| Motherboards | [/pc-components/motherboards/news](https://www.tomshardware.com/pc-components/motherboards/news) |
| Overclocking | [/pc-components/overclocking/news](https://www.tomshardware.com/pc-components/overclocking/news) |
| PC Cases | [/pc-components/pc-cases/news](https://www.tomshardware.com/pc-components/pc-cases/news) |
| Power Supplies | [/pc-components/power-supplies/news](https://www.tomshardware.com/pc-components/power-supplies/news) |
| Networking | [/networking/news](https://www.tomshardware.com/networking/news) |
| Monitors | [/monitors/news](https://www.tomshardware.com/monitors/news) |
| Peripherals | [/peripherals/news](https://www.tomshardware.com/peripherals/news) |
| 3D Printers | [/3d-printing/news](https://www.tomshardware.com/3d-printing/news) |
| Tech Industry | [/tech-industry/news](https://www.tomshardware.com/tech-industry/news) |
| Cybersecurity | [/tech-industry/cyber-security/news](https://www.tomshardware.com/tech-industry/cyber-security/news) |
| Supercomputers | [/tech-industry/supercomputers/news](https://www.tomshardware.com/tech-industry/supercomputers/news) |
| Quantum Computing | [/tech-industry/quantum-computing/news](https://www.tomshardware.com/tech-industry/quantum-computing/news) |
| Operating Systems | [/software/operating-systems/news](https://www.tomshardware.com/software/operating-systems/news) |
| Programming | [/software/programming/news](https://www.tomshardware.com/software/programming/news) |
| Applications | [/software/applications/news](https://www.tomshardware.com/software/applications/news) |
| Web Browsers | [/software/browsers/news](https://www.tomshardware.com/software/browsers/news) |

### Canary Media

- provider id: `canarymedia`
- bootstrap state: disabled by default
- default selected targets: `Grid Edge`, `Solar`
- catalog behavior: Static catalog covering the published View All Topics index through `/articles/<topic>` destinations. The Sponsored topic is excluded.
- verification: All destinations produced candidates; a representative article was parsed.
- first-party catalog reference: [publisher navigation or topic index](https://www.canarymedia.com/articles/categories)

| Target | Destination |
| --- | --- |
| Grid Edge | [/articles/grid-edge](https://www.canarymedia.com/articles/grid-edge) |
| Energy Storage | [/articles/energy-storage](https://www.canarymedia.com/articles/energy-storage) |
| Solar | [/articles/solar](https://www.canarymedia.com/articles/solar) |
| Electrification | [/articles/electrification](https://www.canarymedia.com/articles/electrification) |
| Transportation | [/articles/transportation](https://www.canarymedia.com/articles/transportation) |
| Wind | [/articles/wind](https://www.canarymedia.com/articles/wind) |
| Batteries | [/articles/batteries](https://www.canarymedia.com/articles/batteries) |
| Affordability | [/articles/affordability](https://www.canarymedia.com/articles/affordability) |
| Air travel | [/articles/air-travel](https://www.canarymedia.com/articles/air-travel) |
| Balcony solar | [/articles/balcony-solar](https://www.canarymedia.com/articles/balcony-solar) |
| Canary Media | [/articles/canary-media](https://www.canarymedia.com/articles/canary-media) |
| Carbon capture | [/articles/carbon-capture](https://www.canarymedia.com/articles/carbon-capture) |
| Carbon removal | [/articles/carbon-removal](https://www.canarymedia.com/articles/carbon-removal) |
| Carbon-free buildings | [/articles/carbon-free-buildings](https://www.canarymedia.com/articles/carbon-free-buildings) |
| Clean aluminum | [/articles/clean-aluminum](https://www.canarymedia.com/articles/clean-aluminum) |
| Clean energy | [/articles/clean-energy](https://www.canarymedia.com/articles/clean-energy) |
| Clean energy jobs | [/articles/clean-energy-jobs](https://www.canarymedia.com/articles/clean-energy-jobs) |
| Clean energy manufacturing | [/articles/clean-energy-manufacturing](https://www.canarymedia.com/articles/clean-energy-manufacturing) |
| Clean energy supply chain | [/articles/clean-energy-supply-chain](https://www.canarymedia.com/articles/clean-energy-supply-chain) |
| Clean fleets | [/articles/clean-fleets](https://www.canarymedia.com/articles/clean-fleets) |
| Clean industry | [/articles/clean-industry](https://www.canarymedia.com/articles/clean-industry) |
| Climate crisis | [/articles/climate-crisis](https://www.canarymedia.com/articles/climate-crisis) |
| Climate justice | [/articles/climate-justice](https://www.canarymedia.com/articles/climate-justice) |
| Climatetech finance | [/articles/climatetech-finance](https://www.canarymedia.com/articles/climatetech-finance) |
| Corporate procurement | [/articles/corporate-procurement](https://www.canarymedia.com/articles/corporate-procurement) |
| Culture | [/articles/culture](https://www.canarymedia.com/articles/culture) |
| Data centers | [/articles/data-centers](https://www.canarymedia.com/articles/data-centers) |
| Distributed energy resources | [/articles/distributed-energy-resources](https://www.canarymedia.com/articles/distributed-energy-resources) |
| Electric vehicles | [/articles/electric-vehicles](https://www.canarymedia.com/articles/electric-vehicles) |
| Emissions reduction | [/articles/emissions-reduction](https://www.canarymedia.com/articles/emissions-reduction) |
| Energy efficiency | [/articles/energy-efficiency](https://www.canarymedia.com/articles/energy-efficiency) |
| Energy equity | [/articles/energy-equity](https://www.canarymedia.com/articles/energy-equity) |
| Energy markets | [/articles/energy-markets](https://www.canarymedia.com/articles/energy-markets) |
| ENN | [/articles/enn](https://www.canarymedia.com/articles/enn) |
| EV charging | [/articles/ev-charging](https://www.canarymedia.com/articles/ev-charging) |
| Food and farms | [/articles/food-and-farms](https://www.canarymedia.com/articles/food-and-farms) |
| Fossil fuels | [/articles/fossil-fuels](https://www.canarymedia.com/articles/fossil-fuels) |
| Fun stuff | [/articles/fun-stuff](https://www.canarymedia.com/articles/fun-stuff) |
| Geothermal | [/articles/geothermal](https://www.canarymedia.com/articles/geothermal) |
| Green steel | [/articles/green-steel](https://www.canarymedia.com/articles/green-steel) |
| Guides and how-tos | [/articles/guides-and-how-tos](https://www.canarymedia.com/articles/guides-and-how-tos) |
| Heat pumps | [/articles/heat-pumps](https://www.canarymedia.com/articles/heat-pumps) |
| Hydrogen | [/articles/hydrogen](https://www.canarymedia.com/articles/hydrogen) |
| Hydropower | [/articles/hydropower](https://www.canarymedia.com/articles/hydropower) |
| Just transition | [/articles/just-transition](https://www.canarymedia.com/articles/just-transition) |
| Land use | [/articles/land-use](https://www.canarymedia.com/articles/land-use) |
| Liquefied natural gas | [/articles/liquefied-natural-gas](https://www.canarymedia.com/articles/liquefied-natural-gas) |
| Long-duration energy storage | [/articles/long-duration-energy-storage](https://www.canarymedia.com/articles/long-duration-energy-storage) |
| Marine transport | [/articles/sea-transport](https://www.canarymedia.com/articles/sea-transport) |
| Methane | [/articles/methane](https://www.canarymedia.com/articles/methane) |
| Nuclear | [/articles/nuclear](https://www.canarymedia.com/articles/nuclear) |
| Ocean energy | [/articles/ocean-energy](https://www.canarymedia.com/articles/ocean-energy) |
| Offshore wind | [/articles/offshore-wind](https://www.canarymedia.com/articles/offshore-wind) |
| Policy & regulation | [/articles/policy-regulation](https://www.canarymedia.com/articles/policy-regulation) |
| Politics | [/articles/politics](https://www.canarymedia.com/articles/politics) |
| Public transit | [/articles/public-transit](https://www.canarymedia.com/articles/public-transit) |
| Recycling renewables | [/articles/recycling-renewables](https://www.canarymedia.com/articles/recycling-renewables) |
| Transmission | [/articles/transmission](https://www.canarymedia.com/articles/transmission) |
| Utilities | [/articles/utilities](https://www.canarymedia.com/articles/utilities) |
| Virtual power plants | [/articles/virtual-power-plants](https://www.canarymedia.com/articles/virtual-power-plants) |
| Workforce diversity | [/articles/workforce-diversity](https://www.canarymedia.com/articles/workforce-diversity) |

### Lawfare

- provider id: `lawfare`
- bootstrap state: disabled by default
- default selected targets: `Cybersecurity & Tech`, `Surveillance & Privacy`
- catalog behavior: Static catalog covering all twelve Topics navigation entries. Listing extraction accepts written article titles and excludes podcast and multimedia entries.
- verification: Navigation was confirmed. Cybersecurity & Tech produced candidates and a representative article was parsed. Direct requests to the other eleven topic pages returned 403; their raw listing extraction remains unverified.
- first-party catalog reference: [publisher navigation or topic index](https://www.lawfaremedia.org/)

| Target | Destination |
| --- | --- |
| Cybersecurity & Tech | [/topics/cybersecurity-tech](https://www.lawfaremedia.org/topics/cybersecurity-tech) |
| Surveillance & Privacy | [/topics/surveillance-privacy](https://www.lawfaremedia.org/topics/surveillance-privacy) |
| Intelligence | [/topics/intelligence](https://www.lawfaremedia.org/topics/intelligence) |
| Foreign Relations & International Law | [/topics/foreign-relations-international-law](https://www.lawfaremedia.org/topics/foreign-relations-international-law) |
| Armed Conflict | [/topics/armed-conflict](https://www.lawfaremedia.org/topics/armed-conflict) |
| Congress | [/topics/congress](https://www.lawfaremedia.org/topics/congress) |
| Courts & Litigation | [/topics/courts-litigation](https://www.lawfaremedia.org/topics/courts-litigation) |
| Criminal Justice & Rule of Law | [/topics/criminal-justice-rule-of-law](https://www.lawfaremedia.org/topics/criminal-justice-rule-of-law) |
| Democracy & Elections | [/topics/democracy-elections](https://www.lawfaremedia.org/topics/democracy-elections) |
| Executive Branch | [/topics/executive-branch](https://www.lawfaremedia.org/topics/executive-branch) |
| States & Localities | [/topics/states-localities](https://www.lawfaremedia.org/topics/states-localities) |
| Terrorism & Extremism | [/topics/terrorism-extremism](https://www.lawfaremedia.org/topics/terrorism-extremism) |

### InfoQ

- provider id: `infoq`
- bootstrap state: disabled by default
- default selected targets: `Software Architecture`, `Cloud Architecture`
- catalog behavior: Static catalog covering the technical navigation topics and Cloud Architecture. Candidate extraction is restricted to each page’s News and Articles modules, excluding podcasts, presentations, and guides.
- verification: All destinations produced candidates; a representative article was parsed.
- first-party catalog reference: [publisher navigation or topic index](https://www.infoq.com/)

| Target | Destination |
| --- | --- |
| Software Architecture | [/architecture/](https://www.infoq.com/architecture/) |
| Cloud Architecture | [/cloud-architecture/](https://www.infoq.com/cloud-architecture/) |
| DevOps | [/devops/](https://www.infoq.com/devops/) |
| AI, ML & Data Engineering | [/ai-ml-data-eng/](https://www.infoq.com/ai-ml-data-eng/) |
| Java | [/java/](https://www.infoq.com/java/) |
| Development | [/development/](https://www.infoq.com/development/) |
| Kotlin | [/kotlin/](https://www.infoq.com/kotlin/) |
| .NET | [/dotnet/](https://www.infoq.com/dotnet/) |
| C# | [/c_sharp/](https://www.infoq.com/c_sharp/) |
| Swift | [/swift/](https://www.infoq.com/swift/) |
| Go | [/golang/](https://www.infoq.com/golang/) |
| Rust | [/rust/](https://www.infoq.com/rust/) |
| JavaScript | [/javascript/](https://www.infoq.com/javascript/) |
| Architecture & Design | [/architecture-design/](https://www.infoq.com/architecture-design/) |
| Enterprise Architecture | [/enterprise-architecture/](https://www.infoq.com/enterprise-architecture/) |
| Scalability/Performance | [/performance-scalability/](https://www.infoq.com/performance-scalability/) |
| Design | [/design/](https://www.infoq.com/design/) |
| Case Studies | [/Case_Study/](https://www.infoq.com/Case_Study/) |
| Microservices | [/microservices/](https://www.infoq.com/microservices/) |
| Service Mesh | [/servicemesh/](https://www.infoq.com/servicemesh/) |
| Patterns | [/DesignPattern/](https://www.infoq.com/DesignPattern/) |
| Security | [/Security/](https://www.infoq.com/Security/) |
| Big Data | [/bigdata/](https://www.infoq.com/bigdata/) |
| Machine Learning | [/machinelearning/](https://www.infoq.com/machinelearning/) |
| NoSQL | [/nosql/](https://www.infoq.com/nosql/) |
| Database | [/database/](https://www.infoq.com/database/) |
| Data Analytics | [/data-analytics/](https://www.infoq.com/data-analytics/) |
| Streaming | [/streaming/](https://www.infoq.com/streaming/) |
| Culture & Methods | [/culture-methods/](https://www.infoq.com/culture-methods/) |
| Agile | [/agile/](https://www.infoq.com/agile/) |
| Diversity | [/diversity/](https://www.infoq.com/diversity/) |
| Leadership | [/leadership/](https://www.infoq.com/leadership/) |
| Lean/Kanban | [/lean/](https://www.infoq.com/lean/) |
| Personal Growth | [/personal-growth/](https://www.infoq.com/personal-growth/) |
| Scrum | [/scrum/](https://www.infoq.com/scrum/) |
| Sociocracy | [/sociocracy/](https://www.infoq.com/sociocracy/) |
| Software Craftsmanship | [/software_craftsmanship/](https://www.infoq.com/software_craftsmanship/) |
| Team Collaboration | [/team-collaboration/](https://www.infoq.com/team-collaboration/) |
| Testing | [/testing/](https://www.infoq.com/testing/) |
| UX | [/ux/](https://www.infoq.com/ux/) |
| Infrastructure | [/infrastructure/](https://www.infoq.com/infrastructure/) |
| Continuous Delivery | [/continuous_delivery/](https://www.infoq.com/continuous_delivery/) |
| Automation | [/automation/](https://www.infoq.com/automation/) |
| Containers | [/containers/](https://www.infoq.com/containers/) |
| Cloud | [/cloud-computing/](https://www.infoq.com/cloud-computing/) |
| Observability | [/observability/](https://www.infoq.com/observability/) |

### Deloitte Insights

- provider id: `deloitteinsights`
- bootstrap state: disabled by default
- default selected targets: `Strategy`, `Technology`
- catalog behavior: Static catalog covering the editorial Topics menu. Candidate discovery uses the first-party search endpoint and each target’s search tag. Economics uses the research-center hub. Article parsing supports insights articles and readable research-center hubs.
- verification: All six destination pages were accessible. The public search endpoint returned 403, so current candidate discovery could not be verified live. Search-response and article parsing have fixture-backed coverage.
- first-party catalog reference: [publisher navigation or topic index](https://www.deloitte.com/us/en/insights.html)

| Target | Destination |
| --- | --- |
| Strategy | [/us/en/insights/topics/business-strategy-growth.html](https://www.deloitte.com/us/en/insights/topics/business-strategy-growth.html) |
| Technology | [/us/en/insights/topics/technology-management.html](https://www.deloitte.com/us/en/insights/topics/technology-management.html) |
| Workforce | [/us/en/insights/topics/talent.html](https://www.deloitte.com/us/en/insights/topics/talent.html) |
| Operations | [/us/en/insights/topics/operations.html](https://www.deloitte.com/us/en/insights/topics/operations.html) |
| Economics | [/us/en/insights/research-centers/economics.html](https://www.deloitte.com/us/en/insights/research-centers/economics.html) |
| Sustainability | [/us/en/insights/topics/sustainability.html](https://www.deloitte.com/us/en/insights/topics/sustainability.html) |

### Harvard Business Review

- provider id: `hbr`
- bootstrap state: disabled by default
- default selected targets: `Leadership`, `Strategy`
- catalog behavior: Static catalog covering the featured subjects on the Topics index. Candidate extraction reads Digital Article records from server-rendered Next.js result state and supports stream-item cards. Magazine articles, podcasts, store items, and external URLs are excluded. The exhaustive alphabetical subject, industry, and geography directories are outside this catalog.
- verification: All destinations produced digital-article candidates; a representative article was parsed.
- first-party catalog reference: [publisher navigation or topic index](https://hbr.org/topics)

| Target | Destination |
| --- | --- |
| Leadership | [/topic/subject/leadership](https://hbr.org/topic/subject/leadership) |
| Strategy | [/topic/subject/strategy](https://hbr.org/topic/subject/strategy) |
| Innovation | [/topic/subject/innovation](https://hbr.org/topic/subject/innovation) |
| Managing People | [/topic/subject/managing-people](https://hbr.org/topic/subject/managing-people) |
| Managing Yourself | [/topic/subject/managing-yourself](https://hbr.org/topic/subject/managing-yourself) |
| Gender | [/topic/subject/gender](https://hbr.org/topic/subject/gender) |
| Work-life Balance | [/topic/subject/work-life-balance](https://hbr.org/topic/subject/work-life-balance) |
| Technology and Analytics | [/topic/subject/technology-and-analytics](https://hbr.org/topic/subject/technology-and-analytics) |
| Organizational Culture | [/topic/subject/organizational-culture](https://hbr.org/topic/subject/organizational-culture) |
| Marketing | [/topic/subject/marketing](https://hbr.org/topic/subject/marketing) |
| Business Communication | [/topic/subject/business-communication](https://hbr.org/topic/subject/business-communication) |
| Economics | [/topic/subject/economics](https://hbr.org/topic/subject/economics) |
| Decision Making and Problem Solving | [/topic/subject/decision-making-and-problem-solving](https://hbr.org/topic/subject/decision-making-and-problem-solving) |
| Competitive Strategy | [/topic/subject/competitive-strategy](https://hbr.org/topic/subject/competitive-strategy) |
| Customer Experience | [/topic/subject/customer-experience](https://hbr.org/topic/subject/customer-experience) |
| International Business | [/topic/subject/international-business](https://hbr.org/topic/subject/international-business) |
| Career Planning | [/topic/subject/career-planning](https://hbr.org/topic/subject/career-planning) |

### ScienceDaily

- provider id: `sciencedaily`
- bootstrap state: disabled by default
- default selected targets: `Health & Medicine`, `Computers & Math`
- catalog behavior: Static catalog covering the primary science sections. Candidate extraction is scoped to the category-page headline modules, and article URLs are restricted to internal `/releases/*` pages. Deeper subtopic directories are outside this catalog.
- verification: All destinations produced candidates; a representative article was parsed.
- first-party catalog reference: [publisher navigation or topic index](https://www.sciencedaily.com/)

| Target | Destination |
| --- | --- |
| Health & Medicine | [/news/health_medicine/](https://www.sciencedaily.com/news/health_medicine/) |
| Computers & Math | [/news/computers_math/](https://www.sciencedaily.com/news/computers_math/) |
| Earth & Climate | [/news/earth_climate/](https://www.sciencedaily.com/news/earth_climate/) |
| Mind & Brain | [/news/mind_brain/](https://www.sciencedaily.com/news/mind_brain/) |
| Matter & Energy | [/news/matter_energy/](https://www.sciencedaily.com/news/matter_energy/) |
| Living Well | [/news/living_well/](https://www.sciencedaily.com/news/living_well/) |
| Space & Time | [/news/space_time/](https://www.sciencedaily.com/news/space_time/) |
| Plants & Animals | [/news/plants_animals/](https://www.sciencedaily.com/news/plants_animals/) |
| Fossils & Ruins | [/news/fossils_ruins/](https://www.sciencedaily.com/news/fossils_ruins/) |
| Science & Society | [/news/science_society/](https://www.sciencedaily.com/news/science_society/) |
| Business & Industry | [/news/business_industry/](https://www.sciencedaily.com/news/business_industry/) |
| Education & Learning | [/news/education_learning/](https://www.sciencedaily.com/news/education_learning/) |
| Top News | [/news/strange_offbeat/](https://www.sciencedaily.com/news/strange_offbeat/) |
