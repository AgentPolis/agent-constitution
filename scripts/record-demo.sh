#!/bin/bash
# Record demo GIF for README
# Prerequisites:
#   brew install asciinema
#   cargo install --git https://github.com/asciinema/agg  (or: brew install agg)
#
# Usage: ./scripts/record-demo.sh

set -e

CAST_FILE="/tmp/ac-demo.cast"
GIF_FILE="assets/demo.gif"

echo "=== Step 1: Record the demo ==="
echo "A terminal will open. Run these commands:"
echo ""
echo "  ac debate \"Should we build an AI code review tool?\""
echo ""
echo "  Then press Ctrl-D or type 'exit' to stop recording."
echo ""

# Record with asciinema
asciinema rec "$CAST_FILE" \
  --cols 90 \
  --rows 30 \
  --idle-time-limit 2

echo ""
echo "=== Step 2: Convert to GIF ==="

# Convert to GIF
agg "$CAST_FILE" "$GIF_FILE" \
  --cols 90 \
  --rows 30 \
  --font-size 14 \
  --theme monokai

echo ""
echo "=== Done! ==="
echo "GIF saved to: $GIF_FILE"
echo ""
echo "Next steps:"
echo "1. Check the GIF looks good: open $GIF_FILE"
echo "2. Uncomment the GIF line in README.md"
echo "3. git add assets/demo.gif README.md && git commit -m 'feat: add demo GIF'"
