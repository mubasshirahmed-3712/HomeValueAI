# app/app.py

from flask import Flask, render_template, request
import pandas as pd
import joblib
from pathlib import Path
import datetime

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "models" / "best_model.pkl"
RESULTS_FILE = BASE_DIR.parent / "results" / "model_evaluation_results.csv"
LOG_FILE = BASE_DIR.parent / "data" / "predictions_log.csv"

# --- App Init ---
app = Flask(__name__)

# --- Load Best Model ---
if not MODEL_PATH.exists():
    raise FileNotFoundError(f"❌ Best model not found at {MODEL_PATH}")
model = joblib.load(MODEL_PATH)


# --- Routes ---

@app.route("/")
def index():
    """Render input form"""
    return render_template("index.html")


@app.route("/predict", methods=["POST"])
def predict():
    """Handle form submission and make predictions"""
    try:
        # Collect input
        avg_income = float(request.form["avg_income"])
        house_age = float(request.form["house_age"])
        rooms = float(request.form["rooms"])
        bedrooms = float(request.form["bedrooms"])
        population = float(request.form["population"])

        # Input validation
        if avg_income <= 0 or house_age <= 0 or rooms <= 0 or bedrooms <= 0 or population <= 0:
            return render_template(
                "results.html",
                prediction="⚠️ Please enter valid positive values.",
                model_name="Best Model (LinearRegression)",
                inputs={}
            )

        # Build dataframe
        input_df = pd.DataFrame([{
            "Avg. Area Income": avg_income,
            "Avg. Area House Age": house_age,
            "Avg. Area Number of Rooms": rooms,
            "Avg. Area Number of Bedrooms": bedrooms,
            "Area Population": population
        }])

        # Prediction (clamped to min=0)
        prediction_val = model.predict(input_df)[0]
        prediction_val = max(0, prediction_val)  # clamp negatives
        prediction = f"${prediction_val:,.2f}"

        # Log prediction
        log_entry = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Avg. Area Income": avg_income,
            "Avg. Area House Age": house_age,
            "Avg. Area Number of Rooms": rooms,
            "Avg. Area Number of Bedrooms": bedrooms,
            "Area Population": population,
            "Predicted Price": prediction_val
        }
        pd.DataFrame([log_entry]).to_csv(
            LOG_FILE, mode="a", index=False, header=not LOG_FILE.exists()
        )

        # Render output
        return render_template(
            "results.html",
            prediction=prediction,
            model_name="Best Model (LinearRegression)",
            inputs=log_entry
        )

    except Exception as e:
        return render_template(
            "results.html",
            prediction=f"❌ Error: {str(e)}",
            model_name="Best Model (LinearRegression)",
            inputs={}
        )


@app.route("/results")
def results():
    """Show model evaluation results table"""
    if RESULTS_FILE.exists():
        df = pd.read_csv(RESULTS_FILE)

        # Format numbers
        df["MAE"] = df["MAE"].apply(lambda x: f"{x:,.2f}")
        df["RMSE"] = df["RMSE"].apply(lambda x: f"{x:,.2f}")
        df["R2"] = df["R2"].apply(lambda x: f"{x:.4f}")

        # Find best model (highest R²)
        best_idx = df["R2"].astype(float).idxmax()
        best_row = df.loc[best_idx].to_dict()   # ✅ convert to dict

        # Convert table to HTML
        table_html = df.to_html(
            classes="table table-striped table-bordered text-center",
            index=False,
            escape=False
        )

        # Highlight the best row
        rows = table_html.split("<tr>")
        for i, row in enumerate(rows):
            if i == best_idx + 2:  # +2 for header and first row offset
                rows[i] = row.replace("<tr>", "<tr class='highlight'>")
        table_html = "<tr>".join(rows)

        return render_template(
            "model.html",
            tables=[table_html],
            best=best_row
        )
    else:
        return render_template(
            "model.html",
            tables=["<p>No evaluation results found.</p>"],
            best=None
        )


# --- Run ---
if __name__ == "__main__":
    app.run(debug=True)
