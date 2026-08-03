#include <gtest/gtest.h>

#include "rolling_zscore_detector.hpp"

using smartgrid::RollingZScoreDetector;

// A meter's first few readings shouldn't be flagged at all — there isn't
// enough history yet to know what "normal" looks like for it.
TEST(RollingZScoreDetector, WarmupReadingsAreNeverFlagged) {
    RollingZScoreDetector detector(/*threshold=*/3.0, /*warmup_readings=*/5, /*window_size=*/20);

    for (int i = 0; i < 5; ++i) {
        auto result = detector.process("MTR-TEST", 2.5);
        EXPECT_TRUE(result.warming_up);
        EXPECT_FALSE(result.is_anomaly);
    }
}

// A steady, unremarkable stream of readings should never be flagged.
TEST(RollingZScoreDetector, NormalReadingsAreNotFlagged) {
    RollingZScoreDetector detector(3.0, 5, 20);

    std::vector<double> readings = {2.4, 2.6, 2.5, 2.55, 2.45, 2.5, 2.48, 2.52};
    for (double kwh : readings) {
        auto result = detector.process("MTR-TEST", kwh);
        if (!result.warming_up) {
            EXPECT_FALSE(result.is_anomaly) << "kwh=" << kwh << " was wrongly flagged";
        }
    }
}

// A sudden large spike, after a stable baseline, should be flagged.
TEST(RollingZScoreDetector, SpikeIsFlagged) {
    RollingZScoreDetector detector(3.0, 5, 20);

    // Establish a stable baseline first.
    for (double kwh : {2.4, 2.6, 2.5, 2.55, 2.45, 2.5}) {
        detector.process("MTR-TEST", kwh);
    }

    auto result = detector.process("MTR-TEST", 18.9); // clear spike
    EXPECT_TRUE(result.is_anomaly);
}

// A sudden negative reading, after a stable baseline, should be flagged.
TEST(RollingZScoreDetector, NegativeValueIsFlagged) {
    RollingZScoreDetector detector(3.0, 5, 20);

    for (double kwh : {2.4, 2.6, 2.5, 2.55, 2.45, 2.5}) {
        detector.process("MTR-TEST", kwh);
    }

    auto result = detector.process("MTR-TEST", -3.2); // clear negative anomaly
    EXPECT_TRUE(result.is_anomaly);
}

// A flatlined meter (identical readings) should stay quiet, since nothing
// has actually changed — until a reading finally differs.
TEST(RollingZScoreDetector, FlatlineStaysQuietUntilValueChanges) {
    RollingZScoreDetector detector(3.0, 5, 20);

    for (int i = 0; i < 6; ++i) {
        auto result = detector.process("MTR-TEST", 3.0);
        if (!result.warming_up) {
            EXPECT_FALSE(result.is_anomaly);
        }
    }

    auto changed = detector.process("MTR-TEST", 3.5);
    EXPECT_TRUE(changed.is_anomaly);
}

// This is the regression test for the masking bug we found: once an old
// spike ages out of the rolling window, the detector should regain full
// sensitivity — a later anomaly should NOT be hidden by an earlier one.
TEST(RollingZScoreDetector, OldSpikeDoesNotPermanentlyMaskLaterAnomalies) {
    RollingZScoreDetector detector(3.0, /*warmup_readings=*/5, /*window_size=*/5);

    for (double kwh : {2.4, 2.6, 2.5, 2.55, 2.45}) {
        detector.process("MTR-TEST", kwh); // warm-up
    }

    auto spike_result = detector.process("MTR-TEST", 18.9);
    EXPECT_TRUE(spike_result.is_anomaly);

    // Push enough normal readings through to fully evict the spike from
    // a window of size 5.
    for (double kwh : {2.5, 2.5, 2.5, 2.5, 2.5}) {
        detector.process("MTR-TEST", kwh);
    }

    // The baseline should be clean again, so this negative reading should
    // be caught rather than masked by the earlier spike.
    auto negative_result = detector.process("MTR-TEST", -3.2);
    EXPECT_TRUE(negative_result.is_anomaly);
}

// Different meters must not share state with each other.
TEST(RollingZScoreDetector, MetersAreTrackedIndependently) {
    RollingZScoreDetector detector(3.0, 5, 20);

    for (double kwh : {2.4, 2.6, 2.5, 2.55, 2.45}) {
        detector.process("MTR-A", kwh);
    }

    // MTR-B is brand new, so it should still be warming up even though
    // MTR-A already has plenty of history.
    auto result = detector.process("MTR-B", 2.5);
    EXPECT_TRUE(result.warming_up);
}