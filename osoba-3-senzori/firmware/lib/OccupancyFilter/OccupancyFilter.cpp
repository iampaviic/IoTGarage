#include "OccupancyFilter.h"

OccupancyFilter::OccupancyFilter(const FilterConfig& cfg) : cfg_(cfg) { reset(); }

void OccupancyFilter::reset() {
    for (uint8_t i = 0; i < WINDOW; i++) window_[i] = 0.0f;
    count_ = next_ = invalidRun_ = confirm_ = 0;
    candidate_ = state_ = SpotState::Unknown;
    status_ = SensorStatus::Ok;
    filtered_ = -1.0f;
}

float OccupancyFilter::median() const {
    float tmp[WINDOW];
    for (uint8_t i = 0; i < count_; i++) tmp[i] = window_[i];
    for (uint8_t i = 1; i < count_; i++) {  // insertion sort, at most 5 values
        float v = tmp[i];
        int8_t j = i - 1;
        while (j >= 0 && tmp[j] > v) { tmp[j + 1] = tmp[j]; j--; }
        tmp[j + 1] = v;
    }
    return (count_ % 2) ? tmp[count_ / 2] : 0.5f * (tmp[count_ / 2 - 1] + tmp[count_ / 2]);
}

bool OccupancyFilter::update(float d) {
    const SpotState oldState = state_;
    const SensorStatus oldStatus = status_;

    const bool timeout = !(d > 0.0f);  // also catches NaN
    const bool outOfRange = !timeout && (d < cfg_.minValidCm || d > cfg_.maxValidCm);
    if (timeout || outOfRange) {
        if (invalidRun_ < 255) invalidRun_++;
        if (invalidRun_ >= cfg_.maxInvalid) {
            status_ = timeout ? SensorStatus::Timeout : SensorStatus::OutOfRange;
            state_ = candidate_ = SpotState::Unknown;
            confirm_ = 0;
            count_ = next_ = 0;  // start fresh when the sensor comes back
            filtered_ = -1.0f;
        }
        return state_ != oldState || status_ != oldStatus;
    }

    invalidRun_ = 0;
    status_ = SensorStatus::Ok;
    window_[next_] = d;
    next_ = (next_ + 1) % WINDOW;
    if (count_ < WINDOW) count_++;
    if (count_ < 3) return status_ != oldStatus;  // need a few readings for a meaningful median
    filtered_ = median();

    SpotState seen = candidate_;
    if (filtered_ < cfg_.occupiedBelowCm) seen = SpotState::Occupied;
    else if (filtered_ > cfg_.freeAboveCm) seen = SpotState::Free;
    else if (state_ != SpotState::Unknown) seen = state_;  // hysteresis band: keep current state

    if (seen == SpotState::Unknown) return status_ != oldStatus;
    if (seen == state_) {
        confirm_ = 0;
        candidate_ = state_;
    } else if (seen == candidate_) {
        if (++confirm_ >= cfg_.confirmCount) {
            state_ = seen;
            confirm_ = 0;
        }
    } else {
        candidate_ = seen;
        confirm_ = 1;
        if (cfg_.confirmCount <= 1) state_ = seen;
    }
    return state_ != oldState || status_ != oldStatus;
}

const char* OccupancyFilter::stateName() const {
    switch (state_) {
        case SpotState::Free: return "FREE";
        case SpotState::Occupied: return "OCCUPIED";
        default: return "UNKNOWN";
    }
}

const char* OccupancyFilter::statusName() const {
    switch (status_) {
        case SensorStatus::Timeout: return "TIMEOUT";
        case SensorStatus::OutOfRange: return "OUT_OF_RANGE";
        default: return "OK";
    }
}
