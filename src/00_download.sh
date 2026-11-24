#!/bin/sh
# Download the PokerStars NL50 HandHQ files (~820 MB) from the public PHH dataset.
cd "$(dirname "$0")/../data" && mkdir -p raw && cd raw
base="https://raw.githubusercontent.com/uoftcprg/phh-dataset/main/data/handhq/PS-2009-07-01_2009-07-23_50NLH_OBFU/0.5"
seq 1 1299 | xargs -P 16 -I{} sh -c 'curl -sf --retry 3 -o "ps50_{}.phhs" "'$base'/ps%20NLH%20handhq_{}-OBFUSCATED.phhs"'
