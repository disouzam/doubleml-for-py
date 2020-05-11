import numpy as np
import pytest
import math

from sklearn.base import clone

from sklearn.linear_model import LogisticRegression, LinearRegression

import doubleml.api as dml

from doubleml.tests.helper_general import get_n_datasets
from doubleml.tests.helper_pyvsr import export_smpl_split_to_r, r_IIVM

from rpy2.robjects import pandas2ri
pandas2ri.activate()

# number of datasets per dgp
n_datasets = get_n_datasets()

@pytest.fixture(scope='module',
                params = range(n_datasets))
def idx(request):
    return request.param


@pytest.fixture(scope='module',
                params = ['LATE'])
def inf_model(request):
    return request.param


@pytest.fixture(scope='module',
                params = ['dml1', 'dml2'])
def dml_procedure(request):
    return request.param


@pytest.fixture(scope="module")
def dml_iivm_pyvsr_fixture(generate_data_iivm, idx, inf_model, dml_procedure):
    boot_methods = ['normal']
    n_folds = 2

    # collect data
    data = generate_data_iivm[idx]
    X_cols = data.columns[data.columns.str.startswith('X')].tolist()

    # Set machine learning methods for m & gg
    learner_classif = LogisticRegression(penalty='none', solver='newton-cg')
    learner_reg = LinearRegression()
    ml_learners = {'ml_m': clone(learner_classif),
                   'ml_g': clone(learner_reg),
                   'ml_r': clone(learner_classif)}
    
    dml_iivm_obj = dml.DoubleMLIIVM(data, X_cols, 'y', ['d'], 'z',
                                ml_learners,
                                n_folds,
                                dml_procedure=dml_procedure)

    np.random.seed(3141)
    dml_iivm_obj.fit()

    # fit the DML model in R
    all_train, all_test = export_smpl_split_to_r(dml_iivm_obj.smpls[0])

    r_dataframe = pandas2ri.py2rpy(data)
    res_r = r_IIVM(r_dataframe, inf_model, dml_procedure,
                   all_train, all_test)

    res_dict = {'coef_py': dml_iivm_obj.coef,
                'coef_r': res_r[0],
                'se_py': dml_iivm_obj.se,
                'se_r': res_r[1]}

    return res_dict


def test_dml_iivm_pyvsr_coef(dml_iivm_pyvsr_fixture):
    assert math.isclose(dml_iivm_pyvsr_fixture['coef_py'],
                        dml_iivm_pyvsr_fixture['coef_r'],
                        rel_tol=1e-4, abs_tol=1e-1)


def test_dml_iivm_pyvsr_se(dml_iivm_pyvsr_fixture):
    assert math.isclose(dml_iivm_pyvsr_fixture['se_py'],
                        dml_iivm_pyvsr_fixture['se_r'],
                        rel_tol=1e-4, abs_tol=1e-1)
