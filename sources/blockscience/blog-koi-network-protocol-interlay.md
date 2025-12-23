# Digital Infrastructure Research & Development: KOI Network Protocol x Project Interlay

> Source: https://blog.block.science/koi-network-protocol-project-interlay/
> Published: March 25, 2025

Digital Infrastructure Research & Development: KOI Network Protocol x Project Interlay
March 25, 2025
Knowledge Organization Infrastructure Network Protocol (KOI-net) & Project Interlay
KOI-net represents an emerging paradigm in decentralized knowledge organization. By building from foundational communication standards to sophisticated governance frameworks, KOI-net aims to support self-organizing, interoperable knowledge systems. Project Interlay challenges conventional software development paradigms, advocating for a shift from rigid, app-based systems to more fluid, user-configurable environments.

This article represents an in-progress synthesis of a series of BlockScience research initiatives, reflecting our intention to 'work in public' and share internal discussions and findings with a wider community audience. In this video, BlockScience Research Engineer Luke Miller provides an overview of the KOI Network Protocol (KOI-net), highlighting the role of nodes in knowledge exchange, the flexibility of layering protocols, and the systems interoperability and adaptability based on different use cases and network needs. Senior Research Engineer Orion Reed also shares research and development of Project Interlay, demonstrating adaptive interfaces, spatial canvas tooling, the scoped propagators programming model, and their application to KOI-net.


Recorded February 2025, the video above is an internal engineering call that includes the following topics;

PART I: KOI Network Protocol
00:02:15 KOI-net Node Model
00:05:36 Network Architecture and Communication Patterns
00:09:11 Network Configuration
00:13:33 Endpoints
00:15:20 Question on Scalability
00:16:47 Full Nodes vs Partial Nodes
00:17:47 Question on Interface Layers
00:18:25 Proxy Nodes & Inter-Org Communication

PART II: KOI-net Looking Forward
00:19:12 Node Norms
00:21:31 Dynamic Schemas
00:23:42 Layers of Protocols
00:30:34 The Unsolved Problem

PART III: Project Interlay
00:34:01 Introducing Project Interlay
00:35:15 Adaptive Interfaces Demo
00:37:00 Computational Media Research
00:46:13 Folk Canvas Demo
00:46:47 Scoped Propagators Programming Model

Watch this Space! Open-source KOI-net protocol documentation is coming soon.
Part I: KOI Network Protocol
1. KOI-net Node Model
Illustration of he KOI Net node model is structured around four primary interaction modes between nodes
KOI-net protocol Core Developer and Research Engineer Luke Miller presents an overview of the KOI-net node model, which is structured around four primary interaction modes between nodes: one-way event streaming and two-way client-server communication.
Event streaming, represented by blue arrows, involves broadcasting events from node to node without expecting a response. In contrast, the client-server model, represented by red arrows, entails sending queries and receiving responses. These interactions are further categorized into input and output modalities, where input is knowledge moving into the node, and output is knowledge moving out of the node.

Additionally, communication can be viewed in terms of active versus passive participation. When a node actively sends out an event or a query, it initiates an event sequence, making it an active participant in the interaction. Conversely, passive participation occurs when a node listens to events or responds to incoming queries. Key to understanding the communication patterns across the network, this framework provides a structured way to understand how knowledge flows through the system, emphasizing whether a node is initiating or responding to an event sequence.

2. KOI Network Architecture & Communication Patterns
KOI World Boundary presents sensor array, coordinator, processors and actuators nodes
The proposed KOI-net architecture is highly flexible and designed to facilitate seamless knowledge flows within the network. It supports configurations ranging from fully decentralized peer-to-peer models to centralized broker-based pub-sub systems.
In the fully decentralized model, nodes independently decide who to connect with, while in a centralized model, a broker facilitates communication. A middle-ground option, the facilitator model, allows nodes to peer with others to assist in establishing connections, similar to a telephone operator. This flexible approach ensures adaptability based on different use cases and network needs.

In the example configuration, nodes are categorized based on their roles. A sensor array collects data from external platforms like Google Drive and converts it into KOI-net's standard communication format. This data is streamed to a broker, which then distributes it to subscribers, such as processing nodes that analyze and index knowledge. A processor might, for instance, handle text searches by retrieving knowledge from sensor nodes and responding to queries. Downstream, actuators such as user interfaces interact with processed knowledge, enabling users to query and retrieve information efficiently.

3. Network Configuration
The KOI network configuration leverages knowledge objects to dynamically define and adjust itself, eliminating rigid assumptions about structure.
Nodes and edges between them are treated as knowledge objects with unique identifiers (RIDs), allowing them to be queried, transmitted, and processed like any other knowledge. This enables the creation of specialized nodes that passively listen to network events and build an internal representation of the network. Such an approach could facilitate interactive visualizations or even allow the reconfiguration of nodes and their connections in real-time.

