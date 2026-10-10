from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetOption:
    slug: str
    label: str
    path: str


BASE_TARGET_OPTIONS = [
    TargetOption("grid-edge", "Grid Edge", "/articles/grid-edge"),
    TargetOption("energy-storage", "Energy Storage", "/articles/energy-storage"),
    TargetOption("solar", "Solar", "/articles/solar"),
    TargetOption("electrification", "Electrification", "/articles/electrification"),
    TargetOption("transportation", "Transportation", "/articles/transportation"),
    TargetOption("wind", "Wind", "/articles/wind"),
    TargetOption("batteries", "Batteries", "/articles/batteries"),
    TargetOption("affordability", "Affordability", "/articles/affordability"),
    TargetOption("air-travel", "Air travel", "/articles/air-travel"),
    TargetOption("balcony-solar", "Balcony solar", "/articles/balcony-solar"),
    TargetOption("canary-media", "Canary Media", "/articles/canary-media"),
    TargetOption("carbon-capture", "Carbon capture", "/articles/carbon-capture"),
    TargetOption("carbon-removal", "Carbon removal", "/articles/carbon-removal"),
    TargetOption("carbon-free-buildings", "Carbon-free buildings", "/articles/carbon-free-buildings"),
    TargetOption("clean-aluminum", "Clean aluminum", "/articles/clean-aluminum"),
    TargetOption("clean-energy", "Clean energy", "/articles/clean-energy"),
    TargetOption("clean-energy-jobs", "Clean energy jobs", "/articles/clean-energy-jobs"),
    TargetOption(
        "clean-energy-manufacturing",
        "Clean energy manufacturing",
        "/articles/clean-energy-manufacturing",
    ),
    TargetOption(
        "clean-energy-supply-chain",
        "Clean energy supply chain",
        "/articles/clean-energy-supply-chain",
    ),
    TargetOption("clean-fleets", "Clean fleets", "/articles/clean-fleets"),
    TargetOption("clean-industry", "Clean industry", "/articles/clean-industry"),
    TargetOption("climate-crisis", "Climate crisis", "/articles/climate-crisis"),
    TargetOption("climate-justice", "Climate justice", "/articles/climate-justice"),
    TargetOption("climatetech-finance", "Climatetech finance", "/articles/climatetech-finance"),
    TargetOption("corporate-procurement", "Corporate procurement", "/articles/corporate-procurement"),
    TargetOption("culture", "Culture", "/articles/culture"),
    TargetOption("data-centers", "Data centers", "/articles/data-centers"),
    TargetOption(
        "distributed-energy-resources",
        "Distributed energy resources",
        "/articles/distributed-energy-resources",
    ),
    TargetOption("electric-vehicles", "Electric vehicles", "/articles/electric-vehicles"),
    TargetOption("emissions-reduction", "Emissions reduction", "/articles/emissions-reduction"),
    TargetOption("energy-efficiency", "Energy efficiency", "/articles/energy-efficiency"),
    TargetOption("energy-equity", "Energy equity", "/articles/energy-equity"),
    TargetOption("energy-markets", "Energy markets", "/articles/energy-markets"),
    TargetOption("enn", "ENN", "/articles/enn"),
    TargetOption("ev-charging", "EV charging", "/articles/ev-charging"),
    TargetOption("food-and-farms", "Food and farms", "/articles/food-and-farms"),
    TargetOption("fossil-fuels", "Fossil fuels", "/articles/fossil-fuels"),
    TargetOption("fun-stuff", "Fun stuff", "/articles/fun-stuff"),
    TargetOption("geothermal", "Geothermal", "/articles/geothermal"),
    TargetOption("green-steel", "Green steel", "/articles/green-steel"),
    TargetOption("guides-and-how-tos", "Guides and how-tos", "/articles/guides-and-how-tos"),
    TargetOption("heat-pumps", "Heat pumps", "/articles/heat-pumps"),
    TargetOption("hydrogen", "Hydrogen", "/articles/hydrogen"),
    TargetOption("hydropower", "Hydropower", "/articles/hydropower"),
    TargetOption("just-transition", "Just transition", "/articles/just-transition"),
    TargetOption("land-use", "Land use", "/articles/land-use"),
    TargetOption("liquefied-natural-gas", "Liquefied natural gas", "/articles/liquefied-natural-gas"),
    TargetOption(
        "long-duration-energy-storage",
        "Long-duration energy storage",
        "/articles/long-duration-energy-storage",
    ),
    TargetOption("sea-transport", "Marine transport", "/articles/sea-transport"),
    TargetOption("methane", "Methane", "/articles/methane"),
    TargetOption("nuclear", "Nuclear", "/articles/nuclear"),
    TargetOption("ocean-energy", "Ocean energy", "/articles/ocean-energy"),
    TargetOption("offshore-wind", "Offshore wind", "/articles/offshore-wind"),
    TargetOption("policy-regulation", "Policy & regulation", "/articles/policy-regulation"),
    TargetOption("politics", "Politics", "/articles/politics"),
    TargetOption("public-transit", "Public transit", "/articles/public-transit"),
    TargetOption("recycling-renewables", "Recycling renewables", "/articles/recycling-renewables"),
    TargetOption("transmission", "Transmission", "/articles/transmission"),
    TargetOption("utilities", "Utilities", "/articles/utilities"),
    TargetOption("virtual-power-plants", "Virtual power plants", "/articles/virtual-power-plants"),
    TargetOption("workforce-diversity", "Workforce diversity", "/articles/workforce-diversity"),
]
