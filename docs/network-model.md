# Hearth Node Attachment and Network Integration

[Docs](README.md) / [Chinese (Simplified)](network-model.zh-CN.md)

One of the easiest things to misunderstand when first reading about Hearth is the phrase "connect to Hearth".

In practice, that phrase often mixes together four different things:

1. **An operator connects to the Hearth control plane**
   - through the Web UI, CLI, or API.

2. **Local clients attach to the node managed by Hearth**
   - these clients are not just browser tabs; they are Reticulum-aware applications or nodes running on phones, computers, and embedded devices.

3. **The Hearth-managed Reticulum Transport Node attaches to the wider network**
   - through uplink, backbone, radio, or other network-facing interfaces.

4. **You still need to decide what clients and what wider network shape to start with**
   - that is where questions like "what is recommended" and "is it built in" matter.

If these layers are not separated clearly, documentation can feel like it only explains how to open a Web dashboard, without showing the real network path or the actual ecosystem around it.

---

## Start with the three path layers

The simplest model looks like this:

```text
operator browser / CLI / API
            |
            v
      Hearth control plane
            |
            v
Hearth-managed Reticulum node
      |                      |
      |                      |
 local-facing interfaces   uplink / backbone interfaces
      |                      |
 local client nodes       wider Reticulum network
```

The most important point is this:

- **Hearth is the control plane**
- **the actual Reticulum traffic is carried by the runtime and interfaces Hearth manages**

So Hearth does not replace the Reticulum data plane. It makes that data plane operable, visible, recoverable, and manageable.

---

## 1. How humans connect to Hearth

This is the easiest layer to understand.

Operators reach the Hearth control plane through:

- the Web UI, for example `http://127.0.0.1:8480/login`
- the CLI, for example `hearth status --config hearth.toml`
- the REST API, for example `GET /api/node/status`

This layer exists so you can:

- log in
- inspect state
- change configuration
- start and stop runtime or interfaces
- review peers, routes, and announces
- perform backup, restore, maintenance, and security tasks

This layer is **not** the Reticulum data path.

In other words:

- your browser is reaching the Hearth management surface
- it is not itself "joining the Reticulum network"

---

## 2. What are local clients, concretely?

This is where the abstraction often becomes unhelpful if it is not made concrete.

Local clients are things like:

- Reticulum applications running on phones
- Reticulum applications running on laptops or desktops
- embedded devices running Reticulum-aware node software
- your own applications built on top of Reticulum

These are not ordinary Web pages. They are applications or nodes that actually speak Reticulum or are built on Reticulum services.

So the more accurate statement is not that local clients "log into Hearth", but that:

> **local clients attach to the Reticulum Transport Node managed by Hearth.**

That relationship looks more like this:

```text
phone / laptop / embedded device
            |
            v
local Reticulum client or application
            |
            v
Hearth-managed local-facing interface
            |
            v
Hearth-managed Reticulum node
```

### Typical local client examples

These are two of the clearest examples in the current Reticulum ecosystem:

- **Sideband**
  - an official communications application for Android, Linux, and macOS, and one of the easiest ways to understand what a user-facing Reticulum client looks like
  - project / docs: <https://github.com/markqvist/Sideband>

- **Nomad Network**
  - an official communications platform built on LXMF and LXMRouter, useful when you want to understand a more network-native application model
  - project / docs: <https://github.com/markqvist/NomadNet>

- **Your own Reticulum application**
  - if you are building custom tools, devices, or services, any application built on Reticulum can be a local client in this model
  - project / docs: <https://github.com/markqvist/Reticulum>

### What this means for Hearth

Hearth is not those clients.

Hearth is the thing that gives those clients:

- a stable node to attach to
- a manageable interface surface
- visibility into peers, routes, and announces
- recovery, configuration, and security workflows around the node they use

So Hearth is better understood as the node operations layer behind those local clients.

---

## 3. Through what do local clients actually attach?

They do not attach through the Web login page. They attach through **interfaces**.

