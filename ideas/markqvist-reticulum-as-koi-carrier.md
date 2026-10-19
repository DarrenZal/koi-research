# Mark Qvist's Reticulum as a candidate KOI transport binding

**Status:** exploratory implementation hypothesis; review candidate; no adapter implemented

**Date:** 2026-09-07

**Author:** Darren Zal

**Intended target:** `DarrenZal/koi-research`, `ideas/markqvist-reticulum-as-koi-carrier.md`

**Authority:** Darren's personal KOI research note, not a decision or claim by the KOI-net maintainers, Regen AI, or Substrate Dynamics

**Disposition:** `implementation hypothesis`

## Version-pinned sources

- [Reticulum 1.5.2](https://github.com/markqvist/Reticulum/releases/tag/1.5.2), commit [`ea98db4f53dcf0defc0e71a16e60d28b1229c4e6`](https://github.com/markqvist/Reticulum/tree/ea98db4f53dcf0defc0e71a16e60d28b1229c4e6), accessed 2026-09-07.
- [`DynamicalSystemsGroup/koi-net`](https://github.com/DynamicalSystemsGroup/koi-net) implementation snapshot [`7a4d631bcfec86a162d07d8f1b0a004b671c0f0f`](https://github.com/DynamicalSystemsGroup/koi-net/tree/7a4d631bcfec86a162d07d8f1b0a004b671c0f0f), accessed 2026-09-07. This pin supports implementation claims below; it is not asserted to be a final or substrate-independent KOI specification.

At the pinned KOI-net commit, `NodeProfile` carries a `base_url`, `RequestHandler` resolves that URL and calls `httpx.post`, and `NodeServer` creates FastAPI POST endpoints under `/koi-net`. The implementation also defines signed request/response envelopes, RID/manifests/bundles, and `NEW`, `UPDATE`, and `FORGET` events. Its outgoing `EventQueue` and poll/broadcast `EventBuffer` are in-process structures, not a durable restart-safe outbox. [Node profile](https://github.com/DynamicalSystemsGroup/koi-net/blob/7a4d631bcfec86a162d07d8f1b0a004b671c0f0f/src/koi_net/protocol/node.py) · [request handler](https://github.com/DynamicalSystemsGroup/koi-net/blob/7a4d631bcfec86a162d07d8f1b0a004b671c0f0f/src/koi_net/components/request_handler.py) · [server](https://github.com/DynamicalSystemsGroup/koi-net/blob/7a4d631bcfec86a162d07d8f1b0a004b671c0f0f/src/koi_net/components/server.py) · [envelope](https://github.com/DynamicalSystemsGroup/koi-net/blob/7a4d631bcfec86a162d07d8f1b0a004b671c0f0f/src/koi_net/protocol/envelope.py) · [event types](https://github.com/DynamicalSystemsGroup/koi-net/blob/7a4d631bcfec86a162d07d8f1b0a004b671c0f0f/src/koi_net/protocol/event.py) · [event buffer](https://github.com/DynamicalSystemsGroup/koi-net/blob/7a4d631bcfec86a162d07d8f1b0a004b671c0f0f/src/koi_net/components/event_buffer.py)

## Question

Could Reticulum carry KOI request/response envelopes, events, manifests, bundles, and reconciliation traffic across constrained or non-IP networks while preserving KOI's application semantics?

The answer is plausibly yes, but only through an explicit transport binding. This is not a configuration-only change to the pinned KOI-net implementation. It would require replacing or wrapping its HTTP-specific `RequestHandler` and `NodeServer`, or placing a local HTTP-to-Reticulum gateway beneath them.

```text
KOI application semantics
  RIDs · manifests · bundles · NEW/UPDATE/FORGET · signed envelopes
                           ↓
Reticulum transport binding or local gateway
  identified Links when required · Requests · Resources
                           ↓
Reticulum network
  Destinations · announces · routing · interface authentication
                           ↓
TCP/IP · I2P · local Wi-Fi · serial · packet radio · LoRa
```

Reticulum would not replace KOI. KOI's object identities, event meanings, signed-envelope rules, peer relationships, local handlers, caches, and synchronization behavior remain application concerns. Reticulum would supply an alternate addressing, routing, encryption, and carriage layer.

## Candidate correspondence

| KOI-net surface at `7a4d631` | Candidate Reticulum carrier | Qualification |
|---|---|---|
| Node endpoint and `base_url` | Explicit KOI-node-RID ↔ Reticulum-Destination binding | These are different identities. The binding needs signatures, rotation, recovery, and continuity rules. |
| `SignedEnvelope` request or response | Reticulum Request/response or Channel message | The parsed KOI envelope must still verify under KOI's own serialization and key rules. Reticulum cryptography does not replace it. |
| Broadcast-events endpoint | Explicit application fan-out over point-to-point Reticulum requests or channels | Core Reticulum does not supply KOI subscription or broadcast semantics. |
| Poll-events endpoint | Reticulum request/response | Poll cursor, acknowledgement, retry, ordering, and buffer semantics remain KOI/application responsibilities. |
| RID, manifest, or bundle fetch | Request response; Resource for a larger payload | Enforce size and authorization before allocation; verify the KOI manifest/content hash after reassembly. |
| In-process event queue and buffers | A separately specified durable application outbox, shared by comparison arms | Core Reticulum does not make the pinned KOI-net queue restart-safe. Transport availability is not durability. |
| Boundary/proxy node | Reticulum-facing KOI adapter or local gateway | Delivery is a proposal to the receiving node, not automatic semantic admission. |

## Invariants an adapter must preserve

1. **Reference identity:** RIDs retain their KOI meaning and are not silently replaced by Reticulum destination hashes.
2. **Envelope verification:** a signed KOI envelope verifies after the round trip using the same pinned KOI serialization and key rules.
3. **Provenance separation:** a Reticulum identity authenticates a transport peer or destination; KOI provenance identifies an assertion, object, or transformation. Neither substitutes for the other.
4. **Local authority:** receiving a message never forces a node to store, accept, transform, expose, or retransmit its referent.
5. **Idempotency:** duplicate delivery after retry or partition recovery cannot duplicate a materialized state transition.
6. **Forget semantics:** `FORGET` remains a KOI event handled by local policy; it is not equivalent to route loss or disappearance of an announce.
7. **Authorization:** explicit `Link.identify()` plus an allow-listed request path is one possible transport control. An application credential over an anonymous Link is another. RID type, peer relationship, recipient, purpose, and local disclosure policy may still need checks.
8. **Failure legibility:** partition, route loss, rejection, timeout, invalid signature, unavailable bundle, and local-policy refusal remain distinguishable outcomes.
9. **Metadata honesty:** TCP, I2P, radio, and local interfaces expose different metadata. “Encrypted” must not become “anonymous” or “unobservable.”
10. **No transport-to-semantics promotion:** path affinity, announce visibility, link frequency, or packet co-occurrence do not become knowledge edges, trust, consent, or commitments without an explicit governed transformation.

## What Reticulum does not add

Reticulum does not provide a knowledge graph, RID semantics, provenance interpretation, semantic conflict resolution, record-level consent and disclosure policy, a durable KOI outbox, federation agreements, or community standing.

Its `boundary` and `internal` interface modes chiefly alter announce propagation and path discovery; they should not be mapped directly to a KOI proxy or semantic membrane. Interface Access Codes provide coarse segment membership, not per-RID authorization.

Reticulum Link initiators are anonymous by default. Peer-specific endpoint authorization therefore requires explicit Link identification or an application credential. Intermediate nodes ordinarily cannot inspect encrypted application content or filter by a Reticulum source address, so accountable KOI telemetry would have to be produced at governed endpoints without recreating indiscriminate surveillance.

## Canonical experiment card: matched transport binding

**Status:** concept only, not preregistered.

**Primary estimand:** the effect of the transport binding, not the effect of adding a better queue, retry algorithm, or store-and-forward application.

### Matched arms

| Arm | Application payload and policy | Common carrier | Transport binding |
|---|---|---|---|
| H | Same pinned KOI envelopes, handlers, cache policy, durable test outbox, retry/ack rules, and target set | Local TCP with the same imposed partition schedule | Existing HTTP POST/FastAPI binding |
| R | Identical | Identical | Reticulum Request/Resource binding over TCP |

Use two local nodes and synthetic records. A harness outside both transports imposes the same connectivity windows, loss schedule, bandwidth ceiling, and payload sequence. The shared durable test outbox must be identical in both arms; it is an experimental control, not a claim about current KOI-net.

The fixture contains:

- one `NEW`, one `UPDATE`, one duplicate, and one `FORGET` event;
- a fixture-local application policy, identical in both arms, that declares one synthetic RID type inadmissible and emits a frozen refusal code;
- one bundle large enough to exercise the chosen Resource threshold;
- one unauthorized RID type and one corrupted KOI signature;
- a partition after a RID-only event notification and before bundle fetch;
- fixed node keys, Reticulum identities, random seeds, timeouts, and retry schedule.

### Checks

1. KOI envelope signatures verify after transport.
2. The explicit KOI-node-RID ↔ Reticulum-Destination binding verifies.
3. Duplicate delivery yields one materialized transition.
4. Both arms retain pending work through the same harness restart.
5. Unauthorized type and invalid signature produce distinct application-level refusals.
6. The transferred Resource reassembles to the expected bundle hash.
7. `FORGET` invokes the same local policy in both arms.
8. Endpoint logs preserve permitted provenance without prohibited payload fields.
9. Both arms report delivery, latency, transferred bytes, retries, failures, and operator steps in the same units.

### Interpretation and promotion

This comparison can estimate differences between HTTP/TCP and Reticulum-over-TCP under one fixed workload and failure schedule. It cannot establish that Reticulum is generally superior under partition, on radio, or in a community deployment.

Promote to adapter design only if the Reticulum arm preserves every semantic invariant and improves a predeclared operational outcome enough to justify its complexity and licence obligations. If both arms recover equally, or Reticulum merely recreates HTTP with more moving parts, stop or retain it only as a research control.

An optional later Reticulum-plus-LXMF arm would change both transport and delayed-delivery machinery. It therefore has an end-to-end bundle estimand, not the transport-only estimand above, and requires a separate pinned intake of LXMF first.

## Open questions

- Is a native Reticulum request/server pair simpler and safer than a local HTTP-to-Reticulum gateway?
- How should Reticulum identity rotation update a KOI `NodeProfile` without changing the logical KOI node?
- What acknowledgement semantics distinguish transport receipt from local KOI acceptance?
- Which endpoint evidence is sufficient for network research when intermediate transport intentionally hides sources and content?
- Do constrained carriers change knowledge-flow concentration, or only throughput and delay?
- Does the intended use satisfy the Reticulum License, especially if the implementation or associated documentation is copied, modified, redistributed, or used to create model-training data? The licence does not say that application data merely transported over Reticulum inherits that restriction.

## Adoption cautions

- The Reticulum reference implementation says it has not received an external security audit. Treat its security descriptions as project claims until independently assessed.
- The custom Reticulum License has field-of-use restrictions, including a restriction on using the software or associated documentation to create model-training data. It is not an OSI-approved open-source licence.
- Reticulum's GitHub repository is described as a public mirror with no promised public support or contribution cadence.
- The implementation and manual are its authoritative protocol specification; there is no independent RFC.
- Reticulum's contribution policy prohibits generative-AI-authored submissions. This research note must not be submitted upstream as a contribution.

## Disposition

**Implementation hypothesis.** Reticulum may be a useful optional carrier for KOI envelopes and bounded artifacts under constrained or non-IP conditions. The matched experiment above is the next evidential step if the question becomes active. Until then, retain the note as a design option; do not infer that KOI becomes sovereign, private, secure, offline-capable, or bioregional merely by changing transport.
