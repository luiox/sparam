from sparam.monitor_store import MonitorStore


def test_monitor_store_keeps_latest_points_with_ring_buffer_limit() -> None:
    store = MonitorStore(max_points=3)

    store.append("motor_speed", 1.0, 10.0)
    store.append("motor_speed", 2.0, 20.0)
    store.append("motor_speed", 3.0, 30.0)
    store.append("motor_speed", 4.0, 40.0)

    series = store.series("motor_speed")

    assert series.timestamps == [2.0, 3.0, 4.0]
    assert series.values == [20.0, 30.0, 40.0]
    assert store.latest_value("motor_speed") == 40.0


def test_monitor_store_exports_rows_in_timestamp_order() -> None:
    store = MonitorStore(max_points=5)

    store.append("speed", 1.0, 100.0)
    store.append("current", 1.5, 20.0)
    store.append("speed", 2.0, 110.0)

    assert store.export_rows() == [
        (1.0, "speed", 100.0),
        (1.5, "current", 20.0),
        (2.0, "speed", 110.0),
    ]
