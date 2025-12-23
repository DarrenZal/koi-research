# KOI Nodes as Neurons

> Source: https://blog.block.science/koi-nodes-as-neurons/
> Author: David Sisson, Ph.D.
> Published: June 18, 2025

KOI Nodes as Neurons
June 18, 2025
Using computational neuroscience to describe Knowledge Organization Infrastructure (KOI)
In this video, "KOI: What is it Good for?" Senior Research Engineer David Sisson presents the analogy of KOI nodes as neurons, seeding a discussion that both informs and challenges the boundaries between digital and human sensation, perception, cognition, and metacognition.
Drawing from a Ph.D. in Neurophysiology, extensive academic and applied research experience and a focus on using computational neuroscience to bridge micro (molecular and cellular) and macro (behavioral) - this article represents an in-progress synthesis of a series of BlockScience research initiatives, reflecting our intention to 'work in public' and share internal discussions and findings with a wider community audience.


This video post was produced with the assistance of AI, as part of a broader inquiry into the roles that such systems can play in synthesis and sense-making when they are wielded as tools, rather than as oracles. Based on an internal team meeting, this post shares the presentation video, adapted transcript, selected slides, and additional references. The original transcript was generated using AI and reviewed by humans-in-the-loop. Topics include:

Overview of KOI
[00:01:05] KOI Nodes
[00:02:25] Process Overview
[00:03:32] Networks of KOI nodes
Knowledge Processing Systems
[00:04:17] Knowledge Processing Systems
[00:05:19] KOI Node Block Diagram
KOI Nodes as Neurons
[00:06:10] Neuron Analogy
[00:06:48] Network Reflex
Sensation, Perception, Cognition & Metacognition
[00:07:45] Sensor Fusion
[00:09:01] Perception in a Digital System
[00:10:01] Further Developing a KOI Network
[00:11:30] On Cognition & Metacognition
Discussion Q & A
[00:15:20] Q: How to Identify Reflexes in an Evolved System
[00:15:56] A: Effectively, Nothing Between the Sensor & Actuator
[00:17:07] Q: Conceived vs. Observed
[00:18:21] A: Slippery Definitions & Explicitly Leaky
[00:19:30] Q: On Designations of Nodes
[00:20:55] A: Sensemaking
[00:21:31] Q: Differentiating Between Different Functions.
[00:22:33] A: Domain General Architecture
Topology of Expert Systems

Overview of KOI
[00:00:00] David: In 1970, Edmond Starr asked, "War, what is it good for?" and over the next three minutes, he developed his answer, "absolutely nothing!". Today, I will ask a parallel question, "KOI, what is it good for?" and over the next 20 minutes or so, I hope to develop the opposite answer. I will share diagrams that KOI-net lead protocol developer Luke Miller put together, and present an adaptation of these models.

⚙️
KOI (Knowledge Organization Infrastructure) is a collective research effort across BlockScience, Metagov, and Royal Melbourne Institute of Technology (RMIT). This repository serves as a starting point for finding resources and information related to the project. https://github.com/BlockScience/koi
KOI-net Nodes Models
Tech Research Pod Presentation Slide_ KOI Nodes KOI World Boundary_What is Knowledge Organization Infrastucture _David Sission
KOI Node & KOI World Boundary Diagrams by KOI-net Protocol Lead Developer Luke Miller
[00:01:05] We have a KOI node, which is defined within the KOI-net protocol, which specifies that a KOI node has this kind of shape - a block with ports and terminals. Within the block, there are some generically defined processes. There is the ability to compute and a cache to keep track of what you have been computing. Then, a communication protocol allows KOI nodes to talk to one another. There is an event-driven push protocol. You can subscribe to essentially a pub-sub. You can subscribe to other nodes and listen to events that they generate. And you can broadcast your events - forget, update, and new. And what they are in regard to our reference IDs (RID), so references to some object. And since this is knowledge organization infrastructure, the objects that we are talking about are knowledge objects.

