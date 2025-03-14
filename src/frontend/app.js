// Constants
const API_URL = 'http://localhost:8123';
const ALLOWED_EXTENSIONS = ['txt', 'pdf', 'md', 'csv', 'xlsx'];

// State management
let sessionId = generateUUID();
let currentFile = null;
let processedFilePath = null;
let fileContent = null;
let analysisResult = null;
let chatHistory = [];
let isProcessing = false;
let progressId = null;

// DOM Elements
document.addEventListener('DOMContentLoaded', () => {
    // Add highlight.js for code syntax highlighting
    const highlightCss = document.createElement('link');
    highlightCss.rel = 'stylesheet';
    highlightCss.href = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/styles/default.min.css';
    document.head.appendChild(highlightCss);
    
    const highlightJs = document.createElement('script');
    highlightJs.src = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/highlight.min.js';
    document.head.appendChild(highlightJs);
    
    // File name display
    const fileInput = document.getElementById('file-upload');
    const fileNameDisplay = document.getElementById('file-name');
    
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            fileNameDisplay.textContent = fileInput.files[0].name;
        } else {
            fileNameDisplay.textContent = 'No file chosen';
        }
    });
    
    // Tab switching
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.getAttribute('data-tab');
            
            // Update active tab button
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // Show active tab content
            tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === `${tabName}-tab`) {
                    content.classList.add('active');
                }
            });
        });
    });
    
    // File upload
    const uploadBtn = document.getElementById('upload-btn');
    const uploadStatus = document.getElementById('upload-status');
    
    uploadBtn.addEventListener('click', () => {
        const file = fileInput.files[0];
        if (!file) {
            showStatus('Please select a file to upload.', 'error');
            return;
        }
        
        if (!isAllowedFile(file.name)) {
            showStatus('Invalid file type. Please upload txt, pdf, md, csv, or xlsx files.', 'error');
            return;
        }
        
        const uploadType = document.querySelector('input[name="upload-type"]:checked').value;
        handleFileUpload(file, uploadType);
    });
    
    // Chat functionality
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const chatContainer = document.getElementById('chat-container');
    const clearChatBtn = document.getElementById('clear-chat');
    
    sendBtn.addEventListener('click', () => {
        sendChatMessage();
    });
    
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendChatMessage();
        }
    });
    
    clearChatBtn.addEventListener('click', () => {
        clearChat();
    });
    
    // Helper function for sending chat messages
    function sendChatMessage() {
        const query = chatInput.value.trim();
        if (query) {
            sendMessage(query);
            chatInput.value = '';
        }
    }
    
    // Add CSS for markdown tables
    const tableStyles = document.createElement('style');
    tableStyles.textContent = `
        .markdown-table {
            border-collapse: collapse;
            margin: 15px 0;
            width: 100%;
        }
        .markdown-table th, .markdown-table td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        .markdown-table th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        .markdown-table tr:nth-child(even) {
            background-color: #f9f9f9;
        }
    `;
    document.head.appendChild(tableStyles);
});

// Helper functions
function generateUUID() {
    return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
        (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
}

function isAllowedFile(filename) {
    const extension = filename.split('.').pop().toLowerCase();
    return ALLOWED_EXTENSIONS.includes(extension);
}

function showStatus(message, type = 'info') {
    const statusElement = document.getElementById('upload-status');
    statusElement.textContent = message;
    statusElement.className = '';
    statusElement.classList.add(`status-${type}`);
}

async function handleFileUpload(file, uploadType) {
    showStatus('Processing file... This may take a while for large documents.', 'info');
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        if (uploadType === 'chat') {
            const response = await fetch(`${API_URL}/api/v1/upload-file`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.status === 'success' || result.status === 'processing') {
                currentFile = result.file_path;
                progressId = result.progress_id;
                
                if (file.name.toLowerCase().endsWith('.pdf')) {
                    showStatus('PDF processing started. This may take several minutes...', 'info');
                    monitorPdfProcessing();
                } else {
                    showStatus(`File uploaded for chat context: ${file.name}`, 'success');
                    processedFilePath = currentFile;
                    displayFilePreview(file);
                }
            } else {
                showStatus(`Error uploading file: ${result.message}`, 'error');
            }
        } else if (uploadType === 'analysis') {
            const response = await fetch(`${API_URL}/api/v1/upload-report`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.analysis) {
                analysisResult = result.analysis;
                showStatus(`Financial report analyzed: ${file.name}`, 'success');
                displayAnalysisResults();
                displayFilePreview(file);
            } else {
                showStatus(`Error analyzing report: ${result.message}`, 'error');
            }
        }
    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
    }
}

