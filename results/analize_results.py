import pandas as pd
import matplotlib.pyplot as plt
import os
os.makedirs("plot", exist_ok=True)

def add_bar_labels(ax, values):
    for i, v in enumerate(values):
        ax.text(i, v, f"{v:.2f}", ha="center", va="bottom", fontsize=9)

# Load data
df = pd.read_csv("results.csv")

# Rename columns for convenience
df = df.rename(columns={
    "Tempo_totale_sec": "Time",
    "Collisioni_muri": "Collisions",
    "Vite_rimanenti": "Lives",
    "Modalità": "Mode"
})

# ---------------------------
# DESCRIPTIVE STATISTICS
# ---------------------------
grouped = df.groupby("Mode")

summary = grouped[["Time", "Collisions", "Lives"]].agg(["mean", "std"])
print("\nDescriptive statistics:\n")
print(summary)

# ---------------------------
# COMPOSITE SCORE
# ---------------------------
T_min, T_max = df["Time"].min(), df["Time"].max()
C_min, C_max = df["Collisions"].min(), df["Collisions"].max()
L_max = df["Lives"].max()

df["T_norm"] = 1 - (df["Time"] - T_min) / (T_max - T_min)
df["C_norm"] = 1 - (df["Collisions"] - C_min) / (C_max - C_min)
df["L_norm"] = df["Lives"] / L_max

wT, wC, wL = 0.4, 0.3, 0.3
df["SCORE"] = wT * df["T_norm"] + wC * df["C_norm"] + wL * df["L_norm"]

score_summary = df.groupby("Mode")["SCORE"].agg(["mean", "std"])
print("\nComposite score:\n")
print(score_summary)

# ---------------------------
# PLOTS
# ---------------------------

# Completion time
plt.figure()
means = grouped["Time"].mean()
stds = grouped["Time"].std()
ax = means.plot(kind="bar", yerr=stds, capsize=4)
plt.ylabel("Completion Time (s)")
plt.title("Task Completion Time by Feedback Modality")
add_bar_labels(ax, means.values)
plt.tight_layout()
plt.savefig("plot/completion_time.png", dpi=300)
plt.close()

# Collisions
plt.figure()
means = grouped["Collisions"].mean()
stds = grouped["Collisions"].std()
ax = means.plot(kind="bar", yerr=stds, capsize=4)
plt.ylabel("Number of Collisions")
plt.title("Wall Collisions by Feedback Modality")
add_bar_labels(ax, means.values)
plt.tight_layout()
plt.savefig("plot/collisions.png", dpi=300)
plt.close()

# Remaining lives
plt.figure()
means = grouped["Lives"].mean()
stds = grouped["Lives"].std()
ax = means.plot(kind="bar", yerr=stds, capsize=4)
plt.ylabel("Remaining Lives")
plt.title("Remaining Lives by Feedback Modality")
add_bar_labels(ax, means.values)
plt.tight_layout()
plt.savefig("plot/remaining_lives.png", dpi=300)
plt.close()

# Composite score
plt.figure()
means = score_summary["mean"]
stds = score_summary["std"]
ax = means.plot(kind="bar", yerr=stds, capsize=4)
plt.ylabel("Composite Performance Score")
plt.title("Overall Performance by Feedback Modality")
add_bar_labels(ax, means.values)
plt.tight_layout()
plt.savefig("plot/composite_score.png", dpi=300)
plt.close()