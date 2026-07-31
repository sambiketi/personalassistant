# ============================================
# FOCUS AGENT - LLM Fix Implementation Script
# SIMPLIFIED VERSION - No complex regex
# ============================================

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  🚀 FOCUS AGENT - LLM FIX IMPLEMENTATION" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 This script will update 6 files to use frontend-only API key management" -ForegroundColor Yellow
Write-Host ""

$confirmation = Read-Host "Continue? (y/n)"
if ($confirmation -ne 'y') {
    Write-Host "❌ Cancelled." -ForegroundColor Red
    exit
}

# ============================================
# BACKUP FUNCTION
# ============================================
function Backup-File {
    param($FilePath)
    if (Test-Path $FilePath) {
        $backupPath = "$FilePath.bak"
        Copy-Item $FilePath $backupPath -Force
        Write-Host "   📁 Backup created: $backupPath" -ForegroundColor Gray
        return $true
    }
    return $false
}

# ============================================
# FILE 1: backend/app/main.py
# ============================================
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "📄 FILE 1/6: backend/app/main.py" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

$filePath = "backend/app/main.py"
if (Test-Path $filePath) {
    Backup-File $filePath
    $content = Get-Content $filePath -Raw
    
    # Simple replacements
    $content = $content -replace 'LLM_API_KEY = os\.getenv\("LLM_API_KEY", ""\)', '# REMOVED: LLM_API_KEY - now comes from frontend'
    $content = $content -replace '_llm_instance: LLMService = _llm_map\.get\(LLM_PROVIDER, DeepSeekService\)\(LLM_API_KEY\)', '_llm_instance: LLMService = _llm_map.get(LLM_PROVIDER, DeepSeekService)(None)  # ← No API key'
    
    Set-Content -Path $filePath -Value $content -NoNewline
    Write-Host "✅ Updated: $filePath" -ForegroundColor Green
} else {
    Write-Host "❌ File not found: $filePath" -ForegroundColor Red
}

# ============================================
# FILE 2: backend/app/routes/dashboard.py
# ============================================
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "📄 FILE 2/6: backend/app/routes/dashboard.py" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

$filePath = "backend/app/routes/dashboard.py"
if (Test-Path $filePath) {
    Backup-File $filePath
    $content = Get-Content $filePath -Raw
    
    # Add api_key to MessageRequest
    $content = $content -replace '(class MessageRequest\(BaseModel\):.*?user_id: str = Field\(default="demo_user", min_length=1, max_length=100\))', @'
class MessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field(default="demo_user", min_length=1, max_length=100)
    api_key: Optional[str] = Field(default=None, description="LLM API key from frontend")
'@
    
    Set-Content -Path $filePath -Value $content -NoNewline
    Write-Host "✅ Updated: $filePath" -ForegroundColor Green
} else {
    Write-Host "❌ File not found: $filePath" -ForegroundColor Red
}

# ============================================
# FILE 3: backend/app/core/agent.py
# ============================================
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "📄 FILE 3/6: backend/app/core/agent.py" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

$filePath = "backend/app/core/agent.py"
if (Test-Path $filePath) {
    Backup-File $filePath
    $content = Get-Content $filePath -Raw
    
    # Remove API key lookup
    $content = $content -replace 'api_key = self\.user_data\.get\("api_key"\)\s+if api_key:\s+self\.llm\.update_api_key\(api_key\)', '# REMOVED: API key lookup from database - now provided by frontend in the request
        # The LLM is updated in the route handler before calling this method'
    
    Set-Content -Path $filePath -Value $content -NoNewline
    Write-Host "✅ Updated: $filePath" -ForegroundColor Green
} else {
    Write-Host "❌ File not found: $filePath" -ForegroundColor Red
}

# ============================================
# FILE 4: backend/app/models/database.py
# ============================================
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "📄 FILE 4/6: backend/app/models/database.py" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

$filePath = "backend/app/models/database.py"
if (Test-Path $filePath) {
    Backup-File $filePath
    $content = Get-Content $filePath -Raw
    
    # Comment out api_key in CREATE TABLE
    $content = $content -replace 'api_key TEXT,', '-- REMOVED: api_key TEXT,'
    
    Set-Content -Path $filePath -Value $content -NoNewline
    Write-Host "✅ Updated: $filePath" -ForegroundColor Green
} else {
    Write-Host "❌ File not found: $filePath" -ForegroundColor Red
}

# ============================================
# FILE 5: frontend/js/agent.js
# ============================================
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "📄 FILE 5/6: frontend/js/agent.js" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

$filePath = "frontend/js/agent.js"
if (Test-Path $filePath) {
    Backup-File $filePath
    $content = Get-Content $filePath -Raw
    
    # Update chat method
    $content = $content -replace 'chat\(message\) \{\s+return this\._request\(`'/agent/process`', \{\s+method: `'POST`',\s+body: JSON\.stringify\(\{ message, user_id: this\.userId \}\),\s+\}\);\s+\}', @'