⚙️
The KOI-net protocol defines the standard communication patterns and coordination norms needed to establish and maintain Knowledge Organization Infrastructure (KOI) networks.
https://github.com/BlockScience/koi-net
Process Overview
[00:02:25] So we have these references to knowledge objects. We can listen to other KOI nodes sending events about what they have newly learned, what they have changed about what they have learned or how their learnings have affected what they know - change, updates, and a special case of updates is forget (we no longer care about this thing, and we are not gonna talk about it anymore.) So listen, plus computation with caching of what you know, and then broadcast changes. Then, in red below, if you do not want to do event-driven programming, there is a way to poll. You can request information about events from another node, respond to other nodes regarding requests, and send them what they want.

Networks of KOI Nodes
[00:03:32] Using KOI node, you can create networks of KOI nodes where we can use some nodes to sense from outside some boundary. You can have, maybe, a coordinator that helps all the nodes within these boundaries get along. You can have specific processors to make sense of, for instance, anything that these sensory nodes have brought in. And then you have activators that can inject what it has learned into the space outside of this network.

Knowledge Processing Systems
Tech Research Pod Presentation Slide_ Knowledge Processing Systems_What is Knowledge Organization Infrastucture _David Sission
[00:04:17] The context I am going to talk about - knowledge processing systems - sits here (yellow box) in the middle of a digital, distributed, decision-making system. Here, we have sensors in the environment that directly process sensory information (removing noise) and combine things into more abstract, more general knowledge objects.

Based on that general sense of what is going on in the world, you can then apply some context that you want to make a decision in, and then come to some understanding as to what that decision should be. And based on that decision, act, which will affect the environment, which sensors should pick up, and you have a nice little control loop.

Abstract: In order for data to become truly valuable (and truly useful), that data must first be processed. The question animating this essay is thus a straightforward one: What sort of processing must data undergo, in order to become valuable? While the question may be obvious, its answers are anything but; indeed, reaching them will require us to pose, answer – and then revise our answers to – several other questions that will prove trickier than they first appear: Why is data valuable – what is it for? What is "data"? And what does "working with data" actually involve?
📚
Sisson, David and Ben-Meir, Ilan, Why Is There Data? (August 21, 2024). Available at SSRN: https://ssrn.com/abstract=4933063 or http://dx.doi.org/10.2139/ssrn.4933063
Observing an Observed Space: KOI Node Block Diagram
Tech Research Pod Presentation Slide_ KOI Node Block Diagram 1, the language of BlockScience_What is Knowledge Organization Infrastucture _David Sission
KOI Node Block Diagram 1. "Observing an Observed Space"
[00:05:19] This is my KOI node block diagram, because most everything we do at BlockScience can be expressed as a block diagram. The KOI node is responsible for observing (observed space). Points from this observed space come into the node, and based on 1) what the node knows and 2) computational ability, it can crunch observed sensations (input), and then produce some conceptual idea (output) of what is going on out here (conceived space). So that is the simplest thing we do: observe an observed space. Given this diagram, there is not much going on...

An Analogy: KOI Nodes as Neurons
Tech Research Pod Presentation Slide_ Multipolar Neuron Image by Bruce Blaus_What is Knowledge Organization Infrastucture _David Sission.pptx
Multipolar Neuron Image by Bruce Blaus, Own Work. CC by 3.0 Source
[00:06:10] So here at BlockScience, we asked, "Is there anything else in the world like a KOI node?", and maybe I am biased because of my [neurophysiology] background. Yet, it seems that KOI nodes are doing about the same thing neurons do in sensing what is going on. Both KOI nodes and neurons sense what is going on in their environment, they aggregate and try to make sense of it, then send a message out to other systems for further processing.

Network Reflex
Tech Research Pod Presentation Slide_ KOI Node Network Reflex Block Diagram 2_What is Knowledge Organization Infrastucture _David Sission
KOI Node Block Diagram 2. "Network Reflex"
[00:06:48] So the simplest thing we could do is very similar to the simplest thing you can do with neurons - you can create a reflex. So here we have a sensor observing the observed space, processing it, sending what it has come up with to some actuator, which then affects this conceived space.

And this is exactly what happens in, say, the patella tendon reflex. This sensor here would be the spindle fibers in your patellar tendon. You hit your knee with a hammer. That fact is sent up to your spinal cord, where it is passed on to motor neurons, which then cause muscles to contract, and your leg to kick. This is a standard reflex. Fun, but not particularly useful unless you are a doctor.

