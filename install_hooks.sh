#!/bin/bash
# Install git hooks for the project
# Run this once after cloning: bash install_hooks.sh

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOKS_DIR="$PROJECT_ROOT/.git/hooks"

echo "Installing git hooks to $HOOKS_DIR..."

# Create pre-commit hook
cat > "$HOOKS_DIR/pre-commit" << 'HOOK_EOF'
#!/bin/bash
# Pre-commit hook: Test only when core pipeline files are modified
# Test files:
#   - src/core/markdown_to_bullet.py
#   - src/core/stage1_markdown.py
#   - src/core/file_cleaner.py

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEST_SCRIPT="$PROJECT_ROOT/test_pipeline.py"
BULLET_OUTPUT="$PROJECT_ROOT/sample/bullet.md"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if any core files were modified
STAGED_FILES=$(git diff --cached --name-only)

# Files that trigger test
TEST_TRIGGER_FILES=(
    "src/core/markdown_to_bullet.py"
    "src/core/stage1_markdown.py"
    "src/core/file_cleaner.py"
)

SHOULD_TEST=false
for file in "${TEST_TRIGGER_FILES[@]}"; do
    if echo "$STAGED_FILES" | grep -q "^$file$"; then
        SHOULD_TEST=true
        break
    fi
done

# If no trigger files modified, allow commit without testing
if [ "$SHOULD_TEST" = false ]; then
    exit 0
fi

# Core files were modified - run test
echo -e "${YELLOW}Core files modified - running pipeline test...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Run test pipeline
if python3 "$TEST_SCRIPT" > /tmp/test_output.log 2>&1; then
    echo -e "${GREEN}✓ Pipeline test passed${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Stage bullet.md if it was generated
    if [ -f "$BULLET_OUTPUT" ]; then
        echo -e "${GREEN}✓ bullet.md generated ($(stat -f%z "$BULLET_OUTPUT" 2>/dev/null || stat -c%s "$BULLET_OUTPUT") bytes)${NC}"
        git add "$BULLET_OUTPUT"
        echo -e "${GREEN}✓ bullet.md staged for commit${NC}"
    fi

    exit 0
else
    echo -e "${RED}✗ Pipeline test failed${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    cat /tmp/test_output.log
    echo ""
    echo -e "${RED}Commit aborted. Fix the test failures and try again.${NC}"
    exit 1
fi
HOOK_EOF

chmod +x "$HOOKS_DIR/pre-commit"
echo "✓ Pre-commit hook installed"
