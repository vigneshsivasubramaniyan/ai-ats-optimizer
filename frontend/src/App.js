import React, { useState } from 'react';
import { Upload, FileText, Download, Loader2, CheckCircle, AlertCircle, FileType } from 'lucide-react';

const ATSResumeBuilder = () => {
  const [resumeFile, setResumeFile] = useState(null);
  const [jdFile, setJdFile] = useState(null);
  const [resumeText, setResumeText] = useState('');
  const [jdText, setJdText] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  const API_BASE_URL = '/api';

  const handleFileChange = (e, type) => {
    const file = e.target.files[0];
    if (file && file.type === 'application/pdf') {
      if (file.size > 10 * 1024 * 1024) {
        setError('File size must be less than 10MB');
        return;
      }
      if (type === 'resume') {
        setResumeFile(file);
      } else {
        setJdFile(file);
      }
      setError('');
    } else {
      setError('Please select a valid PDF file');
    }
  };

  const handleSubmit = async () => {
    if (!resumeFile && !resumeText) {
      setError('Please provide either resume text or upload a resume PDF');
      return;
    }
    if (!jdFile && !jdText) {
      setError('Please provide either job description text or upload a JD PDF');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    const formData = new FormData();
    if (resumeFile) formData.append('resume_pdf', resumeFile);
    if (resumeText) formData.append('resume_text', resumeText);
    if (jdFile) formData.append('jd_pdf', jdFile);
    if (jdText) formData.append('jd_text', jdText);

    try {
      const response = await fetch(`${API_BASE_URL}/build-resume`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to process resume. Ensure backend is running.');
      }

      setResult(data);
    } catch (err) {
      setError(err.message || 'An error occurred while processing your resume');
    } finally {
      setLoading(false);
    }
  };

  const downloadPDF = async () => {
    if (!result || !result.html) {
      setError('No resume HTML available to convert');
      return;
    }

    setDownloadingPdf(true);
    setError('');

    try {
      const response = await fetch(`${API_BASE_URL}/download-pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ html: result.html }),
      });

      const contentType = response.headers.get('content-type');

      if (contentType && contentType.includes('application/json')) {
        const errorData = await response.json();
        if (errorData.client_side_conversion) {
          openBrowserPrint();
          return;
        }
        throw new Error(errorData.error || 'PDF conversion failed on server');
      }

      const blob = await response.blob();
      if (blob.size < 1000) {
        throw new Error(`PDF generation failed - file is only ${blob.size} bytes.`);
      }

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'ats-optimized-resume.pdf';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message || 'Failed to download PDF.');
    } finally {
      setDownloadingPdf(false);
    }
  };

  const openBrowserPrint = () => {
    const printWindow = window.open('', '_blank');
    printWindow.document.write(result.html);
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => printWindow.print(), 250);
  };

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-900">
      {/* Header */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <div className="bg-blue-600 p-2 rounded-lg">
              <FileText className="h-6 w-6 text-white" />
            </div>
            <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600">
              ATS Optimizer AI
            </h1>
          </div>
          <div className="flex items-center gap-2 text-sm text-slate-500 font-medium">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-green-50 border border-green-200 text-green-700">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              Local AI · Qwen 8B
            </span>
            <span>v4.0.0</span>
          </div>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center mb-12">
          <h2 className="text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl mb-4">
            AI-Powered Resume Optimization
          </h2>
          <p className="max-w-2xl mx-auto text-lg text-slate-600">
            Uses a local <strong>Qwen 8B</strong> model via Ollama to tailor your resume to the job description — privately, with no data leaving your machine.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 items-start">
          {/* Input Section */}
          <div className="lg:col-span-2 space-y-6">

            {/* Resume Upload Card */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 transition-all hover:shadow-md">
              <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 text-blue-600 text-xs font-bold">1</span>
                Your Resume
              </h3>

              <div className="space-y-4">
                <div className="relative group">
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={(e) => handleFileChange(e, 'resume')}
                    className="hidden"
                    id="resume-upload"
                  />
                  <label
                    htmlFor="resume-upload"
                    className={`flex flex-col items-center justify-center w-full h-28 border-2 border-dashed rounded-xl cursor-pointer transition-all duration-200
                      ${resumeFile ? 'border-blue-500 bg-blue-50/50' : 'border-slate-300 hover:border-blue-400 hover:bg-slate-50'}`}
                  >
                    {resumeFile ? (
                      <>
                        <CheckCircle className="h-7 w-7 text-blue-500 mb-2" />
                        <span className="text-sm font-medium text-slate-900">{resumeFile.name}</span>
                        <span className="text-xs text-slate-500 mt-1">Click to change</span>
                      </>
                    ) : (
                      <>
                        <div className="p-2 bg-slate-100 rounded-full mb-2 group-hover:scale-110 transition-transform">
                          <Upload className="h-5 w-5 text-slate-500" />
                        </div>
                        <span className="text-sm font-medium text-slate-600">Upload Resume PDF</span>
                        <span className="text-xs text-slate-400 mt-1">Or paste text below</span>
                      </>
                    )}
                  </label>
                </div>

                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t border-slate-200" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-white px-2 text-slate-400 font-medium">Or</span>
                  </div>
                </div>

                <textarea
                  value={resumeText}
                  onChange={(e) => setResumeText(e.target.value)}
                  placeholder="Paste your raw resume text here if you don't have a PDF..."
                  className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all text-sm resize-y min-h-[80px]"
                />
              </div>
            </div>

            {/* JD Upload Card */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 transition-all hover:shadow-md">
              <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-indigo-100 text-indigo-600 text-xs font-bold">2</span>
                Job Description
              </h3>

              <div className="space-y-4">
                <div className="relative group">
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={(e) => handleFileChange(e, 'jd')}
                    className="hidden"
                    id="jd-upload"
                  />
                  <label
                    htmlFor="jd-upload"
                    className={`flex flex-col items-center justify-center w-full h-28 border-2 border-dashed rounded-xl cursor-pointer transition-all duration-200
                      ${jdFile ? 'border-indigo-500 bg-indigo-50/50' : 'border-slate-300 hover:border-indigo-400 hover:bg-slate-50'}`}
                  >
                    {jdFile ? (
                      <>
                        <CheckCircle className="h-7 w-7 text-indigo-500 mb-2" />
                        <span className="text-sm font-medium text-slate-900">{jdFile.name}</span>
                        <span className="text-xs text-slate-500 mt-1">Click to change</span>
                      </>
                    ) : (
                      <>
                        <div className="p-2 bg-slate-100 rounded-full mb-2 group-hover:scale-110 transition-transform">
                          <FileType className="h-5 w-5 text-slate-500" />
                        </div>
                        <span className="text-sm font-medium text-slate-600">Upload JD PDF</span>
                        <span className="text-xs text-slate-400 mt-1">Or paste text below</span>
                      </>
                    )}
                  </label>
                </div>

                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t border-slate-200" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-white px-2 text-slate-400 font-medium">Or</span>
                  </div>
                </div>

                <textarea
                  value={jdText}
                  onChange={(e) => setJdText(e.target.value)}
                  placeholder="Paste the job description text here if you don't have a PDF..."
                  className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all text-sm resize-y min-h-[80px]"
                />
              </div>
            </div>

            {/* Action Section */}
            <div className="space-y-4">
              {error && (
                <div className="p-4 rounded-xl bg-red-50 border border-red-100 flex items-start gap-3">
                  <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-700 font-medium">{error}</p>
                </div>
              )}

              <button
                onClick={handleSubmit}
                disabled={loading}
                className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-4 px-6 rounded-xl font-semibold shadow-lg shadow-blue-500/30 hover:shadow-blue-500/40 hover:scale-[1.02] disabled:opacity-70 disabled:cursor-not-allowed disabled:hover:scale-100 transition-all duration-200 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="animate-spin h-5 w-5" />
                    Optimizing with Local AI...
                  </>
                ) : (
                  <>
                    Generate AI Resume
                    <span className="text-white/80">→</span>
                  </>
                )}
              </button>

              <p className="text-xs text-center text-slate-400">
                🔒 Fully private · Your data never leaves your machine
              </p>
            </div>
          </div>

          {/* Results Section */}
          <div className="lg:col-span-3 lg:sticky lg:top-8 space-y-6">
            {result ? (
              <div className="bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
                <div className="p-4 bg-slate-50 border-b border-slate-200 flex justify-between items-center">
                  <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-green-500" />
                    Optimization Complete
                  </h3>
                  <div className="flex gap-2">
                    <button
                      onClick={openBrowserPrint}
                      className="bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 shadow-sm"
                    >
                      🖨️ Print
                    </button>
                    <button
                      onClick={downloadPDF}
                      disabled={downloadingPdf}
                      className="bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {downloadingPdf ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Converting...
                        </>
                      ) : (
                        <>
                          <Download className="h-4 w-4" />
                          Download PDF
                        </>
                      )}
                    </button>
                  </div>
                </div>

                <div className="p-8 bg-white overflow-auto max-h-[900px]" style={{ fontSize: '15px' }}>
                  <div
                    className="max-w-full"
                    dangerouslySetInnerHTML={{ __html: result.html }}
                  />
                </div>
              </div>
            ) : (
              <div className="h-full min-h-[600px] bg-white rounded-2xl shadow-sm border border-slate-200 border-dashed flex flex-col items-center justify-center p-8 text-center bg-slate-50/50">
                <div className="w-16 h-16 bg-white rounded-full shadow-sm flex items-center justify-center mb-4">
                  <FileText className="h-8 w-8 text-slate-300" />
                </div>
                <h3 className="text-lg font-medium text-slate-900 mb-2">No Resume Generated Yet</h3>
                <p className="text-slate-500 max-w-xs mx-auto text-sm">
                  Upload your resume and job description, then click Generate to see the AI-optimized result.
                </p>
                <div className="mt-6 p-4 bg-blue-50 rounded-xl border border-blue-100 text-left max-w-sm">
                  <p className="text-xs font-semibold text-blue-700 mb-2">💡 Prerequisites</p>
                  <ol className="text-xs text-blue-600 space-y-1 list-decimal list-inside">
                    <li>Install Ollama: <code className="bg-blue-100 px-1 rounded">ollama serve</code></li>
                    <li>Pull the model: <code className="bg-blue-100 px-1 rounded">ollama pull qwen:8b</code></li>
                    <li>Start this backend: <code className="bg-blue-100 px-1 rounded">python app.py</code></li>
                  </ol>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default ATSResumeBuilder;