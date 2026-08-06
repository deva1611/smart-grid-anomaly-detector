# Dockerfile — builds the C++ engine and runs the FastAPI service.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir pybind11

COPY engine/ ./engine/

RUN cd engine && \
    PYBIND11_DIR=$(python -c "import pybind11; print(pybind11.get_cmake_dir())") && \
    cmake -S . -B build -Dpybind11_DIR="$PYBIND11_DIR" -DCMAKE_BUILD_TYPE=Release && \
    cmake --build build --config Release --target smart_grid_engine

COPY service/ ./service/
RUN cp engine/build/smart_grid_engine*.so ./service/app/
RUN pip install --no-cache-dir -r service/requirements.txt

WORKDIR /app/service/app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
