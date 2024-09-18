from flask import Flask, request, jsonify, render_template
import os
import pandas as pd

app = Flask(__name__)

UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def clean_file(file_path):
    """Cleans the uploaded file by removing specified columns and rows with NaNs in the 'Instrument' column."""
    try:
        df = pd.read_csv(file_path)
        
        # Remove specified columns
        columns_to_remove = ['Process Date', 'Settle Date']
        df_cleaned = df.drop(columns=columns_to_remove, errors='ignore')
        
        # Remove rows where 'Instrument' column is NaN
        if 'Instrument' in df_cleaned.columns:
            df_cleaned = df_cleaned.dropna(subset=['Instrument'])
        
        # Reset index after dropping rows
        df_cleaned.reset_index(drop=True, inplace=True)
        
        # Save cleaned file
        cleaned_file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'cleaned_file.csv')
        df_cleaned.to_csv(cleaned_file_path, index=False)
        return cleaned_file_path, df_cleaned

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
    """Handle file upload, clean the file, and return the cleaned file."""
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
        cleaned_file_path, df_cleaned = clean_file(file_path)
        if not cleaned_file_path:
            return jsonify({"error": "File could not be cleaned."}), 500

        # Convert DataFrame to HTML
        cleaned_file_html = df_cleaned.to_html(classes='table table-striped')

        return render_template('display.html', table=cleaned_file_html, file_name=file.filename)

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({"error": "An error occurred during file upload."}), 500

@app.route('/delete_files', methods=['POST'])
def delete_files():
    """Delete all files in the upload folder."""
    try:
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            file_to_delete = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(file_to_delete):
                os.remove(file_to_delete)
        return render_template('status.html', message="Deleted files successfully.")
    except Exception as e:
        print(f"Error during file deletion: {str(e)}")
        return render_template('status.html', message="Error cleaning up uploads directory.")

if __name__ == '__main__':
    app.run(debug=True, port=8080)