Sensation, Perception, Cognition & Metacognition
Sensor Fusion
Tech Research Pod Presentation Slide_ KOI Node Network Reflex with Sensor Fusion Block Diagram 3_What is Knowledge Organization Infrastucture _David Sission
KOI Node Block Diagram 3. "Model of Sensation in a Digital System"
[00:07:45] But we can do more. This is a modular architecture. We can add more modules if we want to do more complicated things. So, rather than having one sensor and one actuator, we can do sensor fusion. We can take the inputs of many sensors, all observing this observed space from different perspectives.

You could have two "eyes" looking to collect visual information from two different angles. Or it could be more diverse than that. You could have "eyes, ears, and a nose" - different sensory modalities, each making their sense of what is out there, then correlated into a view of this observed space.

Based on this higher-level idea of what is happening in this observed space, we can create a much more refined action than just kicking your leg and pushing that out into the conceived space. So, this is my model of what sensation looks like in a digital system. Now, if you have sensation...

Perception in a Digital System
Tech Research Pod Presentation Slide_Block Diagram 4 Model of Perception Coordination in a digital system_ What is Knowledge Organization Infrastucture _David Sission
KOI Node Block Diagram 4. "Model of Perception & Coordination in a Digital System"
[00:09:01] The next obvious step is to define what perception looks like. To me, perception is expanding this to encompass whole sets of sensor information. Here we essentially have a sensory system - i.e., vision, proprioception, audition - of multiple systems coming together to identify objects, in an otherwise undifferentiated observed space. And then, based on that analysis of the observed space, we can activate a coordinated set of actuators and perform some rather complicated behaviors based on our perceived notion of what is going on in the world. So this then represents perception and the idea of coordination.

Further Developing a KOI Network
[00:10:01] As any good psychologist knows, after perception, you have cognition. And I am not going there yet, because we are currently developing this sensation system. We have our sensors looking at Google Drive, HackMD, and Slack, and based on all of these inputs, we process them through an embedding. We embed them into a semantic vector space and let an LLM have at them, to produce sensible outputs based on these inputs. I do not want to get too far ahead of ourselves, worrying about what cognition looks like, although there are people in the room here who have ideas of what this looks like. I want to leave you with, make KOI not war, and you might end up with understanding rather than just a big mess.

Make KOI not war, and you might end up with understanding rather than just a big mess
On Cognition & Metacognition
"...All epistemic agents physically consist of parts that must somehow comprise an integrated cognitive self. Biological individuals consist of subunits (organs, cells, and molecular networks) that are themselves complex and competent in their own native contexts. How do coherent biological individuals result from the activity of smaller sub-agents?"
📚
Levin, M. (2019). The computational boundary of a “Self”: developmental bioelectricity drives multicellularity and Scale-Free cognition. Frontiers in Psychology, 10. https://doi.org/10.3389/fpsyg.2019.02688
[00:11:30] Zargham: On the cognition thing, David knows that my current take on this is that an organization such as BlockScience is already a cognitive system. We have the capacity for group-level sense-making. In keeping with the Michael Levin approach to thinking about what might be a cognitive system, I would argue that, in a sense, BlockScience, as a group, already exhibits properties of a cognitive system. And that is actually what we are doing right now, which is closer to metacognition.

We are thinking about how we think about things, and altering how we structure our information. And so I would hazard to say that this diagram already goes beyond perception to cognition if you start making explicit the human interfaces that are in some sense perpendicular to this. So some of these sensors, processors, and actuators have interfaces in a perpendicular plane where we read from and write to them. Or we could make the fact more explicit, that this is what the sensors and actuators do, they read from stuff we are doing, and write to the workspaces we are in.

That shows up in Slack with the LLM, but might show up more realistically through things like authoring Google Docs and HackMD where to David's other diagrams about knowledge processing there is a very strong loop closure between our, individual and group level knowledge object production, and our individual and group level knowledge object consumption, which closes a feedback loop, which produces a set of behaviors that go beyond just perception and coordination, but arguably would pass some definitions of cognition.

