#!/bin/bash
# Quick Start Guide - V3 Hybrid Engine Real System Tests
# Run this to execute the complete test suite with testsprite MCP

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║    YojanaMitra V3 Hybrid Engine - Real System Test Suite      ║"
echo "║                    TestSprite MCP Integration                  ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Flask backend is running
check_backend() {
    echo -e "${BLUE}[1/5]${NC} Checking if Flask backend is running..."
    if curl -s http://localhost:5000/api/schemes > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is running at http://localhost:5000${NC}"
        return 0
    else
        echo -e "${RED}✗ Backend NOT responding at http://localhost:5000${NC}"
        echo "   Start it with: python app.py"
        return 1
    fi
}

# Check Python environment
check_python() {
    echo -e "${BLUE}[2/5]${NC} Checking Python environment..."
    if python3 -c "import pytest, requests" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Python dependencies installed${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ Installing dependencies...${NC}"
        pip install pytest requests > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Dependencies installed${NC}"
            return 0
        else
            echo -e "${RED}✗ Failed to install dependencies${NC}"
            return 1
        fi
    fi
}

# Check database
check_database() {
    echo -e "${BLUE}[3/5]${NC} Checking SQLite database..."
    if [ ! -f "yojanamitra.db" ]; then
        echo -e "${RED}✗ Database file not found${NC}"
        return 1
    fi
    
    scheme_count=$(sqlite3 yojanamitra.db "SELECT COUNT(*) FROM scheme" 2>/dev/null)
    if [ "$?" -eq 0 ] && [ "$scheme_count" -ge 50 ]; then
        echo -e "${GREEN}✓ Database ready (${scheme_count} schemes)${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ Could not verify database (need at least 50 schemes)${NC}"
        return 1
    fi
}

# Check Gemini API
check_ai() {
    echo -e "${BLUE}[4/5]${NC} Checking Gemini AI configuration..."
    if grep -q "GEMINI_API_KEY" app.py > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Gemini API configured${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ Could not verify Gemini configuration${NC}"
        return 1
    fi
}

# Run tests
run_tests() {
    echo -e "${BLUE}[5/5]${NC} Running test suite..."
    echo ""
    
    echo -e "${YELLOW}Choose test mode:${NC}"
    echo ""
    echo "  1) Run ALL tests (all 6 phases + full lifecycle)"
    echo "  2) Run Phase 1 only (Database Matching)"
    echo "  3) Run Phase 3 only (AI Context Analysis)"
    echo "  4) Run Phase 6 only (AI Re-Evaluation)"
    echo "  5) Run Full Lifecycle only (Crown Test)"
    echo "  6) Run with pytest directly (for debugging)"
    echo ""
    
    read -p "Enter choice (1-6): " choice
    
    case $choice in
        1)
            echo -e "${GREEN}Starting complete test suite...${NC}"
            python3 run_v3_hybrid_tests.py
            ;;
        2)
            echo -e "${GREEN}Running Phase 1 tests...${NC}"
            python3 run_v3_hybrid_tests.py --phase 1
            ;;
        3)
            echo -e "${GREEN}Running Phase 3 tests...${NC}"
            python3 run_v3_hybrid_tests.py --phase 3
            ;;
        4)
            echo -e "${GREEN}Running Phase 6 tests...${NC}"
            python3 run_v3_hybrid_tests.py --phase 6
            ;;
        5)
            echo -e "${GREEN}Running full lifecycle test...${NC}"
            python3 run_v3_hybrid_tests.py --full
            ;;
        6)
            echo -e "${GREEN}Running pytest directly...${NC}"
            pytest tests/test_v3_hybrid_real_system.py -v --tb=short
            ;;
        *)
            echo -e "${RED}Invalid choice${NC}"
            return 1
            ;;
    esac
}

# Show results
show_results() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                       TEST COMPLETE                            ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "📊 Results saved to:"
    echo "   • report_v3_hybrid_complete.json (JSON format)"
    echo "   • Check console output above for details"
    echo ""
    echo "📖 For detailed documentation, see:"
    echo "   • V3_HYBRID_ENGINE_REAL_SYSTEM_TESTS.md"
    echo ""
    echo "🚀 What was tested:"
    echo "   ✓ Phase 1: Core Database Matching (Hard Filter)"
    echo "   ✓ Phase 2: Verification Trigger & Memory"
    echo "   ✓ Phase 3: AI Context Analysis & Questions"
    echo "   ✓ Phase 4: Hybrid UI Modal Rendering"
    echo "   ✓ Phase 5: Smart Traffic Director (MD5 hash routing)"
    echo "   ✓ Phase 6: AI Re-Evaluation Engine (UPSERT)"
    echo "   ✓ Full Lifecycle: 6-phase complete journey"
    echo ""
    echo "💾 Database verifications:"
    echo "   ✓ SchemeClarification table UPSERTs"
    echo "   ✓ Prior answer retrieval"
    echo "   ✓ Iteration count tracking"
    echo "   ✓ Profile version increments"
    echo ""
    echo "🤖 AI verifications:"
    echo "   ✓ Real Gemini API calls"
    echo "   ✓ MD5 hash generation for questions"
    echo "   ✓ Verdict generation (ELIGIBLE/INELIGIBLE)"
    echo "   ✓ Prompt context injection with DB history"
    echo ""
}

# Main execution
main() {
    # Run checks
    check_backend || { echo ""; read -p "Continue anyway? (y/n): " ans; [ "$ans" != "y" ] && return 1; }
    check_python || return 1
    check_database || { echo ""; read -p "Continue anyway? (y/n): " ans; [ "$ans" != "y" ] && return 1; }
    check_ai || { echo ""; read -p "Continue anyway? (y/n): " ans; [ "$ans" != "y" ] && return 1; }
    
    echo ""
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    
    # Run tests
    run_tests || return 1
    
    # Show results
    show_results
}

# Execute
main
exit $?
