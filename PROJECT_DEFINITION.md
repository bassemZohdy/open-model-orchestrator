# Open Model Orchestrator

OMO is a self-contained Python agent with an embedded generative model and controlled computation inside one CPU Docker deployment. It aims to answer a narrow measured local envelope, use exact helpers where appropriate, and select an eligible configured external model for other requests.

V0.1 is a stateless modular monolith. Callers provide history. Required infrastructure is the container runtime only. It has no database, Kubernetes dependency, Docker socket, message broker, GPU, distributed execution, MCP, A2A, browser, management UI or multi-agent system.

Optional hash-based caller policies and local registry reload administration are bounded single-process features; they do not provide durable multi-instance accounting or deployment-level network enforcement.

Runtime responsibilities are inference, validation, policy, computation, bounded external I/O and content-free operational metadata. Dataset curation, evaluation, training and publishing remain offline engineering functions with separate credentials.

Initial engineering targets (not universal measurements): native four-core CPU, <=1.5 GiB container memory, <=1 GiB unpacked bundled image, <=5 s readiness, <=1 s warm local answer p95 on the development envelope, <=1.5 s bounded sandbox outer deadline. Exact local evidence is in docs/VALIDATION.md. Both architectures passed native offline container acceptance; measured image sizes and the limits of the performance evidence are in docs/VALIDATION.md.
