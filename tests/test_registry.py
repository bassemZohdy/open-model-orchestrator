import json

from omo.registry import Registry, RegistryStore


def test_registry_status_reports_freshness_and_last_known_good(tmp_path, entry):
    path = tmp_path / "registry.yaml"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "version": "new",
                "models": [entry.model_dump()],
            }
        )
    )
    store = RegistryStore(Registry(version="old"), source_path=str(path))
    before = store.snapshot
    assert store.try_reload(str(path)) is True
    assert store.snapshot.version == "new"
    assert store.status(60)["fresh"] is True

    path.write_text('{"version":"invalid","models":[{"id":"broken"}]}')
    assert store.try_reload(str(path)) is False
    assert store.snapshot.version == "new"
    assert store.status(60)["last_reload_error"] is not None
    assert before.version == "old"
