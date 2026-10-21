from gate_sim import AUTO_CLOSE_AFTER_PASS_S, AUTO_CLOSE_TIMEOUT_S, MAX_REVERSALS, MOVE_S, GateSim


class Clock:
    t = 0.0

    def __call__(self):
        return self.t


def make():
    c = Clock()
    return GateSim("ENTRANCE", c), c


def run(g, c, seconds, step=0.1):
    end = c.t + seconds
    while c.t < end:
        c.t += step
        g.tick()


def test_open_pass_autoclose():
    g, c = make()
    g.command("OPEN", "r1")
    ack = g.drain()[0]
    assert (ack.state, ack.request_id, ack.success) == ("OPENING", "r1", True)
    run(g, c, MOVE_S + 0.1)
    assert g.state == "OPEN"
    g.set_vehicle(True)
    g.set_vehicle(False)
    run(g, c, AUTO_CLOSE_AFTER_PASS_S + 0.1)
    assert g.state == "CLOSING"
    run(g, c, MOVE_S + 0.1)
    assert g.state == "CLOSED"


def test_autoclose_timeout_without_vehicle():
    g, c = make()
    g.command("OPEN", "r1")
    run(g, c, MOVE_S + AUTO_CLOSE_TIMEOUT_S + 0.3)
    assert g.state in ("CLOSING", "CLOSED")


def test_close_refused_with_vehicle_under_barrier():
    g, c = make()
    g.command("OPEN", "r1")
    run(g, c, MOVE_S + 0.1)
    g.set_vehicle(True)
    g.drain()
    g.command("CLOSE", "r2")
    ev = g.drain()[0]
    assert not ev.success and ev.reason == "VEHICLE_PRESENT" and g.state == "OPEN"
    run(g, c, AUTO_CLOSE_TIMEOUT_S + 1)
    assert g.state == "OPEN"  # never closes on a car


def test_safety_reopen_and_error_after_reversals():
    g, c = make()
    g.command("OPEN", "r1")
    run(g, c, MOVE_S + AUTO_CLOSE_TIMEOUT_S + 0.2)
    for i in range(MAX_REVERSALS):
        assert g.state == "CLOSING"
        g.set_vehicle(True)
        if i < MAX_REVERSALS - 1:
            assert g.state == "OPENING"
            g.set_vehicle(False)
            run(g, c, MOVE_S + AUTO_CLOSE_TIMEOUT_S + 0.2)
    assert g.state == "ERROR"
    g.drain()
    g.command("OPEN", "r9")
    assert g.drain()[0].reason == "ERROR_STATE"
    g.command("RESET", "r10")
    assert g.state == "OPEN"


def test_duplicate_request_not_executed_twice():
    g, c = make()
    g.command("OPEN", "r1")
    run(g, c, MOVE_S + 0.1)
    g.drain()
    g.command("CLOSE", "r2")
    g.command("CLOSE", "r2")
    evs = g.drain()
    assert evs[-1].reason == "DUPLICATE" and evs[-1].success


def test_button_opens():
    g, c = make()
    g.button()
    assert g.drain()[0].source == "BUTTON"