A key advantage of this design is its adaptability across different organizational structures. A node can maintain an internal "perspective" of the network state, which can then be selectively shared via an access-controlled processor or proxy node. This supports peer-to-peer or inter-organizational communication without enforcing a fixed architecture.

The fractal nature of KOI-net ensures that the same structural principles apply at both the node and network levels, enabling seamless interaction between networks with differing configurations—whether fully decentralized or centrally managed. By ensuring compatibility with the shared interfaces, even unconventional use cases, such as human-mediated responses via SMS, can integrate into KOI-net.

4. Endpoints
The KOI Net architecture defines a set of concrete endpoints to facilitate communication between nodes, translating its abstract model into practical interactions
The KOI-net architecture defines a set of concrete endpoints to facilitate communication between nodes, translating its abstract model into practical interactions.
Event streaming is handled through two primary methods: a webhook-like POST endpoint on the recipient and a polling endpoint allowing non-server nodes to retrieve events. On the output side, nodes can be queried for the RIDs (resource identifiers) they recognize, RID manifests, and knowledge object bundles, ensuring efficient propagation of events and internal state synchronization.

A crucial component for network formation is the handshake endpoint, which enables two nodes to exchange metadata about themselves, establishing mutual awareness before further interaction. In centralized configurations, nodes may handshake with a designated entry point, while in peer-to-peer models, they can connect with any available node to gradually discover the broader network. These endpoints provide a streamlined yet flexible foundation for KOI-net's decentralized knowledge-sharing ecosystem.

5. Full, Partial & Proxy Nodes
KOI-net supports both full and partial nodes, allowing flexibility for nodes that wish to participate without hosting a public or local API server.
Partial nodes can interact with the network through event polling instead of maintaining a persistent webhook connection, enabling lightweight integration. Their main use case is communication between two KOI-nets, allowing organizations to provide access to a controlled subset of the knowledge contained within their internal KOI-net.

Additionally, KOI-net can accommodate proxy nodes, which act as interfaces between external networks and the KOI-net ecosystem.
A proxy node represents a specific set of knowledge and exposes standardized endpoints that allow it to communicate within KOI-net, even if the underlying system is entirely bespoke. This approach enables organizations to maintain independent knowledge management systems while interfacing within the KOI-net ecosystem.

By abstracting internal architectures, proxy nodes facilitate seamless integration between disparate systems, allowing heterogeneous systems to interoperate without enforcing internal standardization. This approach supports inter-organizational collaboration, effectively bridging different infrastructures while preserving internal autonomy - reinforcing KOI-net's commitment to interoperability and decentralized knowledge exchange.

Part II: KOI-net Looking Forward
1. Node Norms
A key challenge in KOI-net's design is its agnosticism toward internal implementations, which allows for flexibility but also means that nodes can change behavior unpredictably while maintaining consistent interfaces.
To address this, nodes can optionally include self-descriptive metadata during handshakes, outlining expected behaviors, interaction norms, and the conditions for maintaining a connection.

This provides a way to establish mutual expectations without rigid enforcement mechanisms. This approach is particularly relevant in peer-to-peer or inter-organizational architectures, where there are no inherent guarantees of trust or reliability beyond interface compatibility.

By incorporating structured metadata—such as JSON-encoded normative agreements—nodes can negotiate social or operational contracts, reinforcing stable relationships. This becomes especially useful for proxy nodes representing entire organizations, ensuring that interactions align with agreed-upon standards for query handling, information sharing, and routing decisions.

2. Dynamic Schemas
KOI-net nodes effectively govern their participation in the network, deciding whom to connect with and when to sever links if necessary.

They are self-regulating entities responsible for managing connections, maintaining data integrity, and disengaging when interactions become unreliable. This autonomy extends to enforcing normative expectations for communication, ensuring that data flows align with agreed-upon behaviors.

A key concept in this framework is the internal monitoring mechanism, which functions like an "internal monologue." This system observes network activity, applies heuristics, and determines when to respond or share information.

The metadata associated with each node sets behavioral expectations and influences decision-making, guiding interactions based on predefined criteria. This approach allows for a dynamic and adaptable peer-to-peer architecture where relationships are formed and maintained through implicit trust mechanisms rather than rigid enforcement.

3. Layers of Protocols
KOI-net is designed as a layered protocol stack. Building upon foundational components like RIDs and expanding to include event-driven communication, security, and trust mechanisms, KOI-net's layered architecture is designed to facilitate communication between distributed systems, but it also introduces complexities—particularly in security, trust, and governance.
At the core of KOI-net's design philosophy is an iterative development process. Early implementations focus on small, controlled KOI-nets where trust is inherent. These initial networks serve as testing grounds for coordination mechanisms before expanding into more complex environments. A facilitator model is introduced as the system scales, where a helper node ensures seamless communication among partially trusted nodes.

