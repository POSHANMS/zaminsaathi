import os
import sys
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Add project root to sys.path to resolve agents module
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from agents.parser_agent import parse_document
from agents.detector_agent import detect_discrepancies
from agents.planner_agent import generate_plan as generate_action_plan

app = Flask(__name__)
# Enable CORS for frontend running on localhost:3000
CORS(app, resources={r"/api/*": {"origins": "*"}})

@app.route('/api/analyse', methods=['POST'])
def analyse():
    try:
        # Check if files are present in the request
        if 'files' not in request.files:
            return jsonify({"error": "No files uploaded. Use form-data key 'files'."}), 400

        uploaded_files = request.files.getlist('files')
        if not uploaded_files or uploaded_files[0].filename == '':
            return jsonify({"error": "No files selected."}), 400

        raw_docs = []
        for file in uploaded_files:
            file_content = file.read().decode('utf-8')
            raw_docs.append(json.loads(file_content))

        if not raw_docs:
            return jsonify({"error": "No valid JSON documents provided."}), 400

        # 1. Run parser_agent on each raw document
        parsed_docs = []
        for doc in raw_docs:
            parsed_docs.append(parse_document(doc))

        # Find primary parsed document to return (prefer RTC)
        main_parsed = parsed_docs[0] if parsed_docs else {}
        for p in parsed_docs:
            if p.get("document_type") == "RTC":
                main_parsed = p
                break

        # 2. Run detector_agent on all documents
        all_discrepancies = []
        permission_granted = True
        cross_check_passed = True
        denial_reason = None

        for parsed_doc in parsed_docs:
            det_res = detect_discrepancies(parsed_doc, raw_docs)
            if not det_res.get("permission_granted", True):
                permission_granted = False
                denial_reason = det_res.get("denial_reason")
            if not det_res.get("cross_check_passed", True):
                cross_check_passed = False
            if "discrepancies_found" in det_res:
                all_discrepancies.extend(det_res["discrepancies_found"])

        detector_result = {
            "document_id": main_parsed.get("document_id", "unknown"),
            "permission_granted": permission_granted,
            "discrepancies_found": all_discrepancies,
            "cross_check_passed": cross_check_passed
        }
        if not permission_granted and denial_reason:
            detector_result["denial_reason"] = denial_reason

        # 3. Run planner_agent on the detector result
        planner_result = generate_action_plan(detector_result)

        return jsonify({
            "parser": main_parsed,
            "detector": detector_result,
            "planner": planner_result
        })

    except Exception as e:
        # Return 500 error if agent fails
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Start Flask app on port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
