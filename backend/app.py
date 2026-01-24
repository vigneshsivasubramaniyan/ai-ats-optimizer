from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
import PyPDF2
import io
import base64
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except:
    WEASYPRINT_AVAILABLE = False
    
try:
    import pdfkit
    PDFKIT_AVAILABLE = True
except:
    PDFKIT_AVAILABLE = False

import requests
import json
import re
import logging

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_file):
    """Extract text from PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            result = page.extract_text()
            if result:
                text += result
        return text
    except Exception as e:
        raise Exception(f"Error extracting PDF: {str(e)}")

def generate_resume_with_ai(resume_text, jd_text, api_key):
    """Generate ATS-friendly resume HTML using Perplexity API"""
    
    merged_content = f"RESUME CONTENT:\n{resume_text}\n\nJOB DESCRIPTION:\n{jd_text}"
    
    url = "https://api.perplexity.ai/chat/completions"
    
    system_prompt = """You are a professional resume writer. Build a single, ATS-friendly resume by combining and aligning the candidate's resume with the job description contained in user input.

Rules for content:
Tailor the resume to the JD while staying truthful to the candidate's information. Prioritize skills/keywords the JD demands. Rephrase; do not invent facts.
Omit sections that have no data instead of adding placeholders.
Prefer the candidate's details when resume and JD conflict; only adjust wording to match JD terminology.
Keep the resume concise and within 2 pages maximum.

Rules for layout & style:
Output one valid HTML document only (no Markdown, no code fences, no JSON, no citations, no comments, no <think> or similar tags, no text before or after).
Use inline CSS inside <style> in the <head>; no external assets (fonts, scripts, images, icons, tables).

