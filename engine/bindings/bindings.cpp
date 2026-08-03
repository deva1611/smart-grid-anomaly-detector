// engine/bindings/bindings.cpp
//
// Exposes RollingZScoreDetector to Python using pybind11. This is what
// lets Python call detector.process("MTR-0001", 2.5) and get back a real
// result computed by the compiled C++ engine — no reimplementation of
// the detection logic in Python.

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "rolling_zscore_detector.hpp"

namespace py = pybind11;

PYBIND11_MODULE(smart_grid_engine, module) {
    module.doc() = "Python bindings for the smart grid rolling z-score anomaly detection engine";

    // Expose DetectionResult as a plain read-only Python object.
    py::class_<smartgrid::DetectionResult>(module, "DetectionResult")
        .def_readonly("is_anomaly", &smartgrid::DetectionResult::is_anomaly)
        .def_readonly("warming_up", &smartgrid::DetectionResult::warming_up)
        .def_readonly("z_score", &smartgrid::DetectionResult::z_score)
        .def_readonly("rolling_mean", &smartgrid::DetectionResult::rolling_mean)
        .def("__repr__", [](const smartgrid::DetectionResult& r) {
            return "<DetectionResult is_anomaly=" + std::to_string(r.is_anomaly) +
                   " warming_up=" + std::to_string(r.warming_up) +
                   " z_score=" + std::to_string(r.z_score) +
                   " rolling_mean=" + std::to_string(r.rolling_mean) + ">";
        });

    // Expose the detector class itself, with the same constructor
    // defaults as the C++ side (threshold, warmup_readings, window_size).
    py::class_<smartgrid::RollingZScoreDetector>(module, "RollingZScoreDetector")
        .def(py::init<double, long, std::size_t>(),
             py::arg("threshold") = 3.0,
             py::arg("warmup_readings") = 5,
             py::arg("window_size") = 20)
        .def("process", &smartgrid::RollingZScoreDetector::process,
             py::arg("meter_id"), py::arg("value"),
             "Feed in one new reading for a meter and get back a DetectionResult.");
}