In official Reticulum documentation and deployment practice, those local-facing interfaces commonly include:

- local-link or LAN discovery style interfaces
  - official docs: AutoInterface
  - <https://reticulum.network/manual/interfaces.html#the-autointerface>

- TCP interfaces on a LAN or local IP network
  - official docs: TCPServerInterface / TCPClientInterface
  - <https://reticulum.network/manual/interfaces.html#the-tcpserverinterface>
  - <https://reticulum.network/manual/interfaces.html#the-tcpclientinterface>

- serial or radio-facing interfaces
  - official docs: RNodeInterface
  - <https://reticulum.network/manual/interfaces.html#the-rnodeinterface>

So "local nodes attach to Hearth" really means they attach to the Transport Node through one of those interfaces.

In the current Hearth repository, the interface-management layer already includes built-in `tcp`, `serial`, `rnode`, and `custom` drivers. The broader local-facing and upstream connectivity model still depends on how you configure and supervise the actual Reticulum runtime for your deployment.

---

## 4. What is the "wider network", exactly?

The wider network is **not** a single official "Hearth Cloud", and it is not a built-in default public network that Hearth automatically joins.

In Reticulum terms, the wider network can be any of the following:

- **your own home or LAN segment**
  - a few devices connected over local links or a LAN
- **your own community network**
  - a set of nodes connected over wired, radio, or mixed links
- **longer-distance IP-connected infrastructure**
  - nodes interconnected over TCP/IP
- **radio networks**
  - nodes interconnected through RNode, LoRa, or other radio transports
- **overlay networks**
  - nodes interconnected through transports such as I2P

A good official starting point for understanding this is the Reticulum manual section on network structure:

- **Building Networks**
  - <https://reticulum.network/manual/understanding.html>

### Common ways a Hearth node reaches the wider network

If you want your Hearth node to reach beyond a single machine or very small local segment, common patterns include:

- **TCP uplink / backbone**
  - for reaching other infrastructure nodes or a wider IP-connected Reticulum network
  - docs: <https://reticulum.network/manual/interfaces.html#the-tcpclientinterface>

- **local TCP / IP entry plus upstream uplink**
  - useful for a home node or community entry node
  - docs: <https://reticulum.network/manual/interfaces.html#the-tcpserverinterface>

- **RNode or radio-facing uplink / edge connectivity**
  - useful for field nodes, community radio, or local wireless segments
  - docs: <https://reticulum.network/manual/interfaces.html#the-rnodeinterface>

- **I2P overlay connectivity**
  - useful for more hidden or specialized network paths
  - docs: <https://reticulum.network/manual/interfaces.html#the-i2pinterface>

So Hearth reaches the wider network not by becoming a new protocol, but by managing the interfaces through which the node joins the broader Reticulum topology.

---

## 5. Two typical deployment examples

### Example 1: always-on home node

```text
phones / laptops / home devices
        |
        v
local LAN / TCP interface
        |
        v
Hearth node
        |
        v
TCP uplink
        |
        v
wider Reticulum network
```

In this model:

- the Hearth node is the local anchor in the home
- nearby devices prefer entering through that local node
- the node then reaches the wider network through its uplink

### Example 2: hybrid radio gateway node

```text
field nodes / handheld nodes
        |
        v
radio link
        |
        v
RNode / serial interface on the Hearth host
        |
        v
Hearth-managed Reticulum node
        |
        v
TCP uplink / community backbone
        |
        v
wider Reticulum network
```

In this model:

- Hearth sits between a local radio segment and a broader IP or community network
- it is not just a dashboard; it is supervising a real infrastructure node that bridges network segments

---

## 6. What is recommended as a starting point?

The following are **engineering recommendations based on the official ecosystem and the current Hearth repository state**. They are not built-in Hearth defaults.

### If you want to start with a local client

A practical starting point is one of these:

- **Sideband**
  - closer to a real user-facing application on an actual device
  - useful when you want to understand what it means for phones or laptops to use your own node
  - <https://github.com/markqvist/Sideband>

