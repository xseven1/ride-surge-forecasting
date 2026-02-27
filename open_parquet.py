import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_parquet("taxi_data.parquet")

# Busiest zones
print("Top 10 busiest pickup zones:")
print(df["PULocationID"].value_counts().head(10))

# Demand by hour
df["hour"] = df["tpep_pickup_datetime"].dt.hour
hourly = df.groupby("hour").size()

plt.figure(figsize=(12, 4))

plt.subplot(1, 2, 1)
df["PULocationID"].value_counts().head(20).plot(kind="bar")
plt.title("Top 20 Busiest Zones")
plt.xlabel("Zone ID")
plt.ylabel("Ride Count")

plt.subplot(1, 2, 2)
hourly.plot(kind="bar")
plt.title("Demand by Hour of Day")
plt.xlabel("Hour")
plt.ylabel("Ride Count")

plt.tight_layout()
plt.savefig("eda.png")
plt.show()