David and I talked a little bit about this idea of entropy and a system with a dotted line around it. The system has the property of entropy in the sense of the variety it can exhibit. The variety it exhibits is smaller at the group level than some of the absolute variety of the subsystems because that implies that those subsystems are co-regulating or self-regulating in some sense.

And so, just starting to ask questions about closing loops and co-regulation and the interfaces between these systems and humans. I think you start to get things that look and feel like - again, depending on your choice of definition - cognitive systems, and that what we are doing is closer to metacognition at the group level because we are cognating about how we cognate, and even reconfiguring that in an intentional way.

I think there is at least a conceived space around cognition and metacognition here that, in some ways, the very purpose of KOI is to ask, "how are we doing group-level cognition? And, are we okay with it?" To borrow from David again, is it wise, not just intelligent? For that, you have to be able to metacognate.

Coming from the other direction would be to say our organization is already a cognitive system as a group. When we metacognate, we ask questions and think about how we think, and then we find ourselves thinking, "Maybe we could rearrange that." And so we are, in fact, moving in the other direction, creating systems that can facilitate improving, adjusting, or restructuring our group-level cognitive feedback processes.

Discussion Q & A
Q: How to Identify Reflexes in an Evolved System
[00:15:20] Anon: I was intrigued by the idea of the reflex as something recognizable in an evolved system rather than a design system, the fact that there is a clear pattern here that you could search for. Maybe you are generating augmented graphs and want to recognize when a reflex has occurred in response to something.

Do you have a sense of how to recognize a reflex in a system and how it would be differentiated from other types of things that could occur?
A: Effectively, Nothing Between the Sensor & Actuator
Block Diagram 1: Referenced in question with answer Effectively, Nothing Between the Sensor & Actuator
[00:15:56] David: My definition is biological. It is simplicity. There is effectively nothing between the sensor and the actuator. In other systems, there could be degenerate pieces in between, but they do not really do anything; they pass through. If you can identify something as a pass-through, eliminate, and filter it out of concern, and still see this sensor straight to the actuator, then you have basically got a reflex.

What I mean by reflex is that there is very little room for behavior modification. The only real thing that the patellar tendon reflex does is act as an actuator with an effective threshold, and if the sensed output hits a certain level, it triggers the knee reflex. But that is the only processing that goes on here. And thresholds are pretty simple. You do not need anything other than these two. The processing within the actuator is sufficient or could be within the sensor. But one or the other implements a threshold and passes it on..

Q: Conceived vs. Observed
[00:17:08] Anon: If an actuator produces knowledge objects that end up in conceived space, there could be a case in which it is noted that a system like this has produced it, and a scenario in which people will validate that information as being satisfactory in some sense.

Is there a distinction considered ar0und the difference between what is conceived and observed, and what makes observed valid to be sensed?
A: Slippery Definitions & Explicitly Leaky
Block Diagram 4: Referenced in question with answer slippery definitions and explicity leaky
[00:18:21] David: The purpose of this is to try to make sense. So, rather than validity, I would use the term "make sense". The other thing you have indicated, which this diagram tries to show, is that the definitions of sensors, processors, and actuators are slippery. If I only think about this box, I could consider this thing that I have labeled a processor, a sensor.

The other thing to think about is that most of the lines in this diagram should be considered leaky. The borders I have drawn are dotted lines to make it explicitly leaky. These wires are also leaky. Or you might not want to have any leakage and explicitly show feedback. But you can not say just because this thing is embedded in something that it is not in some way directly affected by what is going on out in the periphery. It can be insulated, but no insulation is perfect.

Q: On Designations of Nodes
[00:19:30] Anon: Okay. So it is designed as intended. The intention for that leftmost KOI processor is up to the people who designated it as such in this diagram. It is designated as a sensor because somebody made that designation. Someone looked at this diagram, tried to make sense of it, and, in doing so, labeled it a sensor.

What inspired this question was someone describing a Google Drive sensor that was leveraging the Claude.ai API, and it sent me for a bit of a loop because I could not place it in this diagram. This is the diagram that I have in my head, but when somebody else describes something as a sensor or an actuator, there are cases in which I do not know where to place it in the diagram.

