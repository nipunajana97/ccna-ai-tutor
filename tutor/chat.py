"""Shared streaming lifecycle: authorize first; save delivered text even on interruption."""
from tutor.engine import GenerationError


def stream_reply(store, user_id, conversation_id, question, check_subscription, prepare_response):
    question = question.strip()
    if not question or len(question) > 1200:
        raise GenerationError("Enter a question of up to 1,200 characters.")
    # A fresh Stripe lookup is required here, regardless of the cached sidebar display.
    request_id = store.reserve(user_id, check_subscription(), "chat")
    fragments, references = [], []
    interrupted = False
    try:
        tokens, references = prepare_response()
        for token in tokens:
            if token:
                fragments.append(token)
                yield token
        if not "".join(fragments).strip():
            raise GenerationError("No response was returned. Your free prompt is still available.")
    except BaseException:
        interrupted = True
        raise
    finally:
        answer = "".join(fragments)
        if answer.strip():
            store.complete_chat(request_id, user_id, conversation_id, question, answer, references, interrupted)
        else:
            store.fail(request_id, user_id)


def preview_response(question):
    """Curated offline content for the local UI preview; never represented as model output."""
    text = question.lower()
    if any(word in text for word in ("ospf", "neighbor", "adjacency")):
        section = "3"
        answer = """For an OSPF neighbor stuck in **ExStart or Exchange**, check the interface MTU first.

1. Compare MTU on both ends of the link.
2. Check the area, network type, Hello/Dead timers, and authentication.
3. Confirm the expected neighbor relationship: two DROTHER routers on a broadcast segment normally remain at **2-Way** with each other.

An MTU mismatch can prevent database description exchange from completing. [s3-c0]"""
    elif any(word in text for word in ("route", "routing", "prefix", "distance")):
        section = "2"
        answer = """A router forwards a packet using the **longest matching prefix** in its routing table.

If both `10.1.0.0/16` and `10.1.2.0/24` are installed, traffic to `10.1.2.10` uses the `/24` route.

Administrative distance helps select which source installs a route to the **same prefix**. A static route defaults to AD 1, while OSPF defaults to AD 110. Metrics select paths within a routing protocol. [s2-c0]

**Remember:** route installation and packet forwarding are different decisions."""
    elif any(word in text for word in ("stp", "vlan", "switch", "bridge")):
        section = "4"
        answer = """STP elects the switch with the **lowest bridge ID** as the root bridge.

The bridge ID combines the configured priority, VLAN extended system ID, and MAC address. Each non-root switch chooses a root port based first on the lowest total path cost to the root.

**PortFast** lets an edge host port start forwarding quickly. **BPDU Guard** places a protected port into err-disable if it receives a BPDU. [s4-c0]"""
    elif any(word in text for word in ("acl", "security", "arp", "dhcp")):
        section = "5"
        answer = """A **standard ACL** matches source IPv4 addresses. An **extended ACL** can also match destination, protocol, and TCP/UDP ports.

Rules are evaluated from top to bottom; the first match wins. An implicit deny follows the configured entries.

Place a standard ACL near the destination when practical, so it does not block that source from reaching unrelated destinations. Extended ACLs are commonly placed near the source. [s5-c0]"""
    elif any(word in text for word in ("api", "automation", "ansible", "terraform")):
        section = "6"
        answer = """**Ansible** commonly pushes network configuration over SSH without an installed agent. Its playbooks use YAML.

**Terraform** describes desired infrastructure using HCL and tracks managed resources in state.

For a REST API, `GET` retrieves, `POST` creates, `PUT` replaces, `PATCH` partially updates, and `DELETE` removes a resource. [s6-c0]"""
    else:
        section = "1"
        answer = """Here is a subnetting walkthrough using **192.168.10.77/26** as an example.

1. `/26` means a mask of `255.255.255.192`.
2. The last-octet block size is `256 − 192 = 64`.
3. The boundaries are `0`, `64`, `128`, and `192`. The host `77` lies in the block starting at `64`.

| Item | Value |
| --- | --- |
| Network | `192.168.10.64/26` |
| Broadcast | `192.168.10.127` |
| Usable hosts | `192.168.10.65–192.168.10.126` |
| Host count | `62` |

The first address identifies the network; the last is broadcast for this ordinary IPv4 LAN. [s1-c0]"""
    return section, "**Offline example · interface preview**\n\n" + answer
