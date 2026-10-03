from app.config import Settings


def test_admin_roles_parsed_into_list():
    assert Settings(admin_roles="admin,HR, LEGAL").admin_role_list == ["admin", "HR", "LEGAL"]


def test_defaults_are_usable_without_env_file():
    settings = Settings(_env_file=None)
    assert settings.embedding_dim == 1536
    assert settings.top_k >= 1
