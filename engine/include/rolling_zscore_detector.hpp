#pragma once

#include <deque>
#include <string>
#include <unordered_map>

namespace smartgrid {

// Result of processing a single reading for a single meter.
struct DetectionResult {
    bool is_anomaly = false;   // true if this reading was flagged
    bool warming_up = false;   // true if we don't have enough history yet to judge
    double z_score = 0.0;      // how many standard deviations from the mean (0 while warming up)
    double rolling_mean = 0.0; // the meter's current windowed mean
};

// Per-meter sliding window of recent readings, plus running sums that let
// us compute mean/std-dev for the window in O(1) without re-scanning it
// every time. Using a bounded window (rather than the meter's entire
// history) means an old anomaly's influence fades away once it ages out,
// instead of permanently skewing what "normal" looks like.
struct MeterState {
    std::deque<double> window;
    double sum = 0.0;
    double sum_sq = 0.0; // sum of squares, used to derive variance
};

class RollingZScoreDetector {
public:
    // threshold: how many standard deviations away counts as anomalous (3.0 is a common default)
    // warmup_readings: how many readings a meter needs before we start flagging it
    // window_size: how many of the most recent readings count toward the rolling stats
    explicit RollingZScoreDetector(double threshold = 3.0,
                                    long warmup_readings = 5,
                                    std::size_t window_size = 20);

    // Feed in one new reading for a given meter. Updates that meter's
    // rolling window and returns whether this reading looks anomalous.
    DetectionResult process(const std::string& meter_id, double value);

private:
    double threshold_;
    long warmup_readings_;
    std::size_t window_size_;
    std::unordered_map<std::string, MeterState> meter_states_;

    // Mean and standard deviation of a meter's *current* window contents.
    static double window_mean(const MeterState& state);
    static double window_std_dev(const MeterState& state, double mean);
};

} // namespace smartgrid