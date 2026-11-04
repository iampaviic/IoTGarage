// Unit tests of the gate state machine, run on the PC:  pio test -e native
#include <unity.h>
#include "GateController.h"

static uint32_t now;
static GateTiming timing() { return GateTiming(); }

static void run(GateController& g, uint32_t ms) {
    for (uint32_t end = now + ms; now < end; now += 50) g.tick(now);
}

static GateEvent last(GateController& g) {
    GateEvent e{}, tmp;
    while (g.popEvent(tmp)) e = tmp;
    return e;
}

void setUp() { now = 1000; }
void tearDown() {}

void test_open_pass_autoclose() {
    GateController g(timing());
    g.command("OPEN", "r1", "MQTT", now);
    GateEvent ack;
    TEST_ASSERT_TRUE(g.popEvent(ack));
    TEST_ASSERT_EQUAL_STRING("r1", ack.requestId);
    TEST_ASSERT_TRUE(ack.success);
    TEST_ASSERT_EQUAL(GateState::Opening, ack.state);
    run(g, 1100);
    TEST_ASSERT_EQUAL(GateState::Open, g.state());
    g.setVehicle(true, now);
    g.setVehicle(false, now);
    run(g, 2100);
    TEST_ASSERT_EQUAL(GateState::Closing, g.state());
    run(g, 1100);
    TEST_ASSERT_EQUAL(GateState::Closed, g.state());
}

void test_autoclose_timeout() {
    GateController g(timing());
    g.command("OPEN", "r1", "MQTT", now);
    run(g, 1000 + 10000 + 200);
    TEST_ASSERT_TRUE(g.state() == GateState::Closing || g.state() == GateState::Closed);
}

void test_never_closes_on_vehicle() {
    GateController g(timing());
    g.command("OPEN", "r1", "MQTT", now);
    run(g, 1100);
    g.setVehicle(true, now);
    last(g);
    g.command("CLOSE", "r2", "MQTT", now);
    GateEvent e = last(g);
    TEST_ASSERT_FALSE(e.success);
    TEST_ASSERT_EQUAL_STRING("VEHICLE_PRESENT", e.reason);
    run(g, 20000);
    TEST_ASSERT_EQUAL(GateState::Open, g.state());
}

void test_safety_reverse_then_error_then_reset() {
    GateController g(timing());
    g.command("OPEN", "r1", "MQTT", now);
    run(g, 11200);
    for (int i = 0; i < 3; i++) {
        TEST_ASSERT_EQUAL(GateState::Closing, g.state());
        g.setVehicle(true, now);
        if (i < 2) {
            TEST_ASSERT_EQUAL(GateState::Opening, g.state());
            g.setVehicle(false, now);
            run(g, 11200);
        }
    }
    TEST_ASSERT_EQUAL(GateState::Error, g.state());
    TEST_ASSERT_TRUE(g.targetOpen());  // error: barrier stays up
    last(g);
    g.command("OPEN", "r9", "MQTT", now);
    TEST_ASSERT_EQUAL_STRING("ERROR_STATE", last(g).reason);
    g.command("RESET", "r10", "MQTT", now);
    TEST_ASSERT_EQUAL(GateState::Open, g.state());
}

void test_duplicate_request() {
    GateController g(timing());
    g.command("OPEN", "r1", "MQTT", now);
    run(g, 1100);
    last(g);
    g.command("CLOSE", "r2", "MQTT", now);
    g.command("CLOSE", "r2", "MQTT", now);
    GateEvent e = last(g);
    TEST_ASSERT_EQUAL_STRING("DUPLICATE", e.reason);
    TEST_ASSERT_TRUE(e.success);
}

void test_invalid_command_and_button() {
    GateController g(timing());
    g.command("FLY", "r1", "MQTT", now);
    TEST_ASSERT_EQUAL_STRING("INVALID_COMMAND", last(g).reason);
    g.button(now);
    GateEvent e = last(g);
    TEST_ASSERT_EQUAL_STRING("BUTTON", e.source);
    TEST_ASSERT_EQUAL(GateState::Opening, e.state);
}

void test_dead_gate_does_not_answer() {
    GateController g(timing());
    g.setAckEnabled(false);
    g.command("OPEN", "r1", "MQTT", now);
    GateEvent e;
    TEST_ASSERT_FALSE(g.popEvent(e));
}

int main(int, char**) {
    UNITY_BEGIN();
    RUN_TEST(test_open_pass_autoclose);
    RUN_TEST(test_autoclose_timeout);
    RUN_TEST(test_never_closes_on_vehicle);
    RUN_TEST(test_safety_reverse_then_error_then_reset);
    RUN_TEST(test_duplicate_request);
    RUN_TEST(test_invalid_command_and_button);
    RUN_TEST(test_dead_gate_does_not_answer);
    return UNITY_END();
}
