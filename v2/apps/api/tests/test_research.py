import numpy as np
import pandas as pd
import pytest
from research.evaluate import features,evaluate

def test_features_do_not_look_forward():
    p=pd.Series(np.linspace(100,200,500))
    x,_=features(p,5)
    changed=p.copy();changed.iloc[301:]*=2
    other,_=features(changed,5)
    pd.testing.assert_frame_equal(x.iloc[:301],other.iloc[:301])

def test_walk_forward_purges_unobserved_targets():
    # Synthetic TEST fixture; never published as financial evaluation evidence.
    rng=np.random.default_rng(3)
    frame=pd.DataFrame({'date':pd.bdate_range('2020-01-01',periods=440),'adjusted_close':100*np.exp(np.cumsum(rng.normal(0,.01,440)))})
    r=evaluate(frame,20,'synthetic-unit-test-only')
    assert r['deployment_eligible'] is False
    assert r['probabilities'] is None
    assert all(f['training_last_target_index']<f['test_first_index'] for f in r['folds'])
    assert set(r['metrics'])=={'hist_gradient_boosting','no_change','trailing_mean_return'}
    with pytest.raises(ValueError):evaluate(frame.iloc[::-1],1,'test')
