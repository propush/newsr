from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetOption:
    slug: str
    label: str
    path: str


BASE_TARGET_OPTIONS = (
    TargetOption("software-architecture", "Software Architecture", "/architecture/"),
    TargetOption("cloud-architecture", "Cloud Architecture", "/cloud-architecture/"),
    TargetOption("devops", "DevOps", "/devops/"),
    TargetOption("ai-ml-data-engineering", "AI, ML & Data Engineering", "/ai-ml-data-eng/"),
    TargetOption("java", "Java", "/java/"),
    TargetOption("development", "Development", "/development/"),
    TargetOption("kotlin", "Kotlin", "/kotlin/"),
    TargetOption("dotnet", ".NET", "/dotnet/"),
    TargetOption("c-sharp", "C#", "/c_sharp/"),
    TargetOption("swift", "Swift", "/swift/"),
    TargetOption("golang", "Go", "/golang/"),
    TargetOption("rust", "Rust", "/rust/"),
    TargetOption("javascript", "JavaScript", "/javascript/"),
    TargetOption("architecture-design", "Architecture & Design", "/architecture-design/"),
    TargetOption("enterprise-architecture", "Enterprise Architecture", "/enterprise-architecture/"),
    TargetOption("performance-scalability", "Scalability/Performance", "/performance-scalability/"),
    TargetOption("design", "Design", "/design/"),
    TargetOption("case-study", "Case Studies", "/Case_Study/"),
    TargetOption("microservices", "Microservices", "/microservices/"),
    TargetOption("servicemesh", "Service Mesh", "/servicemesh/"),
    TargetOption("designpattern", "Patterns", "/DesignPattern/"),
    TargetOption("security", "Security", "/Security/"),
    TargetOption("bigdata", "Big Data", "/bigdata/"),
    TargetOption("machinelearning", "Machine Learning", "/machinelearning/"),
    TargetOption("nosql", "NoSQL", "/nosql/"),
    TargetOption("database", "Database", "/database/"),
    TargetOption("data-analytics", "Data Analytics", "/data-analytics/"),
    TargetOption("streaming", "Streaming", "/streaming/"),
    TargetOption("culture-methods", "Culture & Methods", "/culture-methods/"),
    TargetOption("agile", "Agile", "/agile/"),
    TargetOption("diversity", "Diversity", "/diversity/"),
    TargetOption("leadership", "Leadership", "/leadership/"),
    TargetOption("lean", "Lean/Kanban", "/lean/"),
    TargetOption("personal-growth", "Personal Growth", "/personal-growth/"),
    TargetOption("scrum", "Scrum", "/scrum/"),
    TargetOption("sociocracy", "Sociocracy", "/sociocracy/"),
    TargetOption("software-craftsmanship", "Software Craftsmanship", "/software_craftsmanship/"),
    TargetOption("team-collaboration", "Team Collaboration", "/team-collaboration/"),
    TargetOption("testing", "Testing", "/testing/"),
    TargetOption("ux", "UX", "/ux/"),
    TargetOption("infrastructure", "Infrastructure", "/infrastructure/"),
    TargetOption("continuous-delivery", "Continuous Delivery", "/continuous_delivery/"),
    TargetOption("automation", "Automation", "/automation/"),
    TargetOption("containers", "Containers", "/containers/"),
    TargetOption("cloud-computing", "Cloud", "/cloud-computing/"),
    TargetOption("observability", "Observability", "/observability/"),
)
