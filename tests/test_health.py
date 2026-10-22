"""/health names the running commit, so the post-deploy smoke test can prove which code is live."""


def test_health_reports_the_deployed_commit(client, monkeypatch):
    monkeypatch.setenv(
        "RAILWAY_GIT_COMMIT_SHA", "c267efdd13144882b2575095c6d95034032a7310"
    )
    body = client.get("/health").json()
    assert body == {
        "status": "ok",
        "commit": "c267efdd13144882b2575095c6d95034032a7310",
    }


def test_health_without_a_git_deploy_reports_no_commit(client, monkeypatch):
    monkeypatch.delenv("RAILWAY_GIT_COMMIT_SHA", raising=False)
    assert client.get("/health").json() == {"status": "ok", "commit": None}
