import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import A4


# -----------------------------------
# Find file using keyword
# -----------------------------------
def find_file(folder, keyword):
    for file in os.listdir(folder):
        if keyword.lower() in file.lower():
            return os.path.join(folder, file)
    return None


# -----------------------------------
# Load signal file (Flow / Thorac / SPO2)
# -----------------------------------
def load_signal(file_path):
    timestamps = []
    values = []

    with open(file_path, "r") as f:
        lines = f.readlines()

    data_started = False

    for line in lines:
        line = line.strip()

        # Start reading only after "Data:"
        if line.startswith("Data:"):
            data_started = True
            continue

        if not data_started:
            continue

        # Expected format:
        # 30.05.2024 20:59:00,000; 120
        try:
            timestamp_part, value_part = line.split(";")
            timestamp_part = timestamp_part.strip()
            value = float(value_part.strip())

            # Replace comma milliseconds with dot
            timestamp_part = timestamp_part.replace(",", ".")

            timestamp = pd.to_datetime(
                timestamp_part,
                format="%d.%m.%Y %H:%M:%S.%f"
            )

            timestamps.append(timestamp)
            values.append(value)

        except:
            continue

    df = pd.DataFrame(values, index=timestamps)
    return df


# -----------------------------------
# Load events file
# -----------------------------------
def load_events(file_path):
    events = []

    with open(file_path, "r") as f:
        lines = f.readlines()

    data_started = False

    for line in lines:
        line = line.strip()

        if line.startswith("Data:"):
            data_started = True
            continue

        if not data_started:
            continue

        # Expected format similar to signals:
        # 30.05.2024 23:10:12,000; 30.05.2024 23:10:35,000; Apnea
        try:
            parts = line.split(";")

            start_str = parts[0].strip().replace(",", ".")
            end_str = parts[1].strip().replace(",", ".")
            event_label = parts[2].strip() if len(parts) > 2 else "Event"

            start = pd.to_datetime(start_str, format="%d.%m.%Y %H:%M:%S.%f")
            end = pd.to_datetime(end_str, format="%d.%m.%Y %H:%M:%S.%f")

            events.append([start, end, event_label])

        except:
            continue

    return pd.DataFrame(events, columns=["start_time", "end_time", "event"])


# -----------------------------------
# Plot signal with event overlays
# -----------------------------------
def plot_signal(df, events, title, save_path):
    plt.figure(figsize=(12, 4))
    plt.plot(df.index, df.iloc[:, 0])

    for _, row in events.iterrows():
        plt.axvspan(row["start_time"], row["end_time"], alpha=0.3)

    plt.title(title)
    plt.xlabel("Time")
    plt.ylabel("Amplitude")
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()


# -----------------------------------
# Main
# -----------------------------------
def main():
    parser = argparse.ArgumentParser(description="Generate sleep visualization PDF")
    parser.add_argument("-name", required=True, help="Participant folder path (e.g., Data/AP01)")
    args = parser.parse_args()

    participant_path = args.name
    participant_name = os.path.basename(participant_path.rstrip("/"))

    output_dir = "Visualizations"
    os.makedirs(output_dir, exist_ok=True)

    # Auto-detect files
    flow_file = find_file(participant_path, "flow")
    thorac_file = find_file(participant_path, "thorac")
    spo2_file = find_file(participant_path, "spo2")
    event_file = find_file(participant_path, "event")

    if not all([flow_file, thorac_file, spo2_file, event_file]):
        print("❌ Error: Required files not found.")
        return

    print("Detected files:")
    print(flow_file)
    print(thorac_file)
    print(spo2_file)
    print(event_file)

    # Load data
    df_flow = load_signal(flow_file)
    df_thorac = load_signal(thorac_file)
    df_spo2 = load_signal(spo2_file)
    events = load_events(event_file)

    # Image paths
    flow_img = os.path.join(output_dir, f"{participant_name}_flow.png")
    thorac_img = os.path.join(output_dir, f"{participant_name}_thorac.png")
    spo2_img = os.path.join(output_dir, f"{participant_name}_spo2.png")

    # Generate plots
    plot_signal(df_flow, events, "Nasal Airflow (8 Hours)", flow_img)
    plot_signal(df_thorac, events, "Thoracic Movement (8 Hours)", thorac_img)
    plot_signal(df_spo2, events, "SpO2 (8 Hours)", spo2_img)

    # Create PDF
    pdf_path = os.path.join(output_dir, f"{participant_name}_Sleep_Visualization.pdf")
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph(f"Sleep Study Visualization - {participant_name}", styles["Heading1"]))
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Image(flow_img, width=6 * inch, height=2 * inch))
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Image(thorac_img, width=6 * inch, height=2 * inch))
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Image(spo2_img, width=6 * inch, height=2 * inch))

    doc.build(elements)

    print("\n✅ PDF successfully saved at:")
    print(pdf_path)


if __name__ == "__main__":
    main()