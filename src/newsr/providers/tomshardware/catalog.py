from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetOption:
    slug: str
    label: str
    path: str


BASE_TARGET_OPTIONS = [
    TargetOption("pc-components", "PC Components", "/pc-components/news"),
    TargetOption("cpus", "CPUs", "/pc-components/cpus/news"),
    TargetOption("gpus", "GPUs", "/pc-components/gpus/news"),
    TargetOption("storage", "Storage", "/pc-components/storage/news"),
    TargetOption("laptops", "Laptops", "/laptops/news"),
    TargetOption("desktops", "Desktops", "/desktops/news"),
    TargetOption("software", "Software", "/software/news"),
    TargetOption(
        "artificial-intelligence",
        "Artificial Intelligence",
        "/tech-industry/artificial-intelligence/news",
    ),
    TargetOption("latest", "Latest", "/news"),
    TargetOption("ram", "RAM", "/pc-components/ram/news"),
    TargetOption("cooling", "Cooling", "/pc-components/cooling/news"),
    TargetOption("motherboards", "Motherboards", "/pc-components/motherboards/news"),
    TargetOption("overclocking", "Overclocking", "/pc-components/overclocking/news"),
    TargetOption("pc-cases", "PC Cases", "/pc-components/pc-cases/news"),
    TargetOption("power-supplies", "Power Supplies", "/pc-components/power-supplies/news"),
    TargetOption("networking", "Networking", "/networking/news"),
    TargetOption("monitors", "Monitors", "/monitors/news"),
    TargetOption("peripherals", "Peripherals", "/peripherals/news"),
    TargetOption("3d-printing", "3D Printers", "/3d-printing/news"),
    TargetOption("tech-industry", "Tech Industry", "/tech-industry/news"),
    TargetOption("cyber-security", "Cybersecurity", "/tech-industry/cyber-security/news"),
    TargetOption("supercomputers", "Supercomputers", "/tech-industry/supercomputers/news"),
    TargetOption("quantum-computing", "Quantum Computing", "/tech-industry/quantum-computing/news"),
    TargetOption("operating-systems", "Operating Systems", "/software/operating-systems/news"),
    TargetOption("programming", "Programming", "/software/programming/news"),
    TargetOption("applications", "Applications", "/software/applications/news"),
    TargetOption("browsers", "Web Browsers", "/software/browsers/news"),
]
