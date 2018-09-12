
from pytest_bdd import scenario, given, when, then

import pytest
import os


@pytest.fixture
def pytestbdd_feature_base_dir():
    return os.path.join(os.getcwd(), "features")


@scenario("maya_publish.feature",
          "model mesh is triangulate")
def test_app_startup():
    pass


@given('a model which has triangulated faces')
def step_impl_given_tri_face():
    pass


@given('a model which has multiple shape nodes')
def step_impl_given_multi_shape():
    pass


@when('the artist want to publish it')
def step_impl_when():
    pass


@then('Pyblish will block with quadrangular validation fail')
def step_impl_then_fail_with_quad_validation():
    pass


@then('Pyblish will block with single shape validation fail')
def step_impl_then_fail_with_shape_validation():
    pass