- **Nomad Network**
  - useful when you already want a more network-native, node-oriented application model
  - <https://github.com/markqvist/NomadNet>

### If you want to start with wider-network connectivity

A practical starting topology is one of these:

- **home / lab start**
  - one local-facing interface
  - one TCP upstream interface
  - easiest to debug and easiest to observe with peers, routes, and announces

- **radio-first start**
  - one RNode / serial interface
  - optionally add a TCP uplink later if you also want broader reach
  - useful if you already have radio hardware or a community radio context

### What is not a good starting assumption

- assuming there is a built-in default public Hearth network
- treating the Web UI itself as the network-attachment path for client nodes
- treating the mock backend as proof that real wider-network attachment is already complete

---

## 7. Does Hearth build any of this in?

This needs to be said very clearly.

### Things Hearth does **not** currently bundle

The current repository does **not** bundle:

- Sideband or similar client applications
- Nomad Network or similar higher-level network applications
- a built-in public Reticulum network list
- a default backbone configuration that automatically connects you outward

In other words:

> **Hearth does not automatically choose your client ecosystem, your upstream network, or your public attachment point for you.**

You still choose those based on your deployment goals.

### Things Hearth **does** already include

What the current repository already includes is primarily control-plane functionality:

- Web / CLI / API management surfaces
- `mock_process` and `external_process` runtime backend entry modes
- a base interface-management framework
- built-in `tcp`, `serial`, `rnode`, and `custom` interface drivers in the current repo
- configuration, backup, monitoring, security, plugin, service, and bridge workflows

### What that means

So Hearth is currently much more like:

- **your node control center**
- **your infrastructure-node operations layer**

and not like:

- a fully bundled all-in-one client suite
- a hosted service with a built-in default public network

---

## 8. Where the repository stands today

This is important for understanding the current project phase.

In the repository today:

- local quick start defaults to `reticulum.backend = "mock_process"`
- that is excellent for learning the UI, API, config, and workflow model first
- but it is **not yet** a full demonstration of a real node already attached to the wider Reticulum network

A good way to think about the current state is:

- **the control plane is already meaningful**
- **the real network integration model is already clear**
- **real integration still depends on deployment-time configuration of actual runtime and interfaces**

The key directions toward real network attachment are:

- switching from the mock backend to a real backend such as `external_process`
- configuring actual local-facing interfaces
- configuring actual uplink or backbone interfaces
- verifying that peers, routes, and announces appear as expected after startup

---

## 9. What you minimally need for real network attachment

A realistic minimum path usually looks like this:

1. Prepare an always-on Linux host
2. Deploy Hearth on that host
3. configure security settings such as `admin_token`, `allow_lan`, and `allow_wan`
4. configure a real Reticulum runtime backend
5. choose a local client direction such as Sideband or Nomad Network
6. configure at least one local-facing interface
7. configure at least one uplink, backbone, or radio-facing interface
8. start the node and verify:
   - interfaces are online
   - peers begin to appear
   - routes are learned
   - announces are visible

That is the point where Hearth moves from "a local control-plane demo" to "an actual node system participating in a live network".

---

## 10. Recommended next reading

If your main question is now "how do I wire this into a real network?", read these next:

1. [`getting-started.md`](getting-started.md)
   - Bring up the control plane first and understand the basic workflow.
2. [`deployment.md`](deployment.md)
   - Move the system onto a host suitable for long-running operation.
3. [`config-reference.md`](config-reference.md)
   - Understand `reticulum`, `web`, `security`, and `[[interfaces]]` configuration.
4. [`security.md`](security.md)
   - Before you let real devices attach, be deliberate about exposure and authentication.

---

## Summary

The easiest sentence to remember is:

> **Hearth is not the network that client nodes directly "log into"; it is the control plane used to run and manage the node, while both local clients and the wider Reticulum network enter and leave through the interfaces that Hearth manages.**
