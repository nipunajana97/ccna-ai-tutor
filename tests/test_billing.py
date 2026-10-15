from types import SimpleNamespace
import pytest
from tutor.billing import BillingUnavailable, StripeBilling


class Obj(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc


class Page:
    def __init__(self, data):
        self.data = data
    def auto_paging_iter(self):
        yield from self.data


def billing(subs, customers=None, items=None, throw=False):
    def list_customers(params):
        if throw:
            raise RuntimeError("private API error")
        assert params["email"] == "learner@example.com"
        return Page(customers if customers is not None else [Obj(id="cus_1", email="learner@example.com", livemode=False)])
    client = SimpleNamespace(v1=SimpleNamespace(
        customers=SimpleNamespace(list=list_customers),
        subscriptions=SimpleNamespace(list=lambda params: Page(subs)),
        subscription_items=SimpleNamespace(list=lambda params: Page(items or []))))
    return StripeBilling("not-used", "price_correct", client=client)


def subscription(status="active", price="price_correct", live=False, more=False):
    return Obj(id="sub_1", status=status, livemode=live,
               latest_invoice={"status": "paid"},
               items={"data": [{"price": {"id": price}, "quantity": 1}], "has_more": more})


def test_exact_active_test_subscription_unlocks():
    result = billing([subscription()]).entitlement("learner@example.com")
    assert result.active and result.customer_id == "cus_1"


@pytest.mark.parametrize("sub", [subscription("canceled"), subscription("past_due"), subscription("unpaid"),
                               subscription("trialing"), subscription("incomplete"), subscription(price="price_other"),
                               subscription(live=True)])
def test_wrong_status_price_or_mode_cannot_unlock(sub):
    assert not billing([sub]).entitlement("learner@example.com").active


def test_no_customers_or_different_email_cannot_unlock():
    assert not billing([], customers=[]).entitlement("learner@example.com").active
    assert not billing([subscription()], customers=[Obj(id="stolen", email="other@example.com", livemode=False)]).entitlement("learner@example.com").active


def test_customer_and_subscription_pagination():
    customers = [Obj(id="old", email="learner@example.com", livemode=False), Obj(id="new", email="learner@example.com", livemode=False)]
    result = billing([subscription(price="wrong"), subscription(more=True)], customers,
                     [{"price": {"id": "price_correct"}, "quantity": 1}]).entitlement("learner@example.com")
    assert result.active


def test_api_failure_is_closed_and_sanitized():
    with pytest.raises(BillingUnavailable) as error:
        billing([], throw=True).entitlement("learner@example.com")
    assert "private" not in str(error.value)


def test_active_but_unpaid_invoice_cannot_unlock():
    sub = subscription()
    sub["latest_invoice"] = {"status": "open"}
    assert not billing([sub]).entitlement("learner@example.com").active


def test_real_stripe_sdk_decodes_subscription_and_expands_invoice(monkeypatch):
    import json
    from stripe import StripeClient, RequestsClient
    requests = []
    transport = RequestsClient()
    def respond(method, url, headers, post_data=None, **kwargs):
        requests.append(url)
        if "/v1/customers" in url:
            data = [{"object": "customer", "id": "cus_real_sdk", "email": "learner@example.com", "livemode": False}]
        elif "/v1/subscriptions" in url:
            data = [{"object": "subscription", "id": "sub_sdk", "status": "active", "livemode": False,
                     "latest_invoice": {"object": "invoice", "id": "in_sdk", "status": "paid"},
                     "items": {"object": "list", "data": [{"object": "subscription_item", "id": "si_sdk", "quantity": 1,
                                                            "price": {"object": "price", "id": "price_correct"}}], "has_more": False}}]
        else:
            raise AssertionError(url)
        return json.dumps({"object": "list", "data": data, "has_more": False, "url": url}), 200, {}
    monkeypatch.setattr(transport, "request", respond)
    client = StripeClient("sk_test_unused", http_client=transport)
    assert StripeBilling("unused", "price_correct", client=client).entitlement("learner@example.com").active
    assert any("latest_invoice" in url for url in requests)
