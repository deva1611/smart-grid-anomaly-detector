// engine/src/main.cpp
//
// Standalone demo for the rolling z-score detector. Uses a small window
// size (5) so eviction happens quickly and is easy to observe within a
// short test sequence. No Python, no pybind11 — just proving the C++
// engine works correctly on its own first.

#include <iostream>
#include <vector>
#include <utility>

#include "rolling_zscore_detector.hpp"

int main() {
    // threshold=3.0, warmup=5 readings, window=5 readings.
    // A small window is used here purely so this short demo can show
    // eviction happening; a real deployment might use a larger window.
    smartgrid::RollingZScoreDetector detector(/*threshold=*/3.0,
                                               /*warmup_readings=*/5,
                                               /*window_size=*/5);

    std::cout << "--- MTR-0001: spike, then watch it age out of the window ---\n";
    std::vector<double> meter1_readings = {
        2.4, 2.6, 2.5, 2.55, 2.45,   // warm-up (5 readings)
        2.5,                          // normal
        18.9,                         // spike -> should be flagged
        2.6, 2.5, 2.5, 2.5, 2.5,      // 5 normal readings: enough for the spike to age out of a window of 5
        -3.2,                         // negative -> should now be flagged too, since the window is clean again
    };
    for (double kwh : meter1_readings) {
        smartgrid::DetectionResult r = detector.process("MTR-0001", kwh);
        std::cout << "kwh=" << kwh;
        if (r.warming_up) {
            std::cout << "  [warming up]\n";
            continue;
        }
        std::cout << " z_score=" << r.z_score << " mean=" << r.rolling_mean;
        if (r.is_anomaly) std::cout << "  <-- ANOMALY";
        std::cout << "\n";
    }

    std::cout << "\n--- MTR-0002: a flatlined meter, then a value that finally changes ---\n";
    std::vector<double> meter2_readings = {
        3.0, 3.0, 3.0, 3.0, 3.0,  // warm-up: identical every time (a stuck sensor)
        3.0,                       // still identical -> not anomalous, nothing has changed
        3.5,                       // finally different -> should be flagged
    };
    for (double kwh : meter2_readings) {
        smartgrid::DetectionResult r = detector.process("MTR-0002", kwh);
        std::cout << "kwh=" << kwh;
        if (r.warming_up) {
            std::cout << "  [warming up]\n";
            continue;
        }
        std::cout << " z_score=" << r.z_score << " mean=" << r.rolling_mean;
        if (r.is_anomaly) std::cout << "  <-- ANOMALY";
        std::cout << "\n";
    }

    return 0;
}