async function monitorPdfProcessing() {
    isProcessing = true;
    
    while (isProcessing) {
        try {
            const response = await fetch(`${API_URL}/api/v1/processing-status/${progressId}`);
            const statusResult = await response.json();
            
            if (statusResult.status === 'completed' || statusResult.status === 'success') {
                showStatus('Document processing completed!', 'success');
                if (statusResult.processed_file_path) {
                    processedFilePath = statusResult.processed_file_path;
                }
                isProcessing = false;
                break;
            } else if (statusResult.status === 'processing') {
                const progress = statusResult.progress || 0;
                showStatus(`Processing: ${progress.toFixed(1)}% complete. ${statusResult.message || ''}`, 'info');
                await new Promise(resolve => setTimeout(resolve, 5000));
            } else if (statusResult.status === 'error') {
                showStatus(`Error processing document: ${statusResult.message}`, 'error');
                isProcessing = false;
                break;
            } else {
                showStatus('Waiting for status update...', 'info');
                await new Promise(resolve => setTimeout(resolve, 5000));
            }
        } catch (error) {
            showStatus(`Error checking status: ${error.message}`, 'error');
            await new Promise(resolve => setTimeout(resolve, 5000));
        }
    }
}

async function displayFilePreview(file) {
    const filePreview = document.querySelector('.file-preview');
    const previewContent = document.getElementById('preview-content');
    
    if (file.type === 'application/pdf') {
        previewContent.textContent = 'PDF file uploaded. Content preview not available.';
    } else {
        try {
            const text = await file.text();
            fileContent = text;
            
            // Limit preview to 500 characters
            const preview = text.length > 500 ? text.substring(0, 500) + '...' : text;
            previewContent.textContent = preview;
        } catch (error) {
            previewContent.textContent = 'Binary file uploaded. Content preview not available.';
        }
    }
    
    filePreview.style.display = 'block';
}

