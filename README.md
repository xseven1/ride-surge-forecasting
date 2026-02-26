# Real-Time Demand Forecasting and Surge Optimization System

This project implements a production-style machine learning system that forecasts short-term ride demand per zone and computes surge multipliers based on predicted demand and current supply. The system simulates city-wide ride activity and demonstrates how demand forecasting models integrate with real-time feature aggregation and model serving.

## Overview

The system performs two core tasks:

1. Forecast next 5-minute ride demand per zone using a regression model.
2. Compute dynamic surge multipliers using forecasted demand and available supply.

The pipeline includes:

- Real-time event simulation or replay mode
- Rolling 1-minute and 5-minute feature aggregation
- LightGBM demand forecasting model
- Redis-backed zone state management
- FastAPI inference service
- Streamlit live dashboard
- Optional Docker-based multi-service orchestration

## System Architecture

Ride Events (Simulation or Replay)
        ->
Online Aggregator (Rolling Windows)
        ->
Redis (Zone State Store)
        ->
LightGBM Demand Forecast Model
        ->
Surge Pricing Policy
        ->
FastAPI Inference API
        ->
Streamlit Dashboard

## Machine Learning Component

### Problem Formulation

For each zone at time t, the model predicts:

next_5m_demand = f(
    demand_1m,
    demand_5m,
    utilization,
    supply_now,
    weather_flag,
    event_flag,
    time_features
)

### Model

- Model type: LightGBM Regressor
- Objective: Minimize RMSE for next 5-minute demand prediction
- Feature set:
  - Rolling demand (1 minute and 5 minutes)
  - Demand growth trend
  - Supply availability
  - Utilization ratio
  - Weather and event indicators
  - Time encodings

### Surge Policy

Predicted demand is converted into a surge multiplier:

ratio = predicted_demand / (supply_now + 1)
surge = clamp(1 + alpha * ratio + beta * weather + gamma * event, 1.0, 3.0)

## Real-Time Feature Engineering

For each zone, the system maintains:

- demand_1m
- demand_5m
- demand_trend
- supply_now
- utilization ratio
- contextual flags

These values are continuously updated using streaming-style aggregation logic. Redis serves as a fast in-memory state store for online inference.

## Dashboard Features

The Streamlit interface provides:

- Live city grid colored by surge multiplier
- Per-zone drill-down charts
- Forecast versus current demand visualization
- System throughput metrics
- Approximate inference latency tracking
- Interactive controls:
  - Request rate slider
  - Rush hour toggle
  - Rain toggle
  - Special event toggle
  - Manual ride injection

## Data Modes

Simulation Mode:
Generates synthetic ride events with configurable supply-demand dynamics.

Replay Mode:
Replays sampled taxi trip data to reproduce realistic demand spikes. Surge labels are generated through a configurable pricing policy.

## Running the Project Locally

1. Clone the repository

git clone https://github.com/yourusername/real-time-demand-forecasting.git
cd real-time-demand-forecasting

2. Install dependencies

pip install -r requirements.txt

3. Start Redis (if not using Docker)

docker run -p 6379:6379 redis

4. Start FastAPI

uvicorn api.main:app --reload

5. Start Streamlit dashboard

streamlit run dashboard/app.py

## Docker (Optional)

To run the full stack:

docker compose up --build

Services include:
- Redis
- FastAPI
- Simulator
- Streamlit dashboard

## Example Metrics

- Forecast RMSE: example 4.82 rides
- Average API latency: approximately 35 ms
- System throughput: simulated events per second under load

## What This Demonstrates

- Real-time online feature engineering
- Time-series demand forecasting
- ML model serving in a production-style architecture
- Stateful inference using Redis
- Streaming-style simulation
- Containerized multi-service systems
- End-to-end ML system design

## Future Improvements

- Kafka-based ingestion
- Concept drift detection
- Automated retraining pipeline
- Driver behavior simulation
- Kubernetes deployment
- Multi-city scaling

## Technologies Used

- Python
- LightGBM
- FastAPI
- Streamlit
- Redis
- Docker
- Pandas
- NumPy
- Scikit-learn

## Author

Udayan Gaikwad
Machine Learning Engineer