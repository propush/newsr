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
    TargetOption("routers", "Routers", "/networking/routers/news"),
    TargetOption("pc-building", "PC Building", "/desktops/pc-building/news"),
    TargetOption("gaming-laptops", "Gaming Laptops", "/laptops/gaming-laptops/news"),
    TargetOption("ultrabooks", "Ultrabooks", "/laptops/ultrabooks-ultraportables/news"),
    TargetOption("gaming-pcs", "Gaming PCs", "/desktops/gaming-pcs/news"),
    TargetOption("gaming-monitors", "Gaming Monitors", "/monitors/gaming-monitors/news"),
    TargetOption("keyboards", "Keyboards", "/peripherals/keyboards/news"),
    TargetOption("mice", "Mice", "/peripherals/mice/news"),
    TargetOption("headphones", "Headphones", "/peripherals/headphones-headsets/news"),
    TargetOption(
        "semiconductors",
        "Semiconductors",
        "/tech-industry/manufacturing/semiconductors/news",
    ),
    TargetOption("gpu-drivers", "GPU Drivers", "/pc-components/gpus/gpu-drivers/news"),
    TargetOption("dram", "DRAM", "/pc-components/ram/dram/news"),
    TargetOption("ddr5", "DDR5", "/pc-components/ram/dram/ddr5/news"),
    TargetOption("hdds", "HDDs", "/pc-components/storage/hdds/news"),
    TargetOption("ssds", "SSDs", "/pc-components/storage/ssds/news"),
    TargetOption("air-cooling", "Air Cooling", "/pc-components/cooling/air-cooling/news"),
    TargetOption("liquid-cooling", "Liquid Cooling", "/pc-components/cooling/liquid-cooling/news"),
    TargetOption("thermal-paste", "Thermal Paste", "/pc-components/cooling/thermal-paste/news"),
    TargetOption("windows", "Windows", "/software/operating-systems/windows/news"),
    TargetOption("macos", "macOS", "/software/operating-systems/macos/news"),
    TargetOption("ios", "iOS", "/software/operating-systems/ios/news"),
    TargetOption("chromeos", "ChromeOS", "/software/operating-systems/chromeos/news"),
    TargetOption("linux", "Linux", "/software/operating-systems/linux/news"),
    TargetOption(
        "microsoft-office",
        "Microsoft Office",
        "/software/applications/microsoft-office/news",
    ),
]
