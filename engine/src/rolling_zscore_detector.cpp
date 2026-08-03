#include "rolling_zscore_detector.hpp"

#include <cmath>

namespace smartgrid {

RollingZScoreDetector::RollingZScoreDetector(double threshold, long warmup_readings, std::size_t window_size)
    : threshold_(threshold), warmup_readings_(warmup_readings), window_size_(window_size) {}

double RollingZScoreDetector::window_mean(const MeterState& state) {
    if (state.window.empty()) {
        return 0.0;
    }
    return state.sum / static_cast<double>(state.window.size());
}

double RollingZScoreDetector::window_std_dev(const MeterState& state, double mean) {
    std::size_t n = state.window.size();
    if (n < 2) {
        return 0.0; // not enough data in the window for a meaningful spread
    }
    // Sample variance from the running sums: avg-of-squares minus mean-squared,
    // scaled up to a sample (n-1 denominator) estimate.
    double variance = (state.sum_sq - static_cast<double>(n) * mean * mean)
                       / static_cast<double>(n - 1);
    if (variance < 0.0) variance = 0.0; // guards against tiny floating-point negatives
    return std::sqrt(variance);
}

DetectionResult RollingZScoreDetector::process(const std::string& meter_id, double value) {
    MeterState& state = meter_states_[meter_id];

    // Judge the new reading against the window as it stood *before* this
    // reading arrives, so an extreme value can't dilute its own signal.
    bool had_enough_history = state.window.size() >= static_cast<std::size_t>(warmup_readings_);
    double prior_mean = window_mean(state);
    double prior_std_dev = window_std_dev(state, prior_mean);

    // Add the new reading into the sliding window.
    state.window.push_back(value);
    state.sum += value;
    state.sum_sq += value * value;

    // Evict the oldest reading once the window exceeds its fixed size —
    // this is what lets an old anomaly's influence fade away over time
    // instead of permanently skewing the baseline.
    if (state.window.size() > window_size_) {
        double oldest = state.window.front();
        state.window.pop_front();
        state.sum -= oldest;
        state.sum_sq -= oldest * oldest;
    }

    DetectionResult result;
    result.rolling_mean = window_mean(state);

    if (!had_enough_history) {
        result.warming_up = true;
        return result;
    }

    if (prior_std_dev == 0.0) {
        // Every reading in the window so far was identical (e.g. a flatline).
        // Any deviation at all from that flat value is meaningful here.
        result.z_score = 0.0;
        result.is_anomaly = (value != prior_mean);
        return result;
    }

    result.z_score = (value - prior_mean) / prior_std_dev;
    result.is_anomaly = std::abs(result.z_score) > threshold_;
    return result;
}

} // namespace smartgrid