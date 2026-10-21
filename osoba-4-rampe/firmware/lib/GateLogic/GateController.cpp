#include "GateController.h"

GateController::GateController(const GateTiming& t) : t_(t) {
    for (uint8_t i = 0; i < REMEMBERED_IDS; i++) ids_[i][0] = 0;
}

const char* GateController::stateName(GateState s) {
    switch (s) {
        case GateState::Closed: return "CLOSED";
        case GateState::Opening: return "OPENING";
        case GateState::Open: return "OPEN";
        case GateState::Closing: return "CLOSING";
        default: return "ERROR";
    }
}

bool GateController::targetOpen() const {
    return state_ == GateState::Opening || state_ == GateState::Open || state_ == GateState::Error;
}

void GateController::emit(const char* requestId, bool success, const char* reason, const char* source) {
    if (qLen_ == QUEUE) {  // drop the oldest; the newest state matters most
        qHead_ = (qHead_ + 1) % QUEUE;
        qLen_--;
    }
    GateEvent& e = queue_[(qHead_ + qLen_) % QUEUE];
    e.state = state_;
    e.vehiclePresent = vehicle_;
    strncpy(e.requestId, requestId ? requestId : "", sizeof e.requestId - 1);
    e.requestId[sizeof e.requestId - 1] = 0;
    e.success = success;
    e.reason = reason;
    e.source = source;
    qLen_++;
}

bool GateController::popEvent(GateEvent& out) {
    if (!qLen_) return false;
    out = queue_[qHead_];
    qHead_ = (qHead_ + 1) % QUEUE;
    qLen_--;
    return true;
}

void GateController::set(GateState s, const char* source, const char* requestId, uint32_t now) {
    state_ = s;
    since_ = now;
    if (s == GateState::Open) {
        openedAt_ = now;
        passed_ = false;
        seenVehicle_ = vehicle_;
    }
    emit(requestId, true, nullptr, source);
}

bool GateController::seenId(const char* id) {
    if (!id || !id[0]) return false;
    for (uint8_t i = 0; i < REMEMBERED_IDS; i++)
        if (strcmp(ids_[i], id) == 0) return true;
    strncpy(ids_[idNext_], id, 40);
    ids_[idNext_][40] = 0;
    idNext_ = (idNext_ + 1) % REMEMBERED_IDS;
    return false;
}

void GateController::command(const char* cmd, const char* requestId, const char* source, uint32_t now) {
    if (!ack_) return;
    if (seenId(requestId)) {
        emit(requestId, true, "DUPLICATE", source);
        return;
    }
    if (strcmp(cmd, "RESET") == 0) {
        reversals_ = 0;
        set(vehicle_ ? GateState::Open : GateState::Closing, source, requestId, now);
    } else if (state_ == GateState::Error) {
        emit(requestId, false, "ERROR_STATE", source);
    } else if (strcmp(cmd, "OPEN") == 0) {
        if (state_ == GateState::Open || state_ == GateState::Opening) {
            if (state_ == GateState::Open) openedAt_ = now;  // keep it open a little longer
            emit(requestId, true, nullptr, source);
        } else {
            set(GateState::Opening, source, requestId, now);
        }
    } else if (strcmp(cmd, "CLOSE") == 0) {
        if (vehicle_) emit(requestId, false, "VEHICLE_PRESENT", source);
        else if (state_ == GateState::Closed || state_ == GateState::Closing) emit(requestId, true, nullptr, source);
        else set(GateState::Closing, source, requestId, now);
    } else {
        emit(requestId, false, "INVALID_COMMAND", source);
    }
}

void GateController::button(uint32_t now) {
    if (state_ == GateState::Closed || state_ == GateState::Closing) set(GateState::Opening, "BUTTON", nullptr, now);
}

void GateController::resetButton(uint32_t now) {
    if (state_ != GateState::Error) return;
    reversals_ = 0;
    set(vehicle_ ? GateState::Open : GateState::Closing, "BUTTON", nullptr, now);
}

void GateController::setVehicle(bool present, uint32_t now) {
    if (present == vehicle_) return;
    vehicle_ = present;
    if (present && state_ == GateState::Closing) {
        if (++reversals_ >= t_.maxReversals) {
            state_ = GateState::Error;
            since_ = now;
            emit(nullptr, false, "CLOSE_OBSTRUCTED", "SAFETY");
            return;
        }
        set(GateState::Opening, "SAFETY", nullptr, now);
        return;
    }
    if (present && state_ == GateState::Open) seenVehicle_ = true;
    if (!present && state_ == GateState::Open && seenVehicle_) {
        passed_ = true;
        passedAt_ = now;
    }
    emit(nullptr, true, nullptr, "SENSOR");
}

void GateController::tick(uint32_t now) {
    if (state_ == GateState::Opening && now - since_ >= t_.moveMs) {
        set(GateState::Open, "SENSOR", nullptr, now);
    } else if (state_ == GateState::Closing && now - since_ >= t_.moveMs) {
        reversals_ = 0;
        set(GateState::Closed, "AUTO_CLOSE", nullptr, now);
    } else if (state_ == GateState::Open && !vehicle_) {
        bool passed = passed_ && now - passedAt_ >= t_.closeAfterPassMs;
        bool timeout = now - openedAt_ >= t_.autoCloseMs;
        if (passed || timeout) set(GateState::Closing, "AUTO_CLOSE", nullptr, now);
    }
}
