// Turns noisy distance readings into a stable FREE / OCCUPIED / UNKNOWN state.
// Pure C++ (no Arduino), so it is unit-tested on the PC: pio test -e native
//
//   1. invalid readings (no echo, out of range) are counted; too many in a row -> UNKNOWN
//   2. median of the last 5 valid readings removes single spikes
//   3. hysteresis: below occupiedBelowCm -> OCCUPIED, above freeAboveCm -> FREE,
//      in between -> keep the current state (no flicker at the threshold)
//   4. a new state must be seen confirmCount times in a row before it is reported
#pragma once
#include <stdint.h>

enum class SpotState : uint8_t { Unknown = 0, Free = 1, Occupied = 2 };
enum class SensorStatus : uint8_t { Ok = 0, Timeout = 1, OutOfRange = 2 };

struct FilterConfig {
    float occupiedBelowCm = 10.0f;
    float freeAboveCm = 12.0f;
    uint8_t confirmCount = 3;
    uint8_t maxInvalid = 5;
    float minValidCm = 2.0f;
    float maxValidCm = 60.0f;
};

class OccupancyFilter {
public:
    static const uint8_t WINDOW = 5;

    explicit OccupancyFilter(const FilterConfig& cfg = FilterConfig());

    // Feed one raw reading in cm; a value <= 0 means "no echo / timeout".
    // Returns true when the reported state or sensor status changed.
    bool update(float distanceCm);

    SpotState state() const { return state_; }
    SensorStatus status() const { return status_; }
    float filteredCm() const { return filtered_; }   // < 0 when not available
    const char* stateName() const;
    const char* statusName() const;
    void reset();

private:
    float median() const;

    FilterConfig cfg_;
    float window_[WINDOW];
    uint8_t count_ = 0;
    uint8_t next_ = 0;
    uint8_t invalidRun_ = 0;
    uint8_t confirm_ = 0;
    SpotState candidate_ = SpotState::Unknown;
    SpotState state_ = SpotState::Unknown;
    SensorStatus status_ = SensorStatus::Ok;
    float filtered_ = -1.0f;
};
