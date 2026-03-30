# Current Providers

This page is the canonical reference for NewsR's currently implemented built-in news providers. When the built-in provider set or its documented bootstrap defaults change, update this page and have other docs link here for the concrete list.

The current built-in news providers are defined in `src/newsr/providers/registry.py`.

## Built-in Providers

### BBC News

- provider id: `bbc`
- bootstrap state: enabled by default
- default selected targets: `World`, `Technology`, `Business`, `Entertainment And Arts`
- catalog behavior: live discovery that merges discovered categories with the built-in base catalog

### TechCrunch

- provider id: `techcrunch`
- bootstrap state: disabled by default
- default selected targets: `Latest`, `Startups`, `Venture`, `AI`, `Security`
- catalog behavior: static built-in topic catalog

### The Hacker News

- provider id: `thehackernews`
- bootstrap state: disabled by default
- default selected targets: `Threat Intelligence`, `Cyber Attacks`, `Vulnerabilities`, `Expert Insights`
- catalog behavior: static built-in section catalog

### Ars Technica

- provider id: `arstechnica`
- bootstrap state: disabled by default
- default selected targets: `Latest`, `Gadgets`, `Science`, `Security`
- catalog behavior: static built-in mixed catalog with a catch-all `Latest` feed plus section targets

### HR Dive

- provider id: `hrdive`
- bootstrap state: disabled by default
- default selected targets: `Talent`, `Comp & Benefits`
- catalog behavior: static built-in topic catalog

### MedCity News

- provider id: `medcitynews`
- bootstrap state: disabled by default
- default selected targets: `Health Tech`, `Devices & Diagnostics`
- catalog behavior: static built-in live-channel catalog

### Hyperallergic

- provider id: `hyperallergic`
- bootstrap state: disabled by default
- default selected targets: `News`, `Reviews`
- catalog behavior: static built-in tag-backed category catalog

### EdSurge

- provider id: `edsurge`
- bootstrap state: disabled by default
- default selected targets: `K-12`, `Higher Ed`
- catalog behavior: static built-in mixed audience/topic catalog using live `news/k-12`, `news/higher-ed`, and `news/topics/artificial-intelligence`

### Marketing Dive

- provider id: `marketingdive`
- bootstrap state: disabled by default
- default selected targets: `Brand Strategy`, `Social Media`
- catalog behavior: static built-in topic/latest catalog with `Marketing` mapped to the site root and topic-backed targets for `Brand Strategy`, `Mobile`, `Creative`, `Social Media`, `Video`, `Agencies`, `Data/Analytics`, `Influencer`, `Ad Tech`, and `CMO Corner`

### Tom's Hardware

- provider id: `tomshardware`
- bootstrap state: disabled by default
- default selected targets: `PC Components`, `CPUs`, `GPUs`
- catalog behavior: static built-in hardware/software section catalog with `PC Components`, `CPUs`, `GPUs`, `Storage`, `Laptops`, `Desktops`, `Software`, and `Artificial Intelligence`

### Canary Media

- provider id: `canarymedia`
- bootstrap state: disabled by default
- default selected targets: `Grid Edge`, `Solar`
- catalog behavior: static built-in climate-tech topic catalog using live `/articles/<topic>` vertical pages for `Grid Edge`, `Energy Storage`, `Solar`, `Electrification`, and `Transportation`

### Lawfare

- provider id: `lawfare`
- bootstrap state: disabled by default
- default selected targets: `Cybersecurity & Tech`, `Surveillance & Privacy`
- catalog behavior: static built-in topic catalog using live `/topics/*` targets for `Cybersecurity & Tech`, `Surveillance & Privacy`, `Intelligence`, and `Foreign Relations & International Law`, with listing extraction restricted to written article titles so podcast and multimedia entries are excluded

### InfoQ

- provider id: `infoq`
- bootstrap state: disabled by default
- default selected targets: `Software Architecture`, `Cloud Architecture`
- catalog behavior: static built-in topic catalog using live InfoQ topic pages `/architecture/`, `/cloud-architecture/`, `/devops/`, `/ai-ml-data-eng/`, and `/java/`, with candidate extraction restricted to each topic page's `News` and `Articles` sections so podcasts, presentations, and guides are excluded

### Deloitte Insights

- provider id: `deloitteinsights`
- bootstrap state: disabled by default
- default selected targets: `Strategy`, `Technology`
- catalog behavior: static built-in topic catalog using live Deloitte topic slugs `business-strategy-growth`, `technology-management`, `talent`, `operations`, and `economy`, with candidate discovery backed by Deloitte's first-party search endpoint and article parsing that accepts standard insights articles plus readable research-center hub pages

### Harvard Business Review

- provider id: `hbr`
- bootstrap state: disabled by default
- default selected targets: `Leadership`, `Strategy`
- catalog behavior: static built-in subject catalog using live `topic/subject/*` targets for `Leadership`, `Strategy`, `Innovation`, `Managing People`, and `Managing Yourself`, with listing results restricted to HBR digital-article cards

### ScienceDaily

- provider id: `sciencedaily`
- bootstrap state: disabled by default
- default selected targets: `Health & Medicine`, `Computers & Math`
- catalog behavior: static built-in live category catalog using exact ScienceDaily `news/*` paths for `Health & Medicine`, `Computers & Math`, `Earth & Climate`, `Mind & Brain`, and `Matter & Energy`, with candidate extraction scoped to the category-page headline modules and article parsing restricted to internal `releases/*` pages
