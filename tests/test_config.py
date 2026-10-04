from pathlib import Path

import pytest
import yaml

from xqi.config import ConfigError, load, load_causes

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "default.yaml"


def test_default_config_loads():
    cfg = load(DEFAULT_CONFIG)

    assert cfg.mode == "advisory"
    assert cfg.printer.nominal["nozzle_temp"] == 210
    assert cfg.envelope.L3.material == "PLA"


def test_config_is_frozen():
    cfg = load(DEFAULT_CONFIG)

    with pytest.raises(AttributeError):
        cfg.mode = "auto"


def _write_config(tmp_path, mutate):
    with DEFAULT_CONFIG.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    mutate(data)

    path = tmp_path / "config.yaml"
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle)

    return path


def test_missing_var_key_raises(tmp_path):
    path = _write_config(
        tmp_path,
        lambda data: data["correction"]["d_max"].pop("flow"),
    )

    with pytest.raises(ConfigError, match=r"correction\.d_max\.flow"):
        load(path)


def test_d_max_greater_than_step_raises(tmp_path):
    path = _write_config(
        tmp_path,
        lambda data: data["correction"]["d_max"].update(
            {"flow": 11}
        ),
    )

    with pytest.raises(ConfigError, match=r"correction\.d_max\.flow"):
        load(path)


def test_l3_outside_l1_raises(tmp_path):
    path = _write_config(
        tmp_path,
        lambda data: data["envelope"]["L3"]["window"].update(
            {"flow": [40, 110]}
        ),
    )

    with pytest.raises(
        ConfigError,
        match=r"envelope\.L3\.window\.flow",
    ):
        load(path)


def test_zero_hits_raises(tmp_path):
    path = _write_config(
        tmp_path,
        lambda data: data["confirm"]["hits"].update(
            {"clog": 0}
        ),
    )

    with pytest.raises(
        ConfigError,
        match=r"confirm\.hits\.clog",
    ):
        load(path)


def test_bad_mode_raises(tmp_path):
    path = _write_config(
        tmp_path,
        lambda data: data.update({"mode": "invalid"}),
    )

    with pytest.raises(ConfigError, match=r"mode"):
        load(path)


def test_bad_critical_action_raises(tmp_path):
    path = _write_config(
        tmp_path,
        lambda data: data["critical"].update(
            {"clog": "noop"}
        ),
    )

    with pytest.raises(
        ConfigError,
        match=r"critical\.clog",
    ):
        load(path)


CAUSES_FILE = ROOT / "config" / "causes.yaml"


def test_causes_yaml_matches_type_defaults():
    from xqi import types

    causes = load_causes(load(DEFAULT_CONFIG).causes_file)

    assert causes.causes == types.CAUSES
    assert causes.cause_action == types.CAUSE_ACTION
    assert causes.cause_defects == {
        k: tuple(v) for k, v in types.CAUSE_DEFECTS.items()
    }
    assert causes.deck_recipes == types.DECK_RECIPES


def _write_causes(tmp_path, mutate):
    with CAUSES_FILE.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    mutate(data)

    path = tmp_path / "causes.yaml"
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle)

    return path


def test_causes_action_for_unknown_cause_raises(tmp_path):
    path = _write_causes(
        tmp_path,
        lambda data: data["cause_action"].update({"glue_low": None}),
    )

    with pytest.raises(ConfigError, match=r"cause_action\.glue_low"):
        load_causes(path)


def test_causes_bad_var_raises(tmp_path):
    path = _write_causes(
        tmp_path,
        lambda data: data["cause_action"].update({"flow_low": ["flux", -1]}),
    )

    with pytest.raises(ConfigError, match=r"cause_action\.flow_low"):
        load_causes(path)


def test_causes_unknown_defect_raises(tmp_path):
    path = _write_causes(
        tmp_path,
        lambda data: data["cause_defects"].update({"flow_low": ["blob"]}),
    )

    with pytest.raises(ConfigError, match=r"cause_defects\.flow_low"):
        load_causes(path)
