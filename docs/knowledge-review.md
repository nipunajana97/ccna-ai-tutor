# Review of the supplied reference

The six sections were retained and clarified. This is a starter subset, not the complete CCNA blueprint.

| Original statement | Correction used in the app |
| --- | --- |
| /25 has 2 subnets, /26 has 4, etc. | Those counts assume a /24 parent. |
| Route lookup is always longest prefix, AD, then metric | Separate route installation from forwarding; do not directly compare metrics of unrelated protocols. |
| Unreachable / discard has AD 255 | AD 255 prevents installation; a normal static Null0 route defaults to AD 1. |
| OSPF metric is always 100 Mbps / bandwidth | That is the default reference bandwidth, with minimum cost 1; configuration can change it. |
| Exactly seven OSPF neighbor states | NBMA can use Attempt. DROther-to-DROther Two-Way can be normal. |
| DR stays until process/router restarts | DR failure and other election events can change roles too. |
| Same mask is required for all OSPF links | Broadcast mask checks must not be generalized to every network type. |
| Any mode plus static trunk makes a trunk | Static access remains access; trunk/access is a mismatch. |
| 802.1D vs Rapid PVST+ 802.1w | RSTP is 802.1w; Rapid PVST+ is Cisco's per-VLAN implementation. |
| All root ports are designated | Avoid an absolute claim across unusual shared/same-switch segments. |
| BPDU Guard only works on PortFast ports | Global PortFast guard and explicit interface guard differ. |
| DAI validates only dynamic leases | Static hosts need suitable bindings or ARP ACL treatment. |
| Bearer tokens and API keys are equivalent | They are distinct credential concepts. |

Primary references:

- Cisco routing: https://www.cisco.com/c/en/us/support/docs/ip/enhanced-interior-gateway-routing-protocol-eigrp/8651-21.html
- Cisco OSPF MTU troubleshooting: https://www.cisco.com/c/en/us/support/docs/ip/open-shortest-path-first-ospf/13684-12.html
- Cisco switchport command reference: https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-16/command_reference/b_1716_9300_cr/interface_and_hardware_commands.html
- Cisco RSTP: https://www.cisco.com/c/en/us/support/docs/lan-switching/spanning-tree-protocol/24062-146.html
- Cisco v1.1 blueprint: https://learningcontent.cisco.com/documents/marketing/exam-topics/200-301-CCNA-v1.1.pdf
- RFC 3021: https://www.rfc-editor.org/rfc/rfc3021

These links are reading references, not proof that every generated explanation has been independently validated. A networking reviewer should check generated examples before a public launch. No scraped Cisco exam questions or paid course extracts are included.