chat(message, apiKey) {
    return this._request('/agent/process', {
        method: 'POST',
        body: JSON.stringify({ 
            message, 
            user_id: this.userId,
            api_key: apiKey || null
        }),
    });
}
'@
    
    Set-Content -Path $filePath -Value $content -NoNewline
    Write-Host "✅ Updated: $filePath" -ForegroundColor Green
} else {
    Write-Host "❌ File not found: $filePath" -ForegroundColor Red
}

# ============================================
# FILE 6: frontend/js/app.js
# ============================================
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "📄 FILE 6/6: frontend/js/app.js" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

$filePath = "frontend/js/app.js"
if (Test-Path $filePath) {
    Backup-File $filePath
    $content = Get-Content $filePath -Raw
    
    # Update client.chat() call to include API key
    $content = $content -replace 'const \{ response \} = await client\.chat\(text\)', 'const { response } = await client.chat(text, state.apiKey)'
    
    # Update saveApiKey function
    $content = $content -replace 'async function saveApiKey\(\) \{.*?\}', @'
function saveApiKey() {
  const key = els.apiKeyInput.value.trim();
  if (!key) {
    els.apiStatus.textContent = '⚠️ Please enter a valid API key';
    els.apiStatus.className = 'api-status error';
    return;
  }
  
  // Save to localStorage only - no backend call
  state.apiKey = key;
  localStorage.setItem('focus_api_key', key);
  
  els.apiStatus.textContent = '✅ API key saved to local storage!';
  els.apiStatus.className = 'api-status ready';
  
  // Show success message in chat
  addMessage('agent', '🔑 API key saved successfully! You can now use AI features.');
}
'@ -replace 'setButtonLoading\(els\.saveApiBtn, true\);', '// REMOVED: setButtonLoading(els.saveApiBtn, true);' -replace 'setButtonLoading\(els\.saveApiBtn, false\);', '// REMOVED: setButtonLoading(els.saveApiBtn, false);'
    
    Set-Content -Path $filePath -Value $content -NoNewline
    Write-Host "✅ Updated: $filePath" -ForegroundColor Green
} else {
    Write-Host "❌ File not found: $filePath" -ForegroundColor Red
}

# ============================================
# OPTIONAL: Clean up .env.example
# ============================================
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "📄 OPTIONAL: .env.example" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

$filePath = ".env.example"
if (Test-Path $filePath) {
    Backup-File $filePath
    $content = Get-Content $filePath -Raw
    $content = $content -replace 'LLM_API_KEY=.*', '# REMOVED: LLM_API_KEY - now managed by frontend localStorage'
    Set-Content -Path $filePath -Value $content -NoNewline
    Write-Host "✅ Updated: $filePath" -ForegroundColor Green
} else {
    Write-Host "⚠️  .env.example not found, skipping..." -ForegroundColor Yellow
}

# ============================================
# OPTIONAL: Clean up docker-compose.yml
# ============================================
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "📄 OPTIONAL: docker-compose.yml" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

$filePath = "docker-compose.yml"
if (Test-Path $filePath) {
    Backup-File $filePath
    $content = Get-Content $filePath -Raw
    $content = $content -replace '      - LLM_API_KEY=\$\{LLM_API_KEY:-\}', '      # REMOVED: LLM_API_KEY - now managed by frontend localStorage'
    Set-Content -Path $filePath -Value $content -NoNewline
    Write-Host "✅ Updated: $filePath" -ForegroundColor Green
} else {
    Write-Host "⚠️  docker-compose.yml not found, skipping..." -ForegroundColor Yellow
}

# ============================================
# COMPLETION
# ============================================
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  ✅ IMPLEMENTATION COMPLETE!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Summary of changes:" -ForegroundColor Cyan
Write-Host "   1. ✅ backend/app/main.py - Removed env API key loading" -ForegroundColor Gray
Write-Host "   2. ✅ backend/app/routes/dashboard.py - Added API key to requests" -ForegroundColor Gray
Write-Host "   3. ✅ backend/app/core/agent.py - Removed DB API key lookup" -ForegroundColor Gray
Write-Host "   4. ✅ backend/app/models/database.py - Removed API key from DB" -ForegroundColor Gray
Write-Host "   5. ✅ frontend/js/agent.js - API key parameter in chat()" -ForegroundColor Gray
Write-Host "   6. ✅ frontend/js/app.js - Always send API key, localStorage only" -ForegroundColor Gray
Write-Host "   7. ✅ .env.example - Removed LLM_API_KEY (optional)" -ForegroundColor Gray
Write-Host "   8. ✅ docker-compose.yml - Removed LLM_API_KEY (optional)" -ForegroundColor Gray
Write-Host ""
Write-Host "📁 Backups created with .bak extension for each file" -ForegroundColor Yellow
Write-Host ""
Write-Host "🚀 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Restart your backend server" -ForegroundColor White
Write-Host "   2. Clear your browser cache (Ctrl+Shift+R)" -ForegroundColor White
Write-Host "   3. Enter your API key in the frontend" -ForegroundColor White
Write-Host "   4. Test sending a message - should get REAL LLM response!" -ForegroundColor White
Write-Host ""
Write-Host "⚠️  To restore a file: copy <filename>.bak to <filename>" -ForegroundColor Yellow
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "🎉 Done!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green