CRITICAL CSS REQUIREMENTS - Copy these exact styles:
body {{ margin: 25px 30px; line-height: 1.25; font-size: 13.5px; font-family: Arial, sans-serif; }}
h1 {{ font-size: 26px; margin: 0 0 5px 0; text-align: center; font-weight: bold; }}
.contact {{ font-size: 11px; margin: 0 0 12px 0; text-align: center; }}
h2 {{ font-size: 17px; margin: 12px 0 4px 0; padding-bottom: 2px; border-bottom: 1.5px solid #000; font-weight: bold; }}
p {{ margin: 4px 0; }}
ul {{ margin: 4px 0 8px 0; padding-left: 18px; }}
li {{ margin: 2px 0; line-height: 1.3; }}
.job-title {{ font-weight: bold; margin: 6px 0 2px 0; }}
.job-company {{ font-style: italic; margin: 0; }}
.job-date {{ margin: 0 0 3px 0; }}

Structure:
Name at top center (h1), contact below (div.contact)
Section titles as h2 with underline
Skills section: Use category labels in bold followed by comma-separated items (NOT bullet lists)
Experience: Use .job-title, .job-company, .job-date classes, then <ul> for achievements
Keep everything tight and compact - NO extra whitespace between sections

Output requirement (critical):
Return only:
<!DOCTYPE html>
<html>...full document with inline <style>...</html>"""

    user_prompt = f"""Generate an ATS-friendly resume in HTML with extremely compact spacing.

Input data:
{merged_content}

MANDATORY CSS (use exactly as provided):
body {{ margin: 25px 30px; line-height: 1.25; font-size: 13.5px; font-family: Arial, sans-serif; }}
h1 {{ font-size: 26px; margin: 0 0 5px 0; text-align: center; font-weight: bold; }}
.contact {{ font-size: 11px; margin: 0 0 12px 0; text-align: center; }}
h2 {{ font-size: 17px; margin: 12px 0 4px 0; padding-bottom: 2px; border-bottom: 1.5px solid #000; font-weight: bold; }}
p {{ margin: 4px 0; }}
ul {{ margin: 4px 0 8px 0; padding-left: 18px; }}
li {{ margin: 2px 0; line-height: 1.3; }}
.job-title {{ font-weight: bold; margin: 6px 0 2px 0; }}
.job-company {{ font-style: italic; margin: 0; }}
.job-date {{ margin: 0 0 3px 0; }}

STRUCTURE REQUIREMENTS:
1. Name (h1) → Contact info (div.contact) → Sections (h2)
2. Skills: Format as "Category: skill1, skill2, skill3" (NO bullets, just paragraphs)
3. Experience: job-title/company/date divs, then <ul> for bullet achievements
4. Keep spacing TIGHT - minimize all gaps
5. Aim for 2 pages max

Output ONLY the complete HTML document. No explanations."""

    payload = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        logger.info("Sending request to Perplexity API...")
        response = requests.post(url, json=payload, headers=headers)
        
        if not response.ok:
            error_detail = response.text
            logger.error(f"Perplexity API Error: {response.status_code} - {error_detail}")
            raise Exception(f"Perplexity API Error: {error_detail}")
            
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        logger.info(f"Received {len(content)} chars from Perplexity")
        
        # Extract HTML using multiple patterns
        patterns = [
            r'<!DOCTYPE html>[\s\S]*?</html>',
            r'<html[\s\S]*?</html>',
            r'```html\s*(<!DOCTYPE html>[\s\S]*?</html>)\s*```',
            r'```html\s*(<html[\s\S]*?</html>)\s*```',
            r'```\s*(<!DOCTYPE html>[\s\S]*?</html>)\s*```',
            r'```\s*(<html[\s\S]*?</html>)\s*```'
        ]
        
        clean_html = None
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                clean_html = match.group(1) if match.lastindex and match.lastindex > 0 else match.group(0)
                break
        
        if clean_html:
            if not clean_html.strip().startswith('<!DOCTYPE html>'):
                clean_html = '<!DOCTYPE html>\n' + clean_html
            logger.info(f"✓ Extracted HTML: {len(clean_html)} chars")
            return clean_html
        else:
            logger.warning("No HTML found, wrapping content")
            return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        h1 {{ text-align: center; }}
    </style>
</head>
<body>
{content}
</body>
</html>"""
            
    except Exception as e:
        logger.error(f"AI Generation Failed: {str(e)}")
        raise Exception(f"AI Generation Failed: {str(e)}")


@app.route('/')
@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'ATS Resume Builder API',
        'version': '3.0.0',
        'pdf_engines': {
            'weasyprint': WEASYPRINT_AVAILABLE,
            'pdfkit': PDFKIT_AVAILABLE
        }
    }), 200

@app.route('/api/build-resume', methods=['POST'])
def build_resume():
    """Main endpoint to build ATS resume"""
    try:
        resume_text = request.form.get('resume_text', '')
        jd_text = request.form.get('jd_text', '')
        api_key = request.form.get('api_key', '')
        resume_pdf = request.files.get('resume_pdf')
        jd_pdf = request.files.get('jd_pdf')
        
        if not api_key:
            return jsonify({'error': 'Perplexity API Key is required'}), 401
        
        # Extract resume text from PDF if provided
        if resume_pdf:
            logger.info("Extracting text from resume PDF...")
            pdf_text = extract_text_from_pdf(resume_pdf)
            if pdf_text:
                resume_text += ' ' + pdf_text
        
        if not resume_text or len(resume_text.strip()) < 10:
            return jsonify({'error': 'No valid resume content provided'}), 400
        
        # Extract JD text from PDF if provided, otherwise use text input
        if jd_pdf:
            logger.info("Extracting text from JD PDF...")
            pdf_jd_text = extract_text_from_pdf(jd_pdf)
            if pdf_jd_text:
                jd_text += ' ' + pdf_jd_text
        
        if not jd_text or len(jd_text.strip()) < 10:
            return jsonify({'error': 'No valid job description provided'}), 400
        
        logger.info("Generating resume with AI...")
        html_resume = generate_resume_with_ai(resume_text, jd_text, api_key)
        
        logger.info(f"✓ Resume generated successfully")
        
        return jsonify({
            'html': html_resume,
            'success': True
        })
        
    except Exception as e:
        logger.error(f"Error in build_resume: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download-pdf', methods=['POST'])
def download_pdf():
    """Convert HTML to PDF - trying multiple methods"""
    html_content = None
    
    try:
        data = request.get_json()
        html_content = data.get('html')
        
        if not html_content:
            return jsonify({'error': 'No HTML content provided'}), 400
        
        logger.info("="*60)
        logger.info(f"PDF Conversion - HTML length: {len(html_content)}")
        
        # Ensure proper HTML structure
        if not html_content.strip().startswith('<!DOCTYPE html>'):
            html_content = '<!DOCTYPE html>\n' + html_content
        
        pdf_bytes = None
        method_used = None
        
        # Method 1: Try WeasyPrint
        if WEASYPRINT_AVAILABLE and pdf_bytes is None:
            try:
                logger.info("Trying WeasyPrint...")
                logger.debug(f"HTML preview (first 500 chars):\n{html_content[:500]}")
                logger.debug(f"HTML preview (last 300 chars):\n{html_content[-300:]}")
                
                pdf_bytes = HTML(string=html_content).write_pdf()
                method_used = "weasyprint"
                logger.info(f"✓ WeasyPrint succeeded: {len(pdf_bytes)} bytes")
            except Exception as e:
                logger.error(f"WeasyPrint failed: {str(e)}")
                import traceback
                logger.error(f"Full traceback:\n{traceback.format_exc()}")
                logger.error(f"HTML that failed (first 1000 chars):\n{html_content[:1000]}")
        
        # Method 2: Try pdfkit
        if PDFKIT_AVAILABLE and pdf_bytes is None:
            try:
                logger.info("Trying pdfkit...")
                options = {
                    'page-size': 'Letter',
                    'margin-top': '0.75in',
                    'margin-right': '0.75in',
                    'margin-bottom': '0.75in',
                    'margin-left': '0.75in',
                    'encoding': 'UTF-8',
                    'enable-local-file-access': None
                }
                pdf_bytes = pdfkit.from_string(html_content, False, options=options)
                method_used = "pdfkit"
                logger.info(f"✓ pdfkit succeeded: {len(pdf_bytes)} bytes")
            except Exception as e:
                logger.error(f"pdfkit failed: {str(e)}")
                import traceback
                logger.error(f"Full traceback:\n{traceback.format_exc()}")
        
        # Method 3: Return HTML with instructions (fallback)
        if pdf_bytes is None:
            logger.error("All PDF conversion methods failed!")
            logger.info("Returning HTML for client-side conversion")
            
            # Return a special response with HTML
            return jsonify({
                'error': 'Server PDF conversion unavailable',
                'html': html_content,
                'message': 'Please use browser print or install WeasyPrint/pdfkit on server',
                'client_side_conversion': True
            }), 500
        
        # Validate PDF size
        if len(pdf_bytes) < 1000:
            logger.error(f"PDF too small: {len(pdf_bytes)} bytes")
            logger.debug(f"HTML:\n{html_content[:1000]}")
            return jsonify({
                'error': 'Generated PDF is too small',
                'html': html_content,
                'pdf_size': len(pdf_bytes)
            }), 400
        
        # Create response
        pdf_io = io.BytesIO(pdf_bytes)
        pdf_io.seek(0)
        
        logger.info(f"✓ Sending PDF ({method_used}): {len(pdf_bytes)} bytes")
        logger.info("="*60)
        
        response = make_response(send_file(
            pdf_io,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='ats-resume.pdf'
        ))
        
        # Add headers to prevent caching issues
        response.headers['Content-Length'] = len(pdf_bytes)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Return HTML as fallback
        return jsonify({
            'error': f'PDF conversion failed: {str(e)}',
            'html': html_content if html_content else '',
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/preview-html', methods=['POST'])
def preview_html():
    """Preview HTML"""
    try:
        data = request.get_json()
        html_content = data.get('html', '')
        return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-pdf', methods=['GET'])
def test_pdf():
    """Test PDF generation with simple HTML"""
    try:
        test_html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
    </style>
</head>
<body>
    <h1>Test PDF</h1>
    <p>This is a test PDF generated by WeasyPrint.</p>
    <p>If you can read this, PDF generation is working!</p>
</body>
</html>"""
        
        logger.info("Testing PDF generation with simple HTML...")
        pdf_bytes = HTML(string=test_html).write_pdf()
        logger.info(f"Test PDF generated: {len(pdf_bytes)} bytes")
        
        pdf_io = io.BytesIO(pdf_bytes)
        pdf_io.seek(0)
        
        return send_file(
            pdf_io,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='test.pdf'
        )
    except Exception as e:
        logger.error(f"Test PDF failed: {str(e)}")
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

if __name__ == '__main__':
    logger.info(f"WeasyPrint available: {WEASYPRINT_AVAILABLE}")
    logger.info(f"pdfkit available: {PDFKIT_AVAILABLE}")
    app.run(debug=True, host='0.0.0.0', port=5000)