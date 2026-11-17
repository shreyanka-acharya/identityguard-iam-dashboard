import pytest
from iam import initialize, identities, events, joiner, mover, leaver, access_findings

def test_jml_and_audit(tmp_path):
    db=tmp_path/'test.db'
    initialize(db)
    user_id=joiner('Test User','TEST@example.test','Support','Employee',db)
    assert any(p['id']==user_id for p in identities(db))
    mover(user_id,'Security','Administrator',db)
    assert any(p['id']==user_id for p in access_findings(db))
    leaver(user_id,db)
    assert not any(p['id']==user_id for p in access_findings(db))
    assert [e['action'] for e in events(db)[:3]] == ['LEAVER','MOVER','JOINER']
    with pytest.raises(ValueError):
        mover(user_id,'HR','Viewer',db)
