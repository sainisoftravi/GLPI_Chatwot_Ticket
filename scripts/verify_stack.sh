#!/usr/bin/env bash
# ==============================================================================
# Stack Health & Configuration Verifier
# Run this script anytime on your server to check the status of all components.
# ==============================================================================

echo "=========================================================================="
echo " 🔍 IT Ticketing & WhatsApp AI Stack Health Check "
echo "=========================================================================="
echo ""

PASS=0
WARN=0
FAIL=0

check_endpoint() {
    local name="$1"
    local url="$2"
    local expected_code="$3"
    
    echo -n "Testing $name ($url)... "
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" || echo "000")
    
    if [ "$response" = "$expected_code" ] || [ "$response" = "200" ] || [ "$response" = "302" ]; then
        echo "✅ ONLINE (HTTP $response)"
        ((PASS++))
    else
        echo "❌ OFFLINE or UNREACHABLE (HTTP $response)"
        ((FAIL++))
    fi
}

# 1. Test Container Connectivity
echo "[1] Checking Container Endpoints..."
check_endpoint "GLPI ITSM Portal" "http://localhost:8085" "200"
check_endpoint "Chatwoot Web Dashboard" "http://localhost:8050" "200"
check_endpoint "OpenWA WhatsApp Gateway" "http://localhost:2785" "200"
check_endpoint "Integration Bridge" "http://localhost:5050/health" "200"
echo ""

# 2. Check Docker Container Status
echo "[2] Docker Container Status:"
if command -v docker &>/dev/null; then
    docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || docker-compose ps
else
    echo "❌ Docker command not found."
fi
echo ""

# 3. Check Configuration File (.env)
echo "[3] Checking Configuration & Tokens in .env..."
if [ -f .env ]; then
    echo "✅ .env file exists."
    
    check_env_var() {
        local var_name="$1"
        local val
        val=$(grep "^${var_name}=" .env | cut -d '=' -f2- | tr -d '"' | tr -d "'" | tr -d ' ')
        if [ -n "$val" ] && [ "$val" != "your_${var_name,,}_here" ] && [ "$val" != "your_openwa_api_key_here" ]; then
            echo "   ✅ $var_name is configured"
            ((PASS++))
        else
            echo "   ⚠️ $var_name is NOT configured or still using placeholder"
            ((WARN++))
        fi
    }
    
    check_env_var "GLPI_APP_TOKEN"
    check_env_var "GLPI_USER_TOKEN"
    check_env_var "OPENWA_API_KEY"
    check_env_var "CHATWOOT_API_ACCESS_TOKEN"
else
    echo "❌ .env file missing! Create one using: cp .env.example .env"
    ((FAIL++))
fi

echo ""
echo "=========================================================================="
echo " Summary: $PASS Passed, $WARN Warnings, $FAIL Failed"
echo "=========================================================================="
if [ "$WARN" -gt 0 ]; then
    echo "👉 Tip: Complete the missing tokens in .env by following docs/INSTALLATION_GUIDE.md"
fi
if [ "$FAIL" -eq 0 ] && [ "$WARN" -eq 0 ]; then
    echo "🎉 All systems operational! The end-to-end integration is ready."
fi

