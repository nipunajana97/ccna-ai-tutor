from concurrent.futures import ThreadPoolExecutor
import pytest
from tutor.identity import IdentityError, verified_identity
from tutor.store import AccessDenied, UsageStore


def claims(**overrides):
    return {"iss": "https://accounts.google.com", "sub": "unique-subject", "email": "Learner@Example.com",
            "email_verified": True, "exp": 2000, **overrides}


def test_verified_identity_is_stable():
    identity = verified_identity(claims(), now=1000)
    assert identity.email == "learner@example.com"
    assert len(identity.user_id) == 64
    assert identity.user_id == verified_identity(claims(iss="accounts.google.com"), now=1000).user_id


@pytest.mark.parametrize("override", [{"email_verified": False}, {"email_verified": "true"},
                                     {"iss": "https://attacker.invalid"}, {"sub": ""}, {"exp": 999}, {"email": ""}])
def test_invalid_identities_do_not_get_access(override):
    with pytest.raises(IdentityError):
        verified_identity(claims(**override), now=1000)


def test_one_trial_survives_restart_and_failed_retry(tmp_path):
    path = tmp_path / "usage.db"
    store = UsageStore(path, cooldown_seconds=0)
    first = store.reserve("learner", False)
    store.fail(first, "learner")
    second = store.reserve("learner", False)
    store.complete(second, "learner", {"scenario": "saved"})
    fresh = UsageStore(path, cooldown_seconds=0)
    assert fresh.trial_used("learner")
    assert fresh.latest_scenario("learner")["id"] == second
    with pytest.raises(AccessDenied, match="free scenario"):
        fresh.reserve("learner", False)


def test_parallel_browser_tabs_cannot_reserve_multiple_trials(tmp_path):
    store = UsageStore(tmp_path / "quota.db", cooldown_seconds=0)
    def attempt(_):
        try:
            return store.reserve("same-account", False)
        except AccessDenied:
            return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(attempt, range(16)))
    assert sum(value is not None for value in results) == 1


def test_expired_pending_request_does_not_lock_account_forever(tmp_path):
    store = UsageStore(tmp_path / "quota.db", cooldown_seconds=0)
    old = store.reserve("u", False, now=1000)
    new = store.reserve("u", False, now=1601)
    with pytest.raises(AccessDenied):
        store.complete(old, "u")
    store.complete(new, "u")
    assert store.trial_used("u")


def test_subscriber_allowed_then_cancellation_blocks_new_requests(tmp_path):
    store = UsageStore(tmp_path / "quota.db", cooldown_seconds=0)
    request = store.reserve("u", False)
    store.complete(request, "u")
    request = store.reserve("u", True, "chat")
    store.complete(request, "u")
    with pytest.raises(AccessDenied):
        store.reserve("u", False)


def test_chat_not_available_as_free_trial(tmp_path):
    with pytest.raises(AccessDenied):
        UsageStore(tmp_path / "quota.db").reserve("u", False, "chat")


def test_ownership_and_single_answer(tmp_path):
    store = UsageStore(tmp_path / "quota.db", cooldown_seconds=0)
    request = store.reserve("owner", False)
    with pytest.raises(AccessDenied):
        store.complete(request, "other", {"scenario": "stolen"})
    store.complete(request, "owner", {"scenario": "own"})
    assert store.latest_scenario("other") is None
    store.answer(request, "other", 1)
    assert store.latest_scenario("owner")["selected_answer"] is None
    store.answer(request, "owner", 2)
    store.answer(request, "owner", 3)
    assert store.latest_scenario("owner")["selected_answer"] == 2


def test_usage_limits_and_utc_reset(tmp_path):
    store = UsageStore(tmp_path / "quota.db", daily_limit=1, global_daily_limit=2, cooldown_seconds=0)
    first = store.reserve("a", True, now=1000)
    store.fail(first, "a")  # failed attempts still count toward the cost ceiling
    with pytest.raises(AccessDenied, match="practice limit"):
        store.reserve("a", True, now=1001)
    second = store.reserve("b", True, now=1001)
    store.complete(second, "b")
    with pytest.raises(AccessDenied, match="service limit"):
        store.reserve("c", True, now=1002)
    assert store.reserve("a", True, now=86401)
