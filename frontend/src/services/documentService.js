import { authAxios } from './authService';
import FileSaver from 'file-saver';
import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable"
// Remove the '/api' prefix since it's already included in the baseURL in authAxios
const API_URL = '/documents';

const generatePDF = (jsonData) => {
  console.log(jsonData)
  if (!jsonData) {
    alert("Please upload a JSON file first!");
    return;
  }

  const doc = new jsPDF();
  doc.text("JSON Data PDF", 10, 10);

  const keys = Object.keys(jsonData);
  const values = Object.values(jsonData);

  const tableData = keys.map((key, index) => [key, JSON.stringify(values[index])]);

  autoTable(doc,{
    head: [["Key", "Value"]],
    body: tableData,
  });
  

  doc.save("converted_data.pdf");
};
export const generatePDFFromJSON = (jsonData) => {
  // Initialize the PDF document
  console.log(jsonData)
  const doc = new jsPDF();
  
  // Add title
  doc.setFontSize(18);
  doc.text(`Analysis Report: ${jsonData.filename}`, 14, 22);
  
  // Add document info
  doc.setFontSize(12);
  doc.text(`Document Type: ${jsonData.document_type}`, 14, 32);
  doc.text(`Upload Date: ${jsonData.upload_date}`, 14, 38);
  
  // Add analysis summary
  doc.setFontSize(14);
  doc.text('Clause Analysis', 14, 48);
  console.log("test1")
  // Prepare risk level distribution data
  const riskCounts = {
    high: 0,
    medium: 0,
    low: 0,
    negligible: 0
  };
  
  jsonData.clauses.forEach(clause => {
    riskCounts[clause.risk_level] += 1;
  });
  console.log("test2")
  
  // Add risk distribution table
  doc.setFontSize(12);
  doc.text('Risk Distribution', 14, 58);
  
  doc.autoTable({
    startY: 62,
    head: [['Risk Level', 'Count']],
    body: [
      ['High', riskCounts.high],
      ['Medium', riskCounts.medium],
      ['Low', riskCounts.low],
      ['Negligible', riskCounts.negligible]
    ],
    theme: 'striped',
    headStyles: { fillColor: [66, 66, 66] }
  });
  
  // Add clauses table
  const tableY = doc.lastAutoTable.finalY + 10;
  console.log("test3")
  doc.text('Detailed Clause Analysis', 14, tableY);
  
  const tableRows = jsonData.clauses.map(clause => [
    clause.type.replace('_', ' '),
    clause.risk_level,
    clause.risk_score.toFixed(2),
    clause.explanation.slice(0, 60) + (clause.explanation.length > 60 ? '...' : '')
  ]);
  console.log("test4")
  
  doc.autoTable({
    startY: tableY + 4,
    head: [['Clause Type', 'Risk Level', 'Score', 'Explanation']],
    body: tableRows,
    theme: 'grid',
    headStyles: { fillColor: [66, 66, 66] },
    columnStyles: {
      0: { cellWidth: 40 },
      1: { cellWidth: 30 },
      2: { cellWidth: 20 },
      3: { cellWidth: 'auto' }
    },
    styles: { overflow: 'ellipsize', cellWidth: 'wrap' }
  });
  console.log("test5")
  
  // For each clause, add a detailed section
  let currentPage = 1;
  let currentY = doc.previousAutoTable.finalY + 10;
  
  jsonData.clauses.forEach((clause, index) => {
    // Check if we need a new page
    if (currentY > 260) {
      doc.addPage();
      currentPage++;
      currentY = 20;
    }
    
    // Add clause details
    doc.setFontSize(12);
    doc.text(`${index + 1}. ${clause.type.replace('_', ' ').toUpperCase()}`, 14, currentY);
    currentY += 6;
    
    doc.setFontSize(10);
    doc.text(`Risk Level: ${clause.risk_level} (${clause.risk_score.toFixed(2)})`, 14, currentY);
    currentY += 5;
    
    doc.text(`Explanation: ${clause.explanation}`, 14, currentY);
    currentY += 5;
    
    // Wrap text for clause content
    const textLines = doc.splitTextToSize(`Clause Text: ${clause.text}`, 180);
    doc.text(textLines, 14, currentY);
    
    currentY += textLines.length * 5 + 10; // Adjust Y position based on text height
  });
  console.log("test6")
  // Save the PDF
  doc.save(`analysis_report_${jsonData.filename.split('.')[0]}.pdf`);
};
// Upload a document for analysis
export const uploadDocument = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await authAxios.post(`${API_URL}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  } catch (error) {
    throw error.response ? error.response.data : new Error('Server error');
  }
};

// Get document analysis results
export const getDocumentAnalysis = async (documentId) => {
  try {
    const response = await authAxios.get(`${API_URL}/${documentId}`);
    return response.data;
  } catch (error) {
    throw error.response ? error.response.data : new Error('Server error');
  }
};

// Get list of user's documents
export const getUserDocuments = async () => {
  try {
    const response = await authAxios.get(`${API_URL}/user`);
    return response.data;
  } catch (error) {
    throw error.response ? error.response.data : new Error('Server error');
  }
};

// Query a document
export const queryDocument = async (documentId, query) => {
  try {
    const response = await authAxios.post(`${API_URL}/${documentId}/query`, { query });
    return response.data;
  } catch (error) {
    throw error.response ? error.response.data : new Error('Server error');
  }
};

// Download the original document
export const downloadDocument = async (documentId, filename) => {
  try {
    const response = await authAxios.get(`${API_URL}/${documentId}/download`, {
      responseType: 'blob',
    });
    
    // Use file-saver to save the file
    FileSaver.saveAs(response.data, filename);
    
    return true;
  } catch (error) {
    throw error.response ? error.response.data : new Error('Server error');
  }
};

// Download analysis report as PDF
export const downloadAnalysisReport = async (documentId, filename) => {
  try {
    const response = await authAxios.get(`${API_URL}/${documentId}/report`, {
      responseType: 'json',
    });
    const jsonString = JSON.stringify(response.data);

// Create a Blob object with the JSON string and set the content type as "application/json"
    const blob = new Blob([jsonString], { type: "application/json" });
    // Use file-saver to save the file
    generatePDF(response.data)
    // try {
    //   const response = await authAxios.get(`${API_URL}/${documentId}/report`, {
    //     responseType: 'blob',
    //   });
    //   // Use file-saver to save the file
    //   FileSaver.saveAs(blob, `${filename.split('.')[0]}_analysis_report.pdf`);
    
    return true;
  } catch (error) {
    throw error.response ? error.response.data : new Error('Server error');
  }
};

// Save analysis to local folder
export const saveAnalysisToLocal = async (analysis) => {
  try {
    // Convert analysis to JSON string
    const analysisJson = JSON.stringify(analysis, null, 2);
    
    // Create a blob from the JSON
    const blob = new Blob([analysisJson], { type: 'application/json' });
    
    // Use file-saver to save the file
    FileSaver.saveAs(blob, `document_analysis_${analysis.document_id}.json`);
    
    return true;
  } catch (error) {
    throw new Error('Failed to save analysis to local folder');
  }
};