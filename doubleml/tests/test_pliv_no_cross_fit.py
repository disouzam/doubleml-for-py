import numpy as np
import pytest
import math

from sklearn.model_selection import KFold
from sklearn.base import clone

from sklearn.ensemble import RandomForestRegressor

import doubleml as dml

from ._utils_pliv_manual import pliv_dml1, fit_nuisance_pliv, boot_pliv


@pytest.fixture(scope='module',
                params=[RandomForestRegressor(max_depth=2, n_estimators=10)])
def learner(request):
    return request.param


@pytest.fixture(scope='module',
                params=['partialling out'])
def score(request):
    return request.param


@pytest.fixture(scope='module',
                params=[1, 2])
def n_folds(request):
    return request.param


@pytest.fixture(scope='module')
def dml_pliv_no_cross_fit_fixture(generate_data_iv, learner, score, n_folds):
    boot_methods = ['normal']
    n_rep_boot = 503
    dml_procedure = 'dml1'

    # collect data
    data = generate_data_iv
    x_cols = data.columns[data.columns.str.startswith('X')].tolist()

    # Set machine learning methods for g, m & r
    ml_g = clone(learner)
    ml_m = clone(learner)
    ml_r = clone(learner)

    np.random.seed(3141)
    obj_dml_data = dml.DoubleMLData(data, 'y', ['d'], x_cols, 'Z1')
    dml_pliv_obj = dml.DoubleMLPLIV(obj_dml_data,
                                    ml_g, ml_m, ml_r,
                                    n_folds,
                                    dml_procedure=dml_procedure,
                                    apply_cross_fitting=False)

    dml_pliv_obj.fit()

    np.random.seed(3141)
    y = data['y'].values
    x = data.loc[:, x_cols].values
    d = data['d'].values
    z = data['Z1'].values
    if n_folds == 1:
        smpls = [(np.arange(len(y)), np.arange(len(y)))]
    else:
        resampling = KFold(n_splits=n_folds,
                           shuffle=True)
        smpls = [(train, test) for train, test in resampling.split(x)]
        smpls = [smpls[0]]

    g_hat, m_hat, r_hat = fit_nuisance_pliv(y, x, d, z,
                                            clone(learner), clone(learner), clone(learner),
                                            smpls)

    assert dml_procedure == 'dml1'
    res_manual, se_manual = pliv_dml1(y, x, d,
                                      z,
                                      g_hat, m_hat, r_hat,
                                      smpls, score)

    res_dict = {'coef': dml_pliv_obj.coef,
                'coef_manual': res_manual,
                'se': dml_pliv_obj.se,
                'se_manual': se_manual,
                'boot_methods': boot_methods}

    for bootstrap in boot_methods:
        np.random.seed(3141)
        boot_theta, boot_t_stat = boot_pliv(res_manual,
                                            y, d,
                                            z,
                                            g_hat, m_hat, r_hat,
                                            smpls, score,
                                            se_manual,
                                            bootstrap, n_rep_boot,
                                            apply_cross_fitting=False)

        np.random.seed(3141)
        dml_pliv_obj.bootstrap(method=bootstrap, n_rep_boot=n_rep_boot)
        res_dict['boot_coef' + bootstrap] = dml_pliv_obj.boot_coef
        res_dict['boot_t_stat' + bootstrap] = dml_pliv_obj.boot_t_stat
        res_dict['boot_coef' + bootstrap + '_manual'] = boot_theta
        res_dict['boot_t_stat' + bootstrap + '_manual'] = boot_t_stat

    return res_dict


@pytest.mark.ci
def test_dml_pliv_no_cross_fit_coef(dml_pliv_no_cross_fit_fixture):
    assert math.isclose(dml_pliv_no_cross_fit_fixture['coef'],
                        dml_pliv_no_cross_fit_fixture['coef_manual'],
                        rel_tol=1e-9, abs_tol=1e-4)


@pytest.mark.ci
def test_dml_pliv_no_cross_fit_se(dml_pliv_no_cross_fit_fixture):
    assert math.isclose(dml_pliv_no_cross_fit_fixture['se'],
                        dml_pliv_no_cross_fit_fixture['se_manual'],
                        rel_tol=1e-9, abs_tol=1e-4)


@pytest.mark.ci
def test_dml_pliv_no_cross_fit_boot(dml_pliv_no_cross_fit_fixture):
    for bootstrap in dml_pliv_no_cross_fit_fixture['boot_methods']:
        assert np.allclose(dml_pliv_no_cross_fit_fixture['boot_coef' + bootstrap],
                           dml_pliv_no_cross_fit_fixture['boot_coef' + bootstrap + '_manual'],
                           rtol=1e-9, atol=1e-4)
        assert np.allclose(dml_pliv_no_cross_fit_fixture['boot_t_stat' + bootstrap],
                           dml_pliv_no_cross_fit_fixture['boot_t_stat' + bootstrap + '_manual'],
                           rtol=1e-9, atol=1e-4)