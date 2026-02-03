# mlops/evidently/drift_service.py
import pandas as pd
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset

def run_drift_check(reference_data_path, current_data_path):
    ref_df = pd.read_csv(reference_data_path)
    cur_df = pd.read_csv(current_data_path)
    
    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=ref_df, current_data=cur_df)
    
    report.save_html("drift_report.html")
    print("Drift check completed.")

if __name__ == "__main__":
    run_drift_check("s3://data/ref.csv", "s3://data/current.csv")