Is there some kind of a goalpost that will help a group place these blocks?
A: Sensemaking
Defining KOI Nodes with the complexity of Block Diagram 4 vs Block Diagram 1
[00:20:55] David: They will have to develop their own sensemaking standard largely because this big, complicated thing can be collapsed into that. Any one of these nodes can have the complexity of this entire perception /coordination diagram [KOI Node Block Diagram 4], and this whole diagram can be represented with the simplicity of a single node. [KOI Node Block Diagram 1]

Q: Differentiating Between Different Functions
[00:21:31] Anon: In differentiating between the different functions, I can think about this "one type of KOI node to rule them all", as like a stem cell, and then you end up with a kind of way that the environment feeds back onto it, it starts to differentiate itself.

To what extent is the ultimate game plan or goal when we start to leverage this in our work? To have a broad tapestry of predefined KOI nodes that we have to pick up and slot, maybe in a visual medium to figure out what connectors we need for our context for an LLM to do its work versus having like archetypes that are very general...
Like you were saying, you draw a box around and say, "Just pick a sensor type", and it will figure out what it needs to connect to. Given all the possible things it can connect to, let it do its work by chewing on the context you feed it. Gradually, it will become either one of our stock types or bespoke to your project or usage.

Where do you see the end result going toward?
A: Domain General Architecture
[00:22:33] David: There is this idea of a sort of domain-general architecture that we could use as the stereotypical or the prototypical standard example. Something along the lines of a deep, convoluted neural network, that constitutes this random latent space that gets trained to do something.