As the network matures, it incorporates analytics to refine operations and enforces stricter access controls, allowing for broader but regulated interaction. The ultimate goal is to develop interfaces that support interoperability at a large scale, culminating in a restricted open API that enables participation from external entities while safeguarding the network's integrity.

Video Screenshot showing OSI B graphic a concept developed by Blocksscience Senior Researcher, David Sission
The vision behind KOI-net extends beyond traditional assumptions about digital infrastructure. A key insight from the discussion is the "OSI B" concept—a theoretical extension of the classic Open Systems Interconnection model tailored for modern decentralized networks. Unlike conventional frameworks that rely on predefined computational models such as Ethereum Virtual Machines (EVMs), KOI-net takes a more agnostic approach. By avoiding rigid specifications on processing layers, the architecture remains adaptable, ensuring it can evolve alongside emerging technologies rather than being constrained by them.

📚
Sisson, D., & Ben-Meir, I. (2023). From Networks of Computers to Network Computers—and Beyond. Retrieved February 25, 2025, from https://blog.block.science/from-networks-of-computers-to-network-computers-and-beyond/
Another essential component of KOI-net is its approach to provenance and trust. Maintaining reliable attribution is crucial as knowledge flows across different nodes and organizations. This is where Content-Addressable Transformers (CATs), a provenance protocol, plays a role. Inspired by systems like warehouse receipts and shipping manifests, CATs provide a mechanism for tracking the origin and flow of information, ensuring that knowledge remains verifiable even across multiple network hops. Provenance-aware protocols like this will become increasingly important as KOI-net scales into a system that supports complex, self-organizing networks.

4. Designing Adaptive Systems
Orion Reed: we really haven't figured out how to specify the behavior of systems... we have lots of methods and type systems and so on to, to say exactly the shape of some data, but specifying the internal behavior of something or how that even appears from the outside is at the very least an unsolved problem and quite likely to be unsolvable because of the limits of computable languages....
Michael Zargham: That's the difference between a computer science problem and an engineering problem. An engineering problem presupposes the imperfect ability to assert the behavior of the system that you're making, but allows you to make contextually appropriate kind of axiomatic assumptions and then to render a system that has situationally appropriate stable behavior, not like infinitely guaranteed stable behavior.
A fully deterministic specification of the internal behavior of complex systems is often impossible. This limitation stems from technical constraints and deeper mathematical and computational limits. Instead of attempting to fully define behavior, a more practical approach is to develop engineering methodologies that ensure situational stability while preserving adaptability.
KOI-net embraces this philosophy by differentiating between peer-to-peer interactions and structured oversight mechanisms. At its core, KOI-net operates on a "FUN plane," where decentralized agents interact freely. However, to maintain system integrity, it also incorporates a "CRUD plane" - a structured layer where oversight can be exercised to create, read, update, and delete, when necessary. This distinction ensures responsible entities can intervene, adjust, and maintain stability against expected behaviors while the system remains decentralized and flexible.

Luke Miller: FUN is our own internal concept from the KOI-net protocol, it stands for forget, update, new. We compare it with CRUD since it also relates to data, but instead of being an operation that's carried out, it's an event that a node emits to indicate its internal state change. For example, if a piece of knowledge is new to that node, an update to an existing piece of knowledge it knows about, or that knowledge is forgotten (deleted). It's a signaling primitive allowing nodes to make decisions about events other nodes emit, rather than a command/operation like CRUD.
A useful analogy for this approach is the concept of a manifold in mathematics. Manifolds are structures that appear simple and well-defined at a local level but can exhibit extreme complexity when viewed globally. Similarly, KOI Net's architecture ensures that each network remains coherent and navigable at a local level. However, as these local structures interconnect, they give rise to emergent global properties that are not explicitly predefined. This ability to scale from local simplicity to global complexity allows KOI-net to support highly diverse and evolving systems without imposing rigid top-down constraints.

The key to this adaptability is defining minimal, locally enforceable protocols and connectivity rules. Rather than attempting to dictate a universal structure, KOI-net ensures that small, contextually appropriate rules guide interactions at the local level. When stitched together, these interactions create an organic, evolving network capable of reflecting the complexity of the real world.
This design philosophy enables maximum variety while preserving coherence, allowing individual actors to make decisions that influence the system's evolution over time. By ensuring that each part of the network remains well-defined and navigable while allowing for unrestricted complexity at scale, KOI-net presents a model for building resilient, adaptive, decentralized systems that can evolve alongside the needs of their users.

