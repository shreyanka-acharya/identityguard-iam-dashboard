from seed_data import seed_enterprise, enterprise_summary, enterprise_table
from iam import identities

def test_synthetic_enterprise_seed_is_repeatable(tmp_path):
    db = tmp_path / 'enterprise.db'
    assert seed_enterprise(db, count=25) is True
    assert seed_enterprise(db, count=25) is False
    people = identities(db)
    assert len(people) == 29  # 4 starter identities + 25 synthetic
    assert sum(p['email'].endswith('@identityguard.example') for p in people) == 25
    summary = enterprise_summary(db)
    assert summary['applications'] == 12
    assert summary['assignments'] >= 50
    assert len(enterprise_table('requests',db)) == 7
