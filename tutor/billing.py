from dataclasses import dataclass


class BillingUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class Entitlement:
    active: bool = False
    customer_id: str | None = None


class StripeBilling:
    def __init__(self, secret_key, price_id, mode="test", client=None):
        if client is None:
            from stripe import StripeClient
            client = StripeClient(secret_key, max_network_retries=1)
        self.client = client
        self.price_id = price_id
        self.live = mode == "live"

    def entitlement(self, verified_email):
        """Call with an email from verified_identity, never from a textbox."""
        try:
            customers = self.client.v1.customers.list({"email": verified_email, "limit": 100})
            for raw_customer in customers.auto_paging_iter():
                customer = raw_customer.to_dict() if hasattr(raw_customer, "to_dict") else raw_customer
                if bool(customer.get("livemode")) != self.live:
                    continue
                if (customer.get("email") or "").strip().lower() != verified_email:
                    continue
                subs = self.client.v1.subscriptions.list({"customer": customer["id"], "status": "active", "limit": 100,
                                                          "expand": ["data.latest_invoice"]})
                for raw_sub in subs.auto_paging_iter():
                    sub = raw_sub.to_dict() if hasattr(raw_sub, "to_dict") else raw_sub
                    if sub.get("status") != "active" or bool(sub.get("livemode")) != self.live:
                        continue
                    invoice = sub.get("latest_invoice")
                    if not isinstance(invoice, dict) or invoice.get("status") != "paid":
                        continue
                    items = sub.get("items", {})
                    # Auto-paginate line items too; do not accidentally authorize another price.
                    line_items = self.client.v1.subscription_items.list({"subscription": sub["id"], "limit": 100}) if items.get("has_more") else None
                    lines = line_items.auto_paging_iter() if line_items else items.get("data", [])
                    for raw_item in lines:
                        item = raw_item.to_dict() if hasattr(raw_item, "to_dict") else raw_item
                        if item.get("price", {}).get("id") == self.price_id and (item.get("quantity") or 0) > 0:
                            return Entitlement(True, customer["id"])
            return Entitlement()
        except Exception as exc:
            # Fail closed. Do not expose SDK exceptions which can contain email/API details.
            raise BillingUnavailable("Subscription verification is temporarily unavailable. Please retry.") from exc

    def portal(self, customer_id, return_url):
        try:
            return self.client.v1.billing_portal.sessions.create({"customer": customer_id, "return_url": return_url}).url
        except Exception as exc:
            raise BillingUnavailable("Billing management is unavailable. Please contact support.") from exc
