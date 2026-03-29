from sparam.monitor_state import MonitorState


def test_monitor_state_add_remove_and_series_index() -> None:
    state = MonitorState()

    assert state.add_monitored("speed")
    assert not state.add_monitored("speed")
    assert state.add_monitored("current")

    assert state.monitored_names == ["speed", "current"]
    assert state.series_index("speed") == 0
    assert state.series_index("current") == 1
    assert state.series_index("voltage") == 2

    assert state.remove_monitored("speed")
    assert not state.remove_monitored("speed")
    assert state.monitored_names == ["current"]


def test_monitor_state_pause_and_reset() -> None:
    state = MonitorState(monitored_names=["speed"], active=True, paused=False)

    assert state.toggle_paused() is True
    assert state.toggle_paused() is False

    state.stop_streaming()
    assert state.active is False

    state.reset()
    assert state.monitored_names == []
    assert state.active is False
    assert state.paused is False
