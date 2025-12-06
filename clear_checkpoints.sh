#!/bin/bash
# Clear corrupted checkpoint directories to fix streaming errors
# Keeps only the final output checkpoints (kafka_alerts, mongodb)

echo "🧹 Cleaning corrupted checkpoint directories..."

cd /workspaces/real-time-network-intrusion-detection-spark-kafka/checkpoints

# Remove all UUID-named checkpoint directories (these are intermediate/corrupted)
for dir in */; do
    # Check if it's a UUID pattern (not kafka_alerts or mongodb)
    if [[ "$dir" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/$ ]]; then
        echo "Removing: $dir"
        rm -rf "$dir"
    else
        echo "Keeping: $dir"
    fi
done

echo "✅ Checkpoint cleanup complete!"
echo ""
echo "Remaining checkpoints:"
ls -la