Part III: Project Interlay
Challenging conventional software development paradigms and advocating for a shift from rigid, app-based systems to more fluid, user-configurable environments, Senior Research Engineer Orion Reed demonstrates tools under development for adapting existing interfaces and research encompassing computational media, scoped propagators, and spatial canvases.
1. Adaptive Interface Demo

South Park Commons Adaptive Interface Demo 2024 by Orion Reed

Orion Reed: you take an existing system that you can't change, and look at the ways that you actually kind of can make changes...
2. Computational Media
Project Interlay builds on research in computational media, aiming to fundamentally rethink how software is constructed.
Rather than focusing on creating better applications, computational media explores changing the materials from which software is built. This approach challenges the traditional model, where tightly coupled systems make it difficult to modify, adapt, or reappropriate software components.

Inspired by Stephen Kell's work on integration domains, Interlay introduces a new framework that separates the process of building software components from the process of integrating them—much like how circuit design separates the construction of individual components from the design of a printed circuit board (PCB).

Video screenshot showing graph of economic constraints of the current application model
A key motivation for this shift is the economic constraints of the current application model. Traditional software development prioritizes the most common user needs, leaving many niche or individualized requirements unmet.

Computational media proposes a shift towards designing for emergence—providing more adaptable materials that enable users to modify and extend their digital environments according to their needs.
This requires rethinking application topology, moving away from isolated, monolithic apps toward a more flexible model where interfaces and underlying software layers are decoupled. By providing better building materials rather than just better tools, computational media opens possibilities for more personalized and emergent forms of software design.

3. Spatial Canvases

Interlay's approach draws from spatial canvas systems, where users can visually organize and connect different software components.

By making relationships between data sources explicit—such as linking a map with a database query—users gain greater control over interactions without the risk of conflicting behaviors. This contrasts with traditional interface design, which assumes centralized coordination among developers to prevent conflicts. Project Interlay instead envisions an open-ended system where multiple contributors can shape software collaboratively without interfering with each other's work.

The project's origins trace back to knowledge organization infrastructure (KOI) research, particularly designing better interfaces for querying and interacting with graph-structured data. Unlike conventional UI frameworks optimized for predefined schemas—such as an e-commerce product page with fixed attributes—Interlay seeks to create interfaces that dynamically adapt to data whose structure may be unknown. This adaptability is crucial for working with complex, evolving datasets that do not fit neatly into rigid interface models.

Z: While we have [with KOI Net] a bunch of lower level protocols that make it possible to build stuff and arrange it in a more distributed, even decentralized way, we don't necessarily have interfaces or common development modalities that compliment that. And so what you're [Orion] presenting here is basically both the thesis for and you're developing tools for building [interfaces or common development modalities].
4. Folk Canvas Demo
Video Screenshot showing discussion of Folk Canvas trying to strip things down to the basic building blocks
Folk Canvas is trying to strip things down to the basic building blocks of the spatial canvas approach to building interfaces. In this demo, Orion Reed shows the ability to treat a plain HTML document as if it were a spatial canvas.

5. Scoped Propagators Programming Model
Scoped Propagators is a simple event-driven programming model that lets you take existing UI elements and wire them up without requiring any hooks or affordances.

Orion Reed on Scoped Propagators at Splash Pasadena 2024 LIVE

📚
Orion Reed. (n.d.). Retrieved February 25, 2025, from https://www.orionreed.com/posts/scoped-propagators
Abstract: Graphs, as a model of computation and as a means of interaction and authorship, have found success in specific domains such as shader programming and signal processing. In these systems, computation is often expressed on nodes of specific types, with edges representing the flow of information. This is a powerful and general-purpose model, but is typically a closed-world environment where both node and edge types are decided at design-time. By choosing an alternate topology where computation is represented by edges, the incentive for a closed environment is reduced.

I present Scoped Propagators (SPs), a programming model designed to be embedded within existing environments and user interfaces. By representing computation as mappings between nodes along edges, SPs make it possible to add behaviour and interactivity to environments which were not designed with liveness in mind. I demonstrate an implementation of the SP model in an infinite canvas environment, where users can create arrows between arbitrary shapes and define SPs as Javascript object literals on these arrows
About BlockScience
Thanks for your interest in our research!  If you or your team are interested in experimenting with KOI tooling, please get in touch at media@block.science
BlockScience® is a complex systems engineering, R&D, and analytics firm. By integrating ethnography, applied mathematics, and computational science, we analyze and design safe and resilient socio-technical systems. With deep expertise in Market Design, Distributed Systems, and AI, we provide engineering, design, and analytics services to a wide range of clients, including for-profit, non-profit, academic, and government organizations.