// Barrier gate state machine - C++ twin of simulator/gate_sim.py (keep in sync!).
// Pure C++, no Arduino: unit-tested on the PC with `pio test -e native`.
//
//   CLOSED -> OPENING -> OPEN -> CLOSING -> CLOSED      ERROR (stays where it is)
//   * OPEN in CLOSED/CLOSING -> OPENING; in OPEN/OPENING -> success, nothing to do
//   * CLOSE is refused (VEHICLE_PRESENT) while the IR sensor sees a vehicle
//   * auto close: closeAfterPassMs after the vehicle passed, or autoCloseMs after opening
//   * vehicle detected while CLOSING -> reopen (safety); maxReversals in a row -> ERROR
//   * RESET clears ERROR; a repeated requestId is acknowledged but not executed twice
#pragma once
#include <stdint.h>
#include <string.h>

enum class GateState : uint8_t { Closed, Opening, Open, Closing, Error };

struct GateTiming {
    uint32_t moveMs = 1000;
    uint32_t closeAfterPassMs = 2000;
    uint32_t autoCloseMs = 10000;
    uint8_t maxReversals = 3;
};

struct GateEvent {
    GateState state;
    bool vehiclePresent;
    char requestId[41];   // empty = not an answer to a command
    bool success;
    const char* reason;   // nullptr or VEHICLE_PRESENT, ERROR_STATE, INVALID_COMMAND, DUPLICATE, CLOSE_OBSTRUCTED
    const char* source;   // MQTT, BUTTON, AUTO_CLOSE, SAFETY, SERIAL, SENSOR ...
};

class GateController {
public:
    static const uint8_t QUEUE = 8;
    static const uint8_t REMEMBERED_IDS = 8;

    explicit GateController(const GateTiming& t = GateTiming());

    void command(const char* cmd, const char* requestId, const char* source, uint32_t nowMs);
    void button(uint32_t nowMs);
    void resetButton(uint32_t nowMs);              // long press: same as RESET command
    void setVehicle(bool present, uint32_t nowMs);
    void tick(uint32_t nowMs);
    void setAckEnabled(bool on) { ack_ = on; }      // testing aid: false simulates a dead gate

    bool popEvent(GateEvent& out);                  // events to publish, oldest first
    GateState state() const { return state_; }
    bool vehiclePresent() const { return vehicle_; }
    bool targetOpen() const;                         // where the servo should move to
    static const char* stateName(GateState s);

private:
    void set(GateState s, const char* source, const char* requestId, uint32_t nowMs);
    void emit(const char* requestId, bool success, const char* reason, const char* source);
    bool seenId(const char* requestId);

    GateTiming t_;
    GateState state_ = GateState::Closed;
    bool vehicle_ = false;
    bool ack_ = true;
    uint32_t since_ = 0, openedAt_ = 0, passedAt_ = 0;
    bool passed_ = false, seenVehicle_ = false;
    uint8_t reversals_ = 0;
    char ids_[REMEMBERED_IDS][41];
    uint8_t idNext_ = 0;
    GateEvent queue_[QUEUE];
    uint8_t qHead_ = 0, qLen_ = 0;
};