async function sendMessage(query) {
    // Add user message to chat
    addMessageToChat(query, 'user');
    
    // Add to chat history
    chatHistory.push({ role: 'user', content: query });
    
    // Show thinking indicator
    const thinkingElement = document.createElement('div');
    thinkingElement.className = 'chat-message assistant-message';
    thinkingElement.textContent = 'Thinking...';
    document.getElementById('chat-container').appendChild(thinkingElement);
    
    try {
        // Wait for processing to complete if needed
        if (progressId && !processedFilePath) {
            showStatus('Waiting for document processing to complete before answering...', 'info');
            
            while (true) {
                const response = await fetch(`${API_URL}/api/v1/processing-status/${progressId}`);
                const statusResult = await response.json();
                
                if (statusResult.status === 'completed' || statusResult.status === 'success') {
                    if (statusResult.processed_file_path) {
                        processedFilePath = statusResult.processed_file_path;
                    } else {
                        processedFilePath = currentFile;
                    }
                    isProcessing = false;
                    break;
                }
                await new Promise(resolve => setTimeout(resolve, 2000));
            }
        }
        
        // Send query to backend
        const payload = {
            query: query,
            session_id: sessionId
        };
        
        if (currentFile) {
            payload.file_path = currentFile;
        }
        
        if (processedFilePath) {
            payload.processed_file_path = processedFilePath;
        }
        
        const response = await fetch(`${API_URL}/api/v1/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        const result = await response.json();
        
        // Remove thinking indicator
        document.getElementById('chat-container').removeChild(thinkingElement);
        
        // Add assistant response to chat
        addMessageToChat(result.answer, 'assistant');
        
        // Add to chat history
        chatHistory.push({ role: 'assistant', content: result.answer });
        
    } catch (error) {
        // Remove thinking indicator
        document.getElementById('chat-container').removeChild(thinkingElement);
        
        // Show error message
        addMessageToChat(`Error: ${error.message}`, 'assistant');
    }
}

function addMessageToChat(message, role) {
    const chatContainer = document.getElementById('chat-container');
    
    // Remove welcome message if it exists
    const welcomeMessage = chatContainer.querySelector('.welcome-message');
    if (welcomeMessage) {
        chatContainer.removeChild(welcomeMessage);
    }
    
    const messageElement = document.createElement('div');
    messageElement.className = `chat-message ${role}-message`;
    
    // Format message with markdown
    const formattedMessage = formatMessage(message);
    messageElement.innerHTML = formattedMessage;
    
    chatContainer.appendChild(messageElement);
    
    // Apply syntax highlighting to code blocks
    if (window.hljs) {
        messageElement.querySelectorAll('pre code').forEach((block) => {
            window.hljs.highlightBlock(block);
        });
    }
    
    // Make tables responsive
    messageElement.querySelectorAll('.markdown-table').forEach(table => {
        const wrapper = document.createElement('div');
        wrapper.className = 'table-responsive';
        table.parentNode.insertBefore(wrapper, table);
        wrapper.appendChild(table);
    });
    
    // Scroll to bottom
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function formatMessage(message) {
    // Use a markdown library like marked.js to parse markdown
    // First, escape any HTML to prevent XSS attacks
    let formatted = escapeHtml(message);
    
    // Handle dollar signs in financial context
    formatted = formatted.replace(/\\\$/g, '___ESCAPED_DOLLAR___');
    formatted = formatted.replace(/\$(\d+(?:\.\d+)?)/g, '<span class="dollar">$</span>$1');
    formatted = formatted.replace(/___ESCAPED_DOLLAR___/g, '$');
    
    // Code blocks with syntax highlighting
    formatted = formatted.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>');
    
    // Inline code
    formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // Handle tables - improved table handling
    formatted = formatted.replace(/\|(.+)\|\n\|([-:]+\|)+\n((\|.+\|\n)+)/g, function(match) {
        const rows = match.trim().split('\n');
        let tableHtml = '<table class="markdown-table">';
        
        // Header row
        tableHtml += '<thead><tr>';
        const headerCells = rows[0].split('|').slice(1, -1);
        headerCells.forEach(cell => {
            tableHtml += `<th>${cell.trim()}</th>`;
        });
        tableHtml += '</tr></thead>';
        
        // Body rows
        tableHtml += '<tbody>';
        for (let i = 2; i < rows.length; i++) {
            tableHtml += '<tr>';
            const cells = rows[i].split('|').slice(1, -1);
            cells.forEach(cell => {
                tableHtml += `<td>${cell.trim()}</td>`;
            });
            tableHtml += '</tr>';
        }
        tableHtml += '</tbody></table>';
        
        return tableHtml;
    });
    
    // Blockquotes - new addition
    formatted = formatted.replace(/^>\s+(.*$)/gm, '<blockquote>$1</blockquote>');
    
    // Process lists first (before line breaks)
    // Unordered lists - improved
    let listMatches = formatted.match(/(?:^\s*[\-\*]\s+.*(?:\n|$))+/gm);
    if (listMatches) {
        listMatches.forEach(match => {
            const listItems = match.split(/\n/).filter(line => /^\s*[\-\*]\s+/.test(line))
                .map(line => line.replace(/^\s*[\-\*]\s+/, ''));
            const listHtml = '<ul>' + listItems.map(item => `<li>${item}</li>`).join('') + '</ul>';
            formatted = formatted.replace(match, listHtml);
        });
    }
    
    // Ordered lists - improved
    listMatches = formatted.match(/(?:^\s*\d+\.\s+.*(?:\n|$))+/gm);
    if (listMatches) {
        listMatches.forEach(match => {
            const listItems = match.split(/\n/).filter(line => /^\s*\d+\.\s+/.test(line))
                .map(line => line.replace(/^\s*\d+\.\s+/, ''));
            const listHtml = '<ol>' + listItems.map(item => `<li>${item}</li>`).join('') + '</ol>';
            formatted = formatted.replace(match, listHtml);
        });
    }
    
    // Headers
    formatted = formatted.replace(/^### (.*$)/gm, '<h3>$1</h3>');
    formatted = formatted.replace(/^## (.*$)/gm, '<h2>$1</h2>');
    formatted = formatted.replace(/^# (.*$)/gm, '<h1>$1</h1>');
    
    // Bold text
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    formatted = formatted.replace(/__(.*?)__/g, '<strong>$1</strong>');
    
    // Italic text
    formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
    formatted = formatted.replace(/_(.*?)_/g, '<em>$1</em>');
    
    // Strikethrough - new addition
    formatted = formatted.replace(/~~(.*?)~~/g, '<del>$1</del>');
    
    // Horizontal rule - new addition
    formatted = formatted.replace(/^---+$/gm, '<hr>');
    
    // Links
    formatted = formatted.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    
    // Images - new addition
    formatted = formatted.replace(/!\[([^\]]+)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" class="markdown-image">');
    
    // Line breaks (after processing lists)
    formatted = formatted.replace(/\n\n/g, '<br><br>');  // Double line breaks
    formatted = formatted.replace(/\n/g, '<br>');
    
    return formatted;
}

// Helper function to escape HTML and prevent XSS
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

async function clearChat() {
    try {
        const response = await fetch(`${API_URL}/api/v1/clear-chat?session_id=${sessionId}`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            chatHistory = [];
            document.getElementById('chat-container').innerHTML = '';
            showStatus('Chat history cleared', 'success');
        } else {
            showStatus(`Failed to clear chat: ${result.message}`, 'error');
        }
    } catch (error) {
        showStatus(`Error clearing chat: ${error.message}`, 'error');
    }
}

function displayAnalysisResults() {
    const analysisContainer = document.getElementById('analysis-results');
    
    if (analysisResult) {
        let html = '<h2><i class="fas fa-chart-line"></i> Analysis Results</h2>';
        
        if (typeof analysisResult === 'object') {
            for (const [section, content] of Object.entries(analysisResult)) {
                html += `<div class="analysis-section">
                    <h3>${section.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</h3>`;
                
                if (typeof content === 'object') {
                    html += '<div class="analysis-data">';
                    for (const [key, value] of Object.entries(content)) {
                        html += `<p><strong>${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</strong> ${value}</p>`;
                    }
                    html += '</div>';
                } else {
                    html += `<p>${content}</p>`;
                }
                
                html += '</div>';
            }
            
            // Add download button
            html += `<button id="download-analysis">Download Analysis</button>`;
            
            analysisContainer.innerHTML = html;
            
            // Add event listener for download button
            document.getElementById('download-analysis').addEventListener('click', () => {
                const jsonString = JSON.stringify(analysisResult, null, 2);
                const blob = new Blob([jsonString], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                
                const a = document.createElement('a');
                a.href = url;
                a.download = 'financial_analysis.json';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            });
        } else {
            analysisContainer.innerHTML = `<p>${analysisResult}</p>`;
        }
    } else {
        analysisContainer.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-file-invoice-dollar"></i>
                <p>Upload a financial report using the sidebar to see analysis results.</p>
            </div>
        `;
    }
} 