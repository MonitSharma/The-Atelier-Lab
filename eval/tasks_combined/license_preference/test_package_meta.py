from package_meta import package_license


def test_package_uses_user_preferred_license():
    assert package_license() == "Apache-2.0"
