from flask import Flask, render_template, request, redirect, url_for
import os
import cv2
import easyocr
import pandas as pd

# Initialize EasyOCR Reader
reader = easyocr.Reader(['en'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Ensure uploads folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    uploaded_image_path = None
    processed_image_path = None
    detected_data = []

    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)

        if file:
            # Save uploaded image
            filename = file.filename
            uploaded_image_path = 'uploads/' + filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Process image
            img = cv2.imread(filepath)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            plate_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_russian_plate_number.xml')
            plates = plate_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(25, 25))

            for (x, y, w, h) in plates:
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                plate_roi = gray[y:y+h, x:x+w]
                result = reader.readtext(plate_roi)

                for bbox, text, conf in result:
                    country = "Unknown"
                    if len(text) >= 2:
                        prefix = text[:2].upper()
                        indian_states = ['GJ', 'MH', 'DL', 'RJ', 'UP', 'MP', 'TN', 'KA', 'WB']
                        if prefix in indian_states:
                            country = "India"
                    detected_data.append({"Number Plate": text, "Country": country})
                    display_text = f"{country}: {text}"
                    cv2.putText(img, display_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36,255,12), 2)

            # Save processed image
            processed_filename = f"processed_{filename}"
            processed_path = os.path.join(app.config['UPLOAD_FOLDER'], processed_filename)
            cv2.imwrite(processed_path, img)
            processed_image_path = 'uploads/' + processed_filename

            # Save to Excel (append below existing data)
            output_excel_path = os.path.join(app.config['UPLOAD_FOLDER'], 'number_plate_results.xlsx')
            df_new = pd.DataFrame(detected_data)
            if os.path.exists(output_excel_path):
                df_existing = pd.read_excel(output_excel_path)
                df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            else:
                df_combined = df_new
            df_combined.to_excel(output_excel_path, index=False)

    return render_template('index.html',
                           uploaded_image_path=uploaded_image_path,
                           processed_image_path=processed_image_path,
                           detected_data=detected_data)

if __name__ == '__main__':
    app.run(debug=True)
