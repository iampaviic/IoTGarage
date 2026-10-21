// Unit tests of the spot filter, run on the PC:  pio test -e native
#include <unity.h>
#include "OccupancyFilter.h"

static FilterConfig cfg() {
    FilterConfig c;
    c.occupiedBelowCm = 10.0f;
    c.freeAboveCm = 12.0f;
    c.confirmCount = 3;
    c.maxInvalid = 5;
    return c;
}

static int feed(OccupancyFilter& f, float d, int n) {
    int changes = 0;
    for (int i = 0; i < n; i++) changes += f.update(d) ? 1 : 0;
    return changes;
}

void setUp() {}
void tearDown() {}

void test_starts_unknown_then_free() {
    OccupancyFilter f(cfg());
    TEST_ASSERT_EQUAL(SpotState::Unknown, f.state());
    feed(f, 14.0f, 10);
    TEST_ASSERT_EQUAL(SpotState::Free, f.state());
    TEST_ASSERT_EQUAL_STRING("FREE", f.stateName());
}

void test_car_arrives_and_leaves() {
    OccupancyFilter f(cfg());
    feed(f, 14.0f, 10);
    feed(f, 6.5f, 10);
    TEST_ASSERT_EQUAL(SpotState::Occupied, f.state());
    feed(f, 14.0f, 10);
    TEST_ASSERT_EQUAL(SpotState::Free, f.state());
}

void test_single_spike_is_ignored() {
    OccupancyFilter f(cfg());
    feed(f, 14.0f, 10);
    TEST_ASSERT_EQUAL(0, feed(f, 3.0f, 1));   // one bad echo
    TEST_ASSERT_EQUAL(0, feed(f, 14.0f, 5));
    TEST_ASSERT_EQUAL(SpotState::Free, f.state());
}

void test_hysteresis_band_does_not_flicker() {
    OccupancyFilter f(cfg());
    feed(f, 6.0f, 10);
    TEST_ASSERT_EQUAL(SpotState::Occupied, f.state());
    // values between 10 and 12 cm: keep OCCUPIED, no state changes at all
    int changes = 0;
    for (int i = 0; i < 50; i++) changes += f.update(i % 2 ? 10.5f : 11.5f) ? 1 : 0;
    TEST_ASSERT_EQUAL(0, changes);
    TEST_ASSERT_EQUAL(SpotState::Occupied, f.state());
}

void test_needs_confirmation_before_switching() {
    OccupancyFilter f(cfg());
    feed(f, 14.0f, 10);
    // median needs a majority of new values first, then 3 confirmations
    TEST_ASSERT_EQUAL(0, feed(f, 6.0f, 3));
    TEST_ASSERT_EQUAL(SpotState::Free, f.state());
    feed(f, 6.0f, 3);
    TEST_ASSERT_EQUAL(SpotState::Occupied, f.state());
}

void test_no_echo_becomes_unknown_and_recovers() {
    OccupancyFilter f(cfg());
    feed(f, 14.0f, 10);
    feed(f, 0.0f, 4);
    TEST_ASSERT_EQUAL(SpotState::Free, f.state());  // a few lost echoes are tolerated
    feed(f, 0.0f, 1);
    TEST_ASSERT_EQUAL(SpotState::Unknown, f.state());
    TEST_ASSERT_EQUAL_STRING("TIMEOUT", f.statusName());
    feed(f, 6.0f, 10);
    TEST_ASSERT_EQUAL(SpotState::Occupied, f.state());
    TEST_ASSERT_EQUAL_STRING("OK", f.statusName());
}

void test_out_of_range_is_reported() {
    OccupancyFilter f(cfg());
    feed(f, 300.0f, 5);
    TEST_ASSERT_EQUAL(SpotState::Unknown, f.state());
    TEST_ASSERT_EQUAL_STRING("OUT_OF_RANGE", f.statusName());
}

void test_twenty_cycles_without_flicker() {
    // project criterion: 20x place + remove the car, exactly 40 state changes
    OccupancyFilter f(cfg());
    feed(f, 14.0f, 10);
    int changes = 0;
    for (int cycle = 0; cycle < 20; cycle++) {
        for (int i = 0; i < 12; i++) changes += f.update(i == 5 ? 13.5f : 6.3f + (i % 3) * 0.2f) ? 1 : 0;
        for (int i = 0; i < 12; i++) changes += f.update(i == 4 ? 7.0f : 14.1f - (i % 2) * 0.3f) ? 1 : 0;
    }
    TEST_ASSERT_EQUAL(40, changes);
}

int main(int, char**) {
    UNITY_BEGIN();
    RUN_TEST(test_starts_unknown_then_free);
    RUN_TEST(test_car_arrives_and_leaves);
    RUN_TEST(test_single_spike_is_ignored);
    RUN_TEST(test_hysteresis_band_does_not_flicker);
    RUN_TEST(test_needs_confirmation_before_switching);
    RUN_TEST(test_no_echo_becomes_unknown_and_recovers);
    RUN_TEST(test_out_of_range_is_reported);
    RUN_TEST(test_twenty_cycles_without_flicker);
    return UNITY_END();
}
