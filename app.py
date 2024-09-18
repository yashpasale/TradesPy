import os
import uuid
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_from_directory
import pandas as pd

app = Flask(__name__)

UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def clean_file(file_path):
    """Cleans and processes the uploaded file to calculate trading performance."""
    try:
        df = pd.read_csv(file_path)

        # Remove unwanted columns but keep 'Activity Date'
        columns_to_remove = ['Process Date', 'Settle Date']
        df_cleaned = df.drop(columns=columns_to_remove, errors='ignore')

        # Keep all rows and remove rows where 'Instrument' is empty
        df_cleaned = df_cleaned[df_cleaned['Instrument'].notna()]

        # Clean up numeric fields
        df_cleaned['Amount'] = pd.to_numeric(
            df_cleaned['Amount'].replace({r'\$': '', r',': '', r'\(': '-', r'\)': ''}, regex=True),
            errors='coerce'
        )

        # Separate sell and buy trades
        sell_trades = df_cleaned[df_cleaned['Trans Code'].isin(['STO', 'STC'])]
        buy_trades = df_cleaned[df_cleaned['Trans Code'].isin(['BTO', 'BTC'])]

        # Calculate P/L for each option
        pl_summary = pd.DataFrame()
        for description, group in df_cleaned.groupby('Description'):
            total_sell = sell_trades[sell_trades['Description'] == description]['Amount'].sum()
            total_buy = buy_trades[buy_trades['Description'] == description]['Amount'].sum()
            net_pl = total_sell - total_buy
            pl_summary = pd.concat([pl_summary, pd.DataFrame({
                'Description': [description],
                'Total Sell': [total_sell],
                'Total Buy': [total_buy],
                'P/L': [net_pl]
            })], ignore_index=True)

        return df_cleaned, pl_summary

    except Exception as e:
        print(f"Error in cleaning file: {str(e)}")
        return None, None

@app.route('/')
def home():
    """Render the home page."""
    return render_template('index.html')

@app.route('/upload')
def upload_page():
    """Render the upload page."""
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload, clean the file, and redirect to cleaned file display page."""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # Save the uploaded file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        # Clean the file
        cleaned_data, pl_summary = clean_file(file_path)
        if cleaned_data is None:
            return jsonify({"error": "File could not be cleaned."}), 500

        # Save the cleaned data and P/L summary to temporary files
        unique_id = str(uuid.uuid4())
        cleaned_file_path = os.path.join(app.config['UPLOAD_FOLDER'], f'cleaned_file_{unique_id}.csv')
        pl_summary_file = os.path.join(app.config['UPLOAD_FOLDER'], f'pl_summary_{unique_id}.csv')

        cleaned_data.to_csv(cleaned_file_path, index=False)
        pl_summary.to_csv(pl_summary_file, index=False)

        # Redirect to cleaned file display page
        return redirect(url_for('cleaned_file_page', cleaned_file_name=os.path.basename(cleaned_file_path), pl_summary_file=os.path.basename(pl_summary_file)))

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({"error": "An error occurred during file upload."}), 500

@app.route('/cleaned_file')
def cleaned_file_page():
    """Render the cleaned file page with the cleaned data."""
    cleaned_file_name = request.args.get('cleaned_file_name')
    pl_summary_file = request.args.get('pl_summary_file')

    if not cleaned_file_name:
        return redirect(url_for('upload_page'))

    # Load data from the file
    cleaned_file_path = os.path.join(app.config['UPLOAD_FOLDER'], cleaned_file_name)
    cleaned_data = pd.read_csv(cleaned_file_path)

    # Convert the cleaned data DataFrame to HTML
    cleaned_data_html = cleaned_data.to_html(classes='table table-striped')

    # Render the cleaned file page
    return render_template('cleaned_file.html', table=cleaned_data_html, pl_summary_file=pl_summary_file, cleaned_file_name=cleaned_file_name)

@app.route('/download/<filename>')
def download_file(filename):
    """Serve the cleaned file for download."""
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.isfile(file_path):
            return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
        else:
            return jsonify({"error": "File not found."}), 404
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({"error": "An error occurred while downloading the file."}), 500

@app.route('/delete_files', methods=['POST'])
def delete_files():
    """Delete all files in the uploads folder."""
    try:
        folder_path = app.config['UPLOAD_FOLDER']
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        return render_template('status.html', message="All files in the uploads folder were deleted successfully.")
    except Exception as e:
        return render_template('status.html', message=f"Error occurred while deleting files: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True, port=8080)
