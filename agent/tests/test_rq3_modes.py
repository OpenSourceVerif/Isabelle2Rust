"""Protect mode selection and relative-runtime direction in cross-language reports."""
import importlib.util
from pathlib import Path
import pytest

@pytest.fixture
def controller():
    path=Path(__file__).resolve().parents[1]/'scripts/measure_rq3.py'
    spec=importlib.util.spec_from_file_location('rq3_measure_test',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

@pytest.mark.parametrize('mode',['rust-only','full'])
def test_selected_mode_is_bootstrap_denominator(controller,mode):
    controller.RUST_ID=mode+'-arbitrary'
    controller.IMPLEMENTATIONS=(controller.RUST_ID,*controller.REFERENCES)
    medians={controller.RUST_ID:[2.]*10,**{r:[6.]*10 for r in controller.REFERENCES}}
    _,ratios=controller.workload_bootstrap('case','input',medians,replicates=30)
    assert all(values==[3.]*30 for values in ratios.values())
    assert all(controller.RUST_ID in order for order in controller.order_design())

def test_mixed_or_missing_rust_mode_rejected(controller):
    controller.RUST_ID='rust-only-arbitrary'
    controller.IMPLEMENTATIONS=(controller.RUST_ID,*controller.REFERENCES)
    with pytest.raises(controller.Failure):
        controller.workload_bootstrap('case','input',{'full-arbitrary':[2.]*10,**{r:[6.]*10 for r in controller.REFERENCES}},replicates=3)
