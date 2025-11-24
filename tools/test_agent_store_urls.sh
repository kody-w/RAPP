#!/bin/bash
# Test RAPP Agent Store GitHub URLs
# Verifies that agent files are accessible from GitHub

echo "🧪 Testing RAPP Agent Store GitHub URLs"
echo "========================================="
echo ""

# GitHub configuration
GITHUB_OWNER="kody-w"
GITHUB_REPO="AI-Agent-Templates"
GITHUB_BRANCH="main"
GITHUB_RAW="https://raw.githubusercontent.com/${GITHUB_OWNER}/${GITHUB_REPO}/${GITHUB_BRANCH}"

# Test a few sample agents
declare -a TEST_AGENTS=(
    "energy_stacks:permit-license-management"
    "b2b_sales_stacks:account-intelligence"
    "financial_services_stacks:fraud-detection-alert"
    "general_stacks:customer-360"
)

SUCCESS_COUNT=0
FAIL_COUNT=0

echo "Testing ${#TEST_AGENTS[@]} sample agents..."
echo ""

for test_case in "${TEST_AGENTS[@]}"; do
    IFS=':' read -r category agent_id <<< "$test_case"

    # Construct URL
    stack_name="${agent_id}_stack"
    agent_file="${agent_id}_agent.py"
    url="${GITHUB_RAW}/agent_stacks/${category}/${stack_name}/agents/${agent_file}"

    echo "Testing: $agent_id"
    echo "  Category: $category"
    echo "  URL: $url"

    # Test if URL is accessible
    http_code=$(curl -s -o /dev/null -w "%{http_code}" "$url")

    if [ "$http_code" -eq 200 ]; then
        echo "  ✅ SUCCESS (HTTP $http_code)"
        ((SUCCESS_COUNT++))
    else
        echo "  ❌ FAILED (HTTP $http_code)"
        ((FAIL_COUNT++))

        # Try alternative paths
        echo "  🔍 Trying alternative paths..."

        # Try without agents/ subdirectory
        alt_url="${GITHUB_RAW}/agent_stacks/${category}/${stack_name}/${agent_file}"
        alt_http_code=$(curl -s -o /dev/null -w "%{http_code}" "$alt_url")

        if [ "$alt_http_code" -eq 200 ]; then
            echo "  ✅ Found at: $alt_url"
        else
            echo "  ❌ Not found at alternative path either"
        fi
    fi

    echo ""
done

echo "========================================="
echo "Test Results:"
echo "  ✅ Success: $SUCCESS_COUNT"
echo "  ❌ Failed: $FAIL_COUNT"
echo "  📊 Total: ${#TEST_AGENTS[@]}"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo "🎉 All tests passed!"
    exit 0
else
    echo "⚠️  Some tests failed. Check the GitHub repository structure."
    exit 1
fi