[With regards to domain-general, modular architecture (DOGMA) and the role that things like deep convoluted neural networks (DCNNs) play in this architecture, see Cameron J. Buckner's work ]

📚
Buckner, C. J. (2023). From Deep Learning to Rational Machines: What the History of Philosophy Can Teach Us about the Future of Artificial Intelligence. Oxford University Press.
📚
Buckner, C. (2018). Empiricism without magic: Transformational abstraction in deep convolutional neural networks. Synthese, 195(12), 5339–5372. https://doi.org/10.1007/s11229-018-01949-1
Now, people do that, but it takes nine months for that stem cell to become self-supporting. And it takes another 30 years for your brain to mature so people will trust what you say. I think we can short-circuit that process with a little bit of engineering. So each one of these nodes could be a deep, convoluted neural network that has to learn. We can create a network as complicated as we want and have it make every possible connection.

But then you need something along the lines of Hebbian learning to decide which connections are any good and which ones are not. And it is just a really inefficient process. So if you know ahead of time where you want to go, you might be able to shape where you want to get to more rapidly. And we know that we want to have these standard pieces, so it is our job right now to understand how to recognize them when we have created them.

[00:22:00] Anon: I think that is exactly the challenge. Because from my perspective, I can see like a catalog of sensors being readily apparent, but I can see a lot of gray areas starting to come about where you are not entirely certain what process you are supposed to be using - you want perception, but what kind of perception is not defined until you have already delineated the types of sensors that are fusing. And you may not even necessarily know how to classify this. To use the diagram as an example...

I was wondering about the extent to which there are limitations on back propagation updating or a Hebbian learning or something else that would work in that context.
Topology of Expert Systems
ChatGPT Tesselation of blue and orange KOI in the style of M.C. Escher’s Circle Limit III, the tesselation worked, but fails to capture the mathematical intricacies of Escher's hyperbolic design See: "A 'Circle Limit III' Calculation",   
ChatGPT Tesselation of Blue & Orange KOI. Artistic style prompt: M.C. Escher’s Circle Limit III. See: "A 'Circle Limit III' Calculation", 
[00:25:00] Zargham: I also want to do a concrete sanity check. One is that we do not need these things to be super AI or learning heavy. Once you are doing the architecture this way, you could have an entirely expert system, like a topology of expert systems, with just rules like this, which could be viewed entirely like a data supply chain, like a bunch of kinds of ingest and conformed steps, and then some expert system.

I have been thinking a lot about this because I have been working on developing business around this knowledge and capability as algorithms as policy. I am talking to some folks who are interested in bringing automation into at least a fast-chain quick approval process where you have to take in different multimodal information and have basically sensor decoders.

So if you think of the clusters of sensors of being common type - maybe they are PDFs - and then you have sensor decoders that structure and organize that information, and then processes that take the structured and ordered information into a refinement, into something like estimating some facts, and then taking the fact estimates and applying some existing expert systems rules that are literally legislated and then ultimately rendered as a decision. Then, that whole system is fed back on by an oversight body that measures it against other metrics.

At the narrowest scope, that is what the e-bike stuff is. We are going to prescribe specific sensors. We can configure our HackMD sensor, our GitHub sensor, and our Google Drive sensor, and we can point it so we can both configure it and point it at something. Then, we can write a decoder one step down that is aware of what we pointed it at.

I think some of the issues here are that, in general, it is easy to talk about these stories, but in specificity, you are literally just creating a model the same way we do for our client models. We are literally just taking a bigger picture — observed space and conceived space — and saying, "We want to get from here to there." Then, we break down what that means and say, "Okay, well, here is not just one place."

It has all of these things that we can sense. Great. But now that we know that, we know something about what should be downstream of those things to make sense of them, conform, and integrate them. But in order to fill one of these in a non-abstract way, you need to start with an observed space, and a conceived space, and an animating purpose. Then start breaking it down until you can specify the blocks, which I think we are now at the point where this is exactly what we need to do in this research.

That is why, in our previous meeting, I was pretty excited to take a really minimalist kind of output template conceived space and input open-ended observed space, but just to constrain it to say things we can sense with: something that can read PDFs, something that can read Google Docs, something that can read Markdown, something that can read a Github repo. And that is enough.

You just put the stuff you want to sense in the places the sensors are hooked. You prescribe something about what you expect to see, then decode and organize the sensor data. And then, as you go through the process, you get to something that outputs in the conceived space. And then, of course, this goes back to the human kind of cyborg-y bit.

It is not good enough just because it transformed the data from the observed space into the conceived space. We have some validation, some sense of whether it did a good job and some capacity for calibrating. And so to some extent our feedback loop, our backdrop is not algorithmic, it is human.
It is us going back in and being like, oh yeah, this was not quite right. Let me tweak the rules in the processor that decodes the data that came from GitHub. Give it a little bit more information about what to look for and how to parse it, extend the question kit that we are using, or maybe shrink the question kit that we are using because one of the questions is causing more noise than benefit.

There is this like total coin flip where we have got all of this theory and all of these tools and it is like we are entering the phase where we turn it upside down and start just using it to do stuff to figure out what the node templates should be, how to make them more configurable and how to maintain this.

Or actually, not just to maintain, but to actualize the research that we have done both on the systems design side with things like BDP, MSML and cadCAD to make sense of closed loop behavior of complex systems from a design and analysis standpoint and what we have researched and how to implement them from a KOI side. Now we can design, implement, and use closed-loop knowledge processing systems. And because these are expressible as block diagrams, we should be able to develop a cadCAD representation of them that will allow us to rapidly explore that solution space.

⚙️
The Block Diagram Potocol (BDP) defines a schema for data that represents a block diagram as well as functionality for these block diagrams.
Docs https://blockscience.github.io/bdp-lib/
Repo https://github.com/BlockScience/bdp-lib
⚙️
The Mathematical Specification Mapping Library (MSML) is a library for standardizing the creation of mathematical specifications as JSON objects, and also the automation of report and visualization creation from these standardized JSON.
https://github.com/BlockScience/MSML
⚙️
Complex adaptive dynamics Computer-Aided Design (cadCAD) is an open-source Python package that assists in designing, testing, and validating complex systems through simulation.
cadCAD Documentation
Differential Specifications Syntax Key
Acknowledgments
This blog post is based on the original ideas presented by David Sisson, Ph.D, and with his express permission, repurposed here with the assistance of Descript, and humans in the loop for technical and editorial review, and publishing. Thank you, David, Zargham, Sean, Christine, Jessica Zartler, and lee0007. The video also includes a thank you from David to Orion, Luke, Jeff, Joshua, and Sayer.

About BlockScience
BlockScience® is a complex systems engineering, R&D, and analytics firm. By integrating ethnography, applied mathematics, and computational science, we analyze and design safe and resilient socio-technical systems. With deep expertise in Market Design, Distributed Systems, and AI, we provide engineering, design, and analytics services to a wide range of clients, including for-profit, non-profit, academic, and government organizations.

